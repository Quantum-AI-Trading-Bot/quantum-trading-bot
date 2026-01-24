#!/usr/bin/env python3
"""
Phase 1: Moving Average Crossover Strategy
Classic trend-following strategy using moving average crossovers
"""

import pandas as pd
import numpy as np
import logging
from typing import Dict, Any
from .base_strategy import BaseStrategy

logger = logging.getLogger(__name__)


class MovingAverageCrossover(BaseStrategy):
    """
    Moving Average Crossover Strategy

    Generates buy/sell signals when short-term MA crosses long-term MA:
    - BUY when short MA crosses above long MA (Golden Cross)
    - SELL when short MA crosses below long MA (Death Cross)
    """

    def __init__(
        self,
        short_window: int = 10,
        long_window: int = 50,
        signal_threshold: float = 0.02
    ):
        """
        Initialize MA Crossover strategy

        Args:
            short_window: Short-term MA period
            long_window: Long-term MA period
            signal_threshold: Minimum price change to confirm signal
        """
        # Set attributes first
        self.short_window = short_window
        self.long_window = long_window
        self.signal_threshold = signal_threshold

        params = {
            'short_window': short_window,
            'long_window': long_window,
            'signal_threshold': signal_threshold
        }

        super().__init__(
            name="Moving Average Crossover",
            params=params
        )

    def validate(self):
        """Validate strategy parameters"""
        if self.short_window >= self.long_window:
            raise ValueError(f"Short window ({self.short_window}) must be less than long window ({self.long_window})")

        if self.short_window < 2:
            raise ValueError(f"Short window ({self.short_window}) must be at least 2")

        if self.signal_threshold < 0 or self.signal_threshold > 1:
            raise ValueError(f"Signal threshold ({self.signal_threshold}) must be between 0 and 1")

        logger.info(f"✅ Parameters validated: short={self.short_window}, long={self.long_window}")

    def generate_signals(self, data: pd.DataFrame) -> pd.DataFrame:
        """
        Generate MA crossover signals

        Args:
            data: DataFrame with OHLCV data

        Returns:
            DataFrame with MA columns and Signal column
        """
        df = data.copy()

        # Calculate moving averages
        df[f'MA_{self.short_window}'] = df['Close'].rolling(window=self.short_window).mean()
        df[f'MA_{self.long_window}'] = df['Close'].rolling(window=self.long_window).mean()

        # Calculate crossover points
        df['MA_Diff'] = df[f'MA_{self.short_window}'] - df[f'MA_{self.long_window}']
        df['MA_Diff_Prev'] = df['MA_Diff'].shift(1)

        # Generate signals
        df['Signal'] = 'HOLD'
        df['Signal_Strength'] = 0.0

        # Golden Cross: Short MA crosses above Long MA
        golden_cross = (df['MA_Diff'] > 0) & (df['MA_Diff_Prev'] <= 0)
        df.loc[golden_cross, 'Signal'] = 'BUY'
        df.loc[golden_cross, 'Signal_Strength'] = 0.8

        # Death Cross: Short MA crosses below Long MA
        death_cross = (df['MA_Diff'] < 0) & (df['MA_Diff_Prev'] >= 0)
        df.loc[death_cross, 'Signal'] = 'SELL'
        df.loc[death_cross, 'Signal_Strength'] = 0.8

        # Remove NaN signals
        df = df.dropna(subset=['Signal'])

        logger.info(f"Generated {len(df[df['Signal'] == 'BUY'])} BUY signals")
        logger.info(f"Generated {len(df[df['Signal'] == 'SELL'])} SELL signals")
        logger.info(f"Generated {len(df[df['Signal'] == 'HOLD'])} HOLD signals")

        return df

    def get_signal_strength(self, data: pd.DataFrame) -> pd.Series:
        """
        Calculate signal strength based on MA separation

        Args:
            data: DataFrame with MA columns

        Returns:
            Series with signal strength values
        """
        ma_short = data[f'MA_{self.short_window}']
        ma_long = data[f'MA_{self.long_window}']
        price = data['Close']

        # Calculate percentage difference
        ma_diff_pct = (ma_short - ma_long) / ma_long

        # Normalize to 0-1 range
        strength = np.abs(ma_diff_pct) / self.signal_threshold
        strength = np.clip(strength, 0, 1)

        return strength


class MultiMAStrategy(BaseStrategy):
    """
    Multiple Moving Average Strategy

    Uses multiple MA pairs for confirmation
    """

    def __init__(
        self,
        ma_pairs: list = None,
        consensus_threshold: int = 2
    ):
        """
        Initialize Multi-MA strategy

        Args:
            ma_pairs: List of (short, long) MA pairs
            consensus_threshold: Minimum number of pairs to agree for signal
        """
        if ma_pairs is None:
            ma_pairs = [(5, 20), (10, 50), (20, 200)]

        # Set attributes first
        self.ma_pairs = ma_pairs
        self.consensus_threshold = consensus_threshold

        params = {
            'ma_pairs': ma_pairs,
            'consensus_threshold': consensus_threshold
        }

        super().__init__(
            name="Multiple Moving Average",
            params=params
        )

    def validate(self):
        """Validate strategy parameters"""
        if len(self.ma_pairs) < 1:
            raise ValueError("At least one MA pair required")

        if self.consensus_threshold < 1 or self.consensus_threshold > len(self.ma_pairs):
            raise ValueError(f"Consensus threshold must be between 1 and {len(self.ma_pairs)}")

        for short, long in self.ma_pairs:
            if short >= long:
                raise ValueError(f"Short window ({short}) must be less than long window ({long})")

        logger.info(f"✅ Parameters validated: {len(self.ma_pairs)} MA pairs, threshold={self.consensus_threshold}")

    def generate_signals(self, data: pd.DataFrame) -> pd.DataFrame:
        """
        Generate multi-MA consensus signals

        Args:
            data: DataFrame with OHLCV data

        Returns:
            DataFrame with MA columns and Signal column
        """
        df = data.copy()

        # Calculate all MA pairs
        buy_signals = pd.Series(0, index=df.index)
        sell_signals = pd.Series(0, index=df.index)

        for short, long in self.ma_pairs:
            short_ma = df['Close'].rolling(window=short).mean()
            long_ma = df['Close'].rolling(window=long).mean()

            # Detect crossovers
            ma_diff = short_ma - long_ma
            ma_diff_prev = ma_diff.shift(1)

            # Buy signal: Short crosses above Long
            buy_signals += (ma_diff > 0) & (ma_diff_prev <= 0)

            # Sell signal: Short crosses below Long
            sell_signals += (ma_diff < 0) & (ma_diff_prev >= 0)

            # Store MA values for reference
            df[f'MA_{short}'] = short_ma
            df[f'MA_{long}'] = long_ma

        # Generate consensus signals
        df['Signal'] = 'HOLD'
        df['Signal_Strength'] = 0.0

        # Buy signal
        buy_mask = buy_signals >= self.consensus_threshold
        df.loc[buy_mask, 'Signal'] = 'BUY'
        df.loc[buy_mask, 'Signal_Strength'] = buy_signals[buy_mask] / len(self.ma_pairs)

        # Sell signal
        sell_mask = sell_signals >= self.consensus_threshold
        df.loc[sell_mask, 'Signal'] = 'SELL'
        df.loc[sell_mask, 'Signal_Strength'] = sell_signals[sell_mask] / len(self.ma_pairs)

        # Remove NaN signals
        df = df.dropna(subset=['Signal'])

        logger.info(f"Generated {len(df[df['Signal'] == 'BUY'])} BUY signals (consensus)")
        logger.info(f"Generated {len(df[df['Signal'] == 'SELL'])} SELL signals (consensus)")

        return df


if __name__ == "__main__":
    # Test the strategies
    from data.fetch_price_data import fetch_price_data
    from data.feature_engineering import add_technical_indicators

    logger.info("Testing Moving Average Strategies...")

    # Fetch sample data
    symbol = "AAPL"
    start_date = "2024-01-01"
    end_date = "2025-01-01"

    logger.info(f"\nFetching {symbol} data...")
    data = fetch_price_data(symbol, start_date, end_date)

    if data is not None:
        data_with_indicators = add_technical_indicators(data)

        logger.info(f"\n{'='*60}")
        logger.info("Testing Simple MA Crossover")
        logger.info(f"{'='*60}\n")

        ma_strategy = MovingAverageCrossover(short_window=10, long_window=50)
        signals = ma_strategy.generate_signals(data_with_indicators)

        latest_signal = ma_strategy.get_latest_signal(signals)
        logger.info(f"\nLatest Signal: {latest_signal.action}")
        logger.info(f"Confidence: {latest_signal.confidence:.2f}")
        logger.info(f"Reason: {latest_signal.reason}")

        logger.info(f"\n{'='*60}")
        logger.info("Testing Multi-MA Strategy")
        logger.info(f"{'='*60}\n")

        multi_ma_strategy = MultiMAStrategy(
            ma_pairs=[(5, 20), (10, 50), (20, 200)],
            consensus_threshold=2
        )
        signals_multi = multi_ma_strategy.generate_signals(data_with_indicators)

        latest_signal_multi = multi_ma_strategy.get_latest_signal(signals_multi)
        logger.info(f"\nLatest Signal: {latest_signal_multi.action}")
        logger.info(f"Confidence: {latest_signal_multi.confidence:.2f}")
        logger.info(f"Reason: {latest_signal_multi.reason}")

        logger.info(f"\n{'='*60}")
        logger.info("Running Backtest")
        logger.info(f"{'='*60}\n")

        backtest_results = ma_strategy.backtest(data_with_indicators)
        logger.info(f"\nBacktest Results:")
        logger.info(f"Initial Capital: ${backtest_results['initial_capital']:,.2f}")
        logger.info(f"Final Value: ${backtest_results['final_value']:,.2f}")
        logger.info(f"Total Return: {backtest_results['total_return']:.2%}")
        logger.info(f"Total Trades: {backtest_results['total_trades']}")
