#!/usr/bin/env python3
"""
Quick test script to verify Phase 1 models can be loaded via Model Zoo
"""

import sys
import os
from pathlib import Path

# Add platform to path
platform_path = Path(__file__).parent.parent
sys.path.insert(0, str(platform_path))

from models.registry import ModelRegistry

def test_phase1_models():
    """Test loading Phase 1 models from registry."""

    print("="*60)
    print("Testing Phase 1 Model Zoo Integration")
    print("="*60)

    registry = ModelRegistry()

    # Test 1: Check if models are registered
    print("\n1. Checking registered models...")
    signal_models = registry._signal_models.keys()
    print(f"   Registered signal models: {list(signal_models)}")

    phase1_models = [name for name in signal_models if name.startswith('phase1_')]
    print(f"   Phase 1 models: {phase1_models}")

    if not phase1_models:
        print("   ❌ FAILED: No Phase 1 models registered!")
        return False

    print(f"   ✅ PASSED: {len(phase1_models)} Phase 1 models registered")

    # Test 2: Try to instantiate each model
    print("\n2. Testing model instantiation...")
    for model_name in phase1_models:
        try:
            if model_name == "phase1_ma_crossover":
                config = {
                    'short_window': 10,
                    'long_window': 50,
                    'signal_threshold': 0.02
                }
            elif model_name == "phase1_multi_ma":
                config = {
                    'ma_pairs': [(5, 20), (10, 50)],
                    'consensus_threshold': 2
                }
            elif model_name == "phase1_ml_joblib":
                # Skip if model file doesn't exist
                model_path = "/home/davidsanker/platform/phase1/phase1/results/SPY_random_forest_model_20260123_120503.joblib"
                if not os.path.exists(model_path):
                    print(f"   ⚠️  SKIPPED {model_name}: Model file not found at {model_path}")
                    continue
                config = {
                    'model_path': model_path,
                    'confidence_threshold': 0.6
                }
            else:
                print(f"   ⚠️  SKIPPED {model_name}: Unknown model")
                continue

            model = registry.create_signal_model(model_name, config)
            print(f"   ✅ PASSED {model_name}: {model.__class__.__name__}")

        except Exception as e:
            print(f"   ❌ FAILED {model_name}: {e}")
            return False

    print("\n" + "="*60)
    print("All Phase 1 model tests PASSED!")
    print("="*60)
    return True

if __name__ == "__main__":
    success = test_phase1_models()
    sys.exit(0 if success else 1)
