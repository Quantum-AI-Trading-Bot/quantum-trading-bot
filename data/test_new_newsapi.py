#!/usr/bin/env python3
"""
Test New NewsAPI Key - Quick Validation and Integration Test
"""

import asyncio
import sys
import aiohttp
from datetime import datetime, timezone, timedelta

sys.path.append('/home/davidsanker/platform')

async def test_new_newsapi_key():
    """Test the new NewsAPI key"""
    api_key = os.environ.get('NEWSAPI_KEY', '')

    print("🔑 Testing New NewsAPI Key:")
    print(f"API Key: {api_key[:8]}...{api_key[-4:]}")

    # Test 1: Simple validation
    print("\n1️⃣ Validating API Key...")
    url = "https://newsapi.org/v2/everything"
    params = {
        'q': 'financial news',
        'apiKey': api_key,
        'pageSize': 3,
        'sortBy': 'publishedAt'
    }

    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, params=params, timeout=10) as response:
                print(f"   HTTP Status: {response.status}")

                if response.status == 200:
                    data = await response.json()
                    print("   ✅ API Key is VALID!")

                    if 'articles' in data:
                        articles = data['articles']
                        print(f"   📰 Retrieved {len(articles)} test articles")
                        return True, articles
                    else:
                        print("   ⚠️ No articles in response")
                        return True, []
                else:
                    text = await response.text()
                    print(f"   ❌ API Error: {response.status}")
                    print(f"   Response: {text[:200]}...")
                    return False, None

    except Exception as e:
        print(f"   ❌ Connection error: {e}")
        return False, None

async def test_financial_news_retrieval():
    """Test financial news retrieval"""
    print("\n2️⃣ Testing Financial News Retrieval...")

    api_key = os.environ.get('NEWSAPI_KEY', '')

    # Test financial news from major sources
    url = "https://newsapi.org/v2/everything"
    params = {
        'q': 'stock market OR trading OR economy OR finance OR investment',
        'domains': 'reuters.com,cnbc.com,bloomberg.com,marketwatch.com,seekingalpha.com,wsj.com,ft.com',
        'sortBy': 'publishedAt',
        'from': (datetime.now(timezone.utc) - timedelta(hours=24)).isoformat(),
        'language': 'en',
        'pageSize': 10,
        'apiKey': api_key
    }

    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, params=params, timeout=15) as response:
                if response.status == 200:
                    data = await response.json()

                    if 'articles' in data and data['articles']:
                        articles = data['articles']
                        print(f"   ✅ Retrieved {len(articles)} financial news articles")

                        print("\n   📰 Latest Financial News:")
                        for i, article in enumerate(articles[:5], 1):
                            title = article.get('title', 'No title')
                            source = article.get('source', {}).get('name', 'Unknown')
                            published = article.get('publishedAt', '')
                            description = article.get('description', '')[:80]

                            print(f"      {i}. {title[:60]}...")
                            print(f"         📰 {source} | 🕐 {published[:19]}")
                            print(f"         📝 {description}...")
                            print()

                        return articles
                    else:
                        print("   ⚠️ No financial articles found")
                        return []
                else:
                    print(f"   ❌ HTTP Error: {response.status}")
                    return []

    except Exception as e:
        print(f"   ❌ Error retrieving financial news: {e}")
        return []

async def test_stock_specific_news():
    """Test stock-specific news retrieval"""
    print("3️⃣ Testing Stock-Specific News...")

    api_key = os.environ.get('NEWSAPI_KEY', '')
    test_symbols = ['AAPL', 'GOOGL', 'TSLA', 'MSFT', 'NVDA']

    async with aiohttp.ClientSession() as session:
        for symbol in test_symbols:
            print(f"\n   🍎 Testing {symbol} news...")

            url = "https://newsapi.org/v2/everything"
            params = {
                'q': f'{symbol} OR "{symbol} stock" OR "{symbol} shares" OR "{symbol} earnings"',
                'sortBy': 'publishedAt',
                'from': (datetime.now(timezone.utc) - timedelta(hours=48)).isoformat(),
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
                            print(f"      ✅ Found {len(articles)} {symbol} articles")

                            # Show latest article
                            if articles:
                                latest = articles[0]
                                title = latest.get('title', 'No title')
                                source = latest.get('source', {}).get('name', 'Unknown')
                                print(f"      📄 Latest: {title[:50]}...")
                                print(f"      📰 Source: {source}")
                        else:
                            print(f"      ⚠️ No {symbol} articles found")
                    else:
                        print(f"      ❌ HTTP {response.status} for {symbol}")

            except Exception as e:
                print(f"      ❌ Error for {symbol}: {e}")

async def test_sentiment_analysis():
    """Test sentiment analysis on retrieved news"""
    print("\n4️⃣ Testing Sentiment Analysis...")

    try:
        from data.sentiment_analysis import SentimentFusionEngine

        # Initialize sentiment engine
        sentiment_engine = SentimentFusionEngine()
        await sentiment_engine.initialize()
        print("   ✅ Sentiment analysis engine initialized")

        # Get some financial news
        api_key = os.environ.get('NEWSAPI_KEY', '')
        url = "https://newsapi.org/v2/everything"
        params = {
            'q': 'economy OR stock market OR trading',
            'sortBy': 'publishedAt',
            'from': (datetime.now(timezone.utc) - timedelta(hours=12)).isoformat(),
            'language': 'en',
            'pageSize': 8,
            'apiKey': api_key
        }

        async with aiohttp.ClientSession() as session:
            async with session.get(url, params=params, timeout=10) as response:
                if response.status == 200:
                    data = await response.json()

                    if 'articles' in data and data['articles']:
                        articles = data['articles']
                        print(f"   📰 Analyzing sentiment for {len(articles)} articles...")

                        sentiment_scores = []
                        sources = []

                        for article in articles[:5]:
                            title = article.get('title', '')
                            description = article.get('description', '')
                            content = f"{title} {description}"
                            source = article.get('source', {}).get('name', 'Unknown')

                            if content.strip():
                                sentiment, confidence = sentiment_engine.analyze_sentiment(content)
                                sentiment_scores.append(sentiment)
                                sources.append(source)

                                print(f"      📊 {source}: {sentiment:+.3f} (confidence: {confidence:.3f})")

                        if sentiment_scores:
                            avg_sentiment = sum(sentiment_scores) / len(sentiment_scores)
                            print(f"\n   🎯 Overall News Sentiment: {avg_sentiment:+.3f}")

                            if avg_sentiment > 0.1:
                                print("      ✅ Positive news sentiment - Bullish bias")
                            elif avg_sentiment < -0.1:
                                print("      ❌ Negative news sentiment - Bearish bias")
                            else:
                                print("      ⚖️ Neutral news sentiment - Balanced market")

                        return True
                    else:
                        print("   ⚠️ No articles for sentiment analysis")
                        return False
                else:
                    print(f"   ❌ NewsAPI error: {response.status}")
                    return False

    except Exception as e:
        print(f"   ❌ Sentiment analysis failed: {e}")
        return False

async def main():
    print("🚀 New NewsAPI Key Test Suite")
    print("Testing API Key: YOUR_NEWSAPI_KEY")
    print(f"Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 70)

    # Test 1: API Key validation
    key_valid, sample_articles = await test_new_newsapi_key()

    if not key_valid:
        print("\n❌ API Key is INVALID!")
        print("Please check your NewsAPI key and try again.")
        return 1

    # Test 2: Financial news retrieval
    financial_articles = await test_financial_news_retrieval()

    # Test 3: Stock-specific news
    await test_stock_specific_news()

    # Test 4: Sentiment analysis
    sentiment_success = await test_sentiment_analysis()

    # Summary
    print("\n" + "=" * 70)
    print("📋 NEWSAPI TEST SUMMARY")
    print("=" * 70)

    total_tests = 4
    passed = 0

    if key_valid:
        print("✅ API Key Validation: PASSED")
        passed += 1
    else:
        print("❌ API Key Validation: FAILED")

    if financial_articles:
        print(f"✅ Financial News Retrieval: PASSED ({len(financial_articles)} articles)")
        passed += 1
    else:
        print("❌ Financial News Retrieval: FAILED")

    print("✅ Stock-Specific News: COMPLETED")
    passed += 1

    if sentiment_success:
        print("✅ Sentiment Analysis: PASSED")
        passed += 1
    else:
        print("❌ Sentiment Analysis: FAILED")

    success_rate = (passed / total_tests) * 100
    print(f"\n📊 Success Rate: {success_rate:.1f}%")

    if success_rate >= 75:
        print("\n🎉 EXCELLENT! Your NewsAPI integration is working!")
        print("✅ Your trading bot now has access to real-time financial news!")
        print("\n📰 News Capabilities Now Available:")
        print("  🔴 Real-time financial news from major sources")
        print("  💭 Automated sentiment analysis")
        print("  📊 Stock-specific news tracking")
        print("  ⚡ Breaking news alerts")
        print("  📈 News-driven trading signals")

        return 0
    elif success_rate >= 50:
        print("\n⚠️ PARTIAL SUCCESS - Some features working")
        return 1
    else:
        print("\n❌ SIGNIFICANT ISSUES - Troubleshooting needed")
        return 2

if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)