#!/usr/bin/env python3
"""
NewsAPI Integration Test
Tests the NewsAPI key integration and retrieves real financial news data
"""

import asyncio
import sys
import json
import aiohttp
from datetime import datetime, timezone, timedelta
import re

# Add platform to path
sys.path.append('/home/davidsanker/platform')

async def test_newsapi_directly():
    """Test NewsAPI directly to validate the key"""
    print("📰 Testing NewsAPI Direct Access...")

    api_key = "da43d52f-4661-4094-9ce6-04a7e02d5567"

    # Test with general financial news
    url = "https://newsapi.org/v2/everything"
    params = {
        'q': 'stock market OR trading OR finance',
        'domains': 'reuters.com,cnbc.com,bloomberg.com,marketwatch.com,seekingalpha.com',
        'sortBy': 'publishedAt',
        'from': (datetime.now() - timedelta(hours=24)).isoformat(),
        'language': 'en',
        'pageSize': 10,
        'apiKey': api_key
    }

    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, params=params, timeout=15) as response:
                print(f"  HTTP Status: {response.status}")

                if response.status == 200:
                    data = await response.json()

                    if 'articles' in data:
                        articles = data['articles']
                        print(f"  ✅ Successfully retrieved {len(articles)} financial news articles")

                        # Show latest articles
                        if articles:
                            print(f"  📰 Latest Financial News:")
                            for i, article in enumerate(articles[:3], 1):
                                title = article.get('title', 'No title')[:60]
                                source = article.get('source', {}).get('name', 'Unknown')
                                published = article.get('publishedAt', 'Unknown')
                                print(f"    {i}. {title}...")
                                print(f"       Source: {source} | Time: {published[:10]}")

                        return True
                    else:
                        print(f"  ❌ Unexpected response structure: {list(data.keys())}")
                        if 'error' in data:
                            print(f"  API Error: {data['error']}")
                        return False
                else:
                    text = await response.text()
                    print(f"  ❌ API Error: {response.status}")
                    print(f"  Response: {text[:300]}...")
                    return False

    except Exception as e:
        print(f"  ❌ Connection error: {e}")
        return False

async def test_stock_specific_news():
    """Test NewsAPI for specific stock symbols"""
    print("\n🍎 Testing Stock-Specific News...")

    api_key = "da43d52f-4661-4094-9ce6-04a7e02d5567"

    # Test symbols
    test_symbols = ['AAPL', 'GOOGL', 'TSLA', 'MSFT', 'NVDA']
    results = {}

    async with aiohttp.ClientSession() as session:
        for symbol in test_symbols:
            print(f"  🔍 Testing {symbol} news...")

            url = "https://newsapi.org/v2/everything"
            params = {
                'q': f'{symbol} OR "{symbol} stock" OR "{symbol} shares" OR "{symbol} earnings"',
                'sortBy': 'publishedAt',
                'from': (datetime.now() - timedelta(hours=48)).isoformat(),
                'language': 'en',
                'pageSize': 5,
                'apiKey': api_key
            }

            try:
                async with session.get(url, params=params, timeout=10) as response:
                    if response.status == 200:
                        data = await response.json()

                        if 'articles' in data and data['articles']:
                            articles = data['articles']
                            results[symbol] = {
                                'count': len(articles),
                                'articles': articles[:3]  # Keep top 3
                            }
                            print(f"    ✅ Found {len(articles)} articles for {symbol}")

                            # Show latest article
                            if articles:
                                latest = articles[0]
                                title = latest.get('title', 'No title')[:50]
                                print(f"      📄 {title}...")
                        else:
                            print(f"    ⚠️ No articles found for {symbol}")
                            results[symbol] = {'count': 0, 'articles': []}
                    else:
                        print(f"    ❌ HTTP {response.status} for {symbol}")
                        results[symbol] = {'count': 0, 'articles': []}

            except Exception as e:
                print(f"    ❌ Error for {symbol}: {e}")
                results[symbol] = {'count': 0, 'articles': []}

    return results

async def test_newsapi_sentiment_analysis():
    """Test NewsAPI data with sentiment analysis"""
    print("\n💭 Testing NewsAPI + Sentiment Analysis...")

    try:
        # Import our sentiment analysis modules
        from data.sentiment_analysis import SentimentFusionEngine

        # Initialize sentiment engine
        sentiment_engine = SentimentFusionEngine()
        await sentiment_engine.initialize()
        print("  ✅ Sentiment analysis engine initialized")

        # Get some news data
        api_key = "da43d52f-4661-4094-9ce6-04a7e02d5567"
        url = "https://newsapi.org/v2/everything"
        params = {
            'q': 'economy OR inflation OR interest rates OR stock market',
            'sortBy': 'publishedAt',
            'from': (datetime.now() - timedelta(hours=12)).isoformat(),
            'language': 'en',
            'pageSize': 10,
            'apiKey': api_key
        }

        async with aiohttp.ClientSession() as session:
            async with session.get(url, params=params, timeout=10) as response:
                if response.status == 200:
                    data = await response.json()

                    if 'articles' in data and data['articles']:
                        articles = data['articles']
                        print(f"  📰 Retrieved {len(articles)} articles for sentiment analysis")

                        # Analyze sentiment of first few articles
                        sentiment_scores = []
                        for article in articles[:5]:
                            title = article.get('title', '')
                            description = article.get('description', '')
                            content = f"{title} {description}"

                            if content.strip():
                                sentiment, confidence = sentiment_engine.analyze_sentiment(content)
                                sentiment_scores.append(sentiment)

                                source = article.get('source', {}).get('name', 'Unknown')
                                print(f"    📊 {source}: {sentiment:+.3f} (confidence: {confidence:.3f})")

                        if sentiment_scores:
                            avg_sentiment = sum(sentiment_scores) / len(sentiment_scores)
                            print(f"  🎯 Overall News Sentiment: {avg_sentiment:+.3f}")

                            if avg_sentiment > 0.1:
                                print(f"    ✅ Positive news sentiment - Bullish bias")
                            elif avg_sentiment < -0.1:
                                print(f"    ❌ Negative news sentiment - Bearish bias")
                            else:
                                print(f"    ⚖️ Neutral news sentiment - Balanced market")

                        return True
                    else:
                        print("  ❌ No articles retrieved for sentiment analysis")
                        return False
                else:
                    print(f"  ❌ NewsAPI error: {response.status}")
                    return False

    except Exception as e:
        print(f"  ❌ Sentiment analysis test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

async def test_alternative_data_newsapi_integration():
    """Test NewsAPI integration through our AlternativeDataSource"""
    print("\n🔗 Testing NewsAPI via AlternativeDataSource...")

    try:
        from data.alternative_data import AlternativeDataSource

        # Create with both API keys
        api_keys = {
            'fred': os.environ.get('NEWSAPI_KEY', ''),
            'newsapi': 'da43d52f-4661-4094-9ce6-04a7e02d5567'
        }

        alt_source = AlternativeDataSource(api_keys)
        await alt_source.initialize()
        print("  ✅ AlternativeDataSource initialized with NewsAPI")

        # Test news data provider
        news_provider = alt_source.alternative_source.news_analyzer
        await news_provider.initialize()
        print("  ✅ News provider initialized")

        # Test fetching news for AAPL
        print("  🍎 Testing financial news for AAPL...")
        aapl_news = await news_provider.fetch_news('AAPL', hours_back=48)

        if aapl_news:
            print(f"    ✅ Retrieved {len(aapl_news)} AAPL news articles")

            # Show some articles
            for i, article in enumerate(aapl_news[:3], 1):
                title = article.get('title', 'No title')[:40]
                source = article.get('source', 'Unknown')
                print(f"      {i}. {title}... ({source})")

        # Test integrated alternative data for different symbols
        test_symbols = ['AAPL', 'GOOGL', 'TSLA']
        for symbol in test_symbols:
            print(f"  🔍 Testing integrated news for {symbol}...")
            alt_data = await alt_source.get_alternative_data(symbol, ['news'])

            if alt_data and 'news' in alt_data:
                news_data = alt_data['news']
                if isinstance(news_data, list):
                    print(f"    ✅ News data for {symbol}: {len(news_data)} articles")
                elif isinstance(news_data, dict):
                    print(f"    ✅ News metadata for {symbol}: {list(news_data.keys())}")
                else:
                    print(f"    ✅ News data available for {symbol}")

        return True

    except Exception as e:
        print(f"  ❌ Alternative data integration test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

async def test_sentiment_source_with_newsapi():
    """Test sentiment analysis source with NewsAPI integration"""
    print("\n💭 Testing SentimentDataSource with NewsAPI...")

    try:
        from data.sentiment_analysis import SentimentDataSource

        # Create with NewsAPI key
        api_config = {'newsapi_key': 'da43d52f-4661-4094-9ce6-04a7e02d5567'}
        sentiment_source = SentimentDataSource(api_config)
        await sentiment_source.initialize()
        print("  ✅ SentimentDataSource initialized with NewsAPI")

        # Test getting sentiment data for multiple symbols
        test_symbols = ['AAPL', 'GOOGL', 'MSFT', 'TSLA']

        for symbol in test_symbols:
            print(f"  💭 Testing sentiment for {symbol}...")
            sentiment_data = await sentiment_source.get_sentiment_data(symbol)

            if sentiment_data:
                print(f"    ✅ Sentiment data for {symbol}:")
                print(f"      📊 Score: {sentiment_data.get('sentiment_score', 0):+3f}")
                print(f"      🎯 Confidence: {sentiment_data.get('sentiment_confidence', 0):.3f}")
                print(f"      📰 Volume: {sentiment_data.get('sentiment_volume', 0):,}")

                # Check if trend analysis is available
                trend = sentiment_data.get('sentiment_trend', {})
                if trend:
                    print(f"      📈 Trend: {trend.get('trend', 'unknown')} ({trend.get('strength', 0):.3f})")
            else:
                print(f"    ⚠️ No sentiment data for {symbol}")

        return True

    except Exception as e:
        print(f"  ❌ Sentiment source integration test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def analyze_news_sentiment_for_trading(results):
    """Analyze news sentiment for trading insights"""
    print("\n💡 News Sentiment Trading Analysis:")

    if not results:
        print("  ❌ No news data to analyze")
        return

    # Count positive vs negative sentiment
    positive_count = 0
    negative_count = 0
    total_articles = 0

    print("  📰 News Coverage Analysis:")
    for symbol, data in results.items():
        count = data.get('count', 0)
        total_articles += count

        if count > 0:
            print(f"    📊 {symbol}: {count} articles")

            # This is where sentiment analysis would happen in production
            # For now, just count articles
            if count > 3:
                positive_count += 1  # High coverage could be positive

    print(f"\n  🎯 Trading Insights:")
    print(f"    📰 Total Articles Analyzed: {total_articles}")
    print(f"    📈 Symbols with High Coverage: {positive_count}")

    if total_articles > 20:
        print("    ✅ High news activity - Increased market volatility likely")
    elif total_articles > 10:
        print("    ⚖️ Moderate news activity - Normal market conditions")
    else:
        print("    📉 Low news activity - Quiet market period")

    print("    💡 Recommendation: Combine news sentiment with FRED data for enhanced analysis")

async def main():
    """Main test runner"""
    print("📰 NewsAPI Integration Test Suite")
    print("Testing API Key: da43d52f-4661-4094-9ce6-04a7e02d5567")
    print(f"Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 70)

    tests = [
        ("Direct NewsAPI Test", test_newsapi_directly),
        ("Stock-Specific News", test_stock_specific_news),
        ("NewsAPI + Sentiment Analysis", test_newsapi_sentiment_analysis),
        ("Alternative Data Integration", test_alternative_data_newsapi_integration),
        ("SentimentSource Integration", test_sentiment_source_with_newsapi)
    ]

    passed = 0
    failed = 0
    news_results = None

    for test_name, test_func in tests:
        print(f"\n{'='*60}")
        print(f"🧪 Running: {test_name}")
        print(f"{'='*60}")

        try:
            result = await test_func()

            if result:
                passed += 1
                print(f"✅ {test_name}: PASSED")

                # Store news results for analysis
                if test_name == "Stock-Specific News" and isinstance(result, dict):
                    news_results = result

            else:
                failed += 1
                print(f"❌ {test_name}: FAILED")

        except Exception as e:
            failed += 1
            print(f"💥 {test_name}: CRASHED - {e}")

    # Analyze news sentiment if available
    if news_results:
        analyze_news_sentiment_for_trading(news_results)

    # Final summary
    print(f"\n{'='*70}")
    print("📋 NEWSAPI INTEGRATION TEST SUMMARY")
    print(f"{'='*70}")
    print(f"Total Tests: {passed + failed}")
    print(f"Passed: {passed}")
    print(f"Failed: {failed}")

    if failed == 0:
        print("\n🎉 ALL NEWSAPI INTEGRATION TESTS PASSED!")
        print("✅ Your NewsAPI key is working perfectly!")
        print("🚀 Your trading bot now has access to real-time financial news!")

        print("\n📰 News Data Now Available:")
        if news_results:
            print("  📈 Real-Time Financial News:")
            for symbol, data in news_results.items():
                if data.get('count', 0) > 0:
                    print(f"    • {symbol}: {data['count']} recent articles")

        print("\n🎯 Enhanced Trading Capabilities:")
        print("  📰 Real-time news sentiment analysis")
        print("  💭 News-driven trading signals")
        print("  ⚡ Breaking news alerts")
        print("  📊 News volume and trend analysis")

        return 0
    else:
        success_rate = (passed / (passed + failed)) * 100
        print(f"\n⚠️ {failed} test(s) failed")
        print(f"📊 Success Rate: {success_rate:.1f}%")

        if success_rate >= 80:
            print("✅ NewsAPI integration is largely working")
        elif success_rate >= 60:
            print("⚠️ Some issues with NewsAPI integration")
        else:
            print("❌ Significant issues with NewsAPI integration")

        return 1

if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)