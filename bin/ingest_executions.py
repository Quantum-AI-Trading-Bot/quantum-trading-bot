#!/usr/bin/env python3
"""
Ingest Execution Receipts into Ledger

Purpose: Read execution receipts from execution_receipts/ directory and
         append to executions.jsonl in state/ledgers/ (idempotent)

Safety: READ-ONLY + append-only. No order placement.
         Idempotent: tracks seen receipts, skips duplicates.

Usage:
    python3 bin/ingest_executions.py --receipts-dir execution_receipts --out state/ledgers
    python3 bin/ingest_executions.py --recent-only  # Process only new receipts
"""

import os
import sys
import json
import uuid
import hashlib
import argparse
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any


# Paths
PLATFORM_ROOT = Path("/home/davidsanker/platform")
DEFAULT_RECEIPTS_DIR = PLATFORM_ROOT / "execution_receipts"
DEFAULT_LEDGERS_DIR = PLATFORM_ROOT / "state" / "ledgers"
INDEX_FILE = DEFAULT_LEDGERS_DIR / "ledger_index.json"


def load_index(ledgers_dir: Path) -> Dict[str, Any]:
    """Load ledger index (create if not exists)."""
    index_file = ledgers_dir / "ledger_index.json"
    if index_file.exists():
        with open(index_file, 'r') as f:
            return json.load(f)
    else:
        return {
            "last_update": None,
            "ledgers": {
                "decisions": {"path": str(ledgers_dir / "decisions.jsonl"), "count": 0},
                "executions": {"path": str(ledgers_dir / "executions.jsonl"), "count": 0},
                "trades": {"path": str(ledgers_dir / "trades.jsonl"), "count": 0},
                "outcomes": {"path": str(ledgers_dir / "outcomes.jsonl"), "count": 0}
            },
            "seen_receipts": {}
        }


def save_index(ledgers_dir: Path, index: Dict[str, Any]) -> None:
    """Save ledger index atomically."""
    index["last_update"] = datetime.utcnow().isoformat()
    index_file = ledgers_dir / "ledger_index.json"
    temp_file = index_file.with_suffix('.tmp')

    with open(temp_file, 'w') as f:
        json.dump(index, f, indent=2)

    temp_file.replace(index_file)


def get_receipt_id(receipt_path: Path) -> str:
    """Compute stable receipt ID from filename (without extension)."""
    return receipt_path.stem  # e.g., "20260120_201316_133379_SPY"


def find_vpa_id(receipt: Dict[str, Any], vpa_storage: Path) -> Optional[str]:
    """Try to find VPA ID from receipt timestamp or references."""
    # Check if VPA file exists for this timestamp
    timestamp = receipt.get("timestamp", "")
    if timestamp:
        # Parse timestamp and format as VPA filename
        try:
            dt = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
            vpa_filename = f"vpa_{dt.strftime('%Y%m%d_%H%M%S')}.json"
            vpa_path = vpa_storage / vpa_filename
            if vpa_path.exists():
                return vpa_filename
        except:
            pass

    return None


def receipt_to_execution(
    receipt: Dict[str, Any],
    receipt_id: str,
    vpa_id: Optional[str]
) -> Dict[str, Any]:
    """Convert receipt to execution record."""
    intent = receipt.get("intent", {})
    guardrail = receipt.get("guardrail_result", {})
    order_result = receipt.get("order_result", {})

    execution = {
        "execution_id": str(uuid.uuid4()),
        "receipt_id": receipt_id,
        "decision_id": None,  # Linkable if VPA contains decision_id
        "vpa_id": vpa_id,
        "timestamp": receipt.get("timestamp"),
        "symbol": intent.get("symbol"),
        "action": intent.get("action"),
        "quantity": intent.get("quantity"),
        "order_type": intent.get("order_type"),
        "status": order_result.get("status", "UNKNOWN"),
        "order_id": order_result.get("order_id"),
        "client_id": order_result.get("client_id"),
        "dry_run": receipt.get("dry_run", True),
        "blocked_reason": guardrail.get("reason") if not guardrail.get("allowed", True) else None,
        "guardrail_checks": guardrail.get("checks", {})
    }

    return execution


def append_execution(ledger_path: Path, execution: Dict[str, Any]) -> None:
    """Append execution record to ledger (append-only)."""
    with open(ledger_path, 'a') as f:
        f.write(json.dumps(execution) + '\n')


def ingest_receipts(
    receipts_dir: Path,
    ledgers_dir: Path,
    recent_only: bool = False,
    dry_run: bool = False
) -> Dict[str, int]:
    """
    Ingest execution receipts into ledger.

    Returns:
        Dict with counts: ingested, skipped, errors
    """
    vpa_storage = PLATFORM_ROOT / "vpa_storage"

    # Load index
    index = load_index(ledgers_dir)
    seen_receipts = index.get("seen_receipts", {})

    # Find receipt files
    if not receipts_dir.exists():
        print(f"⚠ Receipts directory not found: {receipts_dir}")
        return {"ingested": 0, "skipped": 0, "errors": 0}

    receipt_files = sorted(receipts_dir.glob("*.json"), reverse=True)  # Newest first

    if recent_only:
        # Only process receipts newer than last index update
        last_update = index.get("last_update")
        if last_update:
            last_update_dt = datetime.fromisoformat(last_update)
            # Filter: only files modified after last update
            receipt_files = [f for f in receipt_files if datetime.fromtimestamp(f.stat().st_mtime) > last_update_dt]

    # Initialize ledger path
    executions_ledger = ledgers_dir / "executions.jsonl"
    executions_ledger.parent.mkdir(parents=True, exist_ok=True)

    if not executions_ledger.exists():
        executions_ledger.touch()

    # Stats
    stats = {"ingested": 0, "skipped": 0, "errors": 0}

    print(f"📂 Scanning {len(receipt_files)} receipt files...")

    for receipt_file in receipt_files:
        receipt_id = get_receipt_id(receipt_file)

        # Check if already processed (idempotency)
        if receipt_id in seen_receipts:
            stats["skipped"] += 1
            continue

        try:
            # Load receipt
            with open(receipt_file, 'r') as f:
                receipt = json.load(f)

            # Find VPA ID
            vpa_id = find_vpa_id(receipt, vpa_storage)

            # Convert to execution record
            execution = receipt_to_execution(receipt, receipt_id, vpa_id)

            # Append to ledger
            if not dry_run:
                append_execution(executions_ledger, execution)

            # Mark as seen
            seen_receipts[receipt_id] = True
            stats["ingested"] += 1

            print(f"  ✓ Ingested: {receipt_id} ({execution['status']})")

        except json.JSONDecodeError as e:
            print(f"  ✗ JSON error in {receipt_file}: {e}")
            stats["errors"] += 1
        except Exception as e:
            print(f"  ✗ Error processing {receipt_file}: {e}")
            stats["errors"] += 1

    # Update index
    if not dry_run and stats["ingested"] > 0:
        # Update counts
        index["ledgers"]["executions"]["count"] = sum(1 for _ in open(executions_ledger))
        index["ledgers"]["executions"]["last_record_time"] = datetime.utcnow().isoformat()

        save_index(ledgers_dir, index)

    return stats


def main():
    parser = argparse.ArgumentParser(
        description='Ingest execution receipts into ledger',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Ingest all receipts
  python3 bin/ingest_executions.py --receipts-dir execution_receipts --out state/ledgers

  # Ingest only new receipts (since last run)
  python3 bin/ingest_executions.py --recent-only

  # Dry run (show what would be ingested)
  python3 bin/ingest_executions.py --dry-run
        """
    )

    parser.add_argument(
        '--receipts-dir',
        type=str,
        default=str(DEFAULT_RECEIPTS_DIR),
        help='Execution receipts directory (default: execution_receipts/)'
    )
    parser.add_argument(
        '--out',
        type=str,
        default=str(DEFAULT_LEDGERS_DIR),
        help='Output ledgers directory (default: state/ledgers/)'
    )
    parser.add_argument(
        '--recent-only',
        action='store_true',
        help='Only process receipts newer than last index update'
    )
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Show what would be ingested without writing'
    )
    parser.add_argument(
        '--quiet',
        action='store_true',
        help='Suppress output except errors'
    )

    args = parser.parse_args()

    receipts_dir = Path(args.receipts_dir)
    ledgers_dir = Path(args.out)

    quiet = args.quiet
    if not quiet:
        print(f"🔄 Ingesting execution receipts...")
        print(f"   From: {receipts_dir}")
        print(f"   To: {ledgers_dir / 'executions.jsonl'}")
        print(f"   Mode: {'DRY RUN' if args.dry_run else 'LIVE'}")
        if args.recent_only:
            print(f"   Filter: recent-only")
        print("")

    # Ingest
    stats = ingest_receipts(
        receipts_dir=receipts_dir,
        ledgers_dir=ledgers_dir,
        recent_only=args.recent_only,
        dry_run=args.dry_run
    )

    # Summary
    if not args.quiet:
        print("")
        print(f"📊 Ingestion Summary:")
        print(f"   Ingested: {stats['ingested']}")
        print(f"   Skipped:  {stats['skipped']} (already processed)")
        print(f"   Errors:   {stats['errors']}")
        print("")

        if stats['ingested'] > 0:
            print(f"✅ Successfully ingested {stats['ingested']} receipt(s)")
        elif stats['skipped'] > 0:
            print(f"ℹ No new receipts to ingest (all {stats['skipped']} already processed)")

    # Exit code
    sys.exit(0 if stats['errors'] == 0 else 1)


if __name__ == "__main__":
    main()
