#!/usr/bin/env python3
"""
Phase 1: Main CLI Interface
Entry point for the Quantum AI Trading Bot backtesting system
"""

import argparse
import logging
import sys
import os
from pathlib import Path
import pandas as pd
import matplotlib.pyplot as plt
import json
from datetime import datetime

# Add phase1 to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from data.fetch_price_data import fetch_price_data, DataFetcher
from data.feature_engineering import add_technical_indicators, create_trading_signals
from strategy.moving_average_crossover import MovingAverageCrossover, MultiMAStrategy
from execution.backtester import Backtester
from risk.guardrails import RiskGuardrails, apply_guardrails
from models.ml_trainer import MLTrainer, ModelType, train_and_evaluate

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('logs/trading_bot.log')
    ]
)
logger = logging.getLogger(__name__)


def parse_arguments():
    """Parse command line arguments"""
    parser = argparse.ArgumentParser(
        description='Quantum AI Trading Bot - Phase 1: Backtesting Engine',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Simple backtest with moving average crossover
  python main.py --symbol AAPL --strategy ma_crossover --backtest --plot

  # Train ML model on historical data
  python main.py --symbol SPY --train-model --model-type random_forest

  # Run strategy with risk management
  python main.py --symbol TSLA --strategy ma_crossover --backtest --apply-risk

  # Multiple symbols with ensemble
  python main.py --symbols AAPL MSFT GOOGL --strategy multi_ma --backtest
        """
    )

    # Data parameters
    parser.add_argument('--symbol', type=str, help='Trading symbol (e.g., AAPL, SPY)')
    parser.add_argument('--symbols', type=str, nargs='+', help='Multiple symbols')
    parser.add_argument('--start-date', type=str, default='2024-01-01', help='Start date (YYYY-MM-DD)')
    parser.add_argument('--end-date', type=str, default=None, help='End date (YYYY-MM-DD)')

    # Strategy parameters
    parser.add_argument('--strategy', type=str, default='ma_crossover',
                       choices=['ma_crossover', 'multi_ma', 'ml_model'],
                       help='Trading strategy to use')
    parser.add_argument('--short-window', type=int, default=10, help='Short MA window')
    parser.add_argument('--long-window', type=int, default=50, help='Long MA window')

    # Backtesting parameters
    parser.add_argument('--backtest', action='store_true', help='Run backtest')
    parser.add_argument('--initial-capital', type=float, default=100000, help='Initial capital')
    parser.add_argument('--position-size', type=float, default=0.95, help='Position size as percentage of capital')

    # Risk management
    parser.add_argument('--apply-risk', action='store_true', help='Apply risk guardrails')
    parser.add_argument('--stop-loss', type=float, default=0.02, help='Stop loss percentage')
    parser.add_argument('--take-profit', type=float, default=0.05, help='Take profit percentage')

    # ML model parameters
    parser.add_argument('--train-model', action='store_true', help='Train ML model')
    parser.add_argument('--model-type', type=str, default='random_forest',
                       choices=['logistic_regression', 'random_forest', 'gradient_boosting'],
                       help='ML model type')
    parser.add_argument('--save-model', action='store_true', help='Save trained model')

    # Output options
    parser.add_argument('--plot', action='store_true', help='Plot results')
    parser.add_argument('--save-results', action='store_true', help='Save results to file')
    parser.add_argument('--output-dir', type=str, default='phase1/results', help='Output directory')
    parser.add_argument('--verbose', action='store_true', help='Verbose output')

    return parser.parse_args()


def run_backtest(args, data, signals):
    """Run backtest with given parameters"""
    logger.info(f"\n{'='*60}")
    logger.info("RUNNING BACKTEST")
    logger.info(f"{'='*60}\n")

    # Initialize backtester
    backtester = Backtester(
        initial_capital=args.initial_capital,
        position_size_pct=args.position_size,
        stop_loss_pct=args.stop_loss,
        take_profit_pct=args.take_profit
    )

    # Run backtest
    results = backtester.run_backtest(data, signals)

    # Print results
    backtester.print_results(results)

    # Save results
    if args.save_results:
        output_dir = Path(args.output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)

        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        results_file = output_dir / f'backtest_results_{args.symbol}_{timestamp}.json'
        backtester.save_results(results, str(results_file))

    # Plot results
    if args.plot:
        plot_backtest_results(data, signals, results, args.symbol, args.output_dir)

    return results


def plot_backtest_results(data, signals, results, symbol, output_dir='phase1/results'):
    """Plot backtest results"""
    fig, axes = plt.subplots(3, 1, figsize=(15, 10))

    # Price and signals
    ax1 = axes[0]
    ax1.plot(data.index, data['Close'], label='Price', alpha=0.7)

    # Plot buy/sell signals
    buy_signals = signals[signals['Signal'] == 'BUY']
    sell_signals = signals[signals['Signal'] == 'SELL']

    ax1.scatter(buy_signals.index, buy_signals['Close'], color='green', marker='^', s=100, label='Buy', zorder=5)
    ax1.scatter(sell_signals.index, sell_signals['Close'], color='red', marker='v', s=100, label='Sell', zorder=5)

    ax1.set_title(f'{symbol} - Price and Trading Signals')
    ax1.set_ylabel('Price ($)')
    ax1.legend()
    ax1.grid(True)

    # Equity curve
    ax2 = axes[1]
    ax2.plot(results.equity_curve, label='Portfolio Value', color='blue')
    ax2.axhline(y=results.initial_capital, color='red', linestyle='--', label='Initial Capital')
    ax2.set_title('Equity Curve')
    ax2.set_ylabel('Portfolio Value ($)')
    ax2.legend()
    ax2.grid(True)

    # Drawdown
    ax3 = axes[2]
    equity_series = pd.Series(results.equity_curve)
    rolling_max = equity_series.expanding().max()
    drawdown = (equity_series - rolling_max) / rolling_max * 100

    ax3.fill_between(equity_series.index, drawdown, 0, alpha=0.3, color='red')
    ax3.plot(drawdown, color='red', label='Drawdown')
    ax3.set_title('Drawdown')
    ax3.set_ylabel('Drawdown (%)')
    ax3.set_xlabel('Time')
    ax3.legend()
    ax3.grid(True)

    plt.tight_layout()

    # Save plot
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    plot_file = output_dir / f'backtest_plot_{symbol}_{timestamp}.png'
    plt.savefig(plot_file, dpi=150, bbox_inches='tight')
    logger.info(f"Plot saved to {plot_file}")

    plt.show()


def train_ml_model(args, data):
    """Train ML model on historical data"""
    logger.info(f"\n{'='*60}")
    logger.info("TRAINING ML MODEL")
    logger.info(f"{'='*60}\n")

    # Prepare data
    from data.feature_engineering import prepare_features
    data_with_indicators = add_technical_indicators(data)
    X, y, feature_cols = prepare_features(data_with_indicators)

    # Combine for training
    train_data = data_with_indicators.copy()
    train_data['Target'] = y

    # Train model
    model_type = ModelType(args.model_type)
    trainer, evaluation = train_and_evaluate(train_data, model_type=model_type)

    # Save model
    if args.save_model:
        output_dir = Path(args.output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)

        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        model_file = output_dir / f'{args.symbol}_{args.model_type}_model_{timestamp}.joblib'
        trainer.save_model(str(model_file))

        logger.info(f"\nModel saved to {model_file}")

    return trainer, evaluation


def main():
    """Main entry point"""
    args = parse_arguments()

    # Create logs directory
    Path('phase1/logs').mkdir(parents=True, exist_ok=True)

    # Validate arguments
    if not args.symbol and not args.symbols:
        logger.error("Please provide --symbol or --symbols")
        sys.exit(1)

    symbols = [args.symbol] if args.symbol else args.symbols

    logger.info(f"\n{'='*60}")
    logger.info("QUANTUM AI TRADING BOT - PHASE 1")
    logger.info(f"{'='*60}")
    logger.info(f"Symbols: {', '.join(symbols)}")
    logger.info(f"Strategy: {args.strategy}")
    logger.info(f"Period: {args.start_date} to {args.end_date or 'present'}")
    logger.info(f"{'='*60}\n")

    # Process each symbol
    all_results = {}

    for symbol in symbols:
        logger.info(f"\n{'#'*60}")
        logger.info(f"PROCESSING: {symbol}")
        logger.info(f"{'#'*60}\n")

        # Fetch data
        logger.info(f"Fetching data for {symbol}...")
        data = fetch_price_data(
            symbol,
            args.start_date,
            args.end_date,
            cache_dir='phase1/data/cache'
        )

        if data is None:
            logger.error(f"Failed to fetch data for {symbol}")
            continue

        logger.info(f"✅ Fetched {len(data)} rows of data")

        # Add technical indicators
        logger.info("Adding technical indicators...")
        data_with_indicators = add_technical_indicators(data)
        data_with_signals = create_trading_signals(data_with_indicators)

        # Generate trading signals
        if args.strategy == 'ma_crossover':
            logger.info("Applying Moving Average Crossover strategy...")
            strategy = MovingAverageCrossover(
                short_window=args.short_window,
                long_window=args.long_window
            )
            signals = strategy.generate_signals(data_with_signals)

        elif args.strategy == 'multi_ma':
            logger.info("Applying Multi-MA strategy...")
            strategy = MultiMAStrategy()
            signals = strategy.generate_signals(data_with_signals)

        elif args.strategy == 'ml_model':
            logger.info("Training ML model...")
            trainer, evaluation = train_ml_model(args, data_with_signals)

            # Use ML predictions as signals - only use the features the model was trained on
            data_for_pred = data_with_signals.dropna()
            X_pred = data_for_pred[trainer.feature_names]
            predictions = trainer.predict(X_pred)

            # Create signals dataframe matching the data_for_pred length
            signals = data_for_pred.copy()
            signals['Signal'] = 'HOLD'
            signals.loc[predictions == 1, 'Signal'] = 'BUY'
            signals.loc[predictions == 0, 'Signal'] = 'SELL'
            signals['Signal_Strength'] = 0.8

            # Update data_with_signals to match signals length
            data_with_signals = data_for_pred

        # Apply risk guardrails if requested
        if args.apply_risk:
            logger.info("Applying risk guardrails...")
            guardrails = RiskGuardrails(
                stop_loss_pct=args.stop_loss,
                take_profit_pct=args.take_profit
            )
            # Signals already modified by backtester's risk management
            logger.info("✅ Risk guardrails configured")

        # Run backtest
        if args.backtest:
            results = run_backtest(args, data_with_signals, signals)
            all_results[symbol] = results

        # Train model if requested
        if args.train_model and args.strategy != 'ml_model':
            trainer, evaluation = train_ml_model(args, data_with_signals)

    # Summary
    if all_results:
        logger.info(f"\n{'='*60}")
        logger.info("SUMMARY OF RESULTS")
        logger.info(f"{'='*60}\n")

        for symbol, results in all_results.items():
            logger.info(f"{symbol}:")
            logger.info(f"  Return: {results.total_return_pct:+.2f}%")
            logger.info(f"  Trades: {results.total_trades}")
            logger.info(f"  Win Rate: {results.win_rate:.2f}%")
            logger.info(f"  Sharpe: {results.sharpe_ratio:.2f}")
            logger.info(f"  Max Drawdown: {results.max_drawdown_pct:.2f}%")

    logger.info(f"\n{'='*60}")
    logger.info("PHASE 1 COMPLETE!")
    logger.info(f"{'='*60}\n")


if __name__ == "__main__":
    main()
