---
title: "Building the Machine Learning Pipeline for Algorithmic Trading"
author: "David Sanker"
date: "January 25, 2026"
tags: ["MachineLearning", "TradingPipeline", "FeatureEngineering", "ModelTraining", "PaperTrading", "Python"]
reading_time: "10 min read"
excerpt: "A deep dive into the ML pipeline powering the Quantum AI Trading Bot — from feature engineering through model training to paper trading inference."
---

The heart of the Quantum AI Trading Bot is its machine learning pipeline. This week I completed the first end-to-end version: raw market data goes in, trade signals come out. The pipeline is far from perfect — paper trading results will tell me where it needs improvement — but having a working end-to-end system is a critical milestone. Here's how it's built.

## Pipeline Overview

The ML pipeline has four stages, each designed to be independently testable and replaceable:

1. **Feature Engineering** — transforms raw market data into the 50+ feature vectors the models consume
2. **Model Training** — trains and validates multiple model architectures on historical data
3. **Model Selection** — evaluates trained models and selects the best performer for each market regime
4. **Inference** — generates real-time predictions for the paper trading system

Each stage writes its outputs to a versioned artifact store, so I can always trace a specific trade signal back to the exact model weights, training data, and feature definitions that produced it. This traceability is essential for debugging and for building trust in the system's decisions.

## Feature Engineering

The feature engineering stage consumes the unified data stream from the multi-source integration layer and produces feature vectors at configurable time intervals (currently 1-minute bars for short-term signals and 1-hour bars for position management).

Features fall into five categories:

**Price-derived features** include returns at multiple horizons (1m, 5m, 15m, 1h, 4h), price relative to moving averages (SMA 20, 50, 200), and price velocity and acceleration. These are the bread and butter of any trading model.

**Volume features** capture trading activity patterns: volume relative to the 20-day average, VWAP deviation, and volume-weighted price momentum. Volume often leads price, making these features valuable for anticipating moves.

**Volatility features** measure market uncertainty: ATR (Average True Range), Bollinger Band width and position, and realized vs implied volatility spread where available. These help the model adjust its confidence based on market conditions.

**Cross-asset features** capture relationships between instruments: sector correlation rankings, S&P 500 beta, VIX term structure slope, and treasury yield curve position. Markets don't exist in isolation, and these features encode the broader context.

**Temporal features** encode time-based patterns: hour of day, day of week, minutes to market close, and distance to next scheduled economic event. Markets have well-documented temporal regularities that the models can exploit.

A critical design decision was to normalize all features to zero mean and unit variance using rolling statistics rather than global statistics. This prevents look-ahead bias (the model can't see future normalization parameters during training) and handles the non-stationarity of financial time series more gracefully than static normalization.

```python
class RollingNormalizer:
    def __init__(self, window: int = 252 * 390):  # ~1 year of minute bars
        self.window = window
        self.buffer = deque(maxlen=window)
    
    def transform(self, value: float) -> float:
        self.buffer.append(value)
        if len(self.buffer) < 30:  # minimum sample
            return 0.0
        mean = np.mean(self.buffer)
        std = np.std(self.buffer)
        return (value - mean) / (std + 1e-8)
```

## Model Architecture

I'm currently training three model architectures in parallel, with the goal of eventually combining them into an ensemble:

**Gradient Boosted Trees (XGBoost)** — the workhorse. Fast to train, interpretable, and excellent at capturing non-linear relationships in tabular data. I use 500 trees with max depth 6 and a learning rate of 0.05. Feature importance from XGBoost also serves as a diagnostic tool for understanding what the model is paying attention to.

**LSTM Networks** — for capturing temporal dependencies. Financial time series have patterns that unfold over time — trends, mean reversion, regime changes — and recurrent architectures can capture these in ways that tree models cannot. The current architecture uses 2 LSTM layers with 128 hidden units, followed by a dense layer for classification.

**Attention-Based Transformer** — an experimental addition inspired by recent NLP breakthroughs. The self-attention mechanism allows the model to directly attend to any point in the input sequence, potentially capturing long-range dependencies that LSTMs might miss. This is the most computationally expensive model and I'm still tuning it.

## Training Protocol

Training happens nightly on the previous day's data, following a walk-forward validation protocol:

1. **Training window**: 6 months of historical data
2. **Validation window**: 1 month following the training window
3. **Test window**: the most recent 2 weeks (never seen during training or validation)
4. **Walk-forward**: the windows slide forward by 1 week, and training repeats

This protocol prevents the most common mistake in financial ML: overfitting to historical data and then being surprised when the model fails in live trading. By using walk-forward validation, the model is always evaluated on genuinely out-of-sample data.

The target variable is the forward 1-hour return, binned into three classes: up (>0.1%), down (<-0.1%), and flat (between -0.1% and 0.1%). I chose classification over regression because the trading strategy doesn't need to know the exact magnitude of the move — it just needs to know the direction with reasonable confidence.

## Inference and Paper Trading

During market hours, the inference engine runs the latest trained models on the streaming feature vectors and produces trade signals. Each model outputs a probability distribution over the three classes (up, down, flat), and the trading logic converts these into actionable signals:

- If P(up) > 0.65 and P(down) < 0.15: **BUY signal**
- If P(down) > 0.65 and P(up) < 0.15: **SELL signal**
- Otherwise: **HOLD**

These thresholds are deliberately conservative. I'd rather miss trades than take bad ones, especially while the system is being validated in paper trading. The thresholds will be tuned as I accumulate more data on model performance.

## Early Results

After the first week of paper trading with the full pipeline:

- **XGBoost** achieved 58% directional accuracy on 1-hour predictions — modestly above the 50% baseline but consistent across symbols.
- **LSTM** achieved 54% accuracy but showed much higher accuracy (63%) on high-volatility symbols, suggesting it captures regime-dependent patterns that XGBoost misses.
- **Transformer** is still underperforming at 51%, likely due to insufficient training data. Attention models are notoriously data-hungry.

The ensemble (simple average of the three models' probability outputs) achieved 60% directional accuracy — better than any individual model. This is encouraging and validates the multi-model approach.

## Lessons Learned

**Financial ML is humbling.** A 60% accuracy model sounds unimpressive compared to the 95%+ accuracy common in computer vision or NLP. But in financial markets, even a small edge compounds into meaningful returns over thousands of trades — if the risk management layer (covered in a separate post) keeps drawdowns controlled.

**Feature engineering matters more than model architecture.** Swapping XGBoost for a transformer changed accuracy by 7%. Adding the cross-asset features improved all models by 4-6%. The data and features are the ceiling; the model architecture determines how close you get to that ceiling.

**Reproducibility is non-negotiable.** Every training run logs the exact feature definitions, hyperparameters, random seeds, and data versions used. Without this, debugging model regressions is impossible. This discipline carries over directly to how I think about AI governance in UAPK — autonomous systems must be auditable.

## What's Next

The pipeline is operational but far from optimized. Next steps include adding quantum-inspired optimization for hyperparameter tuning (using QAOA-style algorithms), implementing online learning to allow models to adapt intraday, and expanding the feature set to include options market data. All of this remains firmly in the paper trading domain — the goal is research and learning, not profits. But the engineering standards have to be production-grade, because sloppy infrastructure produces sloppy results regardless of whether money is involved.
