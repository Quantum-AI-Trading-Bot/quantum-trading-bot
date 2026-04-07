#!/usr/bin/env python3
"""
Advanced Sentiment Analysis Module for Quantum Trading Bot
Integrates real-time sentiment from Twitter, Reddit, news, and financial blogs
"""

import asyncio
import aiohttp
import json
import numpy as np
import pandas as pd
from datetime import datetime, timezone, timedelta
import logging
import re
from typing import Dict, List, Optional, Tuple, Any
import hashlib
from dataclasses import dataclass, asdict
from textblob import TextBlob
import requests
from collections import defaultdict, deque
import time
import threading

# Try to import NLTK for more advanced sentiment analysis
try:
    import nltk
    from nltk.sentiment.vader import SentimentIntensityAnalyzer
    from nltk.tokenize import word_tokenize
    from nltk.corpus import stopwords
    NLTK_AVAILABLE = True
except ImportError:
    NLTK_AVAILABLE = False

# Try to import transformers for advanced NLP
try:
    from transformers import pipeline, AutoTokenizer, AutoModelForSequenceClassification
    TRANSFORMERS_AVAILABLE = True
except ImportError:
    TRANSFORMERS_AVAILABLE = False

@dataclass
class SentimentData:
    """Sentiment data structure with quantum-ready formatting"""
    source: str
    symbol: str
    timestamp: datetime
    sentiment_score: float  # -1 to 1
    confidence: float  # 0 to 1
    volume: int  # number of mentions
    text_sample: str
    keywords: List[str]
    volatility_indicator: float
    quantum_signature: str

    def to_dict(self) -> Dict:
        """Convert to dictionary for JSON serialization"""
        data = asdict(self)
        data['timestamp'] = self.timestamp.isoformat()
        return data

    def generate_quantum_signature(self) -> str:
        """Generate quantum-inspired signature for sentiment data"""
        content = f"{self.source}{self.symbol}{self.timestamp}{self.sentiment_score}{self.volume}"
        return hashlib.sha256(content.encode()).hexdigest()[:32]

class TwitterSentimentAnalyzer:
    """Real-time Twitter sentiment analysis for trading symbols"""

    def __init__(self, api_config: Dict = None):
        self.api_config = api_config or {}
        self.session = None
        self.logger = logging.getLogger(__name__)
        self.sentiment_cache = defaultdict(lambda: deque(maxlen=1000))
        self.rate_limits = {}
        self.running = False

        # Advanced sentiment analyzer
        if NLTK_AVAILABLE:
            try:
                nltk.data.find('vader_lexicon')
            except LookupError:
                nltk.download('vader_lexicon', quiet=True)
            try:
                nltk.data.find('tokenizers/punkt')
            except LookupError:
                nltk.download('punkt', quiet=True)
            try:
                nltk.data.find('corpora/stopwords')
            except LookupError:
                nltk.download('stopwords', quiet=True)

            self.vader = SentimentIntensityAnalyzer()

        if TRANSFORMERS_AVAILABLE:
            try:
                self.finbert_pipeline = pipeline(
                    "sentiment-analysis",
                    model="yiyanghkust/finbert-tone",
                    tokenizer="yiyanghkust/finbert-tone"
                )
            except Exception:
                self.finbert_pipeline = None

    async def initialize(self):
        """Initialize async session and connections"""
        self.session = aiohttp.ClientSession(
            timeout=aiohttp.ClientTimeout(total=30),
            headers={'User-Agent': 'QuantumTradingBot/1.0'}
        )

    async def search_twitter(self, symbol: str, count: int = 100) -> List[Dict]:
        """Search Twitter for symbol-related tweets using various methods"""
        tweets = []

        # Method 1: Try official API if available
        if self.api_config.get('bearer_token'):
            tweets.extend(await self._search_official_api(symbol, count))

        # Method 2: Fallback to web scraping (Twitter's advanced search)
        tweets.extend(await self._scrape_twitter_web(symbol, count))

        return tweets

    async def _search_official_api(self, symbol: str, count: int) -> List[Dict]:
        """Search using Twitter's official API v2"""
        try:
            url = "https://api.twitter.com/2/tweets/search/recent"
            query = f"${symbol} OR #{symbol} OR {symbol} stock -is:retweet lang:en"

            params = {
                'query': query,
                'max_results': min(count, 100),
                'tweet.fields': 'created_at,public_metrics,lang,context_annotations',
                'expansions': 'author_id,attachments.media_keys'
            }

            headers = {
                'Authorization': f"Bearer {self.api_config['bearer_token']}",
                'Content-Type': 'application/json'
            }

            async with self.session.get(url, params=params, headers=headers) as response:
                if response.status == 200:
                    data = await response.json()
                    return self._process_twitter_response(data)
                else:
                    self.logger.warning(f"Twitter API error: {response.status}")
                    return []

        except Exception as e:
            self.logger.error(f"Twitter API search failed: {e}")
            return []

    async def _scrape_twitter_web(self, symbol: str, count: int) -> List[Dict]:
        """Fallback method: scrape Twitter web search"""
        tweets = []
        try:
            search_url = f"https://twitter.com/search?q={symbol}%20stock&src=typed_query&f=live"

            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
                'Accept-Language': 'en-US,en;q=0.5',
                'Accept-Encoding': 'gzip, deflate',
                'Connection': 'keep-alive',
            }

            async with self.session.get(search_url, headers=headers) as response:
                if response.status == 200:
                    content = await response.text()
                    # Parse HTML for tweet data (simplified parsing)
                    tweets = self._parse_twitter_html(content, symbol)

        except Exception as e:
            self.logger.error(f"Twitter web scraping failed: {e}")

        return tweets

    def _process_twitter_response(self, data: Dict) -> List[Dict]:
        """Process Twitter API v2 response"""
        tweets = []
        if 'data' in data:
            for tweet in data['data']:
                tweets.append({
                    'id': tweet['id'],
                    'text': tweet['text'],
                    'created_at': tweet['created_at'],
                    'public_metrics': tweet.get('public_metrics', {}),
                    'source': 'twitter_api_v2'
                })
        return tweets

    def _parse_twitter_html(self, html: str, symbol: str) -> List[Dict]:
        """Parse HTML content for tweet data"""
        tweets = []
        # This is a simplified parser - in production, use proper HTML parsing
        tweet_pattern = r'<div[^>]*data-testid="tweet"[^>]*>(.*?)</div>'

        matches = re.findall(tweet_pattern, html, re.DOTALL)[:50]  # Limit results

        for match in matches:
            # Extract text from HTML
            text_match = re.search(r'<div[^>]*data-testid="tweetText"[^>]*>(.*?)</div>', match, re.DOTALL)
            if text_match:
                text = re.sub(r'<[^>]+>', '', text_match.group(1)).strip()
                if len(text) > 20:  # Filter very short texts
                    tweets.append({
                        'text': text,
                        'created_at': datetime.now(timezone.utc).isoformat(),
                        'source': 'twitter_web_scrape',
                        'symbol': symbol
                    })

        return tweets

    def analyze_sentiment(self, text: str) -> Tuple[float, float]:
        """Analyze sentiment using multiple methods"""
        if not text or len(text.strip()) < 3:
            return 0.0, 0.0

        # Method 1: TextBlob (baseline)
        blob = TextBlob(text)
        textblob_polarity = blob.sentiment.polarity
        textblob_subjectivity = blob.sentiment.subjectivity

        # Method 2: VADER (if available)
        vader_score = 0.0
        if NLTK_AVAILABLE:
            vader_scores = self.vader.polarity_scores(text)
            vader_score = (vader_scores['compound'] + 1) / 2  # Normalize to 0-1

        # Method 3: FinBERT (if available)
        finbert_score = 0.5
        finbert_confidence = 0.5
        if TRANSFORMERS_AVAILABLE and hasattr(self, 'finbert_pipeline') and self.finbert_pipeline:
            try:
                result = self.finbert_pipeline(text[:512])  # Limit length
                if result and len(result) > 0:
                    label = result[0]['label']
                    score = result[0]['score']
                    if label == 'POSITIVE':
                        finbert_score = (score + 1) / 2
                        finbert_confidence = score
                    elif label == 'NEGATIVE':
                        finbert_score = (1 - score)
                        finbert_confidence = score
                    else:  # NEUTRAL
                        finbert_score = 0.5
                        finbert_confidence = score * 0.5
            except Exception:
                pass

        # Ensemble sentiment calculation
        # Weight the methods based on their reliability
        weights = [0.3, 0.3, 0.4] if TRANSFORMERS_AVAILABLE else [0.5, 0.5, 0.0]
        scores = [textblob_polarity, vader_score * 2 - 1, finbert_score * 2 - 1]

        ensemble_score = sum(w * s for w, s in zip(weights, scores)) / sum(weights)
        confidence = min(0.9, 1.0 - textblob_subjectivity * 0.5)  # Adjust confidence based on subjectivity

        return np.clip(ensemble_score, -1, 1), np.clip(confidence, 0, 1)

class RedditSentimentAnalyzer:
    """Real-time Reddit sentiment analysis from financial subreddits"""

    def __init__(self):
        self.session = None
        self.logger = logging.getLogger(__name__)
        self.subreddits = [
            'wallstreetbets', 'investing', 'stocks', 'SecurityAnalysis',
            'ValueInvesting', 'pennystocks', 'StockMarket', 'options',
            'trading', 'forex', 'CryptoCurrency', 'Bitcoin'
        ]
        self.sentiment_cache = defaultdict(lambda: deque(maxlen=500))

    async def initialize(self):
        """Initialize Reddit API session"""
        self.session = aiohttp.ClientSession(
            timeout=aiohttp.ClientTimeout(total=30),
            headers={'User-Agent': 'QuantumTradingBot/1.0'}
        )

    async def search_reddit(self, symbol: str, count: int = 50) -> List[Dict]:
        """Search Reddit for symbol-related posts"""
        posts = []

        # Search multiple subreddits
        for subreddit in self.subreddits:
            subreddit_posts = await self._search_subreddit(symbol, subreddit, count // len(self.subreddits))
            posts.extend(subreddit_posts)

        return posts

    async def _search_subreddit(self, symbol: str, subreddit: str, count: int) -> List[Dict]:
        """Search specific subreddit for symbol mentions"""
        posts = []
        try:
            # Method 1: Try Reddit API (if auth is available)
            posts.extend(await self._search_reddit_api(symbol, subreddit, count))

            # Method 2: Fallback to web scraping
            posts.extend(await self._scrape_reddit_web(symbol, subreddit, count))

        except Exception as e:
            self.logger.error(f"Reddit search failed for r/{subreddit}: {e}")

        return posts

    async def _search_reddit_api(self, symbol: str, subreddit: str, count: int) -> List[Dict]:
        """Search using Reddit API (simplified without authentication)"""
        posts = []
        try:
            url = f"https://www.reddit.com/r/{subreddit}/search.json"
            params = {
                'q': symbol,
                'sort': 'new',
                't': 'day',
                'limit': min(count, 25),
                'type': 'link'
            }

            headers = {'User-Agent': 'QuantumTradingBot/1.0'}

            async with self.session.get(url, params=params, headers=headers) as response:
                if response.status == 200:
                    data = await response.json()
                    for post in data.get('data', {}).get('children', []):
                        post_data = post.get('data', {})
                        posts.append({
                            'title': post_data.get('title', ''),
                            'selftext': post_data.get('selftext', ''),
                            'score': post_data.get('score', 0),
                            'num_comments': post_data.get('num_comments', 0),
                            'created_utc': post_data.get('created_utc'),
                            'subreddit': subreddit,
                            'source': 'reddit_api'
                        })

        except Exception as e:
            self.logger.error(f"Reddit API search failed: {e}")

        return posts

    async def _scrape_reddit_web(self, symbol: str, subreddit: str, count: int) -> List[Dict]:
        """Fallback method: scrape Reddit web search"""
        posts = []
        try:
            search_url = f"https://www.reddit.com/r/{subreddit}/search?q={symbol}&sort=new&t=day"

            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8'
            }

            async with self.session.get(search_url, headers=headers) as response:
                if response.status == 200:
                    content = await response.text()
                    posts = self._parse_reddit_html(content, subreddit, symbol)

        except Exception as e:
            self.logger.error(f"Reddit web scraping failed: {e}")

        return posts

    def _parse_reddit_html(self, html: str, subreddit: str, symbol: str) -> List[Dict]:
        """Parse Reddit HTML for post data"""
        posts = []
        # Simplified HTML parsing - in production, use proper parsing libraries
        post_pattern = r'<div[^>]*data-testid="post-container"[^>]*>(.*?)</div>'

        matches = re.findall(post_pattern, html, re.DOTALL)[:20]

        for match in matches:
            title_match = re.search(r'<h3[^>]*>(.*?)</h3>', match)
            if title_match:
                title = re.sub(r'<[^>]+>', '', title_match.group(1)).strip()
                if len(title) > 10:
                    posts.append({
                        'title': title,
                        'selftext': '',
                        'score': 1,  # Default score
                        'num_comments': 0,
                        'created_utc': time.time(),
                        'subreddit': subreddit,
                        'source': 'reddit_web_scrape',
                        'symbol': symbol
                    })

        return posts

class NewsSentimentAnalyzer:
    """Real-time financial news sentiment analysis"""

    def __init__(self, api_config: Dict = None):
        self.api_config = api_config or {}
        self.session = None
        self.logger = logging.getLogger(__name__)
        self.news_sources = [
            'reuters', 'bloomberg', 'cnbc', 'marketwatch', 'seekingalpha',
            'wsj', 'ft', 'yahoo_finance', 'benzinga', 'the_motley_fool'
        ]

    async def initialize(self):
        """Initialize news API sessions"""
        self.session = aiohttp.ClientSession(
            timeout=aiohttp.ClientTimeout(total=30),
            headers={'User-Agent': 'QuantumTradingBot/1.0'}
        )

    async def fetch_news(self, symbol: str, hours_back: int = 24) -> List[Dict]:
        """Fetch news articles for symbol"""
        news = []

        # Try multiple news APIs
        if self.api_config.get('newsapi_key'):
            news.extend(await self._fetch_newsapi(symbol, hours_back))

        if self.api_config.get('benzinga_key'):
            news.extend(await self._fetch_benzinga(symbol, hours_back))

        # Fallback to free RSS feeds
        news.extend(await self._fetch_rss_feeds(symbol, hours_back))

        return news

    async def _fetch_newsapi(self, symbol: str, hours_back: int) -> List[Dict]:
        """Fetch from NewsAPI"""
        articles = []
        try:
            url = "https://newsapi.org/v2/everything"
            params = {
                'q': f'{symbol} OR "{symbol} stock" OR "{symbol} shares"',
                'domains': ','.join(['reuters.com', 'cnbc.com', 'marketwatch.com', 'seekingalpha.com']),
                'sortBy': 'publishedAt',
                'from': (datetime.now(timezone.utc) - timedelta(hours=hours_back)).isoformat(),
                'pageSize': 50,
                'apiKey': self.api_config['newsapi_key']
            }

            async with self.session.get(url, params=params) as response:
                if response.status == 200:
                    data = await response.json()
                    for article in data.get('articles', []):
                        articles.append({
                            'title': article.get('title', ''),
                            'description': article.get('description', ''),
                            'content': article.get('content', ''),
                            'source': article.get('source', {}).get('name', 'Unknown'),
                            'publishedAt': article.get('publishedAt'),
                            'url': article.get('url'),
                            'news_source': 'newsapi'
                        })

        except Exception as e:
            self.logger.error(f"NewsAPI fetch failed: {e}")

        return articles

    async def _fetch_benzinga(self, symbol: str, hours_back: int) -> List[Dict]:
        """Fetch from Benzinga API"""
        articles = []
        try:
            url = "https://api.benzinga.com/api/v2/news"
            params = {
                'symbols': symbol,
                'since': (datetime.now(timezone.utc) - timedelta(hours=hours_back)).strftime('%Y-%m-%d'),
                'apikey': self.api_config['benzinga_key'],
                'pagesize': 50
            }

            async with self.session.get(url, params=params) as response:
                if response.status == 200:
                    data = await response.json()
                    for article in data:
                        articles.append({
                            'title': article.get('title', ''),
                            'content': article.get('body', ''),
                            'source': 'Benzinga',
                            'publishedAt': article.get('created'),
                            'url': article.get('url'),
                            'news_source': 'benzinga'
                        })

        except Exception as e:
            self.logger.error(f"Benzinga API fetch failed: {e}")

        return articles

    async def _fetch_rss_feeds(self, symbol: str, hours_back: int) -> List[Dict]:
        """Fetch from free RSS feeds"""
        articles = []
        rss_feeds = [
            'https://feeds.reuters.com/reuters/topNews',
            'https://feeds.cnbc.com/CNBCBankingWealth',
            'https://www.marketwatch.com/feed/topstories'
        ]

        for feed_url in rss_feeds:
            try:
                async with self.session.get(feed_url) as response:
                    if response.status == 200:
                        content = await response.text()
                        articles.extend(self._parse_rss(content, symbol, feed_url))
            except Exception as e:
                self.logger.error(f"RSS feed fetch failed for {feed_url}: {e}")

        return articles

    def _parse_rss(self, rss_content: str, symbol: str, feed_url: str) -> List[Dict]:
        """Parse RSS content for symbol-related news"""
        articles = []
        # Simplified RSS parsing - in production, use feedparser
        item_pattern = r'<item>(.*?)</item>'
        items = re.findall(item_pattern, rss_content, re.DOTALL)

        for item in items[:10]:
            title_match = re.search(r'<title>(.*?)</title>', item)
            desc_match = re.search(r'<description>(.*?)</description>', item)

            if title_match:
                title = title_match.group(1)
                if symbol.upper() in title.upper():
                    articles.append({
                        'title': title,
                        'description': desc_match.group(1) if desc_match else '',
                        'content': '',
                        'source': feed_url.split('/')[2],
                        'publishedAt': datetime.now(timezone.utc).isoformat(),
                        'url': '',
                        'news_source': 'rss_feed'
                    })

        return articles

class SentimentFusionEngine:
    """Fuses sentiment data from multiple sources using quantum-inspired algorithms"""

    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.twitter_analyzer = TwitterSentimentAnalyzer()
        self.reddit_analyzer = RedditSentimentAnalyzer()
        self.news_analyzer = NewsSentimentAnalyzer()
        self.sentiment_history = defaultdict(lambda: deque(maxlen=1000))

        # Quantum-inspired weights for different sources
        self.source_weights = {
            'twitter': 0.25,
            'reddit': 0.20,
            'news': 0.30,
            'technical': 0.15,
            'options_flow': 0.10
        }

        # Time decay factors
        self.time_decay_factor = 0.95  # per hour

    async def initialize(self):
        """Initialize all sentiment analyzers"""
        await self.twitter_analyzer.initialize()
        await self.reddit_analyzer.initialize()
        await self.news_analyzer.initialize()
        self.logger.info("Sentiment Fusion Engine initialized")

    async def get_comprehensive_sentiment(self, symbol: str, time_window: int = 24) -> SentimentData:
        """Get comprehensive sentiment data for a symbol"""
        tasks = [
            self._get_twitter_sentiment(symbol),
            self._get_reddit_sentiment(symbol),
            self._get_news_sentiment(symbol),
            self._get_technical_sentiment(symbol)
        ]

        try:
            twitter_sentiment, reddit_sentiment, news_sentiment, technical_sentiment = await asyncio.gather(
                *tasks, return_exceptions=True
            )

            # Fusion algorithm with quantum-inspired weighting
            fused_sentiment = self._fuse_sentiments(
                symbol, twitter_sentiment, reddit_sentiment, news_sentiment, technical_sentiment
            )

            # Store in history
            self.sentiment_history[symbol].append(fused_sentiment)

            return fused_sentiment

        except Exception as e:
            self.logger.error(f"Comprehensive sentiment analysis failed for {symbol}: {e}")
            # Return neutral sentiment
            return self._create_neutral_sentiment(symbol)

    async def _get_twitter_sentiment(self, symbol: str) -> Dict:
        """Get Twitter sentiment"""
        try:
            tweets = await self.twitter_analyzer.search_twitter(symbol, count=100)

            if not tweets:
                return {'score': 0.0, 'confidence': 0.0, 'volume': 0, 'volatility': 0.0}

            sentiments = []
            for tweet in tweets:
                text = tweet.get('text', '')
                if text:
                    sentiment, confidence = self.twitter_analyzer.analyze_sentiment(text)
                    sentiments.append((sentiment, confidence))

            if sentiments:
                scores, confidences = zip(*sentiments)
                avg_score = np.mean(scores)
                avg_confidence = np.mean(confidences)
                volume = len(tweets)
                volatility = np.std(scores) if len(scores) > 1 else 0.0

                return {
                    'score': avg_score,
                    'confidence': avg_confidence,
                    'volume': volume,
                    'volatility': volatility
                }

        except Exception as e:
            self.logger.error(f"Twitter sentiment analysis failed: {e}")

        return {'score': 0.0, 'confidence': 0.0, 'volume': 0, 'volatility': 0.0}

    async def _get_reddit_sentiment(self, symbol: str) -> Dict:
        """Get Reddit sentiment"""
        try:
            posts = await self.reddit_analyzer.search_reddit(symbol, count=50)

            if not posts:
                return {'score': 0.0, 'confidence': 0.0, 'volume': 0, 'volatility': 0.0}

            sentiments = []
            for post in posts:
                text = f"{post.get('title', '')} {post.get('selftext', '')}"
                if text.strip():
                    sentiment, confidence = self.twitter_analyzer.analyze_sentiment(text)
                    # Weight by engagement (score + comments)
                    engagement = post.get('score', 0) + post.get('num_comments', 0)
                    sentiments.append((sentiment, confidence, max(1, engagement)))

            if sentiments:
                # Weight by engagement
                total_engagement = sum(s[2] for s in sentiments)
                weighted_score = sum(s[0] * s[2] for s in sentiments) / total_engagement
                weighted_confidence = sum(s[1] * s[2] for s in sentiments) / total_engagement
                volume = len(posts)
                volatility = np.std([s[0] for s in sentiments]) if len(sentiments) > 1 else 0.0

                return {
                    'score': weighted_score,
                    'confidence': weighted_confidence,
                    'volume': volume,
                    'volatility': volatility
                }

        except Exception as e:
            self.logger.error(f"Reddit sentiment analysis failed: {e}")

        return {'score': 0.0, 'confidence': 0.0, 'volume': 0, 'volatility': 0.0}

    async def _get_news_sentiment(self, symbol: str) -> Dict:
        """Get news sentiment"""
        try:
            articles = await self.news_analyzer.fetch_news(symbol, hours_back=24)

            if not articles:
                return {'score': 0.0, 'confidence': 0.0, 'volume': 0, 'volatility': 0.0}

            sentiments = []
            for article in articles:
                text = f"{article.get('title', '')} {article.get('description', '')} {article.get('content', '')}"
                if text.strip():
                    sentiment, confidence = self.twitter_analyzer.analyze_sentiment(text)
                    # News has inherently higher confidence
                    sentiments.append((sentiment, min(0.95, confidence * 1.2)))

            if sentiments:
                scores, confidences = zip(*sentiments)
                avg_score = np.mean(scores)
                avg_confidence = np.mean(confidences)
                volume = len(articles)
                volatility = np.std(scores) if len(scores) > 1 else 0.0

                return {
                    'score': avg_score,
                    'confidence': avg_confidence,
                    'volume': volume,
                    'volatility': volatility
                }

        except Exception as e:
            self.logger.error(f"News sentiment analysis failed: {e}")

        return {'score': 0.0, 'confidence': 0.0, 'volume': 0, 'volatility': 0.0}

    async def _get_technical_sentiment(self, symbol: str) -> Dict:
        """Get technical analysis-based sentiment"""
        try:
            # This would integrate with technical indicators
            # For now, return neutral
            return {'score': 0.0, 'confidence': 0.5, 'volume': 0, 'volatility': 0.0}

        except Exception as e:
            self.logger.error(f"Technical sentiment analysis failed: {e}")
            return {'score': 0.0, 'confidence': 0.0, 'volume': 0, 'volatility': 0.0}

    def _fuse_sentiments(self, symbol: str, *source_sentiments) -> SentimentData:
        """Fuse multiple sentiment sources using quantum-inspired weighting"""
        sources = ['twitter', 'reddit', 'news', 'technical']
        valid_sentiments = []

        for i, sentiment_data in enumerate(source_sentiments):
            if not isinstance(sentiment_data, Exception) and sentiment_data.get('volume', 0) > 0:
                valid_sentiments.append({
                    'source': sources[i],
                    'weight': self.source_weights[sources[i]],
                    'data': sentiment_data
                })

        if not valid_sentiments:
            return self._create_neutral_sentiment(symbol)

        # Quantum-inspired fusion algorithm
        total_weight = sum(s['weight'] for s in valid_sentiments)

        # Weighted average of sentiment scores
        weighted_score = sum(s['data']['score'] * s['weight'] for s in valid_sentiments) / total_weight

        # Combined confidence (geometric mean)
        combined_confidence = np.prod([s['data']['confidence'] ** (s['weight'] / total_weight) for s in valid_sentiments])

        # Total volume
        total_volume = sum(s['data']['volume'] for s in valid_sentiments)

        # Combined volatility (weighted by source importance)
        combined_volatility = sum(s['data']['volatility'] * s['weight'] for s in valid_sentiments) / total_weight

        # Extract keywords from all sources
        keywords = self._extract_keywords(symbol, valid_sentiments)

        # Create sentiment data
        sentiment_data = SentimentData(
            source="fusion_engine",
            symbol=symbol,
            timestamp=datetime.now(timezone.utc),
            sentiment_score=weighted_score,
            confidence=combined_confidence,
            volume=total_volume,
            text_sample=f"Fused sentiment from {len(valid_sentiments)} sources",
            keywords=keywords,
            volatility_indicator=combined_volatility,
            quantum_signature=""
        )

        sentiment_data.quantum_signature = sentiment_data.generate_quantum_signature()

        return sentiment_data

    def _extract_keywords(self, symbol: str, valid_sentiments: List[Dict]) -> List[str]:
        """Extract relevant keywords from sentiment sources"""
        keywords = set([symbol.upper(), symbol.lower()])

        # Add common trading keywords
        trading_keywords = [
            'bullish', 'bearish', 'buy', 'sell', 'hold', 'call', 'put',
            'earnings', 'dividend', 'merger', 'acquisition', 'ipo',
            'stock', 'share', 'market', 'trading', 'investing',
            'growth', 'value', 'technical', 'fundamental'
        ]

        keywords.update(trading_keywords[:10])  # Limit to 10 keywords

        return list(keywords)[:15]  # Return max 15 keywords

    def _create_neutral_sentiment(self, symbol: str) -> SentimentData:
        """Create neutral sentiment data"""
        sentiment_data = SentimentData(
            source="fusion_engine",
            symbol=symbol,
            timestamp=datetime.now(timezone.utc),
            sentiment_score=0.0,
            confidence=0.0,
            volume=0,
            text_sample="No sentiment data available",
            keywords=[symbol],
            volatility_indicator=0.0,
            quantum_signature=""
        )
        sentiment_data.quantum_signature = sentiment_data.generate_quantum_signature()
        return sentiment_data

    def get_sentiment_trend(self, symbol: str, hours_back: int = 24) -> Dict:
        """Analyze sentiment trend over time"""
        history = self.sentiment_history.get(symbol, deque(maxlen=1000))

        if not history:
            return {'trend': 'neutral', 'strength': 0.0, 'direction': 0.0}

        # Filter by time window
        cutoff_time = datetime.now(timezone.utc) - timedelta(hours=hours_back)
        recent_sentiments = [s for s in history if s.timestamp >= cutoff_time]

        if len(recent_sentiments) < 2:
            return {'trend': 'neutral', 'strength': 0.0, 'direction': 0.0}

        # Calculate trend
        scores = [s.sentiment_score for s in recent_sentiments]
        times = [(s.timestamp - recent_sentiments[0].timestamp).total_seconds() / 3600 for s in recent_sentiments]

        # Linear regression for trend
        if len(times) > 1:
            coeffs = np.polyfit(times, scores, 1)
            slope = coeffs[0]

            # Determine trend
            if abs(slope) < 0.01:
                trend = 'neutral'
            elif slope > 0:
                trend = 'bullish'
            else:
                trend = 'bearish'

            strength = abs(slope)
            direction = np.sign(slope)

            return {
                'trend': trend,
                'strength': strength,
                'direction': direction,
                'sample_size': len(recent_sentiments),
                'avg_sentiment': np.mean(scores),
                'sentiment_volatility': np.std(scores)
            }

        return {'trend': 'neutral', 'strength': 0.0, 'direction': 0.0}

# Export for use in quantum context composer
class SentimentDataSource:
    """Main interface for sentiment data in quantum context composer"""

    def __init__(self):
        self.fusion_engine = SentimentFusionEngine()
        self.initialized = False

    async def initialize(self):
        """Initialize sentiment data source"""
        if not self.initialized:
            await self.fusion_engine.initialize()
            self.initialized = True
            logging.info("Sentiment data source initialized")

    async def get_sentiment_data(self, symbol: str) -> Dict:
        """Get sentiment data for symbol"""
        sentiment_data = await self.fusion_engine.get_comprehensive_sentiment(symbol)
        return {
            'sentiment_score': sentiment_data.sentiment_score,
            'sentiment_confidence': sentiment_data.confidence,
            'sentiment_volume': sentiment_data.volume,
            'sentiment_volatility': sentiment_data.volatility_indicator,
            'sentiment_trend': self.fusion_engine.get_sentiment_trend(symbol),
            'quantum_signature': sentiment_data.quantum_signature
        }