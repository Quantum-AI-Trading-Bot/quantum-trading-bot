#!/usr/bin/env python3
"""
Multi-Source Data Manager for Quantum AI Trading Bot
Integrates FRED, NewsAPI, Reddit, and other sources for enhanced trading decisions
"""

import logging
import json
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
from dataclasses import dataclass
import sys
import os

# Add platform path
sys.path.append('/home/davidsanker/platform')

# Import existing providers
from data.fred_provider import FREDDataProvider
from data.newsapi_provider import NewsAPIProvider
from data.alpha_vantage_provider import AlphaVantageProvider

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

@dataclass
class MultiSourceSignal:
    """Combined signal from multiple data sources"""
    symbol: str
    timestamp: datetime

    # Source-specific signals
    economic_signal: float  # From FRED
    news_sentiment: float   # From NewsAPI
    social_sentiment: float  # From Reddit/Twitter
    technical_signal: float  # From Alpha Vantage

    # Combined metrics
    overall_sentiment: float  # -1 to 1
    confidence: float         # 0 to 1
    data_sources_used: List[str]

    # Additional context
    economic_indicators: Dict[str, float]
    top_headlines: List[str]
    technical_indicators: Dict[str, float]
    reasoning: List[str]

class MultiSourceDataManager:
    """
    Manages multiple data sources and provides unified signals
    """

    def __init__(self):
        # API Keys (from your existing code)
        self.api_keys = {
            'fred': os.environ.get('NEWSAPI_KEY', ''),
            'newsapi': os.environ.get('NEWSAPI_KEY', ''),
            'alphavantage': os.environ.get('ALPHAVANTAGE_API_KEY', '')
        }

        # Initialize providers
        self.fred_provider = FREDDataProvider(self.api_keys['fred'])
        self.newsapi_provider = NewsAPIProvider(self.api_keys['newsapi'])
        self.alpha_vantage_provider = AlphaVantageProvider(self.api_keys['alphavantage'])

        # Cache for data (to avoid API rate limits)
        self.cache = {}
        self.cache_duration = timedelta(hours=4)  # Increased to avoid NewsAPI rate limits (100/day)

        # Performance tracking
        self.metrics = {
            'requests_made': 0,
            'cache_hits': 0,
            'errors': 0,
            'sources_used': {}
        }

        logger.info("✅ Multi-Source Data Manager initialized")
        logger.info(f"   Available sources: FRED, NewsAPI, AlphaVantage")

    def get_comprehensive_signal(self, symbol: str) -> MultiSourceSignal:
        """
        Get comprehensive trading signal from all available sources
        """
        try:
            logger.info(f"📊 Gathering multi-source data for {symbol}...")

            timestamp = datetime.now()

            # Initialize signal components
            economic_signal = 0.0
            news_sentiment = 0.0
            social_sentiment = 0.0
            technical_signal = 0.0

            economic_indicators = {}
            top_headlines = []
            technical_indicators = {}
            data_sources_used = []
            reasoning = []

            # 1. Get FRED Economic Data
            try:
                econ_data = self._get_fred_economic_data()
                if econ_data:
                    economic_signal = econ_data['signal']
                    economic_indicators = econ_data['indicators']
                    data_sources_used.append('FRED')
                    reasoning.extend(econ_data['reasoning'])
                    logger.info(f"   ✅ FRED: Economic signal = {economic_signal:.3f}")
            except Exception as e:
                logger.error(f"   ❌ FRED error: {e}")

            # 2. Get NewsAPI Sentiment
            try:
                news_data = self._get_news_sentiment(symbol)
                if news_data:
                    news_sentiment = news_data['sentiment_score']
                    top_headlines = news_data.get('top_headlines', [])
                    data_sources_used.append('NewsAPI')
                    reasoning.append(f"News sentiment: {news_sentiment:.2f}")
                    logger.info(f"   ✅ NewsAPI: Sentiment = {news_sentiment:.3f}")
            except Exception as e:
                logger.error(f"   ❌ NewsAPI error: {e}")

            # 3. Get Alpha Vantage Technical Indicators (NEW!)
            try:
                tech_data = self.alpha_vantage_provider.get_technical_indicators(symbol)
                if tech_data:
                    technical_signal = tech_data.signal
                    technical_indicators = {
                        'RSI': tech_data.rsi,
                        'MACD': tech_data.macd,
                        'Signal': tech_data.signal,
                        'Confidence': tech_data.confidence
                    }
                    data_sources_used.append('AlphaVantage')
                    reasoning.extend(tech_data.reasoning)
                    logger.info(f"   ✅ AlphaVantage: Technical signal = {technical_signal:.3f}")
            except Exception as e:
                logger.error(f"   ❌ AlphaVantage error: {e}")

            # 4. Calculate combined sentiment
            weights = {
                'economic': 0.25,   # Economic indicators
                'news': 0.40,        # News sentiment (primary driver)
                'social': 0.10,      # Social sentiment (secondary)
                'technical': 0.25    # Technical indicators (NEW!)
            }

            # Weighted combination
            overall_sentiment = (
                economic_signal * weights['economic'] +
                news_sentiment * weights['news'] +
                social_sentiment * weights['social'] +
                technical_signal * weights['technical']
            )

            # Confidence based on number of sources (now max 4 sources)
            confidence = min(len(data_sources_used) * 0.30, 0.95)

            # Create signal
            signal = MultiSourceSignal(
                symbol=symbol,
                timestamp=timestamp,
                economic_signal=economic_signal,
                news_sentiment=news_sentiment,
                social_sentiment=social_sentiment,
                technical_signal=technical_signal,
                overall_sentiment=overall_sentiment,
                confidence=confidence,
                data_sources_used=data_sources_used,
                economic_indicators=economic_indicators,
                top_headlines=top_headlines,
                technical_indicators=technical_indicators,
                reasoning=reasoning
            )

            # Update metrics
            self.metrics['requests_made'] += 1
            for source in data_sources_used:
                self.metrics['sources_used'][source] = self.metrics['sources_used'].get(source, 0) + 1

            logger.info(f"   📊 Overall sentiment: {overall_sentiment:.3f} (confidence: {confidence:.2f})")
            logger.info(f"   🔗 Sources used: {', '.join(data_sources_used)}")

            return signal

        except Exception as e:
            logger.error(f"❌ Error getting comprehensive signal for {symbol}: {e}")
            # Return neutral signal on error
            return MultiSourceSignal(
                symbol=symbol,
                timestamp=datetime.now(),
                economic_signal=0.0,
                news_sentiment=0.0,
                social_sentiment=0.0,
                technical_signal=0.0,
                overall_sentiment=0.0,
                confidence=0.0,
                data_sources_used=[],
                economic_indicators={},
                top_headlines=[],
                technical_indicators={},
                reasoning=["Error fetching multi-source data"]
            )

    def _get_fred_economic_data(self) -> Optional[Dict]:
        """Get economic indicators from FRED"""
        try:
            # Key economic indicators
            indicators = {
                'DFF': 'Federal Funds Rate',
                'DGS10': '10-Year Treasury',
                'UNRATE': 'Unemployment Rate',
                'CPIAUCSL': 'CPI (Inflation)',
                'GDP': 'GDP'
            }

            data = {}
            signal = 0.0
            reasoning = []

            for series_id, name in indicators.items():
                try:
                    value = self.fred_provider.get_series(series_id)
                    if value is not None:
                        data[name] = value

                        # Simple signal logic
                        if series_id == 'DFF':  # Fed Funds Rate
                            if value < 3.0:
                                signal += 0.2  # Low rates = bullish
                                reasoning.append(f"Low Fed rate ({value:.2f}%) supports growth")
                            elif value > 4.5:
                                signal -= 0.2  # High rates = bearish
                                reasoning.append(f"High Fed rate ({value:.2f}%) restricts growth")

                        elif series_id == 'UNRATE':  # Unemployment
                            if value < 4.0:
                                signal += 0.15  # Low unemployment = bullish
                                reasoning.append(f"Low unemployment ({value:.1f}%) indicates strength")
                            elif value > 5.0:
                                signal -= 0.15  # High unemployment = bearish
                                reasoning.append(f"High unemployment ({value:.1f}%) signals weakness")

                        elif series_id == 'DGS10':  # 10-Year Treasury
                            if value < 3.5:
                                signal += 0.1
                                reasoning.append(f"Low 10Y yield ({value:.2f}%) supports equities")

                except Exception as e:
                    logger.debug(f"Error getting {series_id}: {e}")

            return {
                'signal': max(min(signal, 1.0), -1.0),
                'indicators': data,
                'reasoning': reasoning
            }

        except Exception as e:
            logger.error(f"Error getting FRED data: {e}")
            return None

    def _get_news_sentiment(self, symbol: str) -> Optional[Dict]:
        """Get news sentiment from NewsAPI"""
        try:
            # Check cache first
            cache_key = f"news_{symbol}"
            if cache_key in self.cache:
                cached_data, cached_time = self.cache[cache_key]
                if datetime.now() - cached_time < self.cache_duration:
                    self.metrics['cache_hits'] += 1
                    return cached_data

            # Fetch fresh data
            news_data = self.newsapi_provider.get_symbol_sentiment(symbol)

            if news_data:
                # Cache the result
                self.cache[cache_key] = (news_data, datetime.now())
                return news_data

            return None

        except Exception as e:
            logger.error(f"Error getting news sentiment for {symbol}: {e}")
            return None

    def get_metrics(self) -> Dict[str, Any]:
        """Get performance metrics"""
        return {
            'total_requests': self.metrics['requests_made'],
            'cache_hits': self.metrics['cache_hits'],
            'cache_hit_rate': (
                self.metrics['cache_hits'] / self.metrics['requests_made']
                if self.metrics['requests_made'] > 0 else 0
            ),
            'errors': self.metrics['errors'],
            'sources_usage': self.metrics['sources_used']
        }

# Singleton instance
_manager_instance = None

def get_multi_source_manager() -> MultiSourceDataManager:
    """Get or create the singleton instance"""
    global _manager_instance
    if _manager_instance is None:
        _manager_instance = MultiSourceDataManager()
    return _manager_instance

# Test function
def test_multi_source_integration():
    """Test the multi-source data integration"""
    print("🧪 Testing Multi-Source Data Integration")
    print("=" * 60)

    manager = get_multi_source_manager()

    # Test symbols
    test_symbols = ['AAPL', 'TSLA', 'NVDA']

    for symbol in test_symbols:
        print(f"\n🔍 Analyzing {symbol}...")
        signal = manager.get_comprehensive_signal(symbol)

        print(f"   Overall Sentiment: {signal.overall_sentiment:.3f}")
        print(f"   Confidence: {signal.confidence:.2f}")
        print(f"   Sources: {', '.join(signal.data_sources_used)}")

        if signal.economic_indicators:
            print(f"   Economic Indicators:")
            for name, value in signal.economic_indicators.items():
                print(f"      {name}: {value}")

        if signal.top_headlines:
            print(f"   Top Headlines:")
            for headline in signal.top_headlines[:3]:
                print(f"      • {headline}")

        if signal.reasoning:
            print(f"   Key Factors:")
            for reason in signal.reasoning[:3]:
                print(f"      • {reason}")

    # Show metrics
    metrics = manager.get_metrics()
    print(f"\n📊 Performance Metrics:")
    print(f"   Total Requests: {metrics['total_requests']}")
    print(f"   Cache Hit Rate: {metrics['cache_hit_rate']:.1%}")
    print(f"   Errors: {metrics['errors']}")
    print(f"   Source Usage: {metrics['sources_usage']}")

    print("\n✅ Multi-Source Integration Test Complete!")

if __name__ == "__main__":
    test_multi_source_integration()
