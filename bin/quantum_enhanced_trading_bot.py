#!/usr/bin/env python3
"""
Enhanced Quantum Trading Bot with Quantum Signal Generation
Integrates Phase 1 quantum algorithms into the main trading bot

Author: Quantum AI Trading Bot Team
Version: 2.0 (Quantum Enhanced)
Date: January 28, 2026
"""

import os
import sys
import time
import logging
import warnings
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Optional
import pandas as pd
import numpy as np
from ib_insync import IB, Stock, MarketOrder, LimitOrder, util
import yfinance as yf

# Add quantum module path
sys.path.insert(0, '/home/davidsanker/quantum-trading-bot-new')
from quantum_signal_generation.enhanced_quantum_analyzer import create_enhanced_quantum_analyzer

# Suppress warnings
warnings.filterwarnings('ignore')

# Configuration
IB_HOST = "127.0.0.1"
IB_PORT = 4002
CLIENT_ID = 401  # QUANTUM bot gets priority
UPDATE_INTERVAL = 120  # 2 minute cycles

# Trading universe - TOP 20 for quantum testing
TRADING_SYMBOLS = [
    'SPY', 'QQQ', 'IWM', 'DIA', 'VTI',
    'AAPL', 'MSFT', 'GOOGL', 'AMZN', 'TSLA',
    'NVDA', 'META', 'BRK.B', 'LLY', 'V',
    'JPM', 'MA', 'HD', 'PG', 'CVX'
]

logger = logging.getLogger(__name__)


class QuantumEnhancedTradingBot:
    """
    Quantum Enhanced Trading Bot

    Replaces classical technical analysis with quantum algorithms:
    - Quantum Fourier Transform (QFT) for cycle detection
    - Quantum Phase Estimation (QPE) for trend analysis
    - Quantum Walk (QW) for momentum prediction
    """

    def __init__(self):
        self.ib = None
        self.account = None
        self.quantum_analyzer = None
        self.positions = {}
        self.last_update = None

        # Performance tracking
        self.quantum_decisions = []
        self.classical_decisions = []

        logger.info("🚀 Quantum Enhanced Trading Bot v2.0")
        logger.info(f"   Trading {len(TRADING_SYMBOLS)} symbols")
        logger.info(f"   Quantum utilization: 80% (Phase 1)")

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
        """Initialize enhanced quantum signal analyzer"""
        logger.info("⚛️  Initializing Quantum Signal Analyzer...")
        self.quantum_analyzer = create_enhanced_quantum_analyzer()
        logger.info("✅ Quantum Analyzer ready")

    def get_market_data(self, symbol: str, period: str = '6mo') -> pd.DataFrame:
        """Fetch comprehensive market data"""
        try:
            ticker = yf.Ticker(symbol)
            df = ticker.history(period=period)

            if df.empty:
                logger.warning(f"No yfinance data for {symbol}")
                return pd.DataFrame()

            # Rename columns
            df.columns = [col.lower().replace(' ', '_') for col in df.columns]
            df = df.rename(columns={'adj_close': 'close'})

            logger.info(f"📊 Retrieved {len(df)} days of data for {symbol}")
            return df

        except Exception as e:
            logger.error(f"Error fetching data for {symbol}: {e}")
            return pd.DataFrame()

    def quantum_analyze(self, symbol: str) -> Dict:
        """
        Enhanced quantum analysis using Phase 1 algorithms

        REPLACES classical technical analysis with quantum algorithms
        """
        logger.info(f"\n⚛️  ENHANCED QUANTUM Analysis: {symbol}")

        # Get market data
        data = self.get_market_data(symbol, period='6mo')

        if data.empty or len(data) < 50:
            return {
                'symbol': symbol,
                'action': 'HOLD',
                'confidence': 0.0,
                'method': 'INSUFFICIENT_DATA'
            }

        try:
            # Use enhanced quantum analyzer
            result = self.quantum_analyzer.analyze_market_quantum(
                symbol=symbol,
                price_data=data['close'].values,
                include_visualization=False
            )

            # Extract final decision
            final_decision = result['final_decision']

            # Add metadata
            final_decision['symbol'] = symbol
            final_decision['quantum_utilization'] = result['quantum_utilization']
            final_decision['data_points'] = len(data)
            final_decision['method'] = 'ENHANCED_QUANTUM_V1'

            # Log summary
            logger.info(f"  🎯 Action: {final_decision['action']}")
            logger.info(f"  💪 Confidence: {final_decision['confidence']:.1%}")
            logger.info(f"  📈 Quantum Score: {final_decision['quantum_score']:.4f}")
            logger.info(f"  ⚛️  Quantum Utilization: {result['quantum_utilization']:.1%}")

            # Track decision
            self.quantum_decisions.append({
                'symbol': symbol,
                'timestamp': datetime.now(),
                'action': final_decision['action'],
                'confidence': final_decision['confidence'],
                'quantum_score': final_decision['quantum_score']
            })

            return final_decision

        except Exception as e:
            logger.error(f"❌ Quantum analysis failed for {symbol}: {e}")
            return {
                'symbol': symbol,
                'action': 'HOLD',
                'confidence': 0.0,
                'method': 'ERROR',
                'error': str(e)
            }

    def execute_trades(self, symbols: List[str]):
        """Analyze and execute trades for all symbols"""
        logger.info(f"\n{'='*60}")
        logger.info(f"🚀 Starting Quantum Trading Cycle")
        logger.info(f"{'='*60}")

        buy_signals = []
        sell_signals = []
        hold_signals = []

        for symbol in symbols:
            # Get quantum analysis
            decision = self.quantum_analyze(symbol)

            action = decision['action']
            confidence = decision['confidence']

            # Categorize signals
            if action == 'BUY' and confidence > 0.6:
                buy_signals.append((symbol, confidence))
            elif action == 'SELL' and confidence > 0.6:
                sell_signals.append((symbol, confidence))
            else:
                hold_signals.append((symbol, confidence))

        # Summary
        logger.info(f"\n{'='*60}")
        logger.info(f"📊 Quantum Trading Summary")
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

    def run_quantum_trading_cycle(self):
        """Run one complete quantum trading cycle"""
        try:
            # Check IB connection
            if not self.ib or not self.ib.isConnected():
                if not self.connect_to_ib():
                    logger.error("Failed to connect to IB Gateway")
                    return

            # Initialize quantum analyzer
            if not self.quantum_analyzer:
                self.initialize_quantum_analyzer()

            # Execute trading cycle
            self.execute_trades(TRADING_SYMBOLS)

            # Calculate performance stats
            self._calculate_performance_stats()

        except Exception as e:
            logger.error(f"❌ Error in trading cycle: {e}")

    def _calculate_performance_stats(self):
        """Calculate quantum bot performance statistics"""
        if not self.quantum_decisions:
            return

        total_decisions = len(self.quantum_decisions)
        buy_decisions = sum(1 for d in self.quantum_decisions if d['action'] == 'BUY')
        sell_decisions = sum(1 for d in self.quantum_decisions if d['action'] == 'SELL')
        hold_decisions = sum(1 for d in self.quantum_decisions if d['action'] == 'HOLD')

        avg_confidence = np.mean([d['confidence'] for d in self.quantum_decisions])
        avg_quantum_score = np.mean([d['quantum_score'] for d in self.quantum_decisions])

        logger.info(f"\n📈 Quantum Bot Performance:")
        logger.info(f"  Total Decisions: {total_decisions}")
        logger.info(f"  BUY: {buy_decisions} ({buy_decisions/total_decisions*100:.1f}%)")
        logger.info(f"  SELL: {sell_decisions} ({sell_decisions/total_decisions*100:.1f}%)")
        logger.info(f"  HOLD: {hold_decisions} ({hold_decisions/total_decisions*100:.1f}%)")
        logger.info(f"  Avg Confidence: {avg_confidence:.1%}")
        logger.info(f"  Avg Quantum Score: {avg_quantum_score:.4f}")

    def run_continuous(self):
        """Run continuous trading bot"""
        logger.info("🚀 Starting Quantum Enhanced Trading Bot...")
        logger.info(f"   Update interval: {UPDATE_INTERVAL} seconds")
        logger.info(f"   Symbols: {len(TRADING_SYMBOLS)}")
        logger.info(f"   Press Ctrl+C to stop\n")

        try:
            while True:
                self.run_quantum_trading_cycle()

                # Wait for next cycle
                logger.info(f"\n⏰ Next cycle in {UPDATE_INTERVAL} seconds...")
                time.sleep(UPDATE_INTERVAL)

        except KeyboardInterrupt:
            logger.info("\n🛑 Bot stopped by user")
        except Exception as e:
            logger.error(f"❌ Fatal error: {e}")
            raise


def main():
    """Main entry point"""
    # Setup logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler('/home/davidsanker/logs/quantum_trading_bot.log'),
            logging.StreamHandler()
        ]
    )

    # Create bot
    bot = QuantumEnhancedTradingBot()

    # Run continuous
    bot.run_continuous()


if __name__ == "__main__":
    main()
