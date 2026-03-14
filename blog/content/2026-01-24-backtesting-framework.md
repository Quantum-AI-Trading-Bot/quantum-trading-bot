---
title: "Backtesting Framework: Validating Trading Strategies Against History"
author: "David Sanker"
date: "January 24, 2026"
tags: ["Backtesting", "TradingStrategies", "QuantitativeFinance", "PaperTrading", "PerformanceAnalysis", "RiskMetrics"]
reading_time: "7 min read"
excerpt: "Building a backtesting framework that honestly evaluates trading strategies — including the pitfalls that make most backtests dangerously misleading."
---

Before trusting any trading strategy with even paper money, I need to know how it would have performed historically. That's the purpose of a backtesting framework: replay historical market data through the strategy and measure the results. Sounds simple, but backtesting is one of the most deceptive exercises in quantitative finance. This week I built the framework and learned firsthand why most published backtests are worthless.

## Why Most Backtests Lie

The dirty secret of quantitative trading is that it's trivially easy to build a strategy that looks spectacular in backtests but fails catastrophically in live trading. The three most common traps:

**Look-ahead bias.** The strategy accidentally uses future information to make decisions. This can be subtle — using a feature that's normalized with statistics computed over the entire dataset, or using an economic indicator that's reported with a 2-day lag as if it were available in real time. My framework enforces strict temporal ordering: at time T, the strategy can only see data from time T-1 and earlier.

**Survivorship bias.** Testing only on stocks that exist today ignores all the companies that went bankrupt, were delisted, or were acquired. A strategy that "always bought tech stocks" looks brilliant if you test it on today's S&P 500 constituents — but many tech companies from 2008 no longer exist. I use point-in-time constituent lists to avoid this.

**Overfitting.** If you test 1,000 strategies on the same historical data, 50 will look profitable at the 5% significance level purely by chance. The more parameters you tune, the more likely you are to find a strategy that fits the noise in historical data rather than genuine market patterns. My framework uses walk-forward validation with strict separation between in-sample and out-of-sample periods.

## Framework Architecture

The backtesting framework has three components:

**The Market Simulator** replays historical data bar-by-bar, maintaining a realistic order book simulation. It models slippage (the difference between the expected price and the actual fill price), transaction costs ($0.005 per share for equities), and market impact (large orders move the price). These friction costs are often the difference between a profitable backtest and a realistic one.

**The Strategy Executor** takes the ML model's signals and converts them into orders, passing each order through the same 8-gate risk management system used in live paper trading. This ensures the backtest results reflect the actual system, not an idealized version of it.

**The Analytics Engine** computes performance metrics on the simulated portfolio:

```python
@dataclass
class BacktestMetrics:
    total_return: float        # cumulative P&L
    annualized_return: float   # annualized return rate
    sharpe_ratio: float        # risk-adjusted return
    sortino_ratio: float       # downside-risk-adjusted return
    max_drawdown: float        # worst peak-to-trough decline
    calmar_ratio: float        # return / max drawdown
    win_rate: float            # percentage of profitable trades
    profit_factor: float       # gross profit / gross loss
    avg_trade_duration: float  # average holding period
    trades_per_day: float      # trading frequency
```

## Results: The Honest Numbers

I ran the current ensemble model (XGBoost + LSTM + Transformer) through 12 months of historical data using walk-forward validation with monthly retraining. Here are the honest numbers:

| Metric | Value |
|--------|-------|
| Total Return | +23.4% |
| Annualized Return | +23.4% |
| Sharpe Ratio | 1.31 |
| Sortino Ratio | 1.87 |
| Max Drawdown | -12.8% |
| Calmar Ratio | 1.83 |
| Win Rate | 54.2% |
| Profit Factor | 1.38 |
| Avg Trade Duration | 4.2 hours |
| Trades per Day | 8.3 |

These numbers are intentionally modest. I've seen published trading bot backtests claiming 200%+ annual returns with Sharpe ratios above 5 — numbers that are almost certainly the result of overfitting or simulation errors. A Sharpe ratio of 1.3 is realistic for a medium-frequency strategy and would be considered acceptable by institutional standards.

## Regime Analysis

The most valuable output of the backtest wasn't the headline numbers — it was the regime analysis showing how the strategy performed under different market conditions:

**Bull markets (S&P 500 up >1% monthly):** The strategy performed well, capturing 68% of upside moves with controlled drawdowns. The long bias in the ML model's predictions aligned naturally with trending markets.

**Bear markets (S&P 500 down >1% monthly):** Performance degraded significantly, with the strategy capturing only 41% of directional moves. The model struggled to identify short-selling opportunities, likely because the training data contains more up-moves than down-moves (a structural bias in equity markets).

**Sideways/choppy markets:** Surprisingly, this was where the strategy performed worst. In low-volatility, range-bound environments, the model generated many false signals, and transaction costs ate into marginal gains. The win rate dropped to 48% — essentially random.

This regime analysis directly informs the next iteration of the model. The clear weakness in choppy markets suggests I need to add a regime detection layer that reduces trading frequency when the market lacks a clear trend.

## Transaction Cost Sensitivity

One analysis that many backtests skip: how sensitive are the results to transaction cost assumptions? I ran the backtest with three cost models:

- **Zero costs:** +41.2% return, 2.1 Sharpe (the fantasy scenario)
- **Realistic costs ($0.005/share + 0.5bp slippage):** +23.4% return, 1.31 Sharpe
- **Conservative costs ($0.01/share + 1bp slippage):** +14.1% return, 0.92 Sharpe

The strategy remains profitable under conservative cost assumptions, but the margin is thin. This means execution quality will matter enormously if this strategy is ever applied to real trading. It also explains why high-frequency strategies are dominated by firms with co-located servers and direct market access — execution costs are the moat.

## Lessons for AI Systems Beyond Trading

Building this backtesting framework reinforced principles that apply to any AI system that makes consequential decisions:

**Test under adversarial conditions.** Don't just test your AI on the scenarios where it's expected to perform well. Deliberately stress-test it against edge cases, regime changes, and distribution shifts. This applies equally to a trading bot, an IP monitoring system, or an AI governance framework.

**Measure what matters.** Accuracy alone is misleading. A model that's 55% accurate but has a 2:1 profit-to-loss ratio is far better than one that's 65% accurate with a 1:1 ratio. Choose metrics that reflect the actual decision-making context.

**Be honest about limitations.** The strategy doesn't work in choppy markets. Rather than hiding this, I'm documenting it and building a regime detector to address it. Intellectual honesty about AI system limitations is something I believe should be a requirement for any autonomous system — a principle I'm building into the UAPK governance framework.

## What's Next

The backtesting results have given me a clear roadmap: improve bear market performance, add regime detection to reduce trading in choppy markets, and optimize execution to minimize transaction cost drag. All of this continues in paper trading mode — the backtest just helps me prioritize which improvements to tackle first.
