#!/usr/bin/env python3
"""
Phase 1: Position Sizing Module
Calculates optimal position sizes based on risk parameters
"""

import logging
from typing import Dict, Any
import numpy as np

logger = logging.getLogger(__name__)


class PositionSizer:
    """
    Dynamic position sizing based on confidence and risk
    """

    def __init__(
        self,
        max_position_pct: float = 0.15,
        min_position_pct: float = 0.01,
        confidence_multiplier: float = 1.5,
        risk_per_trade: float = 0.02
    ):
        """
        Initialize position sizer

        Args:
            max_position_pct: Maximum position as % of portfolio
            min_position_pct: Minimum position as % of portfolio
            confidence_multiplier: Multiply position by confidence
            risk_per_trade: Risk 2% of portfolio per trade
        """
        self.max_position_pct = max_position_pct
        self.min_position_pct = min_position_pct
        self.confidence_multiplier = confidence_multiplier
        self.risk_per_trade = risk_per_trade

        logger.info(f"PositionSizer initialized: max={max_position_pct:.1%}, risk_per_trade={risk_per_trade:.1%}")

    def calculate_position_size(
        self,
        portfolio_value: float,
        price: float,
        confidence: float,
        volatility: float = None
    ) -> int:
        """
        Calculate optimal position size

        Args:
            portfolio_value: Total portfolio value
            price: Current price of asset
            confidence: Trade confidence (0.0 to 1.0)
            volatility: Asset volatility (optional)

        Returns:
            Number of shares to trade
        """
        # Base position size
        base_position_value = portfolio_value * self.max_position_pct

        # Adjust by confidence
        adjusted_value = base_position_value * confidence * self.confidence_multiplier

        # Apply volatility adjustment if available
        if volatility and volatility > 0:
            # Reduce position size for high volatility
            volatility_adjustment = 1.0 / (1.0 + volatility)
            adjusted_value *= volatility_adjustment

        # Apply limits
        adjusted_value = max(
            portfolio_value * self.min_position_pct,
            min(adjusted_value, portfolio_value * self.max_position_pct)
        )

        # Calculate shares
        shares = int(adjusted_value / price)

        if shares <= 0:
            logger.warning(f"Calculated position size too small: {shares} shares")
            return 0

        logger.info(f"Position size: {shares} shares @ ${price:.2f} = ${shares * price:,.2f} ({confidence:.2%} confidence)")
        return shares

    def calculate_kelly_criterion(
        self,
        win_rate: float,
        avg_win: float,
        avg_loss: float,
        portfolio_value: float,
        price: float
    ) -> int:
        """
        Calculate position size using Kelly Criterion

        Args:
            win_rate: Historical win rate (0.0 to 1.0)
            avg_win: Average winning trade return
            avg_loss: Average losing trade return (negative)
            portfolio_value: Total portfolio value
            price: Current price of asset

        Returns:
            Number of shares to trade
        """
        # Kelly formula: f = (bp - q) / b
        # where b = avg_win / abs(avg_loss)
        # p = win_rate
        # q = 1 - win_rate

        if avg_loss >= 0:
            logger.warning("avg_loss should be negative for Kelly calculation")
            avg_loss = -abs(avg_loss)

        b = avg_win / abs(avg_loss)
        p = win_rate
        q = 1 - win_rate

        kelly_fraction = (b * p - q) / b

        # Cap Kelly fraction at 25% (half-Kelly for safety)
        kelly_fraction = max(0, min(kelly_fraction, 0.25))

        position_value = portfolio_value * kelly_fraction
        shares = int(position_value / price)

        logger.info(f"Kelly position: {kelly_fraction:.2%} = {shares} shares")
        return shares

    def calculate_fixed_fractional(
        self,
        portfolio_value: float,
        price: float,
        fraction: float = 0.10
    ) -> int:
        """
        Calculate position size using fixed fractional method

        Args:
            portfolio_value: Total portfolio value
            price: Current price of asset
            fraction: Fraction of portfolio to use

        Returns:
            Number of shares to trade
        """
        position_value = portfolio_value * fraction
        shares = int(position_value / price)

        logger.info(f"Fixed fractional position: {fraction:.2%} = {shares} shares")
        return shares

    def calculate_risk_parity(
        self,
        portfolio_value: float,
        price: float,
        volatility: float,
        target_volatility: float = 0.15
    ) -> int:
        """
        Calculate position size using risk parity

        Args:
            portfolio_value: Total portfolio value
            price: Current price of asset
            volatility: Asset volatility
            target_volatility: Target portfolio volatility

        Returns:
            Number of shares to trade
        """
        # Scale position inversely with volatility
        volatility_ratio = target_volatility / volatility if volatility > 0 else 1.0
        position_value = portfolio_value * volatility_ratio

        # Cap at max position
        position_value = min(position_value, portfolio_value * self.max_position_pct)

        shares = int(position_value / price)

        logger.info(f"Risk parity position: {volatility_ratio:.2f} = {shares} shares")
        return shares
