#!/usr/bin/env python3
"""
Signal Generator - Classical Technical Analysis for QUANTUM Trading
Generates actionable BUY/SELL/HOLD decisions based on technical indicators

Generated: 2026-01-20 17:25:00 UTC
Purpose: Provide signal-based decision plans for VPA execution
"""

import os
import sys
import json
import argparse
import logging
from datetime import datetime
from typing import Dict, List, Tuple, Optional

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)
logger = logging.getLogger(__name__)

# Try to import yfinance
try:
    import yfinance as yf
    import pandas as pd
    import numpy as np
    LIBS_AVAILABLE = True
except ImportError as e:
    LIBS_AVAILABLE = False
    logger.error(f"Required libraries not available: {e}")


class TechnicalIndicators:
    """Calculate technical indicators from price data"""

    @staticmethod
    def calculate_rsi(df: pd.DataFrame, period: int = 14) -> pd.Series:
        """Calculate Relative Strength Index"""
        delta = df['Close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
        rs = gain / loss
        rsi = 100 - (100 / (1 + rs))
        return rsi

    @staticmethod
    def calculate_macd(df: pd.DataFrame) -> Tuple[pd.Series, pd.Series, pd.Series]:
        """Calculate MACD (Moving Average Convergence Divergence)"""
        exp1 = df['Close'].ewm(span=12, adjust=False).mean()
        exp2 = df['Close'].ewm(span=26, adjust=False).mean()
        macd = exp1 - exp2
        signal = macd.ewm(span=9, adjust=False).mean()
        histogram = macd - signal
        return macd, signal, histogram

    @staticmethod
    def calculate_bollinger_bands(df: pd.DataFrame, period: int = 20, std_dev: int = 2) -> Tuple[pd.Series, pd.Series, pd.Series]:
        """Calculate Bollinger Bands"""
        middle = df['Close'].rolling(window=period).mean()
        std = df['Close'].rolling(window=period).std()
        upper = middle + (std * std_dev)
        lower = middle - (std * std_dev)
        return upper, middle, lower

    @staticmethod
    def calculate_moving_averages(df: pd.DataFrame) -> Tuple[pd.Series, pd.Series]:
        """Calculate moving averages"""
        ma_short = df['Close'].rolling(window=10).mean()
        ma_long = df['Close'].rolling(window=50).mean()
        return ma_short, ma_long


class SignalScorer:
    """Score technical signals and generate trading decisions"""

    def __init__(self, min_confidence: float = 0.75):
        self.min_confidence = min_confidence

    def score_rsi(self, rsi: float) -> float:
        """Score RSI signal"""
        if rsi < 30:
            return 0.8  # Strong oversold
        elif rsi < 40:
            return 0.4  # Mild oversold
        elif rsi > 70:
            return -0.8  # Strong overbought
        elif rsi > 60:
            return -0.4  # Mild overbought
        else:
            return 0.0  # Neutral

    def score_macd(self, macd: float, signal: float) -> float:
        """Score MACD signal"""
        if macd > signal and macd > 0:
            return 0.6  # Bullish crossover above zero
        elif macd > signal:
            return 0.3  # Mildly bullish
        elif macd < signal and macd < 0:
            return -0.6  # Bearish crossover below zero
        elif macd < signal:
            return -0.3  # Mildly bearish
        else:
            return 0.0  # Neutral

    def score_ma_cross(self, price: float, ma_short: float, ma_long: float) -> float:
        """Score moving average crossover"""
        if price > ma_short > ma_long:
            return 0.5  # Bullish
        elif price < ma_short < ma_long:
            return -0.5  # Bearish
        else:
            return 0.0  # Neutral

    def score_bollinger(self, bb_position: float) -> float:
        """Score Bollinger Band position"""
        if bb_position < 0.2:
            return 0.7  # Near lower band - potential buy
        elif bb_position > 0.8:
            return -0.7  # Near upper band - potential sell
        else:
            return 0.0  # Neutral

    def generate_decision(
        self,
        rsi: float,
        macd: float,
        signal: float,
        price: float,
        ma_short: float,
        ma_long: float,
        bb_position: float
    ) -> Tuple[str, float, List[str]]:
        """Generate final trading decision"""
        # Score each indicator
        signals = {
            'rsi': self.score_rsi(rsi),
            'macd': self.score_macd(macd, signal),
            'ma_cross': self.score_ma_cross(price, ma_short, ma_long),
            'bollinger': self.score_bollinger(bb_position)
        }

        # Calculate composite score
        composite_score = sum(signals.values()) / len(signals)

        # Generate action and confidence
        if composite_score > 0.4:
            action = "BUY"
            confidence = min(0.95, abs(composite_score) + 0.3)
        elif composite_score < -0.4:
            action = "SELL"
            confidence = min(0.95, abs(composite_score) + 0.3)
        else:
            action = "HOLD"
            confidence = 0.5

        # Apply confidence threshold
        if confidence < self.min_confidence:
            action = "HOLD"

        # Generate reasons
        reasons = []
        for signal_name, signal_value in signals.items():
            if abs(signal_value) > 0.5:
                if signal_value > 0:
                    reasons.append(f"{signal_name.replace('_', ' ').title()}: Bullish")
                else:
                    reasons.append(f"{signal_name.replace('_', ' ').title()}: Bearish")

        if composite_score > 0.3:
            reasons.append(f"Composite score: {composite_score:.2f} (Bullish)")
        elif composite_score < -0.3:
            reasons.append(f"Composite score: {composite_score:.2f} (Bearish)")

        return action, confidence, reasons


def generate_decision_plan(
    symbol: str = "SPY",
    min_confidence: float = 0.75,
    target_value_pct: float = 0.05,
    period: str = "6mo"
) -> Dict:
    """
    Generate decision plan with action, confidence, and details

    Args:
        symbol: Stock symbol (default: SPY)
        min_confidence: Minimum confidence threshold (default: 0.75)
        target_value_pct: Target position as % of portfolio (default: 0.05)
        period: Historical data period for yfinance (default: "6mo")

    Returns:
        Decision plan dict with action, confidence, reason, etc.
    """
    logger.info(f"Generating decision plan for {symbol}...")

    if not LIBS_AVAILABLE:
        return {
            "action": "HOLD",
            "symbol": symbol,
            "confidence": 0.0,
            "reason": "Libraries not available (yfinance, pandas, numpy)",
            "order_type": "MKT",
            "target_value_pct": target_value_pct,
            "error": "MISSING_DEPS"
        }

    try:
        # Fetch historical data
        logger.info(f"Fetching {period} of data for {symbol}...")
        ticker = yf.Ticker(symbol)
        df = ticker.history(period=period)

        if df.empty or len(df) < 50:
            return {
                "action": "HOLD",
                "symbol": symbol,
                "confidence": 0.0,
                "reason": f"Insufficient data (only {len(df)} days)",
                "order_type": "MKT",
                "target_value_pct": target_value_pct,
                "error": "INSUFFICIENT_DATA"
            }

        # Calculate indicators
        logger.info("Calculating technical indicators...")
        df['RSI'] = TechnicalIndicators.calculate_rsi(df)
        df['MACD'], df['MACD_Signal'], df['MACD_Hist'] = TechnicalIndicators.calculate_macd(df)
        df['BB_Upper'], df['BB_Middle'], df['BB_Lower'] = TechnicalIndicators.calculate_bollinger_bands(df)
        df['MA_Short'], df['MA_Long'] = TechnicalIndicators.calculate_moving_averages(df)

        # Get latest values
        latest = df.iloc[-1]
        price = latest['Close']
        rsi = latest['RSI']
        macd = latest['MACD']
        signal = latest['MACD_Signal']
        ma_short = latest['MA_Short']
        ma_long = latest['MA_Long']

        # Calculate Bollinger Band position
        bb_upper = latest['BB_Upper']
        bb_lower = latest['BB_Lower']
        bb_position = (price - bb_lower) / (bb_upper - bb_lower) if (bb_upper - bb_lower) > 0 else 0.5

        # Generate decision
        logger.info("Scoring signals...")
        scorer = SignalScorer(min_confidence=min_confidence)
        action, confidence, reasons = scorer.generate_decision(
            rsi, macd, signal, price, ma_short, ma_long, bb_position
        )

        # Build decision plan
        decision_plan = {
            "action": action,
            "symbol": symbol,
            "confidence": round(confidence, 2),
            "order_type": "MKT",
            "target_value_pct": target_value_pct,
            "quantity": None,
            "limit_price": None,
            "time_in_force": "DAY",
            "reason": "; ".join(reasons) if reasons else "No strong signals",
            "indicators": {
                "rsi": round(rsi, 2),
                "macd": round(macd, 2),
                "macd_signal": round(signal, 2),
                "ma_short": round(ma_short, 2),
                "ma_long": round(ma_long, 2),
                "bb_position": round(bb_position, 2),
                "current_price": round(price, 2)
            },
            "timestamp": datetime.now().isoformat()
        }

        logger.info(f"Decision: {action} {symbol} (confidence: {confidence:.2%})")
        return decision_plan

    except Exception as e:
        logger.error(f"Error generating decision: {e}")
        return {
            "action": "HOLD",
            "symbol": symbol,
            "confidence": 0.0,
            "reason": f"Signal generation failed: {str(e)}",
            "order_type": "MKT",
            "target_value_pct": target_value_pct,
            "error": str(e)
        }


def main():
    """Main entry point for command-line usage"""
    parser = argparse.ArgumentParser(description='Generate trading signal for VPA')
    parser.add_argument('--symbol', type=str, default='SPY', help='Trading symbol')
    parser.add_argument('--min-confidence', type=float, default=0.75, help='Minimum confidence')
    parser.add_argument('--target-value-pct', type=float, default=0.05, help='Target position size (% of portfolio)')
    parser.add_argument('--period', type=str, default='6mo', help='Historical data period')
    parser.add_argument('--output', type=str, help='Output JSON file path')

    args = parser.parse_args()

    # Generate decision plan
    decision_plan = generate_decision_plan(
        symbol=args.symbol,
        min_confidence=args.min_confidence,
        target_value_pct=args.target_value_pct,
        period=args.period
    )

    # Output to file or stdout
    if args.output:
        with open(args.output, 'w') as f:
            json.dump(decision_plan, f, indent=2)
        logger.info(f"Decision plan saved to: {args.output}")
    else:
        print(json.dumps(decision_plan, indent=2))

    # Exit with error if signal generation failed
    if 'error' in decision_plan:
        return 1

    return 0


if __name__ == '__main__':
    sys.exit(main())
