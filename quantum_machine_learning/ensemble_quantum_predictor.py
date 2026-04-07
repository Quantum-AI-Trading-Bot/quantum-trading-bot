#!/usr/bin/env python3
"""
Ensemble Quantum ML Predictor for Trading Signals
Combines QNN, QSVM, and QBM for robust price prediction and trading decisions

Based on:
- Ensemble learning with quantum algorithms
- Confidence-weighted prediction combination
- Quantum-enhanced feature extraction
- Multi-model consensus for robustness

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

# Import quantum ML modules
try:
    from .quantum_neural_network import QuantumNeuralNetwork, QuantumNNConfig
    from .quantum_svm import QuantumSupportVectorMachine, QuantumSVMConfig
    from .quantum_boltzmann_machine import QuantumBoltzmannMachine, QuantumBMConfig
except ImportError:
    from quantum_neural_network import QuantumNeuralNetwork, QuantumNNConfig
    from quantum_svm import QuantumSupportVectorMachine, QuantumSVMConfig
    from quantum_boltzmann_machine import QuantumBoltzmannMachine, QuantumBMConfig

logger = logging.getLogger(__name__)


@dataclass
class EnsembleConfig:
    """Configuration for Ensemble Quantum Predictor"""

    # Model weights (sum should = 1.0)
    qnn_weight: float = 0.4  # Neural network weight
    qsvm_weight: float = 0.4  # SVM weight
    qbm_weight: float = 0.2  # Boltzmann machine weight

    # Confidence thresholds
    min_confidence: float = 0.3  # Minimum confidence for trading
    strong_signal_threshold: float = 0.7  # Threshold for strong signals

    # Voting mechanism
    voting_strategy: str = "weighted"  # weighted, soft, hard
    consensus_threshold: float = 0.6  # Agreement threshold for consensus

    # Individual model configs
    qnn_config: QuantumNNConfig = None
    qsvm_config: QuantumSVMConfig = None
    qbm_config: QuantumBMConfig = None

    def __post_init__(self):
        """Validate configuration"""
        total_weight = self.qnn_weight + self.qsvm_weight + self.qbm_weight
        if abs(total_weight - 1.0) > 0.01:
            logger.warning(f"Weights sum to {total_weight}, normalizing...")
            self.qnn_weight /= total_weight
            self.qsvm_weight /= total_weight
            self.qbm_weight /= total_weight

        # Create default configs if not provided
        if self.qnn_config is None:
            self.qnn_config = QuantumNNConfig()
        if self.qsvm_config is None:
            self.qsvm_config = QuantumSVMConfig()
        if self.qbm_config is None:
            self.qbm_config = QuantumBMConfig()


class EnsembleQuantumPredictor:
    """
    Ensemble Quantum Machine Learning Predictor

    Combines predictions from QNN, QSVM, and QBM to generate
    robust trading signals with confidence measures.
    """

    def __init__(self, config: EnsembleConfig = None):
        self.config = config or EnsembleConfig()

        # Initialize individual models
        logger.info("🔧 Initializing Quantum ML Ensemble...")

        self.qnn = QuantumNeuralNetwork(self.config.qnn_config)
        self.qsvm = QuantumSupportVectorMachine(self.config.qsvm_config)
        self.qbm = QuantumBoltzmannMachine(self.config.qbm_config)

        # Training state
        self.is_trained = False
        self.training_history = {}

        logger.info(f"✅ Ensemble initialized:")
        logger.info(f"  QNN weight: {self.config.qnn_weight:.2%}")
        logger.info(f"  QSVM weight: {self.config.qsvm_weight:.2%}")
        logger.info(f"  QBM weight: {self.config.qbm_weight:.2%}")
        logger.info(f"  Voting strategy: {self.config.voting_strategy}")

    def prepare_features(self, price_data: pd.DataFrame) -> np.ndarray:
        """
        Prepare features for all models

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
            rsi_normalized = (price_data['rsi'] - 50) / 50
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

    def train(self, price_data: pd.DataFrame) -> Dict[str, Any]:
        """
        Train all ensemble models

        Args:
            price_data: Training data with features

        Returns:
            Training metrics for all models
        """
        logger.info("\n🎓 Training Ensemble Quantum ML Models...")

        # Prepare features
        X = self.prepare_features(price_data)
        y = price_data['close'].values

        logger.info(f"  Samples: {len(X)}")
        logger.info(f"  Features: {X.shape[1]}")

        # Train QNN for price prediction
        logger.info("\n🧠 Training Quantum Neural Network...")
        try:
            # Use sliding window for time series
            window_size = 50
            X_qnn = []
            y_qnn = []

            for i in range(window_size, len(X)):
                X_qnn.append(X[i-window_size:i].flatten())
                y_qnn.append(y[i])

            X_qnn = np.array(X_qnn)
            y_qnn = np.array(y_qnn)

            if len(X_qnn) > 100:  # Minimum samples
                qnn_history = self.qnn.train(X_qnn, y_qnn, epochs=50)
                self.training_history['qnn'] = qnn_history
                logger.info("✅ QNN training complete")
            else:
                logger.warning("⚠️  Insufficient data for QNN training")
                self.training_history['qnn'] = None
        except Exception as e:
            logger.error(f"❌ QNN training failed: {e}")
            self.training_history['qnn'] = None

        # Train QSVM for signal classification
        logger.info("\n🎯 Training Quantum SVM...")
        try:
            qsvm_metrics = self.qsvm.train(price_data)
            self.training_history['qsvm'] = qsvm_metrics
            logger.info(f"✅ QSVM training complete (accuracy: {qsvm_metrics['accuracy']:.2%})")
        except Exception as e:
            logger.error(f"❌ QSVM training failed: {e}")
            self.training_history['qsvm'] = None

        # Train QBM for distribution learning
        logger.info("\n🎲 Training Quantum Boltzmann Machine...")
        try:
            qbm_results = self.qbm.learn_market_distribution(price_data)
            self.training_history['qbm'] = qbm_results
            logger.info("✅ QBM training complete")
        except Exception as e:
            logger.error(f"❌ QBM training failed: {e}")
            self.training_history['qbm'] = None

        self.is_trained = True

        logger.info("\n✅ Ensemble training complete!")

        return self.training_history

    def predict_price(self, current_features: np.ndarray) -> Dict[str, Any]:
        """
        Predict future price using ensemble

        Args:
            current_features: Current market features

        Returns:
            Price prediction with confidence
        """
        if not self.is_trained:
            raise ValueError("Models not trained yet. Call train() first.")

        predictions = {}
        confidences = {}

        # QNN prediction (if trained)
        if self.training_history.get('qnn') is not None:
            try:
                qnn_pred = self.qnn.predict(current_features.reshape(1, -1))[0]
                predictions['qnn'] = qnn_pred
                # Confidence based on training loss
                qnn_loss = self.training_history['qnn'].get('final_loss', 1.0)
                confidences['qnn'] = 1.0 / (1.0 + qnn_loss)
            except Exception as e:
                logger.error(f"QNN prediction failed: {e}")
                confidences['qnn'] = 0.0

        # QSVM-based price prediction (if trained)
        if self.training_history.get('qsvm') is not None:
            try:
                # Use QSVM class probabilities to estimate price direction
                signal = self.qsvm.generate_trading_signal(current_features)
                # Convert signal to price estimate (simplified)
                if signal['action'] == 'BUY':
                    qsvm_pred = current_features[-1] * (1 + 0.01 * signal['strength'])
                elif signal['action'] == 'SELL':
                    qsvm_pred = current_features[-1] * (1 - 0.01 * signal['strength'])
                else:
                    qsvm_pred = current_features[-1]

                predictions['qsvm'] = qsvm_pred
                confidences['qsvm'] = signal['confidence']
            except Exception as e:
                logger.error(f"QSVM prediction failed: {e}")
                confidences['qsvm'] = 0.0

        # QBM-based prediction (if trained)
        if self.training_history.get('qbm') is not None:
            try:
                # Use QBM to generate scenarios and take average
                scenarios = self.qbm.generate_scenarios(num_scenarios=100, num_steps=1)
                qbm_pred = np.mean(scenarios[:, 0, :])
                predictions['qbm'] = qbm_pred
                # Confidence based on scenario agreement
                confidences['qbm'] = 1.0 - self.training_history['qbm']['risk_metrics']['volatility']
            except Exception as e:
                logger.error(f"QBM prediction failed: {e}")
                confidences['qbm'] = 0.0

        # Weighted ensemble prediction
        if predictions:
            ensemble_pred = 0.0
            total_weight = 0.0

            for model_name in ['qnn', 'qsvm', 'qbm']:
                if model_name in predictions and model_name in confidences:
                    weight = getattr(self.config, f'{model_name}_weight')
                    confidence = confidences[model_name]
                    ensemble_pred += predictions[model_name] * weight * confidence
                    total_weight += weight * confidence

            if total_weight > 0:
                ensemble_pred /= total_weight
            else:
                # Fallback to simple average
                ensemble_pred = np.mean(list(predictions.values()))

            # Overall confidence (weighted average)
            overall_confidence = 0.0
            for model_name in ['qnn', 'qsvm', 'qbm']:
                if model_name in confidences:
                    weight = getattr(self.config, f'{model_name}_weight')
                    overall_confidence += confidences[model_name] * weight

            return {
                'prediction': ensemble_pred,
                'confidence': overall_confidence,
                'individual_predictions': predictions,
                'individual_confidences': confidences
            }
        else:
            return {
                'prediction': current_features[-1],  # No change
                'confidence': 0.0,
                'error': 'All predictions failed'
            }

    def generate_trading_signal(self, price_data: pd.DataFrame) -> Dict[str, Any]:
        """
        Generate comprehensive trading signal using ensemble

        Args:
            price_data: Current market data

        Returns:
            Trading signal with ensemble recommendations
        """
        logger.info("\n🔮 Generating Ensemble Trading Signal...")

        # Prepare features
        X = self.prepare_features(price_data)

        if len(X) < 50:
            return {
                'action': 'HOLD',
                'confidence': 0.0,
                'strength': 0.0,
                'reason': 'Insufficient data (need 50+ data points)'
            }

        # Get latest features
        current_features = X[-50:]  # Last 50 data points

        # Get individual model signals
        signals = {}
        signal_strengths = {}

        # QSVM signal
        if self.training_history.get('qsvm') is not None:
            try:
                qsvm_signal = self.qsvm.generate_trading_signal(current_features)
                signals['qsvm'] = qsvm_signal['action']
                signal_strengths['qsvm'] = qsvm_signal['strength']
            except Exception as e:
                logger.error(f"QSVM signal generation failed: {e}")

        # QNN-based signal
        if self.training_history.get('qnn') is not None:
            try:
                current_price = price_data['close'].iloc[-1]
                price_pred = self.predict_price(current_features.flatten())

                if 'prediction' in price_pred:
                    predicted_change = (price_pred['prediction'] - current_price) / current_price

                    if predicted_change > 0.01:
                        signals['qnn'] = 'BUY'
                        signal_strengths['qnn'] = min(abs(predicted_change) * 10, 1.0)
                    elif predicted_change < -0.01:
                        signals['qnn'] = 'SELL'
                        signal_strengths['qnn'] = min(abs(predicted_change) * 10, 1.0)
                    else:
                        signals['qnn'] = 'HOLD'
                        signal_strengths['qnn'] = 0.0
            except Exception as e:
                logger.error(f"QNN signal generation failed: {e}")

        # QBM-based signal (risk assessment)
        if self.training_history.get('qbm') is not None:
            try:
                risk_metrics = self.qbm.assess_risk(
                    current_state=current_features[-1],
                    num_scenarios=500
                )

                # High risk ->倾向于 HOLD or reduce position
                if risk_metrics['prob_large_loss'] > 0.2:
                    signals['qbm'] = 'HOLD'
                    signal_strengths['qbm'] = -0.5  # Negative strength (risk warning)
                else:
                    signals['qbm'] = 'HOLD'
                    signal_strengths['qbm'] = 0.5  # Positive (low risk)
            except Exception as e:
                logger.error(f"QBM signal generation failed: {e}")

        # Combine signals using weighted voting
        if not signals:
            return {
                'action': 'HOLD',
                'confidence': 0.0,
                'strength': 0.0,
                'reason': 'No signals generated'
            }

        # Convert signals to numeric values
        signal_values = {'BUY': 1, 'HOLD': 0, 'SELL': -1}

        weighted_signal = 0.0
        total_weight = 0.0

        for model_name in ['qnn', 'qsvm', 'qbm']:
            if model_name in signals:
                weight = getattr(self.config, f'{model_name}_weight')
                strength = signal_strengths.get(model_name, 0.5)
                signal_value = signal_values[signals[model_name]]

                weighted_signal += signal_value * weight * strength
                total_weight += weight * strength

        if total_weight > 0:
            weighted_signal /= total_weight
        else:
            # Fallback: simple majority vote
            buy_votes = sum(1 for s in signals.values() if s == 'BUY')
            sell_votes = sum(1 for s in signals.values() if s == 'SELL')

            if buy_votes > sell_votes:
                weighted_signal = 0.5
            elif sell_votes > buy_votes:
                weighted_signal = -0.5
            else:
                weighted_signal = 0.0

        # Convert to final action
        if weighted_signal > self.config.min_confidence:
            action = 'BUY'
            strength = weighted_signal
        elif weighted_signal < -self.config.min_confidence:
            action = 'SELL'
            strength = abs(weighted_signal)
        else:
            action = 'HOLD'
            strength = 0.0

        # Calculate confidence based on agreement
        if len(signals) > 1:
            unique_actions = len(set(signals.values()))
            agreement = 1.0 - (unique_actions - 1) / 2.0  # 1.0 if all agree, 0.5 if split
            confidence = agreement * min(1.0, total_weight)
        else:
            confidence = 0.5  # Low confidence if only one model

        return {
            'action': action,
            'confidence': confidence,
            'strength': strength,
            'weighted_signal': weighted_signal,
            'individual_signals': signals,
            'individual_strengths': signal_strengths,
            'method': 'ENSEMBLE_QUANTUM_ML',
            'reason': f'Ensemble decision based on {len(signals)} models'
        }

    def evaluate_ensemble(self, test_data: pd.DataFrame) -> Dict[str, Any]:
        """
        Evaluate ensemble performance on test data

        Args:
            test_data: Test dataset

        Returns:
            Performance metrics
        """
        logger.info("\n📊 Evaluating Ensemble Performance...")

        X_test = self.prepare_features(test_data)
        y_test = test_data['close'].values

        # Make predictions
        predictions = []
        for i in range(50, len(X_test)):
            current_features = X_test[i-50:i]
            pred_result = self.predict_price(current_features.flatten())
            if 'prediction' in pred_result:
                predictions.append(pred_result['prediction'])
            else:
                predictions.append(y_test[i])

        predictions = np.array(predictions)
        y_test_aligned = y_test[50:]

        # Calculate metrics
        mse = np.mean((predictions - y_test_aligned) ** 2)
        mae = np.mean(np.abs(predictions - y_test_aligned))

        # Directional accuracy
        y_direction = np.sign(np.diff(y_test_aligned))
        pred_direction = np.sign(np.diff(predictions))
        directional_accuracy = np.mean(y_direction == pred_direction) if len(y_direction) > 0 else 0

        # R-squared
        ss_res = np.sum((y_test_aligned - predictions) ** 2)
        ss_tot = np.sum((y_test_aligned - np.mean(y_test_aligned)) ** 2)
        r2 = 1 - (ss_res / ss_tot) if ss_tot > 0 else 0

        metrics = {
            'mse': mse,
            'mae': mae,
            'r2_score': r2,
            'directional_accuracy': directional_accuracy,
            'num_predictions': len(predictions)
        }

        logger.info(f"\n📊 Ensemble Performance Metrics:")
        logger.info(f"  Mean Squared Error: {mse:.4f}")
        logger.info(f"  Mean Absolute Error: {mae:.4f}")
        logger.info(f"  R² Score: {r2:.4f}")
        logger.info(f"  Directional Accuracy: {directional_accuracy:.2%}")

        return metrics


# Factory function
def create_ensemble_predictor(
    qnn_weight: float = 0.4,
    qsvm_weight: float = 0.4,
    qbm_weight: float = 0.2
) -> EnsembleQuantumPredictor:
    """Create Ensemble Quantum Predictor with default configuration"""
    config = EnsembleConfig(
        qnn_weight=qnn_weight,
        qsvm_weight=qsvm_weight,
        qbm_weight=qbm_weight
    )
    return EnsembleQuantumPredictor(config)


# Testing and demonstration
if __name__ == "__main__":
    print("🚀 Ensemble Quantum ML Predictor - Testing")
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

    # Create ensemble
    print("\n🔬 Creating Ensemble Quantum Predictor...")
    ensemble = create_ensemble_predictor(
        qnn_weight=0.4,
        qsvm_weight=0.4,
        qbm_weight=0.2
    )

    # Train
    print("\n🎓 Training ensemble...")
    training_history = ensemble.train(data)

    # Generate trading signal
    print("\n🔮 Generating trading signal...")
    signal = ensemble.generate_trading_signal(data)

    print(f"\n📊 Trading Signal:")
    print(f"  Action: {signal['action']}")
    print(f"  Confidence: {signal['confidence']:.2%}")
    print(f"  Strength: {signal['strength']:.3f}")
    print(f"  Individual Signals: {signal['individual_signals']}")

    # Evaluate on test set
    print("\n📈 Evaluating on test set...")
    test_data = data.iloc[400:]  # Use last 100 days for testing
    metrics = ensemble.evaluate_ensemble(test_data)

    print(f"\n📊 Test Results:")
    print(f"  Mean Squared Error: {metrics['mse']:.4f}")
    print(f"  Mean Absolute Error: {metrics['mae']:.4f}")
    print(f"  R² Score: {metrics['r2_score']:.4f}")
    print(f"  Directional Accuracy: {metrics['directional_accuracy']:.2%}")

    print("\n✅ Ensemble Quantum ML Predictor test completed!")
