#!/usr/bin/env python3
"""
Phase 1 Integration: Multi-MA Consensus Signal Model
Wraps Phase 1 MultiMAStrategy as a Model Zoo SignalModel
"""

import sys
import os
from pathlib import Path
from typing import Dict, Any, Optional, List
import numpy as np
import pandas as pd

# Add Phase 1 to path
phase1_path = Path(__file__).parent.parent.parent / "phase1"
sys.path.insert(0, str(phase1_path))

from models.interfaces import SignalModel, SignalResult, ModelMetadata
from strategy.moving_average_crossover import MultiMAStrategy


class Phase1MultiMASignal(SignalModel):
    """
    SignalModel wrapper for Phase 1 Multi-MA Consensus strategy.

    Generates BUY/SELL/HOLD signals based on consensus of multiple MA pairs.
    """

    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)

        # Extract Phase 1 parameters
        self.ma_pairs = config.get('ma_pairs', [(5, 20), (10, 50), (20, 200)])
        self.consensus_threshold = config.get('consensus_threshold', 2)

        # Initialize Phase 1 strategy
        self.phase1_strategy = MultiMAStrategy(
            ma_pairs=self.ma_pairs,
            consensus_threshold=self.consensus_threshold
        )

        # Update metadata
        self.metadata.parameters = {
            'ma_pairs': self.ma_pairs,
            'consensus_threshold': self.consensus_threshold
        }

    def generate_signal(
        self,
        features: Dict[str, Any],
        forecast: Optional[Any] = None
    ) -> SignalResult:
        """
        Generate signal using Phase 1 Multi-MA consensus logic.

        Args:
            features: Dictionary of features (should contain price data)
            forecast: Optional forecast (not used by MA strategy)

        Returns:
            SignalResult with action, confidence, and reasons
        """
        try:
            # Convert features dict to DataFrame row
            df = self._features_to_dataframe(features)

            # Generate signal using Phase 1 strategy
            signals_df = self.phase1_strategy.generate_signals(df)

            # Extract latest signal
            if len(signals_df) > 0:
                latest = signals_df.iloc[-1]
                action = latest.get('Signal', 'HOLD')

                # Compute confidence based on consensus strength
                confidence = self._compute_confidence(latest, features)

                if action == 'BUY':
                    reasons = self._generate_buy_reasons(latest, features)
                elif action == 'SELL':
                    reasons = self._generate_sell_reasons(latest, features)
                else:
                    reasons = self._generate_hold_reasons(latest, features)

                signal_components = self._extract_signal_components(latest, features)

                return SignalResult(
                    action=action,
                    confidence=confidence,
                    reasons=reasons,
                    signal_components=signal_components,
                    metadata={
                        'phase1_strategy': 'multi_ma',
                        'phase1_params': self.metadata.parameters,
                        'consensus_count': int(latest.get('MA_Consensus', 0)),
                        'total_pairs': len(self.ma_pairs)
                    }
                )
            else:
                return SignalResult(
                    action='HOLD',
                    confidence=0.0,
                    reasons=['Insufficient data for signal generation'],
                    signal_components={},
                    metadata={'error': 'no_data'}
                )

        except Exception as e:
            return SignalResult(
                action='HOLD',
                confidence=0.0,
                reasons=[f'Error generating signal: {str(e)}'],
                signal_components={},
                metadata={'error': str(e), 'phase1_strategy': 'multi_ma'}
            )

    def train(self, X: np.ndarray, y: np.ndarray) -> None:
        """Multi-MA is rule-based, no training needed."""
        pass

    def _features_to_dataframe(self, features: Dict[str, Any]) -> pd.DataFrame:
        """Convert features dict to single-row DataFrame."""
        flat_features = {}

        for key, value in features.items():
            if isinstance(value, dict):
                flat_features.update(value)
            else:
                flat_features[key] = value

        df = pd.DataFrame([flat_features])

        if 'Close' not in df.columns:
            if 'price_close' in flat_features:
                df['Close'] = flat_features['price_close']
            else:
                raise ValueError("Feature dict must contain 'Close' or 'price_close'")

        return df

    def _compute_confidence(self, signal_row: pd.Series, features: Dict[str, Any]) -> float:
        """Compute confidence based on consensus strength."""
        consensus = signal_row.get('MA_Consensus', 0)
        total_pairs = len(self.ma_pairs)

        # Base confidence on consensus ratio
        if total_pairs > 0:
            consensus_ratio = abs(consensus) / total_pairs
            base_confidence = 0.5 + (consensus_ratio * 0.4)  # 0.5 to 0.9
        else:
            base_confidence = 0.5

        # Boost for strong consensus
        if abs(consensus) >= self.consensus_threshold:
            base_confidence = min(1.0, base_confidence + 0.1)

        return float(base_confidence)

    def _generate_buy_reasons(self, signal_row: pd.Series, features: Dict[str, Any]) -> list:
        """Generate human-readable buy reasons."""
        reasons = []

        consensus = signal_row.get('MA_Consensus', 0)
        total_pairs = len(self.ma_pairs)

        reasons.append(f"MA Consensus: {consensus}/{total_pairs} pairs indicate BUY")

        # List which pairs are bullish
        for i, (short, long) in enumerate(self.ma_pairs):
            col = f'MA_{short}_{long}'
            signal = signal_row.get(f'{col}_Signal', 0)
            if signal > 0:
                reasons.append(f"  MA({short},{long}): Bullish (short above long)")

        rsi = features.get('rsi', features.get('RSI', 50))
        if rsi < 40:
            reasons.append(f"RSI confirms: {rsi:.1f} (oversold zone)")

        return reasons

    def _generate_sell_reasons(self, signal_row: pd.Series, features: Dict[str, Any]) -> list:
        """Generate human-readable sell reasons."""
        reasons = []

        consensus = signal_row.get('MA_Consensus', 0)
        total_pairs = len(self.ma_pairs)

        reasons.append(f"MA Consensus: {abs(consensus)}/{total_pairs} pairs indicate SELL")

        # List which pairs are bearish
        for i, (short, long) in enumerate(self.ma_pairs):
            col = f'MA_{short}_{long}'
            signal = signal_row.get(f'{col}_Signal', 0)
            if signal < 0:
                reasons.append(f"  MA({short},{long}): Bearish (short below long)")

        rsi = features.get('rsi', features.get('RSI', 50))
        if rsi > 60:
            reasons.append(f"RSI confirms: {rsi:.1f} (overbought zone)")

        return reasons

    def _generate_hold_reasons(self, signal_row: pd.Series, features: Dict[str, Any]) -> list:
        """Generate human-readable hold reasons."""
        reasons = []

        consensus = signal_row.get('MA_Consensus', 0)
        total_pairs = len(self.ma_pairs)

        if abs(consensus) < self.consensus_threshold:
            reasons.append(f"Insufficient consensus: {abs(consensus)}/{total_pairs} pairs agree (threshold: {self.consensus_threshold})")
        else:
            reasons.append("Mixed MA signals - no clear direction")

        # Show individual pair signals
        signals_list = []
        for i, (short, long) in enumerate(self.ma_pairs):
            col = f'MA_{short}_{long}'
            signal = signal_row.get(f'{col}_Signal', 0)
            if signal > 0:
                signals_list.append(f"MA({short},{long})=BULL")
            elif signal < 0:
                signals_list.append(f"MA({short},{long})=BEAR")
            else:
                signals_list.append(f"MA({short},{long})=NEUTRAL")

        reasons.append("Individual pairs: " + ", ".join(signals_list))

        return reasons

    def _extract_signal_components(self, signal_row: pd.Series, features: Dict[str, Any]) -> Dict[str, float]:
        """Extract individual signal components for transparency."""
        components = {}

        # Overall consensus
        components['consensus'] = float(signal_row.get('MA_Consensus', 0))

        # Individual MA pair signals
        for i, (short, long) in enumerate(self.ma_pairs):
            col = f'MA_{short}_{long}'
            signal_col = f'{col}_Signal'
            if signal_col in signal_row:
                components[f'ma_{short}_{long}'] = float(signal_row[signal_col])

        # RSI signal
        rsi_signal = signal_row.get('RSI_Signal', 0)
        components['rsi_signal'] = float(rsi_signal)

        return components
