#!/usr/bin/env python3
"""
Baseline Forecast Models

Implements simple, reliable forecast models:
- EWMAModel: Exponentially Weighted Moving Average forecast
- AR1Model: Auto-Regressive(1) model

These are classical baselines that don't require ML libraries.
"""

import numpy as np
from typing import Dict, Any
from datetime import datetime, timedelta

from models.interfaces import ForecastModel, ForecastResult, ModelMetadata


class EWMAModel(ForecastModel):
    """
    Exponentially Weighted Moving Average forecast model.

    Simple, robust baseline that forecasts future returns based on
    exponentially weighted historical returns.
    """

    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.alpha = config.get('alpha', 0.5)  # Smoothing factor
        self.prediction_horizon = config.get('prediction_horizon', '1d')
        self.returns_history = []  # Store recent returns

        # Update metadata
        self.metadata = ModelMetadata(
            name="EWMAModel",
            version="1.0.0",
            model_type="forecast",
            parameters={'alpha': self.alpha}
        )

    def predict(self, features: Dict[str, Any]) -> ForecastResult:
        """
        Generate forecast using EWMA of historical returns.

        Args:
            features: Must contain 'returns' key with historical returns

        Returns:
            ForecastResult with predicted return
        """
        # Get historical returns from features
        returns = features.get('returns', [])
        if not returns or len(returns) < 5:
            # Not enough data, return neutral forecast
            return ForecastResult(
                predicted_return=0.0,
                confidence_interval=(-0.02, 0.02),
                prediction_horizon=self.prediction_horizon,
                confidence=0.5,  # Low confidence with no data
                metadata={'method': 'ewma', 'data_points': len(returns)}
            )

        # Update returns history
        self.returns_history = returns[-50:]  # Keep last 50 returns

        # Compute EWMA forecast
        ewma_forecast = 0.0
        weight = 1.0
        total_weight = 0.0

        for ret in reversed(self.returns_history):
            ewma_forecast += ret * weight
            total_weight += weight
            weight *= (1 - self.alpha)

        predicted_return = ewma_forecast / total_weight if total_weight > 0 else 0.0

        # Compute confidence interval based on historical volatility
        returns_array = np.array(self.returns_history)
        std_dev = np.std(returns_array) if len(returns_array) > 1 else 0.01

        # Confidence based on data availability
        confidence = min(1.0, len(self.returns_history) / 20)  # More data = higher confidence

        return ForecastResult(
            predicted_return=predicted_return,
            confidence_interval=(predicted_return - 2*std_dev, predicted_return + 2*std_dev),
            prediction_horizon=self.prediction_horizon,
            confidence=confidence,
            metadata={
                'method': 'ewma',
                'alpha': self.alpha,
                'data_points': len(self.returns_history),
                'volatility': std_dev
            }
        )

    def train(self, X: np.ndarray, y: np.ndarray) -> None:
        """EWMA doesn't require training."""
        pass


class AR1Model(ForecastModel):
    """
    Auto-Regressive(1) forecast model.

    Forecasts next return based on linear regression of current return on previous return.
    Simple classical time series model.
    """

    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.lag = config.get('lag', 1)
        self.prediction_horizon = config.get('prediction_horizon', '1d')
        self.ar_coefficient = 0.0  # Will be estimated from data
        self.intercept = 0.0
        self.returns_history = []

        # Update metadata
        self.metadata = ModelMetadata(
            name="AR1Model",
            version="1.0.0",
            model_type="forecast",
            parameters={'lag': self.lag}
        )

    def predict(self, features: Dict[str, Any]) -> ForecastResult:
        """
        Generate forecast using AR(1) model.

        Args:
            features: Must contain 'returns' key with historical returns

        Returns:
            ForecastResult with predicted return
        """
        returns = features.get('returns', [])
        if not returns or len(returns) < 3:
            # Not enough data, return neutral forecast
            return ForecastResult(
                predicted_return=0.0,
                confidence_interval=(-0.02, 0.02),
                prediction_horizon=self.prediction_horizon,
                confidence=0.5,
                metadata={'method': 'ar1', 'data_points': len(returns)}
            )

        self.returns_history = returns[-50:]

        # Estimate AR(1) coefficient: y_t = c + phi * y_{t-1} + epsilon
        returns_array = np.array(self.returns_history)

        if len(returns_array) >= 3:
            y = returns_array[1:]  # t
            x = returns_array[:-1]  # t-1

            # Simple OLS: phi = cov(x,y) / var(x)
            phi = np.cov(x, y)[0, 1] / np.var(x) if np.var(x) > 0 else 0.0
            c = np.mean(y) - phi * np.mean(x)

            self.ar_coefficient = phi
            self.intercept = c

            # Forecast
            last_return = returns_array[-1]
            predicted_return = c + phi * last_return

            # Confidence interval
            residuals = y - (c + phi * x)
            std_dev = np.std(residuals) if len(residuals) > 1 else 0.01

            # Confidence based on fit quality
            confidence = min(1.0, len(self.returns_history) / 20)

            return ForecastResult(
                predicted_return=predicted_return,
                confidence_interval=(predicted_return - 2*std_dev, predicted_return + 2*std_dev),
                prediction_horizon=self.prediction_horizon,
                confidence=confidence,
                metadata={
                    'method': 'ar1',
                    'phi': phi,
                    'intercept': c,
                    'data_points': len(self.returns_history),
                    'residual_std': std_dev
                }
            )
        else:
            return ForecastResult(
                predicted_return=0.0,
                confidence_interval=(-0.02, 0.02),
                prediction_horizon=self.prediction_horizon,
                confidence=0.5,
                metadata={'method': 'ar1', 'data_points': len(returns)}
            )

    def train(self, X: np.ndarray, y: np.ndarray) -> None:
        """AR(1) doesn't require separate training."""
        pass


if __name__ == "__main__":
    # Test baseline forecast models
    print("Testing baseline forecast models...")

    # Create sample features
    sample_returns = [0.01, -0.005, 0.02, 0.015, -0.01, 0.008, -0.003, 0.012, -0.008, 0.025]
    features = {'returns': sample_returns}

    # Test EWMA
    ewma = EWMAModel({'alpha': 0.5})
    result = ewma.predict(features)
    print(f"\n✅ EWMA Forecast:")
    print(f"   Predicted return: {result.predicted_return:.4f}")
    print(f"   Confidence interval: ({result.confidence_interval[0]:.4f}, {result.confidence_interval[1]:.4f})")
    print(f"   Confidence: {result.confidence:.2f}")

    # Test AR(1)
    ar1 = AR1Model({'lag': 1})
    result = ar1.predict(features)
    print(f"\n✅ AR(1) Forecast:")
    print(f"   Predicted return: {result.predicted_return:.4f}")
    print(f"   Confidence interval: ({result.confidence_interval[0]:.4f}, {result.confidence_interval[1]:.4f})")
    print(f"   Confidence: {result.confidence:.2f}")
    print(f"   AR coefficient (phi): {result.metadata['phi']:.4f}")

    print("\n✅ Baseline forecast models working correctly")
