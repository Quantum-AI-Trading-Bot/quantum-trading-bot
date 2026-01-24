#!/usr/bin/env python3
"""
Shadow Learning - Label Decisions with Next-Bar Returns

Purpose: Label historical decisions with next-bar returns using yfinance
         for shadow learning (no real trades needed)

Safety: READ-ONLY historical price fetching. No order placement.

Usage:
    python3 bin/shadow_label_decisions.py --input state/decisions.jsonl --output state/ledgers/shadow_outcomes.jsonl
    python3 bin/shadow_label_decisions.py --recent 30 --output state/ledgers/shadow_outcomes.jsonl
"""

import os
import sys
import json
import uuid
import argparse
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Any

try:
    import yfinance as yf
except ImportError:
    print("⚠ yfinance not installed. Install with: pip install yfinance")
    sys.exit(1)


# Paths
PLATFORM_ROOT = Path("/home/davidsanker/platform")
DEFAULT_DECISIONS_FILE = PLATFORM_ROOT / "state" / "decisions.jsonl"
DEFAULT_OUTPUT_FILE = PLATFORM_ROOT / "state" / "ledgers" / "shadow_outcomes.jsonl"


def fetch_next_bar_return(symbol: str, timestamp: str, bar_minutes: int = 5) -> Optional[float]:
    """
    Fetch next-bar return for a symbol after a given timestamp.

    Args:
        symbol: Stock symbol (e.g., "SPY")
        timestamp: Decision timestamp (ISO-8601)
        bar_minutes: Bar size in minutes (default: 5)

    Returns:
        Next-bar return as percentage (e.g., 0.012 for 1.2%)
    """
    try:
        dt = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))

        # Fetch historical data (with buffer)
        start_date = (dt - timedelta(days=7)).strftime('%Y-%m-%d')
        end_date = (dt + timedelta(days=1)).strftime('%Y-%m-%d')

        # Use 5m interval for intraday
        ticker = yf.Ticker(symbol)
        hist = ticker.history(start=start_date, end=end_date, interval='5m')

        if hist.empty:
            return None

        # Find the first bar AFTER the decision timestamp
        for i, (time_idx, row) in enumerate(hist.iterrows()):
            if time_idx.to_pydatetime() > dt:
                # Found next bar
                open_price = row['Open']
                close_price = row['Close']

                # Calculate return
                if open_price and close_price and open_price > 0:
                    return (close_price - open_price) / open_price

        return None

    except Exception as e:
        print(f"  ✗ Error fetching {symbol} at {timestamp}: {e}")
        return None


def label_decision(decision: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """
    Label a decision with next-bar return.

    Returns:
        Shadow outcome record or None if labeling failed
    """
    symbol = decision.get("symbol")
    timestamp = decision.get("timestamp")
    action = decision.get("action")
    confidence = decision.get("confidence", 0.5)

    if not symbol or not timestamp:
        return None

    if action not in ["BUY", "SELL"]:
        return None  # Only label actionable decisions

    # Fetch next-bar return
    next_return = fetch_next_bar_return(symbol, timestamp)

    if next_return is None:
        return None

    # Determine if decision was correct
    if action == "BUY":
        correct_direction = next_return > 0
        pnl_pct = next_return
    else:  # SELL
        correct_direction = next_return < 0
        pnl_pct = -next_return

    # Create shadow outcome
    outcome = {
        "outcome_id": str(uuid.uuid4()),
        "decision_id": decision.get("timestamp"),  # Use timestamp as ID
        "symbol": symbol,
        "decision_time": timestamp,
        "action": action,
        "confidence": confidence,
        "next_return": next_return,
        "pnl_pct": pnl_pct,
        "win": pnl_pct > 0,
        "correct_direction": correct_direction,
        "shadow": True,
        "label_time": datetime.utcnow().isoformat()
    }

    return outcome


def shadow_label_decisions(
    decisions_file: Path,
    output_file: Path,
    recent: Optional[int] = None,
    dry_run: bool = False
) -> Dict[str, int]:
    """
    Label decisions with shadow outcomes.

    Args:
        decisions_file: Input decisions.jsonl
        output_file: Output shadow_outcomes.jsonl
        recent: Only process N most recent decisions
        dry_run: Show what would be labeled without writing

    Returns:
        Dict with counts: labeled, skipped, errors
    """
    stats = {"labeled": 0, "skipped": 0, "errors": 0}

    if not decisions_file.exists():
        print(f"⚠ Decisions file not found: {decisions_file}")
        return stats

    # Read decisions
    decisions = []
    with open(decisions_file, 'r') as f:
        for line in f:
            try:
                decision = json.loads(line)
                decisions.append(decision)
            except json.JSONDecodeError:
                stats["errors"] += 1

    # Filter to recent N decisions if requested
    if recent:
        decisions = decisions[-recent:]

    print(f"📂 Labeling {len(decisions)} decision(s)...")

    # Create output directory
    output_file.parent.mkdir(parents=True, exist_ok=True)

    # Label each decision
    outcomes = []
    for decision in decisions:
        outcome = label_decision(decision)

        if outcome:
            outcomes.append(outcome)
            stats["labeled"] += 1
            print(f"  ✓ Labeled: {decision.get('symbol')} {decision.get('action')} → {outcome['pnl_pct']:.4f}")
        else:
            stats["skipped"] += 1

    # Write to file
    if not dry_run and outcomes:
        with open(output_file, 'a') as f:
            for outcome in outcomes:
                f.write(json.dumps(outcome) + '\n')

    return stats


def main():
    parser = argparse.ArgumentParser(
        description='Label decisions with next-bar returns (shadow learning)',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Label all decisions
  python3 bin/shadow_label_decisions.py --input state/decisions.jsonl --output state/ledgers/shadow_outcomes.jsonl

  # Label only 30 most recent decisions
  python3 bin/shadow_label_decisions.py --recent 30

  # Dry run (show what would be labeled)
  python3 bin/shadow_label_decisions.py --dry-run
        """
    )

    parser.add_argument(
        '--input',
        type=str,
        default=str(DEFAULT_DECISIONS_FILE),
        help='Input decisions file (default: state/decisions.jsonl)'
    )
    parser.add_argument(
        '--output',
        type=str,
        default=str(DEFAULT_OUTPUT_FILE),
        help='Output shadow outcomes file (default: state/ledgers/shadow_outcomes.jsonl)'
    )
    parser.add_argument(
        '--recent',
        type=int,
        help='Only label N most recent decisions'
    )
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Show what would be labeled without writing'
    )
    parser.add_argument(
        '--quiet',
        action='store_true',
        help='Suppress output except errors'
    )

    args = parser.parse_args()

    decisions_file = Path(args.input)
    output_file = Path(args.output)

    if not args.quiet:
        print(f"🏷️ Shadow Labeling Decisions...")
        print(f"   From: {decisions_file}")
        print(f"   To: {output_file}")
        print(f"   Mode: {'DRY RUN' if args.dry_run else 'LIVE'}")
        if args.recent:
            print(f"   Filter: recent {args.recent}")
        print("")

    # Label
    stats = shadow_label_decisions(
        decisions_file=decisions_file,
        output_file=output_file,
        recent=args.recent,
        dry_run=args.dry_run
    )

    # Summary
    if not args.quiet:
        print("")
        print(f"📊 Shadow Labeling Summary:")
        print(f"   Labeled:  {stats['labeled']}")
        print(f"   Skipped:  {stats['skipped']}")
        print(f"   Errors:   {stats['errors']}")
        print("")

        if stats['labeled'] > 0:
            print(f"✅ Successfully labeled {stats['labeled']} decision(s)")
        elif stats['skipped'] > 0:
            print(f"ℹ No decisions labeled (all {stats['skipped']} skipped)")

    sys.exit(0 if stats['errors'] == 0 else 1)


if __name__ == "__main__":
    main()
