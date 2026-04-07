#!/usr/bin/env python3
"""
Simple test for Enhanced Quantum LSTM
"""

import numpy as np
import sys
import os

# Add the platform directory to the path
sys.path.append('/home/davidsanker/platform')

from ml.enhanced_quantum_lstm import create_enhanced_quantum_lstm

def test_enhanced_quantum_lstm():
    """Test the enhanced quantum LSTM implementation"""
    print("🚀 Testing Enhanced Quantum LSTM...")

    # Create a small test model
    model = create_enhanced_quantum_lstm(
        input_dim=1,
        hidden_dim=16,  # Smaller for faster testing
        quantum_bits=4,
        use_bls=True,
        use_multi_scale_attention=True,
        epochs=2,  # Just 2 epochs for testing
        batch_size=8
    )

    print("✅ Model created successfully")

    # Create small test data
    np.random.seed(42)
    seq_length = 10
    num_samples = 20

    # Simple sine wave data
    X = np.random.randn(num_samples, seq_length, 1)
    y = np.random.randn(num_samples, 1)

    print(f"📊 Test data shape: X={X.shape}, y={y.shape}")

    # Test forward pass
    try:
        outputs, hidden = model.forward(X)
        print(f"✅ Forward pass successful: output shape={outputs.shape}")
    except Exception as e:
        print(f"❌ Forward pass failed: {e}")
        return False

    # Test prediction
    try:
        predictions = model.predict(X)
        print(f"✅ Prediction successful: shape={predictions.shape}")
    except Exception as e:
        print(f"❌ Prediction failed: {e}")
        return False

    # Test training step
    try:
        loss = model.train_step(X, y, 0.01)
        print(f"✅ Training step successful: loss={loss:.6f}")
    except Exception as e:
        print(f"❌ Training step failed: {e}")
        return False

    print("🎉 All tests passed!")
    return True

if __name__ == "__main__":
    success = test_enhanced_quantum_lstm()
    if success:
        print("✅ Enhanced Quantum LSTM is working correctly")
    else:
        print("❌ Enhanced Quantum LSTM has issues")
        sys.exit(1)