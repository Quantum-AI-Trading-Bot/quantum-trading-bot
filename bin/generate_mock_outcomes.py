#!/usr/bin/env python3
"""
Generate Mock Outcomes for Learning Demo

Purpose: Generate synthetic outcomes for testing learning update
         when yfinance is not available

Usage:
    python3 bin/generate_mock_outcomes.py --count 30 --output state/ledgers/mock_outcomes.jsonl
"""

import json
import uuid
import argparse
from datetime import datetime, timedelta
from pathlib import Path
import random


def generate_mock_outcomes(count: int, output_file: Path) -> None:
    """Generate mock outcomes for learning demo."""
    output_file.parent.mkdir(parents=True, exist_ok=True)

    outcomes = []
    base_time = datetime.utcnow() - timedelta(days=7)

    for i in range(count):
        # Generate random outcome
        win = random.random() > 0.45  # 55% win rate (slightly profitable)
        pnl_pct = random.uniform(-0.02, 0.03) if win else random.uniform(-0.015, 0.005)
        confidence = random.uniform(0.60, 0.95)

        outcome = {
            "outcome_id": str(uuid.uuid4()),
            "decision_id": f"decision_{i}",
            "symbol": random.choice(["SPY", "QQQ", "AAPL", "MSFT", "NVDA"]),
            "decision_time": (base_time + timedelta(hours=i)).isoformat(),
            "action": random.choice(["BUY", "SELL"]),
            "confidence": round(confidence, 2),
            "pnl_pct": round(pnl_pct, 4),
            "win": pnl_pct > 0,
            "shadow": False,
            "label_time": (base_time + timedelta(hours=i)).isoformat()
        }

        outcomes.append(outcome)

    # Write to file
    with open(output_file, 'w') as f:
        for outcome in outcomes:
            f.write(json.dumps(outcome) + '\n')

    print(f"✅ Generated {count} mock outcomes → {output_file}")


def main():
    parser = argparse.ArgumentParser(description='Generate mock outcomes for learning demo')
    parser.add_argument('--count', type=int, default=30, help='Number of mock outcomes')
    parser.add_argument('--output', type=str, default='state/ledgers/mock_outcomes.jsonl')

    args = parser.parse_args()

    generate_mock_outcomes(args.count, Path(args.output))


if __name__ == "__main__":
    main()
