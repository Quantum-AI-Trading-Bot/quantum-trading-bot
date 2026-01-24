#!/usr/bin/env python3
"""
Phase 1: Risk Guardrails System
Implements comprehensive risk checks and limits
"""

import logging
from typing import Dict, Any, Optional
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class RiskCheck:
    """Result of a risk check"""
    passed: bool
    reason: str
    check_type: str
    metadata: Dict[str, Any] = None


class RiskGuardrails:
    """
    Comprehensive risk management guardrails system
    """

    def __init__(
        self,
        max_position_size_pct: float = 0.15,
        max_portfolio_exposure: float = 1.0,
        max_daily_loss_pct: float = 0.05,
        max_drawdown_pct: float = 0.20,
        min_confidence: float = 0.75,
        stop_loss_pct: float = 0.02,
        take_profit_pct: float = 0.05,
        emergency_stop_file: str = "/tmp/EMERGENCY_STOP"
    ):
        """
        Initialize risk guardrails

        Args:
            max_position_size_pct: Max position size as % of portfolio
            max_portfolio_exposure: Max total exposure as % of portfolio
            max_daily_loss_pct: Max daily loss as % of portfolio
            max_drawdown_pct: Max drawdown as % of portfolio
            min_confidence: Minimum confidence for trades
            stop_loss_pct: Stop loss percentage
            take_profit_pct: Take profit percentage
            emergency_stop_file: Path to emergency stop file
        """
        self.max_position_size_pct = max_position_size_pct
        self.max_portfolio_exposure = max_portfolio_exposure
        self.max_daily_loss_pct = max_daily_loss_pct
        self.max_drawdown_pct = max_drawdown_pct
        self.min_confidence = min_confidence
        self.stop_loss_pct = stop_loss_pct
        self.take_profit_pct = take_profit_pct
        self.emergency_stop_file = emergency_stop_file

        # Track state
        self.current_exposure = 0.0
        self.daily_pnl = 0.0
        self.peak_equity = 0.0
        self.current_equity = 0.0

        logger.info("Risk guardrails initialized")

    def check_emergency_stop(self) -> RiskCheck:
        """Check for emergency stop file"""
        import os
        if os.path.exists(self.emergency_stop_file):
            return RiskCheck(
                passed=False,
                reason=f"EMERGENCY_STOP file detected at {self.emergency_stop_file}",
                check_type="emergency_stop",
                metadata={'file_path': self.emergency_stop_file}
            )
        return RiskCheck(
            passed=True,
            reason="No emergency stop detected",
            check_type="emergency_stop"
        )

    def check_confidence(self, confidence: float) -> RiskCheck:
        """Check if confidence meets minimum threshold"""
        if confidence < self.min_confidence:
            return RiskCheck(
                passed=False,
                reason=f"Confidence {confidence:.2f} below minimum {self.min_confidence}",
                check_type="confidence",
                metadata={'confidence': confidence, 'min_confidence': self.min_confidence}
            )
        return RiskCheck(
            passed=True,
            reason=f"Confidence {confidence:.2f} meets minimum {self.min_confidence}",
            check_type="confidence",
            metadata={'confidence': confidence}
        )

    def check_position_size(
        self,
        position_value: float,
        portfolio_value: float
    ) -> RiskCheck:
        """Check if position size within limits"""
        position_pct = position_value / portfolio_value

        if position_pct > self.max_position_size_pct:
            return RiskCheck(
                passed=False,
                reason=f"Position size {position_pct:.2%} exceeds max {self.max_position_size_pct:.2%}",
                check_type="position_size",
                metadata={
                    'position_pct': position_pct,
                    'max_position_pct': self.max_position_size_pct,
                    'position_value': position_value,
                    'portfolio_value': portfolio_value
                }
            )
        return RiskCheck(
            passed=True,
            reason=f"Position size {position_pct:.2%} within limit {self.max_position_size_pct:.2%}",
            check_type="position_size",
            metadata={'position_pct': position_pct}
        )

    def check_portfolio_exposure(self, exposure: float) -> RiskCheck:
        """Check if total portfolio exposure within limits"""
        if exposure > self.max_portfolio_exposure:
            return RiskCheck(
                passed=False,
                reason=f"Portfolio exposure {exposure:.2%} exceeds max {self.max_portfolio_exposure:.2%}",
                check_type="portfolio_exposure",
                metadata={'exposure': exposure, 'max_exposure': self.max_portfolio_exposure}
            )
        return RiskCheck(
            passed=True,
            reason=f"Portfolio exposure {exposure:.2%} within limit {self.max_portfolio_exposure:.2%}",
            check_type="portfolio_exposure",
            metadata={'exposure': exposure}
        )

    def check_daily_loss(self, daily_pnl: float, portfolio_value: float) -> RiskCheck:
        """Check if daily loss exceeds limit"""
        daily_loss_pct = abs(daily_pnl) / portfolio_value if daily_pnl < 0 else 0

        if daily_loss_pct > self.max_daily_loss_pct:
            return RiskCheck(
                passed=False,
                reason=f"Daily loss {daily_loss_pct:.2%} exceeds max {self.max_daily_loss_pct:.2%}",
                check_type="daily_loss",
                metadata={
                    'daily_pnl': daily_pnl,
                    'daily_loss_pct': daily_loss_pct,
                    'max_daily_loss_pct': self.max_daily_loss_pct
                }
            )
        return RiskCheck(
            passed=True,
            reason=f"Daily loss {daily_loss_pct:.2%} within limit {self.max_daily_loss_pct:.2%}",
            check_type="daily_loss",
            metadata={'daily_pnl': daily_pnl, 'daily_loss_pct': daily_loss_pct}
        )

    def check_drawdown(self, current_equity: float, peak_equity: float) -> RiskCheck:
        """Check if drawdown exceeds limit"""
        drawdown = (peak_equity - current_equity) / peak_equity

        if drawdown > self.max_drawdown_pct:
            return RiskCheck(
                passed=False,
                reason=f"Drawdown {drawdown:.2%} exceeds max {self.max_drawdown_pct:.2%}",
                check_type="drawdown",
                metadata={
                    'drawdown': drawdown,
                    'max_drawdown_pct': self.max_drawdown_pct,
                    'current_equity': current_equity,
                    'peak_equity': peak_equity
                }
            )
        return RiskCheck(
            passed=True,
            reason=f"Drawdown {drawdown:.2%} within limit {self.max_drawdown_pct:.2%}",
            check_type="drawdown",
            metadata={'drawdown': drawdown}
        )

    def run_all_checks(
        self,
        confidence: float,
        position_value: float,
        portfolio_value: float,
        daily_pnl: float = None
    ) -> Dict[str, RiskCheck]:
        """
        Run all risk checks

        Args:
            confidence: Trade confidence
            position_value: Value of position
            portfolio_value: Total portfolio value
            daily_pnl: Daily P&L (optional)

        Returns:
            Dictionary of risk check results
        """
        checks = {}

        # Run all checks
        checks['emergency_stop'] = self.check_emergency_stop()
        checks['confidence'] = self.check_confidence(confidence)
        checks['position_size'] = self.check_position_size(position_value, portfolio_value)
        checks['portfolio_exposure'] = self.check_portfolio_exposure(self.current_exposure)

        if daily_pnl is not None:
            checks['daily_loss'] = self.check_daily_loss(daily_pnl, portfolio_value)

        if self.peak_equity > 0:
            checks['drawdown'] = self.check_drawdown(self.current_equity, self.peak_equity)

        # Log results
        failed_checks = [name for name, check in checks.items() if not check.passed]
        if failed_checks:
            logger.warning(f"Risk checks failed: {', '.join(failed_checks)}")
        else:
            logger.info("All risk checks passed")

        return checks

    def approve_trade(
        self,
        confidence: float,
        position_value: float,
        portfolio_value: float,
        daily_pnl: float = None
    ) -> tuple[bool, str]:
        """
        Approve or reject trade based on risk checks

        Args:
            confidence: Trade confidence
            position_value: Value of position
            portfolio_value: Total portfolio value
            daily_pnl: Daily P&L (optional)

        Returns:
            Tuple of (approved: bool, reason: str)
        """
        checks = self.run_all_checks(confidence, position_value, portfolio_value, daily_pnl)

        failed_checks = [name for name, check in checks.items() if not check.passed]

        if failed_checks:
            reasons = [checks[name].reason for name in failed_checks]
            return False, "; ".join(reasons)
        else:
            return True, "All risk checks passed"


def apply_guardrails(
    order: Dict[str, Any],
    account_state: Dict[str, Any],
    guardrails: RiskGuardrails = None
) -> Dict[str, Any]:
    """
    Apply risk guardrails to an order

    Args:
        order: Order dictionary
        account_state: Account state dictionary
        guardrails: RiskGuardrails instance

    Returns:
        Modified order with risk checks applied
    """
    if guardrails is None:
        guardrails = RiskGuardrails()

    # Extract order parameters
    confidence = order.get('confidence', 0.0)
    position_value = order.get('quantity', 0) * order.get('price', 0)
    portfolio_value = account_state.get('portfolio_value', 0)
    daily_pnl = account_state.get('daily_pnl')

    # Run risk checks
    approved, reason = guardrails.approve_trade(
        confidence=confidence,
        position_value=position_value,
        portfolio_value=portfolio_value,
        daily_pnl=daily_pnl
    )

    # Add risk check results to order
    order['risk_approved'] = approved
    order['risk_reason'] = reason

    # Add stop loss and take profit if approved
    if approved:
        entry_price = order.get('price', 0)
        order['stop_loss'] = entry_price * (1 - guardrails.stop_loss_pct)
        order['take_profit'] = entry_price * (1 + guardrails.take_profit_pct)

    return order
