#!/usr/bin/env python3
"""
Alpha Vantage Provider for Technical Indicators
Provides RSI, MACD, Bollinger Bands, and other technical indicators
"""

import requests
import logging
import json
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
from dataclasses import dataclass

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@dataclass
class TechnicalIndicators:
    """Technical indicators data"""
    symbol: str
    timestamp: datetime
    
    # Individual indicators
    rsi: float  # Relative Strength Index
    macd: float  # MACD
    macd_signal: float  # MACD Signal
    bollinger_upper: float  # Bollinger Bands Upper
    bollinger_middle: float  # Bollinger Bands Middle
    bollinger_lower: float  # Bollinger Bands Lower
    stochastic_k: float  # Stochastic %K
    stochastic_d: float  # Stochastic %D
    atr: float  # Average True Range
    
    # Combined signal
    signal: float  # -1 to 1
    confidence: float  # 0 to 1
    reasoning: List[str]

class AlphaVantageProvider:
    """Alpha Vantage provider for technical indicators"""
    
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.base_url = "https://www.alphavantage.co/query"
        self.session = requests.Session()
        
        # Cache to avoid hitting API limits (25 requests/day)
        self.cache = {}
        self.cache_duration = timedelta(hours=6)  # Cache for 6 hours
        
        logger.info("✅ Alpha Vantage Provider initialized")
    
    def get_technical_indicators(self, symbol: str) -> Optional[TechnicalIndicators]:
        """
        Get comprehensive technical indicators for a symbol
        Returns: TechnicalIndicators object with all indicators and combined signal
        """
        try:
            logger.info(f"📊 Getting Alpha Vantage technical indicators for {symbol}...")
            
            # Check cache first
            cache_key = f"av_{symbol}"
            if cache_key in self.cache:
                cached_data, cached_time = self.cache[cache_key]
                if datetime.now() - cached_time < self.cache_duration:
                    logger.info(f"   ✅ Using cached data for {symbol}")
                    return cached_data
            
            # Get RSI
            rsi = self._get_rsi(symbol)
            
            # Get MACD
            macd_data = self._get_macd(symbol)
            
            # Get Bollinger Bands
            bb_data = self._get_bollinger_bands(symbol)
            
            # Get Stochastic
            stoch_data = self._get_stochastic(symbol)
            
            # Get ATR
            atr = self._get_atr(symbol)
            
            # Calculate combined signal
            signal, reasoning = self._calculate_signal(rsi, macd_data, bb_data, stoch_data)
            
            # Calculate confidence based on indicator agreement
            confidence = self._calculate_confidence(rsi, macd_data, bb_data, stoch_data)
            
            indicators = TechnicalIndicators(
                symbol=symbol,
                timestamp=datetime.now(),
                rsi=rsi,
                macd=macd_data.get('macd', 0),
                macd_signal=macd_data.get('signal', 0),
                bollinger_upper=bb_data.get('upper', 0),
                bollinger_middle=bb_data.get('middle', 0),
                bollinger_lower=bb_data.get('lower', 0),
                stochastic_k=stoch_data.get('k', 0),
                stochastic_d=stoch_data.get('d', 0),
                atr=atr,
                signal=signal,
                confidence=confidence,
                reasoning=reasoning
            )
            
            # Cache the result
            self.cache[cache_key] = (indicators, datetime.now())
            
            logger.info(f"   ✅ Alpha Vantage signal: {signal:+.2f} (confidence: {confidence:.2f})")
            
            return indicators
            
        except Exception as e:
            logger.error(f"❌ Error getting Alpha Vantage indicators for {symbol}: {e}")
            return None
    
    def _get_rsi(self, symbol: str, time_period: int = 14) -> float:
        """Get RSI indicator"""
        try:
            params = {
                'function': 'RSI',
                'symbol': symbol,
                'interval': 'daily',
                'time_period': str(time_period),
                'series_type': 'close',
                'apikey': self.api_key
            }
            
            response = self.session.get(self.base_url, params=params, timeout=10)
            response.raise_for_status()
            data = response.json()
            
            if 'Technical Analysis: RSI' in data:
                rsi_values = data['Technical Analysis: RSI']
                latest_rsi = float(list(rsi_values.values())[0]['RSI'])
                return latest_rsi
            else:
                logger.warning(f"   ⚠️ No RSI data for {symbol}")
                return 50.0  # Neutral RSI
                
        except Exception as e:
            logger.error(f"   ❌ Error getting RSI: {e}")
            return 50.0
    
    def _get_macd(self, symbol: str) -> Dict[str, float]:
        """Get MACD indicator"""
        try:
            params = {
                'function': 'MACD',
                'symbol': symbol,
                'interval': 'daily',
                'series_type': 'close',
                'apikey': self.api_key
            }
            
            response = self.session.get(self.base_url, params=params, timeout=10)
            response.raise_for_status()
            data = response.json()
            
            if 'Technical Analysis: MACD' in data:
                macd_values = data['Technical Analysis: MACD']
                latest = list(macd_values.values())[0]
                return {
                    'macd': float(latest.get('MACD', 0)),
                    'signal': float(latest.get('MACD_Signal', 0)),
                    'hist': float(latest.get('MACD_Hist', 0))
                }
            else:
                logger.warning(f"   ⚠️ No MACD data for {symbol}")
                return {'macd': 0, 'signal': 0, 'hist': 0}
                
        except Exception as e:
            logger.error(f"   ❌ Error getting MACD: {e}")
            return {'macd': 0, 'signal': 0, 'hist': 0}
    
    def _get_bollinger_bands(self, symbol: str, time_period: int = 20) -> Dict[str, float]:
        """Get Bollinger Bands"""
        try:
            params = {
                'function': 'BBANDS',
                'symbol': symbol,
                'interval': 'daily',
                'time_period': str(time_period),
                'series_type': 'close',
                'nbdevup': '3',
                'nbdevdn': '3',
                'apikey': self.api_key
            }
            
            response = self.session.get(self.base_url, params=params, timeout=10)
            response.raise_for_status()
            data = response.json()
            
            if 'Technical Analysis: BBANDS' in data:
                bb_values = data['Technical Analysis: BBANDS']
                latest = list(bb_values.values())[0]
                return {
                    'upper': float(latest.get('Real Upper Band', 0)),
                    'middle': float(latest.get('Real Middle Band', 0)),
                    'lower': float(latest.get('Real Lower Band', 0))
                }
            else:
                logger.warning(f"   ⚠️ No Bollinger Bands data for {symbol}")
                return {'upper': 0, 'middle': 0, 'lower': 0}
                
        except Exception as e:
            logger.error(f"   ❌ Error getting Bollinger Bands: {e}")
            return {'upper': 0, 'middle': 0, 'lower': 0}
    
    def _get_stochastic(self, symbol: str) -> Dict[str, float]:
        """Get Stochastic Oscillator"""
        try:
            params = {
                'function': 'STOCH',
                'symbol': symbol,
                'interval': 'daily',
                'apikey': self.api_key
            }
            
            response = self.session.get(self.base_url, params=params, timeout=10)
            response.raise_for_status()
            data = response.json()
            
            if 'Technical Analysis: STOCH' in data:
                stoch_values = data['Technical Analysis: STOCH']
                latest = list(stoch_values.values())[0]
                return {
                    'k': float(latest.get('SlowK', 50)),
                    'd': float(latest.get('SlowD', 50))
                }
            else:
                logger.warning(f"   ⚠️ No Stochastic data for {symbol}")
                return {'k': 50, 'd': 50}
                
        except Exception as e:
            logger.error(f"   ❌ Error getting Stochastic: {e}")
            return {'k': 50, 'd': 50}
    
    def _get_atr(self, symbol: str, time_period: int = 14) -> float:
        """Get Average True Range"""
        try:
            params = {
                'function': 'ATR',
                'symbol': symbol,
                'interval': 'daily',
                'time_period': str(time_period),
                'apikey': self.api_key
            }
            
            response = self.session.get(self.base_url, params=params, timeout=10)
            response.raise_for_status()
            data = response.json()
            
            if 'Technical Analysis: ATR' in data:
                atr_values = data['Technical Analysis: ATR']
                latest_atr = float(list(atr_values.values())[0]['ATR'])
                return latest_atr
            else:
                logger.warning(f"   ⚠️ No ATR data for {symbol}")
                return 0.0
                
        except Exception as e:
            logger.error(f"   ❌ Error getting ATR: {e}")
            return 0.0
    
    def _calculate_signal(self, rsi: float, macd_data: Dict, 
                         bb_data: Dict, stoch_data: Dict) -> tuple:
        """
        Calculate combined technical signal
        Returns: (signal_score, reasoning_list)
        """
        signal = 0.0
        reasoning = []
        
        # RSI Signal (30% weight)
        if rsi < 30:
            # Oversold = bullish
            rsi_signal = (30 - rsi) / 30.0  # 0 to 1
            signal += rsi_signal * 0.30
            reasoning.append(f"RSI {rsi:.1f} oversold (bullish)")
        elif rsi > 70:
            # Overbought = bearish
            rsi_signal = (70 - rsi) / 30.0  # -1 to 0
            signal += rsi_signal * 0.30
            reasoning.append(f"RSI {rsi:.1f} overbought (bearish)")
        else:
            reasoning.append(f"RSI {rsi:.1f} neutral")
        
        # MACD Signal (30% weight)
        macd = macd_data.get('macd', 0)
        macd_signal = macd_data.get('signal', 0)
        if macd > macd_signal:
            # MACD above signal = bullish
            signal += 0.30
            reasoning.append("MACD bullish (above signal)")
        else:
            # MACD below signal = bearish
            signal -= 0.30
            reasoning.append("MACD bearish (below signal)")
        
        # Stochastic Signal (20% weight)
        stoch_k = stoch_data.get('k', 50)
        if stoch_k < 20:
            # Oversold = bullish
            stoch_signal = (20 - stoch_k) / 20.0
            signal += stoch_signal * 0.20
            reasoning.append(f"Stochastic {stoch_k:.1f} oversold")
        elif stoch_k > 80:
            # Overbought = bearish
            stoch_signal = (80 - stoch_k) / 20.0
            signal += stoch_signal * 0.20
            reasoning.append(f"Stochastic {stoch_k:.1f} overbought")
        else:
            reasoning.append(f"Stochastic {stoch_k:.1f} neutral")
        
        # Bollinger Bands Signal (20% weight)
        bb_middle = bb_data.get('middle', 0)
        bb_upper = bb_data.get('upper', 0)
        bb_lower = bb_data.get('lower', 0)
        
        if bb_lower > 0 and bb_upper > 0:
            bb_width = bb_upper - bb_lower
            if bb_width > 0:
                # Calculate position within bands (this would need current price)
                # For now, use neutral
                reasoning.append("Bollinger Bands neutral")
        
        # Clamp signal to [-1, 1]
        signal = max(-1.0, min(1.0, signal))
        
        return signal, reasoning
    
    def _calculate_confidence(self, rsi: float, macd_data: Dict,
                            bb_data: Dict, stoch_data: Dict) -> float:
        """Calculate confidence based on indicator agreement"""
        agreement_count = 0
        total_indicators = 0
        
        # RSI extreme?
        if rsi < 30 or rsi > 70:
            agreement_count += 1
        total_indicators += 1
        
        # MACD divergence?
        macd = macd_data.get('macd', 0)
        macd_signal = macd_data.get('signal', 0)
        if abs(macd - macd_signal) > 0.5:
            agreement_count += 1
        total_indicators += 1
        
        # Stochastic extreme?
        stoch_k = stoch_data.get('k', 50)
        if stoch_k < 20 or stoch_k > 80:
            agreement_count += 1
        total_indicators += 1
        
        # Calculate confidence
        if total_indicators > 0:
            confidence = agreement_count / total_indicators
            return max(0.3, min(0.95, confidence))
        else:
            return 0.5


# Test function
if __name__ == "__main__":
    import sys
    
    # Test with provided API key
    api_key = os.environ.get('ALPHAVANTAGE_API_KEY', '')
    
    provider = AlphaVantageProvider(api_key)
    
    # Test with a few symbols
    test_symbols = ['AAPL', 'MSFT', 'GOOGL']
    
    for symbol in test_symbols:
        print(f"\n{'='*60}")
        print(f"Testing {symbol}")
        print('='*60)
        
        indicators = provider.get_technical_indicators(symbol)
        
        if indicators:
            print(f"RSI: {indicators.rsi:.2f}")
            print(f"MACD: {indicators.macd:.2f}")
            print(f"Signal: {indicators.signal:+.2f}")
            print(f"Confidence: {indicators.confidence:.2f}")
            print(f"Reasoning: {', '.join(indicators.reasoning)}")
        else:
            print("Failed to get indicators")
        
        # Sleep to respect API rate limits
        import time
        time.sleep(12)  # Alpha Vantage free tier: 5 requests/minute
