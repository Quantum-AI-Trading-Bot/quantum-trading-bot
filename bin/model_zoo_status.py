#!/usr/bin/env python3
"""
Model Zoo Status - Display current model configuration and status.

Shows:
- Enabled models and versions
- Last decision info
- Learner weights
- Feature flags
"""

import sys
import os
from pathlib import Path
from datetime import datetime

# Add platform to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from models.registry import get_registry
from engine.model_orchestrator import ModelOrchestrator


def print_header(title: str):
    print("\n" + "=" * 80)
    print(f"  {title}")
    print("=" * 80 + "\n")


def print_model_status():
    """Print model zoo status."""
    print_header("MODEL ZOO STATUS")

    # Load config
    orchestrator = ModelOrchestrator()
    config = orchestrator.config

    # Feature flags
    print("🔌 FEATURE FLAGS:")
    print(f"   MODEL_ZOO_ENABLED: {config.get('MODEL_ZOO_ENABLED', False)}")
    print(f"   LEARNING_ENABLED: {config.get('LEARNING_ENABLED', True)}")
    print(f"   RL_ENABLED: {config.get('RL_ENABLED', False)}")
    print(f"   QUANTUM_OPT_ENABLED: {config.get('QUANTUM_OPT_ENABLED', False)}")
    print(f"   QUANTUM_EXECUTION_ENABLED: {os.environ.get('QUANTUM_EXECUTION_ENABLED', 'false')}")
    print(f"   QUANTUM_EXECUTION_DRY_RUN: {os.environ.get('QUANTUM_EXECUTION_DRY_RUN', 'true')}")

    # Active models
    print("\n🤖 ACTIVE MODELS:")
    print(f"   Forecast: {config.get('FORECAST_MODEL', 'ewma')}")
    print(f"   Signal: {config.get('SIGNAL_MODEL', 'signal_generator')}")
    print(f"   Allocation: {config.get('ALLOCATION_MODEL', 'fixed')}")
    print(f"   Execution: {config.get('EXECUTION_POLICY', 'default')}")

    # Available models
    registry = get_registry()
    model_info = registry.get_model_info()

    print("\n📚 AVAILABLE MODELS:")
    for model_type, models in model_info.items():
        print(f"   {model_type.upper()}: {', '.join(models) if models else 'None'}")

    # Safety constraints
    print("\n🔒 SAFETY CONSTRAINTS:")
    print(f"   MAX_POSITION_SIZE_PCT: {config.get('MAX_POSITION_SIZE_PCT', 0.15):.1%}")
    print(f"   MIN_CONFIDENCE_THRESHOLD: {config.get('MIN_CONFIDENCE_THRESHOLD', 0.75):.2f}")
    print(f"   MAX_DAILY_TRADES: {config.get('MAX_DAILY_TRADES', 50)}")

    # Last decision (check ledger)
    print("\n📊 LAST DECISION:")
    try:
        from learning.trade_ledger import TradeLedger
        ledger = TradeLedger()
        decisions = ledger.read_decisions(limit=1)

        if decisions:
            dec = decisions[0]
            print(f"   Timestamp: {dec.get('timestamp', 'Unknown')}")
            print(f"   Symbol: {dec.get('symbol', 'Unknown')}")
            print(f"   Action: {dec.get('action', 'Unknown')}")
            print(f"   Confidence: {dec.get('confidence', 0.0):.2f}")
            print(f"   Dry Run: {dec.get('dry_run', True)}")
            print(f"   Trading Enabled: {dec.get('trading_enabled', False)}")

            if dec.get('model_metadata'):
                meta = dec['model_metadata']
                print(f"\n   Models Used:")
                print(f"     Forecast: {meta.get('forecast_model', 'N/A')}")
                print(f"     Signal: {meta.get('signal_model', 'N/A')}")
                print(f"     Allocation: {meta.get('allocation_model', 'N/A')}")
        else:
            print("   No decisions recorded yet")
    except Exception as e:
        print(f"   Could not read decisions: {e}")

    # Learner weights
    print("\n🧠 LEARNER STATUS:")
    try:
        from learning.signal_weight_learner import SignalWeightLearner
        learner = SignalWeightLearner()
        weights = learner.get_weights()

        print("   Signal Weights:")
        for signal, weight in weights.items():
            print(f"     {signal}: {weight:.3f}")

        stats = learner.get_statistics()
        print(f"\n   Total Updates: {stats['total_updates']}")
        print(f"   Trades Learned: {stats['total_trades_learned']}")
        print(f"   Last Update: {stats['last_update'] or 'Never'}")

    except Exception as e:
        print(f"   Could not read learner state: {e}")

    # VPA storage
    print("\n📁 VPA STORAGE:")
    vpa_path = Path(config.get('vpa_storage_path', '/home/davidsanker/platform/vpa_storage'))
    if vpa_path.exists():
        vpa_files = list(vpa_path.glob('vpa_*.json'))
        print(f"   Total VPA artifacts: {len(vpa_files)}")
        if vpa_files:
            latest = max(vpa_files, key=lambda p: p.stat().st_mtime)
            print(f"   Latest: {latest.name}")
            print(f"   Modified: {datetime.fromtimestamp(latest.stat().st_mtime).isoformat()}")
    else:
        print("   VPA storage directory not found")

    print("\n" + "=" * 80)


def main():
    """Main entry point."""
    print_model_status()


if __name__ == "__main__":
    main()
