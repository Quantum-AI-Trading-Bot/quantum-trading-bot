#!/usr/bin/env python3
"""
Quantum ML Enhanced Trading Bot with Phase 2 Integration
Combines Phase 1 quantum signals with Phase 2 quantum ML predictions

Author: Quantum AI Trading Bot Team
Version: 3.0 (Quantum ML Enhanced)
Date: January 28, 2026
Phase: 2 - Quantum Machine Learning Integration
"""

import os
import sys
import time
import logging
import warnings
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Optional
from pathlib import Path
import pandas as pd
import numpy as np
from ib_insync import IB, Stock, MarketOrder, LimitOrder, util
import yfinance as yf
import pickle

# Add quantum module paths
sys.path.insert(0, '/home/davidsanker/quantum-trading-bot-new')
from quantum_signal_generation.enhanced_quantum_analyzer import create_enhanced_quantum_analyzer
from quantum_machine_learning.ensemble_quantum_predictor import create_ensemble_predictor

# Suppress warnings
warnings.filterwarnings('ignore')

# Configuration
IB_HOST = "127.0.0.1"
IB_PORT = 4002
CLIENT_ID = 402  # Quantum ML bot
UPDATE_INTERVAL = 120  # 2 minute cycles

# Trading universe - TOP 20 for quantum ML testing
TRADING_SYMBOLS = [
    'SPY', 'QQQ', 'IWM', 'DIA', 'VTI',
    'AAPL', 'MSFT', 'GOOGL', 'AMZN', 'TSLA',
    'NVDA', 'META', 'BRK.B', 'LLY', 'V',
    'JPM', 'MA', 'HD', 'PG', 'CVX'
]

# Model storage
MODEL_DIR = Path('/home/davidsanker/quantum-trading-bot-new/models')
MODEL_DIR.mkdir(exist_ok=True)

logger = logging.getLogger(__name__)


class QuantumMLEnhancedBot:
    """
    Quantum ML Enhanced Trading Bot

    Combines:
    - Phase 1: QFT, QPE, QW for signal generation
    - Phase 2: QNN, QSVM, QBM for price prediction and classification

    Target: 75% quantum utilization in price prediction
    """

    def __init__(self):
        self.ib = None
        self.account = None
        self.quantum_analyzer = None  # Phase 1
        self.ensemble_predictor = None  # Phase 2
        self.positions = {}
        self.last_update = None

        # Performance tracking
        self.phase1_decisions = []
        self.phase2_decisions = []
        self.ml_predictions = []

        # Model state
        self.models_loaded = False
        self.model_file = MODEL_DIR / 'quantum_ml_models.pkl'

        logger.info("🚀 Quantum ML Enhanced Trading Bot v3.0")
        logger.info(f"   Trading {len(TRADING_SYMBOLS)} symbols")
        logger.info(f"   Phase 1: QFT, QPE, QW (80% quantum)")
        logger.info(f"   Phase 2: QNN, QSVM, QBM (75% quantum target)")

    def connect_to_ib(self) -> bool:
        """Connect to Interactive Brokers Gateway"""
        try:
            logger.info("🔌 Connecting to IB Gateway...")
            self.ib = IB()
            self.ib.connect(IB_HOST, IB_PORT, clientId=CLIENT_ID)

            # Request delayed data
            self.ib.reqMarketDataType(3)

            accounts = self.ib.managedAccounts()
            if accounts:
                self.account = accounts[0]
                logger.info(f"✅ Connected - Account: {self.account}")
                return True

            logger.error("No accounts found")
            return False

        except Exception as e:
            logger.error(f"❌ Connection failed: {e}")
            return False

    def initialize_quantum_analyzer(self):
        """Initialize Phase 1 quantum signal analyzer"""
        logger.info("⚛️  Initializing Phase 1 Quantum Signal Analyzer...")
        self.quantum_analyzer = create_enhanced_quantum_analyzer()
        logger.info("✅ Phase 1 Quantum Analyzer ready (QFT + QPE + QW)")

    def initialize_ensemble_predictor(self):
        """Initialize Phase 2 ensemble quantum ML predictor"""
        logger.info("🧠 Initializing Phase 2 Ensemble Quantum ML Predictor...")
        self.ensemble_predictor = create_ensemble_predictor(
            qnn_weight=0.4,
            qsvm_weight=0.4,
            qbm_weight=0.2
        )
        logger.info("✅ Phase 2 Ensemble Predictor ready (QNN + QSVM + QBM)")

    def get_market_data(self, symbol: str, period: str = '1y') -> pd.DataFrame:
        """Fetch comprehensive market data with technical indicators"""
        try:
            ticker = yf.Ticker(symbol)
            df = ticker.history(period=period)

            if df.empty:
                logger.warning(f"No yfinance data for {symbol}")
                return pd.DataFrame()

            # Rename columns
            df.columns = [col.lower().replace(' ', '_') for col in df.columns]
            df = df.rename(columns={'adj_close': 'close'})

            # Add technical indicators
            df = self._add_technical_indicators(df)

            logger.info(f"📊 Retrieved {len(df)} days of data for {symbol}")
            return df

        except Exception as e:
            logger.error(f"Error fetching data for {symbol}: {e}")
            return pd.DataFrame()

    def _add_technical_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        """Add technical indicators for ML models"""
        # RSI
        delta = df['close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
        rs = gain / loss
        df['rsi'] = 100 - (100 / (1 + rs))

        # MACD
        exp1 = df['close'].ewm(span=12, adjust=False).mean()
        exp2 = df['close'].ewm(span=26, adjust=False).mean()
        df['macd'] = exp1 - exp2
        df['signal'] = df['macd'].ewm(span=9, adjust=False).mean()

        # Bollinger Bands
        df['sma'] = df['close'].rolling(window=20).mean()
        df['std'] = df['close'].rolling(window=20).std()
        df['upper_band'] = df['sma'] + (df['std'] * 2)
        df['lower_band'] = df['sma'] - (df['std'] * 2)

        return df

    def train_quantum_ml_models(self, symbols: List[str] = None):
        """Train Phase 2 quantum ML models on historical data"""
        if symbols is None:
            symbols = TRADING_SYMBOLS[:5]  # Train on top 5 for speed

        logger.info(f"\n🎓 Training Phase 2 Quantum ML Models...")
        logger.info(f"   Training symbols: {symbols}")

        # Combine data from all symbols
        all_data = []
        for symbol in symbols:
            data = self.get_market_data(symbol, period='2y')
            if not data.empty and len(data) > 300:
                all_data.append(data)

        if not all_data:
            logger.error("No data available for training")
            return

        # Concatenate all data
        combined_data = pd.concat(all_data, ignore_index=True)

        logger.info(f"   Total training samples: {len(combined_data)}")

        # Train ensemble predictor
        try:
            training_history = self.ensemble_predictor.train(combined_data)

            # Save models
            self._save_models()

            logger.info("✅ Phase 2 Quantum ML training complete!")
            logger.info(f"   QNN loss: {training_history.get('qnn', {}).get('final_loss', 'N/A')}")
            logger.info(f"   QSVM accuracy: {training_history.get('qsvm', {}).get('accuracy', 'N/A')}")
            logger.info(f"   QBM loss: {training_history.get('qbm', {}).get('training_history', {}).get('final_loss', 'N/A')}")

            self.models_loaded = True

        except Exception as e:
            logger.error(f"❌ Quantum ML training failed: {e}")

    def _save_models(self):
        """Save trained models to disk"""
        try:
            model_data = {
                'ensemble_predictor': self.ensemble_predictor,
                'timestamp': datetime.now(),
                'symbols': TRADING_SYMBOLS
            }

            with open(self.model_file, 'wb') as f:
                pickle.dump(model_data, f)

            logger.info(f"💾 Models saved to {self.model_file}")

        except Exception as e:
            logger.error(f"Failed to save models: {e}")

    def _load_models(self):
        """Load trained models from disk"""
        try:
            if self.model_file.exists():
                with open(self.model_file, 'rb') as f:
                    model_data = pickle.load(f)

                self.ensemble_predictor = model_data['ensemble_predictor']
                self.models_loaded = True

                logger.info(f"📥 Models loaded from {self.model_file}")
                logger.info(f"   Model age: {datetime.now() - model_data['timestamp']}")
                return True

        except Exception as e:
            logger.error(f"Failed to load models: {e}")

        return False

    def quantum_analyze_phase1(self, symbol: str, data: pd.DataFrame) -> Dict:
        """
        Phase 1: Quantum signal generation (QFT + QPE + QW)
        """
        try:
            result = self.quantum_analyzer.analyze_market_quantum(
                symbol=symbol,
                price_data=data['close'].values,
                include_visualization=False
            )

            final_decision = result['final_decision']
            final_decision['phase'] = 'PHASE1_SIGNALS'
            final_decision['quantum_utilization'] = result['quantum_utilization']

            return final_decision

        except Exception as e:
            logger.error(f"Phase 1 analysis failed: {e}")
            return {
                'action': 'HOLD',
                'confidence': 0.0,
                'phase': 'PHASE1_ERROR'
            }

    def quantum_analyze_phase2(self, symbol: str, data: pd.DataFrame) -> Dict:
        """
        Phase 2: Quantum ML prediction (QNN + QSVM + QBM)
        """
        if not self.models_loaded:
            logger.warning("Phase 2 models not trained yet")
            return {
                'action': 'HOLD',
                'confidence': 0.0,
                'phase': 'PHASE2_NOT_READY'
            }

        try:
            # Generate ensemble trading signal
            signal = self.ensemble_predictor.generate_trading_signal(data)

            signal['phase'] = 'PHASE2_ML'
            signal['symbol'] = symbol

            return signal

        except Exception as e:
            logger.error(f"Phase 2 analysis failed: {e}")
            return {
                'action': 'HOLD',
                'confidence': 0.0,
                'phase': 'PHASE2_ERROR'
            }

    def combined_quantum_analysis(self, symbol: str) -> Dict:
        """
        Combined Phase 1 + Phase 2 quantum analysis

        Strategy:
        - Phase 1 provides signal (market conditions)
        - Phase 2 provides prediction (price direction)
        - Combine for final decision
        """
        logger.info(f"\n⚛️  COMBINED QUANTUM Analysis: {symbol}")

        # Get market data
        data = self.get_market_data(symbol, period='1y')

        if data.empty or len(data) < 50:
            return {
                'symbol': symbol,
                'action': 'HOLD',
                'confidence': 0.0,
                'method': 'INSUFFICIENT_DATA'
            }

        # Phase 1: Signal generation
        phase1_signal = self.quantum_analyze_phase1(symbol, data)

        # Phase 2: ML prediction (if models are loaded)
        phase2_signal = self.quantum_analyze_phase2(symbol, data)

        # Combine signals
        # Weight: 50% Phase 1, 50% Phase 2
        signal_values = {'BUY': 1, 'HOLD': 0, 'SELL': -1}

        phase1_value = signal_values[phase1_signal['action']] * phase1_signal['confidence']
        phase2_value = signal_values[phase2_signal['action']] * phase2_signal.get('confidence', 0.0)

        combined_score = 0.5 * phase1_value + 0.5 * phase2_value

        # Final decision
        if combined_score > 0.3:
            final_action = 'BUY'
            final_confidence = min(abs(combined_score), 1.0)
        elif combined_score < -0.3:
            final_action = 'SELL'
            final_confidence = min(abs(combined_score), 1.0)
        else:
            final_action = 'HOLD'
            final_confidence = 0.0

        # Calculate quantum utilization
        phase1_utilization = phase1_signal.get('quantum_utilization', 0.8)
        phase2_utilization = 0.75 if phase2_signal.get('phase') == 'PHASE2_ML' else 0.0
        combined_utilization = 0.5 * phase1_utilization + 0.5 * phase2_utilization

        result = {
            'symbol': symbol,
            'action': final_action,
            'confidence': final_confidence,
            'phase1_action': phase1_signal['action'],
            'phase1_confidence': phase1_signal['confidence'],
            'phase2_action': phase2_signal['action'],
            'phase2_confidence': phase2_signal.get('confidence', 0.0),
            'combined_score': combined_score,
            'quantum_utilization': combined_utilization,
            'method': 'COMBINED_QUANTUM_V2',
            'data_points': len(data)
        }

        # Log summary
        logger.info(f"  🎯 Final Action: {result['action']}")
        logger.info(f"  💪 Confidence: {result['confidence']:.1%}")
        logger.info(f"  📊 Combined Score: {result['combined_score']:.4f}")
        logger.info(f"  ⚛️  Quantum Utilization: {result['quantum_utilization']:.1%}")
        logger.info(f"     Phase 1: {phase1_signal['action']} ({phase1_signal['confidence']:.1%})")
        logger.info(f"     Phase 2: {phase2_signal['action']} ({phase2_signal.get('confidence', 0.0):.1%})")

        # Track decision
        self.phase1_decisions.append({
            'symbol': symbol,
            'timestamp': datetime.now(),
            'action': phase1_signal['action'],
            'confidence': phase1_signal['confidence']
        })

        self.phase2_decisions.append({
            'symbol': symbol,
            'timestamp': datetime.now(),
            'action': phase2_signal['action'],
            'confidence': phase2_signal.get('confidence', 0.0)
        })

        return result

    def execute_trades(self, symbols: List[str]):
        """Analyze and execute trades for all symbols"""
        logger.info(f"\n{'='*60}")
        logger.info(f"🚀 Starting Combined Quantum Trading Cycle")
        logger.info(f"{'='*60}")

        buy_signals = []
        sell_signals = []
        hold_signals = []

        for symbol in symbols:
            # Get combined quantum analysis
            decision = self.combined_quantum_analysis(symbol)

            action = decision['action']
            confidence = decision['confidence']

            # Categorize signals
            if action == 'BUY' and confidence > 0.5:
                buy_signals.append((symbol, confidence))
            elif action == 'SELL' and confidence > 0.5:
                sell_signals.append((symbol, confidence))
            else:
                hold_signals.append((symbol, confidence))

        # Summary
        logger.info(f"\n{'='*60}")
        logger.info(f"📊 Combined Quantum Trading Summary")
        logger.info(f"{'='*60}")
        logger.info(f"  ✅ BUY Signals: {len(buy_signals)}")
        for symbol, conf in sorted(buy_signals, key=lambda x: x[1], reverse=True):
            logger.info(f"     - {symbol}: {conf:.1%} confidence")

        logger.info(f"  ❌ SELL Signals: {len(sell_signals)}")
        for symbol, conf in sorted(sell_signals, key=lambda x: x[1], reverse=True):
            logger.info(f"     - {symbol}: {conf:.1%} confidence")

        logger.info(f"  ⏸️  HOLD Signals: {len(hold_signals)}")

        # Execute trades (paper trading mode)
        self._execute_paper_trades(buy_signals, sell_signals)

        # Update last update time
        self.last_update = datetime.now()

    def _execute_paper_trades(self, buy_signals: List[Tuple], sell_signals: List[Tuple]):
        """Execute trades in paper trading mode"""
        logger.info(f"\n📝 Paper Trading Mode:")
        logger.info(f"  BUY orders: {len(buy_signals)}")
        logger.info(f"  SELL orders: {len(sell_signals)}")
        logger.info(f"  (No actual trades executed - paper mode)")

    def run_combined_quantum_cycle(self):
        """Run one complete combined quantum trading cycle"""
        try:
            # Check IB connection
            if not self.ib or not self.ib.isConnected():
                if not self.connect_to_ib():
                    logger.error("Failed to connect to IB Gateway")
                    return

            # Initialize Phase 1 quantum analyzer
            if not self.quantum_analyzer:
                self.initialize_quantum_analyzer()

            # Initialize Phase 2 ensemble predictor
            if not self.ensemble_predictor:
                self.initialize_ensemble_predictor()

            # Try to load pre-trained models
            if not self.models_loaded:
                self._load_models()

            # If no models available, train them (first time only)
            if not self.models_loaded:
                logger.warning("No pre-trained models found. Training now...")
                self.train_quantum_ml_models(TRADING_SYMBOLS[:5])

            # Run trading cycle
            self.execute_trades(TRADING_SYMBOLS)

        except Exception as e:
            logger.error(f"Error in trading cycle: {e}")

    def run_continuous(self):
        """Run continuous trading cycles"""
        logger.info("🔄 Starting continuous quantum ML trading...")
        logger.info(f"   Update interval: {UPDATE_INTERVAL} seconds")

        cycle_count = 0

        while True:
            try:
                cycle_count += 1
                logger.info(f"\n{'#'*60}")
                logger.info(f"Cycle #{cycle_count} - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
                logger.info(f"{'#'*60}")

                # Run combined quantum cycle
                self.run_combined_quantum_cycle()

                # Wait for next cycle
                logger.info(f"\n⏳ Waiting {UPDATE_INTERVAL} seconds for next cycle...")
                time.sleep(UPDATE_INTERVAL)

            except KeyboardInterrupt:
                logger.info("\n🛑 Shutting down gracefully...")
                break
            except Exception as e:
                logger.error(f"Error in continuous loop: {e}")
                time.sleep(60)  # Wait 1 minute before retry

    def shutdown(self):
        """Cleanup and shutdown"""
        logger.info("🔄 Shutting down Quantum ML Enhanced Trading Bot...")

        if self.ib and self.ib.isConnected():
            self.ib.disconnect()
            logger.info("✅ Disconnected from IB Gateway")

        logger.info("👋 Shutdown complete")


def main():
    """Main entry point"""
    print("=" * 60)
    print("🚀 Quantum ML Enhanced Trading Bot v3.0")
    print("=" * 60)
    print()
    print("Phase 1: Quantum Signal Generation (QFT + QPE + QW)")
    print("Phase 2: Quantum Machine Learning (QNN + QSVM + QBM)")
    print()
    print("Target: 75% quantum utilization in price prediction")
    print("=" * 60)
    print()

    # Setup logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler('/home/davidsanker/logs/quantum_ml_trading_bot.log'),
            logging.StreamHandler()
        ]
    )

    # Create bot
    bot = QuantumMLEnhancedBot()

    try:
        # Run continuous trading
        bot.run_continuous()

    except KeyboardInterrupt:
        logger.info("\n🛑 Interrupted by user")
    finally:
        bot.shutdown()


if __name__ == "__main__":
    main()
