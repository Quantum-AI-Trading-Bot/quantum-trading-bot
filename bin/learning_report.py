#!/usr/bin/env python3
"""
Learning Report Dashboard - Display learning progress and metrics.

Shows:
- Last N decisions with confidence and outcomes
- Last N trades with P&L
- Current signal weights
- Calibration statistics
- Top improved signals
"""

import sys
import json
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Any

# Add learning module to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from learning.trade_ledger import TradeLedger
from learning.signal_weight_learner import SignalWeightLearner
from learning.confidence_calibrator import ConfidenceCalibrator
from learning.outcome_metrics import OutcomeMetrics


class LearningReport:
    """Generate and display learning reports."""

    def __init__(self):
        self.ledger = TradeLedger()
        self.weight_learner = SignalWeightLearner()
        self.calibrator = ConfidenceCalibrator()

    def print_header(self, title: str):
        """Print a formatted header."""
        print("\n" + "=" * 80)
        print(f"  {title}")
        print("=" * 80 + "\n")

    def print_recent_decisions(self, n: int = 20):
        """Print last N decisions with confidence and outcomes."""
        decisions = self.ledger.read_decisions(limit=n)

        self.print_header(f"LAST {len(decisions)} DECISIONS")

        if not decisions:
            print("No decisions recorded yet.")
            return

        for i, decision in enumerate(decisions, 1):
            decision_id = decision.get('decision_id', 'N/A')[:8]
            symbol = decision.get('symbol', 'N/A')
            action = decision.get('action', 'N/A')
            confidence = decision.get('confidence', 0.0)
            dry_run = "SHADOW" if decision.get('dry_run', True) else "LIVE"

            # Try to find outcome
            trade = self.ledger.get_trade_by_decision_id(decision_id)
            outcome = None
            if trade:
                outcome = self.ledger.get_outcome_by_trade_id(trade.get('trade_id'))

            outcome_str = "PENDING"
            if outcome:
                hit = "✓" if outcome.get('hit', False) else "✗"
                pnl = outcome.get('realized_pnl', 0.0)
                outcome_str = f"{hit} ${pnl:+.2f}"

            print(f"{i:2}. [{decision_id}] {symbol:4} {action:4} @ {confidence:.2f} "
                  f"({dry_run}) → {outcome_str}")

    def print_recent_trades(self, n: int = 20):
        """Print last N trades with P&L."""
        trades = self.ledger.read_trades(limit=n, status='CLOSED')

        self.print_header(f"LAST {len(trades)} CLOSED TRADES")

        if not trades:
            print("No closed trades yet.")
            return

        total_pnl = 0.0
        hits = 0

        for i, trade in enumerate(trades, 1):
            trade_id = trade.get('trade_id', 'N/A')[:8]
            symbol = trade.get('symbol', 'N/A')
            direction = trade.get('direction', 'N/A')
            entry_price = trade.get('entry_price', 0.0)
            exit_price = trade.get('exit_price', 0.0)
            quantity = trade.get('quantity', 0)

            # Get outcome
            outcome = self.ledger.get_outcome_by_trade_id(trade_id)
            if not outcome:
                continue

            pnl = outcome.get('realized_pnl', 0.0)
            hit = outcome.get('hit', False)
            return_pct = outcome.get('return_pct', 0.0)

            total_pnl += pnl
            if hit:
                hits += 1

            hit_str = "✓" if hit else "✗"
            print(f"{i:2}. [{trade_id}] {symbol:4} {direction:5} "
                  f"{entry_price:.2f} → {exit_price:.2f} ({quantity} shares)")
            print(f"    P&L: ${pnl:+8.2f} ({return_pct:+.2f}%) {hit_str}")

        hit_rate = hits / len(trades) if trades else 0.0
        print(f"\n📊 Total: ${total_pnl:+.2f} | Hit Rate: {hit_rate:.1%} | Trades: {len(trades)}")

    def print_signal_weights(self):
        """Print current signal weights."""
        weights = self.weight_learner.get_weights()
        ranking = self.weight_learner.get_weight_ranking()

        self.print_header("CURRENT SIGNAL WEIGHTS")

        for signal, weight in ranking:
            # Show improvement if available
            improvements = self.weight_learner.get_top_improvements(10)
            improvement = 0.0
            for imp in improvements:
                if imp['signal'] == signal:
                    improvement = imp['total_improvement']
                    break

            improvement_str = f"({improvement:+.3f})" if improvement != 0 else ""

            print(f"  {signal:15} {weight:5.2f}  {improvement_str}")

    def print_calibration_stats(self):
        """Print calibration statistics."""
        report = self.calibrator.get_calibration_report()

        self.print_header("CONFIDENCE CALIBRATION")

        print(f"Platt Scaling Parameters:")
        print(f"  A = {report['platt_params']['A']:.3f}")
        print(f"  B = {report['platt_params']['B']:.3f}")
        print(f"  sigmoid(A * confidence + B)\n")

        print("Calibration Bins:")
        print(f"  {'Bin':>8}  {'Preds':>6}  {'Hits':>5}  {'Hit Rate':>8}  {'Expected':>9}  {'Error':>6}")
        print(f"  {'-'*8}  {'-'*6}  {'-'*5}  {'-'*8}  {'-'*9}  {'-'*6}")

        for bin_info in report['calibration_bins']:
            if bin_info['predictions'] > 0:
                print(f"  {bin_info['bin']:>8}  "
                      f"{bin_info['predictions']:>6}  "
                      f"{bin_info['hits']:>5}  "
                      f"{bin_info['hit_rate']:>7.1%}  "
                      f"{bin_info['expected_hit_rate']:>8.1%}  "
                      f"{bin_info['calibration_error']:>5.3f}")

    def print_top_improvements(self, n: int = 5):
        """Print top N most improved signals."""
        improvements = self.weight_learner.get_top_improvements(n)

        self.print_header(f"TOP {len(improvements)} MOST IMPROVED SIGNALS")

        if not improvements:
            print("No improvements yet (need more trade outcomes).")
            return

        for i, imp in enumerate(improvements, 1):
            signal = imp['signal']
            improvement = imp['total_improvement']
            current_weight = self.weight_learner.weights.get(signal, 1.0)

            print(f"{i}. {signal:15} {current_weight:.2f} (Δ {improvement:+.3f})")

    def print_summary_statistics(self):
        """Print summary statistics."""
        stats = self.ledger.get_statistics()
        learner_stats = self.weight_learner.get_statistics()
        calibrator_stats = self.calibrator.statistics

        self.print_header("LEARNING SUMMARY STATISTICS")

        print(f"Ledger:")
        print(f"  Total Decisions: {stats['total_decisions']}")
        print(f"  Total Trades: {stats['total_trades']}")
        print(f"  Closed Trades: {stats['closed_trades']}")
        print(f"  Outcomes Recorded: {stats['total_outcomes']}")
        print(f"  Dry Run Decisions: {stats['dry_run_decisions']}")
        print(f"  Live Decisions: {stats['live_decisions']}")

        print(f"\nWeight Learner:")
        print(f"  Total Updates: {learner_stats['total_updates']}")
        print(f"  Trades Learned: {learner_stats['total_trades_learned']}")
        print(f"  Last Update: {learner_stats['last_update'] or 'Never'}")

        print(f"\nConfidence Calibrator:")
        print(f"  Total Calibrations: {calibrator_stats.get('total_calibrations', 0)}")
        print(f"  Last Calibration: {calibrator_stats.get('last_calibration_time', 'Never')}")

        # Compute overall hit rate
        outcomes = self.ledger.read_outcomes()
        if outcomes:
            hit_stats = OutcomeMetrics.compute_hit_rate(outcomes)
            expectancy_stats = OutcomeMetrics.compute_expectancy(outcomes)

            print(f"\nPerformance:")
            print(f"  Overall Hit Rate: {hit_stats['hit_rate']:.1%}")
            print(f"  Expectancy: {expectancy_stats['expectancy_pct']:+.2f}%")
            print(f"  Profit Factor: {expectancy_stats['profit_factor']:.2f}")
            print(f"  Win/Loss Ratio: {expectancy_stats['avg_win_pct']:.2f}% / {expectancy_stats['avg_loss_pct']:.2f}%")

    def print_safety_status(self):
        """Print safety status."""
        self.print_header("SAFETY STATUS")

        # Check if trading is enabled
        state_file = Path("/home/davidsanker/platform/state/learner_state.json")
        if state_file.exists():
            with open(state_file, 'r') as f:
                state = json.load(f)
                safety = state.get('safety_limits', {})

                trading_enabled = safety.get('trading_enabled', False)
                max_position = safety.get('max_position_size', 'N/A')
                max_drawdown = safety.get('max_drawdown_pct', 'N/A')

                print(f"  Trading Enabled: {trading_enabled}")
                print(f"  Max Position Size: {max_position}")
                print(f"  Max Drawdown: {max_drawdown}%")
        else:
            print("  No safety state file found")

        # Check weight bounds
        weights = self.weight_learner.get_weights()
        all_in_bounds = all(
            0.1 <= w <= 5.0 for w in weights.values()
        )
        print(f"  Weights Within Bounds: {'✓' if all_in_bounds else '✗'}")

    def print_full_report(self):
        """Print complete learning report."""
        print("\n" + "=" * 80)
        print("  QUANTUM TRADING LEARNING DASHBOARD")
        print("=" * 80)
        print(f"  Generated: {datetime.utcnow().isoformat()}")
        print("=" * 80)

        self.print_summary_statistics()
        self.print_safety_status()
        self.print_recent_decisions(20)
        self.print_recent_trades(20)
        self.print_signal_weights()
        self.print_calibration_stats()
        self.print_top_improvements(5)

        print("\n" + "=" * 80)
        print("  END OF REPORT")
        print("=" * 80 + "\n")


def main():
    """Main entry point."""
    import argparse

    parser = argparse.ArgumentParser(description='Generate learning report')
    parser.add_argument('--decisions', type=int, default=20,
                       help='Number of recent decisions to show')
    parser.add_argument('--trades', type=int, default=20,
                       help='Number of recent trades to show')
    parser.add_argument('--full', action='store_true',
                       help='Print full report')

    args = parser.parse_args()

    report = LearningReport()

    if args.full:
        report.print_full_report()
    else:
        report.print_summary_statistics()
        report.print_recent_decisions(args.decisions)
        report.print_recent_trades(args.trades)
        report.print_signal_weights()
        report.print_calibration_stats()
        report.print_top_improvements(5)


if __name__ == "__main__":
    main()
