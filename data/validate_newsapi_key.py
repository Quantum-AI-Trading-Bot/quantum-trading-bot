#!/usr/bin/env python3
"""
Quick NewsAPI Key Validation
"""

import asyncio
import aiohttp
import sys

async def test_newsapi_key(key):
    """Test if NewsAPI key is valid"""
    print(f"🔍 Testing NewsAPI Key: {key[:12]}...{key[-4:]}")

    # Simple test request
    url = "https://newsapi.org/v2/everything"
    params = {
        'q': 'test',
        'apiKey': key,
        'pageSize': 1
    }

    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, params=params, timeout=10) as response:
                print(f"HTTP Status: {response.status}")

                if response.status == 200:
                    data = await response.json()
                    print("✅ API Key is VALID!")
                    if 'articles' in data:
                        print(f"📰 Retrieved {len(data['articles'])} test articles")
                    return True
                else:
                    text = await response.text()
                    print(f"❌ API Error: {response.status}")
                    print(f"Response: {text[:200]}...")
                    return False

    except Exception as e:
        print(f"❌ Connection error: {e}")
        return False

async def main():
    key = "da43d52f-4661-4094-9ce6-04a7e02d5567"
    success = await test_newsapi_key(key)

    if not success:
        print("\n💡 Possible issues:")
        print("1. API key might be expired or invalid")
        print("2. API key format might be incorrect")
        print("3. NewsAPI service might be down")
        print("4. API key might have reached usage limits")

        print("\n🔧 Troubleshooting steps:")
        print("1. Double-check your NewsAPI key")
        print("2. Visit https://newsapi.org to confirm key status")
        print("3. Try regenerating a new API key")
        print("4. Check if key has required permissions")

if __name__ == "__main__":
    asyncio.run(main())