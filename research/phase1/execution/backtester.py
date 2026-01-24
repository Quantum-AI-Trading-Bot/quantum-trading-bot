#!/usr/bin/env python3
"""
Phase 1: Backtesting Engine
Simulates trades and evaluates strategy performance
"""

import pandas as pd
import numpy as np
import logging
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field
from datetime import datetime
import json

logger = logging.getLogger(__name__)


@dataclass
class Trade:
    """Individual trade record"""
    entry_time: datetime
    exit_time: Optional[datetime]
    symbol: str
    action: str  # 'BUY' or 'SELL'
    entry_price: float
    exit_price: Optional[float]
    quantity: int
    stop_loss: Optional[float]
    take_profit: Optional[float]
    pnl: Optional[float]
    pnl_percent: Optional[float]
    exit_reason: str  # 'signal', 'stop_loss', 'take_profit', 'end_of_period'
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class BacktestResults:
    """Complete backtest results"""
    strategy_name: str
    symbol: str
    period: Dict[str, str]
    initial_capital: float
    final_capital: float
    total_return: float
    total_return_pct: float
    total_trades: int
    winning_trades: int
    losing_trades: int
    win_rate: float
    avg_win: float
    avg_loss: float
    profit_factor: float
    max_drawdown: float
    max_drawdown_pct: float
    sharpe_ratio: float
    trades: List[Trade] = field(default_factory=list)
    equity_curve: List[float] = field(default_factory=list)


class Backtester:
    """
    Comprehensive backtesting engine with realistic trade simulation
    """

    def __init__(
        self,
        initial_capital: float = 100000,
        commission: float = 0.001,  # 0.1% per trade
        slippage: float = 0.0001,  # 0.01% slippage
        position_size_pct: float = 0.95,  # Use 95% of capital per trade
        stop_loss_pct: float = 0.02,  # 2% stop loss
        take_profit_pct: float = 0.05,  # 5% take profit
    ):
        """
        Initialize backtester

        Args:
            initial_capital: Starting capital
            commission: Commission rate per trade
            slippage: Slippage rate per trade
            position_size_pct: Percentage of capital to use per trade
            stop_loss_pct: Stop loss percentage
            take_profit_pct: Take profit percentage
        """
        self.initial_capital = initial_capital
        self.commission = commission
        self.slippage = slippage
        self.position_size_pct = position_size_pct
        self.stop_loss_pct = stop_loss_pct
        self.take_profit_pct = take_profit_pct

        logger.info(f"Backtester initialized: ${initial_capital:,.2f} initial capital")

    def run_backtest(
        self,
        data: pd.DataFrame,
        signals: pd.DataFrame
    ) -> BacktestResults:
        """
        Run backtest on price data with signals

        Args:
            data: DataFrame with OHLCV data
            signals: DataFrame with Signal column

        Returns:
            BacktestResults object with complete results
        """
        logger.info("Starting backtest...")

        # Ensure data and signals are aligned
        if len(data) != len(signals):
            raise ValueError("Data and signals must have same length")

        # Initialize backtest state
        capital = self.initial_capital
        position = 0  # Number of shares
        trades = []
        equity_curve = [capital]

        current_trade = None
        peak_equity = capital
        max_drawdown = 0
        max_drawdown_pct = 0

        # Simulate trades day by day
        for i in range(1, len(data)):
            current_price = data['Close'].iloc[i]
            current_high = data['High'].iloc[i]
            current_low = data['Low'].iloc[i]
            signal = signals['Signal'].iloc[i-1]  # Use previous day's signal
            timestamp = data.index[i]

            # Check exit conditions if in position
            if position > 0 and current_trade:
                # Check stop loss
                if current_low <= current_trade.stop_loss:
                    exit_price = current_trade.stop_loss
                    exit_reason = 'stop_loss'
                    capital, position = self._exit_trade(capital, position, exit_price)
                    current_trade = self._close_trade(current_trade, exit_price, timestamp, exit_reason, capital)
                    trades.append(current_trade)
                    current_trade = None

                # Check take profit
                elif current_high >= current_trade.take_profit:
                    exit_price = current_trade.take_profit
                    exit_reason = 'take_profit'
                    capital, position = self._exit_trade(capital, position, exit_price)
                    current_trade = self._close_trade(current_trade, exit_price, timestamp, exit_reason, capital)
                    trades.append(current_trade)
                    current_trade = None

                # Check for sell signal
                elif signal == 'SELL':
                    exit_price = current_price * (1 - self.slippage)  # Apply slippage
                    exit_reason = 'signal'
                    capital, position = self._exit_trade(capital, position, exit_price)
                    current_trade = self._close_trade(current_trade, exit_price, timestamp, exit_reason, capital)
                    trades.append(current_trade)
                    current_trade = None

            # Enter new position
            elif position == 0 and signal == 'BUY':
                entry_price = current_price * (1 + self.slippage)  # Apply slippage
                position_size = capital * self.position_size_pct
                quantity = int(position_size / entry_price)

                if quantity > 0:
                    cost = quantity * entry_price * (1 + self.commission)
                    if cost <= capital:
                        capital -= cost
                        position = quantity

                        current_trade = Trade(
                            entry_time=timestamp,
                            exit_time=None,
                            symbol=data.get('Symbol', 'UNKNOWN').iloc[0],
                            action='BUY',
                            entry_price=entry_price,
                            exit_price=None,
                            quantity=quantity,
                            stop_loss=entry_price * (1 - self.stop_loss_pct),
                            take_profit=entry_price * (1 + self.take_profit_pct),
                            pnl=None,
                            pnl_percent=None,
                            exit_reason=None
                        )

            # Calculate current equity
            if position > 0:
                current_equity = capital + (position * current_price)
            else:
                current_equity = capital

            equity_curve.append(current_equity)

            # Update max drawdown
            if current_equity > peak_equity:
                peak_equity = current_equity

            drawdown = peak_equity - current_equity
            drawdown_pct = (drawdown / peak_equity) * 100

            if drawdown > max_drawdown:
                max_drawdown = drawdown
                max_drawdown_pct = drawdown_pct

        # Close any open position at end
        if position > 0 and current_trade:
            final_price = data['Close'].iloc[-1]
            capital, position = self._exit_trade(capital, position, final_price)
            current_trade = self._close_trade(current_trade, final_price, data.index[-1], 'end_of_period', capital)
            trades.append(current_trade)

        # Calculate results
        results = self._calculate_results(
            trades=trades,
            equity_curve=equity_curve,
            initial_capital=self.initial_capital,
            final_capital=capital,
            max_drawdown=max_drawdown,
            max_drawdown_pct=max_drawdown_pct
        )

        logger.info(f"Backtest complete. Return: {results.total_return_pct:.2f}%, Trades: {results.total_trades}")
        return results

    def _exit_trade(self, capital: float, position: int, exit_price: float) -> tuple:
        """Calculate capital after exiting position"""
        proceeds = position * exit_price * (1 - self.commission)
        new_capital = capital + proceeds
        return new_capital, 0

    def _close_trade(self, trade: Trade, exit_price: float, exit_time: datetime, exit_reason: str, capital: float) -> Trade:
        """Close trade and calculate P&L"""
        trade.exit_time = exit_time
        trade.exit_price = exit_price
        trade.exit_reason = exit_reason

        # Calculate P&L
        trade.pnl = (exit_price - trade.entry_price) * trade.quantity
        trade.pnl_percent = ((exit_price - trade.entry_price) / trade.entry_price) * 100

        return trade

    def _calculate_results(
        self,
        trades: List[Trade],
        equity_curve: List[float],
        initial_capital: float,
        final_capital: float,
        max_drawdown: float,
        max_drawdown_pct: float
    ) -> BacktestResults:
        """Calculate complete backtest results"""

        total_return = final_capital - initial_capital
        total_return_pct = (total_return / initial_capital) * 100

        winning_trades = [t for t in trades if t.pnl and t.pnl > 0]
        losing_trades = [t for t in trades if t.pnl and t.pnl < 0]

        win_rate = (len(winning_trades) / len(trades) * 100) if trades else 0

        avg_win = np.mean([t.pnl for t in winning_trades]) if winning_trades else 0
        avg_loss = np.mean([t.pnl for t in losing_trades]) if losing_trades else 0

        total_wins = sum([t.pnl for t in winning_trades]) if winning_trades else 0
        total_losses = abs(sum([t.pnl for t in losing_trades])) if losing_trades else 0
        profit_factor = total_wins / total_losses if total_losses > 0 else float('inf')

        # Calculate Sharpe Ratio (simplified)
        returns = pd.Series(equity_curve).pct_change().dropna()
        sharpe_ratio = (returns.mean() / returns.std()) * np.sqrt(252) if returns.std() > 0 else 0

        return BacktestResults(
            strategy_name="Backtest",
            symbol="SYMBOL",
            period={'start': '2024-01-01', 'end': '2025-01-01'},
            initial_capital=initial_capital,
            final_capital=final_capital,
            total_return=total_return,
            total_return_pct=total_return_pct,
            total_trades=len(trades),
            winning_trades=len(winning_trades),
            losing_trades=len(losing_trades),
            win_rate=win_rate,
            avg_win=avg_win,
            avg_loss=avg_loss,
            profit_factor=profit_factor,
            max_drawdown=max_drawdown,
            max_drawdown_pct=max_drawdown_pct,
            sharpe_ratio=sharpe_ratio,
            trades=trades,
            equity_curve=equity_curve
        )

    def save_results(self, results: BacktestResults, filename: str):
        """Save backtest results to file"""
        results_dict = {
            'strategy_name': results.strategy_name,
            'symbol': results.symbol,
            'period': results.period,
            'initial_capital': results.initial_capital,
            'final_capital': results.final_capital,
            'total_return': results.total_return,
            'total_return_pct': results.total_return_pct,
            'total_trades': results.total_trades,
            'winning_trades': results.winning_trades,
            'losing_trades': results.losing_trades,
            'win_rate': results.win_rate,
            'avg_win': results.avg_win,
            'avg_loss': results.avg_loss,
            'profit_factor': results.profit_factor,
            'max_drawdown': results.max_drawdown,
            'max_drawdown_pct': results.max_drawdown_pct,
            'sharpe_ratio': results.sharpe_ratio,
            'trades': [
                {
                    'entry_time': str(t.entry_time),
                    'exit_time': str(t.exit_time) if t.exit_time else None,
                    'symbol': t.symbol,
                    'action': t.action,
                    'entry_price': t.entry_price,
                    'exit_price': t.exit_price,
                    'quantity': t.quantity,
                    'pnl': t.pnl,
                    'pnl_percent': t.pnl_percent,
                    'exit_reason': t.exit_reason
                }
                for t in results.trades
            ]
        }

        with open(filename, 'w') as f:
            json.dump(results_dict, f, indent=2)

        logger.info(f"Results saved to {filename}")

    def print_results(self, results: BacktestResults):
        """Print backtest results summary"""
        print(f"\n{'='*60}")
        print(f"BACKTEST RESULTS")
        print(f"{'='*60}\n")
        print(f"Initial Capital: ${results.initial_capital:,.2f}")
        print(f"Final Capital:   ${results.final_capital:,.2f}")
        print(f"Total Return:    ${results.total_return:,.2f} ({results.total_return_pct:.2f}%)")
        print(f"\nTrading Statistics:")
        print(f"Total Trades:    {results.total_trades}")
        print(f"Winning Trades:  {results.winning_trades}")
        print(f"Losing Trades:   {results.losing_trades}")
        print(f"Win Rate:        {results.win_rate:.2f}%")
        print(f"\nPerformance Metrics:")
        print(f"Avg Win:         ${results.avg_win:,.2f}")
        print(f"Avg Loss:        ${results.avg_loss:,.2f}")
        print(f"Profit Factor:   {results.profit_factor:.2f}")
        print(f"Max Drawdown:    ${results.max_drawdown:,.2f} ({results.max_drawdown_pct:.2f}%)")
        print(f"Sharpe Ratio:    {results.sharpe_ratio:.2f}")
        print(f"\n{'='*60}\n")
