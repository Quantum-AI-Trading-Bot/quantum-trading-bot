#!/usr/bin/env python3
"""
Phase 1: Strategy Manager
Manages multiple strategies and combines their signals
"""

import pandas as pd
import logging
from typing import Dict, List, Any
from .base_strategy import BaseStrategy, Signal

logger = logging.getLogger(__name__)


class StrategyManager:
    """
    Manages multiple trading strategies and combines their signals
    """

    def __init__(self, strategies: List[BaseStrategy] = None):
        """
        Initialize strategy manager

        Args:
            strategies: List of strategy instances
        """
        self.strategies = strategies or []
        logger.info(f"StrategyManager initialized with {len(self.strategies)} strategies")

    def add_strategy(self, strategy: BaseStrategy):
        """Add a strategy to the manager"""
        self.strategies.append(strategy)
        logger.info(f"Added strategy: {strategy.name}")

    def generate_combined_signals(self, data: pd.DataFrame) -> pd.DataFrame:
        """
        Generate signals from all strategies and combine them

        Args:
            data: DataFrame with OHLCV data

        Returns:
            DataFrame with combined signals
        """
        if not self.strategies:
            raise ValueError("No strategies registered")

        # Generate signals from each strategy
        all_signals = pd.DataFrame(index=data.index)

        for strategy in self.strategies:
            signals_df = strategy.generate_signals(data)
            all_signals[f'{strategy.name}_Signal'] = signals_df['Signal']
            all_signals[f'{strategy.name}_Strength'] = signals_df['Signal_Strength']

        # Combine signals using voting
        all_signals['Combined_Signal'] = 'HOLD'

        # Count buy and sell votes
        signal_cols = [f'{s.name}_Signal' for s in self.strategies]
        buy_votes = (all_signals[signal_cols] == 'BUY').sum(axis=1)
        sell_votes = (all_signals[signal_cols] == 'SELL').sum(axis=1)

        # Generate combined signal
        buy_threshold = len(self.strategies) / 2  # Majority
        all_signals.loc[buy_votes >= buy_threshold, 'Combined_Signal'] = 'BUY'
        all_signals.loc[sell_votes >= buy_threshold, 'Combined_Signal'] = 'SELL'

        # Calculate combined strength
        strength_cols = [f'{s.name}_Strength' for s in self.strategies]
        all_signals['Combined_Strength'] = all_signals[strength_cols].mean(axis=1)

        logger.info(f"Generated combined signals from {len(self.strategies)} strategies")
        return all_signals

    def get_best_signal(self, data: pd.DataFrame) -> Signal:
        """
        Get the best signal from all strategies

        Args:
            data: DataFrame with OHLCV data

        Returns:
            Best Signal object
        """
        combined_signals = self.generate_combined_signals(data)

        # Get latest combined signal
        latest = combined_signals.iloc[-1]

        # Find strategy with highest confidence for the chosen action
        best_strategy = None
        best_confidence = 0.0

        for strategy in self.strategies:
            signal = strategy.get_latest_signal(data)
            if signal.confidence > best_confidence:
                best_confidence = signal.confidence
                best_strategy = strategy

        if best_strategy:
            return best_strategy.get_latest_signal(data)
        else:
            # Default to combined signal
            return self._create_signal_from_combined(latest, data)

    def _create_signal_from_combined(self, combined_row: pd.Series, data: pd.DataFrame) -> Signal:
        """Create Signal object from combined signals"""
        latest_data = data.iloc[-1]

        return Signal(
            symbol=latest_data.get('Symbol', 'UNKNOWN'),
            timestamp=combined_row.name if isinstance(combined_row.name, pd.Timestamp) else pd.Timestamp.now(),
            action=combined_row['Combined_Signal'],
            confidence=float(combined_row.get('Combined_Strength', 0.5)),
            price=float(latest_data['Close']),
            reason=f"Combined signal from {len(self.strategies)} strategies",
            metadata={'strategy': 'Combined', 'num_strategies': len(self.strategies)}
        )

    def ensemble_predict(self, data: pd.DataFrame) -> pd.DataFrame:
        """
        Use ensemble of strategies for prediction

        Args:
            data: DataFrame with OHLCV data

        Returns:
            DataFrame with ensemble predictions
        """
        combined = self.generate_combined_signals(data)

        # Convert signals to numeric for averaging
        signal_map = {'BUY': 1, 'HOLD': 0, 'SELL': -1}
        numeric_cols = [f'{s.name}_Signal' for s in self.strategies]

        for col in numeric_cols:
            combined[col + '_Numeric'] = combined[col].map(signal_map)

        # Calculate ensemble prediction
        numeric_cols = [col + '_Numeric' for col in numeric_cols]
        combined['Ensemble_Prediction'] = combined[numeric_cols].mean(axis=1)

        # Convert back to signal
        combined['Ensemble_Signal'] = 'HOLD'
        combined.loc[combined['Ensemble_Prediction'] > 0.3, 'Ensemble_Signal'] = 'BUY'
        combined.loc[combined['Ensemble_Prediction'] < -0.3, 'Ensemble_Signal'] = 'SELL'

        return combined
