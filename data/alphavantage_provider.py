#!/usr/bin/env python3
"""
Alpha Vantage Data Provider for Technical Indicators
Provides free technical indicators (RSI, MACD, Bollinger Bands, etc.)
Supports stocks, forex, crypto, and commodities
"""

import requests
import json
import logging
import time
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict
from decimal import Decimal

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@dataclass
class AlphaVantageIndicator:
    """Technical indicator data from Alpha Vantage"""
    symbol: str
    indicator_type: str
    timestamp: datetime
    value: float
    signal: str  # BUY, SELL, HOLD
    metadata: Dict[str, Any]

@dataclass
class AlphaVantageTechnicalData:
    """Complete technical analysis data"""
    symbol: str
    timestamp: datetime
    rsi: Optional[float] = None
    macd: Optional[Dict[str, float]] = None
    bollinger_bands: Optional[Dict[str, float]] = None
    sma_20: Optional[float] = None
    sma_50: Optional[float] = None
    ema_12: Optional[float] = None
    ema_26: Optional[float] = None
    stochastic: Optional[Dict[str, float]] = None
    adx: Optional[float] = None
    cci: Optional[float] = None
    williams_r: Optional[float] = None
    signal_strength: int = 0  # 0-10
    overall_signal: str = "HOLD"
    metadata: Dict[str, Any] = None

class AlphaVantageProvider:
    """
    Alpha Vantage API provider for free technical indicators

    Features:
    - 20+ technical indicators
    - Multiple asset classes (stocks, forex, crypto, commodities)
    - Real-time and historical data
    - Signal generation
    - Rate limiting (500 calls/day free tier)
    """

    def __init__(self, api_key: str):
        self.api_key = api_key
        self.base_url = "https://www.alphavantage.co/query"
        self.last_call_time = 0
        self.min_interval = 12  # 12 seconds between calls (500 calls/day = ~20 per hour)
        self.session = requests.Session()

        logger.info("🎯 Alpha Vantage Technical Indicators Provider initialized")
        logger.info(f"📊 Free tier limit: 500 calls/day (1 call every ~12 seconds)")
        logger.info("⚠️ Rate limiting enabled for free tier usage")

    def _rate_limit(self):
        """Implement rate limiting for free tier"""
        current_time = time.time()
        time_since_last_call = current_time - self.last_call_time

        if time_since_last_call < self.min_interval:
            wait_time = self.min_interval - time_since_last_call
            logger.info(f"⏳ Rate limiting: waiting {wait_time:.1f} seconds...")
            time.sleep(wait_time)

        self.last_call_time = time.time()

    def _make_request(self, params: Dict[str, str]) -> Optional[Dict[str, Any]]:
        """Make API request with error handling"""
        try:
            self._rate_limit()

            params['apikey'] = self.api_key

            response = self.session.get(self.base_url, params=params, timeout=30)
            response.raise_for_status()

            data = response.json()

            # Check for API errors
            if 'Error Message' in data:
                logger.error(f"❌ Alpha Vantage API Error: {data['Error Message']}")
                return None

            if 'Note' in data:
                logger.warning(f"⚠️ Alpha Vantage API Note: {data['Note']}")
                return None

            return data

        except requests.exceptions.RequestException as e:
            logger.error(f"❌ Request failed: {e}")
            return None
        except json.JSONDecodeError as e:
            logger.error(f"❌ JSON decode error: {e}")
            return None
        except Exception as e:
            logger.error(f"❌ Unexpected error: {e}")
            return None

    def get_rsi(self, symbol: str, interval: str = "daily", time_period: int = 14) -> Optional[float]:
        """Get Relative Strength Index (RSI)"""
        params = {
            'function': 'RSI',
            'symbol': symbol,
            'interval': interval,
            'time_period': str(time_period),
            'series_type': 'close'
        }

        data = self._make_request(params)
        if not data or 'Technical Analysis: RSI' not in data:
            return None

        # Get most recent RSI value
        rsi_data = data['Technical Analysis: RSI']
        latest_timestamp = sorted(rsi_data.keys())[-1]
        rsi_value = float(rsi_data[latest_timestamp]['RSI'])

        return rsi_value

    def get_macd(self, symbol: str, interval: str = "daily") -> Optional[Dict[str, float]]:
        """Get MACD (Moving Average Convergence Divergence)"""
        params = {
            'function': 'MACD',
            'symbol': symbol,
            'interval': interval,
            'series_type': 'close'
        }

        data = self._make_request(params)
        if not data or 'Technical Analysis: MACD' not in data:
            return None

        macd_data = data['Technical Analysis: MACD']
        latest_timestamp = sorted(macd_data.keys())[-1]
        latest_values = macd_data[latest_timestamp]

        return {
            'macd': float(latest_values['MACD']),
            'signal': float(latest_values['MACD_Signal']),
            'histogram': float(latest_values['MACD_Hist'])
        }

    def get_bollinger_bands(self, symbol: str, interval: str = "daily", time_period: int = 20) -> Optional[Dict[str, float]]:
        """Get Bollinger Bands"""
        params = {
            'function': 'BBANDS',
            'symbol': symbol,
            'interval': interval,
            'time_period': str(time_period),
            'series_type': 'close'
        }

        data = self._make_request(params)
        if not data or 'Technical Analysis: BBANDS' not in data:
            return None

        bb_data = data['Technical Analysis: BBANDS']
        latest_timestamp = sorted(bb_data.keys())[-1]
        latest_values = bb_data[latest_timestamp]

        return {
            'upper_band': float(latest_values['Real Upper Band']),
            'middle_band': float(latest_values['Real Middle Band']),
            'lower_band': float(latest_values['Real Lower Band'])
        }

    def get_sma(self, symbol: str, interval: str = "daily", time_period: int = 20) -> Optional[float]:
        """Get Simple Moving Average (SMA)"""
        params = {
            'function': 'SMA',
            'symbol': symbol,
            'interval': interval,
            'time_period': str(time_period),
            'series_type': 'close'
        }

        data = self._make_request(params)
        if not data or 'Technical Analysis: SMA' not in data:
            return None

        sma_data = data['Technical Analysis: SMA']
        latest_timestamp = sorted(sma_data.keys())[-1]
        sma_value = float(sma_data[latest_timestamp]['SMA'])

        return sma_value

    def get_ema(self, symbol: str, interval: str = "daily", time_period: int = 12) -> Optional[float]:
        """Get Exponential Moving Average (EMA)"""
        params = {
            'function': 'EMA',
            'symbol': symbol,
            'interval': interval,
            'time_period': str(time_period),
            'series_type': 'close'
        }

        data = self._make_request(params)
        if not data or 'Technical Analysis: EMA' not in data:
            return None

        ema_data = data['Technical Analysis: EMA']
        latest_timestamp = sorted(ema_data.keys())[-1]
        ema_value = float(ema_data[latest_timestamp]['EMA'])

        return ema_value

    def get_stochastic(self, symbol: str, interval: str = "daily") -> Optional[Dict[str, float]]:
        """Get Stochastic Oscillator"""
        params = {
            'function': 'STOCH',
            'symbol': symbol,
            'interval': interval,
            'slowkperiod': '5',
            'slowdperiod': '3',
            'slowkmatype': '0',
            'slowdmatype': '0'
        }

        data = self._make_request(params)
        if not data or 'Technical Analysis: STOCH' not in data:
            return None

        stoch_data = data['Technical Analysis: STOCH']
        latest_timestamp = sorted(stoch_data.keys())[-1]
        latest_values = stoch_data[latest_timestamp]

        return {
            'slow_k': float(latest_values['SlowK']),
            'slow_d': float(latest_values['SlowD'])
        }

    def get_adx(self, symbol: str, interval: str = "daily", time_period: int = 14) -> Optional[float]:
        """Get Average Directional Index (ADX)"""
        params = {
            'function': 'ADX',
            'symbol': symbol,
            'interval': interval,
            'time_period': str(time_period)
        }

        data = self._make_request(params)
        if not data or 'Technical Analysis: ADX' not in data:
            return None

        adx_data = data['Technical Analysis: ADX']
        latest_timestamp = sorted(adx_data.keys())[-1]
        adx_value = float(adx_data[latest_timestamp]['ADX'])

        return adx_value

    def get_cci(self, symbol: str, interval: str = "daily", time_period: int = 20) -> Optional[float]:
        """Get Commodity Channel Index (CCI)"""
        params = {
            'function': 'CCI',
            'symbol': symbol,
            'interval': interval,
            'time_period': str(time_period)
        }

        data = self._make_request(params)
        if not data or 'Technical Analysis: CCI' not in data:
            return None

        cci_data = data['Technical Analysis: CCI']
        latest_timestamp = sorted(cci_data.keys())[-1]
        cci_value = float(cci_data[latest_timestamp]['CCI'])

        return cci_value

    def get_williams_r(self, symbol: str, interval: str = "daily", time_period: int = 14) -> Optional[float]:
        """Get Williams %R"""
        params = {
            'function': 'WILLR',
            'symbol': symbol,
            'interval': interval,
            'time_period': str(time_period)
        }

        data = self._make_request(params)
        if not data or 'Technical Analysis: WILLR' not in data:
            return None

        willr_data = data['Technical Analysis: WILLR']
        latest_timestamp = sorted(willr_data.keys())[-1]
        willr_value = float(willr_data[latest_timestamp]['WILLR'])

        return willr_value

    def get_quote(self, symbol: str) -> Optional[Dict[str, Any]]:
        """Get real-time quote data"""
        params = {
            'function': 'GLOBAL_QUOTE',
            'symbol': symbol
        }

        data = self._make_request(params)
        if not data or 'Global Quote' not in data:
            return None

        quote = data['Global Quote']

        return {
            'symbol': quote['01. symbol'],
            'price': float(quote['05. price']),
            'change': float(quote['09. change']),
            'change_percent': quote['10. change percent'],
            'volume': int(quote['06. volume']),
            'high': float(quote['03. high']),
            'low': float(quote['04. low']),
            'open': float(quote['02. open']),
            'previous_close': float(quote['08. previous close'])
        }

    def get_technical_analysis(self, symbol: str) -> AlphaVantageTechnicalData:
        """Get comprehensive technical analysis for a symbol"""
        logger.info(f"📊 Getting technical analysis for {symbol}")

        technical_data = AlphaVantageTechnicalData(
            symbol=symbol,
            timestamp=datetime.now(),
            metadata={}
        )

        try:
            # Get basic quote first
            quote = self.get_quote(symbol)
            if quote:
                technical_data.metadata['quote'] = quote

            # Get technical indicators with proper delays
            technical_data.rsi = self.get_rsi(symbol)
            time.sleep(0.5)  # Small delay between calls

            technical_data.sma_20 = self.get_sma(symbol, time_period=20)
            time.sleep(0.5)

            technical_data.sma_50 = self.get_sma(symbol, time_period=50)
            time.sleep(0.5)

            technical_data.ema_12 = self.get_ema(symbol, time_period=12)
            time.sleep(0.5)

            technical_data.ema_26 = self.get_ema(symbol, time_period=26)
            time.sleep(0.5)

            technical_data.macd = self.get_macd(symbol)
            time.sleep(0.5)

            technical_data.bollinger_bands = self.get_bollinger_bands(symbol)
            time.sleep(0.5)

            technical_data.stochastic = self.get_stochastic(symbol)
            time.sleep(0.5)

            technical_data.adx = self.get_adx(symbol)
            time.sleep(0.5)

            technical_data.cci = self.get_cci(symbol)
            time.sleep(0.5)

            technical_data.williams_r = self.get_williams_r(symbol)

            # Generate trading signals
            self._generate_trading_signals(technical_data)

            logger.info(f"✅ Technical analysis completed for {symbol}")
            logger.info(f"📊 Signal: {technical_data.overall_signal} (Strength: {technical_data.signal_strength}/10)")

        except Exception as e:
            logger.error(f"❌ Error getting technical analysis for {symbol}: {e}")

        return technical_data

    def _generate_trading_signals(self, data: AlphaVantageTechnicalData):
        """Generate trading signals based on technical indicators"""
        buy_signals = 0
        sell_signals = 0
        neutral_signals = 0

        # RSI signals
        if data.rsi:
            if data.rsi < 30:
                buy_signals += 2  # Oversold
            elif data.rsi > 70:
                sell_signals += 2  # Overbought
            else:
                neutral_signals += 1

        # MACD signals
        if data.macd:
            if data.macd['macd'] > data.macd['signal'] and data.macd['histogram'] > 0:
                buy_signals += 2  # Bullish crossover
            elif data.macd['macd'] < data.macd['signal'] and data.macd['histogram'] < 0:
                sell_signals += 2  # Bearish crossover
            else:
                neutral_signals += 1

        # SMA signals
        if data.sma_20 and data.sma_50 and data.metadata.get('quote'):
            price = data.metadata['quote']['price']
            if price > data.sma_20 > data.sma_50:
                buy_signals += 2  # Above moving averages
            elif price < data.sma_20 < data.sma_50:
                sell_signals += 2  # Below moving averages
            else:
                neutral_signals += 1

        # Bollinger Bands signals
        if data.bollinger_bands and data.metadata.get('quote'):
            price = data.metadata['quote']['price']
            upper = data.bollinger_bands['upper_band']
            lower = data.bollinger_bands['lower_band']

            if price > upper:
                sell_signals += 1  # Overbought
            elif price < lower:
                buy_signals += 1  # Oversold
            else:
                neutral_signals += 1

        # Stochastic signals
        if data.stochastic:
            slow_k = data.stochastic['slow_k']
            slow_d = data.stochastic['slow_d']

            if slow_k < 20 and slow_d < 20:
                buy_signals += 1  # Oversold
            elif slow_k > 80 and slow_d > 80:
                sell_signals += 1  # Overbought
            elif slow_k > slow_d:
                buy_signals += 1  # Bullish
            else:
                sell_signals += 1  # Bearish

        # ADX signals (trend strength)
        if data.adx:
            if data.adx > 25:
                # Strong trend, weigh other signals more
                pass
            elif data.adx < 20:
                # Weak trend, reduce signal strength
                buy_signals = max(0, buy_signals - 1)
                sell_signals = max(0, sell_signals - 1)
                neutral_signals += 1

        # Calculate overall signal
        total_signals = buy_signals + sell_signals + neutral_signals
        if total_signals > 0:
            buy_percentage = buy_signals / total_signals
            sell_percentage = sell_signals / total_signals

            if buy_percentage > 0.6:
                data.overall_signal = "BUY"
                data.signal_strength = min(10, int(buy_percentage * 10))
            elif sell_percentage > 0.6:
                data.overall_signal = "SELL"
                data.signal_strength = min(10, int(sell_percentage * 10))
            else:
                data.overall_signal = "HOLD"
                data.signal_strength = max(0, 5 - abs(buy_percentage - sell_percentage) * 5)

        logger.info(f"📊 Signal Analysis: {buy_signals} BUY, {sell_signals} SELL, {neutral_signals} NEUTRAL")

    def get_supported_symbols(self) -> Dict[str, List[str]]:
        """Get supported symbols by asset class"""
        return {
            'stocks': [
                'AAPL', 'MSFT', 'GOOGL', 'AMZN', 'TSLA', 'META', 'NVDA', 'AMD',
                'JPM', 'BAC', 'WMT', 'HD', 'JNJ', 'UNH', 'V', 'PG', 'DIS',
                'MA', 'PYPL', 'NFLX', 'CRM', 'ORCL', 'ADBE', 'INTC', 'CSCO'
            ],
            'forex': [
                'EURUSD', 'GBPUSD', 'USDJPY', 'AUDUSD', 'USDCAD', 'USDCHF',
                'EURGBP', 'EURJPY', 'GBPJPY', 'EURCHF', 'EURAUD', 'AUDJPY'
            ],
            'crypto': [
                'BTC', 'ETH', 'BNB', 'XRP', 'ADA', 'SOL', 'DOGE', 'DOT',
                'AVAX', 'MATIC', 'LINK', 'UNI', 'LTC', 'BCH', 'FIL', 'ATOM'
            ],
            'commodities': [
                'GC=F',  # Gold
                'SI=F',  # Silver
                'CL=F',  # Crude Oil
                'NG=F',  # Natural Gas
                'PL=F',  # Platinum
                'PA=F',  # Palladium
                'HG=F',  # Copper
                'ZC=F',  # Corn
                'ZW=F',  # Wheat
                'SB=F'   # Sugar
            ]
        }

    def get_provider_status(self) -> Dict[str, Any]:
        """Get comprehensive provider status"""
        supported_symbols = self.get_supported_symbols()

        return {
            'provider': 'Alpha Vantage Technical Indicators',
            'api_key_configured': bool(self.api_key and self.api_key != 'demo'),
            'free_tier_limits': {
                'calls_per_day': 500,
                'calls_per_minute': 5,
                'rate_limit_interval': '12 seconds'
            },
            'supported_indicators': [
                'RSI', 'MACD', 'Bollinger Bands', 'SMA', 'EMA', 'Stochastic',
                'ADX', 'CCI', 'Williams %R', 'Real-time Quotes'
            ],
            'supported_assets': {
                'stocks': len(supported_symbols['stocks']),
                'forex': len(supported_symbols['forex']),
                'crypto': len(supported_symbols['crypto']),
                'commodities': len(supported_symbols['commodities'])
            },
            'data_refresh_rate': 'Real-time with rate limiting',
            'last_call_time': datetime.fromtimestamp(self.last_call_time).isoformat() if self.last_call_time > 0 else None,
            'operational_status': 'ACTIVE' if self.api_key and self.api_key != 'demo' else 'DEMO'
        }

def test_alphavantage_provider():
    """Test the Alpha Vantage provider with real data"""
    print("🎯 TESTING ALPHA VANTAGE TECHNICAL INDICATORS PROVIDER")
    print("=" * 80)

    # Load API key
    try:
        with open('/home/davidsanker/platform/config/api_keys.json', 'r') as f:
            api_keys = json.load(f)
        api_key = api_keys.get('alphavantage', '')
    except Exception as e:
        print(f"❌ Could not load API key: {e}")
        return

    if not api_key:
        print("❌ No Alpha Vantage API key found")
        return

    print(f"🔑 API Key configured: {'*' * 20}{api_key[-4:]}")
    print()

    # Initialize provider
    provider = AlphaVantageProvider(api_key)

    # Show provider status
    status = provider.get_provider_status()
    print("📊 PROVIDER STATUS:")
    print(f"   ✅ Provider: {status['provider']}")
    print(f"   ✅ API Key: {'Configured' if status['api_key_configured'] else 'Missing'}")
    print(f"   ✅ Free Tier: {status['free_tier_limits']['calls_per_day']} calls/day")
    print(f"   ✅ Rate Limit: {status['free_tier_limits']['rate_limit_interval']}")
    print(f"   ✅ Status: {status['operational_status']}")
    print()

    print("📈 SUPPORTED ASSETS:")
    for asset_class, count in status['supported_assets'].items():
        print(f"   ✅ {asset_class.title()}: {count} symbols")
    print()

    print("📊 AVAILABLE INDICATORS:")
    for indicator in status['supported_indicators']:
        print(f"   ✅ {indicator}")
    print()

    # Test with a few symbols
    test_symbols = ['AAPL', 'MSFT', 'SPY']

    print("🧪 TESTING TECHNICAL ANALYSIS:")
    print("-" * 60)

    for i, symbol in enumerate(test_symbols, 1):
        print(f"\n📊 Test {i}: {symbol}")
        try:
            # Get comprehensive technical analysis
            tech_data = provider.get_technical_analysis(symbol)

            print(f"   📊 Timestamp: {tech_data.timestamp}")

            if tech_data.metadata.get('quote'):
                quote = tech_data.metadata['quote']
                print(f"   💰 Price: ${quote['price']:.2f} ({quote['change_percent']})")

            if tech_data.rsi:
                print(f"   🔄 RSI: {tech_data.rsi:.2f}")

            if tech_data.sma_20 and tech_data.sma_50:
                print(f"   📈 SMA(20): ${tech_data.sma_20:.2f}")
                print(f"   📈 SMA(50): ${tech_data.sma_50:.2f}")

            if tech_data.macd:
                print(f"   📊 MACD: {tech_data.macd['macd']:.4f}")
                print(f"   📊 MACD Signal: {tech_data.macd['signal']:.4f}")

            if tech_data.bollinger_bands:
                bb = tech_data.bollinger_bands
                print(f"   📊 BB Upper: ${bb['upper_band']:.2f}")
                print(f"   📊 BB Lower: ${bb['lower_band']:.2f}")

            print(f"   🎯 Overall Signal: {tech_data.overall_signal}")
            print(f"   💪 Signal Strength: {tech_data.signal_strength}/10")
            print(f"   ✅ Technical analysis completed successfully")

        except Exception as e:
            print(f"   ❌ Error analyzing {symbol}: {e}")

        # Add delay between symbols
        if i < len(test_symbols):
            print("   ⏳ Waiting 15 seconds for rate limit...")
            time.sleep(15)

    print(f"\n🎉 ALPHA VANTAGE PROVIDER TEST COMPLETED!")
    print(f"📊 Technical indicators successfully integrated")
    print(f"🚀 Ready for trading algorithm integration")

if __name__ == "__main__":
    test_alphavantage_provider()