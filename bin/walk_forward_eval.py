#!/usr/bin/env python3
"""
Walk-Forward Validation Evaluator
Implements rolling training/testing windows for robust strategy evaluation
"""

import sys
import os
import json
import csv
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Any
import numpy as np
import pandas as pd
import logging

# Add paths
platform_path = Path(__file__).parent.parent
sys.path.insert(0, str(platform_path))
phase1_path = platform_path / "phase1"
sys.path.insert(0, str(phase1_path))

from data.fetch_price_data import fetch_price_data
from data.feature_engineering import add_technical_indicators
from models.ml_trainer import MLTrainer, ModelType
from execution.backtester import Backtester
from strategy.moving_average_crossover import MovingAverageCrossover, MultiMAStrategy

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s'
)
logger = logging.getLogger(__name__)


class WalkForwardEvaluator:
    """Walk-forward validation evaluator for trading strategies."""

    def __init__(
        self,
        symbols: List[str],
        models: List[str],
        train_window: int = 120,
        test_window: int = 20,
        step_size: int = 20,
        commission: float = 0.0005,
        slippage: float = 0.0005,
        initial_capital: float = 100000,
        position_size: float = 0.95
    ):
        """
        Initialize walk-forward evaluator.

        Args:
            symbols: List of symbols to evaluate
            models: List of model names to evaluate
            train_window: Training window size in days
            test_window: Test window size in days
            step_size: Step size for rolling windows
            commission: Commission rate (decimal)
            slippage: Slippage rate (decimal)
            initial_capital: Initial capital for backtests
            position_size: Position size as fraction of capital
        """
        self.symbols = symbols
        self.models = models
        self.train_window = train_window
        self.test_window = test_window
        self.step_size = step_size
        self.commission = commission
        self.slippage = slippage
        self.initial_capital = initial_capital
        self.position_size = position_size

        # Model configurations
        self.model_configs = {
            'phase1_ma_crossover': {
                'short_window': 10,
                'long_window': 50,
                'signal_threshold': 0.02
            },
            'phase1_multi_ma': {
                'ma_pairs': [(5, 20), (10, 50), (20, 200)],
                'consensus_threshold': 2
            },
            'phase1_ml_joblib': {
                'model_type': ModelType.RANDOM_FOREST,
                'n_estimators': 100,
                'max_depth': 10
            },
            'gradient_boosting': {
                'model_type': ModelType.GRADIENT_BOOSTING,
                'n_estimators': 100,
                'max_depth': 5
            }
        }

        logger.info(f"Initialized WalkForwardEvaluator")
        logger.info(f"  Symbols: {symbols}")
        logger.info(f"  Models: {models}")
        logger.info(f"  Train window: {train_window} days")
        logger.info(f"  Test window: {test_window} days")
        logger.info(f"  Step size: {step_size} days")

    def evaluate(
        self,
        start_date: str,
        end_date: str,
        output_dir: str
    ) -> pd.DataFrame:
        """
        Run walk-forward evaluation.

        Args:
            start_date: Start date (YYYY-MM-DD)
            end_date: End date (YYYY-MM-DD)
            output_dir: Output directory for artifacts

        Returns:
            DataFrame with window results
        """
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)

        all_results = []

        for symbol in self.symbols:
            logger.info(f"\n{'='*60}")
            logger.info(f"EVALUATING SYMBOL: {symbol}")
            logger.info(f"{'='*60}\n")

            # Fetch data
            data = self._fetch_data(symbol, start_date, end_date)
            if data is None or len(data) < self.train_window + self.test_window:
                logger.warning(f"Insufficient data for {symbol}, skipping")
                continue

            # Add features
            data = add_technical_indicators(data)

            # Generate windows
            windows = self._generate_windows(data)

            logger.info(f"Generated {len(windows)} windows for {symbol}\n")

            # Evaluate each window
            for window_idx, (train_data, test_data) in enumerate(windows):
                logger.info(f"Window {window_idx + 1}/{len(windows)}")
                logger.info(f"  Train: {train_data.index[0].date()} to {train_data.index[-1].date()}")
                logger.info(f"  Test:  {test_data.index[0].date()} to {test_data.index[-1].date()}")

                # Detect regime
                regime = self._detect_regime(test_data)

                # Evaluate each model
                for model_name in self.models:
                    try:
                        result = self._evaluate_model(
                            model_name,
                            train_data,
                            test_data,
                            symbol,
                            window_idx,
                            regime
                        )

                        all_results.append(result)
                        logger.info(f"  {model_name}: Sharpe={result['sharpe']:.3f}, Return={result['return']:.2%}")

                    except Exception as e:
                        logger.error(f"  {model_name} failed: {e}")
                        continue

        # Create DataFrame
        results_df = pd.DataFrame(all_results)

        # Save results
        results_file = output_path / "02_window_results.csv"
        results_df.to_csv(results_file, index=False)
        logger.info(f"\n✅ Results saved to {results_file}")

        return results_df

    def _fetch_data(self, symbol: str, start_date: str, end_date: str) -> pd.DataFrame:
        """Fetch price data for symbol."""
        try:
            data = fetch_price_data(
                symbol,
                start_date,
                end_date,
                cache_dir='phase1/data/cache'
            )
            return data
        except Exception as e:
            logger.error(f"Failed to fetch data for {symbol}: {e}")
            return None

    def _generate_windows(self, data: pd.DataFrame) -> List[Tuple[pd.DataFrame, pd.DataFrame]]:
        """Generate rolling train/test windows."""
        windows = []
        total_days = len(data)

        # Calculate start position
        pos = 0

        while pos + self.train_window + self.test_window <= total_days:
            # Train window
            train_start = pos
            train_end = pos + self.train_window

            # Test window
            test_start = train_end
            test_end = test_start + self.test_window

            # Extract windows
            train_data = data.iloc[train_start:train_end].copy()
            test_data = data.iloc[test_start:test_end].copy()

            windows.append((train_data, test_data))

            # Move forward
            pos += self.step_size

        return windows

    def _detect_regime(self, data: pd.DataFrame) -> str:
        """Detect market regime for test window."""
        # Calculate returns
        returns = data['Close'].pct_change().dropna()

        # Trend detection
        sma_20 = data['Close'].rolling(window=20).mean()
        ma_slope = (sma_20.iloc[-1] - sma_20.iloc[0]) / sma_20.iloc[0]
        total_return = (data['Close'].iloc[-1] / data['Close'].iloc[0]) - 1

        is_trend = ma_slope > 0 and total_return > 0.01

        # Volatility detection
        realized_vol = returns.std()
        rolling_median_vol = returns.rolling(window=20).median().iloc[-1]
        is_high_vol = realized_vol > rolling_median_vol

        # Combine
        trend_label = "TREND" if is_trend else "MEAN_REV"
        vol_label = "HIGH_VOL" if is_high_vol else "LOW_VOL"

        return f"{trend_label}_{vol_label}"

    def _evaluate_model(
        self,
        model_name: str,
        train_data: pd.DataFrame,
        test_data: pd.DataFrame,
        symbol: str,
        window_idx: int,
        regime: str
    ) -> Dict[str, Any]:
        """Evaluate a single model on a window."""

        # Initialize backtester
        backtester = Backtester(
            initial_capital=self.initial_capital,
            position_size_pct=self.position_size,
            stop_loss_pct=0.02,
            take_profit_pct=0.05
        )

        # Override costs
        backtester.commission = self.commission
        backtester.slippage = self.slippage

        # Generate signals based on model type
        if model_name == 'phase1_ma_crossover':
            signals = self._generate_ma_signals(train_data, test_data)
        elif model_name == 'phase1_multi_ma':
            signals = self._generate_multi_ma_signals(train_data, test_data)
        elif model_name in ['phase1_ml_joblib', 'gradient_boosting']:
            signals = self._generate_ml_signals(
                train_data,
                test_data,
                model_name
            )
        else:
            raise ValueError(f"Unknown model: {model_name}")

        # Run backtest
        results = backtester.run_backtest(test_data, signals)

        # Calculate metrics
        sharpe = results.sharpe_ratio
        total_return = results.total_return_pct / 100  # Convert to decimal
        max_dd = results.max_drawdown_pct / 100  # Convert to decimal

        # Calculate additional metrics
        trades = results.total_trades
        win_rate = results.win_rate / 100  # Convert to decimal

        # Calculate profit factor
        gross_profit = sum([t.pnl for t in results.trades if t.pnl > 0])
        gross_loss = abs(sum([t.pnl for t in results.trades if t.pnl < 0]))
        profit_factor = gross_profit / gross_loss if gross_loss > 0 else 0

        # Calculate turnover (approximate)
        turnover = (trades * self.position_size) / len(test_data) if len(test_data) > 0 else 0

        return {
            'symbol': symbol,
            'model': model_name,
            'window_id': window_idx,
            'window_start': str(test_data.index[0].date()),
            'window_end': str(test_data.index[-1].date()),
            'sharpe': sharpe,
            'return': total_return,
            'max_drawdown': max_dd,
            'trades': trades,
            'win_rate': win_rate,
            'profit_factor': profit_factor,
            'turnover': turnover,
            'regime': regime
        }

    def _generate_ma_signals(
        self,
        train_data: pd.DataFrame,
        test_data: pd.DataFrame
    ) -> pd.DataFrame:
        """Generate signals for MA crossover strategy."""
        config = self.model_configs['phase1_ma_crossover']

        # Combine data
        combined = pd.concat([train_data, test_data])

        # Initialize strategy
        strategy = MovingAverageCrossover(
            short_window=config['short_window'],
            long_window=config['long_window'],
            signal_threshold=config['signal_threshold']
        )

        # Generate signals
        signals = strategy.generate_signals(combined)

        # Return only test period signals
        return signals.loc[test_data.index[0]:]

    def _generate_multi_ma_signals(
        self,
        train_data: pd.DataFrame,
        test_data: pd.DataFrame
    ) -> pd.DataFrame:
        """Generate signals for multi-MA strategy."""
        config = self.model_configs['phase1_multi_ma']

        # Combine data
        combined = pd.concat([train_data, test_data])

        # Initialize strategy
        strategy = MultiMAStrategy(
            ma_pairs=config['ma_pairs'],
            consensus_threshold=config['consensus_threshold']
        )

        # Generate signals
        signals = strategy.generate_signals(combined)

        # Return only test period signals
        return signals.loc[test_data.index[0]:]

    def _generate_ml_signals(
        self,
        train_data: pd.DataFrame,
        test_data: pd.DataFrame,
        model_name: str
    ) -> pd.DataFrame:
        """Generate signals for ML model."""
        config = self.model_configs[model_name]

        # Prepare training data
        from data.feature_engineering import prepare_features

        train_with_indicators = add_technical_indicators(train_data)
        test_with_indicators = add_technical_indicators(test_data)

        # Prepare features
        X_train, y_train, feature_cols = prepare_features(train_with_indicators)

        # Create trainer
        trainer = MLTrainer(
            model_type=config['model_type'],
            test_size=0.2,
            random_state=42
        )

        # Train model
        trainer.feature_names = feature_cols
        trainer.train(X_train, y_train)

        # Generate predictions for test data
        X_test = test_with_indicators[feature_cols].dropna()
        predictions = trainer.predict(X_test)

        # Create signals
        signals = test_with_indicators.loc[X_test.index].copy()
        signals['Signal'] = 'HOLD'
        signals.loc[predictions == 1, 'Signal'] = 'BUY'
        signals.loc[predictions == 0, 'Signal'] = 'SELL'
        signals['Signal_Strength'] = 0.8

        return signals


def main():
    """CLI entry point."""
    import argparse

    parser = argparse.ArgumentParser(
        description='Walk-forward validation for trading strategies'
    )
    parser.add_argument(
        '--symbols',
        nargs='+',
        default=['SPY', 'AAPL'],
        help='Symbols to evaluate'
    )
    parser.add_argument(
        '--days',
        type=int,
        default=180,
        help='Total days to evaluate'
    )
    parser.add_argument(
        '--train',
        type=int,
        default=90,
        help='Training window size'
    )
    parser.add_argument(
        '--test',
        type=int,
        default=15,
        help='Test window size'
    )
    parser.add_argument(
        '--step',
        type=int,
        default=15,
        help='Step size'
    )
    parser.add_argument(
        '--models',
        nargs='+',
        default=['phase1_ma_crossover', 'phase1_multi_ma'],
        help='Models to evaluate'
    )
    parser.add_argument(
        '--out',
        type=str,
        required=True,
        help='Output directory'
    )

    args = parser.parse_args()

    # Calculate dates
    end_date = datetime.now()
    start_date = end_date - timedelta(days=args.days)

    # Initialize evaluator
    evaluator = WalkForwardEvaluator(
        symbols=args.symbols,
        models=args.models,
        train_window=args.train,
        test_window=args.test,
        step_size=args.step
    )

    # Run evaluation
    results = evaluator.evaluate(
        start_date=start_date.strftime('%Y-%m-%d'),
        end_date=end_date.strftime('%Y-%m-%d'),
        output_dir=args.out
    )

    print(f"\n✅ Evaluation complete!")
    print(f"Total evaluations: {len(results)}")
    print(f"Results saved to: {args.out}")


if __name__ == "__main__":
    main()
