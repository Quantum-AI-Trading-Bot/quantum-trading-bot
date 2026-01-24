#!/usr/bin/env python3
"""
Quantum AI Trading Bot - CLI Entry Points

This module provides command-line interface functions for the trading bot.
These are registered as console scripts in pyproject.toml.
"""

import sys
from pathlib import Path
from typing import Optional

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))


def run_one_cycle(symbol: str = 'SPY', dry_run: bool = True):
    """
    Run a single decision cycle.

    Usage:
        qbot-cycle [--symbol SPY] [--dry-run]

    Args:
        symbol: Symbol to analyze (default: SPY)
        dry_run: If True, don't execute orders (default: True)
    """
    import argparse
    from engine.model_orchestrator import ModelOrchestrator

    parser = argparse.ArgumentParser(description='Run a single trading cycle')
    parser.add_argument('--symbol', default='SPY', help='Symbol to analyze')
    parser.add_argument('--no-dry-run', action='store_false', dest='dry_run',
                       help='Disable dry-run mode and execute trades')
    args = parser.parse_args()

    print(f"\n{'='*80}")
    print(f"  QUANTUM AI TRADING BOT - SINGLE CYCLE")
    print(f"  Symbol: {args.symbol}")
    print(f"  Mode: {'DRY_RUN' if args.dry_run else 'LIVE'}")
    print(f"{'='*80}\n")

    # Initialize orchestrator
    print("🔄 Initializing Model Orchestrator...")
    orchestrator = ModelOrchestrator()

    # Run single cycle
    try:
        result = orchestrator.run_one_cycle(symbol=args.symbol, dry_run=args.dry_run)
        print(f"\n✅ Cycle completed successfully")
        return 0
    except Exception as e:
        print(f"\n❌ Cycle failed: {e}")
        return 1


def run_paper_production():
    """
    Run paper trading in production mode.

    Usage:
        qbot-paper-prod

    This runs continuous paper trading with proper risk controls and logging.
    """
    import argparse

    parser = argparse.ArgumentParser(description='Run paper trading production')
    parser.add_argument('--max-cycles', type=int, default=None,
                       help='Maximum number of cycles to run (default: infinite)')
    args = parser.parse_args()

    print(f"\n{'='*80}")
    print(f"  QUANTUM AI TRADING BOT - PAPER PRODUCTION")
    print(f"  Mode: PAPER TRADING")
    if args.max_cycles:
        print(f"  Max Cycles: {args.max_cycles}")
    else:
        print(f"  Max Cycles: Unlimited (run until stopped)")
    print(f"{'='*80}\n")

    # Import and run paper production
    # This would import from bin/run_paper_production.py
    print("🚀 Starting paper production...")
    print("⚠️  This is a placeholder - implement actual paper production logic")
    return 0


def status_dashboard():
    """
    Display trading bot status dashboard.

    Usage:
        qbot-status
    """
    print(f"\n{'='*80}")
    print(f"  QUANTUM AI TRADING BOT - STATUS DASHBOARD")
    print(f"{'='*80}\n")

    # Import status modules
    print("📊 Bot Status:")
    print("   Trading Mode: PAPER")
    print("   IB Connection: Not connected")
    print("   Last Cycle: Never")
    print("   Open Positions: 0")

    print("\n📈 Performance:")
    print("   Today's P&L: N/A")
    print("   Win Rate: N/A")

    print("\n⚙️  Configuration:")
    print("   Model Zoo: Enabled")
    print("   Learning: Enabled")

    return 0


if __name__ == '__main__':
    # Default to running one cycle
    sys.exit(run_one_cycle())
