#!/usr/bin/env python3
"""
Regime Analysis and Labeler
Analyzes market regimes and model performance by regime
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


class RegimeAnalyzer:
    """Analyzes market regimes and model performance by regime."""

    def __init__(self, results_csv: str, output_dir: str):
        """
        Initialize regime analyzer.

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
        print(f"Regimes found: {self.df['regime'].unique().tolist()}")

    def analyze(self) -> Dict:
        """Analyze regimes and generate report."""
        # Compute regime statistics
        regime_stats = self._compute_regime_statistics()

        # Find best models per regime
        best_per_regime = self._find_best_models_per_regime()

        # Generate report
        report_md = self._generate_regime_report(regime_stats, best_per_regime)

        # Save report
        report_file = self.output_dir / "05_regime_analysis.md"
        with open(report_file, 'w') as f:
            f.write(report_md)

        print(f"\n✅ Regime analysis saved to {report_file}")

        return {
            'regime_stats': regime_stats,
            'best_per_regime': best_per_regime
        }

    def _compute_regime_statistics(self) -> Dict:
        """Compute statistics for each regime."""
        stats = {}

        for regime in self.df['regime'].unique():
            regime_df = self.df[self.df['regime'] == regime]

            stats[regime] = {
                'window_count': len(regime_df),
                'mean_sharpe': float(regime_df['sharpe'].mean()),
                'mean_return': float(regime_df['return'].mean()),
                'mean_drawdown': float(regime_df['max_drawdown'].mean()),
                'sharpe_std': float(regime_df['sharpe'].std())
            }

        return stats

    def _find_best_models_per_regime(self) -> Dict:
        """Find best performing model for each regime."""
        best_models = {}

        for regime in self.df['regime'].unique():
            regime_df = self.df[self.df['regime'] == regime]

            # Group by model and compute mean Sharpe
            model_performance = regime_df.groupby('model').agg({
                'sharpe': 'mean',
                'return': 'mean',
                'max_drawdown': 'max'
            }).sort_values('sharpe', ascending=False)

            # Get best model
            best_model = model_performance.index[0]
            best_sharpe = model_performance.iloc[0]['sharpe']

            best_models[regime] = {
                'model': best_model,
                'mean_sharpe': float(best_sharpe),
                'all_models': model_performance.to_dict('index')
            }

        return best_models

    def _generate_regime_report(self, regime_stats: Dict, best_per_regime: Dict) -> str:
        """Generate regime analysis markdown report."""
        md = []

        md.append("# REGIME ANALYSIS REPORT")
        md.append("=" * 80)
        md.append("")
        md.append(f"Generated: {pd.Timestamp.now()}")
        md.append("")

        # Regime distribution
        md.append("## REGIME DISTRIBUTION")
        md.append("")
        md.append("| Regime | Window Count | % of Total | Mean Sharpe | Mean Return | Mean DD |")
        md.append("|--------|-------------|------------|-------------|-------------|---------|")

        total_windows = len(self.df)

        for regime, stats in sorted(regime_stats.items()):
            pct = (stats['window_count'] / total_windows) * 100
            md.append(
                f"| {regime} | "
                f"{stats['window_count']} | "
                f"{pct:.1f}% | "
                f"{stats['mean_sharpe']:.3f} | "
                f"{stats['mean_return']:.2%} | "
                f"{stats['mean_drawdown']:.2%} |"
            )

        md.append("")

        # Best models per regime
        md.append("## BEST MODELS PER REGIME")
        md.append("")
        md.append("Ranked by mean Sharpe ratio within each regime")
        md.append("")

        for regime, data in sorted(best_per_regime.items()):
            md.append(f"### {regime}")
            md.append("")
            md.append(f"**Best Model:** {data['model']} (Sharpe: {data['mean_sharpe']:.3f})")
            md.append("")
            md.append("| Rank | Model | Mean Sharpe | Mean Return | Max DD |")
            md.append("|------|-------|-------------|-------------|---------|")

            for idx, (model, perf) in enumerate(sorted(
                data['all_models'].items(),
                key=lambda x: x[1]['sharpe'],
                reverse=True
            ), 1):
                md.append(
                    f"| {idx} | {model} | "
                    f"{perf['sharpe']:.3f} | "
                    f"{perf['return']:.2%} | "
                    f"{perf['max_drawdown']:.2%} |"
                )

            md.append("")

        # Regime-specific recommendations
        md.append("## REGIME-SPECIFIC RECOMMENDATIONS")
        md.append("")

        for regime, data in sorted(best_per_regime.items()):
            best_model = data['model']
            sharpe = data['mean_sharpe']

            if sharpe > 1.0:
                recommendation = f"**STRONG BUY** - Use {best_model} in {regime} conditions"
            elif sharpe > 0.5:
                recommendation = f"**BUY** - {best_model} performs well in {regime}"
            elif sharpe > 0:
                recommendation = f"**HOLD** - {best_model} marginal in {regime}, consider reducing position"
            else:
                recommendation = f"**AVOID** - {best_model} underperforms in {regime}"

            md.append(f"- {regime}: {recommendation}")

        md.append("")

        # Model robustness across regimes
        md.append("## MODEL ROBUSTNESS ACROSS REGIMES")
        md.append("")
        md.append("Consistency of model performance across different market conditions")
        md.append("")

        # Calculate per-model regime statistics
        model_regime_perf = {}

        for model in self.df['model'].unique():
            model_df = self.df[self.df['model'] == model]

            regime_perfs = []
            for regime in model_df['regime'].unique():
                regime_df = model_df[model_df['regime'] == regime]
                regime_perfs.append({
                    'regime': regime,
                    'sharpe': regime_df['sharpe'].mean()
                })

            # Calculate variance (lower is more robust)
            sharpe_vals = [r['sharpe'] for r in regime_perfs]
            sharpe_variance = np.var(sharpe_vals) if len(sharpe_vals) > 1 else 0

            model_regime_perf[model] = {
                'mean_sharpe': np.mean(sharpe_vals),
                'sharpe_variance': sharpe_variance,
                'regime_count': len(regime_perfs)
            }

        # Sort by robustness (low variance, high mean)
        sorted_models = sorted(
            model_regime_perf.items(),
            key=lambda x: (x[1]['sharpe_variance'], -x[1]['mean_sharpe'])
        )

        md.append("| Rank | Model | Mean Sharpe | Sharpe Variance | Robustness |")
        md.append("|------|-------|-------------|-----------------|------------|")

        for idx, (model, perf) in enumerate(sorted_models, 1):
            robustness = "HIGH" if perf['sharpe_variance'] < 0.5 else "MEDIUM" if perf['sharpe_variance'] < 1.0 else "LOW"
            md.append(
                f"| {idx} | {model} | "
                f"{perf['mean_sharpe']:.3f} | "
                f"{perf['sharpe_variance']:.3f} | "
                f"{robustness} |"
            )

        md.append("")

        # Regime transitions
        md.append("## REGIME TRANSITIONS")
        md.append("")
        md.append("Analysis of regime transitions in the evaluation period")
        md.append("")

        # Sort by window
        df_sorted = self.df.sort_values(['symbol', 'window_id'])

        transitions = []
        for symbol in df_sorted['symbol'].unique():
            symbol_df = df_sorted[df_sorted['symbol'] == symbol]
            prev_regime = None

            for _, row in symbol_df.iterrows():
                if prev_regime is not None and row['regime'] != prev_regime:
                    transitions.append({
                        'symbol': symbol,
                        'from': prev_regime,
                        'to': row['regime'],
                        'window': row['window_id']
                    })

                prev_regime = row['regime']

        if transitions:
            md.append(f"Total transitions detected: {len(transitions)}")
            md.append("")
            md.append("| Symbol | From | To | Window |")
            md.append("|--------|------|-----|--------|")

            for t in transitions[:10]:  # Show first 10
                md.append(f"| {t['symbol']} | {t['from']} | {t['to']} | {t['window']} |")

            if len(transitions) > 10:
                md.append(f"| ... | ... | ... | ... | ({len(transitions) - 10} more)")
        else:
            md.append("No regime transitions detected in evaluation period")

        md.append("")

        return "\n".join(md)


def main():
    """CLI entry point."""
    import argparse

    parser = argparse.ArgumentParser(
        description='Analyze regimes and model performance'
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

    # Analyze regimes
    analyzer = RegimeAnalyzer(args.results_csv, args.out)
    analyzer.analyze()

    print(f"\n✅ Regime analysis complete!")


if __name__ == "__main__":
    main()
