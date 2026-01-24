#!/usr/bin/env python3
"""
Leaderboard and Aggregated Metrics Report Generator
Computes stability scores and ranks models by multiple criteria
"""

import sys
import json
from pathlib import Path
from typing import Dict, List
import pandas as pd
import numpy as np

# Add paths
platform_path = Path(__file__).parent.parent
sys.path.insert(0, str(platform_path))


class LeaderboardGenerator:
    """Generates leaderboard and aggregated metrics from walk-forward results."""

    def __init__(self, results_csv: str, output_dir: str):
        """
        Initialize leaderboard generator.

        Args:
            results_csv: Path to window results CSV
            output_dir: Output directory for reports
        """
        self.results_csv = Path(results_csv)
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

        # Load results
        self.df = pd.read_csv(self.results_csv)

        print(f"Loaded {len(self.df)} window results")
        print(f"Symbols: {self.df['symbol'].unique().tolist()}")
        print(f"Models: {self.df['model'].unique().tolist()}")

    def generate(self) -> Dict:
        """Generate all leaderboard reports."""
        # Compute aggregated metrics
        agg_metrics = self._compute_aggregated_metrics()

        # Save aggregated metrics
        agg_file = self.output_dir / "03_agg_metrics.json"
        with open(agg_file, 'w') as f:
            json.dump(agg_metrics, f, indent=2)
        print(f"\n✅ Aggregated metrics saved to {agg_file}")

        # Generate leaderboard
        leaderboard_md = self._generate_leaderboard_markdown(agg_metrics)

        leaderboard_file = self.output_dir / "04_leaderboard.md"
        with open(leaderboard_file, 'w') as f:
            f.write(leaderboard_md)
        print(f"✅ Leaderboard saved to {leaderboard_file}")

        return agg_metrics

    def _compute_aggregated_metrics(self) -> Dict:
        """Compute aggregated metrics by (symbol, model)."""
        metrics = {}

        # Group by symbol and model
        grouped = self.df.groupby(['symbol', 'model'])

        for (symbol, model), group in grouped:
            key = f"{symbol}_{model}"

            # Basic statistics
            mean_sharpe = group['sharpe'].mean()
            median_sharpe = group['sharpe'].median()
            sharpe_std = group['sharpe'].std()
            mean_return = group['return'].mean()
            max_drawdown = group['max_drawdown'].max()
            p95_drawdown = group['max_drawdown'].quantile(0.95)
            mean_trades = group['trades'].mean()
            mean_win_rate = group['win_rate'].mean()
            mean_profit_factor = group['profit_factor'].mean()
            mean_turnover = group['turnover'].mean()

            # Stability score: mean sharpe / (1 + std)
            stability_score = mean_sharpe / (1 + sharpe_std) if sharpe_std >= 0 else 0

            # Hit rate: percentage of windows with positive returns
            hit_rate = (group['return'] > 0).sum() / len(group)

            # Windows count
            window_count = len(group)

            metrics[key] = {
                'symbol': symbol,
                'model': model,
                'mean_sharpe': float(mean_sharpe),
                'median_sharpe': float(median_sharpe),
                'sharpe_std': float(sharpe_std),
                'stability_score': float(stability_score),
                'mean_return': float(mean_return),
                'max_drawdown': float(max_drawdown),
                'p95_drawdown': float(p95_drawdown),
                'mean_trades': float(mean_trades),
                'mean_win_rate': float(mean_win_rate),
                'mean_profit_factor': float(mean_profit_factor),
                'mean_turnover': float(mean_turnover),
                'hit_rate': float(hit_rate),
                'window_count': int(window_count)
            }

        return metrics

    def _generate_leaderboard_markdown(self, metrics: Dict) -> str:
        """Generate leaderboard markdown."""
        md = []

        md.append("# LEADERBOARD REPORT")
        md.append("=" * 80)
        md.append("")
        md.append(f"Generated: {pd.Timestamp.now()}")
        md.append(f"Total evaluations: {len(self.df)}")
        md.append(f"Unique (symbol, model) pairs: {len(metrics)}")
        md.append("")

        # Create DataFrame for ranking
        metrics_df = pd.DataFrame.from_dict(metrics, orient='index')

        # Sort by stability score
        metrics_df = metrics_df.sort_values('stability_score', ascending=False)

        # Overall leaderboard
        md.append("## OVERALL LEADERBOARD (Ranking by Stability Score)")
        md.append("")
        md.append("Stability Score = Mean Sharpe / (1 + Sharpe Std)")
        md.append("Higher is better (rewarded for high returns, penalized for volatility)")
        md.append("")
        md.append("| Rank | Symbol | Model | Stability | Mean Sharpe | Sharpe Std | Mean Return | Max DD | Hit Rate | Trades |")
        md.append("|------|--------|-------|-----------|-------------|------------|-------------|---------|----------|--------|")

        for idx, (_, row) in enumerate(metrics_df.iterrows(), 1):
            md.append(
                f"| {idx} | {row['symbol']} | {row['model']} | "
                f"{row['stability_score']:.3f} | "
                f"{row['mean_sharpe']:.3f} | "
                f"{row['sharpe_std']:.3f} | "
                f"{row['mean_return']:.2%} | "
                f"{row['max_drawdown']:.2%} | "
                f"{row['hit_rate']:.2%} | "
                f"{row['mean_trades']:.1f} |"
            )

        md.append("")

        # Per-symbol rankings
        md.append("## PER-SYMBOL RANKINGS")
        md.append("")

        for symbol in sorted(self.df['symbol'].unique()):
            symbol_df = metrics_df[metrics_df['symbol'] == symbol].sort_values('stability_score', ascending=False)

            md.append(f"### {symbol}")
            md.append("")
            md.append("| Rank | Model | Stability | Mean Sharpe | Return | Max DD | Win Rate |")
            md.append("|------|-------|-----------|-------------|--------|---------|----------|")

            for idx, (_, row) in enumerate(symbol_df.iterrows(), 1):
                md.append(
                    f"| {idx} | {row['model']} | "
                    f"{row['stability_score']:.3f} | "
                    f"{row['mean_sharpe']:.3f} | "
                    f"{row['mean_return']:.2%} | "
                    f"{row['max_drawdown']:.2%} | "
                    f"{row['mean_win_rate']:.2%} |"
                )

            md.append("")

        # Best models per criteria
        md.append("## BEST MODELS BY CRITERIA")
        md.append("")

        # Best Sharpe
        best_sharpe = metrics_df.loc[metrics_df['mean_sharpe'].idxmax()]
        md.append(f"**Best Mean Sharpe:** {best_sharpe['model']} on {best_sharpe['symbol']} ({best_sharpe['mean_sharpe']:.3f})")

        # Best Stability
        best_stability = metrics_df.loc[metrics_df['stability_score'].idxmax()]
        md.append(f"**Best Stability:** {best_stability['model']} on {best_stability['symbol']} ({best_stability['stability_score']:.3f})")

        # Lowest Drawdown
        best_dd = metrics_df.loc[metrics_df['max_drawdown'].idxmin()]
        md.append(f"**Lowest Max Drawdown:** {best_dd['model']} on {best_dd['symbol']} ({best_dd['max_drawdown']:.2%})")

        # Highest Hit Rate
        best_hit = metrics_df.loc[metrics_df['hit_rate'].idxmax()]
        md.append(f"**Highest Hit Rate:** {best_hit['model']} on {best_hit['symbol']} ({best_hit['hit_rate']:.2%})")

        md.append("")

        # Model comparison
        md.append("## MODEL COMPARISON (Averaged Across Symbols)")
        md.append("")

        model_agg = metrics_df.groupby('model').agg({
            'mean_sharpe': 'mean',
            'stability_score': 'mean',
            'max_drawdown': 'max',
            'hit_rate': 'mean'
        }).sort_values('stability_score', ascending=False)

        md.append("| Model | Mean Sharpe | Mean Stability | Max DD | Hit Rate |")
        md.append("|-------|-------------|----------------|---------|----------|")

        for model, row in model_agg.iterrows():
            md.append(
                f"| {model} | "
                f"{row['mean_sharpe']:.3f} | "
                f"{row['stability_score']:.3f} | "
                f"{row['max_drawdown']:.2%} | "
                f"{row['hit_rate']:.2%} |"
            )

        md.append("")

        # Performance criteria summary
        md.append("## SUCCESS CRITERIA CHECK")
        md.append("")

        for _, row in metrics_df.iterrows():
            checks = []

            # Primary criteria
            if row['mean_sharpe'] > 0.5:
                checks.append("✅ Sharpe > 0.5")
            else:
                checks.append("❌ Sharpe < 0.5")

            if row['max_drawdown'] < 0.15:
                checks.append("✅ Max DD < 15%")
            else:
                checks.append("❌ Max DD ≥ 15%")

            if row['stability_score'] > 0.5:
                checks.append("✅ Stability > 0.5")
            else:
                checks.append("❌ Stability < 0.5")

            # Secondary criteria
            if row['mean_win_rate'] > 0.45:
                checks.append("✅ Win Rate > 45%")
            if row['mean_profit_factor'] > 1.2:
                checks.append("✅ Profit Factor > 1.2")
            if row['sharpe_std'] < 1.0:
                checks.append("✅ Sharpe Std < 1.0")

            # Disqualification checks
            if row['mean_sharpe'] < 0:
                checks.append("🚫 DISQUALIFIED: Negative Sharpe")
            if row['max_drawdown'] > 0.25:
                checks.append("🚫 DISQUALIFIED: Max DD > 25%")
            if row['mean_trades'] < 2:
                checks.append("🚫 DISQUALIFIED: Insufficient Trades")
            if row['hit_rate'] < 0.35:
                checks.append("🚫 DISQUALIFIED: Hit Rate < 35%")

            md.append(f"**{row['symbol']}_{row['model']}**")
            md.append(f"  {', '.join(checks)}")
            md.append("")

        return "\n".join(md)


def main():
    """CLI entry point."""
    import argparse

    parser = argparse.ArgumentParser(
        description='Generate leaderboard from walk-forward results'
    )
    parser.add_argument(
        'results_csv',
        help='Path to window results CSV'
    )
    parser.add_argument(
        '--out',
        type=str,
        required=True,
        help='Output directory'
    )

    args = parser.parse_args()

    # Generate leaderboard
    generator = LeaderboardGenerator(args.results_csv, args.out)
    metrics = generator.generate()

    print(f"\n✅ Leaderboard generation complete!")


if __name__ == "__main__":
    main()
