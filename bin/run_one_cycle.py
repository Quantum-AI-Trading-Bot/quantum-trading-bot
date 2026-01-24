#!/usr/bin/env python3
"""
Run One Cycle - Execute a single decision cycle in DRY_RUN mode.

Useful for:
- Testing model configuration
- Generating VPA artifacts
- Debugging model pipeline
- Smoke testing
"""

import sys
import os
from pathlib import Path
from datetime import datetime

# Add platform to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from engine.model_orchestrator import ModelOrchestrator


def print_header(title: str):
    print("\n" + "=" * 80)
    print(f"  {title}")
    print("=" * 80 + "\n")


def run_one_cycle(symbol: str = 'SPY', dry_run: bool = True):
    """
    Run a single decision cycle.

    Args:
        symbol: Symbol to analyze (default: SPY)
        dry_run: If True, don't execute orders (default: True)
    """
    print_header(f"MODEL ZOO - SINGLE CYCLE TEST ({'DRY_RUN' if dry_run else 'LIVE'})")

    # Initialize orchestrator
    print("🔄 Initializing Model Orchestrator...")
    orchestrator = ModelOrchestrator()

    # Show configuration
    config = orchestrator.config
    print(f"\n📋 Configuration:")
    print(f"   MODEL_ZOO_ENABLED: {config.get('MODEL_ZOO_ENABLED', False)}")
    print(f"   Forecast Model: {config.get('FORECAST_MODEL', 'ewma')}")
    print(f"   Signal Model: {config.get('SIGNAL_MODEL', 'signal_generator')}")
    print(f"   Allocation Model: {config.get('ALLOCATION_MODEL', 'fixed')}")

    # Create sample context
    print(f"\n📊 Creating sample context for {symbol}...")

    # Generate sample price data (simulated)
    base_price = 450.0
    prices = [base_price]
    for i in range(1, 20):
        # Random walk
        change = (hash(str(i)) % 100 - 50) / 1000  # -0.05 to +0.05
        prices.append(prices[-1] * (1 + change))

    context = {
        'symbol': symbol,
        'prices': prices,
        'indicators': {
            'RSI': 50 + (hash(str(42)) % 40),  # Random RSI
            'MACD': (hash(str(43)) % 100) / 100 - 0.5
        },
        'portfolio': {},
        'market_data': {
            'VIX': 18.0 + (hash(str(44)) % 10) / 2
        }
    }

    print(f"   Prices: {len(prices)} data points")
    print(f"   Latest price: ${prices[-1]:.2f}")
    print(f"   Return (latest): {(prices[-1] - prices[-2]) / prices[-2]:.2%}")

    # Run decision cycle
    print(f"\n🚀 Running decision cycle...")
    result = orchestrator.run_decision_cycle(context, dry_run=dry_run)

    # Display results
    if result['success']:
        plan = result['decision_plan']

        print(f"\n✅ DECISION CYCLE SUCCESSFUL")
        print(f"\n   Decision Plan:")
        print(f"     Action: {plan['action']}")
        print(f"     Symbol: {plan['symbol']}")
        print(f"     Confidence: {plan['confidence']:.2f}")
        print(f"     Target Value %: {plan['target_value_pct']:.2%}")
        print(f"     Order Type: {plan['order_type']}")

        print(f"\n   Reasons:")
        for i, reason in enumerate(plan['reasons'], 1):
            print(f"     {i}. {reason}")

        print(f"\n   Model Metadata:")
        meta = plan['model_metadata']
        print(f"     Forecast: {meta['forecast_model']} (v{meta['model_versions']['forecast']})")
        print(f"     Signal: {meta['signal_model']} (v{meta['model_versions']['signal']})")
        print(f"     Allocation: {meta['allocation_model']} (v{meta['model_versions']['allocation']})")

        print(f"\n   Learning Metadata:")
        learn = plan['learning_metadata']
        print(f"     Signal Components: {learn['signal_components']}")
        print(f"     Weights Used: {learn['weights_used']}")
        print(f"     Confidence Raw: {learn['confidence_raw']:.2f}")

        print(f"\n   VPA Artifact:")
        print(f"     Path: {result['vpa_path']}")
        print(f"     Decision ID: {plan['decision_id']}")

        # Verify VPA file exists
        vpa_path = Path(result['vpa_path'])
        if vpa_path.exists():
            print(f"     Status: ✅ VPA file created")
            file_size = vpa_path.stat().st_size
            print(f"     Size: {file_size} bytes")
        else:
            print(f"     Status: ❌ VPA file NOT created")

        # Safety verification
        print(f"\n   🔒 SAFETY VERIFICATION:")
        print(f"     Dry Run: {plan['model_metadata']['dry_run']}")
        print(f"     Trading Enabled: {plan.get('trading_enabled', False)}")

        if plan['model_metadata']['dry_run'] and not plan.get('trading_enabled', False):
            print(f"     Status: ✅ SAFE (no orders will be placed)")
        elif not plan['model_metadata']['dry_run'] and plan.get('trading_enabled', False):
            print(f"     Status: ⚠️  WARNING - LIVE TRADING POSSIBLE")
        else:
            print(f"     Status: ✅ SAFE (configuration inconsistent, defaults to safe)")

    else:
        print(f"\n❌ DECISION CYCLE FAILED")
        print(f"   Error: {result.get('error', 'Unknown error')}")

    print("\n" + "=" * 80)

    return result


def main():
    """Main entry point."""
    import argparse

    parser = argparse.ArgumentParser(description='Run one Model Zoo decision cycle')
    parser.add_argument('--symbol', type=str, default='SPY',
                       help='Symbol to analyze (default: SPY)')
    parser.add_argument('--live', action='store_true',
                       help='Disable dry-run (NOT recommended without proper setup)')

    args = parser.parse_args()

    # Safety check for live mode
    if args.live:
        print("\n⚠️  WARNING: LIVE MODE REQUESTED")
        print("   This will attempt to place real orders if QUANTUM_EXECUTION_ENABLED=true")
        print("   and QUANTUM_EXECUTION_DRY_RUN=false")
        response = input("\n   Confirm you want to run in live mode? (yes/no): ")
        if response.lower() != 'yes':
            print("   Aborting. Use --dry-run flag for safe testing.")
            return

        dry_run = False
    else:
        dry_run = True

    # Run cycle
    result = run_one_cycle(symbol=args.symbol, dry_run=dry_run)

    # Exit code based on success
    sys.exit(0 if result['success'] else 1)


if __name__ == "__main__":
    main()
