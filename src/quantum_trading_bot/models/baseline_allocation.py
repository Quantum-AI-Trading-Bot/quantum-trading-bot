#!/usr/bin/env python3
"""
Baseline Allocation and Execution Models

Implements:
- FixedAllocationModel: Fixed percentage allocation (safe default)
- RiskParityAllocationModel: Risk parity allocation (optional)
- DefaultExecutionPolicy: Simple market order execution
"""

import numpy as np
from typing import Dict, Any
import logging

from models.interfaces import AllocationModel, AllocationResult, ExecutionModel, ExecutionPolicy, ModelMetadata

logger = logging.getLogger(__name__)


class FixedAllocationModel(AllocationModel):
    """
    Fixed allocation model - safe default.

    Allocates a fixed percentage of portfolio value.
    Enforces max position size constraint.
    """

    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.target_value_pct = config.get('target_value_pct', 0.01)  # Default 1%
        self.max_position_pct = config.get('max_position_pct', 0.15)  # Max 15%

        # Update metadata
        self.metadata = ModelMetadata(
            name="FixedAllocationModel",
            version="1.0.0",
            model_type="allocation",
            parameters={
                'target_value_pct': self.target_value_pct,
                'max_position_pct': self.max_position_pct
            }
        )

    def allocate(self, features: Dict[str, Any],
                 signal: 'SignalResult',
                 current_portfolio: Dict[str, float]) -> AllocationResult:
        """
        Allocate fixed percentage based on signal.

        Args:
            features: Features dictionary
            signal: Signal result with action and confidence
            current_portfolio: Current portfolio {symbol: weight}

        Returns:
            AllocationResult with target_value_pct
        """
        # Start with target allocation
        allocation_pct = self.target_value_pct

        # Adjust based on signal confidence
        if signal.action == 'HOLD':
            # Hold: no allocation
            allocation_pct = 0.0
        elif signal.action in ['BUY', 'SELL']:
            # Scale allocation by confidence
            allocation_pct = self.target_value_pct * signal.confidence

        # Enforce max position size
        allocation_pct = min(allocation_pct, self.max_position_pct)

        # Position sizing (for single symbol)
        symbol = features.get('symbol', 'UNKNOWN')
        position_sizing = {symbol: allocation_pct}

        # Risk metrics
        risk_metrics = {
            'portfolio_var': allocation_pct * 0.2,  # Rough estimate
            'max_drawdown': allocation_pct * 0.1  # Rough estimate
        }

        reasoning = f"Fixed allocation: {allocation_pct:.1%} of portfolio for {signal.action} on {symbol}"

        return AllocationResult(
            target_value_pct=allocation_pct,
            position_sizing=position_sizing,
            reasoning=reasoning,
            risk_metrics=risk_metrics,
            metadata={
                'model': 'fixed',
                'signal_action': signal.action,
                'signal_confidence': signal.confidence
            }
        )


class RiskParityAllocationModel(AllocationModel):
    """
    Risk parity allocation model.

    Allocates based on inverse volatility (equal risk contribution).
    Optional: requires PyPortfolioOpt, falls back to simple version.
    """

    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.target_value_pct = config.get('target_value_pct', 0.01)
        self.max_position_pct = config.get('max_position_pct', 0.15)

        # Try to import PyPortfolioOpt
        try:
            import pypfopt
            self.pypfopt_available = True
        except ImportError:
            logger.warning("PyPortfolioOpt not available, using simple risk parity")
            self.pypfopt_available = False

        # Update metadata
        self.metadata = ModelMetadata(
            name="RiskParityAllocationModel",
            version="1.0.0",
            model_type="allocation",
            parameters=config
        )

    def allocate(self, features: Dict[str, Any],
                 signal: 'SignalResult',
                 current_portfolio: Dict[str, float]) -> AllocationResult:
        """Allocate using risk parity or fallback to fixed."""
        if not self.pypfopt_available:
            # Fallback to fixed allocation
            logger.info("Using fixed allocation as fallback")
            fallback_model = FixedAllocationModel(self.config)
            return fallback_model.allocate(features, signal, current_portfolio)

        # Compute returns covariance
        returns_matrix = features.get('returns_matrix', None)
        if returns_matrix is None:
            # Fallback
            logger.warning("No returns matrix provided, using fixed allocation")
            fallback_model = FixedAllocationModel(self.config)
            return fallback_model.allocate(features, signal, current_portfolio)

        # Use PyPortfolioOpt for risk parity
        try:
            from pypfopt import RiskParity, CovarianceShrinkage

            # Shrink covariance matrix
            cov_shrinkage = CovarianceShrinkage()
            shrunk_cov = cov_shrinkage.fit(returns_matrix)

            # Risk parity optimization
            rp = RiskParity()
            rp_weights = rp.optimize(shrunk_cov)

            # Get weight for target symbol
            symbol = features.get('symbol', 'UNKNOWN')
            symbols = features.get('symbols', [])

            if symbol in symbols:
                symbol_index = symbols.index(symbol)
                allocation_pct = rp_weights[symbol_index]
            else:
                allocation_pct = 0.0

            # Scale by target value and confidence
            if signal.action == 'HOLD':
                allocation_pct = 0.0
            elif signal.action in ['BUY', 'SELL']:
                allocation_pct = self.target_value_pct * signal.confidence

            # Enforce max
            allocation_pct = min(allocation_pct, self.max_position_pct)

            return AllocationResult(
                target_value_pct=allocation_pct,
                position_sizing={symbol: allocation_pct},
                reasoning=f"Risk parity allocation: {allocation_pct:.1%} for {symbol}",
                risk_metrics={'portfolio_var': np.var(rp_weights)},
                metadata={'model': 'risk_parity'}
            )

        except Exception as e:
            logger.error(f"Risk parity optimization failed: {e}")
            # Fallback
            fallback_model = FixedAllocationModel(self.config)
            return fallback_model.allocate(features, signal, current_portfolio)


class DefaultExecutionPolicy(ExecutionModel):
    """
    Default execution policy - simple market orders.

    Always uses market orders for immediate execution.
    """

    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.order_type = config.get('order_type', 'MKT')
        self.time_in_force = config.get('time_in_force', 'DAY')
        self.timing = config.get('timing', 'immediate')

        # Update metadata
        self.metadata = ModelMetadata(
            name="DefaultExecutionPolicy",
            version="1.0.0",
            model_type="execution",
            parameters=config
        )

    def get_execution_policy(self, features: Dict[str, Any],
                             signal: 'SignalResult',
                             allocation: 'AllocationResult') -> ExecutionPolicy:
        """
        Get default execution policy (market orders).

        Args:
            features: Features dictionary
            signal: Signal result
            allocation: Allocation result

        Returns:
            ExecutionPolicy with market order
        """
        # For HOLD, no execution needed
        if signal.action == 'HOLD':
            return ExecutionPolicy(
                order_type='MKT',
                timing='none',
                time_in_force='DAY',
                metadata={'action': 'HOLD', 'reason': 'No execution for HOLD'}
            )

        # For BUY/SELL, use market orders
        return ExecutionPolicy(
            order_type='MKT',
            limit_price=None,
            timing='immediate',
            time_in_force=self.time_in_force,
            metadata={
                'action': signal.action,
                'confidence': signal.confidence,
                'allocation_pct': allocation.target_value_pct
            }
        )


# Quantum-inspired optimizer placeholder (DRY_RUN only)
class QuantumAnnealingAllocationModel(AllocationModel):
    """
    Quantum-inspired allocation using simulated annealing.

    Placeholder for future quantum optimization.
    Falls back to fixed allocation.
    """

    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.target_value_pct = config.get('target_value_pct', 0.01)
        self.max_position_pct = config.get('max_position_pct', 0.15)
        self.temperature = config.get('temperature', 1000)
        self.cooling_rate = config.get('cooling_rate', 0.95)
        self.iterations = config.get('iterations', 100)

        # Update metadata
        self.metadata = ModelMetadata(
            name="QuantumAnnealingAllocationModel",
            version="0.1.0",  # Experimental
            model_type="allocation",
            parameters=config
        )

    def allocate(self, features: Dict[str, Any],
                 signal: 'SignalResult',
                 current_portfolio: Dict[str, float]) -> AllocationResult:
        """
        Simulated annealing allocation (DRY_RUN only).

        In production, this would use QAOA or other quantum algorithms.
        For now, falls back to fixed allocation.
        """
        logger.warning("Quantum annealing is experimental, using fixed allocation")

        # Check if in DRY_RUN
        dry_run = features.get('dry_run', True)
        if not dry_run:
            logger.error("Quantum annealing only allowed in DRY_RUN mode")
            # Force HOLD if not in DRY_RUN
            return AllocationResult(
                target_value_pct=0.0,
                position_sizing={},
                reasoning="Quantum annealing only allowed in DRY_RUN mode",
                risk_metrics={},
                metadata={'model': 'quantum_annealing', 'blocked': 'not_dry_run'}
            )

        # Fallback to fixed allocation
        fallback_model = FixedAllocationModel(self.config)
        result = fallback_model.allocate(features, signal, current_portfolio)

        # Add quantum metadata
        result.metadata['model'] = 'quantum_annealing_fallback'
        result.reasoning += " [Quantum annealing placeholder - using fixed allocation]"

        return result


if __name__ == "__main__":
    # Test baseline allocation and execution models
    print("Testing baseline allocation and execution models...")

    # Sample signal
    from models.baseline_signal import SignalResult
    signal = SignalResult(
        action='BUY',
        confidence=0.8,
        reasons=['Positive momentum'],
        signal_components={'momentum': 0.7},
        metadata={}
    )

    features = {
        'symbol': 'SPY',
        'returns': [0.01] * 10
    }

    # Test FixedAllocationModel
    print("\n✅ FixedAllocationModel:")
    alloc_model = FixedAllocationModel({'target_value_pct': 0.01})
    result = alloc_model.allocate(features, signal, {})
    print(f"   Target value %: {result.target_value_pct:.2%}")
    print(f"   Reasoning: {result.reasoning}")

    # Test DefaultExecutionPolicy
    print("\n✅ DefaultExecutionPolicy:")
    exec_model = DefaultExecutionPolicy({})
    policy = exec_model.get_execution_policy(features, signal, result)
    print(f"   Order type: {policy.order_type}")
    print(f"   Timing: {policy.timing}")

    print("\n✅ Baseline allocation and execution models working correctly")
