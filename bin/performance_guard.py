#!/usr/bin/env python3
"""
Performance Guard
Monitors trading performance and auto-falls back to DRY_RUN if metrics degrade
"""

import sys
import os
import json
from pathlib import Path
from datetime import datetime, timedelta
import logging

# Add platform to path
platform_path = Path(__file__).parent.parent
sys.path.insert(0, str(platform_path))

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)s | %(message)s'
)
logger = logging.getLogger(__name__)

# Configuration
OUTCOMES_FILE = platform_path / "state/ledgers/outcomes.jsonl"
RUNTIME_ENV = platform_path / "config/quantum_runtime.env"
INCIDENTS_DIR = platform_path / "logs/incidents"

# Performance thresholds
MIN_HIT_RATE = 0.48  # Below 48% hit rate → trigger fallback
MAX_DAILY_DRAWDOWN_PCT = 0.01  # More than 1% daily drawdown → trigger fallback
MIN_OUTCOMES = 10  # Need at least 10 outcomes before evaluating

def load_recent_outcomes(n=50):
    """Load the last N outcomes."""
    if not OUTCOMES_FILE.exists():
        return []

    outcomes = []
    with open(OUTCOMES_FILE, 'r') as f:
        for line in f:
            try:
                outcome = json.loads(line.strip())
                outcomes.append(outcome)
            except:
                continue

    return outcomes[-n:]

def calculate_metrics(outcomes):
    """Calculate performance metrics from outcomes."""
    if len(outcomes) < MIN_OUTCOMES:
        return None

    # Count wins and losses
    wins = 0
    losses = 0
    total_pnl = 0.0

    for outcome in outcomes:
        pnl = outcome.get('pnl', 0)
        total_pnl += pnl

        if pnl > 0:
            wins += 1
        elif pnl < 0:
            losses += 1

    total = wins + losses
    if total == 0:
        return None

    hit_rate = wins / total if total > 0 else 0

    # Calculate max drawdown
    peak = float('-inf')
    max_drawdown = 0.0
    cumulative_pnl = 0.0

    for outcome in outcomes:
        pnl = outcome.get('pnl', 0)
        cumulative_pnl += pnl

        if cumulative_pnl > peak:
            peak = cumulative_pnl

        drawdown = (peak - cumulative_pnl) / peak if peak > 0 else 0
        if drawdown > max_drawdown:
            max_drawdown = drawdown

    return {
        'total_outcomes': total,
        'wins': wins,
        'losses': losses,
        'hit_rate': hit_rate,
        'total_pnl': total_pnl,
        'max_drawdown_pct': max_drawdown,
        'average_pnl': total_pnl / total if total > 0 else 0
    }

def trigger_fallback(reason, metrics):
    """Trigger fallback to DRY_RUN mode."""
    logger.error(f"⚠️ PERFORMANCE GUARD TRIGGERED: {reason}")

    # Write incident report
    INCIDENTS_DIR.mkdir(parents=True, exist_ok=True)
    incident_file = INCIDENTS_DIR / f"incident_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.json"

    incident = {
        'timestamp': datetime.utcnow().isoformat(),
        'trigger': reason,
        'metrics': metrics,
        'action': 'FALLBACK_TO_DRY_RUN'
    }

    with open(incident_file, 'w') as f:
        json.dump(incident, f, indent=2)

    logger.error(f"📄 Incident report written: {incident_file}")

    # Update runtime config to DRY_RUN
    if not RUNTIME_ENV.exists():
        logger.error("Runtime env file not found")
        return False

    # Read current config
    with open(RUNTIME_ENV, 'r') as f:
        lines = f.readlines()

    # Update DRY_RUN setting
    updated_lines = []
    for line in lines:
        if line.startswith('QUANTUM_EXECUTION_DRY_RUN='):
            updated_lines.append('QUANTUM_EXECUTION_DRY_RUN=true  # AUTO-FALLBACK by performance guard\n')
        elif line.startswith('QUANTUM_EXECUTION_ENABLED='):
            updated_lines.append('QUANTUM_EXECUTION_ENABLED=false  # AUTO-DISABLED by performance guard\n')
        else:
            updated_lines.append(line)

    # Write back
    with open(RUNTIME_ENV, 'w') as f:
        f.writelines(updated_lines)

    logger.error("✅ System fallen back to DRY_RUN mode")
    logger.error("✅ Trading execution disabled")
    logger.error("📧 Manual intervention required")

    return True

def main():
    """Main execution."""
    logger.info("=" * 60)
    logger.info("PERFORMANCE GUARD CHECK")
    logger.info("=" * 60)

    # Load recent outcomes
    outcomes = load_recent_outcomes(n=50)
    logger.info(f"Loaded {len(outcomes)} recent outcomes")

    if len(outcomes) < MIN_OUTCOMES:
        logger.info(f"Insufficient outcomes ({len(outcomes)} < {MIN_OUTCOMES}) - skipping evaluation")
        return 0

    # Calculate metrics
    metrics = calculate_metrics(outcomes)
    if not metrics:
        logger.warning("Could not calculate metrics")
        return 1

    logger.info(f"Metrics: {json.dumps(metrics, indent=2)}")

    # Check hit rate
    if metrics['hit_rate'] < MIN_HIT_RATE:
        reason = f"Hit rate ({metrics['hit_rate']:.2%}) below threshold ({MIN_HIT_RATE:.2%})"
        trigger_fallback(reason, metrics)
        return 1

    # Check drawdown
    if metrics['max_drawdown_pct'] > MAX_DAILY_DRAWDOWN_PCT:
        reason = f"Max drawdown ({metrics['max_drawdown_pct']:.2%}) exceeds threshold ({MAX_DAILY_DRAWDOWN_PCT:.2%})"
        trigger_fallback(reason, metrics)
        return 1

    # All checks passed
    logger.info("✅ All performance checks passed")
    logger.info(f"✅ Hit rate: {metrics['hit_rate']:.2%} (threshold: {MIN_HIT_RATE:.2%})")
    logger.info(f"✅ Max drawdown: {metrics['max_drawdown_pct']:.2%} (threshold: {MAX_DAILY_DRAWDOWN_PCT:.2%})")

    return 0

if __name__ == "__main__":
    sys.exit(main())
