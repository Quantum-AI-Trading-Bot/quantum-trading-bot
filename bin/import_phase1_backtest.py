#!/usr/bin/env python3
"""
Phase 1 Backtest to Ledger Exporter
Converts Phase 1 backtest JSON results into learning ledger format
"""

import sys
import json
import uuid
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, List
import argparse

# Add platform to path
platform_path = Path(__file__).parent.parent
sys.path.insert(0, str(platform_path))


class BacktestToLedgerExporter:
    """Exports Phase 1 backtest results to learning ledgers."""

    def __init__(self, ledger_dir: str = "/home/davidsanker/platform/state/ledgers"):
        self.ledger_dir = Path(ledger_dir)
        self.ledger_dir.mkdir(parents=True, exist_ok=True)

        self.decisions_file = self.ledger_dir / "decisions.jsonl"
        self.trades_file = self.ledger_dir / "trades.jsonl"
        self.outcomes_file = self.ledger_dir / "outcomes.jsonl"

    def export_backtest(
        self,
        backtest_json_path: str,
        backtest_id: str = None,
        source: str = "phase1_backtest"
    ) -> Dict[str, int]:
        """
        Export a Phase 1 backtest JSON to ledger format.

        Args:
            backtest_json_path: Path to Phase 1 backtest JSON file
            backtest_id: Optional custom backtest ID (auto-generated if None)
            source: Source identifier

        Returns:
            Dict with counts of exported records
        """
        # Load backtest JSON
        with open(backtest_json_path, 'r') as f:
            backtest = json.load(f)

        # Generate backtest ID if not provided
        if backtest_id is None:
            backtest_id = self._generate_backtest_id(backtest_json_path, backtest)

        print(f"\nExporting backtest: {backtest_id}")
        print(f"Source: {backtest_json_path}")

        # Export trades to ledgers
        counts = {
            'decisions': 0,
            'trades': 0,
            'outcomes': 0
        }

        for i, trade in enumerate(backtest.get('trades', [])):
            decision_id = f"phase1_{backtest_id}_trade_{i}"

            # Create decision record
            decision = self._create_decision_record(
                trade, decision_id, backtest_id, source, backtest
            )
            self._append_to_ledger(self.decisions_file, decision)
            counts['decisions'] += 1

            # Create trade record
            trade_record = self._create_trade_record(
                trade, decision_id, backtest_id, source
            )
            self._append_to_ledger(self.trades_file, trade_record)
            counts['trades'] += 1

            # Create outcome record
            outcome = self._create_outcome_record(
                trade, decision_id, backtest_id, source
            )
            self._append_to_ledger(self.outcomes_file, outcome)
            counts['outcomes'] += 1

        print(f"\nExported:")
        print(f"  - {counts['decisions']} decisions → {self.decisions_file}")
        print(f"  - {counts['trades']} trades → {self.trades_file}")
        print(f"  - {counts['outcomes']} outcomes → {self.outcomes_file}")

        return counts

    def _generate_backtest_id(self, json_path: str, backtest: Dict) -> str:
        """Generate unique backtest ID."""
        # Extract info from filename and backtest data
        path = Path(json_path)
        symbol = backtest.get('symbol', 'UNKNOWN').lower()

        # Try to parse timestamp from filename
        stem = path.stem  # e.g., "backtest_results_SPY_20260123_120500"
        parts = stem.split('_')
        if len(parts) >= 4:
            timestamp = '_'.join(parts[-2:])  # "20260123_120500"
        else:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')

        # Extract strategy from metadata if available
        strategy = backtest.get('strategy_name', 'backtest').lower()

        return f"{symbol}_{strategy}_{timestamp}"

    def _create_decision_record(
        self,
        trade: Dict,
        decision_id: str,
        backtest_id: str,
        source: str,
        backtest: Dict
    ) -> Dict:
        """Create a decision ledger record from a trade."""
        entry_time = trade.get('entry_time', '')

        return {
            'decision_id': decision_id,
            'timestamp': entry_time,
            'symbol': trade.get('symbol', 'UNKNOWN'),
            'action': trade.get('action', 'HOLD'),
            'confidence': 0.8,  # Phase 1 strategies don't have per-trade confidence
            'model_name': f"phase1_{backtest.get('strategy_name', 'backtest')}",
            'model_version': '1.0.0',
            'features': {
                # We don't have feature values in trade JSON, but we can record what we know
                'entry_price': trade.get('entry_price', 0.0),
                'quantity': trade.get('quantity', 0)
            },
            'signal_components': {},
            'metadata': {
                'source': source,
                'backtest_file': str(backtest_id),
                'backtest_id': backtest_id,
                'phase1_strategy': backtest.get('strategy_name', 'backtest'),
                'phase1_params': {
                    'initial_capital': backtest.get('initial_capital', 0),
                    'period': backtest.get('period', {})
                },
                'entry_price': trade.get('entry_price', 0.0),
                'quantity': trade.get('quantity', 0)
            }
        }

    def _create_trade_record(
        self,
        trade: Dict,
        decision_id: str,
        backtest_id: str,
        source: str
    ) -> Dict:
        """Create a trade ledger record from a trade."""
        return {
            'trade_id': decision_id,  # Use same ID for backtest (1:1 mapping)
            'decision_id': decision_id,
            'timestamp': trade.get('entry_time', ''),
            'symbol': trade.get('symbol', 'UNKNOWN'),
            'action': trade.get('action', 'HOLD'),
            'quantity': trade.get('quantity', 0),
            'price': trade.get('entry_price', 0.0),
            'execution_type': 'SIMULATED',
            'commission': 0.0,  # Phase 1 may or may not include commission
            'status': 'FILLED',
            'metadata': {
                'source': source,
                'backtest_id': backtest_id,
                'exit_time': trade.get('exit_time', ''),
                'exit_price': trade.get('exit_price', 0.0),
                'exit_reason': trade.get('exit_reason', 'unknown')
            }
        }

    def _create_outcome_record(
        self,
        trade: Dict,
        decision_id: str,
        backtest_id: str,
        source: str
    ) -> Dict:
        """Create an outcome ledger record from a completed trade."""
        exit_time = trade.get('exit_time', '')
        entry_time = trade.get('entry_time', '')

        # Calculate hold duration
        try:
            exit_dt = datetime.fromisoformat(exit_time.replace('Z', '+00:00'))
            entry_dt = datetime.fromisoformat(entry_time.replace('Z', '+00:00'))
            hold_duration_seconds = int((exit_dt - entry_dt).total_seconds())
        except:
            hold_duration_seconds = 0

        pnl_pct = trade.get('pnl_percent', 0.0)
        pnl_abs = trade.get('pnl', 0.0)

        return {
            'outcome_id': f"phase1_{backtest_id}_outcome_{decision_id}",
            'decision_id': decision_id,
            'trade_id': decision_id,
            'timestamp': exit_time,
            'symbol': trade.get('symbol', 'UNKNOWN'),
            'action': trade.get('action', 'HOLD'),
            'confidence': 0.8,
            'pnl_pct': pnl_pct,
            'pnl_abs': pnl_abs,
            'win': pnl_abs > 0,
            'shadow': False,
            'hold_duration_seconds': hold_duration_seconds,
            'label_time': exit_time,
            'metadata': {
                'source': source,
                'backtest_id': backtest_id,
                'exit_reason': trade.get('exit_reason', 'unknown'),
                'phase1_strategy': backtest_id.split('_')[1] if '_' in backtest_id else 'unknown'
            }
        }

    def _append_to_ledger(self, ledger_file: Path, record: Dict):
        """Append a JSON record to a ledger file."""
        with open(ledger_file, 'a') as f:
            f.write(json.dumps(record) + '\n')


def main():
    """CLI entry point."""
    parser = argparse.ArgumentParser(
        description='Import Phase 1 backtest results into learning ledgers'
    )
    parser.add_argument(
        'backtest_json',
        help='Path to Phase 1 backtest JSON file'
    )
    parser.add_argument(
        '--backtest-id',
        help='Custom backtest ID (auto-generated if not provided)'
    )
    parser.add_argument(
        '--ledger-dir',
        default='/home/davidsanker/platform/state/ledgers',
        help='Ledger directory (default: /home/davidsanker/platform/state/ledgers)'
    )
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Print what would be exported without actually writing'
    )

    args = parser.parse_args()

    # Validate input file exists
    if not Path(args.backtest_json).exists():
        print(f"Error: File not found: {args.backtest_json}")
        sys.exit(1)

    # Create exporter
    exporter = BacktestToLedgerExporter(ledger_dir=args.ledger_dir)

    if args.dry_run:
        print("DRY RUN MODE - No files will be written")
        # TODO: Implement dry-run preview
        print("(Dry-run preview not implemented yet)")

    # Export backtest
    try:
        counts = exporter.export_backtest(
            args.backtest_json,
            backtest_id=args.backtest_id
        )

        print("\n✅ Export complete!")
        sys.exit(0)

    except Exception as e:
        print(f"\n❌ Export failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
