#!/usr/bin/env python3
"""
Phase 1: Feature Engineering Module
Creates technical indicators and features for ML models
"""

import pandas as pd
import numpy as np
import logging
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)


def add_technical_indicators(df: pd.DataFrame) -> pd.DataFrame:
    """
    Add comprehensive technical indicators to OHLCV data

    Args:
        df: DataFrame with OHLCV data (columns: Open, High, Low, Close, Volume)

    Returns:
        DataFrame with added technical indicators
    """
    df = df.copy()

    # ===== Trend Indicators =====
    # Simple Moving Averages
    df['SMA_10'] = df['Close'].rolling(window=10).mean()
    df['SMA_20'] = df['Close'].rolling(window=20).mean()
    df['SMA_50'] = df['Close'].rolling(window=50).mean()
    df['SMA_200'] = df['Close'].rolling(window=200).mean()

    # Exponential Moving Averages
    df['EMA_12'] = df['Close'].ewm(span=12, adjust=False).mean()
    df['EMA_26'] = df['Close'].ewm(span=26, adjust=False).mean()

    # ===== Momentum Indicators =====
    # RSI (Relative Strength Index)
    delta = df['Close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
    rs = gain / loss
    df['RSI'] = 100 - (100 / (1 + rs))

    # MACD
    df['MACD'] = df['EMA_12'] - df['EMA_26']
    df['MACD_Signal'] = df['MACD'].ewm(span=9, adjust=False).mean()
    df['MACD_Histogram'] = df['MACD'] - df['MACD_Signal']

    # Momentum
    df['Momentum_5'] = df['Close'].pct_change(5)
    df['Momentum_10'] = df['Close'].pct_change(10)
    df['Momentum_20'] = df['Close'].pct_change(20)

    # Rate of Change
    df['ROC'] = ((df['Close'] - df['Close'].shift(10)) / df['Close'].shift(10)) * 100

    # ===== Volatility Indicators =====
    # Bollinger Bands
    df['BB_Middle'] = df['Close'].rolling(window=20).mean()
    bb_std = df['Close'].rolling(window=20).std()
    df['BB_Upper'] = df['BB_Middle'] + (bb_std * 2)
    df['BB_Lower'] = df['BB_Middle'] - (bb_std * 2)
    df['BB_Width'] = df['BB_Upper'] - df['BB_Lower']
    df['BB_Position'] = (df['Close'] - df['BB_Lower']) / (df['BB_Upper'] - df['BB_Lower'])

    # ATR (Average True Range)
    high_low = df['High'] - df['Low']
    high_close = np.abs(df['High'] - df['Close'].shift())
    low_close = np.abs(df['Low'] - df['Close'].shift())
    true_range = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
    df['ATR'] = true_range.rolling(window=14).mean()

    # Historical Volatility
    df['Volatility_20'] = df['Close'].pct_change().rolling(window=20).std() * np.sqrt(252)

    # ===== Volume Indicators =====
    # Volume Moving Average
    df['Volume_MA'] = df['Volume'].rolling(window=20).mean()
    df['Volume_Ratio'] = df['Volume'] / df['Volume_MA']

    # On-Balance Volume (OBV)
    obv = []
    obv_value = 0
    for i in range(len(df)):
        if i == 0:
            obv_value = df['Volume'].iloc[i]
        elif df['Close'].iloc[i] > df['Close'].iloc[i-1]:
            obv_value += df['Volume'].iloc[i]
        elif df['Close'].iloc[i] < df['Close'].iloc[i-1]:
            obv_value -= df['Volume'].iloc[i]
        else:
            obv_value += 0
        obv.append(obv_value)
    df['OBV'] = obv

    # ===== Price Patterns =====
    # Returns
    df['Returns'] = df['Close'].pct_change()
    df['Log_Returns'] = np.log(df['Close'] / df['Close'].shift(1))

    # High-Low Range
    df['HL_Range'] = (df['High'] - df['Low']) / df['Close']

    # Open-Close Gap
    df['OC_Gap'] = (df['Close'] - df['Open']) / df['Open']

    # Gap Up/Down
    df['Gap'] = (df['Open'] - df['Close'].shift(1)) / df['Close'].shift(1)

    logger.info(f"Added {len([col for col in df.columns if col not in ['Open', 'High', 'Low', 'Close', 'Volume']])} technical indicators")
    return df


def prepare_features(df: pd.DataFrame, target_col: str = 'Returns', lookforward: int = 1) -> pd.DataFrame:
    """
    Prepare features for ML model training

    Args:
        df: DataFrame with technical indicators
        target_col: Column to use as target (future returns)
        lookforward: Number of periods to look forward for target

    Returns:
        DataFrame with features and target, ready for ML
    """
    df = df.copy()

    # Create target variable (future returns)
    df['Target'] = df[target_col].shift(-lookforward)

    # Remove rows with missing values
    df_clean = df.dropna()

    # Select feature columns (exclude non-numeric columns)
    feature_cols = [col for col in df_clean.columns
                   if col not in ['Symbol', 'Data_Source', 'Fetch_Date', 'Target']
                   and df_clean[col].dtype in ['float64', 'int64']]

    X = df_clean[feature_cols]
    y = df_clean['Target']

    logger.info(f"Prepared {len(feature_cols)} features for {len(X)} samples")
    logger.info(f"Target variable: {target_col} (lookforward {lookforward} periods)")

    return X, y, feature_cols


def create_trading_signals(df: pd.DataFrame) -> pd.DataFrame:
    """
    Create trading signals based on technical indicators

    Args:
        df: DataFrame with technical indicators

    Returns:
        DataFrame with added signal columns
    """
    df = df.copy()

    # RSI Signal
    df['RSI_Signal'] = 0
    df.loc[df['RSI'] < 30, 'RSI_Signal'] = 1  # Oversold - Buy
    df.loc[df['RSI'] > 70, 'RSI_Signal'] = -1  # Overbought - Sell

    # MACD Signal
    df['MACD_Signal'] = 0
    df.loc[df['MACD'] > df['MACD_Signal'], 'MACD_Signal'] = 1  # Bullish
    df.loc[df['MACD'] < df['MACD_Signal'], 'MACD_Signal'] = -1  # Bearish

    # Moving Average Crossover Signal
    df['MA_Cross_Signal'] = 0
    df.loc[df['SMA_10'] > df['SMA_50'], 'MA_Cross_Signal'] = 1  # Golden Cross
    df.loc[df['SMA_10'] < df['SMA_50'], 'MA_Cross_Signal'] = -1  # Death Cross

    # Bollinger Band Signal
    df['BB_Signal'] = 0
    df.loc[df['Close'] < df['BB_Lower'], 'BB_Signal'] = 1  # Below lower band - Buy
    df.loc[df['Close'] > df['BB_Upper'], 'BB_Signal'] = -1  # Above upper band - Sell

    # Combined Signal (simple average)
    signal_cols = ['RSI_Signal', 'MACD_Signal', 'MA_Cross_Signal', 'BB_Signal']
    df['Combined_Signal'] = df[signal_cols].mean(axis=1)

    # Normalize combined signal to -1 to 1
    df['Combined_Signal'] = df['Combined_Signal'] / df[signal_cols].abs().max(axis=1)

    logger.info("Added trading signals based on technical indicators")
    return df


if __name__ == "__main__":
    # Test feature engineering
    from fetch_price_data import fetch_price_data

    logger.info("Testing Feature Engineering...")

    # Fetch sample data
    symbol = "AAPL"
    start_date = "2024-01-01"
    end_date = "2025-01-01"

    logger.info(f"\nFetching {symbol} data...")
    data = fetch_price_data(symbol, start_date, end_date)

    if data is not None:
        logger.info(f"\n{'='*60}")
        logger.info("Adding Technical Indicators")
        logger.info(f"{'='*60}\n")

        data_with_indicators = add_technical_indicators(data)

        logger.info(f"\n✅ Added indicators")
        logger.info(f"\nNew columns: {[col for col in data_with_indicators.columns if col not in data.columns]}")

        logger.info(f"\n{'='*60}")
        logger.info("Creating Trading Signals")
        logger.info(f"{'='*60}\n")

        data_with_signals = create_trading_signals(data_with_indicators)

        logger.info(f"\n✅ Added signals")
        logger.info(f"\nSignal statistics:")
        logger.info(data_with_signals[['RSI_Signal', 'MACD_Signal', 'MA_Cross_Signal', 'BB_Signal', 'Combined_Signal']].describe())

        logger.info(f"\n{'='*60}")
        logger.info("Preparing Features for ML")
        logger.info(f"{'='*60}\n")

        X, y, feature_cols = prepare_features(data_with_signals)

        logger.info(f"\n✅ Prepared {len(feature_cols)} features for {len(X)} samples")
        logger.info(f"\nFeature columns: {feature_cols[:10]}...")  # Show first 10
        logger.info(f"\nTarget statistics:")
        logger.info(y.describe())
