#!/usr/bin/env python3
"""
Outcome Metrics - Compute performance metrics from trade outcomes.

Calculates P&L, MAE/MFE, slippage, holding time, hit rate, expectancy, etc.
"""

from typing import Dict, List, Any, Optional
from datetime import datetime
import numpy as np


class OutcomeMetrics:
    """Compute performance metrics from trade outcomes."""

    @staticmethod
    def compute_realized_pnl(entry_price: float, exit_price: float,
                            quantity: int, direction: str) -> float:
        """
        Compute realized profit/loss.

        Args:
            entry_price: Entry price per share
            exit_price: Exit price per share
            quantity: Number of shares
            direction: 'LONG' or 'SHORT'

        Returns:
            Realized P&L in dollars
        """
        if direction == 'LONG':
            return (exit_price - entry_price) * quantity
        else:  # SHORT
            return (entry_price - exit_price) * quantity

    @staticmethod
    def compute_return_pct(pnl: float, entry_value: float) -> float:
        """
        Compute return as percentage.

        Args:
            pnl: Profit/loss in dollars
            entry_value: Total entry value (entry_price * quantity)

        Returns:
            Return as percentage (e.g., 2.5 for 2.5%)
        """
        if entry_value == 0:
            return 0.0
        return (pnl / entry_value) * 100

    @staticmethod
    def compute_mae_mfe(trade: Dict[str, Any],
                       price_history: List[float]) -> Dict[str, float]:
        """
        Compute Maximum Adverse Excursion (MAE) and Maximum Favorable Excursion (MFE).

        MAE: Worst price movement against position (max loss)
        MFE: Best price movement in favor of position (max profit)

        Args:
            trade: Trade dictionary with entry_price, direction
            price_history: List of prices during the trade

        Returns:
            Dict with 'mae' and 'mfe' in dollars per share
        """
        entry_price = trade['entry_price']
        direction = trade['direction']

        if direction == 'LONG':
            # For long: adverse = price drop, favorable = price rise
            adverse = [entry_price - p for p in price_history]
            favorable = [p - entry_price for p in price_history]
        else:  # SHORT
            # For short: adverse = price rise, favorable = price drop
            adverse = [p - entry_price for p in price_history]
            favorable = [entry_price - p for p in price_history]

        return {
            'mae': max(adverse) if adverse else 0.0,
            'mfe': max(favorable) if favorable else 0.0
        }

    @staticmethod
    def compute_holding_period(entry_time: str, exit_time: Optional[str]) -> int:
        """
        Compute holding period in seconds.

        Args:
            entry_time: Entry time ISO string
            exit_time: Exit time ISO string (None if position still open)

        Returns:
            Holding period in seconds (0 if still open)
        """
        if not exit_time:
            return 0

        entry = datetime.fromisoformat(entry_time.replace('Z', '+00:00'))
        exit = datetime.fromisoformat(exit_time.replace('Z', '+00:00'))

        return int((exit - entry).total_seconds())

    @staticmethod
    def compute_slippage_bps(expected_price: float, fill_price: float) -> int:
        """
        Compute slippage in basis points.

        Args:
            expected_price: Expected execution price
            fill_price: Actual fill price

        Returns:
            Slippage in basis points (1 bps = 0.01%)
        """
        if expected_price == 0:
            return 0

        slippage_pct = abs((fill_price - expected_price) / expected_price)
        return int(slippage_pct * 10000)  # Convert to bps

    @staticmethod
    def compute_hit_rate(outcomes: List[Dict[str, Any]]) -> Dict[str, float]:
        """
        Compute hit rate (percentage of profitable trades).

        Args:
            outcomes: List of outcome dictionaries with 'hit' boolean

        Returns:
            Dict with overall hit rate and confidence interval
        """
        if not outcomes:
            return {'hit_rate': 0.0, 'count': 0}

        hits = sum(1 for o in outcomes if o.get('hit', False))
        total = len(outcomes)
        hit_rate = hits / total if total > 0 else 0.0

        # 95% confidence interval using Wilson score interval
        # Simple approximation: sqrt(p(1-p)/n)
        if total > 0:
            margin = 1.96 * np.sqrt(hit_rate * (1 - hit_rate) / total)
        else:
            margin = 0.0

        return {
            'hit_rate': hit_rate,
            'count': total,
            'hits': hits,
            'margin_of_error': margin,
            'lower_bound': max(0, hit_rate - margin),
            'upper_bound': min(1, hit_rate + margin)
        }

    @staticmethod
    def compute_expectancy(outcomes: List[Dict[str, Any]]) -> Dict[str, float]:
        """
        Compute expectancy (average return per trade).

        Args:
            outcomes: List of outcome dictionaries with 'return_pct'

        Returns:
            Dict with expectancy and related metrics
        """
        if not outcomes:
            return {'expectancy_pct': 0.0, 'count': 0}

        returns = [o.get('return_pct', 0.0) for o in outcomes]
        expectancy = np.mean(returns) if returns else 0.0

        # Separate winners and losers
        winners = [r for r in returns if r > 0]
        losers = [r for r in returns if r < 0]

        avg_win = np.mean(winners) if winners else 0.0
        avg_loss = np.mean(losers) if losers else 0.0

        # Profit factor
        total_profit = sum(winners)
        total_loss = abs(sum(losers))
        profit_factor = total_profit / total_loss if total_loss > 0 else 0.0

        return {
            'expectancy_pct': expectancy,
            'count': len(outcomes),
            'avg_win_pct': avg_win,
            'avg_loss_pct': avg_loss,
            'profit_factor': profit_factor,
            'total_trades': len(outcomes),
            'winning_trades': len(winners),
            'losing_trades': len(losers)
        }

    @staticmethod
    def compute_sharpe_ratio(returns: List[float], risk_free_rate: float = 0.0) -> float:
        """
        Compute Sharpe ratio (annualized).

        Args:
            returns: List of returns (as decimals, e.g., 0.025 for 2.5%)
            risk_free_rate: Annual risk-free rate (as decimal)

        Returns:
            Sharpe ratio (annualized)
        """
        if not returns or len(returns) < 2:
            return 0.0

        excess_returns = [r - risk_free_rate / 252 for r in returns]  # Daily
        sharpe = np.mean(excess_returns) / np.std(excess_returns) if np.std(excess_returns) > 0 else 0.0

        # Annualize (assuming daily returns)
        return sharpe * np.sqrt(252)

    @staticmethod
    def compute_max_drawdown(equity_curve: List[float]) -> Dict[str, float]:
        """
        Compute maximum drawdown from equity curve.

        Args:
            equity_curve: List of portfolio values over time

        Returns:
            Dict with max drawdown and related metrics
        """
        if not equity_curve:
            return {'max_drawdown_pct': 0.0, 'max_drawdown': 0.0}

        equity = np.array(equity_curve)
        running_max = np.maximum.accumulate(equity)
        drawdown = (equity - running_max) / running_max
        max_dd = np.min(drawdown)

        # Find the peak and trough
        max_dd_idx = np.argmin(drawdown)
        peak_idx = np.argmax(equity[:max_dd_idx + 1])

        return {
            'max_drawdown_pct': abs(max_dd) * 100,  # Convert to percentage
            'max_drawdown': abs(equity[max_dd_idx] - equity[peak_idx]),
            'peak_value': equity[peak_idx],
            'trough_value': equity[max_dd_idx]
        }

    @staticmethod
    def compute_outcome(trade: Dict[str, Any],
                       entry_execution: Dict[str, Any],
                       exit_execution: Optional[Dict[str, Any]] = None,
                       price_history: Optional[List[float]] = None) -> Dict[str, Any]:
        """
        Compute full outcome from trade and executions.

        Args:
            trade: Trade dictionary
            entry_execution: Entry execution details
            exit_execution: Exit execution details (None if trade open)
            price_history: Price history during trade (for MAE/MFE)

        Returns:
            Complete outcome dictionary
        """
        entry_price = entry_execution['fill_price']
        quantity = trade['quantity']
        direction = trade['direction']

        # If trade is still open, we can't compute realized P&L
        if not exit_execution:
            return {
                'trade_id': trade.get('trade_id'),
                'status': 'OPEN',
                'realized_pnl': 0.0,
                'return_pct': 0.0,
                'hit': False,
                'mae': 0.0,
                'mfe': 0.0,
                'holding_time_seconds': 0
            }

        exit_price = exit_execution['fill_price']

        # Compute realized P&L
        pnl = OutcomeMetrics.compute_realized_pnl(entry_price, exit_price, quantity, direction)

        # Compute return percentage
        entry_value = entry_price * quantity
        return_pct = OutcomeMetrics.compute_return_pct(pnl, entry_value)

        # Compute MAE/MFE if price history available
        mae_mfe = {'mae': 0.0, 'mfe': 0.0}
        if price_history:
            mae_mfe = OutcomeMetrics.compute_mae_mfe(trade, price_history)

        # Compute holding period
        holding_time = OutcomeMetrics.compute_holding_period(
            entry_execution['timestamp'],
            exit_execution['timestamp']
        )

        # Determine if hit (profitable)
        hit = pnl > 0

        # Compute slippage
        entry_slippage = OutcomeMetrics.compute_slippage_bps(
            trade.get('entry_price', entry_price),
            entry_price
        )
        exit_slippage = OutcomeMetrics.compute_slippage_bps(
            trade.get('exit_price', exit_price),
            exit_price
        )

        return {
            'trade_id': trade.get('trade_id'),
            'status': 'CLOSED',
            'realized_pnl': pnl,
            'return_pct': return_pct,
            'hit': hit,
            'mae': mae_mfe['mae'],
            'mfe': mae_mfe['mfe'],
            'holding_time_seconds': holding_time,
            'entry_slippage_bps': entry_slippage,
            'exit_slippage_bps': exit_slippage,
            'total_slippage_bps': entry_slippage + exit_slippage,
            'exit_reason': trade.get('close_reason', 'unknown')
        }

    @staticmethod
    def attribute_signals(trade: Dict[str, Any],
                         decision: Dict[str, Any],
                         outcome: Dict[str, Any]) -> Dict[str, float]:
        """
        Attribute outcome to signal components.

        Simple attribution: Multiply signal strength by outcome P&L.

        Args:
            trade: Trade dictionary
            decision: Decision dictionary with signal_components
            outcome: Outcome dictionary with realized_pnl

        Returns:
            Dict mapping signal names to their attributed P&L
        """
        signal_components = decision.get('signal_components', {})
        weights_used = decision.get('weights_used', {})
        pnl = outcome.get('realized_pnl', 0.0)

        # Compute weighted signal contribution
        total_weight = sum(weights_used.values())
        if total_weight == 0:
            total_weight = 1

        attribution = {}
        for signal, strength in signal_components.items():
            weight = weights_used.get(signal, 1.0)
            weighted_strength = strength * weight
            attribution[signal] = (weighted_strength / total_weight) * pnl

        return attribution


if __name__ == "__main__":
    # Test outcome computation
    trade = {
        'trade_id': 'test-trade-1',
        'symbol': 'SPY',
        'direction': 'LONG',
        'quantity': 100,
        'entry_price': 450.0,
        'close_reason': 'take_profit'
    }

    entry_exec = {
        'execution_id': 'exec-1',
        'fill_price': 450.0,
        'timestamp': '2026-01-21T10:00:00Z'
    }

    exit_exec = {
        'execution_id': 'exec-2',
        'fill_price': 455.0,
        'timestamp': '2026-01-21T11:00:00Z'
    }

    decision = {
        'decision_id': 'dec-1',
        'signal_components': {
            'trend': 0.8,
            'momentum': 0.6,
            'mean_reversion': 0.3
        },
        'weights_used': {
            'trend': 1.0,
            'momentum': 1.0,
            'mean_reversion': 1.0
        }
    }

    outcome = OutcomeMetrics.compute_outcome(trade, entry_exec, exit_exec)
    attribution = OutcomeMetrics.attribute_signals(trade, decision, outcome)

    print("✅ Test outcome computed:")
    print(f"   Realized P&L: ${outcome['realized_pnl']:.2f}")
    print(f"   Return: {outcome['return_pct']:.2f}%")
    print(f"   Hit: {outcome['hit']}")
    print(f"   Holding time: {outcome['holding_time_seconds']}s")
    print(f"\n📊 Signal attribution:")
    for signal, pnl in attribution.items():
        print(f"   {signal}: ${pnl:.2f}")
