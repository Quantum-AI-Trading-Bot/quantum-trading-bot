#!/usr/bin/env python3
"""
Phase 1: Base Strategy Class
Abstract base class for all trading strategies
"""

from abc import ABC, abstractmethod
import pandas as pd
import logging
from typing import Dict, Any, Optional
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class Signal:
    """Trading signal data structure"""
    symbol: str
    timestamp: pd.Timestamp
    action: str  # 'BUY', 'SELL', 'HOLD'
    confidence: float  # 0.0 to 1.0
    price: float
    reason: str
    metadata: Dict[str, Any] = None

    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}


class BaseStrategy(ABC):
    """
    Abstract base class for trading strategies

    All strategies must inherit from this class and implement:
    - generate_signals(): Generate buy/sell/hold signals
    - validate(): Validate strategy parameters
    """

    def __init__(self, name: str, params: Dict[str, Any] = None):
        """
        Initialize base strategy

        Args:
            name: Strategy name
            params: Strategy parameters
        """
        self.name = name
        self.params = params or {}
        self.validate()

        logger.info(f"Initialized strategy: {self.name} with params: {self.params}")

    @abstractmethod
    def generate_signals(self, data: pd.DataFrame) -> pd.DataFrame:
        """
        Generate trading signals from price data

        Args:
            data: DataFrame with OHLCV data and technical indicators

        Returns:
            DataFrame with added signal columns
        """
        pass

    @abstractmethod
    def validate(self):
        """Validate strategy parameters"""
        pass

    def get_latest_signal(self, data: pd.DataFrame) -> Signal:
        """
        Get the latest trading signal from data

        Args:
            data: DataFrame with signal columns

        Returns:
            Signal object with latest trading decision
        """
        if len(data) == 0:
            raise ValueError("No data available")

        latest = data.iloc[-1]
        timestamp = latest.name if isinstance(latest.name, pd.Timestamp) else pd.Timestamp.now()

        # Determine action and confidence
        if 'Signal' in latest:
            action = latest['Signal']
            confidence = abs(latest.get('Signal_Strength', 0.5))
        elif 'Combined_Signal' in latest:
            signal_value = latest['Combined_Signal']
            if signal_value > 0.3:
                action = 'BUY'
                confidence = min(signal_value, 1.0)
            elif signal_value < -0.3:
                action = 'SELL'
                confidence = min(abs(signal_value), 1.0)
            else:
                action = 'HOLD'
                confidence = 0.5
        else:
            action = 'HOLD'
            confidence = 0.0

        price = latest['Close']

        # Generate reason
        reason = self._generate_reason(latest, action)

        # Extract metadata
        metadata = {
            'strategy': self.name,
            'params': self.params,
            'indicators': {
                col: latest[col]
                for col in latest.index
                if col in ['RSI', 'MACD', 'SMA_10', 'SMA_50', 'BB_Upper', 'BB_Lower']
            }
        }

        return Signal(
            symbol=latest.get('Symbol', 'UNKNOWN'),
            timestamp=timestamp,
            action=action,
            confidence=confidence,
            price=price,
            reason=reason,
            metadata=metadata
        )

    def _generate_reason(self, latest_row: pd.Series, action: str) -> str:
        """Generate human-readable reason for signal"""
        reasons = []

        if action == 'BUY':
            if 'RSI' in latest_row and latest_row['RSI'] < 30:
                reasons.append(f"RSI oversold ({latest_row['RSI']:.2f})")
            if 'SMA_10' in latest_row and 'SMA_50' in latest_row:
                if latest_row['SMA_10'] > latest_row['SMA_50']:
                    reasons.append("Golden cross (SMA_10 > SMA_50)")
            if 'MACD' in latest_row and 'MACD_Signal' in latest_row:
                if latest_row['MACD'] > latest_row['MACD_Signal']:
                    reasons.append("MACD bullish")
            if 'BB_Lower' in latest_row and latest_row['Close'] < latest_row['BB_Lower']:
                reasons.append("Price below Bollinger Lower Band")

        elif action == 'SELL':
            if 'RSI' in latest_row and latest_row['RSI'] > 70:
                reasons.append(f"RSI overbought ({latest_row['RSI']:.2f})")
            if 'SMA_10' in latest_row and 'SMA_50' in latest_row:
                if latest_row['SMA_10'] < latest_row['SMA_50']:
                    reasons.append("Death cross (SMA_10 < SMA_50)")
            if 'MACD' in latest_row and 'MACD_Signal' in latest_row:
                if latest_row['MACD'] < latest_row['MACD_Signal']:
                    reasons.append("MACD bearish")
            if 'BB_Upper' in latest_row and latest_row['Close'] > latest_row['BB_Upper']:
                reasons.append("Price above Bollinger Upper Band")

        if not reasons:
            reasons.append("No clear signal")

        return "; ".join(reasons)

    def backtest(self, data: pd.DataFrame, initial_capital: float = 10000) -> Dict[str, Any]:
        """
        Simple backtest of strategy

        Args:
            data: DataFrame with OHLCV data
            initial_capital: Starting capital for backtest

        Returns:
            Dictionary with backtest results
        """
        logger.info(f"Running backtest for {self.name}...")

        # Generate signals
        data_with_signals = self.generate_signals(data)

        # Simple backtest logic
        position = 0
        cash = initial_capital
        trades = []

        for i in range(1, len(data_with_signals)):
            current_price = data_with_signals['Close'].iloc[i]
            signal = data_with_signals['Signal'].iloc[i-1]

            if signal == 'BUY' and position == 0:
                # Buy
                shares = (cash // current_price)
                if shares > 0:
                    position = shares
                    cash = cash - (shares * current_price)
                    trades.append({
                        'type': 'BUY',
                        'price': current_price,
                        'shares': shares,
                        'timestamp': data_with_signals.index[i]
                    })

            elif signal == 'SELL' and position > 0:
                # Sell
                cash = cash + (position * current_price)
                trades.append({
                    'type': 'SELL',
                    'price': current_price,
                    'shares': position,
                    'timestamp': data_with_signals.index[i]
                })
                position = 0

        # Calculate final value
        final_price = data_with_signals['Close'].iloc[-1]
        final_value = cash + (position * final_price)
        total_return = (final_value - initial_capital) / initial_capital

        results = {
            'strategy': self.name,
            'initial_capital': initial_capital,
            'final_value': final_value,
            'total_return': total_return,
            'total_trades': len(trades),
            'trades': trades
        }

        logger.info(f"Backtest complete. Return: {total_return:.2%}, Trades: {len(trades)}")
        return results
