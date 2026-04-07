#!/usr/bin/env python3
"""
Unified Data Source Manager
Integrates Yahoo Finance and CoinGecko providers for comprehensive market data
"""

import asyncio
import json
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any, Union
from dataclasses import dataclass, asdict
import logging
import sys

sys.path.append('/home/davidsanker/platform')

from data.yahoo_finance_provider import YahooFinanceProvider, YahooFinanceData
from data.coingecko_provider import CoinGeckoProvider, CoinGeckoData

@dataclass
class UnifiedMarketData:
    """Unified market data structure combining different data sources"""
    symbol: str
    name: str
    asset_type: str  # 'stock', 'etf', 'crypto', 'forex', 'option'
    price: float
    change: float
    change_percent: float
    volume: int
    market_cap: Optional[float]
    data_source: str  # 'yahoo_finance', 'coingecko', 'combined'
    last_updated: datetime
    confidence_score: float  # 0.0 to 1.0
    additional_metrics: Dict[str, Any]

class UnifiedDataManager:
    """Unified manager for multiple data sources"""

    def __init__(self, config: Dict[str, Any] = None):
        self.logger = logging.getLogger(__name__)
        self.config = config or {}
        self.yahoo_provider = YahooFinanceProvider()
        self.coingecko_provider = CoinGeckoProvider(
            api_key=self.config.get('coingecko_api_key')
        )
        self.providers = {
            'yahoo_finance': self.yahoo_provider,
            'coingecko': self.coingecko_provider
        }
        self.cache = {}
        self.cache_timeout = 300  # 5 minutes
        self.is_initialized = False

    async def initialize(self) -> bool:
        """Initialize all data providers"""
        try:
            self.logger.info("Initializing Unified Data Manager...")

            # Initialize Yahoo Finance
            yahoo_success = await self.yahoo_provider.initialize()
            if yahoo_success:
                self.logger.info("✅ Yahoo Finance provider initialized")
            else:
                self.logger.warning("⚠️ Yahoo Finance provider failed to initialize")

            # Initialize CoinGecko
            coingecko_success = await self.coingecko_provider.initialize()
            if coingecko_success:
                self.logger.info("✅ CoinGecko provider initialized")
            else:
                self.logger.warning("⚠️ CoinGecko provider failed to initialize")

            self.is_initialized = yahoo_success or coingecko_success

            if self.is_initialized:
                self.logger.info("🎉 Unified Data Manager initialized successfully")
                return True
            else:
                self.logger.error("❌ No data providers could be initialized")
                return False

        except Exception as e:
            self.logger.error(f"Error initializing Unified Data Manager: {e}")
            return False

    async def close(self):
        """Close all provider connections"""
        try:
            await self.coingecko_provider.close()
            self.logger.info("Data providers closed")
        except Exception as e:
            self.logger.error(f"Error closing data providers: {e}")

    def _determine_data_source(self, symbol: str) -> List[str]:
        """Determine which data sources to try for a symbol"""
        symbol = symbol.upper().strip()

        sources = []

        # Crypto patterns
        if symbol.endswith('-USD') or symbol.endswith('USD'):
            sources.append('coingecko')
            symbol = symbol.replace('-USD', '')  # Convert for CoinGecko
        elif symbol in ['BTC', 'ETH', 'SOL', 'ADA', 'DOT', 'AVAX', 'MATIC', 'LINK', 'UNI', 'AAVE']:
            sources.append('coingecko')

        # Default to Yahoo Finance for stocks, ETFs, forex
        sources.append('yahoo_finance')

        return sources

    async def get_market_data(self, symbol: str) -> Optional[UnifiedMarketData]:
        """Get unified market data for a symbol from the best available source"""
        try:
            # Check cache first
            cache_key = f"market_data_{symbol}_{int(datetime.now().timestamp() / self.cache_timeout)}"
            if cache_key in self.cache:
                return self.cache[cache_key]

            # Determine which data sources to try
            sources_to_try = self._determine_data_source(symbol)

            unified_data = None
            source_used = None

            # Try each data source in order of preference
            for source in sources_to_try:
                try:
                    if source == 'yahoo_finance':
                        data = await self.yahoo_provider.get_market_data(symbol)
                        if data:
                            unified_data = self._convert_yahoo_to_unified(data, 'yahoo_finance')
                            source_used = 'yahoo_finance'
                            break

                    elif source == 'coingecko':
                        # Convert symbol for CoinGecko
                        coin_symbol = symbol.replace('-USD', '').lower()

                        # Try to find the coin by ID or search
                        coin_data = await self.coingecko_provider.get_coin_data(coin_symbol)
                        if not coin_data:
                            # Try searching for the coin
                            search_results = await self.coingecko_provider.search_coins(coin_symbol)
                            if search_results:
                                coin_data = await self.coingecko_provider.get_coin_data(search_results[0]['id'])

                        if coin_data:
                            unified_data = self._convert_coingecko_to_unified(coin_data, 'coingecko')
                            source_used = 'coingecko'
                            break

                except Exception as e:
                    self.logger.debug(f"Error getting data from {source} for {symbol}: {e}")
                    continue

            if unified_data:
                # Cache the result
                self.cache[cache_key] = unified_data
                return unified_data
            else:
                self.logger.warning(f"No data found for symbol: {symbol}")
                return None

        except Exception as e:
            self.logger.error(f"Error getting market data for {symbol}: {e}")
            return None

    def _convert_yahoo_to_unified(self, data: YahooFinanceData, source: str) -> UnifiedMarketData:
        """Convert Yahoo Finance data to unified format"""
        return UnifiedMarketData(
            symbol=data.symbol,
            name=data.symbol,  # Yahoo doesn't provide name in basic data
            asset_type=data.asset_type,
            price=data.price,
            change=data.change,
            change_percent=data.change_percent,
            volume=data.volume,
            market_cap=data.market_cap,
            data_source=source,
            last_updated=data.timestamp,
            confidence_score=0.85,  # High confidence for Yahoo Finance
            additional_metrics={
                'pe_ratio': data.pe_ratio,
                'dividend_yield': data.dividend_yield,
                'beta': data.beta,
                'eps': data.eps,
                'fifty_two_week_high': data.fifty_two_week_high,
                'fifty_two_week_low': data.fifty_two_week_low,
                'yahoo_additional': data.additional_data
            }
        )

    def _convert_coingecko_to_unified(self, data: CoinGeckoData, source: str) -> UnifiedMarketData:
        """Convert CoinGecko data to unified format"""
        return UnifiedMarketData(
            symbol=data.symbol,
            name=data.name,
            asset_type='crypto',
            price=data.current_price,
            change=data.price_change_24h,
            change_percent=data.price_change_percentage_24h,
            volume=int(data.total_volume),
            market_cap=data.market_cap,
            data_source=source,
            last_updated=data.last_updated,
            confidence_score=0.90,  # Very high confidence for CoinGecko
            additional_metrics={
                'market_cap_rank': data.market_cap_rank,
                'circulating_supply': data.circulating_supply,
                'total_supply': data.total_supply,
                'max_supply': data.max_supply,
                'high_24h': data.high_24h,
                'low_24h': data.low_24h,
                'price_change_percentage_7d': data.price_change_percentage_7d,
                'price_change_percentage_30d': data.price_change_percentage_30d,
                'coingecko_additional': data.additional_data
            }
        )

    async def get_multi_asset_data(self, symbols: List[str]) -> Dict[str, UnifiedMarketData]:
        """Get market data for multiple symbols concurrently"""
        try:
            tasks = [self.get_market_data(symbol) for symbol in symbols]
            results = await asyncio.gather(*tasks, return_exceptions=True)

            multi_data = {}
            for symbol, result in zip(symbols, results):
                if isinstance(result, UnifiedMarketData):
                    multi_data[symbol] = result
                else:
                    self.logger.warning(f"Failed to get data for {symbol}: {result}")

            return multi_data

        except Exception as e:
            self.logger.error(f"Error getting multi-asset data: {e}")
            return {}

    async def get_market_overview(self) -> Dict[str, Any]:
        """Get comprehensive market overview"""
        try:
            overview = {}

            # Get top stocks via Yahoo Finance
            if self.is_initialized:
                major_indices = await self.get_multi_asset_data(['^GSPC', '^DJI', '^IXIC', '^VIX'])
                overview['indices'] = {symbol: asdict(data) for symbol, data in major_indices.items()}

                # Get top cryptos via CoinGecko
                top_cryptos = await self.coingecko_provider.get_top_cryptos(10)
                if top_cryptos:
                    overview['top_cryptos'] = [asdict(crypto) for crypto in top_cryptos[:5]]

                # Get global crypto data
                global_crypto = await self.coingecko_provider.get_global_crypto_data()
                if global_crypto:
                    overview['global_crypto'] = global_crypto

                # Get market movers
                movers = await self.yahoo_provider.get_market_movers()
                if movers:
                    overview['market_movers'] = {
                        'gainers': [asdict(gainer) for gainer in movers.get('gainers', [])[:5]],
                        'losers': [asdict(loser) for loser in movers.get('losers', [])[:5]]
                    }

            overview['last_updated'] = datetime.now(timezone.utc).isoformat()

            return overview

        except Exception as e:
            self.logger.error(f"Error getting market overview: {e}")
            return {}

    async def search_symbols(self, query: str) -> List[Dict[str, Any]]:
        """Search for symbols across all data sources"""
        try:
            all_results = []

            # Search Yahoo Finance (limited implementation)
            yahoo_results = await self.yahoo_provider.search_symbols(query)
            for result in yahoo_results:
                result['source'] = 'yahoo_finance'
                all_results.append(result)

            # Search CoinGecko
            coingecko_results = await self.coingecko_provider.search_coins(query)
            for result in coingecko_results:
                result['source'] = 'coingecko'
                all_results.append(result)

            return all_results[:10]  # Return top 10 results

        except Exception as e:
            self.logger.error(f"Error searching symbols: {e}")
            return []

    async def get_portfolio_data(self, symbols: List[str]) -> Dict[str, Any]:
        """Get comprehensive portfolio data for a list of symbols"""
        try:
            # Get market data for all symbols
            market_data = await self.get_multi_asset_data(symbols)

            portfolio_analysis = {
                'symbols': {},
                'summary': {
                    'total_value': 0,
                    'total_change': 0,
                    'total_change_percent': 0,
                    'asset_allocation': {},
                    'best_performer': None,
                    'worst_performer': None
                }
            }

            best_change = -float('inf')
            worst_change = float('inf')
            best_symbol = None
            worst_symbol = None

            for symbol, data in market_data.items():
                symbol_analysis = {
                    'symbol': data.symbol,
                    'name': data.name,
                    'asset_type': data.asset_type,
                    'price': data.price,
                    'change': data.change,
                    'change_percent': data.change_percent,
                    'market_cap': data.market_cap,
                    'volume': data.volume,
                    'data_source': data.data_source,
                    'confidence_score': data.confidence_score
                }

                portfolio_analysis['symbols'][symbol] = symbol_analysis

                # Update summary statistics
                if data.change_percent > best_change:
                    best_change = data.change_percent
                    best_symbol = symbol

                if data.change_percent < worst_change:
                    worst_change = data.change_percent
                    worst_symbol = symbol

                # Asset allocation
                asset_type = data.asset_type
                if asset_type not in portfolio_analysis['summary']['asset_allocation']:
                    portfolio_analysis['summary']['asset_allocation'][asset_type] = 0
                portfolio_analysis['summary']['asset_allocation'][asset_type] += 1

            portfolio_analysis['summary']['best_performer'] = best_symbol
            portfolio_analysis['summary']['worst_performer'] = worst_symbol

            return portfolio_analysis

        except Exception as e:
            self.logger.error(f"Error getting portfolio data: {e}")
            return {}

    def get_system_status(self) -> Dict[str, Any]:
        """Get system status and provider information"""
        try:
            status = {
                'unified_manager': {
                    'initialized': self.is_initialized,
                    'cache_size': len(self.cache),
                    'cache_timeout': self.cache_timeout
                },
                'providers': {}
            }

            # Yahoo Finance status
            status['providers']['yahoo_finance'] = self.yahoo_provider.get_provider_info()

            # CoinGecko status
            status['providers']['coingecko'] = self.coingecko_provider.get_provider_info()

            status['total_sources'] = len([p for p in ['yahoo_finance', 'coingecko']
                                          if self.providers.get(p)])

            return status

        except Exception as e:
            self.logger.error(f"Error getting system status: {e}")
            return {}

# Example usage and testing
async def demo_unified_manager():
    """Demonstrate the unified data manager capabilities"""
    print("🚀 UNIFIED DATA MANAGER DEMO")
    print("=" * 60)

    manager = UnifiedDataManager()

    try:
        # Initialize
        print("\n1️⃣ Initializing Unified Data Manager...")
        success = await manager.initialize()
        print(f"   ✅ Initialization: {'Success' if success else 'Failed'}")

        if not success:
            return

        # Test stock data
        print("\n2️⃣ Testing stock data (AAPL)...")
        stock_data = await manager.get_market_data("AAPL")
        if stock_data:
            print(f"   📈 {stock_data.symbol}: ${stock_data.price} ({stock_data.change_percent:+.2f}%)")
            print(f"   📊 Source: {stock_data.data_source} | Confidence: {stock_data.confidence_score:.2f}")

        # Test crypto data
        print("\n3️⃣ Testing crypto data (BTC-USD)...")
        crypto_data = await manager.get_market_data("BTC-USD")
        if crypto_data:
            print(f"   ₿ {crypto_data.symbol}: ${crypto_data.price:,.2f} ({crypto_data.change_percent:+.2f}%)")
            print(f"   📊 Source: {crypto_data.data_source} | Rank: #{crypto_data.additional_metrics.get('market_cap_rank', 'N/A')}")

        # Test multi-asset data
        print("\n4️⃣ Testing multi-asset data...")
        symbols = ["AAPL", "MSFT", "GOOGL", "BTC-USD", "ETH-USD"]
        multi_data = await manager.get_multi_asset_data(symbols)
        print(f"   📊 Retrieved data for {len(multi_data)} symbols:")
        for symbol, data in multi_data.items():
            print(f"      • {symbol}: ${data.price:,.4f} ({data.change_percent:+.2f}%) [{data.asset_type}]")

        # Test portfolio analysis
        print("\n5️⃣ Testing portfolio analysis...")
        portfolio_data = await manager.get_portfolio_data(["AAPL", "MSFT", "GOOGL", "TSLA", "NVDA"])
        if portfolio_data:
            summary = portfolio_data['summary']
            print(f"   📈 Portfolio: {len(portfolio_data['symbols'])} symbols")
            print(f"   🏆 Best: {summary['best_performer']} | 📉 Worst: {summary['worst_performer']}")
            print(f"   📊 Asset Mix: {summary['asset_allocation']}")

        # Test market overview
        print("\n6️⃣ Testing market overview...")
        overview = await manager.get_market_overview()
        if overview:
            indices = overview.get('indices', {})
            if indices:
                print(f"   📊 Market Indices:")
                for symbol, data in indices.items():
                    print(f"      • {symbol}: {data['price']:.2f} ({data['change_percent']:+.2f}%)")

            top_cryptos = overview.get('top_cryptos', [])
            if top_cryptos:
                print(f"   🪙 Top Cryptos:")
                for crypto in top_cryptos[:3]:
                    print(f"      • {crypto['symbol']}: ${crypto['current_price']:,.2f}")

        # Test search functionality
        print("\n7️⃣ Testing search functionality...")
        search_results = await manager.search_symbols("tesla")
        if search_results:
            print(f"   🔍 Search results for 'tesla':")
            for result in search_results[:3]:
                print(f"      • {result.get('name', 'N/A')} ({result.get('symbol', 'N/A')}) [{result.get('source')}]")

        # System status
        print("\n8️⃣ System Status:")
        status = manager.get_system_status()
        print(f"   ✅ Manager Initialized: {status['unified_manager']['initialized']}")
        print(f"   📊 Active Providers: {status['total_sources']}")
        print(f"   💾 Cache Size: {status['unified_manager']['cache_size']} items")

        print(f"\n🎉 Unified Data Manager demo completed!")
        return True

    finally:
        await manager.close()

if __name__ == "__main__":
    asyncio.run(demo_unified_manager())