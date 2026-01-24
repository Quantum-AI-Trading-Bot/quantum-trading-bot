#!/usr/bin/env python3
"""
Phase 1 Integration: Moving Average Crossover Signal Model
Wraps Phase 1 MovingAverageCrossover strategy as a Model Zoo SignalModel
"""

import sys
import os
from pathlib import Path
from typing import Dict, Any, Optional
import numpy as np
import pandas as pd

# Add Phase 1 to path
phase1_path = Path(__file__).parent.parent.parent / "phase1"
sys.path.insert(0, str(phase1_path))

from models.interfaces import SignalModel, SignalResult, ModelMetadata
from strategy.moving_average_crossover import MovingAverageCrossover


class Phase1MACrossoverSignal(SignalModel):
    """
    SignalModel wrapper for Phase 1 Moving Average Crossover strategy.

    Generates BUY/SELL/HOLD signals based on MA crossovers.
    """

    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)

        # Extract Phase 1 parameters
        self.short_window = config.get('short_window', 10)
        self.long_window = config.get('long_window', 50)
        self.signal_threshold = config.get('signal_threshold', 0.02)

        # Initialize Phase 1 strategy
        self.phase1_strategy = MovingAverageCrossover(
            short_window=self.short_window,
            long_window=self.long_window,
            signal_threshold=self.signal_threshold
        )

        # Update metadata
        self.metadata.parameters = {
            'short_window': self.short_window,
            'long_window': self.long_window,
            'signal_threshold': self.signal_threshold
        }

    def generate_signal(
        self,
        features: Dict[str, Any],
        forecast: Optional[Any] = None
    ) -> SignalResult:
        """
        Generate signal using Phase 1 MA crossover logic.

        Args:
            features: Dictionary of features (should contain price data)
            forecast: Optional forecast (not used by MA strategy)

        Returns:
            SignalResult with action, confidence, and reasons
        """
        try:
            # Convert features dict to DataFrame row (required by Phase 1)
            # Features should have at least: Close, and ideally SMA columns
            df = self._features_to_dataframe(features)

            # Generate signal using Phase 1 strategy
            signals_df = self.phase1_strategy.generate_signals(df)

            # Extract latest signal
            if len(signals_df) > 0:
                latest = signals_df.iloc[-1]
                action = latest.get('Signal', 'HOLD')

                # Map Phase 1 signal to SignalResult
                confidence = self._compute_confidence(latest, features)

                if action == 'BUY':
                    reasons = self._generate_buy_reasons(latest, features)
                elif action == 'SELL':
                    reasons = self._generate_sell_reasons(latest, features)
                else:
                    reasons = ["No crossover signal - HOLD"]

                signal_components = self._extract_signal_components(latest, features)

                return SignalResult(
                    action=action,
                    confidence=confidence,
                    reasons=reasons,
                    signal_components=signal_components,
                    metadata={
                        'phase1_strategy': 'ma_crossover',
                        'phase1_params': self.metadata.parameters,
                        'ma_diff': latest.get('MA_Diff', 0.0),
                        'ma_short': latest.get('SMA_10', 0.0) if self.short_window == 10 else latest.get(f'SMA_{self.short_window}', 0.0),
                        'ma_long': latest.get('SMA_50', 0.0) if self.long_window == 50 else latest.get(f'SMA_{self.long_window}', 0.0)
                    }
                )
            else:
                # No data - return HOLD
                return SignalResult(
                    action='HOLD',
                    confidence=0.0,
                    reasons=['Insufficient data for signal generation'],
                    signal_components={},
                    metadata={'error': 'no_data'}
                )

        except Exception as e:
            # Log error and return safe HOLD
            return SignalResult(
                action='HOLD',
                confidence=0.0,
                reasons=[f'Error generating signal: {str(e)}'],
                signal_components={},
                metadata={'error': str(e), 'phase1_strategy': 'ma_crossover'}
            )

    def train(self, X: np.ndarray, y: np.ndarray) -> None:
        """
        MA crossover is rule-based, no training needed.

        Args:
            X: Not used (rule-based strategy)
            y: Not used (rule-based strategy)
        """
        pass

    def _features_to_dataframe(self, features: Dict[str, Any]) -> pd.DataFrame:
        """Convert features dict to single-row DataFrame."""
        # Handle both flat dict and nested dict structures
        flat_features = {}

        for key, value in features.items():
            if isinstance(value, dict):
                # Flatten nested dicts
                flat_features.update(value)
            else:
                flat_features[key] = value

        # Create DataFrame with single row
        df = pd.DataFrame([flat_features])

        # Ensure we have required columns
        if 'Close' not in df.columns:
            # Try alternate naming
            if 'price_close' in flat_features:
                df['Close'] = flat_features['price_close']
            else:
                raise ValueError("Feature dict must contain 'Close' or 'price_close'")

        return df

    def _compute_confidence(self, signal_row: pd.Series, features: Dict[str, Any]) -> float:
        """Compute confidence based on signal strength."""
        # For MA crossover, confidence can be based on:
        # 1. Distance from crossover point
        # 2. RSI confirmation (if available)
        # 3. Volume confirmation (if available)

        base_confidence = 0.8

        # Check for RSI confirmation
        rsi = features.get('rsi', features.get('RSI', 50))
        if signal_row.get('Signal') == 'BUY' and rsi < 30:
            base_confidence = min(1.0, base_confidence + 0.1)
        elif signal_row.get('Signal') == 'SELL' and rsi > 70:
            base_confidence = min(1.0, base_confidence + 0.1)

        return base_confidence

    def _generate_buy_reasons(self, signal_row: pd.Series, features: Dict[str, Any]) -> list:
        """Generate human-readable buy reasons."""
        reasons = []

        short_ma = signal_row.get('SMA_10', signal_row.get(f'SMA_{self.short_window}', 0))
        long_ma = signal_row.get('SMA_50', signal_row.get(f'SMA_{self.long_window}', 0))

        if short_ma > long_ma:
            reasons.append(f"Golden Cross: SMA_{self.short_window} ({short_ma:.2f}) crossed above SMA_{self.long_window} ({long_ma:.2f})")

        rsi = features.get('rsi', features.get('RSI', 50))
        if rsi < 30:
            reasons.append(f"RSI oversold: {rsi:.1f}")
        elif rsi < 50:
            reasons.append(f"RSI bullish: {rsi:.1f}")

        if not reasons:
            reasons.append("Moving average bullish alignment")

        return reasons

    def _generate_sell_reasons(self, signal_row: pd.Series, features: Dict[str, Any]) -> list:
        """Generate human-readable sell reasons."""
        reasons = []

        short_ma = signal_row.get('SMA_10', signal_row.get(f'SMA_{self.short_window}', 0))
        long_ma = signal_row.get('SMA_50', signal_row.get(f'SMA_{self.long_window}', 0))

        if short_ma < long_ma:
            reasons.append(f"Death Cross: SMA_{self.short_window} ({short_ma:.2f}) crossed below SMA_{self.long_window} ({long_ma:.2f})")

        rsi = features.get('rsi', features.get('RSI', 50))
        if rsi > 70:
            reasons.append(f"RSI overbought: {rsi:.1f}")
        elif rsi > 50:
            reasons.append(f"RSI bearish: {rsi:.1f}")

        if not reasons:
            reasons.append("Moving average bearish alignment")

        return reasons

    def _extract_signal_components(self, signal_row: pd.Series, features: Dict[str, Any]) -> Dict[str, float]:
        """Extract individual signal components for transparency."""
        components = {}

        # MA difference
        components['ma_diff'] = signal_row.get('MA_Diff', 0.0)

        # RSI signal
        rsi_signal = signal_row.get('RSI_Signal', 0)
        components['rsi_signal'] = float(rsi_signal)

        # MACD signal
        macd_signal = signal_row.get('MACD_Signal', 0)
        components['macd_signal'] = float(macd_signal)

        # Bollinger Band signal
        bb_signal = signal_row.get('BB_Signal', 0)
        components['bb_signal'] = float(bb_signal)

        return components
