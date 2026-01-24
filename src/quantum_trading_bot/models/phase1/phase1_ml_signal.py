#!/usr/bin/env python3
"""
Phase 1 Integration: ML Model Signal Model
Wraps Phase 1 trained ML models (.joblib) as a Model Zoo SignalModel
"""

import sys
import os
from pathlib import Path
from typing import Dict, Any, Optional
import numpy as np
import pandas as pd
import joblib
import logging

# Add Phase 1 to path
phase1_path = Path(__file__).parent.parent.parent / "phase1"
sys.path.insert(0, str(phase1_path))

from models.interfaces import SignalModel, SignalResult, ModelMetadata

logger = logging.getLogger(__name__)


class Phase1MLSignal(SignalModel):
    """
    SignalModel wrapper for Phase 1 trained ML models.

    Loads .joblib model files and generates signals using ML predictions.
    """

    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)

        # Extract configuration
        self.model_path = config.get('model_path', '')
        self.confidence_threshold = config.get('confidence_threshold', 0.6)

        # Validate model path
        if not self.model_path or not os.path.exists(self.model_path):
            raise ValueError(f"Invalid model_path: {self.model_path}")

        # Load Phase 1 model
        self.model_data = joblib.load(self.model_path)
        self.model = self.model_data['model']
        self.feature_names = self.model_data.get('feature_names', [])
        self.model_type = self.model_data.get('model_type', 'unknown')

        # Update metadata
        self.metadata.parameters = {
            'model_path': self.model_path,
            'model_type': self.model_type,
            'confidence_threshold': self.confidence_threshold,
            'n_features': len(self.feature_names)
        }

        logger.info(f"Loaded Phase 1 ML model: {self.model_type} from {self.model_path}")
        logger.info(f"Features: {len(self.feature_names)}")

    def generate_signal(
        self,
        features: Dict[str, Any],
        forecast: Optional[Any] = None
    ) -> SignalResult:
        """
        Generate signal using Phase 1 ML model.

        Args:
            features: Dictionary of features
            forecast: Optional forecast (not used)

        Returns:
            SignalResult with action, confidence, and reasons
        """
        try:
            # Prepare features for model
            X = self._prepare_features(features)

            if X is None:
                return SignalResult(
                    action='HOLD',
                    confidence=0.0,
                    reasons=['Insufficient or invalid features for ML prediction'],
                    signal_components={},
                    metadata={'error': 'invalid_features'}
                )

            # Make prediction
            prediction = self.model.predict(X)[0]

            # Get probability if available
            if hasattr(self.model, 'predict_proba'):
                proba = self.model.predict_proba(X)[0]
                confidence = float(proba[1]) if len(proba) > 1 else float(proba[0])
            else:
                # Use fixed confidence for models without probability
                confidence = 0.7

            # Convert prediction to action
            if prediction == 1:
                action = 'BUY'
            elif prediction == 0:
                action = 'SELL'
            else:
                action = 'HOLD'

            # Apply confidence threshold
            if confidence < self.confidence_threshold:
                action = 'HOLD'
                reasons = [f"Low confidence ({confidence:.2f} < {self.confidence_threshold}) - HOLD"]
            else:
                reasons = self._generate_reasons(action, confidence, features, prediction)

            # Extract feature importance if available
            signal_components = self._extract_signal_components(features, X)

            return SignalResult(
                action=action,
                confidence=confidence,
                reasons=reasons,
                signal_components=signal_components,
                metadata={
                    'phase1_strategy': 'ml_model',
                    'phase1_params': self.metadata.parameters,
                    'prediction': int(prediction),
                    'model_type': self.model_type,
                    'features_used': len(self.feature_names)
                }
            )

        except Exception as e:
            logger.error(f"Error generating ML signal: {e}")
            return SignalResult(
                action='HOLD',
                confidence=0.0,
                reasons=[f'Error generating signal: {str(e)}'],
                signal_components={},
                metadata={'error': str(e), 'phase1_strategy': 'ml_model'}
            )

    def train(self, X: np.ndarray, y: np.ndarray) -> None:
        """
        Model already trained - this is a no-op.

        Args:
            X: Not used (model pre-trained)
            y: Not used (model pre-trained)
        """
        pass

    def _prepare_features(self, features: Dict[str, Any]) -> Optional[np.ndarray]:
        """
        Prepare features for ML model.

        Args:
            features: Dictionary of features

        Returns:
            Feature array ready for model prediction, or None if invalid
        """
        try:
            # Flatten features dict
            flat_features = {}
            for key, value in features.items():
                if isinstance(value, dict):
                    flat_features.update(value)
                else:
                    flat_features[key] = value

            # Handle feature name mapping
            # Phase 1 uses names like "Close", Phase 2 might use "price_close"
            feature_mapping = {
                'price_close': 'Close',
                'price_open': 'Open',
                'price_high': 'High',
                'price_low': 'Low',
                'sma_10': 'SMA_10',
                'sma_20': 'SMA_20',
                'sma_50': 'SMA_50',
                'sma_200': 'SMA_200',
                'rsi': 'RSI',
                'macd': 'MACD'
            }

            # Apply mapping
            for phase2_name, phase1_name in feature_mapping.items():
                if phase2_name in flat_features and phase1_name not in flat_features:
                    flat_features[phase1_name] = flat_features[phase2_name]

            # Extract features in correct order
            feature_values = []
            missing_features = []

            for feat_name in self.feature_names:
                if feat_name in flat_features:
                    value = flat_features[feat_name]
                    # Handle NaN/None
                    if pd.isna(value) or value is None:
                        missing_features.append(feat_name)
                        feature_values.append(0.0)
                    else:
                        feature_values.append(float(value))
                else:
                    missing_features.append(feat_name)
                    feature_values.append(0.0)

            if missing_features:
                logger.warning(f"Missing features for ML model: {missing_features}")

            # Return as 2D array (single sample)
            return np.array([feature_values])

        except Exception as e:
            logger.error(f"Error preparing features: {e}")
            return None

    def _generate_reasons(
        self,
        action: str,
        confidence: float,
        features: Dict[str, Any],
        prediction: int
    ) -> list:
        """Generate human-readable reasons for the signal."""
        reasons = []

        if action == 'BUY':
            reasons.append(f"ML model predicts UP (class={prediction}) with confidence {confidence:.2f}")
        elif action == 'SELL':
            reasons.append(f"ML model predicts DOWN (class={prediction}) with confidence {confidence:.2f}")
        else:
            reasons.append(f"ML model signal: {action}")

        # Add context about key features
        rsi = features.get('rsi', features.get('RSI', None))
        if rsi is not None:
            if action == 'BUY' and rsi < 40:
                reasons.append(f"RSI ({rsi:.1f}) confirms oversold condition")
            elif action == 'SELL' and rsi > 60:
                reasons.append(f"RSI ({rsi:.1f}) confirms overbought condition")

        # Add model type info
        reasons.append(f"Model type: {self.model_type}")

        return reasons

    def _extract_signal_components(
        self,
        features: Dict[str, Any],
        X: np.ndarray
    ) -> Dict[str, float]:
        """Extract feature contributions for transparency."""
        components = {}

        # If model has feature importance, include it
        if hasattr(self.model, 'feature_importances_'):
            for i, feat_name in enumerate(self.feature_names):
                if i < len(self.model.feature_importances_):
                    components[f'importance_{feat_name}'] = float(self.model.feature_importances_[i])

        # Include top features by value
        flat_features = {}
        for key, value in features.items():
            if isinstance(value, dict):
                flat_features.update(value)
            elif isinstance(value, (int, float)):
                flat_features[key] = value

        # Add feature values
        for feat_name in self.feature_names[:5]:  # Top 5
            if feat_name in flat_features:
                components[feat_name] = float(flat_features[feat_name])

        return components
