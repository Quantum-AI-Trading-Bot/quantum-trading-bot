#!/usr/bin/env python3
"""
Yahoo Finance Data Provider
Comprehensive integration with Yahoo Finance API for stocks, ETFs, crypto, forex, and options
"""

import asyncio
import yfinance as yf
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Union
from dataclasses import dataclass
import logging
import sys
import time

sys.path.append('/home/davidsanker/platform')

@dataclass
class YahooFinanceData:
    """Data structure for Yahoo Finance market data"""
    symbol: str
    asset_type: str  # 'stock', 'etf', 'crypto', 'forex', 'option'
    price: float
    change: float
    change_percent: float
    volume: int
    market_cap: Optional[float]
    pe_ratio: Optional[float]
    dividend_yield: Optional[float]
    fifty_two_week_high: Optional[float]
    fifty_two_week_low: Optional[float]
    beta: Optional[float]
    eps: Optional[float]
    timestamp: datetime
    additional_data: Dict[str, Any]

class YahooFinanceProvider:
    """Yahoo Finance data provider for comprehensive market data"""

    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.cache = {}
        self.cache_timeout = 300  # 5 minutes
        self.rate_limit_delay = 0.5  # 500ms between requests

    async def initialize(self) -> bool:
        """Initialize the Yahoo Finance provider"""
        try:
            self.logger.info("Initializing Yahoo Finance provider...")
            # Test with a well-known symbol
            test_data = await self.get_market_data("AAPL")
            if test_data:
                self.logger.info("Yahoo Finance provider initialized successfully")
                return True
            else:
                self.logger.error("Failed to initialize Yahoo Finance provider")
                return False
        except Exception as e:
            self.logger.error(f"Error initializing Yahoo Finance provider: {e}")
            return False

    def _get_cache_key(self, symbol: str, data_type: str = "market_data") -> str:
        """Generate cache key for data requests"""
        return f"{symbol}_{data_type}_{int(datetime.now().timestamp() / self.cache_timeout)}"

    def _is_cache_valid(self, cache_key: str) -> bool:
        """Check if cached data is still valid"""
        if cache_key not in self.cache:
            return False
        cache_time = self.cache[cache_key].get('timestamp', 0)
        return (datetime.now().timestamp() - cache_time) < self.cache_timeout

    async def get_market_data(self, symbol: str) -> Optional[YahooFinanceData]:
        """Get current market data for a symbol"""
        try:
            # Check cache first
            cache_key = self._get_cache_key(symbol)
            if self._is_cache_valid(cache_key):
                return self.cache[cache_key]['data']

            # Add rate limiting delay
            await asyncio.sleep(self.rate_limit_delay)

            # Get ticker data
            ticker = yf.Ticker(symbol)
            info = ticker.info
            hist = ticker.history(period="1d")

            if hist.empty:
                self.logger.warning(f"No historical data found for {symbol}")
                return None

            # Extract current price data
            current_price = hist['Close'].iloc[-1] if len(hist) > 0 else None
            prev_close = info.get('previousClose', current_price)

            if current_price is None:
                self.logger.error(f"No price data available for {symbol}")
                return None

            change = current_price - prev_close if prev_close else 0
            change_percent = (change / prev_close * 100) if prev_close else 0

            # Determine asset type
            asset_type = self._determine_asset_type(info)

            # Create data object
            market_data = YahooFinanceData(
                symbol=symbol.upper(),
                asset_type=asset_type,
                price=round(current_price, 4),
                change=round(change, 4),
                change_percent=round(change_percent, 4),
                volume=int(info.get('volume', hist['Volume'].iloc[-1] if len(hist) > 0 else 0)),
                market_cap=info.get('marketCap'),
                pe_ratio=info.get('trailingPE'),
                dividend_yield=info.get('dividendYield'),
                fifty_two_week_high=info.get('fiftyTwoWeekHigh'),
                fifty_two_week_low=info.get('fiftyTwoWeekLow'),
                beta=info.get('beta'),
                eps=info.get('trailingEps'),
                timestamp=datetime.now(),
                additional_data={
                    'open': info.get('open'),
                    'day_high': info.get('dayHigh'),
                    'day_low': info.get('dayLow'),
                    'average_volume': info.get('averageVolume'),
                    'forward_pe': info.get('forwardPE'),
                    'earnings_growth': info.get('earningsGrowth'),
                    'revenue_growth': info.get('revenueGrowth'),
                    'price_to_sales': info.get('priceToSalesTrailing12Months'),
                    'industry': info.get('industry'),
                    'sector': info.get('sector'),
                    'currency': info.get('currency'),
                    'quote_type': info.get('quoteType'),
                    'regular_market_price': info.get('regularMarketPrice'),
                    'pre_market_price': info.get('preMarketPrice'),
                    'post_market_price': info.get('postMarketPrice')
                }
            )

            # Cache the data
            self.cache[cache_key] = {
                'data': market_data,
                'timestamp': datetime.now().timestamp()
            }

            return market_data

        except Exception as e:
            self.logger.error(f"Error getting market data for {symbol}: {e}")
            return None

    def _determine_asset_type(self, info: Dict) -> str:
        """Determine the asset type based on ticker info"""
        quote_type = info.get('quoteType', '').lower()

        if quote_type == 'equity':
            return 'stock'
        elif quote_type == 'etf':
            return 'etf'
        elif quote_type == 'cryptocurrency':
            return 'crypto'
        elif quote_type == 'currency':
            return 'forex'
        elif quote_type == 'option':
            return 'option'
        else:
            # Fallback: check symbol patterns
            symbol = info.get('symbol', '').upper()
            if symbol.endswith('-USD') or symbol.endswith('=X'):
                return 'crypto'
            elif '=' in symbol:
                return 'forex'
            else:
                return 'stock'

    async def get_historical_data(self, symbol: str, period: str = "1mo") -> Optional[pd.DataFrame]:
        """Get historical price data"""
        try:
            # Add rate limiting delay
            await asyncio.sleep(self.rate_limit_delay)

            ticker = yf.Ticker(symbol)
            hist = ticker.history(period=period)

            if hist.empty:
                return None

            return hist

        except Exception as e:
            self.logger.error(f"Error getting historical data for {symbol}: {e}")
            return None

    async def get_financials(self, symbol: str) -> Dict[str, Any]:
        """Get financial statements and metrics"""
        try:
            # Add rate limiting delay
            await asyncio.sleep(self.rate_limit_delay)

            ticker = yf.Ticker(symbol)
            financials = {}

            # Income Statement
            if hasattr(ticker, 'financials') and not ticker.financials.empty:
                financials['income_statement'] = ticker.financials.to_dict()

            # Balance Sheet
            if hasattr(ticker, 'balance_sheet') and not ticker.balance_sheet.empty:
                financials['balance_sheet'] = ticker.balance_sheet.to_dict()

            # Cash Flow
            if hasattr(ticker, 'cashflow') and not ticker.cashflow.empty:
                financials['cash_flow'] = ticker.cashflow.to_dict()

            # Quarterly data
            if hasattr(ticker, 'quarterly_financials') and not ticker.quarterly_financials.empty:
                financials['quarterly_income'] = ticker.quarterly_financials.to_dict()

            return financials

        except Exception as e:
            self.logger.error(f"Error getting financials for {symbol}: {e}")
            return {}

    async def get_options_chain(self, symbol: str, expiration: Optional[str] = None) -> Dict[str, pd.DataFrame]:
        """Get options chain data"""
        try:
            # Add rate limiting delay
            await asyncio.sleep(self.rate_limit_delay)

            ticker = yf.Ticker(symbol)

            # Get available expiration dates
            expirations = ticker.options
            if not expirations:
                return {}

            # Use provided expiration or get the nearest one
            if expiration and expiration in expirations:
                target_expiration = expiration
            else:
                target_expiration = expirations[0]  # Nearest expiration

            options = ticker.option_chain(target_expiration)

            return {
                'calls': options.calls,
                'puts': options.puts,
                'expiration': target_expiration,
                'available_expirations': expirations
            }

        except Exception as e:
            self.logger.error(f"Error getting options chain for {symbol}: {e}")
            return {}

    async def get_sector_data(self, sector_symbols: List[str]) -> Dict[str, YahooFinanceData]:
        """Get market data for entire sector"""
        sector_data = {}

        for symbol in sector_symbols:
            try:
                data = await self.get_market_data(symbol)
                if data:
                    sector_data[symbol] = data
            except Exception as e:
                self.logger.error(f"Error getting sector data for {symbol}: {e}")
                continue

        return sector_data

    async def get_market_movers(self) -> Dict[str, List[YahooFinanceData]]:
        """Get top market movers (gainers and losers)"""
        try:
            # Predefined list of major indices and popular stocks for demonstration
            # In production, you'd use screeners or specific market movers endpoints
            market_symbols = [
                # Indices
                '^GSPC', '^DJI', '^IXIC', '^RUT', '^VIX',
                # Popular stocks
                'AAPL', 'MSFT', 'GOOGL', 'AMZN', 'TSLA', 'META', 'NVDA', 'NFLX',
                # ETFs
                'SPY', 'QQQ', 'IWM', 'GLD', 'TLT',
                # Crypto
                'BTC-USD', 'ETH-USD'
            ]

            all_data = []
            for symbol in market_symbols:
                try:
                    data = await self.get_market_data(symbol)
                    if data and data.change_percent != 0:
                        all_data.append(data)
                except Exception as e:
                    continue

            # Sort by percentage change
            gainers = sorted([d for d in all_data if d.change_percent > 0],
                           key=lambda x: x.change_percent, reverse=True)[:10]
            losers = sorted([d for d in all_data if d.change_percent < 0],
                           key=lambda x: x.change_percent)[:10]

            return {
                'gainers': gainers,
                'losers': losers,
                'most_active': sorted(all_data, key=lambda x: x.volume, reverse=True)[:10]
            }

        except Exception as e:
            self.logger.error(f"Error getting market movers: {e}")
            return {'gainers': [], 'losers': [], 'most_active': []}

    async def search_symbols(self, query: str) -> List[Dict[str, str]]:
        """Search for symbols (limited implementation)"""
        try:
            # Note: yfinance doesn't provide a direct search API
            # This is a basic implementation using common patterns
            query = query.upper().strip()

            suggestions = []

            # Common stock symbols
            if 'AAPL'.startswith(query):
                suggestions.append({'symbol': 'AAPL', 'name': 'Apple Inc.', 'type': 'stock'})
            if 'MSFT'.startswith(query):
                suggestions.append({'symbol': 'MSFT', 'name': 'Microsoft Corporation', 'type': 'stock'})
            if 'GOOGL'.startswith(query):
                suggestions.append({'symbol': 'GOOGL', 'name': 'Alphabet Inc.', 'type': 'stock'})
            if 'AMZN'.startswith(query):
                suggestions.append({'symbol': 'AMZN', 'name': 'Amazon.com Inc.', 'type': 'stock'})
            if 'TSLA'.startswith(query):
                suggestions.append({'symbol': 'TSLA', 'name': 'Tesla Inc.', 'type': 'stock'})

            # Crypto
            if 'BTC'.startswith(query):
                suggestions.append({'symbol': 'BTC-USD', 'name': 'Bitcoin USD', 'type': 'crypto'})
            if 'ETH'.startswith(query):
                suggestions.append({'symbol': 'ETH-USD', 'name': 'Ethereum USD', 'type': 'crypto'})

            # ETFs
            if 'SPY'.startswith(query):
                suggestions.append({'symbol': 'SPY', 'name': 'SPDR S&P 500 ETF', 'type': 'etf'})
            if 'QQQ'.startswith(query):
                suggestions.append({'symbol': 'QQQ', 'name': 'Invesco QQQ Trust', 'type': 'etf'})

            return suggestions[:5]  # Return top 5 suggestions

        except Exception as e:
            self.logger.error(f"Error searching symbols: {e}")
            return []

    def get_provider_info(self) -> Dict[str, Any]:
        """Get information about the data provider"""
        return {
            'name': 'Yahoo Finance API',
            'description': 'Comprehensive financial data from Yahoo Finance',
            'data_types': ['stocks', 'etfs', 'crypto', 'forex', 'options'],
            'features': [
                'Real-time and historical prices',
                'Financial statements',
                'Options chains',
                'Company fundamentals',
                'Market movers',
                'Sector analysis'
            ],
            'limitations': [
                'Rate limited (no official API)',
                'Data may have delays',
                'Not suitable for high-frequency trading',
                'Requires internet connection'
            ],
            'cost': 'Free',
            'api_key_required': False
        }

# Example usage and testing
async def demo_yahoo_finance():
    """Demonstrate Yahoo Finance provider capabilities"""
    print("📊 YAHOO FINANCE PROVIDER DEMO")
    print("=" * 50)

    provider = YahooFinanceProvider()

    # Initialize
    print("\n1️⃣ Initializing provider...")
    success = await provider.initialize()
    print(f"   ✅ Initialization: {'Success' if success else 'Failed'}")

    if not success:
        return

    # Test stock data
    print("\n2️⃣ Testing stock data (AAPL)...")
    stock_data = await provider.get_market_data("AAPL")
    if stock_data:
        print(f"   📈 {stock_data.symbol}: ${stock_data.price} ({stock_data.change_percent:+.2f}%)")
        print(f"   💹 Volume: {stock_data.volume:,} | Cap: ${stock_data.market_cap/1e9:.1f}B" if stock_data.market_cap else "   💹 Volume: {stock_data.volume:,}")
        print(f"   🏢 Sector: {stock_data.additional_data.get('sector', 'N/A')}")

    # Test crypto data
    print("\n3️⃣ Testing crypto data (BTC-USD)...")
    crypto_data = await provider.get_market_data("BTC-USD")
    if crypto_data:
        print(f"   ₿ {crypto_data.symbol}: ${crypto_data.price:,.2f} ({crypto_data.change_percent:+.2f}%)")
        print(f"   📊 Volume: {crypto_data.volume:,}")

    # Test ETF data
    print("\n4️⃣ Testing ETF data (SPY)...")
    etf_data = await provider.get_market_data("SPY")
    if etf_data:
        print(f"   💼 {etf_data.symbol}: ${etf_data.price} ({etf_data.change_percent:+.2f}%)")
        print(f"   📈 52W Range: ${etf_data.fifty_two_week_low:.2f} - ${etf_data.fifty_two_week_high:.2f}")

    # Test historical data
    print("\n5️⃣ Testing historical data...")
    hist_data = await provider.get_historical_data("MSFT", "5d")
    if hist_data is not None and not hist_data.empty:
        print(f"   📅 MSFT 5-day data: {len(hist_data)} records")
        latest_price = hist_data['Close'].iloc[-1]
        print(f"   📈 Latest close: ${latest_price:.2f}")

    # Test options data
    print("\n6️⃣ Testing options data...")
    options_data = await provider.get_options_chain("AAPL")
    if options_data:
        calls_count = len(options_data.get('calls', pd.DataFrame()))
        puts_count = len(options_data.get('puts', pd.DataFrame()))
        print(f"   📊 AAPL Options: {calls_count} calls, {puts_count} puts")
        print(f"   📅 Expiration: {options_data.get('expiration', 'N/A')}")

    # Test market movers
    print("\n7️⃣ Testing market movers...")
    movers = await provider.get_market_movers()
    if movers.get('gainers'):
        print(f"   🚀 Top Gainer: {movers['gainers'][0].symbol} (+{movers['gainers'][0].change_percent:.2f}%)")
    if movers.get('losers'):
        print(f"   📉 Top Loser: {movers['losers'][0].symbol} ({movers['losers'][0].change_percent:.2f}%)")

    # Provider info
    print("\n8️⃣ Provider Information:")
    info = provider.get_provider_info()
    print(f"   📊 Data Types: {', '.join(info['data_types'])}")
    print(f"   💰 Cost: {info['cost']}")
    print(f"   🔑 API Key: {'Required' if info['api_key_required'] else 'Not Required'}")

    print(f"\n✅ Yahoo Finance provider demo completed!")
    return True

if __name__ == "__main__":
    asyncio.run(demo_yahoo_finance())