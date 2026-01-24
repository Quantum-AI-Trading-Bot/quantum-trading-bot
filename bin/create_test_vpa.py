#!/usr/bin/env python3
"""
Manual Test VPA Generator
Creates VPA artifacts with specified actions for deterministic testing

Generated: 2026-01-20 17:27:00 UTC
Purpose: Enable manual testing of executor with specific BUY/SELL/HOLD signals
"""

import os
import sys
import json
import argparse
import logging
from datetime import datetime
from pathlib import Path

# Configuration
PLATFORM_ROOT = Path("/home/davidsanker/platform")
VPA_STORAGE = PLATFORM_ROOT / "vpa_storage"

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)
logger = logging.getLogger(__name__)


def create_test_vpa(
    symbol: str = "SPY",
    action: str = "BUY",
    confidence: float = 0.90,
    target_value_pct: float = 0.02,
    order_type: str = "MKT",
    limit_price: float = None,
    time_in_force: str = "DAY",
    reason: str = "Manual test signal",
    dry_run_exec: bool = False
) -> str:
    """
    Create a test VPA artifact with specified parameters

    Returns:
        Path to created VPA file
    """
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    vpa_filename = f"vpa_test_{action.lower()}_{symbol}_{timestamp}.json"
    vpa_path = VPA_STORAGE / vpa_filename

    # Build decision plan
    decision_plan = {
        "action": action.upper(),
        "symbol": symbol.upper(),
        "confidence": confidence,
        "order_type": order_type.upper(),
        "target_value_pct": target_value_pct,
        "quantity": None,
        "limit_price": limit_price,
        "time_in_force": time_in_force.upper(),
        "reason": reason
    }

    # Build full VPA
    vpa = {
        "timestamp": datetime.now().isoformat(),
        "track": "B",
        "mode": "true",
        "test_vpa": True,
        "predictions": {
            "symbols": [symbol.upper()],
            "confidence": confidence,
            "signal": action.upper()
        },
        "risk_metrics": {
            "portfolio_var": 0.15,
            "max_drawdown": 0.08
        },
        "decision_plan": decision_plan
    }

    # Write VPA file
    VPA_STORAGE.mkdir(parents=True, exist_ok=True)
    with open(vpa_path, 'w') as f:
        json.dump(vpa, f, indent=2)

    logger.info(f"Created test VPA: {vpa_path}")
    logger.info(f"  Decision: {action.upper()} {symbol.upper()}")
    logger.info(f"  Confidence: {confidence:.2%}")
    logger.info(f"  Target: {target_value_pct:.1%} of portfolio")

    # Optionally run executor in DRY_RUN
    if dry_run_exec:
        logger.info("\nRunning executor in DRY_RUN mode...")
        run_executor(vpa_path, dry_run=True)

    return str(vpa_path)


def run_executor(vpa_path: str, dry_run: bool = True):
    """Run VPA executor on the test VPA"""
    try:
        # Add platform bin to path
        sys.path.insert(0, str(PLATFORM_ROOT / 'bin'))

        from vpa_executor import VPAExecutor, load_config
        from pathlib import Path as PathlibPath

        # Load VPA
        with open(vpa_path, 'r') as f:
            vpa = json.load(f)

        # Load config
        config_file = PLATFORM_ROOT / "config" / "quantum_runtime.env"
        config = load_config(str(config_file))

        # Create executor
        executor = VPAExecutor(config)

        # Parse intents
        intents = executor.parse_decision_plan(vpa)

        if not intents:
            logger.info("  No actionable intents in VPA")
            return

        # Execute in DRY_RUN
        results = executor.execute_intents(intents, dry_run=dry_run)

        # Log results
        logger.info(f"\n  Execution Results:")
        for result in results:
            logger.info(f"    Intent: {result.intent.action} {result.intent.symbol}")
            logger.info(f"    Allowed: {result.guardrail_result.allowed}")
            logger.info(f"    Reason: {result.guardrail_result.reason}")
            if result.order_result:
                logger.info(f"    Status: {result.order_result.get('status')}")

    except Exception as e:
        logger.error(f"Error running executor: {e}")


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(
        description='Create manual test VPA for executor testing'
    )
    parser.add_argument('--symbol', type=str, default='SPY',
                       help='Trading symbol (default: SPY)')
    parser.add_argument('--action', type=str, choices=['BUY', 'SELL', 'HOLD'],
                       default='BUY', help='Trading action (default: BUY)')
    parser.add_argument('--confidence', type=float, default=0.90,
                       help='Confidence level 0-1 (default: 0.90)')
    parser.add_argument('--target-value-pct', type=float, default=0.02,
                       help='Target position as %% of portfolio (default: 0.02)')
    parser.add_argument('--order-type', type=str, choices=['MKT', 'LMT'],
                       default='MKT', help='Order type (default: MKT)')
    parser.add_argument('--limit-price', type=float,
                       help='Limit price (required for LMT orders)')
    parser.add_argument('--time-in-force', type=str, choices=['DAY', 'GTC'],
                       default='DAY', help='Time in force (default: DAY)')
    parser.add_argument('--reason', type=str,
                       default='Manual test signal for executor validation',
                       help='Reason for the trade')
    parser.add_argument('--dry-run-exec', action='store_true',
                       help='Run executor in DRY_RUN mode after creating VPA')

    args = parser.parse_args()

    # Validate limit price for LMT orders
    if args.order_type == 'LMT' and args.limit_price is None:
        logger.error("LMT orders require --limit-price")
        return 1

    # Create test VPA
    vpa_path = create_test_vpa(
        symbol=args.symbol,
        action=args.action,
        confidence=args.confidence,
        target_value_pct=args.target_value_pct,
        order_type=args.order_type,
        limit_price=args.limit_price,
        time_in_force=args.time_in_force,
        reason=args.reason,
        dry_run_exec=args.dry_run_exec
    )

    print(f"\n✓ Test VPA created: {vpa_path}")
    print(f"  Use this VPA to test the executor:")
    print(f"    python /home/davidsanker/platform/bin/test_vpa_execution.py")
    print(f"  Or to test this specific VPA:")
    print(f"    python /home/davidsanker/platform/bin/test_vpa_execution.py --vpa-file {vpa_path}")

    return 0


if __name__ == '__main__':
    sys.exit(main())
