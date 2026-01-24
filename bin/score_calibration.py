#!/usr/bin/env python3
"""
Calibration Scorer - Phase 3.0

Computes shadow outcomes, hit-rate, calibration metrics, and updates learning state.
"""

import sys
import os
import json
import csv
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, List, Any
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class CalibrationScorer:
    """Score calibration and compute metrics."""

    def __init__(self, decisions_file: str, output_dir: str):
        """Initialize scorer."""
        self.decisions_file = Path(decisions_file)
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

        self.decisions = []
        self.metrics = {}

    def load_decisions(self):
        """Load decisions from JSONL or CSV."""
        logger.info(f"Loading decisions from {self.decisions_file}")

        if self.decisions_file.suffix == '.jsonl':
            with open(self.decisions_file, 'r') as f:
                for line in f:
                    if line.strip():
                        self.decisions.append(json.loads(line))
        elif self.decisions_file.suffix == '.csv':
            with open(self.decisions_file, 'r') as f:
                reader = csv.DictReader(f)
                self.decisions = list(reader)
        else:
            raise ValueError(f"Unsupported file type: {self.decisions_file.suffix}")

        # Convert numeric fields
        for d in self.decisions:
            d['confidence'] = float(d.get('confidence', 0.5))
            d['target_value_pct'] = float(d.get('target_value_pct', 0.0))

        logger.info(f"Loaded {len(self.decisions)} decisions")

    def fetch_next_day_returns(self) -> Dict[str, List[float]]:
        """
        Fetch next-day returns for symbols using yfinance.
        Returns dict mapping symbol to list of returns.
        """
        logger.info("Fetching next-day returns using yfinance...")

        try:
            import yfinance as yf
        except ImportError:
            logger.warning("yfinance not available, using simple simulation")
            return self._simulate_returns()

        returns_by_symbol = {}

        for symbol in set(d['symbol'] for d in self.decisions):
            try:
                # Fetch last 5 days to get recent returns
                ticker = yf.Ticker(symbol)
                data = ticker.history(period="5d", interval="1d")

                if len(data) >= 2:
                    # Compute daily returns
                    closes = data['Close'].values
                    daily_returns = []
                    for i in range(1, len(closes)):
                        ret = (closes[i] - closes[i-1]) / closes[i-1]
                        daily_returns.append(ret)

                    returns_by_symbol[symbol] = daily_returns
                    logger.info(f"  {symbol}: {len(daily_returns)} returns fetched")
                else:
                    logger.warning(f"  {symbol}: Insufficient data, using simulation")
                    returns_by_symbol[symbol] = [0.0] * 5

            except Exception as e:
                logger.error(f"  {symbol}: Error fetching data: {e}")
                returns_by_symbol[symbol] = [0.0] * 5

        return returns_by_symbol

    def _simulate_returns(self) -> Dict[str, List[float]]:
        """Simulate returns if yfinance not available."""
        logger.warning("Using simulated returns - not for production!")
        returns_by_symbol = {}
        for symbol in set(d['symbol'] for d in self.decisions):
            # Simulate with some volatility
            import random
            random.seed(hash(symbol))
            returns_by_symbol[symbol] = [random.uniform(-0.02, 0.02) for _ in range(5)]
        return returns_by_symbol

    def compute_outcomes(self, returns_by_symbol: Dict[str, List[float]]):
        """Compute shadow outcomes for each decision."""
        logger.info("Computing shadow outcomes...")

        for i, decision in enumerate(self.decisions):
            symbol = decision['symbol']
            action = decision['action']

            # Get next return (use first available for simplicity)
            returns = returns_by_symbol.get(symbol, [0.0])
            if returns:
                next_return = returns[0]
            else:
                next_return = 0.0

            # Compute outcome label
            if action == 'BUY':
                decision['outcome'] = 1 if next_return > 0.001 else (-1 if next_return < -0.001 else 0)
                decision['next_return'] = next_return
                decision['hit'] = 1 if next_return > 0 else 0
            elif action == 'SELL':
                decision['outcome'] = 1 if next_return < -0.001 else (-1 if next_return > 0.001 else 0)
                decision['next_return'] = next_return
                decision['hit'] = 1 if next_return < 0 else 0
            else:  # HOLD
                decision['outcome'] = 0
                decision['next_return'] = next_return
                decision['hit'] = None  # HOLD not scored

        logger.info(f"Outcomes computed for {len(self.decisions)} decisions")

    def compute_metrics(self):
        """Compute calibration metrics."""
        logger.info("Computing metrics...")

        # Filter to trades only (BUY/SELL)
        trades = [d for d in self.decisions if d['action'] in ['BUY', 'SELL']]

        if not trades:
            logger.warning("No trades found, computing basic metrics only")
            self.metrics = {
                'total_decisions': len(self.decisions),
                'trades': 0,
                'activity_rate': 0.0,
                'buy_count': 0,
                'sell_count': 0,
                'hold_count': len(self.decisions)
            }
            return

        # Basic stats
        buy_trades = [d for d in trades if d['action'] == 'BUY']
        sell_trades = [d for d in trades if d['action'] == 'SELL']

        # Hit rate
        hits = sum(1 for d in trades if d.get('hit') == 1)
        hit_rate = hits / len(trades) if trades else 0.0

        # Activity rate
        activity_rate = len(trades) / len(self.decisions) if self.decisions else 0.0

        # Confidence stats
        confidences = [d['confidence'] for d in trades]
        avg_confidence = sum(confidences) / len(confidences) if confidences else 0.0

        # Calibration bins
        bins = {}
        for d in trades:
            conf = d['confidence']
            bin_key = int(conf * 10)  # 0-1 → 0-10
            if bin_key not in bins:
                bins[bin_key] = {'predictions': 0, 'hits': 0}
            bins[bin_key]['predictions'] += 1
            if d.get('hit') == 1:
                bins[bin_key]['hits'] += 1

        # Compute calibration error
        calibration_error = 0.0
        bin_count = 0
        for bin_key, data in bins.items():
            if data['predictions'] > 0:
                predicted_conf = bin_key / 10.0
                actual_conf = data['hits'] / data['predictions']
                error = (predicted_conf - actual_conf) ** 2
                calibration_error += error
                bin_count += 1

        if bin_count > 0:
            calibration_error /= bin_count

        # Brier score
        brier_score = 0.0
        for d in trades:
            if d.get('hit') is not None:
                brier_score += (d['confidence'] - d['hit']) ** 2

        if trades:
            brier_score /= len(trades)

        self.metrics = {
            'total_decisions': len(self.decisions),
            'trades': len(trades),
            'activity_rate': round(activity_rate, 4),
            'buy_count': len(buy_trades),
            'sell_count': len(sell_trades),
            'hold_count': len(self.decisions) - len(trades),
            'hit_rate': round(hit_rate, 4),
            'avg_confidence': round(avg_confidence, 4),
            'calibration_error': round(calibration_error, 4),
            'brier_score': round(brier_score, 4),
            'calibration_bins': bins,
            'trades_by_symbol': {}
        }

        # Trades by symbol
        for symbol in set(d['symbol'] for d in trades):
            symbol_trades = [d for d in trades if d['symbol'] == symbol]
            symbol_hits = sum(1 for d in symbol_trades if d.get('hit') == 1)
            self.metrics['trades_by_symbol'][symbol] = {
                'total': len(symbol_trades),
                'hits': symbol_hits,
                'hit_rate': round(symbol_hits / len(symbol_trades), 4) if symbol_trades else 0.0
            }

        logger.info(f"Metrics computed: {len(trades)} trades, {hit_rate:.2%} hit rate")

    def update_learning_state(self):
        """Update shadow learning state."""
        logger.info("Updating learning state...")

        state_path = Path("/home/davidsanker/platform/state/learner_state.json")
        state_path.parent.mkdir(parents=True, exist_ok=True)

        # Load existing state or create new
        if state_path.exists():
            try:
                with open(state_path, 'r') as f:
                    state = json.load(f)
            except:
                state = {}
        else:
            state = {}

        # Simple weight update based on signal components
        signal_weights = state.get('signal_weights', {'momentum': 1.0})

        # Analyze momentum performance
        momentum_hits = 0
        momentum_total = 0

        for d in self.decisions:
            if d['action'] in ['BUY', 'SELL']:
                momentum_total += 1
                if d.get('hit') == 1:
                    momentum_hits += 1

        # Update weight
        if momentum_total > 0:
            momentum_hit_rate = momentum_hits / momentum_total
            if momentum_hit_rate > 0.5:
                # Increase weight if performing well
                signal_weights['momentum'] *= 1.1
            else:
                # Decrease weight if performing poorly
                signal_weights['momentum'] *= 0.9

            # Clamp weight
            signal_weights['momentum'] = max(0.1, min(5.0, signal_weights['momentum']))

        # Update state
        state['signal_weights'] = signal_weights
        state['last_updated'] = datetime.utcnow().isoformat()
        state['total_decisions_learned'] = state.get('total_decisions_learned', 0) + len(self.decisions)

        # Backup existing state
        if state_path.exists():
            backup_path = state_path.with_suffix(f".bak_{datetime.now().strftime('%Y%m%d_%H%M%S')}")
            import shutil
            shutil.copy(state_path, backup_path)
            logger.info(f"Backed up state to {backup_path}")

        # Save new state
        with open(state_path, 'w') as f:
            json.dump(state, f, indent=2)

        logger.info(f"Learning state updated: momentum weight = {signal_weights['momentum']:.2f}")

    def save_metrics(self):
        """Save metrics to file."""
        metrics_path = self.output_dir / "05_metrics.json"
        with open(metrics_path, 'w') as f:
            json.dump(self.metrics, f, indent=2)
        logger.info(f"Metrics saved to {metrics_path}")

    def generate_calibration_report(self):
        """Generate calibration report."""
        report_path = self.output_dir / "06_calibration_report.md"

        with open(report_path, 'w') as f:
            f.write("# Calibration Report\n\n")
            f.write(f"**Date**: {datetime.now().isoformat()}\n")
            f.write(f"**Decisions**: {self.metrics.get('total_decisions', 0)}\n")
            f.write(f"**Trades**: {self.metrics.get('trades', 0)}\n\n")

            f.write("## Summary\n\n")
            f.write(f"- **Activity Rate**: {self.metrics.get('activity_rate', 0):.2%}\n")
            f.write(f"- **Hit Rate**: {self.metrics.get('hit_rate', 0):.2%}\n")
            f.write(f"- **Avg Confidence**: {self.metrics.get('avg_confidence', 0):.2f}\n")
            f.write(f"- **Calibration Error**: {self.metrics.get('calibration_error', 0):.4f}\n")
            f.write(f"- **Brier Score**: {self.metrics.get('brier_score', 0):.4f}\n\n")

            f.write("## Trades by Symbol\n\n")
            for symbol, data in self.metrics.get('trades_by_symbol', {}).items():
                f.write(f"- **{symbol}**: {data['total']} trades, {data['hit_rate']:.2%} hit rate\n")

        logger.info(f"Calibration report saved to {report_path}")


def main():
    """Main entry point."""
    import argparse

    parser = argparse.ArgumentParser(description="Score calibration")
    parser.add_argument('--decisions', type=str, required=True,
                       help='Decisions file (JSONL or CSV)')
    parser.add_argument('--output-dir', type=str, required=True,
                       help='Output directory')

    args = parser.parse_args()

    print("=" * 80)
    print("CALIBRATION SCORER - Phase 3.0")
    print("=" * 80)
    print(f"Decisions file: {args.decisions}")
    print(f"Output directory: {args.output_dir}")
    print("=" * 80)
    print()

    try:
        scorer = CalibrationScorer(args.decisions, args.output_dir)
        scorer.load_decisions()

        # Fetch returns and compute outcomes
        returns_by_symbol = scorer.fetch_next_day_returns()
        scorer.compute_outcomes(returns_by_symbol)

        # Compute metrics
        scorer.compute_metrics()

        # Update learning state
        scorer.update_learning_state()

        # Save results
        scorer.save_metrics()
        scorer.generate_calibration_report()

        print()
        print("=" * 80)
        print("SCORING COMPLETE")
        print("=" * 80)
        print(f"Hit Rate: {scorer.metrics.get('hit_rate', 0):.2%}")
        print(f"Activity: {scorer.metrics.get('activity_rate', 0):.2%}")
        print(f"Output directory: {args.output_dir}")
        print("=" * 80)

        return 0

    except Exception as e:
        logger.error(f"Scoring failed: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
