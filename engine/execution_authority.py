"""
Execution Authority Module - Time-Bounded Autonomy

Enforces temporal and safety constraints on trading execution.
FAIL-CLOSED: If any check fails, execution is blocked with detailed reason.

Author: Autonomous Trading System
Date: 2026-01-24
Purpose: Monday 2026-01-26 autonomous paper trading deployment
"""

import os
import sys
from pathlib import Path
from datetime import datetime, time, timezone
from typing import Dict, Any, Tuple
import yaml


class ExecutionAuthority:
    """
    Determines if execution is permitted RIGHT NOW based on:
    - Time windows (Europe/Berlin timezone)
    - Emergency stop file
    - Paper proof requirement
    - Market hours guard
    - Dry run status
    - Paper execution mode
    """

    # Reason codes for blocking
    REASON_CODES = {
        'NOT_IN_WINDOW': 'Outside configured trading window',
        'EMERGENCY_STOP': 'EMERGENCY_STOP file exists',
        'DRY_RUN': 'QUANTUM_EXECUTION_DRY_RUN is true (autonomy disabled)',
        'PAPER_MODE_OFF': 'PAPER_EXECUTION_MODE is false',
        'PAPER_PROOF_FAIL': 'Paper account assertion failed',
        'CONFIG_INVALID': 'Execution authority config invalid',
        'MARKET_CLOSED': 'Market is currently closed',
        'WEEKEND': 'Weekend trading not allowed',
        'ALLOWED': 'Execution permitted',
    }

    def __init__(self, config_path: str = None):
        """Load execution authority configuration."""
        self.platform_path = Path(__file__).parent.parent
        self.config_path = Path(config_path or self.platform_path / 'config' / 'execution_authority.yaml')

        # Load config
        self.config = self._load_config()
        self.timezone_name = self.config.get('timezone', 'Europe/Berlin')

    def _load_config(self) -> Dict[str, Any]:
        """Load execution authority YAML config."""
        if not self.config_path.exists():
            # Fail-closed with default restrictive config
            return {
                'mode': 'disabled',
                'timezone': 'Europe/Berlin',
                'allow_weekends': False,
                'require_paper_proof': True,
                'require_market_hours_guard': True,
                'kill_switch_file': 'EMERGENCY_STOP',
            }

        try:
            with open(self.config_path, 'r') as f:
                config = yaml.safe_load(f)
                return config
        except Exception as e:
            print(f"ERROR: Failed to load execution authority config: {e}", file=sys.stderr)
            return {'mode': 'disabled'}

    def check(self, override_time: str = None) -> Dict[str, Any]:
        """
        Check if execution is permitted RIGHT NOW.

        Args:
            override_time: Test-only ISO timestamp to override current time

        Returns:
            Dict with:
                - allowed: bool
                - reason_code: str (from REASON_CODES)
                - details: dict with additional context
                - authority_stamp: str (deterministic stamp for receipts)
        """
        # Generate authority stamp first (for audit trail)
        authority_stamp = self._generate_authority_stamp(override_time)

        # Check 1: Kill switch (EMERGENCY_STOP file)
        kill_switch_file = os.getenv('EMERGENCY_STOP_FILE', self.config.get('kill_switch_file', 'EMERGENCY_STOP'))
        if Path(kill_switch_file).exists():
            return {
                'allowed': False,
                'reason_code': 'EMERGENCY_STOP',
                'details': {
                    'kill_switch_file': kill_switch_file,
                    'message': 'Emergency stop file exists - all execution halted',
                },
                'authority_stamp': authority_stamp,
            }

        # Check 2: DRY_RUN status
        dry_run = os.getenv('QUANTUM_EXECUTION_DRY_RUN', 'true').lower()
        if dry_run == 'true':
            return {
                'allowed': False,
                'reason_code': 'DRY_RUN',
                'details': {
                    'dry_run': True,
                    'message': 'QUANTUM_EXECUTION_DRY_RUN=true prevents real execution',
                    'fix': 'Set QUANTUM_EXECUTION_DRY_RUN=false for autonomy',
                },
                'authority_stamp': authority_stamp,
            }

        # Check 3: PAPER_EXECUTION_MODE
        paper_mode = os.getenv('PAPER_EXECUTION_MODE', 'false').lower()
        if paper_mode != 'true':
            return {
                'allowed': False,
                'reason_code': 'PAPER_MODE_OFF',
                'details': {
                    'paper_execution_mode': paper_mode,
                    'message': 'PAPER_EXECUTION_MODE is not true',
                    'fix': 'Set PAPER_EXECUTION_MODE=true for paper trading',
                },
                'authority_stamp': authority_stamp,
            }

        # Check 4: ALLOW_LIVE (final hard ban)
        allow_live = os.getenv('ALLOW_LIVE', 'false').lower()
        if allow_live != 'false':
            return {
                'allowed': False,
                'reason_code': 'CONFIG_INVALID',
                'details': {
                    'allow_live': allow_live,
                    'message': 'ALLOW_LIVE is not false - CANNOT PROCEED',
                    'fix': 'Set ALLOW_LIVE=false to ensure paper trading only',
                },
                'authority_stamp': authority_stamp,
            }

        # Check 5: IB Port (must be 4002 for paper)
        ib_port = os.getenv('IB_PORT', '')
        if ib_port != '4002':
            return {
                'allowed': False,
                'reason_code': 'PAPER_PROOF_FAIL',
                'details': {
                    'ib_port': ib_port,
                    'message': 'IB_PORT is not 4002 (paper port)',
                    'fix': 'Set IB_PORT=4002 for paper trading',
                },
                'authority_stamp': authority_stamp,
            }

        # Check 6: Time window
        window_check = self._check_time_window(override_time)
        if not window_check['allowed']:
            return {
                'allowed': False,
                'reason_code': window_check['reason_code'],
                'details': window_check['details'],
                'authority_stamp': authority_stamp,
            }

        # All checks passed
        return {
            'allowed': True,
            'reason_code': 'ALLOWED',
            'details': {
                'message': 'All authority checks passed',
                'timezone': self.timezone_name,
                'window': self._get_current_window_description(),
            },
            'authority_stamp': authority_stamp,
        }

    def _check_time_window(self, override_time: str = None) -> Dict[str, Any]:
        """Check if current time is within configured trading windows."""
        try:
            # Get current time (or override for testing)
            if override_time:
                now = datetime.fromisoformat(override_time)
            else:
                now = datetime.now(timezone.utc)

            # Convert to configured timezone
            import pytz
            tz = pytz.timezone(self.timezone_name)
            now_local = now.astimezone(tz)

            # Check weekend
            if not self.config.get('allow_weekends', False):
                # Monday=0, ..., Sunday=6
                if now_local.weekday() >= 5:  # Saturday or Sunday
                    return {
                        'allowed': False,
                        'reason_code': 'WEEKEND',
                        'details': {
                            'day': now_local.strftime('%A'),
                            'date': now_local.date().isoformat(),
                            'message': 'Weekend trading not allowed',
                        },
                    }

            # Check time windows
            windows = self.config.get('windows', [])
            if not windows:
                return {
                    'allowed': False,
                    'reason_code': 'CONFIG_INVALID',
                    'details': {
                        'message': 'No time windows configured in execution_authority.yaml',
                    },
                }

            current_time = now_local.time()
            for window in windows:
                allowed_days = window.get('days', [])
                if now_local.strftime('%a') not in allowed_days:
                    continue

                start_time = time.fromisoformat(window['start'])
                end_time = time.fromisoformat(window['end'])

                if start_time <= current_time <= end_time:
                    return {
                        'allowed': True,
                        'reason_code': 'ALLOWED',
                        'details': {
                            'window': window,
                            'current_time': now_local.isoformat(),
                        },
                    }

            # Not in any window
            return {
                'allowed': False,
                'reason_code': 'NOT_IN_WINDOW',
                'details': {
                    'current_time': now_local.isoformat(),
                    'current_day': now_local.strftime('%A'),
                    'windows': windows,
                    'message': f'Current time {current_time} is outside configured windows',
                },
            }

        except Exception as e:
            return {
                'allowed': False,
                'reason_code': 'CONFIG_INVALID',
                'details': {
                    'error': str(e),
                    'message': 'Error checking time window',
                },
            }

    def _generate_authority_stamp(self, override_time: str = None) -> str:
        """Generate deterministic authority stamp for audit trail."""
        if override_time:
            now = datetime.fromisoformat(override_time)
        else:
            now = datetime.now(timezone.utc)

        stamp = f"AUTH_{now.strftime('%Y%m%d_%H%M%S')}_UTC"
        return stamp

    def _get_current_window_description(self) -> str:
        """Get description of current valid window."""
        windows = self.config.get('windows', [])
        if not windows:
            return "No windows configured"

        descriptions = []
        for window in windows:
            days = ', '.join(window.get('days', []))
            desc = f"{days} {window['start']}-{window['end']}"
            descriptions.append(desc)

        return '; '.join(descriptions)


def main():
    """CLI for testing execution authority."""
    import argparse

    parser = argparse.ArgumentParser(description='Check execution authority')
    parser.add_argument('--override-time', help='Override current time (ISO format)')
    args = parser.parse_args()

    authority = ExecutionAuthority()
    result = authority.check(override_time=args.override_time)

    print("Execution Authority Check")
    print("=" * 60)
    print(f"Allowed: {result['allowed']}")
    print(f"Reason Code: {result['reason_code']}")
    print(f"Authority Stamp: {result['authority_stamp']}")
    print()
    print("Details:")
    for key, value in result['details'].items():
        print(f"  {key}: {value}")

    return 0 if result['allowed'] else 1


if __name__ == '__main__':
    sys.exit(main())
