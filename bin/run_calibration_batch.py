#!/usr/bin/env python3
"""
Calibration Batch Runner - Phase 3.0

Runs multiple decision cycles in DRY_RUN mode for calibration data collection.
Collects decisions, computes outcomes, and updates learning state.

SAFETY: All runs in DRY_RUN mode, no orders placed.
"""

import sys
import os
import json
import csv
import time
import logging
import argparse
import subprocess
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Any

import yaml

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class CalibrationBatchRunner:
    """Runner for calibration data collection."""

    def __init__(self, symbols: List[str], cycles_per_symbol: int,
                 sleep_seconds: int, output_dir: str):
        """Initialize runner."""
        self.symbols = symbols
        self.cycles_per_symbol = cycles_per_symbol
        self.sleep_seconds = sleep_seconds
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

        self.decisions = []
        self.errors = []

        logger.info(f"Calibration runner initialized:")
        logger.info(f"  Symbols: {symbols}")
        logger.info(f"  Cycles per symbol: {cycles_per_symbol}")
        logger.info(f"  Total cycles: {len(symbols) * cycles_per_symbol}")
        logger.info(f"  Output dir: {output_dir}")

    def get_newest_vpa(self) -> Dict[str, Any]:
        """Get the newest VPA artifact."""
        vpa_dir = Path("/home/davidsanker/platform/vpa_storage")
        vpa_files = list(vpa_dir.glob("*.json"))

        if not vpa_files:
            return None

        newest = max(vpa_files, key=lambda p: p.stat().st_mtime)

        try:
            with open(newest, 'r') as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Error reading VPA {newest}: {e}")
            return None

    def run_one_cycle(self, symbol: str) -> Dict[str, Any]:
        """Run one decision cycle."""
        try:
            # Run the cycle
            result = subprocess.run(
                ["python3", "bin/run_one_cycle.py", "--symbol", symbol],
                capture_output=True,
                text=True,
                timeout=30,
                cwd="/home/davidsanker/platform"
            )

            if result.returncode != 0:
                logger.error(f"Cycle failed for {symbol}: {result.stderr}")
                return None

            # Get the newest VPA
            vpa = self.get_newest_vpa()
            if not vpa:
                logger.error(f"No VPA found for {symbol}")
                return None

            # Extract decision info
            decision = vpa.get('decision_plan', {})
            model_meta = decision.get('model_metadata', {})
            learning_meta = decision.get('learning_metadata', {})

            # Extract features summary
            reasons = decision.get('reasons', [])

            return {
                'timestamp': datetime.utcnow().isoformat(),
                'symbol': symbol,
                'action': decision.get('action', 'HOLD'),
                'confidence': decision.get('confidence', 0.5),
                'target_value_pct': decision.get('target_value_pct', 0.0),
                'order_type': decision.get('order_type', 'MKT'),
                'decision_id': decision.get('decision_id', ''),
                'reasons': reasons,
                'forecast_model': model_meta.get('forecast_model', ''),
                'signal_model': model_meta.get('signal_model', ''),
                'allocation_model': model_meta.get('allocation_model', ''),
                'execution_policy': model_meta.get('execution_policy', ''),
                'model_versions': model_meta.get('model_versions', {}),
                'dry_run': model_meta.get('dry_run', True),
                'signal_components': learning_meta.get('signal_components', {}),
                'weights_used': learning_meta.get('weights_used', {}),
                'vpa_filename': Path(vpa.get('path', '')).name if 'path' in vpa else ''
            }

        except Exception as e:
            logger.error(f"Error running cycle for {symbol}: {e}")
            self.errors.append({
                'symbol': symbol,
                'error': str(e),
                'timestamp': datetime.utcnow().isoformat()
            })
            return None

    def run_batch(self):
        """Run the full batch of cycles."""
        total_cycles = len(self.symbols) * self.cycles_per_symbol
        completed = 0

        logger.info(f"Starting batch run: {total_cycles} cycles")

        for cycle_num in range(1, self.cycles_per_symbol + 1):
            for symbol in self.symbols:
                completed += 1
                logger.info(f"[{completed}/{total_cycles}] Running cycle {cycle_num} for {symbol}...")

                decision = self.run_one_cycle(symbol)

                if decision:
                    self.decisions.append(decision)
                    logger.info(f"  → {decision['action']} {symbol} (conf: {decision['confidence']:.2f})")
                else:
                    logger.warning(f"  → FAILED for {symbol}")

                # Sleep between cycles
                if completed < total_cycles:
                    time.sleep(self.sleep_seconds)

        logger.info(f"Batch complete: {len(self.decisions)} decisions collected")

        if self.errors:
            logger.warning(f"Errors encountered: {len(self.errors)}")

    def save_results(self):
        """Save results to files."""
        # Save JSONL
        jsonl_path = self.output_dir / "03_decisions.jsonl"
        with open(jsonl_path, 'w') as f:
            for decision in self.decisions:
                f.write(json.dumps(decision) + '\n')
        logger.info(f"Saved {len(self.decisions)} decisions to {jsonl_path}")

        # Save CSV
        csv_path = self.output_dir / "04_decisions.csv"
        if self.decisions:
            fieldnames = list(self.decisions[0].keys())
            with open(csv_path, 'w', newline='') as f:
                writer = csv.DictWriter(f, fieldnames=fieldnames)
                writer.writeheader()
                writer.writerows(self.decisions)
            logger.info(f"Saved CSV to {csv_path}")

        # Save errors if any
        if self.errors:
            errors_path = self.output_dir / "errors.json"
            with open(errors_path, 'w') as f:
                json.dump(self.errors, f, indent=2)
            logger.info(f"Saved {len(self.errors)} errors to {errors_path}")


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Run calibration batch")
    parser.add_argument('--symbols', nargs='+', default=['SPY', 'AAPL', 'MSFT'],
                       help='Symbols to run')
    parser.add_argument('--cycles-per-symbol', type=int, default=10,
                       help='Cycles per symbol (default: 10)')
    parser.add_argument('--sleep-seconds', type=int, default=5,
                       help='Sleep between cycles (default: 5)')
    parser.add_argument('--output-dir', type=str, required=True,
                       help='Output directory')

    args = parser.parse_args()

    # Print banner
    print("=" * 80)
    print("CALIBRATION BATCH RUNNER - Phase 3.0")
    print("=" * 80)
    print(f"Symbols: {args.symbols}")
    print(f"Cycles per symbol: {args.cycles_per_symbol}")
    print(f"Total cycles: {len(args.symbols) * args.cycles_per_symbol}")
    print(f"Output dir: {args.output_dir}")
    print(f"Mode: DRY_RUN (safe, no trading)")
    print("=" * 80)
    print()

    try:
        runner = CalibrationBatchRunner(
            symbols=args.symbols,
            cycles_per_symbol=args.cycles_per_symbol,
            sleep_seconds=args.sleep_seconds,
            output_dir=args.output_dir
        )

        runner.run_batch()
        runner.save_results()

        print()
        print("=" * 80)
        print("BATCH RUN COMPLETE")
        print("=" * 80)
        print(f"Decisions collected: {len(runner.decisions)}")
        print(f"Errors: {len(runner.errors)}")
        print(f"Output directory: {args.output_dir}")
        print("=" * 80)

        return 0

    except Exception as e:
        logger.error(f"Batch run failed: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
