#!/usr/bin/env python3
"""
Multi-Source Enhanced Trading Bot
Integrates FRED, NewsAPI, and other sources into the live trading bot
"""

import sys
import os
from datetime import datetime

# Add paths
sys.path.append('/home/davidsanker/platform')
sys.path.append('/home/davidsanker/quantum-trading-bot-new')

# Import the multi-source manager
from data.multi_source_data_manager import get_multi_source_manager

def enhance_trading_decision(symbol: str, base_confidence: float) -> tuple:
    """
    Enhance trading decision with multi-source data

    Returns:
        (adjusted_confidence, reasoning_additions, data_sources_used)
    """
    try:
        # Get multi-source signal
        manager = get_multi_source_manager()
        signal = manager.get_comprehensive_signal(symbol)

        # Base adjustment on overall sentiment
        sentiment_boost = signal.overall_sentiment * 0.5  # Scale influence

        # Calculate adjusted confidence
        adjusted_confidence = base_confidence + sentiment_boost
        adjusted_confidence = max(0.0, min(1.0, adjusted_confidence))  # Clamp to [0, 1]

        # Build reasoning additions
        reasoning_additions = []

        if signal.economic_signal != 0:
            reasoning_additions.append(
                f"FRED Economic Signal: {signal.economic_signal:+.2f}"
            )

        if signal.news_sentiment != 0:
            reasoning_additions.append(
                f"News Sentiment: {signal.news_sentiment:+.2f}"
            )

        if signal.economic_indicators:
            reasoning_additions.append(
                f"Economic: Fed Rate {signal.economic_indicators.get('Federal Funds Rate', 'N/A')}%, "
                f"Unemployment {signal.economic_indicators.get('Unemployment Rate', 'N/A')}%"
            )

        if signal.top_headlines:
            reasoning_additions.append(
                f"Top News: {signal.top_headlines[0][:60]}..."
            )

        return (
            adjusted_confidence,
            reasoning_additions,
            signal.data_sources_used
        )

    except Exception as e:
        print(f"Error enhancing decision for {symbol}: {e}")
        return base_confidence, [], []

# Example usage function
def demonstrate_enhancement():
    """Show how the enhancement works"""
    print("🚀 Multi-Source Trading Enhancement Demo")
    print("=" * 60)

    test_cases = [
        ("AAPL", 0.45, "Moderate BUY signal"),
        ("NVDA", 0.65, "Strong BUY signal"),
        ("TSLA", 0.35, "Weak BUY signal")
    ]

    for symbol, base_conf, description in test_cases:
        print(f"\n📊 {symbol}: {description}")
        print(f"   Base Confidence: {base_conf:.2f}")

        adjusted_conf, reasoning, sources = enhance_trading_decision(symbol, base_conf)

        print(f"   Adjusted Confidence: {adjusted_conf:.2f} ({(adjusted_conf-base_conf):+.2f})")
        print(f"   Data Sources: {', '.join(sources) if sources else 'None'}")

        if reasoning:
            print(f"   Enhancement Factors:")
            for reason in reasoning[:3]:
                print(f"      • {reason}")

if __name__ == "__main__":
    demonstrate_enhancement()
