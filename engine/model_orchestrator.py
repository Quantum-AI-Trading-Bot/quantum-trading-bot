#!/usr/bin/env python3
"""
Model Orchestrator - Core component that ties all models together.

Responsibilities:
- Load model registry and configuration
- Build features from context
- Run forecast -> signal -> allocation -> execution pipeline
- Create VPA artifact with model metadata
- Pass decision to VPA executor
- Persist decision for learning loop
"""

import os
import sys
import json
import uuid
import logging
import hashlib
from datetime import datetime
from typing import Dict, Any, Optional, List
from pathlib import Path

import yaml
import numpy as np

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from models.registry import get_registry
from models.interfaces import (
    ForecastResult, SignalResult, AllocationResult, ExecutionPolicy,
    validate_forecast_result, validate_signal_result, validate_allocation_result
)

from learning.trade_ledger import TradeLedger

logger = logging.getLogger(__name__)


class ModelOrchestrator:
    """
    Orchestrates the model pipeline: forecast -> signal -> allocation -> execution
    """

    def __init__(self, config_path: str = None):
        """
        Initialize orchestrator with configuration.

        Args:
            config_path: Path to model_zoo.yaml config file
        """
        # Load configuration
        if config_path is None:
            config_path = "/home/davidsanker/platform/config/model_zoo.yaml"

        self.config = self._load_config(config_path)

        # Initialize components
        self.registry = get_registry()
        self.ledger = TradeLedger()

        # Model instances (created on demand)
        self._forecast_model = None
        self._signal_model = None
        self._allocation_model = None
        self._execution_model = None

        # Safety constraints
        self.max_position_pct = self.config.get('MAX_POSITION_SIZE_PCT', 0.15)
        self.min_confidence = self.config.get('MIN_CONFIDENCE_THRESHOLD', 0.75)

        # Paths
        self.vpa_storage = Path(self.config.get('vpa_storage_path', '/home/davidsanker/platform/vpa_storage'))
        self.vpa_storage.mkdir(parents=True, exist_ok=True)

        logger.info("Model Orchestrator initialized")

    def _load_config(self, config_path: str) -> Dict[str, Any]:
        """Load configuration from YAML file."""
        try:
            with open(config_path, 'r') as f:
                config = yaml.safe_load(f)
            logger.info(f"Loaded configuration from {config_path}")
            return config
        except Exception as e:
            logger.error(f"Failed to load config: {e}")
            # Return safe defaults
            return {
                'MODEL_ZOO_ENABLED': False,
                'FORECAST_MODEL': 'ewma',
                'SIGNAL_MODEL': 'signal_generator',
                'ALLOCATION_MODEL': 'fixed',
                'EXECUTION_POLICY': 'default',
                'MAX_POSITION_SIZE_PCT': 0.15,
                'MIN_CONFIDENCE_THRESHOLD': 0.75
            }

    def _get_forecast_model(self):
        """Get or create forecast model instance."""
        if self._forecast_model is None:
            model_name = self.config.get('FORECAST_MODEL', 'ewma')
            self._forecast_model = self.registry.create_forecast_model(model_name, self.config.get(model_name, {}))
        return self._forecast_model

    def _get_signal_model(self):
        """Get or create signal model instance."""
        if self._signal_model is None:
            model_name = self.config.get('SIGNAL_MODEL', 'signal_generator')
            self._signal_model = self.registry.create_signal_model(model_name, self.config.get(model_name, {}))
        return self._signal_model

    def _get_allocation_model(self):
        """Get or create allocation model instance."""
        if self._allocation_model is None:
            model_name = self.config.get('ALLOCATION_MODEL', 'fixed')
            self._allocation_model = self.registry.create_allocation_model(model_name, self.config.get(model_name, {}))
        return self._allocation_model

    def _get_execution_model(self):
        """Get or create execution model instance."""
        if self._execution_model is None:
            model_name = self.config.get('EXECUTION_POLICY', 'default')
            self._execution_model = self.registry.create_execution_model(model_name, self.config.get(model_name, {}))
        return self._execution_model

    def _build_features(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Build features from context.

        Args:
            context: Context with prices, indicators, etc.

        Returns:
            Feature dictionary
        """
        features = {}

        # Price features
        prices = context.get('prices', [])
        if prices:
            features['prices'] = prices
            # Compute returns
            returns = []
            for i in range(1, len(prices)):
                ret = (prices[i] - prices[i-1]) / prices[i-1]
                returns.append(ret)
            features['returns'] = returns

        # Technical indicators
        features['indicators'] = context.get('indicators', {})

        # Symbol
        features['symbol'] = context.get('symbol', 'SPY')

        # Portfolio state
        features['portfolio'] = context.get('portfolio', {})

        # Market data
        features['market_data'] = context.get('market_data', {})

        return features

    def run_decision_cycle(self, context: Dict[str, Any],
                          dry_run: bool = True) -> Dict[str, Any]:
        """
        Run complete decision cycle: forecast -> signal -> allocation -> execution.

        Args:
            context: Market context (prices, indicators, etc.)
            dry_run: If True, don't execute orders (default: True)

        Returns:
            Dictionary with decision_plan, vpa_path, execution_result
        """
        try:
            logger.info("Starting decision cycle...")

            # 1. Build features
            features = self._build_features(context)

            # 2. Forecast
            forecast_model = self._get_forecast_model()
            if forecast_model:
                forecast = forecast_model.predict(features)
                if not validate_forecast_result(forecast):
                    logger.error("Invalid forecast result, using neutral")
                    forecast = ForecastResult(
                        predicted_return=0.0,
                        confidence_interval=(-0.01, 0.01),
                        prediction_horizon="1d",
                        confidence=0.5,
                        metadata={'fallback': True}
                    )
            else:
                logger.warning("No forecast model available")
                forecast = None

            # 3. Signal
            signal_model = self._get_signal_model()
            if signal_model:
                signal = signal_model.generate_signal(features, forecast)
                if not validate_signal_result(signal):
                    logger.error("Invalid signal result, using HOLD")
                    signal = SignalResult(
                        action='HOLD',
                        confidence=0.5,
                        reasons=['Invalid signal, defaulting to HOLD'],
                        signal_components={},
                        metadata={'fallback': True}
                    )
            else:
                logger.error("No signal model available")
                signal = SignalResult(
                    action='HOLD',
                    confidence=0.5,
                    reasons=['No signal model'],
                    signal_components={},
                    metadata={'fallback': True}
                )

            # 4. Allocation
            allocation_model = self._get_allocation_model()
            if allocation_model:
                allocation = allocation_model.allocate(features, signal, context.get('portfolio', {}))
                if not validate_allocation_result(allocation, self.max_position_pct):
                    logger.error("Invalid allocation result, using minimum")
                    allocation = AllocationResult(
                        target_value_pct=0.0,
                        position_sizing={},
                        reasoning="Invalid allocation, no position",
                        risk_metrics={},
                        metadata={'fallback': True}
                    )
            else:
                logger.error("No allocation model available")
                allocation = AllocationResult(
                    target_value_pct=0.0,
                    position_sizing={},
                    reasoning="No allocation model",
                    risk_metrics={},
                    metadata={'fallback': True}
                )

            # 5. Execution policy
            execution_model = self._get_execution_model()
            if execution_model:
                execution = execution_model.get_execution_policy(features, signal, allocation)
            else:
                execution = ExecutionPolicy(
                    order_type='MKT',
                    timing='immediate',
                    time_in_force='DAY',
                    metadata={'fallback': True}
                )

            # 6. Assemble decision plan
            decision_plan = self._assemble_decision_plan(
                features, signal, allocation, execution, dry_run
            )

            # 7. Create VPA artifact
            vpa_path = self._create_vpa_artifact(decision_plan)

            # 8. Persist decision to ledger (for learning)
            self._persist_decision(decision_plan, features, signal)

            logger.info(f"Decision cycle complete: {decision_plan['action']} {decision_plan['symbol']}")

            return {
                'decision_plan': decision_plan,
                'vpa_path': str(vpa_path),
                'execution_result': None,  # Will be filled by executor
                'success': True
            }

        except Exception as e:
            logger.error(f"Decision cycle failed: {e}")
            import traceback
            traceback.print_exc()

            # Return safe HOLD decision
            return {
                'decision_plan': {
                    'action': 'HOLD',
                    'symbol': context.get('symbol', 'UNKNOWN'),
                    'confidence': 0.0,
                    'target_value_pct': 0.0,
                    'order_type': 'MKT',
                    'reasons': [f"Error in decision cycle: {str(e)}"],
                    'indicators': {},
                    'decision_id': str(uuid.uuid4()),
                    'timestamp': datetime.utcnow().isoformat(),
                    'model_metadata': {},
                    'learning_metadata': {}
                },
                'vpa_path': None,
                'execution_result': None,
                'success': False,
                'error': str(e)
            }

    def _assemble_decision_plan(self, features: Dict[str, Any],
                                signal: SignalResult,
                                allocation: AllocationResult,
                                execution: ExecutionPolicy,
                                dry_run: bool) -> Dict[str, Any]:
        """Assemble final decision plan."""
        decision_id = str(uuid.uuid4())

        # Apply safety constraints
        action = signal.action
        confidence = signal.confidence

        # Confidence threshold check
        if confidence < self.min_confidence:
            action = 'HOLD'
            signal.reasons.append(f"Confidence {confidence:.2f} below threshold {self.min_confidence}")

        # Build decision plan (VPA-compatible)
        decision_plan = {
            'action': action,
            'symbol': features.get('symbol', 'SPY'),
            'confidence': confidence,
            'target_value_pct': allocation.target_value_pct,
            'order_type': execution.order_type,
            'limit_price': execution.limit_price,
            'reasons': signal.reasons,
            'indicators': features.get('indicators', {}),
            'decision_id': decision_id,
            'timestamp': datetime.utcnow().isoformat(),

            # Model metadata (NEW)
            'model_metadata': {
                'forecast_model': self.config.get('FORECAST_MODEL', 'ewma'),
                'signal_model': self.config.get('SIGNAL_MODEL', 'signal_generator'),
                'allocation_model': self.config.get('ALLOCATION_MODEL', 'fixed'),
                'execution_policy': self.config.get('EXECUTION_POLICY', 'default'),
                'model_versions': {
                    'forecast': self._get_forecast_model().get_version() if self._get_forecast_model() else 'N/A',
                    'signal': self._get_signal_model().get_version() if self._get_signal_model() else 'N/A',
                    'allocation': self._get_allocation_model().get_version() if self._get_allocation_model() else 'N/A',
                    'execution': self._get_execution_model().get_version() if self._get_execution_model() else 'N/A'
                },
                'dry_run': dry_run
            },

            # Learning metadata
            'learning_metadata': {
                'signal_components': signal.signal_components,
                'weights_used': signal.signal_components,  # For now, same as components
                'confidence_raw': confidence,
                'confidence_calibrated': confidence  # TODO: apply calibration
            }
        }

        return decision_plan

    def _create_vpa_artifact(self, decision_plan: Dict[str, Any]) -> Path:
        """Create VPA artifact with model metadata."""
        # VPA filename format: vpa_<action>_<symbol>_<timestamp>.json
        timestamp = datetime.utcnow().strftime('%Y%m%d_%H%M%S')
        filename = f"vpa_{decision_plan['action']}_{decision_plan['symbol']}_{timestamp}.json"
        vpa_path = self.vpa_storage / filename

        # Create VPA content
        vpa_content = {
            'timestamp': decision_plan['timestamp'],
            'track': 'B',
            'mode': 'true',
            'model_zoo_enabled': self.config.get('MODEL_ZOO_ENABLED', False),
            'decision_plan': decision_plan
        }

        # Write VPA
        with open(vpa_path, 'w') as f:
            json.dump(vpa_content, f, indent=2)

        logger.info(f"VPA artifact created: {vpa_path}")
        return vpa_path

    def _persist_decision(self, decision_plan: Dict[str, Any],
                         features: Dict[str, Any],
                         signal: SignalResult):
        """Persist decision to ledger for learning loop."""
        try:
            # Write decision to ledger
            self.ledger.write_decision({
                'decision_id': decision_plan['decision_id'],
                'symbol': decision_plan['symbol'],
                'action': decision_plan['action'],
                'confidence': decision_plan['confidence'],
                'signal_components': signal.signal_components,
                'weights_used': decision_plan['learning_metadata']['weights_used'],
                'market_state': features.get('market_data', {}),
                'dry_run': decision_plan['model_metadata']['dry_run'],
                'trading_enabled': os.environ.get('QUANTUM_EXECUTION_ENABLED', 'false').lower() == 'true',
                'model_metadata': decision_plan['model_metadata']
            })
            logger.debug("Decision persisted to ledger")
        except Exception as e:
            logger.error(f"Failed to persist decision: {e}")

    def get_model_info(self) -> Dict[str, Any]:
        """Get information about available models."""
        return self.registry.get_model_info()


if __name__ == "__main__":
    # Test orchestrator with sample data
    print("Testing Model Orchestrator...")

    orchestrator = ModelOrchestrator()

    # Sample context
    context = {
        'symbol': 'SPY',
        'prices': [450.0, 451.0, 449.5, 452.0, 453.3, 454.5, 454.2, 456.8, 457.5, 459.4],
        'indicators': {'RSI': 65.0, 'MACD': 0.5},
        'portfolio': {},
        'market_data': {'VIX': 18.5}
    }

    # Run decision cycle
    result = orchestrator.run_decision_cycle(context, dry_run=True)

    if result['success']:
        print("\n✅ Decision cycle successful!")
        print(f"\nDecision Plan:")
        plan = result['decision_plan']
        print(f"  Action: {plan['action']}")
        print(f"  Symbol: {plan['symbol']}")
        print(f"  Confidence: {plan['confidence']:.2f}")
        print(f"  Target Value %: {plan['target_value_pct']:.2%}")
        print(f"  Order Type: {plan['order_type']}")
        print(f"  Reasons: {plan['reasons']}")
        print(f"\nModel Metadata:")
        meta = plan['model_metadata']
        print(f"  Forecast: {meta['forecast_model']} (v{meta['model_versions']['forecast']})")
        print(f"  Signal: {meta['signal_model']} (v{meta['model_versions']['signal']})")
        print(f"  Allocation: {meta['allocation_model']} (v{meta['model_versions']['allocation']})")

        print(f"\nVPA Artifact: {result['vpa_path']}")
    else:
        print(f"\n❌ Decision cycle failed: {result.get('error')}")

    print("\n✅ Model Orchestrator test complete")
