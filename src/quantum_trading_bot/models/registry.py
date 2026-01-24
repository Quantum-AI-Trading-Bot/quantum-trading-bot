#!/usr/bin/env python3
"""
Model Registry - Central registry for all models.

Manages model instantiation, versioning, and configuration.
Provides factory methods for creating models by name.
"""

import sys
import importlib
import logging
from typing import Dict, List, Any, Optional, Type
from pathlib import Path

from models.interfaces import (
    ForecastModel, SignalModel, AllocationModel,
    ExecutionModel, Learner
)

logger = logging.getLogger(__name__)


class ModelRegistry:
    """Central registry for all models."""

    def __init__(self):
        self._forecast_models: Dict[str, Type[ForecastModel]] = {}
        self._signal_models: Dict[str, Type[SignalModel]] = {}
        self._allocation_models: Dict[str, Type[AllocationModel]] = {}
        self._execution_models: Dict[str, Type[ExecutionModel]] = {}
        self._learners: Dict[str, Type[Learner]] = {}

        # Register built-in models
        self._register_builtin_models()

    def _register_builtin_models(self):
        """Register built-in baseline models."""
        try:
            # Import baseline models - use try/except for each
            # Forecast models
            try:
                from models.baseline_forecast import EWMAModel, AR1Model
                self.register_forecast_model("ewma", EWMAModel)
                self.register_forecast_model("ar1", AR1Model)
                logger.info("Forecast models registered")
            except ImportError as e:
                logger.warning(f"Could not import forecast models: {e}")

            # Signal models
            try:
                from models.baseline_signal import SignalGeneratorModel, GradientBoostingSignalModel
                self.register_signal_model("signal_generator", SignalGeneratorModel)
                self.register_signal_model("gradient_boosting", GradientBoostingSignalModel)
                logger.info("Baseline signal models registered")
            except ImportError as e:
                logger.warning(f"Could not import baseline signal models: {e}")

            # Phase 1 Signal models
            try:
                from models.phase1.phase1_ma_crossover_signal import Phase1MACrossoverSignal
                from models.phase1.phase1_multi_ma_signal import Phase1MultiMASignal
                from models.phase1.phase1_ml_signal import Phase1MLSignal
                self.register_signal_model("phase1_ma_crossover", Phase1MACrossoverSignal)
                self.register_signal_model("phase1_multi_ma", Phase1MultiMASignal)
                self.register_signal_model("phase1_ml_joblib", Phase1MLSignal)
                logger.info("Phase 1 signal models registered")
            except ImportError as e:
                logger.warning(f"Could not import Phase 1 signal models: {e}")

            # Allocation models
            try:
                from models.baseline_allocation import FixedAllocationModel, RiskParityAllocationModel, DefaultExecutionPolicy
                self.register_allocation_model("fixed", FixedAllocationModel)
                self.register_allocation_model("risk_parity", RiskParityAllocationModel)
                # Register execution model (in same file for now)
                self.register_execution_model("default", DefaultExecutionPolicy)
                logger.info("Allocation and execution models registered")
            except ImportError as e:
                logger.warning(f"Could not import allocation models: {e}")

            logger.info("Built-in models registered successfully")

        except Exception as e:
            logger.error(f"Error registering built-in models: {e}")

    def register_forecast_model(self, name: str, model_class: Type[ForecastModel]):
        """Register a forecast model."""
        self._forecast_models[name] = model_class
        logger.debug(f"Registered forecast model: {name}")

    def register_signal_model(self, name: str, model_class: Type[SignalModel]):
        """Register a signal model."""
        self._signal_models[name] = model_class
        logger.debug(f"Registered signal model: {name}")

    def register_allocation_model(self, name: str, model_class: Type[AllocationModel]):
        """Register an allocation model."""
        self._allocation_models[name] = model_class
        logger.debug(f"Registered allocation model: {name}")

    def register_execution_model(self, name: str, model_class: Type[ExecutionModel]):
        """Register an execution model."""
        self._execution_models[name] = model_class
        logger.debug(f"Registered execution model: {name}")

    def register_learner(self, name: str, learner_class: Type[Learner]):
        """Register a learner."""
        self._learners[name] = learner_class
        logger.debug(f"Registered learner: {name}")

    def create_forecast_model(self, name: str, config: Dict[str, Any]) -> Optional[ForecastModel]:
        """Create a forecast model instance."""
        model_class = self._forecast_models.get(name)
        if model_class is None:
            logger.error(f"Unknown forecast model: {name}")
            return None

        try:
            return model_class(config)
        except Exception as e:
            logger.error(f"Failed to create forecast model {name}: {e}")
            return None

    def create_signal_model(self, name: str, config: Dict[str, Any]) -> Optional[SignalModel]:
        """Create a signal model instance."""
        model_class = self._signal_models.get(name)
        if model_class is None:
            logger.error(f"Unknown signal model: {name}")
            return None

        try:
            return model_class(config)
        except Exception as e:
            logger.error(f"Failed to create signal model {name}: {e}")
            return None

    def create_allocation_model(self, name: str, config: Dict[str, Any]) -> Optional[AllocationModel]:
        """Create an allocation model instance."""
        model_class = self._allocation_models.get(name)
        if model_class is None:
            logger.error(f"Unknown allocation model: {name}")
            return None

        try:
            return model_class(config)
        except Exception as e:
            logger.error(f"Failed to create allocation model {name}: {e}")
            return None

    def create_execution_model(self, name: str, config: Dict[str, Any]) -> Optional[ExecutionModel]:
        """Create an execution model instance."""
        model_class = self._execution_models.get(name)
        if model_class is None:
            logger.error(f"Unknown execution model: {name}")
            return None

        try:
            return model_class(config)
        except Exception as e:
            logger.error(f"Failed to create execution model {name}: {e}")
            return None

    def create_learner(self, name: str, config: Dict[str, Any]) -> Optional[Learner]:
        """Create a learner instance."""
        learner_class = self._learners.get(name)
        if learner_class is None:
            logger.error(f"Unknown learner: {name}")
            return None

        try:
            return learner_class(config)
        except Exception as e:
            logger.error(f"Failed to create learner {name}: {e}")
            return None

    def list_forecast_models(self) -> List[str]:
        """List available forecast models."""
        return list(self._forecast_models.keys())

    def list_signal_models(self) -> List[str]:
        """List available signal models."""
        return list(self._signal_models.keys())

    def list_allocation_models(self) -> List[str]:
        """List available allocation models."""
        return list(self._allocation_models.keys())

    def list_execution_models(self) -> List[str]:
        """List available execution models."""
        return list(self._execution_models.keys())

    def list_learners(self) -> List[str]:
        """List available learners."""
        return list(self._learners.keys())

    def get_model_info(self) -> Dict[str, List[str]]:
        """Get information about all registered models."""
        return {
            'forecast_models': self.list_forecast_models(),
            'signal_models': self.list_signal_models(),
            'allocation_models': self.list_allocation_models(),
            'execution_models': self.list_execution_models(),
            'learners': self.list_learners()
        }


# Global registry instance
_registry = ModelRegistry()


def get_registry() -> ModelRegistry:
    """Get the global model registry."""
    return _registry


def register_custom_model(model_type: str, name: str, model_class: Type):
    """
    Register a custom model.

    Args:
        model_type: One of 'forecast', 'signal', 'allocation', 'execution', 'learner'
        name: Model name
        model_class: Model class
    """
    registry = get_registry()

    if model_type == 'forecast':
        registry.register_forecast_model(name, model_class)
    elif model_type == 'signal':
        registry.register_signal_model(name, model_class)
    elif model_type == 'allocation':
        registry.register_allocation_model(name, model_class)
    elif model_type == 'execution':
        registry.register_execution_model(name, model_class)
    elif model_type == 'learner':
        registry.register_learner(name, model_class)
    else:
        raise ValueError(f"Unknown model type: {model_type}")


if __name__ == "__main__":
    # Test registry
    registry = get_registry()

    print("✅ Model Registry initialized")
    print(f"\nAvailable models:")
    print(f"  Forecast: {registry.list_forecast_models()}")
    print(f"  Signal: {registry.list_signal_models()}")
    print(f"  Allocation: {registry.list_allocation_models()}")
    print(f"  Execution: {registry.list_execution_models()}")
    print(f"  Learners: {registry.list_learners()}")

    # Test model creation (if baseline models exist)
    print("\n🔄 Testing model creation:")

    # Test forecast model
    forecast = registry.create_forecast_model("ewma", {"alpha": 0.5})
    if forecast:
        print(f"  ✓ EWMA forecast model created: v{forecast.get_version()}")

    # Test signal model
    signal = registry.create_signal_model("signal_generator", {})
    if signal:
        print(f"  ✓ Signal generator model created: v{signal.get_version()}")

    # Test allocation model
    allocation = registry.create_allocation_model("fixed", {"target_pct": 0.01})
    if allocation:
        print(f"  ✓ Fixed allocation model created: v{allocation.get_version()}")

    # Test execution model
    execution = registry.create_execution_model("default", {})
    if execution:
        print(f"  ✓ Default execution model created: v{execution.get_version()}")

    print("\n✅ Registry test complete")
