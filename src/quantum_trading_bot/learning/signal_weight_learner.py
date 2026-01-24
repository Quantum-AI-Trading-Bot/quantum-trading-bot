#!/usr/bin/env python3
"""
Signal Weight Learner - Online learning for signal weights.

Uses multiplicative weights algorithm with bounded updates.
Weights are updated based on signal contribution to trade outcomes.
"""

import json
from typing import Dict, List, Any, Optional
from pathlib import Path
from datetime import datetime
import numpy as np


class SignalWeightLearner:
    """Online learner for updating signal weights based on outcomes."""

    # Default weights for all signals
    DEFAULT_WEIGHTS = {
        'trend': 1.0,
        'momentum': 1.0,
        'mean_reversion': 1.0,
        'volume': 1.0,
        'volatility': 1.0
    }

    # Weight bounds to prevent explosion
    MIN_WEIGHT = 0.1
    MAX_WEIGHT = 5.0

    # Learning rate
    LEARNING_RATE = 0.1

    # Minimum number of trades before calibration update
    MIN_TRADES_FOR_CALIBRATION = 20

    def __init__(self, state_dir: str = "/home/davidsanker/platform/state"):
        self.state_dir = Path(state_dir)
        self.state_file = self.state_dir / "learner_state.json"

        # Load existing state or initialize defaults
        self.weights = self.DEFAULT_WEIGHTS.copy()
        self.statistics = {
            'total_updates': 0,
            'total_trades_learned': 0,
            'last_update_time': None,
            'weight_history': []
        }

        self._load_state()

    def _load_state(self):
        """Load learner state from file."""
        if self.state_file.exists():
            try:
                with open(self.state_file, 'r') as f:
                    state = json.load(f)
                    self.weights = state.get('signal_weights', self.DEFAULT_WEIGHTS)
                    self.statistics = state.get('statistics', self.statistics)
            except Exception as e:
                print(f"⚠️  Error loading state: {e}, using defaults")

    def _save_state(self):
        """Save learner state to file (with backup)."""
        # Backup existing state
        if self.state_file.exists():
            backup_file = self.state_file.with_suffix(
                f'.json.v{self.statistics["total_updates"] % 10}'
            )
            self.state_file.rename(backup_file)

        # Prepare state
        state = {
            'version': '1.0',
            'last_updated': datetime.utcnow().isoformat(),
            'signal_weights': self.weights,
            'statistics': self.statistics
        }

        # Save new state
        self.state_file.parent.mkdir(parents=True, exist_ok=True)
        with open(self.state_file, 'w') as f:
            json.dump(state, f, indent=2)

    def _clamp_weight(self, weight: float) -> float:
        """Clamp weight to valid range."""
        return max(self.MIN_WEIGHT, min(self.MAX_WEIGHT, weight))

    def update_weights(self, signal_contributions: Dict[str, float],
                      outcome: Dict[str, Any]) -> Dict[str, float]:
        """
        Update signal weights based on their contribution to trade outcome.

        Uses multiplicative weights algorithm:
        - If trade was profitable (hit), increase weights for signals that contributed positively
        - If trade was unprofitable (miss), decrease weights for signals that contributed negatively

        Args:
            signal_contributions: Dict mapping signal names to their attributed P&L
            outcome: Outcome dict with 'hit' bool and 'return_pct'

        Returns:
            Updated weights dict
        """
        hit = outcome.get('hit', False)
        return_pct = outcome.get('return_pct', 0.0)

        # Adjust learning rate based on magnitude of outcome
        # Larger outcomes → larger updates
        adjusted_lr = self.LEARNING_RATE * (1 + abs(return_pct) / 100)

        weight_deltas = {}

        for signal, contribution in signal_contributions.items():
            if signal not in self.weights:
                self.weights[signal] = 1.0

            old_weight = self.weights[signal]

            # Normalize contribution by P&L magnitude to get direction
            # Positive contribution helped, negative hurt
            if contribution > 0:
                direction = 1  # Signal helped
            else:
                direction = -1  # Signal hurt

            if hit:
                # Profitable trade: reinforce helpful signals, penalize harmful
                if direction > 0:
                    # Signal contributed to profit → increase weight
                    new_weight = old_weight * (1 + adjusted_lr * abs(contribution) / 1000)
                else:
                    # Signal worked against profit → decrease weight
                    new_weight = old_weight * (1 - adjusted_lr * abs(contribution) / 1000)
            else:
                # Unprofitable trade: penalize signals that led to loss
                if direction > 0:
                    # Signal suggested losing trade → decrease weight
                    new_weight = old_weight * (1 - adjusted_lr * abs(contribution) / 1000)
                else:
                    # Signal warned against loss → increase weight
                    new_weight = old_weight * (1 + adjusted_lr * abs(contribution) / 1000)

            # Clamp weight to bounds
            new_weight = self._clamp_weight(new_weight)
            self.weights[signal] = new_weight

            # Record delta
            weight_deltas[signal] = new_weight - old_weight

        # Update statistics
        self.statistics['total_updates'] += 1
        self.statistics['total_trades_learned'] += 1
        self.statistics['last_update_time'] = datetime.utcnow().isoformat()
        self.statistics['weight_history'].append({
            'timestamp': datetime.utcnow().isoformat(),
            'weights': self.weights.copy(),
            'deltas': weight_deltas,
            'outcome_hit': hit,
            'outcome_return_pct': return_pct
        })

        # Keep only last 100 weight updates in history
        if len(self.statistics['weight_history']) > 100:
            self.statistics['weight_history'] = self.statistics['weight_history'][-100:]

        # Save state
        self._save_state()

        return weight_deltas

    def get_weights(self) -> Dict[str, float]:
        """Get current signal weights."""
        return self.weights.copy()

    def get_weight_ranking(self) -> List[tuple]:
        """Get signals ranked by current weight (highest to lowest)."""
        return sorted(self.weights.items(), key=lambda x: x[1], reverse=True)

    def get_top_improvements(self, n: int = 5) -> List[Dict[str, Any]]:
        """
        Get the signals with the largest positive weight changes.

        Args:
            n: Number of top signals to return

        Returns:
            List of dicts with signal name and total improvement
        """
        if not self.statistics['weight_history']:
            return []

        # Sum all weight deltas for each signal
        total_deltas = {}
        for entry in self.statistics['weight_history']:
            for signal, delta in entry['deltas'].items():
                if signal not in total_deltas:
                    total_deltas[signal] = 0.0
                total_deltas[signal] += delta

        # Sort by improvement
        ranked = sorted(total_deltas.items(), key=lambda x: x[1], reverse=True)

        return [
            {'signal': signal, 'total_improvement': delta}
            for signal, delta in ranked[:n]
            if delta > 0
        ]

    def get_statistics(self) -> Dict[str, Any]:
        """Get learner statistics."""
        return {
            'weights': self.weights,
            'total_updates': self.statistics['total_updates'],
            'total_trades_learned': self.statistics['total_trades_learned'],
            'last_update': self.statistics['last_update_time'],
            'weight_ranking': self.get_weight_ranking(),
            'top_improvements': self.get_top_improvements(5)
        }

    def reset_weights(self):
        """Reset weights to default values (safety function)."""
        self.weights = self.DEFAULT_WEIGHTS.copy()
        self._save_state()
        print("✅ Weights reset to defaults")


if __name__ == "__main__":
    # Test weight learner
    learner = SignalWeightLearner()

    print("📊 Initial weights:")
    for signal, weight in learner.get_weights().items():
        print(f"   {signal}: {weight:.2f}")

    # Simulate learning from a profitable trade
    signal_contributions = {
        'trend': 250.0,
        'momentum': 150.0,
        'mean_reversion': -50.0,
        'volume': 100.0,
        'volatility': 50.0
    }

    outcome = {
        'hit': True,
        'return_pct': 2.5
    }

    print("\n🔄 Learning from profitable trade...")
    deltas = learner.update_weights(signal_contributions, outcome)

    print("\n📊 Updated weights:")
    for signal, weight in learner.get_weights().items():
        delta = deltas.get(signal, 0.0)
        arrow = "↑" if delta > 0 else "↓" if delta < 0 else "→"
        print(f"   {signal}: {weight:.2f} ({arrow}{abs(delta):.3f})")

    print(f"\n✅ Total updates: {learner.statistics['total_updates']}")
