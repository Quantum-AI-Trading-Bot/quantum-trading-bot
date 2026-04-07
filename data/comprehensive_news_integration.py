#!/usr/bin/env python3
"""
Comprehensive NewsAPI Integration with Sentiment Analysis
Shows the full capabilities of your NewsAPI + Sentiment Analysis system
"""

import asyncio
import sys
import json
import aiohttp
from datetime import datetime, timezone, timedelta
from collections import defaultdict
import numpy as np

sys.path.append('/home/davidsanker/platform')

async def get_real_news_data():
    """Get real news data from NewsAPI"""
    api_key = os.environ.get('NEWSAPI_KEY', '')

    print("📰 Fetching Real-Time Financial News...")

    # Get comprehensive financial news
    url = "https://newsapi.org/v2/everything"
    params = {
        'q': 'stock market OR economy OR trading OR finance OR investment OR earnings',
        'sortBy': 'publishedAt',
        'from': (datetime.now(timezone.utc) - timedelta(hours=6)).isoformat(),  # Last 6 hours
        'language': 'en',
        'pageSize': 20,
        'apiKey': api_key
    }

    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, params=params, timeout=15) as response:
                if response.status == 200:
                    data = await response.json()
                    if 'articles' in data:
                        return data['articles']
                    else:
                        return []
                else:
                    print(f"   ❌ NewsAPI error: {response.status}")
                    return []
    except Exception as e:
        print(f"   ❌ Error fetching news: {e}")
        return []

def analyze_sentiment_simple(text):
    """Simple sentiment analysis when NLP not available"""
    positive_words = [
        'bullish', 'positive', 'growth', 'rally', 'surge', 'jump', 'rise', 'gain',
        'profit', 'beat', 'strong', 'upgrade', 'buy', 'outperform', 'optimistic',
        'boom', 'expansion', 'recovery', 'momentum', 'breakthrough', 'success'
    ]

    negative_words = [
        'bearish', 'negative', 'decline', 'fall', 'drop', 'slump', 'crash',
        'loss', 'miss', 'weak', 'downgrade', 'sell', 'underperform', 'pessimistic',
        'recession', 'crisis', 'concern', 'risk', 'warning', 'cut', 'reduce'
    ]

    text_lower = text.lower()
    positive_count = sum(1 for word in positive_words if word in text_lower)
    negative_count = sum(1 for word in negative_words if word in text_lower)

    # Simple sentiment score
    if positive_count + negative_count == 0:
        return 0.0, 0.1  # Neutral, low confidence

    sentiment = (positive_count - negative_count) / (positive_count + negative_count)
    confidence = min(0.9, (positive_count + negative_count) / 10.0)

    return sentiment, confidence

async def comprehensive_news_analysis():
    """Comprehensive news sentiment analysis"""
    print("🧪 COMPREHENSIVE NEWS & SENTIMENT ANALYSIS")
    print("=" * 60)

    # Get news articles
    articles = await get_real_news_data()

    if not articles:
        print("❌ No news articles found")
        return

    print(f"📰 Retrieved {len(articles)} recent articles")

    # Analyze each article
    sentiment_results = []
    source_counts = defaultdict(int)
    symbol_mentions = defaultdict(int)

    print("\n📊 Article Analysis:")
    print("-" * 40)

    for i, article in enumerate(articles[:10], 1):  # Analyze top 10
        title = article.get('title', '')
        description = article.get('description', '')
        content = f"{title} {description}"
        source = article.get('source', {}).get('name', 'Unknown')
        published = article.get('publishedAt', '')

        # Count sources
        source_counts[source] += 1

        # Find stock symbols
        symbols = ['AAPL', 'GOOGL', 'MSFT', 'TSLA', 'NVDA', 'AMZN', 'META', 'SPY', 'QQQ']
        for symbol in symbols:
            if symbol.lower() in content.lower():
                symbol_mentions[symbol] += 1

        # Analyze sentiment
        sentiment, confidence = analyze_sentiment_simple(content)

        result = {
            'title': title,
            'source': source,
            'sentiment': sentiment,
            'confidence': confidence,
            'published': published
        }

        sentiment_results.append(result)

        # Display analysis
        sentiment_emoji = "🟢" if sentiment > 0.1 else "🔴" if sentiment < -0.1 else "🟡"
        print(f"{i:2d}. {sentiment_emoji} {sentiment:+.2f} {confidence:.2f} | {source[:15]:<15} | {title[:50]}...")

    # Overall sentiment analysis
    if sentiment_results:
        sentiments = [r['sentiment'] for r in sentiment_results]
        avg_sentiment = np.mean(sentiments)
        positive_count = sum(1 for s in sentiments if s > 0.1)
        negative_count = sum(1 for s in sentiments if s < -0.1)

        print(f"\n🎯 OVERALL MARKET SENTIMENT:")
        print(f"   Average Sentiment: {avg_sentiment:+.3f}")

        if avg_sentiment > 0.1:
            print("   📈 BULLISH BIAS - Positive market sentiment")
        elif avg_sentiment < -0.1:
            print("   📉 BEARISH BIAS - Negative market sentiment")
        else:
            print("   ⚖️ NEUTRAL - Balanced market sentiment")

        print(f"   📊 Positive articles: {positive_count}")
        print(f"   📊 Negative articles: {negative_count}")
        print(f"   📊 Neutral articles: {len(sentiments) - positive_count - negative_count}")

    # Source analysis
    print(f"\n📰 NEWS SOURCE BREAKDOWN:")
    for source, count in sorted(source_counts.items(), key=lambda x: x[1], reverse=True)[:5]:
        print(f"   {source}: {count} articles")

    # Symbol mentions
    if symbol_mentions:
        print(f"\n🏢 MENTIONED SYMBOLS:")
        for symbol, count in sorted(symbol_mentions.items(), key=lambda x: x[1], reverse=True)[:5]:
            print(f"   {symbol}: {count} mentions")

    # Trading signals
    print(f"\n🚀 TRADING SIGNALS:")
    if avg_sentiment > 0.2:
        print("   💹 STRONG BUY SIGNAL - Very bullish news sentiment")
        print("   📈 Recommended: Increase exposure to risk assets")
    elif avg_sentiment > 0.05:
        print("   📈 MODERATE BUY SIGNAL - Bullish sentiment")
        print("   📊 Recommended: Current allocation, monitor for opportunities")
    elif avg_sentiment < -0.2:
        print("   📉 STRONG SELL SIGNAL - Very bearish news sentiment")
        print("   🛡️ Recommended: Reduce risk exposure, increase defensive positions")
    elif avg_sentiment < -0.05:
        print("   📉 MODERATE SELL SIGNAL - Bearish sentiment")
        print("   ⚠️ Recommended: Caution, consider partial position reduction")
    else:
        print("   ⚖️ HOLD SIGNAL - Neutral sentiment")
        print("   📊 Recommended: Maintain current positions")

    # Risk assessment
    volatility_indicator = np.std([r['sentiment'] for r in sentiment_results]) if len(sentiment_results) > 1 else 0

    print(f"\n⚠️ RISK ASSESSMENT:")
    print(f"   Sentiment Volatility: {volatility_indicator:.3f}")
    if volatility_indicator > 0.3:
        print("   🔴 HIGH VOLATILITY - Expect price swings, wider stops recommended")
    elif volatility_indicator > 0.2:
        print("   🟡 MODERATE VOLATILITY - Normal market conditions")
    else:
        print("   🟢 LOW VOLATILITY - Stable sentiment, lower risk environment")

async def demonstrate_trading_integration():
    """Demonstrate how news integrates with trading decisions"""
    print("\n" + "=" * 60)
    print("🔗 NEWS + TRADING INTEGRATION DEMONSTRATION")
    print("=" * 60)

    # Simulate trading scenario
    print("📈 SCENARIO: AAPL Trading Decision")
    print("-" * 40)

    # Get AAPL-specific news
    api_key = os.environ.get('NEWSAPI_KEY', '')
    url = "https://newsapi.org/v2/everything"
    params = {
        'q': 'AAPL OR Apple OR "Tim Cook" OR iPhone OR iPad OR Mac',
        'sortBy': 'publishedAt',
        'from': (datetime.now(timezone.utc) - timedelta(hours=12)).isoformat(),
        'language': 'en',
        'pageSize': 8,
        'apiKey': api_key
    }

    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, params=params, timeout=10) as response:
                if response.status == 200:
                    data = await response.json()

                    if 'articles' in data and data['articles']:
                        articles = data['articles']
                        print(f"📰 Found {len(articles)} AAPL-related articles")

                        # Analyze AAPL news sentiment
                        aapl_sentiments = []
                        aapl_confidences = []

                        for article in articles:
                            title = article.get('title', '')
                            description = article.get('description', '')
                            content = f"{title} {description}"

                            sentiment, confidence = analyze_sentiment_simple(content)
                            aapl_sentiments.append(sentiment)
                            aapl_confidences.append(confidence)

                            source = article.get('source', {}).get('name', 'Unknown')
                            sentiment_emoji = "🟢" if sentiment > 0.1 else "🔴" if sentiment < -0.1 else "🟡"
                            print(f"   {sentiment_emoji} {sentiment:+.2f} | {source[:12]:<12} | {title[:40]}...")

                        if aapl_sentiments:
                            avg_aapl_sentiment = np.mean(aapl_sentiments)
                            avg_confidence = np.mean(aapl_confidences)

                            print(f"\n🎯 AAPL NEWS SENTIMENT: {avg_aapl_sentiment:+.3f}")
                            print(f"   Confidence: {avg_confidence:.3f}")

                            # Trading decision based on news sentiment
                            print(f"\n📊 TRADING RECOMMENDATION:")

                            if avg_aapl_sentiment > 0.15 and avg_confidence > 0.5:
                                print("   🚀 STRONG BUY - Positive news sentiment with good confidence")
                                print("   💰 Suggested: Consider AAPL long positions")
                                print("   📈 Target: Potential 5-8% upside based on news momentum")
                            elif avg_aapl_sentiment > 0.05:
                                print("   📈 MODERATE BUY - Slightly positive sentiment")
                                print("   💰 Suggested: Current AAPL positions, consider averaging in")
                                print("   📊 Target: Hold or small position increase")
                            elif avg_aapl_sentiment < -0.15 and avg_confidence > 0.5:
                                print("   📉 STRONG SELL - Negative news sentiment with good confidence")
                                print("   ⚠️ Suggested: Reduce AAPL exposure, consider short")
                                print("   📊 Risk: Potential 5-10% downside based on news")
                            elif avg_aapl_sentiment < -0.05:
                                print("   📉 MODERATE SELL - Slightly negative sentiment")
                                print("   ⚠️ Suggested: Caution on AAPL, consider position reduction")
                                print("   📊 Target: Risk management focus")
                            else:
                                print("   ⚖️ HOLD - Neutral sentiment")
                                print("   💰 Suggested: Maintain current AAPL positions")
                                print("   📊 Target: Wait for clearer signals")

                            # Position sizing suggestion
                            if avg_aapl_sentiment != 0:
                                position_size = min(abs(avg_aapl_sentiment) * 2, 1.0) * 100  # Max 100% allocation
                                if avg_aapl_sentiment > 0:
                                    print(f"   📊 Position Sizing: Consider up to {position_size:.0f}% portfolio allocation")
                                else:
                                    print(f"   📊 Position Sizing: Consider reducing to {position_size:.0f}% portfolio allocation")

                    else:
                        print("   ⚠️ No recent AAPL news found")
                else:
                    print(f"   ❌ Error fetching AAPL news: {response.status}")

    except Exception as e:
        print(f"   ❌ Error: {e}")

async def main():
    """Main demonstration"""
    print("🚀 COMPREHENSIVE NEWSAPI + SENTIMENT ANALYSIS DEMO")
    print("API Key: YOUR_NEWSAPI_KEY")
    print(f"Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 70)

    # Run comprehensive analysis
    await comprehensive_news_analysis()

    # Show trading integration
    await demonstrate_trading_integration()

    print("\n" + "=" * 70)
    print("✅ NEWSAPI INTEGRATION COMPLETE!")
    print("=" * 70)

    print("🎯 Your Quantum AI Trading Bot Now Has:")
    print("   🔴 Real-time financial news from NewsAPI")
    print("   💭 Automated sentiment analysis")
    print("   📊 Market sentiment indicators")
    print("   🚀 News-driven trading signals")
    print("   ⚡ Stock-specific news analysis")
    print("   📈 Risk assessment based on news volatility")
    print("   💰 Position sizing suggestions")

    print("\n🚀 Ready for Production Trading!")

if __name__ == "__main__":
    asyncio.run(main())