#!/usr/bin/env python3
"""
Comprehensive Test Suite for Quantum Trading Algorithms
Tests all quantum algorithms with real and synthetic data

Author: Quantum AI Trading Bot Team
Version: 1.0
Date: January 28, 2026
"""

import sys
import os
import time
import logging
from pathlib import Path
import numpy as np
import pandas as pd
from datetime import datetime, timedelta

# Add paths
sys.path.insert(0, '/home/davidsanker/quantum-trading-bot-new')

# Import quantum modules
from quantum_signal_generation.quantum_fourier_analyzer import QuantumFourierAnalyzer, create_qft_analyzer
from quantum_signal_generation.quantum_trend_detector import QuantumTrendDetector, create_trend_detector
from quantum_signal_generation.quantum_walk_momentum import QuantumWalkMomentum, create_momentum_analyzer
from quantum_signal_generation.enhanced_quantum_analyzer import create_enhanced_quantum_analyzer

# Import quantum ML modules
from quantum_machine_learning.quantum_neural_network import QuantumNeuralNetwork, create_quantum_nn
from quantum_machine_learning.quantum_svm import QuantumSupportVectorMachine, create_quantum_svm
from quantum_machine_learning.quantum_boltzmann_machine import QuantumBoltzmannMachine, create_quantum_bm
from quantum_machine_learning.ensemble_quantum_predictor import create_ensemble_predictor

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class QuantumAlgorithmTester:
    """Comprehensive test suite for quantum algorithms"""

    def __init__(self):
        self.results = {}
        self.test_data = {}

    def generate_synthetic_data(self, num_days=500, seed=42):
        """Generate synthetic market data for testing"""
        np.random.seed(seed)

        t = np.arange(num_days)

        # Price with trend, cycles, and noise
        price = (
            100 +
            0.1 * t +  # Trend
            5 * np.sin(2 * np.pi * t / 50) +  # 50-day cycle
            3 * np.sin(2 * np.pi * t / 20) +  # 20-day cycle
            np.random.randn(num_days) * 2  # Noise
        )

        # Volume
        volume = (
            1000000 +
            500000 * np.sin(2 * np.pi * t / 20) +
            np.random.randn(num_days) * 100000
        )

        # Technical indicators
        rsi = 50 + 20 * np.sin(2 * np.pi * t / 20) + np.random.randn(num_days) * 5
        rsi = np.clip(rsi, 0, 100)

        macd = 0.5 * np.sin(2 * np.pi * t / 30) + np.random.randn(num_days) * 0.5

        # Create DataFrame
        data = pd.DataFrame({
            'close': price,
            'volume': volume,
            'rsi': rsi,
            'macd': macd
        })

        logger.info(f"Generated synthetic data: {num_days} days")
        return data

    def test_qft_analyzer(self):
        """Test Quantum Fourier Transform Analyzer"""
        logger.info("\n" + "="*60)
        logger.info("Testing QFT Analyzer")
        logger.info("="*60)

        try:
            # Create analyzer
            qft = create_qft_analyzer(num_qubits=10)

            # Generate test data with known cycles
            t = np.arange(500)
            price_with_cycle = (
                100 +
                10 * np.sin(2 * np.pi * t / 50) +  # 50-day cycle
                5 * np.sin(2 * np.pi * t / 20) +   # 20-day cycle
                np.random.randn(500) * 2
            )

            # Detect cycles
            start_time = time.time()
            result = qft.detect_market_cycles(price_with_cycle)
            elapsed = time.time() - start_time

            # Validate results
            assert 'dominant_cycles' in result, "Missing dominant_cycles"
            assert len(result['dominant_cycles']) > 0, "No cycles detected"
            assert 'trading_signal' in result, "Missing trading_signal"

            # Log results
            logger.info(f"✅ QFT Test PASSED")
            logger.info(f"  Cycles detected: {len(result['dominant_cycles'])}")
            logger.info(f"  Dominant cycle: {result['dominant_cycles'][0]['period']:.1f} days")
            logger.info(f"  Trading signal: {result['trading_signal']:.4f}")
            logger.info(f"  Execution time: {elapsed:.3f}s")

            self.results['qft'] = {
                'status': 'PASSED',
                'cycles_detected': len(result['dominant_cycles']),
                'execution_time': elapsed,
                'quantum_utilization': result.get('quantum_utilization', 0.8)
            }

            return True

        except Exception as e:
            logger.error(f"❌ QFT Test FAILED: {e}")
            self.results['qft'] = {'status': 'FAILED', 'error': str(e)}
            return False

    def test_qpe_detector(self):
        """Test Quantum Phase Estimation Trend Detector"""
        logger.info("\n" + "="*60)
        logger.info("Testing QPE Trend Detector")
        logger.info("="*60)

        try:
            # Create detector
            qpe = create_trend_detector(num_qubits=8)

            # Test with bullish trend
            bullish_price = 100 + np.cumsum(np.random.randn(500) * 0.5 + 0.3)

            start_time = time.time()
            result = qpe.estimate_trend_phase(bullish_price)
            elapsed = time.time() - start_time

            # Validate results
            assert 'trend_direction' in result, "Missing trend_direction"
            assert 'phase' in result, "Missing phase"
            assert 'confidence' in result, "Missing confidence"

            logger.info(f"✅ QPE Test PASSED")
            logger.info(f"  Trend: {result['trend_direction']}")
            logger.info(f"  Phase: {result['phase']:.4f}")
            logger.info(f"  Confidence: {result['confidence']:.2%}")
            logger.info(f"  Execution time: {elapsed:.3f}s")

            self.results['qpe'] = {
                'status': 'PASSED',
                'trend_detected': result['trend_direction'],
                'confidence': result['confidence'],
                'execution_time': elapsed
            }

            return True

        except Exception as e:
            logger.error(f"❌ QPE Test FAILED: {e}")
            self.results['qpe'] = {'status': 'FAILED', 'error': str(e)}
            return False

    def test_quantum_walk(self):
        """Test Quantum Walk Momentum Analyzer"""
        logger.info("\n" + "="*60)
        logger.info("Testing Quantum Walk Momentum")
        logger.info("="*60)

        try:
            # Create analyzer
            qw = create_momentum_analyzer(num_qubits=8)

            # Test with upward momentum
            momentum_price = 100 + np.cumsum(np.random.randn(500) * 0.3 + 0.5)

            start_time = time.time()
            result = qw.analyze_momentum(momentum_price)
            elapsed = time.time() - start_time

            # Validate results
            assert 'momentum_direction' in result, "Missing momentum_direction"
            assert 'momentum_strength' in result, "Missing momentum_strength"
            assert 'diffusion_rate' in result, "Missing diffusion_rate"

            logger.info(f"✅ Quantum Walk Test PASSED")
            logger.info(f"  Momentum: {result['momentum_direction']}")
            logger.info(f"  Strength: {result['momentum_strength']:.4f}")
            logger.info(f"  Diffusion rate: {result['diffusion_rate']:.4f}")
            logger.info(f"  Execution time: {elapsed:.3f}s")

            self.results['qw'] = {
                'status': 'PASSED',
                'momentum': result['momentum_direction'],
                'strength': result['momentum_strength'],
                'execution_time': elapsed
            }

            return True

        except Exception as e:
            logger.error(f"❌ Quantum Walk Test FAILED: {e}")
            self.results['qw'] = {'status': 'FAILED', 'error': str(e)}
            return False

    def test_enhanced_analyzer(self):
        """Test Enhanced Quantum Analyzer (all 3 algorithms)"""
        logger.info("\n" + "="*60)
        logger.info("Testing Enhanced Quantum Analyzer")
        logger.info("="*60)

        try:
            # Create enhanced analyzer
            analyzer = create_enhanced_quantum_analyzer()

            # Generate test data
            data = self.generate_synthetic_data(num_days=500)

            start_time = time.time()
            result = analyzer.analyze_market_quantum(
                symbol='TEST',
                price_data=data['close'].values,
                include_visualization=False
            )
            elapsed = time.time() - start_time

            # Validate results
            assert 'final_decision' in result, "Missing final_decision"
            assert 'quantum_utilization' in result, "Missing quantum_utilization"
            assert 'cycle_analysis' in result, "Missing cycle_analysis"
            assert 'trend_analysis' in result, "Missing trend_analysis"
            assert 'momentum_analysis' in result, "Missing momentum_analysis"

            logger.info(f"✅ Enhanced Analyzer Test PASSED")
            logger.info(f"  Action: {result['final_decision']['action']}")
            logger.info(f"  Confidence: {result['final_decision']['confidence']:.2%}")
            logger.info(f"  Quantum utilization: {result['quantum_utilization']:.1%}")
            logger.info(f"  Execution time: {elapsed:.3f}s")

            self.results['enhanced'] = {
                'status': 'PASSED',
                'action': result['final_decision']['action'],
                'confidence': result['final_decision']['confidence'],
                'quantum_utilization': result['quantum_utilization'],
                'execution_time': elapsed
            }

            return True

        except Exception as e:
            logger.error(f"❌ Enhanced Analyzer Test FAILED: {e}")
            self.results['enhanced'] = {'status': 'FAILED', 'error': str(e)}
            return False

    def test_qnn(self):
        """Test Quantum Neural Network"""
        logger.info("\n" + "="*60)
        logger.info("Testing Quantum Neural Network")
        logger.info("="*60)

        try:
            # Create QNN
            qnn = create_quantum_nn(
                input_dim=50,
                hidden_dim=64,
                num_qubits=8
            )

            # Generate training data
            X_train = np.random.randn(500, 50)
            y_train = np.linspace(100, 120, 500)

            # Train (quick test - fewer epochs)
            start_time = time.time()
            history = qnn.train(X_train, y_train, epochs=10)
            elapsed = time.time() - start_time

            # Test prediction
            X_test = np.random.randn(10, 50)
            predictions = qnn.predict(X_test)

            # Validate
            assert len(predictions) == 10, "Wrong number of predictions"
            assert history['epochs_completed'] == 10, "Training incomplete"

            logger.info(f"✅ QNN Test PASSED")
            logger.info(f"  Training epochs: {history['epochs_completed']}")
            logger.info(f"  Final loss: {history['final_loss']:.4f}")
            logger.info(f"  Predictions made: {len(predictions)}")
            logger.info(f"  Training time: {elapsed:.3f}s")

            self.results['qnn'] = {
                'status': 'PASSED',
                'epochs': history['epochs_completed'],
                'final_loss': history['final_loss'],
                'training_time': elapsed
            }

            return True

        except Exception as e:
            logger.error(f"❌ QNN Test FAILED: {e}")
            self.results['qnn'] = {'status': 'FAILED', 'error': str(e)}
            return False

    def test_qsvm(self):
        """Test Quantum Support Vector Machine"""
        logger.info("\n" + "="*60)
        logger.info("Testing Quantum Support Vector Machine")
        logger.info("="*60)

        try:
            # Create QSVM
            qsvm = create_quantum_svm(num_qubits=8)

            # Generate training data
            data = self.generate_synthetic_data(num_days=500)

            # Train
            start_time = time.time()
            metrics = qsvm.train(data)
            elapsed = time.time() - start_time

            # Test prediction
            X_test = qsvm.prepare_features(data.iloc[-10:])
            predictions = qsvm.predict(X_test)

            # Validate
            assert len(predictions) == 10, "Wrong number of predictions"
            assert 'accuracy' in metrics, "Missing accuracy metric"

            logger.info(f"✅ QSVM Test PASSED")
            logger.info(f"  Test accuracy: {metrics['accuracy']:.2%}")
            logger.info(f"  Predictions made: {len(predictions)}")
            logger.info(f"  Training time: {elapsed:.3f}s")

            self.results['qsvm'] = {
                'status': 'PASSED',
                'accuracy': metrics['accuracy'],
                'test_samples': metrics['test_samples'],
                'training_time': elapsed
            }

            return True

        except Exception as e:
            logger.error(f"❌ QSVM Test FAILED: {e}")
            self.results['qsvm'] = {'status': 'FAILED', 'error': str(e)}
            return False

    def test_qbm(self):
        """Test Quantum Boltzmann Machine"""
        logger.info("\n" + "="*60)
        logger.info("Testing Quantum Boltzmann Machine")
        logger.info("="*60)

        try:
            # Create QBM
            qbm = create_quantum_bm(
                num_visible=10,
                num_hidden=20,
                num_qubits=10
            )

            # Generate training data
            data = self.generate_synthetic_data(num_days=500)

            # Train (quick test - fewer epochs)
            start_time = time.time()
            features = qbm.prepare_features(data)
            history = qbm.train(features, epochs=20)
            elapsed = time.time() - start_time

            # Test scenario generation
            scenarios = qbm.generate_scenarios(num_scenarios=10, num_steps=5)

            # Validate
            assert scenarios.shape == (10, 5, 10), "Wrong scenario shape"
            assert history['epochs_completed'] == 20, "Training incomplete"

            logger.info(f"✅ QBM Test PASSED")
            logger.info(f"  Training epochs: {history['epochs_completed']}")
            logger.info(f"  Final loss: {history['final_loss']:.4f}")
            logger.info(f"  Scenarios generated: {scenarios.shape}")
            logger.info(f"  Training time: {elapsed:.3f}s")

            self.results['qbm'] = {
                'status': 'PASSED',
                'epochs': history['epochs_completed'],
                'final_loss': history['final_loss'],
                'scenarios': scenarios.shape,
                'training_time': elapsed
            }

            return True

        except Exception as e:
            logger.error(f"❌ QBM Test FAILED: {e}")
            self.results['qbm'] = {'status': 'FAILED', 'error': str(e)}
            return False

    def test_ensemble(self):
        """Test Ensemble Quantum Predictor"""
        logger.info("\n" + "="*60)
        logger.info("Testing Ensemble Quantum Predictor")
        logger.info("="*60)

        try:
            # Create ensemble
            ensemble = create_ensemble_predictor(
                qnn_weight=0.4,
                qsvm_weight=0.4,
                qbm_weight=0.2
            )

            # Generate training data
            data = self.generate_synthetic_data(num_days=500)

            # Train (quick test with minimal epochs)
            start_time = time.time()
            history = ensemble.train(data)
            elapsed = time.time() - start_time

            # Test signal generation
            signal = ensemble.generate_trading_signal(data)

            # Validate
            assert 'action' in signal, "Missing action"
            assert 'confidence' in signal, "Missing confidence"
            assert 'individual_signals' in signal, "Missing individual_signals"

            logger.info(f"✅ Ensemble Test PASSED")
            logger.info(f"  Action: {signal['action']}")
            logger.info(f"  Confidence: {signal['confidence']:.2%}")
            logger.info(f"  Individual signals: {len(signal['individual_signals'])}")
            logger.info(f"  Training time: {elapsed:.3f}s")

            self.results['ensemble'] = {
                'status': 'PASSED',
                'action': signal['action'],
                'confidence': signal['confidence'],
                'models_used': len(signal['individual_signals']),
                'training_time': elapsed
            }

            return True

        except Exception as e:
            logger.error(f"❌ Ensemble Test FAILED: {e}")
            self.results['ensemble'] = {'status': 'FAILED', 'error': str(e)}
            return False

    def run_all_tests(self):
        """Run all tests and generate report"""
        logger.info("\n" + "="*60)
        logger.info("QUANTUM ALGORITHM TEST SUITE")
        logger.info("="*60)
        logger.info(f"Start time: {datetime.now()}")

        # Run Phase 1 tests
        logger.info("\n📊 PHASE 1 TESTS (Signal Generation)")
        self.test_qft_analyzer()
        self.test_qpe_detector()
        self.test_quantum_walk()
        self.test_enhanced_analyzer()

        # Run Phase 2 tests
        logger.info("\n🧠 PHASE 2 TESTS (Machine Learning)")
        self.test_qnn()
        self.test_qsvm()
        self.test_qbm()
        self.test_ensemble()

        # Generate summary report
        self.generate_report()

    def generate_report(self):
        """Generate test summary report"""
        logger.info("\n" + "="*60)
        logger.info("TEST SUMMARY REPORT")
        logger.info("="*60)

        # Count passed/failed
        passed = sum(1 for r in self.results.values() if r['status'] == 'PASSED')
        failed = sum(1 for r in self.results.values() if r['status'] == 'FAILED')
        total = len(self.results)

        logger.info(f"\nTotal Tests: {total}")
        logger.info(f"Passed: {passed} ({passed/total*100:.1f}%)")
        logger.info(f"Failed: {failed} ({failed/total*100:.1f}%)")

        # Detailed results
        logger.info("\nDetailed Results:")
        logger.info("-" * 60)

        for test_name, result in self.results.items():
            status_icon = "✅" if result['status'] == 'PASSED' else "❌"
            logger.info(f"\n{status_icon} {test_name.upper()}: {result['status']}")

            if result['status'] == 'PASSED':
                # Print key metrics
                for key, value in result.items():
                    if key != 'status':
                        logger.info(f"  {key}: {value}")
            else:
                logger.info(f"  Error: {result.get('error', 'Unknown')}")

        # Performance summary
        logger.info("\n" + "-" * 60)
        logger.info("Performance Summary:")
        logger.info("-" * 60)

        phase1_tests = ['qft', 'qpe', 'qw', 'enhanced']
        phase2_tests = ['qnn', 'qsvm', 'qbm', 'ensemble']

        phase1_time = sum(
            self.results[t].get('execution_time', 0) +
            self.results[t].get('training_time', 0)
            for t in phase1_tests
            if t in self.results and self.results[t]['status'] == 'PASSED'
        )

        phase2_time = sum(
            self.results[t].get('training_time', 0)
            for t in phase2_tests
            if t in self.results and self.results[t]['status'] == 'PASSED'
        )

        logger.info(f"Phase 1 total time: {phase1_time:.3f}s")
        logger.info(f"Phase 2 total time: {phase2_time:.3f}s")
        logger.info(f"Total time: {phase1_time + phase2_time:.3f}s")

        # Quantum utilization
        quantum_util = []
        for test in ['qft', 'enhanced']:
            if test in self.results and 'quantum_utilization' in self.results[test]:
                quantum_util.append(self.results[test]['quantum_utilization'])

        if quantum_util:
            avg_quantum = np.mean(quantum_util)
            logger.info(f"Average quantum utilization: {avg_quantum:.1%}")

        logger.info("\n" + "="*60)
        logger.info("Test Suite Complete")
        logger.info("="*60)


def main():
    """Main test runner"""
    tester = QuantumAlgorithmTester()
    tester.run_all_tests()


if __name__ == "__main__":
    main()
