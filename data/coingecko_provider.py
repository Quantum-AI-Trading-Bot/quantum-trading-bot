#!/usr/bin/env python3
"""
CoinGecko Cryptocurrency Data Provider
Comprehensive integration with CoinGecko API for cryptocurrency market data
"""

import asyncio
import aiohttp
import json
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
import logging
import sys
import time

sys.path.append('/home/davidsanker/platform')

@dataclass
class CoinGeckoData:
    """Data structure for CoinGecko cryptocurrency data"""
    symbol: str
    name: str
    coin_id: str
    current_price: float
    price_change_24h: float
    price_change_percentage_24h: float
    market_cap: float
    market_cap_rank: int
    total_volume: float
    circulating_supply: float
    total_supply: float
    max_supply: Optional[float]
    high_24h: float
    low_24h: float
    price_change_percentage_7d: float
    price_change_percentage_30d: float
    price_change_percentage_1y: float
    last_updated: datetime
    additional_data: Dict[str, Any]

class CoinGeckoProvider:
    """CoinGecko cryptocurrency data provider"""

    def __init__(self, api_key: Optional[str] = None):
        self.logger = logging.getLogger(__name__)
        self.api_key = api_key  # Optional - free tier doesn't require API key
        self.base_url = "https://api.coingecko.com/api/v3"
        self.cache = {}
        self.cache_timeout = 300  # 5 minutes
        self.rate_limit_delay = 1.2  # 1.2 seconds between requests (free tier limit)
        self.session = None

    async def initialize(self) -> bool:
        """Initialize the CoinGecko provider"""
        try:
            self.logger.info("Initializing CoinGecko provider...")
            self.session = aiohttp.ClientSession()

            # Test API connectivity
            test_data = await self.get_coin_data("bitcoin")
            if test_data:
                self.logger.info("CoinGecko provider initialized successfully")
                return True
            else:
                self.logger.error("Failed to initialize CoinGecko provider")
                await self.close()
                return False

        except Exception as e:
            self.logger.error(f"Error initializing CoinGecko provider: {e}")
            if self.session:
                await self.session.close()
            return False

    async def close(self):
        """Close the aiohttp session"""
        if self.session:
            await self.session.close()
            self.session = None

    def _get_cache_key(self, endpoint: str, params: str = "") -> str:
        """Generate cache key for API requests"""
        return f"{endpoint}_{params}_{int(datetime.now().timestamp() / self.cache_timeout)}"

    def _is_cache_valid(self, cache_key: str) -> bool:
        """Check if cached data is still valid"""
        if cache_key not in self.cache:
            return False
        cache_time = self.cache[cache_key].get('timestamp', 0)
        return (datetime.now().timestamp() - cache_time) < self.cache_timeout

    async def _make_request(self, endpoint: str, params: Dict[str, Any] = None) -> Optional[Dict]:
        """Make a rate-limited API request"""
        try:
            # Generate cache key
            params_str = json.dumps(params, sort_keys=True) if params else ""
            cache_key = self._get_cache_key(endpoint, params_str)

            # Check cache first
            if self._is_cache_valid(cache_key):
                return self.cache[cache_key]['data']

            # Rate limiting
            await asyncio.sleep(self.rate_limit_delay)

            # Prepare headers
            headers = {}
            if self.api_key:
                headers['X-Cg-Pro-Api-Key'] = self.api_key

            # Make request
            url = f"{self.base_url}/{endpoint}"
            async with self.session.get(url, params=params, headers=headers) as response:
                if response.status == 200:
                    data = await response.json()

                    # Cache the data
                    self.cache[cache_key] = {
                        'data': data,
                        'timestamp': datetime.now().timestamp()
                    }

                    return data
                elif response.status == 429:
                    self.logger.warning("Rate limit exceeded, backing off...")
                    await asyncio.sleep(60)  # Wait 1 minute on rate limit
                    return None
                else:
                    self.logger.error(f"API request failed: {response.status} - {await response.text()}")
                    return None

        except Exception as e:
            self.logger.error(f"Error making request to {endpoint}: {e}")
            return None

    async def get_coin_data(self, coin_id: str) -> Optional[CoinGeckoData]:
        """Get comprehensive data for a specific cryptocurrency"""
        try:
            params = {
                'localization': 'false',
                'tickers': 'false',
                'market_data': 'true',
                'community_data': 'false',
                'developer_data': 'false',
                'sparkline': 'false'
            }

            data = await self._make_request(f"coins/{coin_id}", params)
            if not data:
                return None

            market_data = data.get('market_data', {})
            current_price = market_data.get('current_price', {}).get('usd', 0)

            return CoinGeckoData(
                symbol=data.get('symbol', '').upper(),
                name=data.get('name', ''),
                coin_id=data.get('id', ''),
                current_price=current_price,
                price_change_24h=market_data.get('price_change_24h_in_currency', {}).get('usd', 0),
                price_change_percentage_24h=market_data.get('price_change_percentage_24h', 0),
                market_cap=market_data.get('market_cap', {}).get('usd', 0),
                market_cap_rank=market_data.get('market_cap_rank', 0),
                total_volume=market_data.get('total_volume', {}).get('usd', 0),
                circulating_supply=market_data.get('circulating_supply', 0),
                total_supply=market_data.get('total_supply', 0),
                max_supply=market_data.get('max_supply'),
                high_24h=market_data.get('high_24h', {}).get('usd', 0),
                low_24h=market_data.get('low_24h', {}).get('usd', 0),
                price_change_percentage_7d=market_data.get('price_change_percentage_7d', 0),
                price_change_percentage_30d=market_data.get('price_change_percentage_30d', 0),
                price_change_percentage_1y=market_data.get('price_change_percentage_1y', 0),
                last_updated=datetime.fromisoformat(data.get('last_updated', '').replace('Z', '+00:00')),
                additional_data={
                    'image': data.get('image', {}).get('small'),
                    'market_data': market_data,
                    'ath': market_data.get('ath', {}).get('usd'),
                    'ath_change_percentage': market_data.get('ath_change_percentage', {}).get('usd'),
                    'atl': market_data.get('atl', {}).get('usd'),
                    'atl_change_percentage': market_data.get('atl_change_percentage', {}).get('usd'),
                    'price_change_percentage_14d': market_data.get('price_change_percentage_14d'),
                    'price_change_percentage_200d': market_data.get('price_change_percentage_200d'),
                    'roi': market_data.get('roi'),
                    'market_cap dominance': market_data.get('market_cap_dominance', 0)
                }
            )

        except Exception as e:
            self.logger.error(f"Error getting coin data for {coin_id}: {e}")
            return None

    async def search_coins(self, query: str) -> List[Dict[str, Any]]:
        """Search for cryptocurrencies"""
        try:
            params = {'query': query}
            data = await self._make_request("search", params)
            if not data:
                return []

            coins = data.get('coins', [])[:10]  # Return top 10 results
            return [{
                'id': coin['id'],
                'name': coin['name'],
                'symbol': coin['symbol'].upper(),
                'market_cap_rank': coin.get('market_cap_rank'),
                'thumb': coin.get('thumb'),
                'large': coin.get('large')
            } for coin in coins]

        except Exception as e:
            self.logger.error(f"Error searching coins: {e}")
            return []

    async def get_top_cryptos(self, limit: int = 100, vs_currency: str = 'usd') -> List[CoinGeckoData]:
        """Get top cryptocurrencies by market cap"""
        try:
            params = {
                'vs_currency': vs_currency,
                'order': 'market_cap_desc',
                'per_page': limit,
                'page': 1,
                'sparkline': 'false',
                'price_change_percentage': '24h,7d,30d,1y'
            }

            data = await self._make_request("coins/markets", params)
            if not data:
                return []

            crypto_list = []
            for coin in data:
                try:
                    crypto_data = CoinGeckoData(
                        symbol=coin.get('symbol', '').upper(),
                        name=coin.get('name', ''),
                        coin_id=coin.get('id', ''),
                        current_price=coin.get('current_price', 0),
                        price_change_24h=coin.get('price_change_24h', 0),
                        price_change_percentage_24h=coin.get('price_change_percentage_24h', 0),
                        market_cap=coin.get('market_cap', 0),
                        market_cap_rank=coin.get('market_cap_rank', 0),
                        total_volume=coin.get('total_volume', 0),
                        circulating_supply=coin.get('circulating_supply', 0),
                        total_supply=coin.get('total_supply', 0),
                        max_supply=coin.get('max_supply'),
                        high_24h=coin.get('high_24h', 0),
                        low_24h=coin.get('low_24h', 0),
                        price_change_percentage_7d=coin.get('price_change_percentage_7d', 0),
                        price_change_percentage_30d=coin.get('price_change_percentage_30d', 0),
                        price_change_percentage_1y=coin.get('price_change_percentage_1y', 0),
                        last_updated=datetime.now(),  # Markets endpoint doesn't provide last_updated
                        additional_data={
                            'image': coin.get('image'),
                            'price_change_percentage_14d': coin.get('price_change_percentage_14d'),
                            'price_change_percentage_200d': coin.get('price_change_percentage_200d'),
                            'ath': coin.get('ath'),
                            'ath_change_percentage': coin.get('ath_change_percentage'),
                            'atl': coin.get('atl'),
                            'atl_change_percentage': coin.get('atl_change_percentage'),
                            'roi': coin.get('roi'),
                            'market_cap_dominance': coin.get('market_cap_dominance', 0)
                        }
                    )
                    crypto_list.append(crypto_data)
                except Exception as e:
                    self.logger.error(f"Error processing coin {coin.get('id')}: {e}")
                    continue

            return crypto_list

        except Exception as e:
            self.logger.error(f"Error getting top cryptos: {e}")
            return []

    async def get_historical_data(self, coin_id: str, days: int = 30, vs_currency: str = 'usd') -> List[Dict]:
        """Get historical price data for a cryptocurrency"""
        try:
            params = {
                'vs_currency': vs_currency,
                'days': days
            }

            data = await self._make_request(f"coins/{coin_id}/market_chart", params)
            if not data:
                return []

            prices = data.get('prices', [])
            volumes = data.get('total_volumes', [])
            market_caps = data.get('market_caps', [])

            result = []
            for i, price_data in enumerate(prices):
                timestamp = price_data[0]
                price = price_data[1]
                volume = volumes[i][1] if i < len(volumes) else 0
                market_cap = market_caps[i][1] if i < len(market_caps) else 0

                result.append({
                    'timestamp': datetime.fromtimestamp(timestamp / 1000),
                    'price': price,
                    'volume': volume,
                    'market_cap': market_cap
                })

            return result

        except Exception as e:
            self.logger.error(f"Error getting historical data for {coin_id}: {e}")
            return []

    async def get_crypto_categories(self) -> List[Dict[str, Any]]:
        """Get cryptocurrency categories and their market data"""
        try:
            params = {'order': 'market_cap_desc'}
            data = await self._make_request("coins/categories", params)
            if not data:
                return []

            categories = []
            for category in data:
                try:
                    categories.append({
                        'id': category.get('id'),
                        'name': category.get('name'),
                        'market_cap': category.get('market_cap', 0),
                        'market_cap_change_24h': category.get('market_cap_change_24h', 0),
                        'volume_24h': category.get('volume_24h', 0),
                        'content': category.get('content', 0),
                        'top_3_coins': category.get('top_3_coins', [])
                    })
                except Exception as e:
                    continue

            return categories

        except Exception as e:
            self.logger.error(f"Error getting crypto categories: {e}")
            return []

    async def get_trending_cryptos(self) -> List[Dict[str, Any]]:
        """Get trending cryptocurrencies"""
        try:
            data = await self._make_request("search/trending")
            if not data:
                return []

            trending = data.get('coins', [])
            result = []

            for item in trending:
                try:
                    coin = item.get('item', {})
                    result.append({
                        'id': coin.get('id'),
                        'name': coin.get('name'),
                        'symbol': coin.get('symbol').upper(),
                        'market_cap_rank': coin.get('market_cap_rank'),
                        'price_btc': coin.get('price_btc'),
                        'score': coin.get('score'),
                        'large': coin.get('large')
                    })
                except Exception as e:
                    continue

            return result

        except Exception as e:
            self.logger.error(f"Error getting trending cryptos: {e}")
            return []

    async def get_global_crypto_data(self) -> Dict[str, Any]:
        """Get global cryptocurrency market data"""
        try:
            data = await self._make_request("global")
            if not data:
                return {}

            return {
                'total_market_cap_usd': data.get('data', {}).get('total_market_cap', {}).get('usd', 0),
                'total_volume_usd': data.get('data', {}).get('total_volume', {}).get('usd', 0),
                'market_cap_percentage_btc': data.get('data', {}).get('market_cap_percentage', {}).get('btc', 0),
                'market_cap_percentage_eth': data.get('data', {}).get('market_cap_percentage', {}).get('eth', 0),
                'market_cap_change_percentage_24h_usd': data.get('data', {}).get('market_cap_change_percentage_24h_usd', 0),
                'updated_at': datetime.fromisoformat(data.get('data', {}).get('updated_at', '').replace('Z', '+00:00'))
            }

        except Exception as e:
            self.logger.error(f"Error getting global crypto data: {e}")
            return {}

    def get_provider_info(self) -> Dict[str, Any]:
        """Get information about the data provider"""
        return {
            'name': 'CoinGecko API',
            'description': 'Comprehensive cryptocurrency market data',
            'data_types': ['cryptocurrency', 'defi', 'nft'],
            'features': [
                'Real-time prices for 10,000+ cryptocurrencies',
                'Historical price data',
                'Market cap and volume data',
                'Trending coins',
                'Category analysis',
                'Global market statistics'
            ],
            'limitations': [
                'Rate limited: ~50 calls/minute free tier',
                'No real-time WebSocket API',
                'Data may have slight delays',
                'Historical data limited to daily granularity'
            ],
            'cost': 'Free tier available',
            'api_key_required': False,
            'free_tier_limits': '10-50 calls/minute, no API key required'
        }

# Example usage and testing
async def demo_coingecko():
    """Demonstrate CoinGecko provider capabilities"""
    print("₿ COINGECKO PROVIDER DEMO")
    print("=" * 50)

    provider = CoinGeckoProvider()

    try:
        # Initialize
        print("\n1️⃣ Initializing provider...")
        success = await provider.initialize()
        print(f"   ✅ Initialization: {'Success' if success else 'Failed'}")

        if not success:
            return

        # Test Bitcoin data
        print("\n2️⃣ Testing Bitcoin data...")
        btc_data = await provider.get_coin_data("bitcoin")
        if btc_data:
            print(f"   ₿ {btc_data.symbol}: ${btc_data.current_price:,.2f} ({btc_data.price_change_percentage_24h:+.2f}%)")
            print(f"   📊 Market Cap: ${btc_data.market_cap/1e9:.1f}B | Rank: #{btc_data.market_cap_rank}")
            print(f"   💹 Volume: ${btc_data.total_volume/1e9:.1f}B")

        # Test Ethereum data
        print("\n3️⃣ Testing Ethereum data...")
        eth_data = await provider.get_coin_data("ethereum")
        if eth_data:
            print(f"   🐐 {eth_data.symbol}: ${eth_data.current_price:,.2f} ({eth_data.price_change_percentage_24h:+.2f}%)")
            print(f"   📈 7d Change: {eth_data.price_change_percentage_7d:+.2f}% | 30d: {eth_data.price_change_percentage_30d:+.2f}%")

        # Test top cryptocurrencies
        print("\n4️⃣ Testing top cryptocurrencies...")
        top_cryptos = await provider.get_top_cryptos(10)
        if top_cryptos:
            print(f"   🏆 Top 10 Cryptocurrencies:")
            for i, crypto in enumerate(top_cryptos[:5], 1):
                change_emoji = "🟢" if crypto.price_change_percentage_24h > 0 else "🔴"
                print(f"      {i}. {crypto.symbol}: ${crypto.current_price:,.4f} ({change_emoji} {crypto.price_change_percentage_24h:+.2f}%)")

        # Test trending cryptos
        print("\n5️⃣ Testing trending cryptocurrencies...")
        trending = await provider.get_trending_cryptos()
        if trending:
            print(f"   🔥 Trending:")
            for coin in trending[:3]:
                print(f"      • {coin['symbol']} ({coin['name']}) - Score: {coin.get('score', 'N/A')}")

        # Test search functionality
        print("\n6️⃣ Testing search functionality...")
        search_results = await provider.search_coins("solana")
        if search_results:
            print(f"   🔍 Search results for 'solana':")
            for result in search_results[:2]:
                print(f"      • {result['name']} ({result['symbol']}) - ID: {result['id']}")

        # Test global crypto data
        print("\n7️⃣ Testing global market data...")
        global_data = await provider.get_global_crypto_data()
        if global_data:
            total_market_cap = global_data.get('total_market_cap_usd', 0)
            if total_market_cap > 0:
                print(f"   🌍 Total Crypto Market Cap: ${total_market_cap/1e12:.2f}T")
                print(f"   📊 24h Volume: ${global_data.get('total_volume_usd', 0)/1e9:.1f}B")
                print(f"   🥇 BTC Dominance: {global_data.get('market_cap_percentage_btc', 0):.1f}%")

        # Test historical data
        print("\n8️⃣ Testing historical data...")
        hist_data = await provider.get_historical_data("bitcoin", 7)  # 7 days
        if hist_data:
            latest_price = hist_data[-1]['price']
            first_price = hist_data[0]['price']
            week_change = ((latest_price - first_price) / first_price * 100)
            print(f"   📈 Bitcoin 7-day historical data: {len(hist_data)} records")
            print(f"   💹 Week change: {week_change:+.2f}%")

        # Provider info
        print("\n9️⃣ Provider Information:")
        info = provider.get_provider_info()
        print(f"   📊 Data Types: {', '.join(info['data_types'])}")
        print(f"   💰 Cost: {info['cost']}")
        print(f"   📋 Limits: {info['free_tier_limits']}")

        print(f"\n✅ CoinGecko provider demo completed!")

    finally:
        await provider.close()

if __name__ == "__main__":
    asyncio.run(demo_coingecko())