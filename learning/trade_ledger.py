#!/usr/bin/env python3
"""
Trade Ledger - Append-only storage for trading decisions and outcomes.

Uses JSONL format for simplicity and reliability.
Each line is a self-contained JSON record.
"""

import json
import uuid
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any
import threading


class TradeLedger:
    """Append-only ledger for trading decisions, executions, and outcomes."""

    def __init__(self, ledger_dir: str = "/home/davidsanker/platform/state"):
        self.ledger_dir = Path(ledger_dir)
        self.decisions_file = self.ledger_dir / "decisions.jsonl"
        self.executions_file = self.ledger_dir / "executions.jsonl"
        self.trades_file = self.ledger_dir / "trades.jsonl"
        self.outcomes_file = self.ledger_dir / "outcomes.jsonl"

        # Create directory if it doesn't exist
        self.ledger_dir.mkdir(parents=True, exist_ok=True)

        # Thread lock for concurrent writes
        self._lock = threading.Lock()

        # Initialize files with headers if they don't exist
        self._init_files()

    def _init_files(self):
        """Initialize ledger files if they don't exist."""
        for f in [self.decisions_file, self.executions_file,
                  self.trades_file, self.outcomes_file]:
            if not f.exists():
                f.write_text("")

    def _append_record(self, file_path: Path, record: Dict[str, Any]) -> None:
        """Append a JSON record to a ledger file (thread-safe)."""
        with self._lock:
            # Add timestamp if not present
            if 'timestamp' not in record:
                record['timestamp'] = datetime.utcnow().isoformat()

            # Add record ID if not present
            if 'id' not in record:
                record['id'] = str(uuid.uuid4())

            # Append to file
            with open(file_path, 'a') as f:
                f.write(json.dumps(record) + '\n')

    def write_decision(self, decision: Dict[str, Any]) -> str:
        """
        Write a trading decision to the ledger.

        Args:
            decision: Decision dictionary with keys:
                - symbol, action, confidence, signal_components,
                  weights_used, market_state, dry_run, trading_enabled

        Returns:
            decision_id: UUID of the written decision
        """
        decision_id = str(uuid.uuid4())
        decision['decision_id'] = decision_id

        self._append_record(self.decisions_file, decision)
        return decision_id

    def write_execution(self, execution: Dict[str, Any]) -> str:
        """
        Write an execution to the ledger.

        Args:
            execution: Execution dictionary with keys:
                - decision_id, order_id, symbol, action, quantity,
                  fill_price, slippage_bps, execution_time_ms

        Returns:
            execution_id: UUID of the written execution
        """
        execution_id = str(uuid.uuid4())
        execution['execution_id'] = execution_id

        self._append_record(self.executions_file, execution)
        return execution_id

    def write_trade(self, trade: Dict[str, Any]) -> str:
        """
        Write a trade to the ledger.

        Args:
            trade: Trade dictionary with keys:
                - decision_id, symbol, direction, entry_execution,
                  exit_execution (optional), entry_time, status

        Returns:
            trade_id: UUID of the written trade
        """
        trade_id = str(uuid.uuid4())
        trade['trade_id'] = trade_id

        self._append_record(self.trades_file, trade)
        return trade_id

    def write_outcome(self, outcome: Dict[str, Any]) -> str:
        """
        Write an outcome to the ledger.

        Args:
            outcome: Outcome dictionary with keys:
                - trade_id, realized_pnl, return_pct, hit,
                  mae, mfe, signal_attribution

        Returns:
            outcome_id: UUID of the written outcome
        """
        outcome_id = str(uuid.uuid4())
        outcome['outcome_id'] = outcome_id

        self._append_record(self.outcomes_file, outcome)
        return outcome_id

    def read_decisions(self, limit: Optional[int] = None) -> List[Dict[str, Any]]:
        """Read decisions from the ledger (most recent first)."""
        decisions = []
        if not self.decisions_file.exists():
            return decisions

        with open(self.decisions_file, 'r') as f:
            for line in f:
                if line.strip():
                    decisions.append(json.loads(line))

        # Reverse to get most recent first
        decisions = decisions[::-1]

        if limit:
            decisions = decisions[:limit]

        return decisions

    def read_executions(self, limit: Optional[int] = None) -> List[Dict[str, Any]]:
        """Read executions from the ledger (most recent first)."""
        executions = []
        if not self.executions_file.exists():
            return executions

        with open(self.executions_file, 'r') as f:
            for line in f:
                if line.strip():
                    executions.append(json.loads(line))

        executions = executions[::-1]

        if limit:
            executions = executions[:limit]

        return executions

    def read_trades(self, limit: Optional[int] = None,
                    status: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Read trades from the ledger (most recent first).

        Args:
            limit: Maximum number of trades to return
            status: Filter by status ('OPEN', 'CLOSED', 'CANCELED')
        """
        trades = []
        if not self.trades_file.exists():
            return trades

        with open(self.trades_file, 'r') as f:
            for line in f:
                if line.strip():
                    trade = json.loads(line)
                    if status is None or trade.get('status') == status:
                        trades.append(trade)

        trades = trades[::-1]

        if limit:
            trades = trades[:limit]

        return trades

    def read_outcomes(self, limit: Optional[int] = None) -> List[Dict[str, Any]]:
        """Read outcomes from the ledger (most recent first)."""
        outcomes = []
        if not self.outcomes_file.exists():
            return outcomes

        with open(self.outcomes_file, 'r') as f:
            for line in f:
                if line.strip():
                    outcomes.append(json.loads(line))

        outcomes = outcomes[::-1]

        if limit:
            outcomes = outcomes[:limit]

        return outcomes

    def get_decision_by_id(self, decision_id: str) -> Optional[Dict[str, Any]]:
        """Get a specific decision by ID."""
        decisions = self.read_decisions()
        for d in decisions:
            if d.get('decision_id') == decision_id:
                return d
        return None

    def get_trade_by_decision_id(self, decision_id: str) -> Optional[Dict[str, Any]]:
        """Get the trade associated with a decision."""
        trades = self.read_trades()
        for t in trades:
            if t.get('decision_id') == decision_id:
                return t
        return None

    def get_outcome_by_trade_id(self, trade_id: str) -> Optional[Dict[str, Any]]:
        """Get the outcome associated with a trade."""
        outcomes = self.read_outcomes()
        for o in outcomes:
            if o.get('trade_id') == trade_id:
                return o
        return None

    def get_statistics(self) -> Dict[str, Any]:
        """Get summary statistics from the ledger."""
        decisions = self.read_decisions()
        executions = self.read_executions()
        trades = self.read_trades()
        outcomes = self.read_outcomes()

        closed_trades = [t for t in trades if t.get('status') == 'CLOSED']

        return {
            'total_decisions': len(decisions),
            'total_executions': len(executions),
            'total_trades': len(trades),
            'closed_trades': len(closed_trades),
            'total_outcomes': len(outcomes),
            'dry_run_decisions': sum(1 for d in decisions if d.get('dry_run', False)),
            'live_decisions': sum(1 for d in decisions if not d.get('dry_run', False))
        }


if __name__ == "__main__":
    # Test the ledger
    ledger = TradeLedger()

    # Write a test decision
    decision_id = ledger.write_decision({
        'symbol': 'SPY',
        'action': 'BUY',
        'confidence': 0.75,
        'signal_components': {
            'trend': 0.8,
            'momentum': 0.6,
            'mean_reversion': 0.3,
            'volume': 0.5,
            'volatility': 0.4
        },
        'weights_used': {
            'trend': 1.0,
            'momentum': 1.0,
            'mean_reversion': 1.0,
            'volume': 1.0,
            'volatility': 1.0
        },
        'market_state': {
            'regime': 'bullish',
            'volatility_regime': 'normal'
        },
        'dry_run': True,
        'trading_enabled': False
    })

    print(f"✅ Test decision written: {decision_id}")
    print(f"📊 Ledger stats: {ledger.get_statistics()}")
