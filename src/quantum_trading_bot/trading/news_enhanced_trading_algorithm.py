#!/usr/bin/env python3
"""
News-Enhanced Quantum Trading Algorithm
Integrates NewsAPI and FRED data into your existing trading system
"""

import asyncio
import sys
import json
import numpy as np
import pandas as pd
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass
from collections import defaultdict
import logging

# Add platform to path
sys.path.append('/home/davidsanker/platform')

# Import our data sources
from data.alternative_data import AlternativeDataSource
from data.sentiment_analysis import SentimentDataSource
from data.multi_modal_fusion import QuantumDataFusion
from data.enhanced_context_composer import EnhancedQuantumContextComposer

# Import existing trading components
try:
    from ib_insync import IB, Stock, Forex, Future, Option
    from ib_insync.util import startLoop
    IB_AVAILABLE = True
except ImportError:
    IB_AVAILABLE = False
    print("Warning: ib_insync not available, using simulation mode")

@dataclass
class TradingSignal:
    """Enhanced trading signal with news and economic context"""
    symbol: str
    signal_type: str  # 'BUY', 'SELL', 'HOLD'
    strength: float  # 0.0 to 1.0
    confidence: float  # 0.0 to 1.0
    position_size: float  # 0.0 to 1.0 (percentage of portfolio)
    price: float
    economic_context: Dict[str, Any]
    news_context: Dict[str, Any]
    quantum_fusion_score: float
    risk_adjustment: float
    timestamp: datetime
    reasoning: List[str]
    stop_loss: Optional[float] = None
    take_profit: Optional[float] = None
    time_horizon: str = "medium"  # 'short', 'medium', 'long'

class EconomicCalendarAlerts:
    """Economic calendar and news event alert system"""

    def __init__(self):
        self.alerts = []
        self.high_impact_events = [
            'FOMC Meeting', 'Federal Reserve', 'GDP Release',
            'CPI Release', 'Unemployment Rate', 'Non-Farm Payrolls',
            'Earnings Report', 'Interest Rate Decision'
        ]
        self.logger = logging.getLogger(__name__)

    def check_fred_release_schedule(self, fred_data: Dict) -> List[Dict]:
        """Check for upcoming economic data releases"""
        alerts = []
        current_time = datetime.now(timezone.utc)

        # Known FRED release schedules (approximate)
        release_schedule = {
            'GDP': {'day_of_month': [25, 26, 27], 'hour': 8, 'impact': 'high'},
            'UNRATE': {'day_of_month': range(1, 8), 'hour': 8, 'impact': 'high'},
            'CPIAUCSL': {'day_of_month': range(10, 15), 'hour': 8, 'impact': 'high'},
            'DGS10': {'frequency': 'daily', 'hour': 9, 'impact': 'medium'},
            'DFF': {'frequency': 'as_needed', 'hour': 14, 'impact': 'high'}
        }

        for series_id, data in fred_data.items():
            if isinstance(data, dict) and data:
                latest_date = data.get('latest_value', {}).get('date')
                if latest_date:
                    latest_dt = datetime.fromisoformat(latest_date.replace('Z', '+00:00'))
                    age_hours = (current_time - latest_dt).total_seconds() / 3600

                    # Alert if data is stale (might indicate upcoming release)
                    if series_id in release_schedule:
                        schedule = release_schedule[series_id]
                        if age_hours > 24:  # Data more than 1 day old
                            alert = {
                                'type': 'economic_data_due',
                                'series': series_id,
                                'hours_old': age_hours,
                                'impact': schedule.get('impact', 'medium'),
                                'message': f"{series_id} data {age_hours:.0f} hours old - upcoming release expected"
                            }
                            alerts.append(alert)

        return alerts

    def generate_news_alerts(self, news_data: Dict) -> List[Dict]:
        """Generate alerts based on news sentiment and volume"""
        alerts = []
        sentiment_score = news_data.get('sentiment_score', 0)
        volume = news_data.get('sentiment_volume', 0)
        volatility = news_data.get('sentiment_volatility', 0)

        # High sentiment alert
        if abs(sentiment_score) > 0.3:
            direction = "BULLISH" if sentiment_score > 0 else "BEARISH"
            alert = {
                'type': 'high_sentiment',
                'direction': direction,
                'strength': abs(sentiment_score),
                'message': f"Strong {direction.lower()} news sentiment detected: {sentiment_score:+.3f}"
            }
            alerts.append(alert)

        # High volume alert
        if volume > 1000:
            alert = {
                'type': 'high_volume',
                'volume': volume,
                'message': f"High news volume: {volume:,} mentions - increased volatility likely"
            }
            alerts.append(alert)

        # High volatility alert
        if volatility > 0.5:
            alert = {
                'type': 'high_volatility',
                'volatility': volatility,
                'message': f"News sentiment volatility: {volatility:.3f} - expect price swings"
            }
            alerts.append(alert)

        return alerts

    def check_time_based_alerts(self) -> List[Dict]:
        """Check for time-based trading alerts"""
        alerts = []
        current_time = datetime.now(timezone.utc)
        hour = current_time.hour
        day_of_week = current_time.weekday()

        # Market opening/closing alerts
        if hour == 13 and day_of_week < 5:  # 9:30 AM EST
            alerts.append({
                'type': 'market_open',
                'message': 'US Market Opening - Increased volume expected'
            })

        if hour == 21 and day_of_week < 5:  # 4:00 PM EST
            alerts.append({
                'type': 'market_close',
                'message': 'US Market Closing - Position adjustment recommended'
            })

        # Fed meeting schedule (simplified - first Wednesday every 6 weeks)
        if day_of_week == 2 and 13 <= hour <= 15:  # Wednesday 1-3 PM EST
            if current_time.day <= 7:  # First week of month
                alerts.append({
                    'type': 'fed_meeting_risk',
                    'message': 'FOMC Meeting Period - Higher market volatility expected',
                    'impact': 'high'
                })

        return alerts

class NewsEnhancedTradingAlgorithm:
    """Main trading algorithm enhanced with news and economic data"""

    def __init__(self, api_keys: Dict[str, str] = None):
        self.api_keys = api_keys or {
            'fred': '201b04c0f88811426821264baa8444c5',
            'newsapi': '35fcde3a2edd4d979a22f4ea42b2c8b8'
        }

        self.logger = logging.getLogger(__name__)
        self.alt_source = None
        self.sentiment_source = None
        self.fusion_engine = None
        self.context_composer = None
        self.calendar_alerts = EconomicCalendarAlerts()

        # Trading parameters
        self.position_limits = {
            'max_single_position': 0.2,  # 20% max per position
            'max_total_exposure': 0.8,    # 80% max total exposure
            'risk_multiplier': 1.5       # Risk adjustment multiplier
        }

        # Performance tracking
        self.signals_generated = []
        self.alert_history = []
        self.performance_metrics = {
            'signals_generated': 0,
            'alerts_triggered': 0,
            'avg_confidence': 0.0,
            'economic_adjustments': 0
        }

    async def initialize(self):
        """Initialize all data sources"""
        try:
            self.logger.info("Initializing News-Enhanced Trading Algorithm...")

            # Initialize data sources
            self.alt_source = AlternativeDataSource(self.api_keys)
            self.sentiment_source = SentimentDataSource()
            self.fusion_engine = QuantumDataFusion(self.api_keys)
            self.context_composer = EnhancedQuantumContextComposer(self.api_keys)

            await asyncio.gather(
                self.alt_source.initialize(),
                self.sentiment_source.initialize(),
                self.fusion_engine.initialize(),
                self.context_composer.initialize()
            )

            self.logger.info("✅ News-Enhanced Trading Algorithm initialized successfully")
            return True

        except Exception as e:
            self.logger.error(f"Initialization failed: {e}")
            return False

    async def generate_trading_signal(self, symbol: str, current_price: float = None) -> TradingSignal:
        """Generate enhanced trading signal with news and economic context"""
        try:
            # Collect all data sources
            tasks = [
                self.alt_source.get_alternative_data(symbol, ['fred']),
                self.sentiment_source.get_sentiment_data(symbol),
                self.fusion_engine.fuse_multi_modal_data(symbol, {'price': current_price}),
                self.context_composer.generate_enhanced_context(symbol)
            ]

            fred_data, sentiment_data, fusion_context, enhanced_context = await asyncio.gather(
                *tasks, return_exceptions=True
            )

            # Generate calendar alerts
            economic_alerts = self.calendar_alerts.check_fred_release_schedule(fred_data)
            news_alerts = self.calendar_alerts.generate_news_alerts(sentiment_data)
            time_alerts = self.calendar_alerts.check_time_based_alerts()

            all_alerts = economic_alerts + news_alerts + time_alerts
            self.alert_history.extend(all_alerts)
            self.performance_metrics['alerts_triggered'] += len(all_alerts)

            # Calculate base signal
            signal_type, strength, reasoning = self._calculate_base_signal(
                fred_data, sentiment_data, fusion_context, enhanced_context, all_alerts
            )

            # Apply risk adjustments
            risk_adjustment = self._calculate_risk_adjustment(
                fred_data, sentiment_data, fusion_context, all_alerts
            )

            # Calculate position sizing
            position_size = self._calculate_position_size(strength, risk_adjustment, symbol)

            # Determine confidence
            confidence = self._calculate_confidence(
                fred_data, sentiment_data, fusion_context, enhanced_context
            )

            # Generate stop loss and take profit
            stop_loss, take_profit = self._calculate_risk_management_levels(
                current_price, signal_type, symbol, fred_data, sentiment_data
            )

            # Create trading signal
            signal = TradingSignal(
                symbol=symbol,
                signal_type=signal_type,
                strength=strength,
                confidence=confidence,
                position_size=position_size,
                price=current_price,
                economic_context=fred_data if not isinstance(fred_data, Exception) else {},
                news_context=sentiment_data if not isinstance(sentiment_data, Exception) else {},
                quantum_fusion_score=fusion_context.confidence_score if not isinstance(fusion_context, Exception) else 0.5,
                risk_adjustment=risk_adjustment,
                timestamp=datetime.now(timezone.utc),
                reasoning=reasoning,
                stop_loss=stop_loss,
                take_profit=take_profit,
                time_horizon=self._determine_time_horizon(fred_data, sentiment_data, all_alerts)
            )

            self.signals_generated.append(signal)
            self.performance_metrics['signals_generated'] += 1
            self.performance_metrics['avg_confidence'] = (
                (self.performance_metrics['avg_confidence'] * (len(self.signals_generated) - 1) + confidence) /
                len(self.signals_generated)
            )

            return signal

        except Exception as e:
            self.logger.error(f"Error generating signal for {symbol}: {e}")
            # Return conservative hold signal
            return TradingSignal(
                symbol=symbol,
                signal_type="HOLD",
                strength=0.0,
                confidence=0.0,
                position_size=0.0,
                price=current_price,
                economic_context={},
                news_context={},
                quantum_fusion_score=0.0,
                risk_adjustment=1.0,
                timestamp=datetime.now(timezone.utc),
                reasoning=["Error during signal generation - conservative hold"],
                time_horizon="medium"
            )

    def _calculate_base_signal(self, fred_data, sentiment_data, fusion_context, enhanced_context, alerts) -> Tuple[str, float, List[str]]:
        """Calculate base trading signal"""
        signal_scores = []
        reasoning = []

        # Economic context score
        if not isinstance(fred_data, Exception) and fred_data:
            econ_score, econ_reasoning = self._analyze_economic_signals(fred_data)
            signal_scores.append(econ_score)
            reasoning.extend(econ_reasoning)

        # Sentiment score
        if not isinstance(sentiment_data, Exception) and sentiment_data:
            sent_score, sent_reasoning = self._analyze_sentiment_signals(sentiment_data)
            signal_scores.append(sent_score)
            reasoning.extend(sent_reasoning)

        # Fusion context score
        if not isinstance(fusion_context, Exception) and fusion_context:
            fusion_score, fusion_reasoning = self._analyze_fusion_signals(fusion_context)
            signal_scores.append(fusion_score)
            reasoning.extend(fusion_reasoning)

        # Alert-based adjustments
        alert_score, alert_reasoning = self._analyze_alerts(alerts)
        signal_scores.append(alert_score)
        reasoning.extend(alert_reasoning)

        # Calculate final signal
        if not signal_scores:
            return "HOLD", 0.0, ["Insufficient data - hold position"]

        avg_score = np.mean(signal_scores)
        strength = abs(avg_score)

        if avg_score > 0.2:
            return "BUY", strength, reasoning
        elif avg_score < -0.2:
            return "SELL", strength, reasoning
        else:
            return "HOLD", strength, reasoning

    def _analyze_economic_signals(self, fred_data: Dict) -> Tuple[float, List[str]]:
        """Analyze economic data for trading signals"""
        score = 0.0
        reasoning = []

        try:
            # Federal Funds Rate impact
            dff_data = fred_data.get('fred', {}).get('DFF', {})
            if dff_data and dff_data.get('trend') == 'down':
                score += 0.3  # Good for stocks
                reasoning.append("Federal Funds Rate trending down - bullish")
            elif dff_data and dff_data.get('trend') == 'up':
                score -= 0.3  # Bad for stocks
                reasoning.append("Federal Funds Rate trending up - bearish")

            # GDP impact
            gdp_data = fred_data.get('fred', {}).get('GDP', {})
            if gdp_data and gdp_data.get('trend') == 'up':
                score += 0.2
                reasoning.append("GDP trending up - economic expansion")

            # Unemployment impact
            unemployment_data = fred_data.get('fred', {}).get('UNRATE', {})
            if unemployment_data and unemployment_data.get('trend') == 'down':
                score += 0.15
                reasoning.append("Unemployment rate falling - positive")

            # Treasury yields impact
            treasury_data = fred_data.get('fred', {}).get('DGS10', {})
            if treasury_data and treasury_data.get('trend') == 'down':
                score += 0.1
                reasoning.append("Treasury yields declining - risk-on sentiment")

        except Exception as e:
            self.logger.error(f"Error analyzing economic signals: {e}")

        return score, reasoning

    def _analyze_sentiment_signals(self, sentiment_data: Dict) -> Tuple[float, List[str]]:
        """Analyze sentiment data for trading signals"""
        score = 0.0
        reasoning = []

        try:
            sentiment_score = sentiment_data.get('sentiment_score', 0)
            confidence = sentiment_data.get('sentiment_confidence', 0)
            volume = sentiment_data.get('sentiment_volume', 0)

            # Weight sentiment by confidence
            weighted_sentiment = sentiment_score * confidence
            score += weighted_sentiment * 0.5

            if weighted_sentiment > 0.2:
                reasoning.append(f"Positive news sentiment: {sentiment_score:+.3f} (confidence: {confidence:.2f})")
            elif weighted_sentiment < -0.2:
                reasoning.append(f"Negative news sentiment: {sentiment_score:+.3f} (confidence: {confidence:.2f})")

            # Volume consideration
            if volume > 1000:
                score += 0.1 * np.sign(weighted_sentiment)
                reasoning.append(f"High news volume: {volume:,} mentions")

        except Exception as e:
            self.logger.error(f"Error analyzing sentiment signals: {e}")

        return score, reasoning

    def _analyze_fusion_signals(self, fusion_context) -> Tuple[float, List[str]]:
        """Analyze quantum fusion context for trading signals"""
        score = 0.0
        reasoning = []

        try:
            # Use fusion confidence as a signal modifier
            if hasattr(fusion_context, 'confidence_score'):
                fusion_confidence = fusion_context.confidence_score
                score += fusion_confidence * 0.3

                if fusion_confidence > 0.7:
                    reasoning.append("High quantum fusion confidence - strong signal")
                elif fusion_confidence < 0.3:
                    reasoning.append("Low quantum fusion confidence - weak signal")

            # Check fusion weights for sentiment bias
            if hasattr(fusion_context, 'quantum_weights') and len(fusion_context.quantum_weights) > 2:
                weights = fusion_context.quantum_weights
                sentiment_bias = weights[2] if len(weights) > 2 else 0  # Sentiment weight
                score += (sentiment_bias - 0.25) * 0.4  # Bias around 0.25

        except Exception as e:
            self.logger.error(f"Error analyzing fusion signals: {e}")

        return score, reasoning

    def _analyze_alerts(self, alerts: List[Dict]) -> Tuple[float, List[str]]:
        """Analyze calendar alerts for trading impact"""
        score = 0.0
        reasoning = []

        try:
            for alert in alerts:
                alert_type = alert.get('type', '')
                impact = alert.get('impact', 'medium')

                if alert_type == 'fed_meeting_risk' or impact == 'high':
                    score -= 0.5  # High risk - reduce positions
                    reasoning.append(f"High-impact alert: {alert.get('message', 'Unknown')}")

                elif alert_type == 'high_sentiment':
                    direction = alert.get('direction', '')
                    strength = alert.get('strength', 0)
                    if direction == 'BULLISH':
                        score += strength * 0.3
                        reasoning.append(f"Bullish sentiment alert: {alert.get('message', '')}")
                    elif direction == 'BEARISH':
                        score -= strength * 0.3
                        reasoning.append(f"Bearish sentiment alert: {alert.get('message', '')}")

                elif alert_type == 'high_volatility':
                    score *= 0.7  # Reduce signal strength during high volatility
                    reasoning.append(f"High volatility alert: {alert.get('message', '')}")

        except Exception as e:
            self.logger.error(f"Error analyzing alerts: {e}")

        return score, reasoning

    def _calculate_risk_adjustment(self, fred_data, sentiment_data, fusion_context, alerts: List[Dict]) -> float:
        """Calculate risk adjustment factor"""
        adjustment = 1.0

        try:
            # Economic risk adjustments
            if not isinstance(fred_data, Exception) and fred_data:
                dff_data = fred_data.get('fred', {}).get('DFF', {})
                if dff_data:
                    rate_level = dff_data.get('latest_value', 3.0)
                    # Higher rates = higher risk adjustment
                    adjustment += (rate_level - 3.0) * 0.1

            # Sentiment volatility risk
            if not isinstance(sentiment_data, Exception) and sentiment_data:
                sentiment_vol = sentiment_data.get('sentiment_volatility', 0)
                adjustment += sentiment_vol * 0.3

            # Alert-based risk
            high_alert_count = sum(1 for alert in alerts if alert.get('impact') == 'high')
            adjustment += high_alert_count * 0.2

            # Fusion reliability
            if not isinstance(fusion_context, Exception) and hasattr(fusion_context, 'data_reliability'):
                fusion_reliability = fusion_context.data_reliability
                adjustment = adjustment * (2.0 - fusion_reliability)  # Lower reliability = higher risk

        except Exception as e:
            self.logger.error(f"Error calculating risk adjustment: {e}")

        return max(0.5, min(3.0, adjustment))  # Bound between 0.5 and 3.0

    def _calculate_position_size(self, strength: float, risk_adjustment: float, symbol: str) -> float:
        """Calculate position size based on signal strength and risk"""
        base_size = strength * 0.3  # Base 30% max position for strongest signal

        # Apply risk adjustment
        adjusted_size = base_size / risk_adjustment

        # Apply position limits
        max_single = self.position_limits['max_single_position']
        position_size = min(adjusted_size, max_single)

        # Symbol-specific adjustments
        symbol_risk_factors = {
            'TSLA': 1.3,  # Higher volatility
            'NVDA': 1.2,
            'AMC': 1.5,
            'BTC': 1.4,
            'SPY': 0.8,  # Lower volatility (ETF)
            'QQQ': 0.8
        }

        risk_factor = symbol_risk_factors.get(symbol, 1.0)
        position_size = position_size / risk_factor

        return max(0.0, position_size)

    def _calculate_confidence(self, fred_data, sentiment_data, fusion_context, enhanced_context) -> float:
        """Calculate overall signal confidence"""
        confidences = []

        # Data availability confidence
        available_sources = 0
        if not isinstance(fred_data, Exception) and fred_data:
            available_sources += 1
        if not isinstance(sentiment_data, Exception) and sentiment_data:
            available_sources += 1
        if not isinstance(fusion_context, Exception) and fusion_context:
            available_sources += 1

        availability_confidence = min(1.0, available_sources / 3.0)
        confidences.append(availability_confidence)

        # Sentiment confidence
        if not isinstance(sentiment_data, Exception) and sentiment_data:
            sent_conf = sentiment_data.get('sentiment_confidence', 0)
            confidences.append(sent_conf)

        # Fusion confidence
        if not isinstance(fusion_context, Exception) and hasattr(fusion_context, 'confidence_score'):
            fusion_conf = fusion_context.confidence_score
            confidences.append(fusion_conf)

        # Context confidence
        if not isinstance(enhanced_context, Exception) and hasattr(enhanced_context, 'confidence_weight'):
            context_conf = enhanced_context.confidence_weight
            confidences.append(context_conf)

        return np.mean(confidences) if confidences else 0.3  # Default confidence

    def _calculate_risk_management_levels(self, current_price: float, signal_type: str, symbol: str, fred_data, sentiment_data) -> Tuple[Optional[float], Optional[float]]:
        """Calculate stop loss and take profit levels"""
        if not current_price or current_price <= 0:
            return None, None

        # Base percentages
        stop_loss_pct = 0.02  # 2% stop loss
        take_profit_pct = 0.04  # 4% take profit

        # Adjust based on volatility
        if not isinstance(sentiment_data, Exception) and sentiment_data:
            volatility = sentiment_data.get('sentiment_volatility', 0)
            stop_loss_pct += volatility * 0.02  # Wider stops for high volatility
            take_profit_pct += volatility * 0.03  # Larger targets for high volatility

        # Adjust based on economic conditions
        if not isinstance(fred_data, Exception) and fred_data:
            dff_data = fred_data.get('fred', {}).get('DFF', {})
            if dff_data:
                rate_level = dff_data.get('latest_value', 3.0)
                # Higher rates = tighter stops
                if rate_level > 4.0:
                    stop_loss_pct *= 0.8
                    take_profit_pct *= 0.8

        # Symbol-specific adjustments
        symbol_adjustments = {
            'TSLA': {'stop': 1.5, 'profit': 1.8},  # More volatility
            'NVDA': {'stop': 1.3, 'profit': 1.5},
            'SPY': {'stop': 0.8, 'profit': 0.9},    # Less volatility
            'QQQ': {'stop': 0.8, 'profit': 0.9}
        }

        if symbol in symbol_adjustments:
            adjustments = symbol_adjustments[symbol]
            stop_loss_pct *= adjustments['stop']
            take_profit_pct *= adjustments['profit']

        # Calculate levels
        stop_loss = None
        take_profit = None

        if signal_type == "BUY":
            stop_loss = current_price * (1 - stop_loss_pct)
            take_profit = current_price * (1 + take_profit_pct)
        elif signal_type == "SELL":
            stop_loss = current_price * (1 + stop_loss_pct)
            take_profit = current_price * (1 - take_profit_pct)

        return stop_loss, take_profit

    def _determine_time_horizon(self, fred_data, sentiment_data, alerts: List[Dict]) -> str:
        """Determine optimal time horizon for the trade"""
        # Check for short-term factors
        if any(alert.get('type') in ['high_volatility', 'high_volume'] for alert in alerts):
            return "short"

        # Check for long-term economic factors
        if not isinstance(fred_data, Exception) and fred_data:
            if fred_data.get('fred', {}).get('GDP', {}).get('trend') == 'up':
                return "long"

        # Check sentiment momentum
        if not isinstance(sentiment_data, Exception) and sentiment_data:
            trend_strength = sentiment_data.get('sentiment_trend', {}).get('strength', 0)
            if trend_strength > 0.5:
                return "long"
            elif trend_strength < -0.5:
                return "short"

        return "medium"  # Default

    def get_active_alerts(self, max_alerts: int = 10) -> List[Dict]:
        """Get recent alerts"""
        return self.alert_history[-max_alerts:] if self.alert_history else []

    def get_performance_summary(self) -> Dict:
        """Get performance metrics summary"""
        if not self.signals_generated:
            return {
                'total_signals': 0,
                'avg_confidence': 0.0,
                'alert_count': 0,
                'economic_adjustments': 0
            }

        return {
            'total_signals': len(self.signals_generated),
            'avg_confidence': self.performance_metrics['avg_confidence'],
            'alert_count': len(self.alert_history),
            'economic_adjustments': self.performance_metrics['economic_adjustments'],
            'recent_signals': [s.signal_type for s in self.signals_generated[-10:]],
            'signal_distribution': {
                'BUY': sum(1 for s in self.signals_generated if s.signal_type == 'BUY'),
                'SELL': sum(1 for s in self.signals_generated if s.signal_type == 'SELL'),
                'HOLD': sum(1 for s in self.signals_generated if s.signal_type == 'HOLD')
            }
        }

# Export the main classes for use in trading systems
__all__ = ['NewsEnhancedTradingAlgorithm', 'TradingSignal', 'EconomicCalendarAlerts']