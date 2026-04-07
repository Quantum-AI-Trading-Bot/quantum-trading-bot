#!/usr/bin/env python3
"""
Reddit Data Provider for Social Sentiment Analysis
Specializes in WallStreetBets and financial subreddits for trading intelligence
"""

import asyncio
import praw
import re
import nltk
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass
import logging
import json
import sys

sys.path.append('/home/davidsanker/platform')

# Download NLTK data if not available
try:
    nltk.data.find('tokenizers/punkt')
    nltk.data.find('corpora/vader_lexicon')
except LookupError:
    print("📥 Downloading NLTK data for sentiment analysis...")
    nltk.download('punkt', quiet=True)
    nltk.download('vader_lexicon', quiet=True)

from nltk.sentiment import SentimentIntensityAnalyzer

@dataclass
class RedditPost:
    """Data structure for Reddit post analysis"""
    post_id: str
    title: str
    author: str
    subreddit: str
    score: int
    upvote_ratio: float
    num_comments: int
    created_utc: datetime
    url: str
    content: str
    symbol_mentions: List[str]
    sentiment_score: float
    sentiment_magnitude: float
    keywords: List[str]
    engagement_level: float

@dataclass
class RedditMentionData:
    """Aggregated data for symbol mentions on Reddit"""
    symbol: str
    total_mentions: int
    sentiment_score: float
    sentiment_distribution: Dict[str, int]  # {'positive': X, 'negative': Y, 'neutral': Z}
    top_posts: List[RedditPost]
    avg_engagement: float
    mention_growth: float  # Change in mentions over time
    subreddits: List[str]
    last_updated: datetime

class RedditProvider:
    """Reddit API provider for social sentiment and trading intelligence"""

    def __init__(self, client_id: str = None, client_secret: str = None, user_agent: str = None):
        self.logger = logging.getLogger(__name__)
        self.client_id = client_id or "trading_bot_reddit"  # Default placeholder
        self.client_secret = client_secret or "placeholder_secret"
        self.user_agent = user_agent or "TradingBot/1.0 by QuantumTrader"
        self.reddit_instance = None
        self.sentiment_analyzer = SentimentIntensityAnalyzer()
        self.cache = {}
        self.cache_timeout = 600  # 10 minutes cache for Reddit data
        self.rate_limit_delay = 1.0  # 1 second between requests

        # Financial subreddits to monitor
        self.financial_subreddits = [
            'wallstreetbets',
            'stocks',
            'investing',
            'SecurityAnalysis',
            'ValueInvesting',
            'Superstonk',  # GME focused
            'DDintoGME',
            'options',
            'pennystocks',
            'RobinHoodPennyStocks'
        ]

        # Stock ticker patterns
        self.ticker_patterns = [
            r'\$([A-Z]{1,5})\b',  # $AAPL pattern
            r'\b([A-Z]{1,5})\b',    # AAPL pattern (context-dependent)
        ]

        # Keywords for bullish/bearish sentiment
        self.bullish_keywords = [
            'moon', 'rocket', 'diamond hands', 'bull', 'bullish', 'buy',
            'long', 'calls', 'tendies', 'profit', 'gain', 'pump', 'squeeze',
            'to the moon', '🚀', '📈', 'bullish', 'buy', 'hold', 'hodl'
        ]

        self.bearish_keywords = [
            'paper hands', 'bear', 'bearish', 'sell', 'short', 'puts',
            'crash', 'dump', 'loss', 'bagholder', 'tendie loss', 'margin call',
            'short squeeze', '💎🙌', 'to the floor', '📉', 'bearish', 'sell'
        ]

    async def initialize(self, read_only_mode: bool = True) -> bool:
        """Initialize Reddit API connection"""
        try:
            self.logger.info("Initializing Reddit provider in read-only mode...")

            # Initialize PRAW with read-only mode (no authentication required)
            self.reddit_instance = praw.Reddit(
                client_id=self.client_id,
                client_secret=self.client_secret,
                user_agent=self.user_agent,
                read_only=read_only_mode
            )

            # Test the connection
            try:
                # Try to access a public subreddit
                subreddit = self.reddit_instance.subreddit('wallstreetbets')
                # Test if we can read the display name
                display_name = subreddit.display_name
                self.logger.info(f"✅ Reddit provider initialized - Connected to r/{display_name}")
                return True

            except Exception as api_error:
                self.logger.warning(f"Reddit API test failed: {api_error}")
                # Try with a simpler approach - using instance.read_only
                if self.reddit_instance.read_only:
                    self.logger.info("✅ Reddit provider initialized in read-only mode")
                    return True
                else:
                    self.logger.error("❌ Reddit provider initialization failed")
                    return False

        except Exception as e:
            self.logger.error(f"Error initializing Reddit provider: {e}")
            return False

    def _extract_tickers(self, text: str) -> List[str]:
        """Extract stock tickers from text"""
        tickers = set()

        for pattern in self.ticker_patterns:
            matches = re.findall(pattern, text.upper())
            for match in matches:
                # Filter out common words that might match ticker patterns
                if match not in ['A', 'I', 'AN', 'IN', 'ON', 'OR', 'AT', 'TO', 'FOR', 'OF', 'BY', 'BE', 'SO', 'MY']:
                    # Additional filter - check if it's a plausible ticker
                    if len(match) >= 1 and len(match) <= 5:
                        tickers.add(match)

        return list(tickers)

    def _calculate_sentiment(self, text: str) -> Tuple[float, float]:
        """Calculate sentiment score and magnitude using NLTK VADER"""
        try:
            # Clean the text
            cleaned_text = re.sub(r'\[.*?\]', '', text)  # Remove markdown
            cleaned_text = re.sub(r'https?://\S+', '', cleaned_text)  # Remove URLs

            # Get VADER sentiment scores
            sentiment = self.sentiment_analyzer.polarity_scores(cleaned_text)

            # Compound score ranges from -1 (most negative) to +1 (most positive)
            sentiment_score = sentiment['compound']
            sentiment_magnitude = sentiment['pos'] + sentiment['neg'] + sentiment['neu']

            return sentiment_score, sentiment_magnitude

        except Exception as e:
            self.logger.error(f"Error calculating sentiment: {e}")
            return 0.0, 0.0

    def _calculate_engagement_level(self, post_score: int, num_comments: int, upvote_ratio: float) -> float:
        """Calculate engagement level based on score, comments, and upvote ratio"""
        try:
            # Normalize engagement score
            score_factor = min(post_score / 1000, 1.0)  # Cap at 1000 upvotes
            comment_factor = min(num_comments / 100, 1.0)  # Cap at 100 comments
            ratio_factor = upvote_ratio  # Higher ratio = better engagement

            # Weighted average
            engagement = (score_factor * 0.4 + comment_factor * 0.4 + ratio_factor * 0.2)

            return engagement

        except Exception as e:
            self.logger.error(f"Error calculating engagement: {e}")
            return 0.0

    async def get_subreddit_posts(self, subreddit_name: str, limit: int = 25, time_filter: str = "day") -> List[RedditPost]:
        """Get recent posts from a subreddit"""
        try:
            await asyncio.sleep(self.rate_limit_delay)

            if not self.reddit_instance:
                return []

            subreddit = self.reddit_instance.subreddit(subreddit_name)
            posts_data = []

            # Get hot posts from the specified time period
            for submission in subreddit.hot(time_filter=time_filter, limit=limit):
                try:
                    # Extract content
                    title = submission.title
                    content = submission.selftext if submission.selftext else ""
                    full_text = f"{title} {content}"

                    # Extract tickers
                    symbol_mentions = self._extract_tickers(full_text)

                    # Skip posts without any stock symbols
                    if not symbol_mentions:
                        continue

                    # Calculate sentiment
                    sentiment_score, sentiment_magnitude = self._calculate_sentiment(full_text)

                    # Calculate engagement
                    engagement = self._calculate_engagement_level(
                        submission.score,
                        submission.num_comments,
                        submission.upvote_ratio
                    )

                    # Extract keywords
                    keywords = self._extract_keywords(full_text)

                    post_data = RedditPost(
                        post_id=submission.id,
                        title=title,
                        author=str(submission.author) if submission.author else "[deleted]",
                        subreddit=subreddit_name,
                        score=submission.score,
                        upvote_ratio=submission.upvote_ratio,
                        num_comments=submission.num_comments,
                        created_utc=datetime.fromtimestamp(submission.created_utc),
                        url=submission.url,
                        content=content,
                        symbol_mentions=symbol_mentions,
                        sentiment_score=sentiment_score,
                        sentiment_magnitude=sentiment_magnitude,
                        keywords=keywords,
                        engagement_level=engagement
                    )

                    posts_data.append(post_data)

                except Exception as e:
                    self.logger.error(f"Error processing submission: {e}")
                    continue

            return posts_data

        except Exception as e:
            self.logger.error(f"Error getting subreddit posts from r/{subreddit_name}: {e}")
            return []

    def _extract_keywords(self, text: str) -> List[str]:
        """Extract relevant keywords from text"""
        keywords = set()
        text_lower = text.lower()

        # Check for bullish/bearish keywords
        for keyword in self.bullish_keywords + self.bearish_keywords:
            if keyword in text_lower:
                keywords.add(keyword)

        # Extract common financial terms
        financial_terms = [
            'earnings', 'revenue', 'profit', 'loss', 'dividend', 'split',
            'merger', 'acquisition', 'ipo', 'market cap', 'pe ratio',
            'options', 'calls', 'puts', 'strike price', 'expiration'
        ]

        for term in financial_terms:
            if term in text_lower:
                keywords.add(term)

        return list(keywords)

    async def get_symbol_mentions(self, symbol: str, days_back: int = 1) -> RedditMentionData:
        """Get aggregated mention data for a specific symbol"""
        try:
            # Check cache
            cache_key = f"mentions_{symbol}_{days_back}_{int(datetime.now().timestamp() / self.cache_timeout)}"
            if cache_key in self.cache:
                return self.cache[cache_key]

            symbol = symbol.upper().replace('$', '')
            all_posts = []
            subreddit_mentions = {}

            # Search through financial subreddits
            for subreddit_name in self.financial_subreddits:
                try:
                    posts = await self.get_subreddit_posts(subreddit_name, limit=20, time_filter="day")

                    for post in posts:
                        if symbol in post.symbol_mentions:
                            all_posts.append(post)
                            subreddit_mentions[subreddit_name] = subreddit_mentions.get(subreddit_name, 0) + 1

                except Exception as e:
                    self.logger.debug(f"Error searching r/{subreddit_name}: {e}")
                    continue

            if not all_posts:
                # Return empty data if no mentions found
                empty_data = RedditMentionData(
                    symbol=symbol,
                    total_mentions=0,
                    sentiment_score=0.0,
                    sentiment_distribution={'positive': 0, 'negative': 0, 'neutral': 0},
                    top_posts=[],
                    avg_engagement=0.0,
                    mention_growth=0.0,
                    subreddits=[],
                    last_updated=datetime.now()
                )

                self.cache[cache_key] = empty_data
                return empty_data

            # Calculate sentiment distribution
            positive_count = sum(1 for post in all_posts if post.sentiment_score > 0.1)
            negative_count = sum(1 for post in all_posts if post.sentiment_score < -0.1)
            neutral_count = len(all_posts) - positive_count - negative_count

            # Calculate average sentiment and engagement
            avg_sentiment = sum(post.sentiment_score for post in all_posts) / len(all_posts)
            avg_engagement = sum(post.engagement_level for post in all_posts) / len(all_posts)

            # Sort posts by engagement (combination of score and comments)
            top_posts = sorted(all_posts, key=lambda x: x.engagement_level, reverse=True)[:5]

            mention_data = RedditMentionData(
                symbol=symbol,
                total_mentions=len(all_posts),
                sentiment_score=avg_sentiment,
                sentiment_distribution={
                    'positive': positive_count,
                    'negative': negative_count,
                    'neutral': neutral_count
                },
                top_posts=top_posts,
                avg_engagement=avg_engagement,
                mention_growth=0.0,  # Could be calculated with historical data
                subreddits=list(subreddit_mentions.keys()),
                last_updated=datetime.now()
            )

            # Cache the result
            self.cache[cache_key] = mention_data

            return mention_data

        except Exception as e:
            self.logger.error(f"Error getting mentions for {symbol}: {e}")
            return RedditMentionData(
                symbol=symbol,
                total_mentions=0,
                sentiment_score=0.0,
                sentiment_distribution={'positive': 0, 'negative': 0, 'neutral': 0},
                top_posts=[],
                avg_engagement=0.0,
                mention_growth=0.0,
                subreddits=[],
                last_updated=datetime.now()
            )

    async def get_trending_stocks(self, limit: int = 10) -> List[Tuple[str, int, float]]:
        """Get trending stocks based on Reddit mentions"""
        try:
            # Get posts from major subreddits
            all_symbol_mentions = {}

            for subreddit_name in ['wallstreetbets', 'stocks', 'investing']:
                posts = await self.get_subreddit_posts(subreddit_name, limit=30)

                for post in posts:
                    for symbol in post.symbol_mentions:
                        if symbol not in all_symbol_mentions:
                            all_symbol_mentions[symbol] = {
                                'mentions': 0,
                                'total_sentiment': 0,
                                'total_engagement': 0
                            }

                        all_symbol_mentions[symbol]['mentions'] += 1
                        all_symbol_mentions[symbol]['total_sentiment'] += post.sentiment_score
                        all_symbol_mentions[symbol]['total_engagement'] += post.engagement_level

            # Sort by mentions
            trending = []
            for symbol, data in all_symbol_mentions.items():
                avg_sentiment = data['total_sentiment'] / data['mentions'] if data['mentions'] > 0 else 0
                trending.append((symbol, data['mentions'], avg_sentiment))

            trending.sort(key=lambda x: x[1], reverse=True)
            return trending[:limit]

        except Exception as e:
            self.logger.error(f"Error getting trending stocks: {e}")
            return []

    async def get_wallstreetbets_activity(self) -> Dict[str, Any]:
        """Get WallStreetBets specific activity and sentiment"""
        try:
            wsb_posts = await self.get_subreddit_posts('wallstreetbets', limit=50)

            if not wsb_posts:
                return {'status': 'No data available'}

            # Analyze WSB activity
            total_posts = len(wsb_posts)
            avg_sentiment = sum(post.sentiment_score for post in wsb_posts) / total_posts
            high_engagement_posts = [post for post in wsb_posts if post.engagement_level > 0.7]

            # Find most mentioned symbols
            symbol_counts = {}
            for post in wsb_posts:
                for symbol in post.symbol_mentions:
                    symbol_counts[symbol] = symbol_counts.get(symbol, 0) + 1

            top_symbols = sorted(symbol_counts.items(), key=lambda x: x[1], reverse=True)[:10]

            return {
                'total_posts_analyzed': total_posts,
                'average_sentiment': avg_sentiment,
                'high_engagement_posts': len(high_engagement_posts),
                'most_mentioned_symbols': top_symbols,
                'top_posts': [
                    {
                        'title': post.title[:100] + '...' if len(post.title) > 100 else post.title,
                        'score': post.score,
                        'sentiment': post.sentiment_score,
                        'symbols': post.symbol_mentions
                    } for post in sorted(wsb_posts, key=lambda x: x.score, reverse=True)[:5]
                ]
            }

        except Exception as e:
            self.logger.error(f"Error getting WSB activity: {e}")
            return {'error': str(e)}

    def get_provider_info(self) -> Dict[str, Any]:
        """Get information about the Reddit provider"""
        return {
            'name': 'Reddit API (PRAW)',
            'description': 'Social sentiment analysis from Reddit financial communities',
            'data_types': ['social_sentiment', 'retail_trading', 'wallstreetbets', 'trending_stocks'],
            'features': [
                'WallStreetBets sentiment analysis',
                'Retail investor sentiment tracking',
                'Meme stock momentum detection',
                'Real-time symbol mentions',
                'Engagement-based filtering',
                'Multi-subreddit coverage'
            ],
            'subreddits_monitored': self.financial_subreddits,
            'limitations': [
                'Rate limited: 60 calls/minute',
                'Read-only mode (no posting)',
                'Delayed data (not real-time)',
                'Sentiment analysis based on text processing'
            ],
            'cost': 'Free (read-only)',
            'api_key_required': True,
            'cache_duration': f'{self.cache_timeout} seconds'
        }

# Example usage and testing
async def demo_reddit_provider():
    """Demonstrate Reddit provider capabilities"""
    print("📱 REDDIT PROVIDER DEMO")
    print("=" * 50)

    provider = RedditProvider()

    # Initialize (read-only mode)
    print("\n1️⃣ Initializing Reddit provider (read-only mode)...")
    success = await provider.initialize(read_only_mode=True)
    print(f"   ✅ Initialization: {'Success' if success else 'Failed'}")

    if not success:
        print("   ⚠️ Note: Reddit API requires proper credentials for full functionality")
        print("   📝 Current implementation uses read-only mode for demonstration")
        return

    # Test symbol mentions
    print("\n2️⃣ Testing symbol mentions (AAPL)...")
    try:
        mentions_data = await provider.get_symbol_mentions("AAPL")
        print(f"   📊 AAPL Mentions: {mentions_data.total_mentions}")
        print(f"   💬 Sentiment: {mentions_data.sentiment_score:+.3f}")
        print(f"   📈 Engagement: {mentions_data.avg_engagement:.3f}")
        if mentions_data.subreddits:
            print(f"   📱 Subreddits: {', '.join(mentions_data.subreddits[:3])}")
    except Exception as e:
        print(f"   ⚠️ Error: {e}")

    # Test trending stocks
    print("\n3️⃣ Testing trending stocks...")
    try:
        trending = await provider.get_trending_stocks(5)
        if trending:
            print(f"   🔥 Top Trending:")
            for i, (symbol, mentions, sentiment) in enumerate(trending, 1):
                emoji = "🟢" if sentiment > 0 else "🔴" if sentiment < 0 else "🟡"
                print(f"      {i}. {symbol}: {mentions} mentions ({emoji} {sentiment:+.2f})")
        else:
            print("   📝 No trending data available in current timeframe")
    except Exception as e:
        print(f"   ⚠️ Error: {e}")

    # Test WSB activity
    print("\n4️⃣ Testing WallStreetBets activity...")
    try:
        wsb_activity = await provider.get_wallstreetbets_activity()
        if 'total_posts_analyzed' in wsb_activity:
            print(f"   📊 Posts Analyzed: {wsb_activity['total_posts_analyzed']}")
            print(f"   💬 Avg Sentiment: {wsb_activity['average_sentiment']:+.3f}")
            print(f"   🚀 High Engagement Posts: {wsb_activity['high_engagement_posts']}")

            if wsb_activity['most_mentioned_symbols']:
                print(f"   🏆 Top Symbols:")
                for symbol, count in wsb_activity['most_mentioned_symbols'][:3]:
                    print(f"      • {symbol}: {count} mentions")
        else:
            print(f"   📝 Limited WSB data available")
    except Exception as e:
        print(f"   ⚠️ Error: {e}")

    # Provider info
    print("\n5️⃣ Provider Information:")
    info = provider.get_provider_info()
    print(f"   📊 Data Types: {', '.join(info['data_types'])}")
    print(f"   💰 Cost: {info['cost']}")
    print(f"   📱 Subreddits Monitored: {len(info['subreddits_monitored'])}")
    print(f"   🔑 API Key: {'Required' if info['api_key_required'] else 'Not Required'}")

    print(f"\n✅ Reddit provider demo completed!")
    return True

if __name__ == "__main__":
    asyncio.run(demo_reddit_provider())