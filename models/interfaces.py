#!/usr/bin/env python3
"""
Model Zoo - Core Interfaces

Defines abstract base classes for all model types:
- ForecastModel: Predict returns/price distributions
- SignalModel: Generate BUY/SELL/HOLD signals with confidence
- AllocationModel: Compute position sizes/portfolio weights
- ExecutionPolicy: Determine order type and timing
- Learner: Online learning from outcomes

All models are versioned and must implement required methods.
"""

from abc import ABC, abstractmethod
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass
from datetime import datetime
import numpy as np


@dataclass
class ModelMetadata:
    """Metadata for model versioning and reproducibility."""
    name: str
    version: str  # Semantic versioning (e.g., "1.0.0")
    model_type: str  # "forecast", "signal", "allocation", "execution"
    trained_at: Optional[datetime] = None
    git_hash: Optional[str] = None
    file_hash: Optional[str] = None
    parameters: Optional[Dict[str, Any]] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            'name': self.name,
            'version': self.version,
            'model_type': self.model_type,
            'trained_at': self.trained_at.isoformat() if self.trained_at else None,
            'git_hash': self.git_hash,
            'file_hash': self.file_hash,
            'parameters': self.parameters
        }


@dataclass
class ForecastResult:
    """Result from forecast model."""
    predicted_return: float  # Expected return (e.g., 0.05 for 5%)
    confidence_interval: Tuple[float, float]  # (lower, upper) e.g., (-0.02, 0.08)
    prediction_horizon: str  # e.g., "1d", "1h", "5m"
    confidence: float  # Model confidence in prediction (range: 0.0 to 1.0)
    metadata: Dict[str, Any]  # Additional model-specific info


class ForecastModel(ABC):
    """
    Abstract base class for forecast models.

    Predicts future returns or price distributions.
    """

    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.metadata = ModelMetadata(
            name=self.__class__.__name__,
            version="1.0.0",
            model_type="forecast"
        )

    @abstractmethod
    def predict(self, features: Dict[str, Any]) -> ForecastResult:
        """
        Generate a forecast from features.

        Args:
            features: Dictionary of features (prices, indicators, etc.)

        Returns:
            ForecastResult with predicted return and confidence interval
        """
        pass

    @abstractmethod
    def train(self, X: np.ndarray, y: np.ndarray) -> None:
        """
        Train model on historical data (optional for some models).

        Args:
            X: Feature matrix
            y: Target vector (returns)
        """
        pass

    def get_version(self) -> str:
        """Get model version."""
        return self.metadata.version


@dataclass
class SignalResult:
    """Result from signal model."""
    action: str  # "BUY", "SELL", or "HOLD"
    confidence: float  # [0.0, 1.0]
    reasons: List[str]  # Human-readable explanations
    signal_components: Dict[str, float]  # Contribution of each signal component
    metadata: Dict[str, Any]  # Additional model-specific info


class SignalModel(ABC):
    """
    Abstract base class for signal models.

    Generates trading signals (BUY/SELL/HOLD) with confidence.
    """

    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.metadata = ModelMetadata(
            name=self.__class__.__name__,
            version="1.0.0",
            model_type="signal"
        )

    @abstractmethod
    def generate_signal(self, features: Dict[str, Any],
                       forecast: Optional[ForecastResult] = None) -> SignalResult:
        """
        Generate a trading signal.

        Args:
            features: Dictionary of features
            forecast: Optional forecast result to inform signal

        Returns:
            SignalResult with action, confidence, and reasons
        """
        pass

    @abstractmethod
    def train(self, X: np.ndarray, y: np.ndarray) -> None:
        """
        Train model on historical data.

        Args:
            X: Feature matrix
            y: Target vector (labels: 1=BUY, -1=SELL, 0=HOLD)
        """
        pass

    def get_version(self) -> str:
        """Get model version."""
        return self.metadata.version


@dataclass
class AllocationResult:
    """Result from allocation model."""
    target_value_pct: float  # Target portfolio value percentage [0.0, 1.0]
    position_sizing: Dict[str, float]  # Symbol → weight
    reasoning: str  # Human-readable explanation
    risk_metrics: Dict[str, float]  # e.g., portfolio_var, max_drawdown
    metadata: Dict[str, Any]  # Additional model-specific info


class AllocationModel(ABC):
    """
    Abstract base class for allocation models.

    Computes position sizes and portfolio weights.
    """

    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.metadata = ModelMetadata(
            name=self.__class__.__name__,
            version="1.0.0",
            model_type="allocation"
        )

    @abstractmethod
    def allocate(self, features: Dict[str, Any],
                 signal: SignalResult,
                 current_portfolio: Dict[str, float]) -> AllocationResult:
        """
        Compute allocation for a signal.

        Args:
            features: Dictionary of features
            signal: Signal result (action, confidence)
            current_portfolio: Current portfolio positions {symbol: weight}

        Returns:
            AllocationResult with target_value_pct and position sizing
        """
        pass

    def get_version(self) -> str:
        """Get model version."""
        return self.metadata.version


@dataclass
class ExecutionPolicy:
    """Execution policy from execution model."""
    order_type: str  # "MKT" or "LMT"
    limit_price: Optional[float] = None  # Required for LMT orders
    timing: str = "immediate"  # "immediate", "open", "close", "custom"
    time_in_force: str = "DAY"  # "DAY" or "GTC"
    metadata: Dict[str, Any] = None


class ExecutionModel(ABC):
    """
    Abstract base class for execution models.

    Determines how to execute orders (order type, timing).
    """

    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.metadata = ModelMetadata(
            name=self.__class__.__name__,
            version="1.0.0",
            model_type="execution"
        )

    @abstractmethod
    def get_execution_policy(self, features: Dict[str, Any],
                             signal: SignalResult,
                             allocation: AllocationResult) -> ExecutionPolicy:
        """
        Determine execution policy.

        Args:
            features: Dictionary of features
            signal: Signal result
            allocation: Allocation result

        Returns:
            ExecutionPolicy with order type and timing
        """
        pass

    def get_version(self) -> str:
        """Get model version."""
        return self.metadata.version


class Learner(ABC):
    """
    Abstract base class for online learners.

    Updates model parameters based on outcomes.
    """

    def __init__(self, config: Dict[str, Any]):
        self.config = config

    @abstractmethod
    def update(self, decision: Dict[str, Any], outcome: Dict[str, Any]) -> None:
        """
        Update learner based on decision and outcome.

        Args:
            decision: Decision dictionary with signal_components, weights_used
            outcome: Outcome dictionary with realized_pnl, hit, return_pct
        """
        pass

    @abstractmethod
    def get_weights(self) -> Dict[str, float]:
        """Get current signal weights."""
        pass

    @abstractmethod
    def get_calibration_params(self) -> Dict[str, float]:
        """Get confidence calibration parameters (Platt scaling)."""
        pass


# Validation functions
def validate_forecast_result(result: ForecastResult) -> bool:
    """Validate forecast result."""
    try:
        assert isinstance(result.predicted_return, (int, float))
        assert isinstance(result.confidence_interval, tuple)
        assert len(result.confidence_interval) == 2
        assert isinstance(result.confidence, float)
        assert 0.0 <= result.confidence <= 1.0
        assert result.prediction_horizon in ["1d", "1h", "5m", "1w", "1m"]
        return True
    except (AssertionError, TypeError):
        return False


def validate_signal_result(result: SignalResult) -> bool:
    """Validate signal result."""
    try:
        assert result.action in ["BUY", "SELL", "HOLD"]
        assert isinstance(result.confidence, float)
        assert 0.0 <= result.confidence <= 1.0
        assert isinstance(result.reasons, list)
        assert isinstance(result.signal_components, dict)
        return True
    except (AssertionError, TypeError):
        return False


def validate_allocation_result(result: AllocationResult,
                               max_position_pct: float = 0.15) -> bool:
    """Validate allocation result."""
    try:
        assert isinstance(result.target_value_pct, float)
        assert 0.0 <= result.target_value_pct <= max_position_pct
        assert isinstance(result.position_sizing, dict)
        assert isinstance(result.risk_metrics, dict)
        return True
    except (AssertionError, TypeError):
        return False


if __name__ == "__main__":
    # Test interfaces
    print("✅ Model interfaces loaded successfully")
    print(f"   ForecastModel: {ForecastModel.__name__}")
    print(f"   SignalModel: {SignalModel.__name__}")
    print(f"   AllocationModel: {AllocationModel.__name__}")
    print(f"   ExecutionModel: {ExecutionModel.__name__}")
    print(f"   Learner: {Learner.__name__}")
