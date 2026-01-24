#!/usr/bin/env python3
"""
Baseline Signal Models

Implements signal generation models:
- SignalGeneratorModel: Wrapper for existing signal_generator
- GradientBoostingSignalModel: Tree-based classifier (sklearn)
"""

import numpy as np
from typing import Dict, Any, List
import logging

from models.interfaces import SignalModel, SignalResult, ModelMetadata

logger = logging.getLogger(__name__)


class SignalGeneratorModel(SignalModel):
    """
    Wrapper for existing signal_generator.py

    Maintains backward compatibility with existing system.
    """

    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.enable_multi_signal = config.get('enable_multi_signal', True)
        self.confidence_threshold = config.get('confidence_threshold', 0.75)
        self.lookback_period = config.get('lookback_period', 20)

        # Try to import existing signal generator
        try:
            # Import from config directory (adjust path as needed)
            from config.signal_generator import SignalGenerator
            self.signal_generator = SignalGenerator(config)
            self.has_signal_generator = True
        except ImportError:
            logger.warning("Could not import signal_generator, using fallback")
            self.signal_generator = None
            self.has_signal_generator = False

        # Update metadata
        self.metadata = ModelMetadata(
            name="SignalGeneratorModel",
            version="2.0.0",  # Existing version
            model_type="signal",
            parameters=config
        )

    def generate_signal(self, features: Dict[str, Any],
                       forecast=None) -> SignalResult:
        """
        Generate signal using existing signal_generator.

        Args:
            features: Dictionary with prices, indicators, etc.
            forecast: Optional forecast result

        Returns:
            SignalResult with action, confidence, reasons
        """
        if self.has_signal_generator and self.signal_generator:
            # Use existing signal generator
            try:
                # Call existing signal generation logic
                signal_data = self.signal_generator.generate(features)

                # Convert to SignalResult format
                action = signal_data.get('action', 'HOLD')
                confidence = signal_data.get('confidence', 0.75)
                reasons = signal_data.get('reasons', ['Signal generator'])
                signal_components = signal_data.get('signal_components', {})

                # Apply confidence threshold
                if confidence < self.confidence_threshold:
                    action = 'HOLD'
                    reasons.append(f"Confidence {confidence:.2f} below threshold {self.confidence_threshold}")

                return SignalResult(
                    action=action,
                    confidence=confidence,
                    reasons=reasons,
                    signal_components=signal_components,
                    metadata={'source': 'signal_generator'}
                )

            except Exception as e:
                logger.error(f"Signal generator failed: {e}")
                # Fall back to simple signal
                pass

        # Fallback: Simple momentum signal
        returns = features.get('returns', [])
        if len(returns) >= 5:
            recent_returns = returns[-5:]
            avg_return = np.mean(recent_returns)

            if avg_return > 0.005:  # > 0.5%
                action = 'BUY'
                confidence = min(0.85, 0.5 + avg_return * 10)
                reasons = [f"Positive momentum: {avg_return:.2%} avg return"]
            elif avg_return < -0.005:  # < -0.5%
                action = 'SELL'
                confidence = min(0.85, 0.5 + abs(avg_return) * 10)
                reasons = [f"Negative momentum: {avg_return:.2%} avg return"]
            else:
                action = 'HOLD'
                confidence = 0.75
                reasons = ['Neutral momentum']

            # Simple signal components
            signal_components = {
                'momentum': avg_return,
                'trend': np.mean(returns[-10:]) if len(returns) >= 10 else 0.0
            }

            return SignalResult(
                action=action,
                confidence=confidence,
                reasons=reasons,
                signal_components=signal_components,
                metadata={'source': 'momentum_fallback'}
            )

        # Not enough data
        return SignalResult(
            action='HOLD',
            confidence=0.5,
            reasons=['Insufficient data for signal generation'],
            signal_components={},
            metadata={'source': 'nodata'}
        )

    def train(self, X: np.ndarray, y: np.ndarray) -> None:
        """Signal generator doesn't require training."""
        pass


class GradientBoostingSignalModel(SignalModel):
    """
    Gradient Boosting signal model using sklearn.

    Tree-based classifier that learns from historical labels.
    Falls back to simple rules if sklearn not available.
    """

    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.n_estimators = config.get('n_estimators', 100)
        self.max_depth = config.get('max_depth', 3)
        self.learning_rate = config.get('learning_rate', 0.1)

        # Try to import sklearn
        try:
            from sklearn.ensemble import GradientBoostingClassifier
            self.sklearn_available = True
            self.model = GradientBoostingClassifier(
                n_estimators=self.n_estimators,
                max_depth=self.max_depth,
                learning_rate=self.learning_rate,
                random_state=42
            )
            self.is_trained = False
        except ImportError:
            logger.warning("sklearn not available, using fallback")
            self.sklearn_available = False
            self.model = None
            self.is_trained = False

        # Update metadata
        self.metadata = ModelMetadata(
            name="GradientBoostingSignalModel",
            version="1.0.0",
            model_type="signal",
            parameters=config
        )

    def _extract_features(self, features: Dict[str, Any]) -> np.ndarray:
        """Extract feature vector from features dict."""
        # Simple feature engineering
        returns = features.get('returns', [])
        prices = features.get('prices', [])

        feature_vector = []

        # Recent returns
        if len(returns) >= 5:
            feature_vector.extend(returns[-5:])
        else:
            feature_vector.extend([0.0] * 5)

        # Moving averages
        if len(returns) >= 10:
            feature_vector.append(np.mean(returns[-5:]))  # Short-term MA
            feature_vector.append(np.mean(returns[-10:]))  # Long-term MA
        else:
            feature_vector.extend([0.0, 0.0])

        # Volatility
        if len(returns) >= 10:
            feature_vector.append(np.std(returns[-10:]))
        else:
            feature_vector.append(0.0)

        # Price momentum
        if len(prices) >= 10:
            price_return = (prices[-1] - prices[-10]) / prices[-10]
            feature_vector.append(price_return)
        else:
            feature_vector.append(0.0)

        return np.array(feature_vector).reshape(1, -1)

    def generate_signal(self, features: Dict[str, Any],
                       forecast=None) -> SignalResult:
        """Generate signal using gradient boosting or fallback."""
        if not self.sklearn_available or not self.is_trained:
            # Fallback to simple signal
            return self._fallback_signal(features)

        # Extract features
        X = self._extract_features(features)

        # Predict
        try:
            prediction = self.model.predict(X)[0]
            probabilities = self.model.predict_proba(X)[0]

            # Convert to action
            # Assuming labels: 1=BUY, 0=HOLD, -1=SELL
            if prediction == 1:
                action = 'BUY'
                confidence = probabilities[1]  # Probability of BUY
            elif prediction == -1:
                action = 'SELL'
                confidence = probabilities[0]  # Probability of SELL
            else:
                action = 'HOLD'
                confidence = max(probabilities)  # Highest probability

            reasons = [
                f"Gradient boosting prediction: {action}",
                f"Class probabilities: BUY={probabilities[1]:.2f}, HOLD={probabilities[2]:.2f}, SELL={probabilities[0]:.2f}"
            ]

            # Signal components (feature importance)
            returns_list = features.get('returns', [])
            momentum_val = returns_list[-1] if returns_list else 0

            trend_list = features.get('returns', [])
            if len(trend_list) >= 5:
                trend_val = np.mean(trend_list[-5:])
            else:
                trend_val = 0.0

            signal_components = {
                'momentum': momentum_val,
                'trend': trend_val
            }

            return SignalResult(
                action=action,
                confidence=confidence,
                reasons=reasons,
                signal_components=signal_components,
                metadata={'source': 'gradient_boosting'}
            )

        except Exception as e:
            logger.error(f"Gradient boosting prediction failed: {e}")
            return self._fallback_signal(features)

    def _fallback_signal(self, features: Dict[str, Any]) -> SignalResult:
        """Simple fallback signal."""
        returns = features.get('returns', [])

        if len(returns) >= 3:
            avg_return = np.mean(returns[-3:])

            if avg_return > 0.01:
                action = 'BUY'
                confidence = 0.7
                reasons = [f"Positive recent returns: {avg_return:.2%}"]
            elif avg_return < -0.01:
                action = 'SELL'
                confidence = 0.7
                reasons = [f"Negative recent returns: {avg_return:.2%}"]
            else:
                action = 'HOLD'
                confidence = 0.75
                reasons = ['Neutral returns']

            signal_components = {'momentum': avg_return}

            return SignalResult(
                action=action,
                confidence=confidence,
                reasons=reasons,
                signal_components=signal_components,
                metadata={'source': 'gb_fallback'}
            )

        return SignalResult(
            action='HOLD',
            confidence=0.5,
            reasons=['Insufficient data'],
            signal_components={},
            metadata={'source': 'nodata_fallback'}
        )

    def train(self, X: np.ndarray, y: np.ndarray) -> None:
        """Train gradient boosting model."""
        if self.sklearn_available and X is not None and y is not None:
            try:
                self.model.fit(X, y)
                self.is_trained = True
                logger.info(f"Gradient boosting model trained on {len(X)} samples")
            except Exception as e:
                logger.error(f"Training failed: {e}")
        else:
            logger.warning("Cannot train: sklearn not available or no data")


if __name__ == "__main__":
    # Test baseline signal models
    print("Testing baseline signal models...")

    # Sample features
    features = {
        'returns': [0.01, 0.015, -0.005, 0.02, 0.008, 0.012, -0.003, 0.025, 0.007, 0.018],
        'prices': [100, 101, 100.5, 102.5, 103.3, 104.5, 104.2, 106.8, 107.5, 109.4]
    }

    # Test SignalGeneratorModel
    print("\n✅ SignalGeneratorModel:")
    sg_model = SignalGeneratorModel({})
    result = sg_model.generate_signal(features)
    print(f"   Action: {result.action}")
    print(f"   Confidence: {result.confidence:.2f}")
    print(f"   Reasons: {result.reasons}")

    # Test GradientBoostingSignalModel
    print("\n✅ GradientBoostingSignalModel:")
    gb_model = GradientBoostingSignalModel({})
    result = gb_model.generate_signal(features)
    print(f"   Action: {result.action}")
    print(f"   Confidence: {result.confidence:.2f}")
    print(f"   Reasons: {result.reasons}")

    print("\n✅ Baseline signal models working correctly")
