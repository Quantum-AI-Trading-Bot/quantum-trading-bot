#!/usr/bin/env python3
"""
Phase 1 Backtest to VPA Artifact Generator
Converts Phase 1 backtest decisions into Verifiable Prediction Artifacts
"""

import sys
import json
import hashlib
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, List
import argparse

# Add platform to path
platform_path = Path(__file__).parent.parent
sys.path.insert(0, str(platform_path))


class VPAGenerator:
    """Generates VPA artifacts from Phase 1 backtest results."""

    def __init__(self, vpa_storage_dir: str = "/home/davidsanker/platform/vpa_storage"):
        self.vpa_storage_dir = Path(vpa_storage_dir)
        self.vpa_storage_dir.mkdir(parents=True, exist_ok=True)

    def generate_vpas_from_backtest(
        self,
        backtest_json_path: str,
        max_vpas: int = 50,
        backtest_id: str = None
    ) -> List[str]:
        """
        Generate VPA artifacts from a Phase 1 backtest.

        Args:
            backtest_json_path: Path to Phase 1 backtest JSON
            max_vpas: Maximum number of VPAs to generate (limit for storage)
            backtest_id: Optional backtest ID

        Returns:
            List of generated VPA file paths
        """
        # Load backtest
        with open(backtest_json_path, 'r') as f:
            backtest = json.load(f)

        # Generate backtest ID if not provided
        if backtest_id is None:
            backtest_id = self._generate_backtest_id(backtest_json_path, backtest)

        print(f"\nGenerating VPAs from backtest: {backtest_id}")
        print(f"Backtest file: {backtest_json_path}")
        print(f"Total trades in backtest: {len(backtest.get('trades', []))}")
        print(f"Max VPAs to generate: {max_vpas}")

        # Get code hash for reproducibility
        code_hash = self._get_code_hash()

        vpa_files = []
        trades = backtest.get('trades', [])

        # Limit number of VPAs
        trades_to_process = trades[:max_vpas]

        for i, trade in enumerate(trades_to_process):
            try:
                vpa = self._create_vpa(
                    trade,
                    backtest,
                    backtest_id,
                    i,
                    code_hash
                )

                # Save VPA
                vpa_filename = f"vpa_phase1_{backtest_id}_decision_{i}.json"
                vpa_path = self.vpa_storage_dir / vpa_filename

                with open(vpa_path, 'w') as f:
                    json.dump(vpa, f, indent=2)

                vpa_files.append(str(vpa_path))

                if (i + 1) % 10 == 0:
                    print(f"  Generated {i + 1}/{len(trades_to_process)} VPAs...")

            except Exception as e:
                print(f"  Warning: Failed to generate VPA for trade {i}: {e}")

        print(f"\n✅ Generated {len(vpa_files)} VPA artifacts")
        print(f"   Location: {self.vpa_storage_dir}")

        return vpa_files

    def _generate_backtest_id(self, json_path: str, backtest: Dict) -> str:
        """Generate backtest ID."""
        path = Path(json_path)
        symbol = backtest.get('symbol', 'UNKNOWN').lower()
        stem = path.stem
        parts = stem.split('_')
        if len(parts) >= 4:
            timestamp = '_'.join(parts[-2:])
        else:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')

        strategy = backtest.get('strategy_name', 'backtest').lower()
        return f"{symbol}_{strategy}_{timestamp}"

    def _get_code_hash(self) -> str:
        """Get hash of Phase 1 code for reproducibility."""
        # For now, return a placeholder
        # In production, this would compute git hash or file hash
        return "phase1_v1.0_placeholder"

    def _create_vpa(
        self,
        trade: Dict,
        backtest: Dict,
        backtest_id: str,
        decision_index: int,
        code_hash: str
    ) -> Dict:
        """Create a VPA artifact from a trade decision."""

        entry_time = trade.get('entry_time', '')
        symbol = trade.get('symbol', 'UNKNOWN')
        action = trade.get('action', 'HOLD')

        # Compute feature hash (simplified - we don't have full features in trade JSON)
        feature_hash = hashlib.sha256(
            json.dumps({
                'symbol': symbol,
                'entry_price': trade.get('entry_price'),
                'action': action
            }, sort_keys=True).encode()
        ).hexdigest()[:16]

        # Determine if this was a win/loss
        pnl = trade.get('pnl', 0.0)
        is_win = pnl > 0

        vpa = {
            "timestamp": entry_time,
            "track": "B",  # Backtest track
            "mode": "simulation",
            "predictions": {
                "symbol": symbol,
                "action": action,
                "confidence": 0.8,
                "model_name": f"phase1_{backtest.get('strategy_name', 'backtest')}",
                "model_version": "1.0.0"
            },
            "risk_metrics": {
                "stop_loss": 0.02,
                "take_profit": 0.05,
                "position_size": 0.95
            },
            "decision_plan": {
                "action": action,
                "reason": self._generate_decision_reason(trade, backtest),
                "signal_strength": 0.8,
                "entry_price": trade.get('entry_price', 0.0),
                "target_exit": trade.get('exit_price', 0.0),
                "stop_price": trade.get('entry_price', 0.0) * 0.98  # Assume 2% stop
            },
            "features": {
                "feature_hash": feature_hash,
                "features": {
                    "entry_price": trade.get('entry_price', 0.0),
                    "quantity": trade.get('quantity', 0)
                }
            },
            "metadata": {
                "source": "phase1_backtest",
                "backtest_id": backtest_id,
                "decision_id": f"phase1_{backtest_id}_decision_{decision_index}",
                "phase1_strategy": backtest.get('strategy_name', 'backtest'),
                "phase1_params": {
                    "initial_capital": backtest.get('initial_capital'),
                    "period": backtest.get('period')
                },
                "outcome_label": {
                    "pnl_pct": trade.get('pnl_percent', 0.0),
                    "pnl_abs": pnl,
                    "win": is_win,
                    "exit_reason": trade.get('exit_reason', 'unknown')
                }
            },
            "reproducibility": {
                "code_hash": code_hash,
                "data_hash": "phase1_data_placeholder",
                "random_seed": 42,
                "deterministic": True
            }
        }

        return vpa

    def _generate_decision_reason(self, trade: Dict, backtest: Dict) -> str:
        """Generate human-readable decision reason."""
        action = trade.get('action', 'HOLD')
        strategy = backtest.get('strategy_name', 'backtest')

        if strategy == 'Backtest':
            # This is likely MA crossover
            if action == 'BUY':
                return "Moving Average Crossover: Golden Cross signal"
            elif action == 'SELL':
                return "Moving Average Crossover: Death Cross signal"
            else:
                return "No clear crossover signal"
        else:
            return f"{strategy} generated {action} signal"


def main():
    """CLI entry point."""
    parser = argparse.ArgumentParser(
        description='Generate VPA artifacts from Phase 1 backtest results'
    )
    parser.add_argument(
        'backtest_json',
        help='Path to Phase 1 backtest JSON file'
    )
    parser.add_argument(
        '--max-vpas',
        type=int,
        default=50,
        help='Maximum number of VPAs to generate (default: 50)'
    )
    parser.add_argument(
        '--backtest-id',
        help='Custom backtest ID (auto-generated if not provided)'
    )
    parser.add_argument(
        '--vpa-dir',
        default='/home/davidsanker/platform/vpa_storage',
        help='VPA storage directory'
    )

    args = parser.parse_args()

    # Validate input
    if not Path(args.backtest_json).exists():
        print(f"Error: File not found: {args.backtest_json}")
        sys.exit(1)

    # Generate VPAs
    generator = VPAGenerator(vpa_storage_dir=args.vpa_dir)

    try:
        vpa_files = generator.generate_vpas_from_backtest(
            args.backtest_json,
            max_vpas=args.max_vpas,
            backtest_id=args.backtest_id
        )

        print("\n✅ VPA generation complete!")
        print(f"\nSample VPA files:")
        for f in vpa_files[:3]:
            print(f"  - {f}")

        if len(vpa_files) > 3:
            print(f"  ... and {len(vpa_files) - 3} more")

        sys.exit(0)

    except Exception as e:
        print(f"\n❌ VPA generation failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
