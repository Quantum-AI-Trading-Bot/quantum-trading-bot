#!/usr/bin/env python3
"""
Learning Update - Update Learner State from Outcomes

Purpose: Update signal weights and calibration bins from new outcomes
         using multiplicative weights algorithm

Safety: READ-ONLY outcomes, updates learner_state.json atomically
         Creates backup before each update

Usage:
    python3 bin/run_learning_update.py --ledgers state/ledgers --state state/learner_state.json
    python3 bin/run_learning_update.py --shadow  # Update shadow weights
"""

import os
import sys
import json
import uuid
import argparse
import shutil
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any
from collections import defaultdict


# Paths
PLATFORM_ROOT = Path("/home/davidsanker/platform")
DEFAULT_LEDGERS_DIR = PLATFORM_ROOT / "state" / "ledgers"
DEFAULT_STATE_FILE = PLATFORM_ROOT / "state" / "learner_state.json"


def load_state(state_file: Path) -> Dict[str, Any]:
    """Load learner state (create default if not exists)."""
    if state_file.exists():
        with open(state_file, 'r') as f:
            return json.load(f)
    else:
        return create_default_state()


def create_default_state() -> Dict[str, Any]:
    """Create default learner state."""
    return {
        "version": "1.0",
        "last_update": None,
        "signal_weights": {
            "momentum": 0.25,
            "mean_reversion": 0.25,
            "breakout": 0.25,
            "sentiment": 0.25
        },
        "confidence_calibration": {
            "bins": [
                {"min_conf": 0.50, "max_conf": 0.60, "count": 0, "wins": 0},
                {"min_conf": 0.60, "max_conf": 0.70, "count": 0, "wins": 0},
                {"min_conf": 0.70, "max_conf": 0.80, "count": 0, "wins": 0},
                {"min_conf": 0.80, "max_conf": 0.90, "count": 0, "wins": 0},
                {"min_conf": 0.90, "max_conf": 1.00, "count": 0, "wins": 0}
            ]
        },
        "model_performance": {},
        "learning_stats": {
            "total_trades": 0,
            "last_trade_time": None,
            "consecutive_wins": 0,
            "consecutive_losses": 0,
            "max_drawdown": 0.0,
            "sharpe_ratio": 0.0
        },
        "shadow_mode": {
            "enabled": False,
            "last_shadow_update": None,
            "shadow_samples": 0
        }
    }


def backup_state(state_file: Path) -> Path:
    """Create backup of learner state."""
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    backup_file = state_file.parent / f"learner_state.bak_{timestamp}"
    shutil.copy2(state_file, backup_file)
    return backup_file


def load_outcomes(
    outcomes_file: Path,
    since_timestamp: Optional[str] = None
) -> List[Dict[str, Any]]:
    """Load outcomes since last update."""
    if not outcomes_file.exists():
        return []

    outcomes = []
    with open(outcomes_file, 'r') as f:
        for line in f:
            try:
                outcome = json.loads(line)
                outcomes.append(outcome)
            except json.JSONDecodeError:
                continue

    # Filter by timestamp if provided
    if since_timestamp:
        since_dt = datetime.fromisoformat(since_timestamp)
        # Normalize to offset-naive for comparison (some timestamps have tz, some don't)
        if since_dt.tzinfo is not None:
            since_dt = since_dt.replace(tzinfo=None)
        filtered = []
        for o in outcomes:
            raw_ts = o.get('label_time', o.get('timestamp', ''))
            try:
                o_dt = datetime.fromisoformat(raw_ts)
                if o_dt.tzinfo is not None:
                    o_dt = o_dt.replace(tzinfo=None)
                if o_dt > since_dt:
                    filtered.append(o)
            except (ValueError, TypeError):
                continue
        outcomes = filtered

    return outcomes


def update_signal_weights(state: Dict[str, Any], outcomes: List[Dict[str, Any]]) -> None:
    """
    Update signal weights using multiplicative weights algorithm.

    Simple implementation: Adjust weights based on win rate
    """
    weights = state["signal_weights"]

    # Group outcomes by model/signal (simplified)
    # In reality, you'd track which signal produced each decision
    signal_wins = defaultdict(int)
    signal_counts = defaultdict(int)

    for outcome in outcomes:
        # Simplified: assume all signals contribute equally
        # In production, track per-signal outcomes
        for signal in weights.keys():
            signal_counts[signal] += 1
            if outcome.get("win", False):
                signal_wins[signal] += 1

    # Update weights using multiplicative weights
    learning_rate = 0.1  # Conservative learning rate

    new_weights = {}
    total_weight = 0.0

    for signal, weight in weights.items():
        wins = signal_wins[signal]
        count = signal_counts[signal]

        if count > 0:
            win_rate = wins / count
            # Multiplicative update
            multiplier = 1.0 + learning_rate * (win_rate - 0.5)
            new_weights[signal] = weight * multiplier
        else:
            new_weights[signal] = weight

        total_weight += new_weights[signal]

    # Normalize weights
    if total_weight > 0:
        for signal in new_weights:
            new_weights[signal] /= total_weight

    state["signal_weights"] = new_weights


def update_calibration(state: Dict[str, Any], outcomes: List[Dict[str, Any]]) -> None:
    """Update confidence calibration bins."""
    # Handle both old and new state structures
    if "confidence_calibration" not in state:
        state["confidence_calibration"] = {
            "bins": [
                {"min_conf": 0.50, "max_conf": 0.60, "count": 0, "wins": 0},
                {"min_conf": 0.60, "max_conf": 0.70, "count": 0, "wins": 0},
                {"min_conf": 0.70, "max_conf": 0.80, "count": 0, "wins": 0},
                {"min_conf": 0.80, "max_conf": 0.90, "count": 0, "wins": 0},
                {"min_conf": 0.90, "max_conf": 1.00, "count": 0, "wins": 0}
            ]
        }

    bins = state["confidence_calibration"]["bins"]

    for outcome in outcomes:
        confidence = outcome.get("confidence", 0.5)
        win = outcome.get("win", False)

        # Find matching bin
        for bin_data in bins:
            if bin_data["min_conf"] <= confidence < bin_data["max_conf"]:
                bin_data["count"] += 1
                if win:
                    bin_data["wins"] += 1
                break


def update_stats(state: Dict[str, Any], outcomes: List[Dict[str, Any]]) -> None:
    """Update learning statistics."""
    # Handle both old and new state structures
    if "learning_stats" not in state:
        state["learning_stats"] = {
            "total_trades": 0,
            "last_trade_time": None,
            "consecutive_wins": 0,
            "consecutive_losses": 0,
            "max_drawdown": 0.0,
            "sharpe_ratio": 0.0
        }

    stats = state["learning_stats"]

    if not outcomes:
        return

    # Update total count
    stats["total_trades"] += len(outcomes)

    # Update last trade time
    last_outcome = max(outcomes, key=lambda o: o.get('label_time', ''))
    stats["last_trade_time"] = last_outcome.get('label_time')

    # Calculate consecutive wins/losses
    recent = sorted(outcomes, key=lambda o: o.get('label_time', ''))
    consecutive_wins = 0
    consecutive_losses = 0

    for outcome in recent:
        if outcome.get("win", False):
            consecutive_wins += 1
            consecutive_losses = 0
        else:
            consecutive_wins = 0
            consecutive_losses += 1

    stats["consecutive_wins"] = consecutive_wins
    stats["consecutive_losses"] = consecutive_losses

    # Calculate Sharpe ratio (simplified)
    if len(outcomes) > 1:
        returns = [o.get("pnl_pct", 0) for o in outcomes]
        avg_return = sum(returns) / len(returns)

        if len(returns) > 1:
            variance = sum((r - avg_return) ** 2 for r in returns) / (len(returns) - 1)
            std_dev = variance ** 0.5

            if std_dev > 0:
                # Annualized Sharpe (assuming 5-min bars, ~79 bars/day)
                stats["sharpe_ratio"] = (avg_return / std_dev) * (79 ** 0.5)


def run_learning_update(
    ledgers_dir: Path,
    state_file: Path,
    shadow: bool = False,
    dry_run: bool = False
) -> Dict[str, Any]:
    """
    Run learning update from outcomes.

    Returns:
        Summary dict with counts and updates
    """
    # Load current state
    state = load_state(state_file)
    last_update = state.get("last_update")

    # Determine which outcomes to process
    if shadow:
        outcomes_file = ledgers_dir / "shadow_outcomes.jsonl"
    else:
        outcomes_file = ledgers_dir / "outcomes.jsonl"

    # Load outcomes
    outcomes = load_outcomes(outcomes_file, last_update)

    if not outcomes:
        return {"processed": 0, "message": "No new outcomes to process"}

    # Backup state
    if not dry_run:
        backup_state(state_file)

    # Update state
    update_signal_weights(state, outcomes)
    update_calibration(state, outcomes)
    update_stats(state, outcomes)

    # Update shadow stats if applicable
    if shadow:
        state["shadow_mode"]["enabled"] = True
        state["shadow_mode"]["last_shadow_update"] = datetime.utcnow().isoformat()
        state["shadow_mode"]["shadow_samples"] += len(outcomes)

    # Update timestamp
    state["last_update"] = datetime.utcnow().isoformat()

    # Save state
    if not dry_run:
        temp_file = state_file.with_suffix('.tmp')
        with open(temp_file, 'w') as f:
            json.dump(state, f, indent=2)
        temp_file.replace(state_file)

    # Create summary
    summary = {
        "processed": len(outcomes),
        "signal_weights": state["signal_weights"],
        "calibration_bins": state["confidence_calibration"]["bins"],
        "learning_stats": state["learning_stats"]
    }

    return summary


def main():
    parser = argparse.ArgumentParser(
        description='Update learner state from outcomes',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Update from live outcomes
  python3 bin/run_learning_update.py --ledgers state/ledgers --state state/learner_state.json

  # Update from shadow outcomes
  python3 bin/run_learning_update.py --shadow

  # Dry run (show what would update)
  python3 bin/run_learning_update.py --dry-run
        """
    )

    parser.add_argument(
        '--ledgers',
        type=str,
        default=str(DEFAULT_LEDGERS_DIR),
        help='Ledgers directory (default: state/ledgers/)'
    )
    parser.add_argument(
        '--state',
        type=str,
        default=str(DEFAULT_STATE_FILE),
        help='Learner state file (default: state/learner_state.json)'
    )
    parser.add_argument(
        '--shadow',
        action='store_true',
        help='Update from shadow outcomes instead of live'
    )
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Show what would update without writing'
    )
    parser.add_argument(
        '--quiet',
        action='store_true',
        help='Suppress output except errors'
    )

    args = parser.parse_args()

    ledgers_dir = Path(args.ledgers)
    state_file = Path(args.state)

    if not args.quiet:
        print(f"🧠 Running Learning Update...")
        print(f"   Ledgers: {ledgers_dir}")
        print(f"   State: {state_file}")
        print(f"   Mode: {'SHADOW' if args.shadow else 'LIVE'}")
        print(f"   Dry Run: {args.dry_run}")
        print("")

    # Run update
    summary = run_learning_update(
        ledgers_dir=ledgers_dir,
        state_file=state_file,
        shadow=args.shadow,
        dry_run=args.dry_run
    )

    # Summary
    if not args.quiet:
        print("")
        print(f"📊 Learning Update Summary:")
        print(f"   Processed: {summary['processed']} outcome(s)")

        if summary['processed'] > 0:
            print("")
            print("   Signal Weights:")
            for signal, weight in summary.get('signal_weights', {}).items():
                print(f"     {signal}: {weight:.4f}")

            print("")
            stats = summary.get('learning_stats', {})
            print(f"   Total Trades: {stats.get('total_trades', 0)}")
            print(f"   Consecutive Wins: {stats.get('consecutive_wins', 0)}")
            print(f"   Consecutive Losses: {stats.get('consecutive_losses', 0)}")
            print(f"   Sharpe Ratio: {stats.get('sharpe_ratio', 0):.4f}")
            print("")

            print("✅ Learning state updated")

    sys.exit(0)


if __name__ == "__main__":
    main()
