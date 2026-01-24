#!/usr/bin/env python3
"""
Confidence Calibrator - Calibrate confidence scores to match empirical hit rates.

Uses Platt scaling (logistic regression) and calibration bins.
"""

import json
import numpy as np
from typing import Dict, List, Any, Optional
from pathlib import Path
from datetime import datetime
from collections import defaultdict


class ConfidenceCalibrator:
    """Calibrate confidence scores to match empirical hit rates."""

    # Calibration bin edges
    BIN_EDGES = [0.0, 0.2, 0.4, 0.6, 0.8, 1.0]

    # Minimum predictions per bin for reliable calibration
    MIN_PREDICTIONS_PER_BIN = 10

    def __init__(self, state_dir: str = "/home/davidsanker/platform/state"):
        self.state_dir = Path(state_dir)
        self.state_file = self.state_dir / "learner_state.json"

        # Calibration parameters (Platt scaling: sigmoid(A * x + B))
        self.platt_A = 1.0
        self.platt_B = 0.0

        # Calibration bins: empirical hit rates per confidence range
        self.calibration_bins = {}

        # Initialize bins
        for i in range(len(self.BIN_EDGES) - 1):
            bin_name = f"{self.BIN_EDGES[i]}-{self.BIN_EDGES[i+1]}"
            self.calibration_bins[bin_name] = {
                'predictions': 0,
                'hits': 0,
                'hit_rate': 0.0
            }

        # Statistics
        self.statistics = {
            'total_calibrations': 0,
            'last_calibration_time': None
        }

        self._load_state()

    def _load_state(self):
        """Load calibration state from file."""
        if self.state_file.exists():
            try:
                with open(self.state_file, 'r') as f:
                    state = json.load(f)

                    # Load calibration parameters
                    calibration = state.get('calibration_params', {})
                    self.platt_A = calibration.get('A', 1.0)
                    self.platt_B = calibration.get('B', 0.0)

                    # Load calibration bins
                    self.calibration_bins = state.get('calibration_bins', self.calibration_bins)

                    # Load statistics
                    self.statistics = state.get('statistics', {})
                    if 'total_calibrations' not in self.statistics:
                        self.statistics['total_calibrations'] = 0

            except Exception as e:
                print(f"⚠️  Error loading calibration state: {e}, using defaults")

    def _save_state(self):
        """Save calibration state to file."""
        # Load full state to preserve other components
        full_state = {}
        if self.state_file.exists():
            with open(self.state_file, 'r') as f:
                full_state = json.load(f)

        # Update calibration components
        full_state['calibration_params'] = {
            'A': self.platt_A,
            'B': self.platt_B
        }
        full_state['calibration_bins'] = self.calibration_bins
        full_state['statistics'] = {
            **full_state.get('statistics', {}),
            'total_calibrations': self.statistics['total_calibrations'],
            'last_calibration_time': self.statistics['last_calibration_time']
        }

        # Save
        self.state_file.parent.mkdir(parents=True, exist_ok=True)
        with open(self.state_file, 'w') as f:
            json.dump(full_state, f, indent=2)

    def apply_platt_scaling(self, raw_confidence: float) -> float:
        """
        Apply Platt scaling to raw confidence.

        Platt scaling: calibrated = sigmoid(A * raw + B)
        sigmoid(x) = 1 / (1 + exp(-x))

        Args:
            raw_confidence: Raw confidence score [0, 1]

        Returns:
            Calibrated confidence [0, 1]
        """
        if raw_confidence < 0 or raw_confidence > 1:
            raise ValueError(f"Raw confidence must be in [0, 1], got {raw_confidence}")

        # Apply Platt scaling
        z = self.platt_A * raw_confidence + self.platt_B
        calibrated = 1.0 / (1.0 + np.exp(-z))

        # Clamp to [0, 1]
        return max(0.0, min(1.0, calibrated))

    def update_bins(self, raw_confidence: float, hit: bool):
        """
        Update calibration bins with a new prediction result.

        Args:
            raw_confidence: Raw confidence score [0, 1]
            hit: True if prediction was correct, False otherwise
        """
        # Find the bin
        bin_name = None
        for i in range(len(self.BIN_EDGES) - 1):
            if self.BIN_EDGES[i] <= raw_confidence < self.BIN_EDGES[i+1]:
                bin_name = f"{self.BIN_EDGES[i]}-{self.BIN_EDGES[i+1]}"
                break

        # Handle edge case where confidence == 1.0
        if bin_name is None and raw_confidence == 1.0:
            bin_name = "0.8-1.0"

        if bin_name:
            self.calibration_bins[bin_name]['predictions'] += 1
            if hit:
                self.calibration_bins[bin_name]['hits'] += 1

            # Update hit rate
            total = self.calibration_bins[bin_name]['predictions']
            hits = self.calibration_bins[bin_name]['hits']
            self.calibration_bins[bin_name]['hit_rate'] = hits / total if total > 0 else 0.0

            # Save state
            self._save_state()

    def calibrate_from_bins(self) -> Dict[str, float]:
        """
        Recalibrate Platt parameters using bin hit rates.

        Uses simple linear regression on bin midpoints vs hit rates.

        Returns:
            Dict with calibration error metrics
        """
        # Collect bins with enough data
        bin_data = []
        for i in range(len(self.BIN_EDGES) - 1):
            bin_name = f"{self.BIN_EDGES[i]}-{self.BIN_EDGES[i+1]}"
            bin_info = self.calibration_bins[bin_name]

            if bin_info['predictions'] >= self.MIN_PREDICTIONS_PER_BIN:
                # Use midpoint of bin as raw confidence
                midpoint = (self.BIN_EDGES[i] + self.BIN_EDGES[i+1]) / 2
                # Use log-odds of hit rate as target
                hit_rate = bin_info['hit_rate']

                # Avoid log(0)
                hit_rate = max(0.01, min(0.99, hit_rate))

                log_odds = np.log(hit_rate / (1 - hit_rate))
                bin_data.append((midpoint, log_odds))

        if len(bin_data) < 2:
            print("⚠️  Not enough bin data for calibration")
            return {'error': 'insufficient_data'}

        # Simple linear regression: log_odds = A * raw_confidence + B
        X = np.array([x for x, y in bin_data])
        Y = np.array([y for x, y in bin_data])

        # Fit line
        A, B = np.polyfit(X, Y, 1)

        # Update parameters
        old_A, old_B = self.platt_A, self.platt_B
        self.platt_A = float(A)
        self.platt_B = float(B)

        # Update statistics
        self.statistics['total_calibrations'] += 1
        self.statistics['last_calibration_time'] = datetime.utcnow().isoformat()

        # Save state
        self._save_state()

        # Compute calibration error
        calibration_error = self._compute_calibration_error(bin_data)

        print(f"✅ Calibration updated: A={A:.3f}, B={B:.3f} (was A={old_A:.3f}, B={old_B:.3f})")

        return {
            'A': self.platt_A,
            'B': self.platt_B,
            'old_A': old_A,
            'old_B': old_B,
            'calibration_error': calibration_error,
            'bins_used': len(bin_data)
        }

    def _compute_calibration_error(self, bin_data: List[tuple]) -> float:
        """Compute mean squared error of calibration."""
        errors = []
        for raw_conf, log_odds in bin_data:
            predicted_log_odds = self.platt_A * raw_conf + self.platt_B
            errors.append((predicted_log_odds - log_odds) ** 2)

        return np.mean(errors) if errors else 0.0

    def get_calibration_report(self) -> Dict[str, Any]:
        """Generate a comprehensive calibration report."""
        report = {
            'platt_params': {
                'A': self.platt_A,
                'B': self.platt_B
            },
            'calibration_bins': [],
            'statistics': self.statistics
        }

        # Add bin information
        for i in range(len(self.BIN_EDGES) - 1):
            bin_name = f"{self.BIN_EDGES[i]}-{self.BIN_EDGES[i+1]}"
            bin_info = self.calibration_bins[bin_name].copy()

            # Compute expected vs actual hit rate
            midpoint = (self.BIN_EDGES[i] + self.BIN_EDGES[i+1]) / 2
            expected_hit_rate = self.apply_platt_scaling(midpoint)
            actual_hit_rate = bin_info['hit_rate']

            bin_info['bin'] = bin_name
            bin_info['midpoint'] = midpoint
            bin_info['expected_hit_rate'] = expected_hit_rate
            bin_info['actual_hit_rate'] = actual_hit_rate
            bin_info['calibration_error'] = abs(expected_hit_rate - actual_hit_rate)

            report['calibration_bins'].append(bin_info)

        return report

    def shadow_update(self, raw_confidence: float,
                     predicted_direction: str,
                     actual_direction: str) -> bool:
        """
        Shadow learning update: update calibration bins without trading.

        Determines if prediction was correct by comparing predicted vs actual direction.

        Args:
            raw_confidence: Raw confidence score
            predicted_direction: 'BUY' or 'SELL'
            actual_direction: 'UP' or 'DOWN' (price movement)

        Returns:
            True if prediction was correct (hit), False otherwise
        """
        # Determine if prediction was correct
        hit = (predicted_direction == 'BUY' and actual_direction == 'UP') or \
              (predicted_direction == 'SELL' and actual_direction == 'DOWN')

        # Update bins
        self.update_bins(raw_confidence, hit)

        return hit


if __name__ == "__main__":
    # Test calibrator
    calibrator = ConfidenceCalibrator()

    print("📊 Initial calibration parameters:")
    print(f"   Platt A: {calibrator.platt_A:.3f}")
    print(f"   Platt B: {calibrator.platt_B:.3f}")

    # Simulate some predictions with outcomes
    print("\n🔄 Simulating predictions...")

    test_cases = [
        (0.7, True),
        (0.8, True),
        (0.6, False),
        (0.9, True),
        (0.5, True),
        (0.4, False),
        (0.3, False),
        (0.75, True),
        (0.65, True),
        (0.55, False),
        (0.85, True),
        (0.45, False),
        (0.35, True),
        (0.95, True),
        (0.25, False)
    ]

    for confidence, hit in test_cases:
        calibrator.update_bins(confidence, hit)

    print("\n📊 Calibration bins after updates:")
    for bin_info in calibrator.get_calibration_report()['calibration_bins']:
        if bin_info['predictions'] > 0:
            print(f"   {bin_info['bin']}: {bin_info['predictions']} predictions, "
                  f"hit rate = {bin_info['hit_rate']:.2f}")

    # Test Platt scaling
    print(f"\n🔄 Applying Platt scaling to confidence 0.75:")
    raw = 0.75
    calibrated = calibrator.apply_platt_scaling(raw)
    print(f"   Raw: {raw:.2f} → Calibrated: {calibrated:.2f}")
