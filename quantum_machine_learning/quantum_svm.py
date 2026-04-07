#!/usr/bin/env python3
"""
Quantum Support Vector Machine (QSVM) for Trading Signal Classification
Hybrid quantum-classical SVM for BUY/SELL/HOLD signal generation

Based on:
- Quantum kernel methods for high-dimensional feature mapping
- Quantum-enhanced support vector machines
- Exponential feature space expansion via quantum circuits

Author: Quantum AI Trading Bot Team
Version: 1.0
Date: January 28, 2026
Phase: 2 - Quantum Machine Learning
"""

import numpy as np
import pandas as pd
from typing import Dict, List, Tuple, Optional, Any
from dataclasses import dataclass
from datetime import datetime
import logging
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler

# Try to import Qiskit and Qiskit Machine Learning
try:
    from qiskit import QuantumCircuit
    from qiskit.circuit.library import ZZFeatureMap
    from qiskit_machine_learning.kernels import QuantumKernel
    from qiskit_machine_learning.algorithms import QSVC
    QISKIT_ML_AVAILABLE = True
except ImportError:
    QISKIT_ML_AVAILABLE = False
    logging.warning("Qiskit Machine Learning not available - using classical SVM")


logger = logging.getLogger(__name__)


@dataclass
class QuantumSVMConfig:
    """Configuration for Quantum Support Vector Machine"""

    # Quantum kernel parameters
    num_qubits: int = 8  # Number of qubits for feature map
    feature_depth: int = 2  # Depth of feature map circuit
    entanglement: str = "linear"  # Entanglement pattern

    # SVM parameters
    C: float = 1.0  # Regularization parameter
    kernel_type: str = "quantum"  # quantum or classical
    class_weight: str = "balanced"  # Class weighting

    # Training parameters
    test_size: float = 0.2
    random_seed: int = 42

    # Labels
    num_classes: int = 3  # BUY, SELL, HOLD
    labels: List[int] = None  # 0=SELL, 1=HOLD, 2=BUY


class QuantumKernel:
    """
    Quantum Kernel for high-dimensional feature mapping

    Uses quantum circuits to compute kernel matrix:
    K(x_i, x_j) = |⟨φ(x_i)|φ(x_j)⟩|²
    """

    def __init__(self, num_qubits: int, depth: int, config: QuantumSVMConfig = None):
        self.num_qubits = num_qubits
        self.depth = depth
        self.config = config or QuantumSVMConfig()

        # Initialize quantum kernel
        if QISKIT_ML_AVAILABLE:
            try:
                feature_map = ZZFeatureMap(
                    feature_dimension=num_qubits,
                    reps=depth,
                    entanglement=self.config.entanglement
                )
                self.quantum_kernel = QuantumKernel(
                    feature_map=feature_map,
                    quantum_instance=None
                )
                self.use_quantum = True
                logger.info("✅ Quantum kernel initialized")
            except Exception as e:
                logger.warning(f"Quantum kernel initialization failed: {e}")
                self.use_quantum = False
        else:
            self.use_quantum = False

    def compute(self, X: np.ndarray, Y: np.ndarray = None) -> np.ndarray:
        """
        Compute kernel matrix

        Args:
            X: First dataset
            Y: Second dataset (optional, defaults to X)

        Returns:
            Kernel matrix K where K[i,j] = K(x_i, x_j)
        """
        if self.use_quantum and hasattr(self, 'quantum_kernel'):
            try:
                # Use quantum kernel
                if Y is None:
                    return self.quantum_kernel.evaluate(x_vec=X)
                else:
                    return self.quantum_kernel.evaluate(x_vec=X, y_vec=Y)
            except Exception as e:
                logger.error(f"Quantum kernel evaluation failed: {e}")
                return self._classical_kernel(X, Y)
        else:
            return self._classical_kernel(X, Y)

    def _classical_kernel(self, X: np.ndarray, Y: np.ndarray = None) -> np.ndarray:
        """
        Classical RBF kernel fallback

        K(x, y) = exp(-γ ||x - y||²)
        """
        from sklearn.metrics.pairwise import rbf_kernel

        if Y is None:
            return rbf_kernel(X, X)
        else:
            return rbf_kernel(X, Y)


class QuantumSupportVectorMachine:
    """
    Quantum Support Vector Machine for trading signal classification

    Uses quantum kernel methods to classify market conditions into
    BUY, SELL, or HOLD signals.
    """

    def __init__(self, config: QuantumSVMConfig = None):
        self.config = config or QuantumSVMConfig()
        self.scaler = StandardScaler()

        # Initialize quantum kernel
        self.quantum_kernel = QuantumKernel(
            num_qubits=self.config.num_qubits,
            depth=self.config.feature_depth,
            config=self.config
        )

        # Initialize SVM model
        if QISKIT_ML_AVAILABLE:
            try:
                self.qsvm = QSVC(
                    quantum_kernel=self.quantum_kernel.quantum_kernel,
                    num_classes=self.config.num_classes
                )
                self.use_quantum = True
                logger.info("✅ QSVM initialized")
            except Exception as e:
                logger.warning(f"QSVM initialization failed: {e}")
                self.use_quantum = False
                self._initialize_classical_svm()
        else:
            self.use_quantum = False
            self._initialize_classical_svm()

        self.is_trained = False
        self.X_train = None
        self.y_train = None

        logger.info(f"🚀 Quantum SVM initialized:")
        logger.info(f"  Qubits: {self.config.num_qubits}")
        logger.info(f"  Feature depth: {self.config.feature_depth}")
        logger.info(f"  Classes: {self.config.num_classes} (BUY, SELL, HOLD)")
        logger.info(f"  Using quantum: {self.use_quantum}")

    def _initialize_classical_svm(self):
        """Initialize classical SVM as fallback"""
        from sklearn.svm import SVC
        self.classical_svm = SVC(
            C=self.config.C,
            kernel='rbf',
            class_weight=self.config.class_weight,
            decision_function_shape='ovr'
        )
        logger.info("ℹ️  Using classical SVM (RBF kernel)")

    def prepare_features(self, price_data: pd.DataFrame) -> np.ndarray:
        """
        Prepare features for SVM classification

        Args:
            price_data: DataFrame with OHLCV data and technical indicators

        Returns:
            Feature matrix X
        """
        features = []

        # Price-based features
        if 'close' in price_data.columns:
            # Returns
            returns = price_data['close'].pct_change().fillna(0)
            features.append(returns.values)

            # Moving averages
            ma_short = price_data['close'].rolling(window=10).mean()
            ma_long = price_data['close'].rolling(window=50).mean()
            ma_ratio = (ma_short / ma_long).fillna(1.0)
            features.append(ma_ratio.values)

            # Volatility
            volatility = price_data['close'].rolling(window=20).std()
            features.append((volatility / price_data['close']).fillna(0).values)

        # RSI if available
        if 'rsi' in price_data.columns:
            rsi_normalized = (price_data['rsi'] - 50) / 50  # Normalize to [-1, 1]
            features.append(rsi_normalized.fillna(0).values)

        # MACD if available
        if 'macd' in price_data.columns:
            macd_normalized = price_data['macd'] / price_data['close'].abs()
            features.append(macd_normalized.fillna(0).values)

        # Combine features
        X = np.column_stack([f for f in features if len(f) > 0])

        # Handle NaN values
        X = np.nan_to_num(X, nan=0.0, posinf=0.0, neginf=0.0)

        return X

    def create_labels(self, price_data: pd.DataFrame) -> np.ndarray:
        """
        Create classification labels from price data

        Rules:
        - BUY (2): Price expected to increase
        - SELL (0): Price expected to decrease
        - HOLD (1): Sideways/uncertain

        Args:
            price_data: DataFrame with OHLCV data

        Returns:
            Label array y
        """
        # Compute future returns
        future_returns = price_data['close'].shift(-1) / price_data['close'] - 1

        # Compute momentum
        momentum = (price_data['close'] - price_data['close'].shift(5)) / price_data['close'].shift(5)

        # Create labels
        labels = []
        for i in range(len(price_data)):
            if pd.isna(future_returns[i]) or pd.isna(momentum[i]):
                labels.append(1)  # HOLD for NaN
            else:
                # Strong buy signal: positive momentum and expected rise
                if momentum[i] > 0.02 and future_returns[i] > 0.01:
                    labels.append(2)  # BUY
                # Strong sell signal: negative momentum and expected drop
                elif momentum[i] < -0.02 and future_returns[i] < -0.01:
                    labels.append(0)  # SELL
                # Otherwise hold
                else:
                    labels.append(1)  # HOLD

        return np.array(labels)

    def train(self, price_data: pd.DataFrame) -> Dict[str, Any]:
        """
        Train quantum SVM on market data

        Args:
            price_data: Training data with features

        Returns:
            Training metrics
        """
        logger.info("\n🎓 Training Quantum SVM...")

        # Prepare features and labels
        X = self.prepare_features(price_data)
        y = self.create_labels(price_data)

        # Remove any remaining NaN rows
        valid_mask = ~(np.isnan(X).any(axis=1) | np.isnan(y))
        X = X[valid_mask]
        y = y[valid_mask]

        logger.info(f"  Samples: {len(X)}")
        logger.info(f"  Features: {X.shape[1]}")

        # Class distribution
        unique, counts = np.unique(y, return_counts=True)
        logger.info(f"  Class distribution:")
        for cls, count in zip(unique, counts):
            label_name = {0: 'SELL', 1: 'HOLD', 2: 'BUY'}[cls]
            logger.info(f"    {label_name}: {count} ({count/len(y)*100:.1f}%)")

        # Split data
        X_train, X_test, y_train, y_test = train_test_split(
            X, y,
            test_size=self.config.test_size,
            random_state=self.config.random_seed,
            stratify=y
        )

        # Scale features
        X_train_scaled = self.scaler.fit_transform(X_train)
        X_test_scaled = self.scaler.transform(X_test)

        # Train model
        if self.use_quantum and hasattr(self, 'qsvm'):
            try:
                logger.info("  Training with quantum kernel...")
                self.qsvm.fit(X_train_scaled, y_train)
                self.is_trained = True
            except Exception as e:
                logger.error(f"Quantum SVM training failed: {e}")
                self._train_classical(X_train_scaled, y_train)
        else:
            logger.info("  Training with classical SVM...")
            self._train_classical(X_train_scaled, y_train)

        # Store training data
        self.X_train = X_train_scaled
        self.y_train = y_train

        # Evaluate
        y_pred = self.predict(X_test)

        # Calculate metrics
        accuracy = np.mean(y_pred == y_test)

        from sklearn.metrics import classification_report, confusion_matrix
        target_names = ['SELL', 'HOLD', 'BUY']
        report = classification_report(y_test, y_pred, target_names=target_names, zero_division=0)

        logger.info(f"\n✅ Training complete!")
        logger.info(f"  Test Accuracy: {accuracy:.2%}")
        logger.info(f"\n  Classification Report:\n{report}")

        return {
            'accuracy': accuracy,
            'classification_report': report,
            'confusion_matrix': confusion_matrix(y_test, y_pred),
            'test_samples': len(X_test),
            'train_samples': len(X_train)
        }

    def _train_classical(self, X_train: np.ndarray, y_train: np.ndarray):
        """Train classical SVM fallback"""
        self.classical_svm.fit(X_train, y_train)
        self.is_trained = True

    def predict(self, X: np.ndarray) -> np.ndarray:
        """
        Make predictions

        Args:
            X: Feature matrix

        Returns:
            Predicted labels (0=SELL, 1=HOLD, 2=BUY)
        """
        if not self.is_trained:
            raise ValueError("Model not trained yet. Call train() first.")

        # Scale features
        X_scaled = self.scaler.transform(X)

        # Predict
        if self.use_quantum and hasattr(self, 'qsvm'):
            try:
                predictions = self.qsvm.predict(X_scaled)
            except Exception as e:
                logger.error(f"Quantum prediction failed: {e}")
                predictions = self.classical_svm.predict(X_scaled)
        else:
            predictions = self.classical_svm.predict(X_scaled)

        return predictions

    def predict_proba(self, X: np.ndarray) -> np.ndarray:
        """
        Predict class probabilities

        Args:
            X: Feature matrix

        Returns:
            Probability distribution over classes
        """
        if not self.is_trained:
            raise ValueError("Model not trained yet. Call train() first.")

        # Scale features
        X_scaled = self.scaler.transform(X)

        # Predict probabilities
        if self.use_quantum and hasattr(self, 'qsvm'):
            # QSVM doesn't have predict_proba, use decision function
            decision = self.qsvm.decision_function(X_scaled)
            # Convert to probabilities via softmax
            proba = np.exp(decision) / np.sum(np.exp(decision), axis=1, keepdims=True)
            return proba
        else:
            return self.classical_svm.predict_proba(X_scaled)

    def generate_trading_signal(self, current_features: np.ndarray) -> Dict[str, Any]:
        """
        Generate trading signal from current market state

        Args:
            current_features: Current market features

        Returns:
            Trading signal with confidence
        """
        # Reshape if needed
        if current_features.ndim == 1:
            current_features = current_features.reshape(1, -1)

        # Predict
        prediction = self.predict(current_features)[0]

        # Get probabilities if available
        try:
            probabilities = self.predict_proba(current_features)[0]
            confidence = np.max(probabilities)
        except:
            confidence = 0.5  # Default confidence

        # Convert to trading signal
        label_map = {
            0: 'SELL',
            1: 'HOLD',
            2: 'BUY'
        }

        action = label_map[prediction]

        # Calculate signal strength
        if prediction == 2:  # BUY
            strength = confidence if confidence > 0.5 else 0.0
        elif prediction == 0:  # SELL
            strength = confidence if confidence > 0.5 else 0.0
        else:  # HOLD
            strength = 0.0

        return {
            'action': action,
            'confidence': confidence,
            'strength': strength,
            'probabilities': {
                'SELL': probabilities[0] if 'probabilities' in locals() else 0.0,
                'HOLD': probabilities[1] if 'probabilities' in locals() else 0.0,
                'BUY': probabilities[2] if 'probabilities' in locals() else 0.0
            },
            'method': 'QUANTUM_SVM' if self.use_quantum else 'CLASSICAL_SVM'
        }


# Factory function
def create_quantum_svm(num_qubits: int = 8) -> QuantumSupportVectorMachine:
    """Create Quantum SVM with default configuration"""
    config = QuantumSVMConfig(num_qubits=num_qubits)
    return QuantumSupportVectorMachine(config)


# Testing and demonstration
if __name__ == "__main__":
    print("🚀 Quantum Support Vector Machine - Testing")
    print("=" * 60)

    # Generate synthetic market data
    np.random.seed(42)
    num_days = 500

    # Generate price with trend and cycles
    t = np.arange(num_days)
    price = 100 + 0.1 * t + 5 * np.sin(2 * np.pi * t / 50) + np.random.randn(num_days) * 2

    # Create technical indicators
    rsi = 50 + 20 * np.sin(2 * np.pi * t / 20) + np.random.randn(num_days) * 5
    rsi = np.clip(rsi, 0, 100)

    macd = 0.5 * np.sin(2 * np.pi * t / 30) + np.random.randn(num_days) * 0.5

    # Create DataFrame
    data = pd.DataFrame({
        'close': price,
        'rsi': rsi,
        'macd': macd
    })

    print(f"📊 Generated synthetic market data:")
    print(f"  Days: {num_days}")
    print(f"  Price range: ${price.min():.2f} - ${price.max():.2f}")

    # Create QSVM
    print("\n🔬 Creating Quantum SVM...")
    qsvm = create_quantum_svm(num_qubits=8)

    # Train
    print("\n🎓 Training...")
    training_metrics = qsvm.train(data)

    # Test predictions
    print("\n🔮 Sample predictions:")
    test_indices = np.random.choice(len(data), 5, replace=False)
    for idx in test_indices:
        features = qsvm.prepare_features(data.iloc[idx:idx+1])
        signal = qsvm.generate_trading_signal(features)

        print(f"  Day {idx}: {signal['action']} (confidence: {signal['confidence']:.2%})")
        print(f"    Probabilities - SELL: {signal['probabilities']['SELL']:.3f}, "
              f"HOLD: {signal['probabilities']['HOLD']:.3f}, BUY: {signal['probabilities']['BUY']:.3f}")

    print("\n✅ Quantum SVM test completed!")
    print(f"📊 Final Test Accuracy: {training_metrics['accuracy']:.2%}")
