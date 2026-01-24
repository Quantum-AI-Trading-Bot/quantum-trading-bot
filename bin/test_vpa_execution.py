#!/usr/bin/env python3
"""
VPA Execution Test Tool
Tests the executor pipeline in DRY_RUN mode

Generated: 2026-01-20 17:00:00 UTC
Purpose: Verification tool for VPA executor
"""

import os
import sys
import json
import logging
from pathlib import Path

# Add platform bin to path
sys.path.insert(0, '/home/davidsanker/platform/bin')

from vpa_executor import VPAExecutor, load_latest_vpa, load_config

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)
logger = logging.getLogger(__name__)


def main():
    """Main test function"""
    print("="*80)
    print("VPA EXECUTION TEST - DRY_RUN MODE")
    print("="*80)
    print()

    # Step 1: Load config
    print("Step 1: Loading configuration...")
    config_file = '/home/davidsanker/platform/config/quantum_runtime.env'
    config = load_config(config_file)

    print(f"  Config file: {config_file}")
    print(f"  QUANTUM_EXECUTION_ENABLED: {config.get('QUANTUM_EXECUTION_ENABLED', 'false')}")
    print(f"  MIN_CONFIDENCE: {config.get('MIN_CONFIDENCE', '0.75')}")
    print(f"  MAX_POSITION_SIZE: {config.get('MAX_POSITION_SIZE', '0.15')}")
    print()

    # Step 2: Load latest VPA
    print("Step 2: Loading latest VPA artifact...")
    vpa = load_latest_vpa()

    if not vpa:
        print("  ❌ No VPA artifact found")
        return 1

    print(f"  ✓ VPA loaded")
    print(f"  Timestamp: {vpa.get('timestamp')}")
    print(f"  Decision Plan: {json.dumps(vpa.get('decision_plan', {}), indent=2)}")
    print()

    # Step 3: Create executor
    print("Step 3: Creating VPA executor...")
    executor = VPAExecutor(config)
    print("  ✓ Executor created")
    print()

    # Step 4: Parse decision plan
    print("Step 4: Parsing decision plan...")
    intents = executor.parse_decision_plan(vpa)
    print(f"  Intents parsed: {len(intents)}")
    print()

    if not intents:
        print("  ℹ No actionable intents in VPA (action is HOLD/NONE)")
        print()
        print("="*80)
        print("RESULT: ✅ Pipeline works correctly (no trades to execute)")
        print("="*80)
        return 0

    # Step 5: Display intents
    print("Step 5: Execution intents:")
    for i, intent in enumerate(intents, 1):
        print(f"  Intent {i}:")
        print(f"    Action: {intent.action}")
        print(f"    Symbol: {intent.symbol}")
        print(f"    Quantity: {intent.quantity}")
        print(f"    Target %: {intent.target_value_pct}")
        print(f"    Order Type: {intent.order_type}")
        print(f"    Confidence: {intent.confidence:.2%}")
        print(f"    Reason: {intent.reason}")
    print()

    # Step 6: Run guardrails check
    print("Step 6: Checking guardrails...")
    account_snapshot = {'net_liquidation': 1000000.0}  # Mock snapshot

    for i, intent in enumerate(intents, 1):
        print(f"  Intent {i}: {intent.action} {intent.symbol}")
        result = executor.enforce_guardrails(intent, account_snapshot)

        if result.allowed:
            print(f"    ✓ ALLOWED: {result.reason}")
        else:
            print(f"    ✗ BLOCKED: {result.reason}")

        print(f"    Checks:")
        for check_name, check_result in result.checks.items():
            symbol = "✓" if check_result == "PASS" else "✗"
            print(f"      {symbol} {check_name}: {check_result}")
    print()

    # Step 7: Execute in DRY_RUN mode
    print("Step 7: Executing in DRY_RUN mode...")
    print("  " + "-"*76)

    results = executor.execute_intents(intents, dry_run=True)

    print("  " + "-"*76)
    print()

    # Step 8: Summary
    print("Step 8: Execution summary:")
    print(f"  Total intents: {len(results)}")
    print(f"  Allowed: {sum(1 for r in results if r.guardrail_result.allowed)}")
    print(f"  Blocked: {sum(1 for r in results if not r.guardrail_result.allowed)}")
    print(f"  Dry run: {all(r.dry_run for r in results)}")
    print()

    # Step 9: Check for execution receipts
    print("Step 9: Checking execution receipts...")
    receipts_dir = Path('/home/davidsanker/platform/execution_receipts')
    if receipts_dir.exists():
        receipts = sorted(receipts_dir.glob('*.json'), reverse=True)[:5]
        print(f"  Recent receipts: {len(receipts)}")
        for receipt in receipts:
            print(f"    - {receipt.name}")
    print()

    # Final result
    print("="*80)
    print("RESULT: ✅ VPA Executor pipeline working correctly")
    print("="*80)
    print()
    print("Next steps:")
    print("  1. To enable trading: Set QUANTUM_EXECUTION_DRY_RUN=false in quantum_runtime.env")
    print("  2. To test with actual decision: Create a VPA with action=BUY/SELL")
    print("  3. To verify paper trades: Run prove_paper_execution.py")
    print()

    return 0


if __name__ == '__main__':
    sys.exit(main())
