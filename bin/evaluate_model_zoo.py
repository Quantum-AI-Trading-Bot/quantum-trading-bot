#!/usr/bin/env python3
"""
Model Zoo Evaluator - Phase 2 Validation

Runs systematic evaluation of model combinations in DRY_RUN mode.
Generates leaderboard and shadow learning updates.

SAFETY: This script NEVER connects to IB or places orders.
All evaluations are offline using historical data.
"""

import sys
import os
import json
import csv
import logging
import argparse
import traceback
from pathlib import Path
from typing import Dict, List, Any, Tuple
from datetime import datetime, timedelta
from itertools import product

import numpy as np

# Add platform to path
sys.path.insert(0, str(Path(__file__).parent.parent))

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class ModelZooEvaluator:
    """Evaluator for Model Zoo combinations."""

    def __init__(self, config_path: str = None):
        """Initialize evaluator."""
        if config_path is None:
            config_path = "/home/davidsanker/platform/config/model_zoo.yaml"

        # Load config
        import yaml
        with open(config_path, 'r') as f:
            self.config = yaml.safe_load(f)

        # Setup paths
        self.base_dir = Path("/home/davidsanker/platform")
        self.state_dir = self.base_dir / "state"
        self.vpa_dir = self.base_dir / "vpa_storage"
        self.log_dir = self.base_dir / "logs"

        # Ensure directories exist
        self.state_dir.mkdir(exist_ok=True)
        self.vpa_dir.mkdir(exist_ok=True)
        self.log_dir.mkdir(exist_ok=True)

        # Load models
        from models.registry import get_registry
        self.registry = get_registry()

        # Load orchestrator
        from engine.model_orchestrator import ModelOrchestrator
        self.orchestrator = ModelOrchestrator(config_path)

        # Metrics storage
        self.results = []
        self.metrics_by_combo = {}

        logger.info("Model Zoo Evaluator initialized")

    def fetch_historical_data(self, symbol: str, days: int = 365) -> Dict[str, Any]:
        """
        Fetch historical data for symbol.

        Args:
            symbol: Stock symbol
            days: Number of days to fetch

        Returns:
            Dictionary with OHLCV data and indicators
        """
        logger.info(f"Fetching {days} days of data for {symbol}...")

        try:
            # Try yfinance
            import yfinance as yf

            # Fetch extra days for warmup
            end_date = datetime.now()
            start_date = end_date - timedelta(days=days + 50)

            ticker = yf.Ticker(symbol)
            df = ticker.history(start=start_date, end=end_date, interval="1d")

            if df is None or len(df) == 0:
                logger.warning(f"No data fetched for {symbol}, using synthetic")
                return self._generate_synthetic_data(symbol, days)

            # Convert to dict format
            data = {
                'symbol': symbol,
                'dates': df.index.strftime('%Y-%m-%d').tolist(),
                'open': df['Open'].tolist(),
                'high': df['High'].tolist(),
                'low': df['Low'].tolist(),
                'close': df['Close'].tolist(),
                'volume': df['Volume'].tolist(),
            }

            # Compute returns
            closes = data['close']
            returns = [0.0]  # First day no return
            for i in range(1, len(closes)):
                ret = (closes[i] - closes[i-1]) / closes[i-1]
                returns.append(ret)
            data['returns'] = returns

            # Compute indicators
            data['indicators'] = self._compute_indicators(data)

            logger.info(f"Fetched {len(data['dates'])} days for {symbol}")
            return data

        except ImportError:
            logger.warning("yfinance not available, using synthetic data")
            return self._generate_synthetic_data(symbol, days)
        except Exception as e:
            logger.error(f"Error fetching data for {symbol}: {e}")
            return self._generate_synthetic_data(symbol, days)

    def _compute_indicators(self, data: Dict[str, Any]) -> Dict[str, List]:
        """Compute technical indicators."""
        closes = np.array(data['close'])
        high = np.array(data['high'])
        low = np.array(data['low'])
        returns = np.array(data['returns'])

        indicators = {}

        # RSI (14)
        rsi_period = 14
        if len(closes) > rsi_period:
            deltas = np.diff(closes)
            gains = np.where(deltas > 0, deltas, 0)
            losses = np.where(deltas < 0, -deltas, 0)

            avg_gain = np.convolve(gains, np.ones(rsi_period)/rsi_period, mode='valid')
            avg_loss = np.convolve(losses, np.ones(rsi_period)/rsi_period, mode='valid')

            rs = avg_gain / (avg_loss + 1e-10)
            rsi = 100 - (100 / (1 + rs))

            # Pad with NaN to match length
            rsi_padded = [np.nan] * (rsi_period - 1) + rsi.tolist()
            indicators['RSI'] = rsi_padded
        else:
            indicators['RSI'] = [50.0] * len(closes)

        # MACD (12, 26, 9)
        if len(closes) > 26:
            ema12 = self._compute_ema(closes, 12)
            ema26 = self._compute_ema(closes, 26)
            macd_line = ema12 - ema26

            if len(macd_line) > 9:
                signal_line = self._compute_ema(macd_line, 9)
                macd = macd_line - signal_line

                # Pad
                macd_padded = [0.0] * (len(closes) - len(macd)) + macd.tolist()
                indicators['MACD'] = macd_padded
            else:
                indicators['MACD'] = [0.0] * len(closes)
        else:
            indicators['MACD'] = [0.0] * len(closes)

        # Bollinger Bands (20, 2)
        bb_period = 20
        if len(closes) > bb_period:
            sma20 = np.convolve(closes, np.ones(bb_period)/bb_period, mode='valid')
            std20 = [np.std(closes[i:i+bb_period]) for i in range(len(closes) - bb_period + 1)]

            upper_band = sma20 + 2 * np.array(std20)
            lower_band = sma20 - 2 * np.array(std20)

            # Pad
            upper_padded = [np.nan] * (bb_period - 1) + upper_band.tolist()
            lower_padded = [np.nan] * (bb_period - 1) + lower_band.tolist()
            indicators['BB_upper'] = upper_padded
            indicators['BB_lower'] = lower_padded
        else:
            indicators['BB_upper'] = [closes[0]] * len(closes)
            indicators['BB_lower'] = [closes[0]] * len(closes)

        # Moving Averages
        if len(closes) > 20:
            ma20 = np.convolve(closes, np.ones(20)/20, mode='valid')
            ma20_padded = [np.nan] * 19 + ma20.tolist()
            indicators['MA20'] = ma20_padded
        else:
            indicators['MA20'] = [closes[0]] * len(closes)

        if len(closes) > 50:
            ma50 = np.convolve(closes, np.ones(50)/50, mode='valid')
            ma50_padded = [np.nan] * 49 + ma50.tolist()
            indicators['MA50'] = ma50_padded
        else:
            indicators['MA50'] = [closes[0]] * len(closes)

        return indicators

    def _compute_ema(self, data: np.ndarray, period: int) -> np.ndarray:
        """Compute Exponential Moving Average."""
        alpha = 2 / (period + 1)
        ema = [data[0]]
        for i in range(1, len(data)):
            ema.append(alpha * data[i] + (1 - alpha) * ema[-1])
        return np.array(ema)

    def _generate_synthetic_data(self, symbol: str, days: int) -> Dict[str, Any]:
        """Generate synthetic price data for testing."""
        logger.info(f"Generating {days} days of synthetic data for {symbol}")

        np.random.seed(hash(symbol) % 10000)  # Reproducible per symbol

        # Initial price
        price = 100.0 + hash(symbol) % 100

        dates = []
        opens = []
        highs = []
        lows = []
        closes = []
        volumes = []
        returns = [0.0]

        base_date = datetime.now() - timedelta(days=days + 50)

        for i in range(days + 50):
            date = base_date + timedelta(days=i)

            # Skip weekends
            if date.weekday() >= 5:
                continue

            dates.append(date.strftime('%Y-%m-%d'))

            # Random walk with drift
            drift = 0.0002  # Slight upward drift
            shock = np.random.normal(0, 0.015)  # 1.5% daily volatility

            ret = drift + shock
            returns.append(ret)

            open_price = price * (1 + np.random.normal(0, 0.005))
            close_price = price * (1 + ret)

            # High and low
            high_price = max(open_price, close_price) * (1 + abs(np.random.normal(0, 0.005)))
            low_price = min(open_price, close_price) * (1 - abs(np.random.normal(0, 0.005)))

            opens.append(open_price)
            highs.append(high_price)
            lows.append(low_price)
            closes.append(close_price)
            volumes.append(np.random.randint(1000000, 10000000))

            price = close_price

        data = {
            'symbol': symbol,
            'dates': dates,
            'open': opens,
            'high': highs,
            'low': lows,
            'close': closes,
            'volume': volumes,
            'returns': returns,
            'indicators': self._compute_indicators({
                'close': closes,
                'high': highs,
                'low': lows,
                'returns': returns
            })
        }

        return data

    def build_features(self, data: Dict[str, Any], index: int) -> Dict[str, Any]:
        """Build features at given index."""
        # Ensure we have enough history
        lookback = 20
        start_idx = max(0, index - lookback)

        features = {
            'symbol': data['symbol'],
            'date': data['dates'][index],
            'prices': data['close'][start_idx:index+1],
            'returns': data['returns'][start_idx:index+1],
            'indicators': {}
        }

        # Add indicators at current index
        for key, values in data['indicators'].items():
            if index < len(values):
                features['indicators'][key] = values[index]
            else:
                features['indicators'][key] = values[-1] if values else 0.0

        return features

    def get_shadow_label(self, data: Dict[str, Any], index: int) -> float:
        """
        Get shadow label from next bar return.

        Returns:
            +1.0 if next return > 0.1%
            -1.0 if next return < -0.1%
            0.0 otherwise
        """
        if index + 1 >= len(data['returns']):
            return 0.0  # No next bar

        next_return = data['returns'][index + 1]

        if next_return > 0.001:  # > 0.1%
            return 1.0
        elif next_return < -0.001:  # < -0.1%
            return -1.0
        else:
            return 0.0

    def evaluate_model_combo(self,
                            forecast_model: str,
                            signal_model: str,
                            allocation_model: str,
                            execution_policy: str,
                            symbols: List[str],
                            eval_days: int = 365) -> List[Dict[str, Any]]:
        """
        Evaluate a single model combination.

        Returns:
            List of result dictionaries
        """
        combo_name = f"{forecast_model}_{signal_model}_{allocation_model}_{execution_policy}"
        logger.info(f"Evaluating combo: {combo_name}")

        # Update config for this combo
        self.config['FORECAST_MODEL'] = forecast_model
        self.config['SIGNAL_MODEL'] = signal_model
        self.config['ALLOCATION_MODEL'] = allocation_model
        self.config['EXECUTION_POLICY'] = execution_policy

        # Reinitialize orchestrator with new config
        # Write temp config file
        import tempfile
        import yaml
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            yaml.dump(self.config, f)
            temp_config_path = f.name

        from engine.model_orchestrator import ModelOrchestrator
        self.orchestrator = ModelOrchestrator(config_path=temp_config_path)

        results = []

        for symbol in symbols:
            logger.info(f"  Symbol: {symbol}")

            # Fetch data
            data = self.fetch_historical_data(symbol, eval_days + 20)

            if len(data['dates']) < eval_days:
                logger.warning(f"    Insufficient data: {len(data['dates'])} days")
                continue

            # Run evaluation (skip first 20 for warmup)
            warmup = 20
            for i in range(warmup, min(warmup + eval_days, len(data['dates']))):
                try:
                    # Build features
                    features = self.build_features(data, i)

                    # Get shadow label
                    shadow_label = self.get_shadow_label(data, i)

                    # Run orchestrator (DRY_RUN)
                    context = {
                        'symbol': symbol,
                        'portfolio': {
                            'cash': 100000.0,
                            'positions': {}
                        },
                        'prices': data['close'][i],
                        **features
                    }

                    decision = self.orchestrator.run_decision_cycle(
                        context=context,
                        dry_run=True
                    )

                    # Extract decision info
                    decision_plan = decision.get('decision_plan', {})

                    action = decision_plan.get('action', 'HOLD')
                    confidence = decision_plan.get('confidence', 0.5)
                    target_pct = decision_plan.get('target_value_pct', 0.0)

                    # Compute hit
                    hit = 0.0
                    if shadow_label != 0.0 and action in ['BUY', 'SELL']:
                        if (action == 'BUY' and shadow_label > 0) or \
                           (action == 'SELL' and shadow_label < 0):
                            hit = 1.0

                    # Record result
                    result = {
                        'symbol': symbol,
                        'date': features['date'],
                        'forecast_model': forecast_model,
                        'signal_model': signal_model,
                        'allocation_model': allocation_model,
                        'execution_policy': execution_policy,
                        'combo': combo_name,
                        'action': action,
                        'confidence': confidence,
                        'target_value_pct': target_pct,
                        'shadow_label': shadow_label,
                        'hit': hit,
                        'next_return': data['returns'][i+1] if i+1 < len(data['returns']) else 0.0
                    }

                    results.append(result)

                except Exception as e:
                    logger.error(f"    Error at index {i}: {e}")
                    results.append({
                        'symbol': symbol,
                        'date': data['dates'][i] if i < len(data['dates']) else 'unknown',
                        'forecast_model': forecast_model,
                        'signal_model': signal_model,
                        'allocation_model': allocation_model,
                        'execution_policy': execution_policy,
                        'combo': combo_name,
                        'action': 'ERROR',
                        'confidence': 0.0,
                        'target_value_pct': 0.0,
                        'shadow_label': 0.0,
                        'hit': 0.0,
                        'next_return': 0.0,
                        'error': str(e)
                    })

        # Cleanup temp config
        try:
            os.unlink(temp_config_path)
        except:
            pass

        logger.info(f"  Completed {len(results)} decisions for {combo_name}")
        return results

    def run_evaluation(self,
                      symbols: List[str] = None,
                      eval_days: int = 365) -> List[Dict[str, Any]]:
        """
        Run full evaluation across all model combinations.

        Args:
            symbols: List of symbols to evaluate
            eval_days: Number of days to evaluate

        Returns:
            List of all results
        """
        if symbols is None:
            symbols = ['SPY', 'QQQ', 'AAPL', 'MSFT', 'NVDA']

        logger.info(f"Starting evaluation for {len(symbols)} symbols over {eval_days} days")

        # Define model combinations
        forecast_models = ['ewma', 'ar1']
        signal_models = ['signal_generator', 'gradient_boosting']
        allocation_models = ['fixed', 'risk_parity']
        execution_policies = ['default']

        all_results = []

        # Iterate all combinations
        for forecast, signal, alloc, exec_policy in product(
            forecast_models,
            signal_models,
            allocation_models,
            execution_policies
        ):
            results = self.evaluate_model_combo(
                forecast_model=forecast,
                signal_model=signal,
                allocation_model=alloc,
                execution_policy=exec_policy,
                symbols=symbols,
                eval_days=eval_days
            )

            all_results.extend(results)

        logger.info(f"Evaluation complete: {len(all_results)} total decisions")
        self.results = all_results
        return all_results

    def compute_metrics(self, results: List[Dict[str, Any]]) -> Dict[str, Dict[str, float]]:
        """
        Compute metrics for each model combination.

        Returns:
            Dictionary mapping combo name to metrics
        """
        # Group by combo
        combos = {}
        for r in results:
            combo = r.get('combo', 'unknown')
            if combo not in combos:
                combos[combo] = []
            combos[combo].append(r)

        metrics = {}

        for combo, combo_results in combos.items():
            # Basic stats
            total_decisions = len(combo_results)
            buy_count = sum(1 for r in combo_results if r.get('action') == 'BUY')
            sell_count = sum(1 for r in combo_results if r.get('action') == 'SELL')
            hold_count = sum(1 for r in combo_results if r.get('action') == 'HOLD')

            # Decision frequencies
            buy_freq = buy_count / total_decisions if total_decisions > 0 else 0
            sell_freq = sell_count / total_decisions if total_decisions > 0 else 0
            hold_freq = hold_count / total_decisions if total_decisions > 0 else 0

            # Confidence stats
            confidences = [r.get('confidence', 0.5) for r in combo_results]
            conf_mean = np.mean(confidences) if confidences else 0.5
            conf_std = np.std(confidences) if len(confidences) > 1 else 0.0
            conf_above_threshold = sum(1 for c in confidences if c >= 0.75) / total_decisions if total_decisions > 0 else 0

            # Hit rate (only for BUY/SELL)
            trades = [r for r in combo_results if r.get('action') in ['BUY', 'SELL']]
            if trades:
                hit_rate = np.mean([r.get('hit', 0.0) for r in trades])
            else:
                hit_rate = 0.0

            # Brier score (for calibration)
            # Binary outcome: 1 if hit, 0 if miss
            if trades:
                brier_score = np.mean([(r.get('hit', 0.0) - r.get('confidence', 0.5))**2 for r in trades])
            else:
                brier_score = 1.0  # Max error

            # Activity score
            # 0 if no trades, 1 if balanced 50/50
            activity = min(1.0, (buy_freq + sell_freq) * 2)

            # Error rate
            error_count = sum(1 for r in combo_results if r.get('action') == 'ERROR')
            error_rate = error_count / total_decisions if total_decisions > 0 else 0

            # Position sizing
            targets = [r.get('target_value_pct', 0.0) for r in combo_results]
            max_target = max(targets) if targets else 0.0
            avg_target = np.mean(targets) if targets else 0.0

            # Overall score
            calibration_score = 1 - brier_score
            stability_score = 1 - error_rate

            overall_score = (
                0.30 * hit_rate +
                0.20 * calibration_score +
                0.20 * activity +
                0.15 * stability_score +
                0.15 * (1.0 if max_target <= 0.15 else 0.5)  # Penalty for exceeding cap
            )

            metrics[combo] = {
                'total_decisions': int(total_decisions),
                'buy_count': int(buy_count),
                'sell_count': int(sell_count),
                'hold_count': int(hold_count),
                'buy_freq': round(buy_freq, 4),
                'sell_freq': round(sell_freq, 4),
                'hold_freq': round(hold_freq, 4),
                'conf_mean': round(conf_mean, 4),
                'conf_std': round(conf_std, 4),
                'conf_above_threshold': round(conf_above_threshold, 4),
                'hit_rate': round(hit_rate, 4),
                'brier_score': round(brier_score, 4),
                'calibration_score': round(calibration_score, 4),
                'activity_score': round(activity, 4),
                'stability_score': round(stability_score, 4),
                'error_rate': round(error_rate, 4),
                'max_target_pct': round(max_target, 4),
                'avg_target_pct': round(avg_target, 4),
                'overall_score': round(overall_score, 4)
            }

        self.metrics_by_combo = metrics
        return metrics

    def save_results(self, results: List[Dict[str, Any]],
                    metrics: Dict[str, Dict[str, float]],
                    artifact_dir: str):
        """Save evaluation results to files."""
        artifact_path = Path(artifact_dir)
        artifact_path.mkdir(parents=True, exist_ok=True)

        # Save raw results CSV
        csv_path = artifact_path / "02_eval_results.csv"
        with open(csv_path, 'w', newline='') as f:
            if results:
                writer = csv.DictWriter(f, fieldnames=results[0].keys())
                writer.writeheader()
                writer.writerows(results)
        logger.info(f"Saved results to {csv_path}")

        # Save metrics JSON
        json_path = artifact_path / "eval_metrics.json"
        with open(json_path, 'w') as f:
            json.dump(metrics, f, indent=2)
        logger.info(f"Saved metrics to {json_path}")

        return csv_path, json_path


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Evaluate Model Zoo combinations")
    parser.add_argument('--symbols', nargs='+', default=['SPY', 'QQQ', 'AAPL', 'MSFT', 'NVDA'],
                       help='Symbols to evaluate')
    parser.add_argument('--days', type=int, default=365,
                       help='Number of days to evaluate')
    parser.add_argument('--artifact-dir', type=str, default=None,
                       help='Artifact directory (default: auto-generated)')
    parser.add_argument('--config', type=str, default=None,
                       help='Config file path')

    args = parser.parse_args()

    # Create artifact directory
    if args.artifact_dir is None:
        artifact_dir = f"/home/davidsanker/logs/model_zoo_phase2_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    else:
        artifact_dir = args.artifact_dir

    print("=" * 80)
    print("MODEL ZOO PHASE 2 EVALUATION")
    print("=" * 80)
    print(f"Symbols: {args.symbols}")
    print(f"Days: {args.days}")
    print(f"Artifact Dir: {artifact_dir}")
    print(f"Mode: DRY_RUN (safe, no trading)")
    print("=" * 80)
    print()

    try:
        # Initialize evaluator
        evaluator = ModelZooEvaluator(config_path=args.config)

        # Run evaluation
        print("Starting evaluation...")
        results = evaluator.run_evaluation(
            symbols=args.symbols,
            eval_days=args.days
        )

        print(f"✓ Completed {len(results)} decision evaluations")

        # Compute metrics
        print("\nComputing metrics...")
        metrics = evaluator.compute_metrics(results)
        print(f"✓ Computed metrics for {len(metrics)} model combinations")

        # Save results
        print(f"\nSaving results to {artifact_dir}...")
        csv_path, json_path = evaluator.save_results(results, metrics, artifact_dir)

        print("\n" + "=" * 80)
        print("EVALUATION COMPLETE")
        print("=" * 80)
        print(f"Results: {csv_path}")
        print(f"Metrics: {json_path}")
        print(f"Artifact Dir: {artifact_dir}")
        print("=" * 80)

        # Show top 3 models
        print("\nTOP 3 MODEL COMBINATIONS:")
        sorted_combos = sorted(metrics.items(), key=lambda x: x[1]['overall_score'], reverse=True)
        for i, (combo, metric) in enumerate(sorted_combos[:3], 1):
            print(f"\n{i}. {combo}")
            print(f"   Overall Score: {metric['overall_score']:.4f}")
            print(f"   Hit Rate: {metric['hit_rate']:.4f}")
            print(f"   Activity: {metric['activity_score']:.4f}")
            print(f"   Calibration: {metric['calibration_score']:.4f}")

        print("\n✓ Phase 2 evaluation complete!")
        print(f"✓ Review artifacts in: {artifact_dir}")

        return 0

    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
