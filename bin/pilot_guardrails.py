#!/usr/bin/env python3
"""
Paper Trading Pilot Guardrails Enforcement
Enforces strict safety checks before allowing any order placement in pilot mode
"""

import sys
import os
from pathlib import Path
from datetime import datetime
import logging

# Add platform to path
platform_path = Path(__file__).parent.parent
sys.path.insert(0, str(platform_path))

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# CRITICAL CONSTANTS
PAPER_PORT = 4002
ALLOW_LIVE = False  # HARD BAN - never allow live trading
MAX_TARGET_VALUE_PCT = 0.005  # 0.5% max per trade
MAX_ORDERS_PER_DAY = 3
PILOT_END_UTC = "2026-01-31T23:59:59"
PILOT_SYMBOLS = ['SPY']


class PilotGuardrails:
    """Enforces pilot mode safety constraints."""

    def __init__(self):
        self.config = self._load_config()
        logger.info("Pilot Guardrails Initialized")

    def _load_config(self) -> dict:
        """Load pilot configuration from environment."""
        config = {}

        # Load from quantum_runtime.env
        env_file = Path('/home/davidsanker/platform/config/quantum_runtime.env')
        if env_file.exists():
            with open(env_file, 'r') as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith('#') and '=' in line:
                        key, value = line.split('=', 1)
                        config[key.strip()] = value.strip()

        return config

    def check_all_guards(self, symbol: str, action: str, target_value_pct: float) -> tuple:
        """
        Run all safety checks before order placement.

        Returns:
            (allowed: bool, reason: str)
        """
        logger.info("=" * 60)
        logger.info("PILOT GUARDRAILS CHECK")
        logger.info("=" * 60)

        checks = []

        # Check 1: Paper account proof
        allowed, reason = self._check_paper_account_proof()
        checks.append(('Paper Account Proof', allowed, reason))

        # Check 2: Allow Live ban
        allowed, reason = self._check_allow_live()
        checks.append(('Live Trading Ban', allowed, reason))

        # Check 3: Pilot symbols
        allowed, reason = self._check_pilot_symbols(symbol)
        checks.append(('Pilot Symbol Whitelist', allowed, reason))

        # Check 4: Target value cap
        allowed, reason = self._check_target_value_cap(target_value_pct)
        checks.append(('Target Value Cap', allowed, reason))

        # Check 5: Orders per day cap
        allowed, reason = self._check_orders_per_day_cap()
        checks.append(('Daily Orders Cap', allowed, reason))

        # Check 6: Market hours
        allowed, reason = self._check_market_hours()
        checks.append(('Market Hours', allowed, reason))

        # Check 7: Pilot timeout
        allowed, reason = self._check_pilot_timeout()
        checks.append(('Pilot Timeout', allowed, reason))

        # Check 8: Kill switch
        allowed, reason = self._check_kill_switch()
        checks.append(('Emergency Stop', allowed, reason))

        # Print results
        logger.info("")
        for name, allowed, reason in checks:
            status = "✅ ALLOW" if allowed else "❌ BLOCK"
            logger.info(f"{status}: {name:30s} - {reason}")

        logger.info("")

        # Overall decision
        all_allowed = all(allowed for _, allowed, _ in checks)

        if all_allowed:
            logger.info("✅ ALL GUARDRAILS PASSED - ORDER ALLOWED")
        else:
            logger.error("❌ GUARDRAIL FAILED - ORDER BLOCKED")

        return all_allowed, "All checks passed" if all_allowed else "Guardrail tripped"

    def _check_paper_account_proof(self) -> tuple:
        """Check if paper account proof exists and is recent."""
        stamp_file = Path('/home/davidsanker/platform/state/paper_account_ok.txt')

        if not stamp_file.exists():
            return False, "Paper account proof not found - run assert_paper_account.py"

        # Check timestamp (must be within last hour)
        try:
            with open(stamp_file, 'r') as f:
                content = f.read()
                for line in content.split('\n'):
                    if line.startswith('Timestamp:'):
                        timestamp_str = line.split(':', 1)[1].strip()
                        timestamp = datetime.fromisoformat(timestamp_str)
                        age = (datetime.utcnow() - timestamp).total_seconds()

                        if age > 3600:  # 1 hour
                            return False, f"Paper proof too old ({age:.0f}s ago)"

                        return True, "Paper account verified (recent)"
        except Exception as e:
            return False, f"Error reading paper proof: {e}"

        return False, "Invalid paper proof file"

    def _check_allow_live(self) -> tuple:
        """HARDBAN: Never allow live trading."""
        allow_live = self.config.get('ALLOW_LIVE', 'false').lower() == 'true'

        if not allow_live:
            return True, "Live trading HARD-BANNED (ALLOW_LIVE=false)"
        else:
            return False, "ALLOW_LIVE=true - LIVE TRADING IS FORBIDDEN"

    def _check_pilot_symbols(self, symbol: str) -> tuple:
        """Check if symbol is in pilot whitelist."""
        pilot_symbols = self.config.get('PILOT_SYMBOLS', 'SPY').split(',')

        if symbol in pilot_symbols:
            return True, f"Symbol {symbol} in pilot whitelist"
        else:
            return False, f"Symbol {symbol} NOT in pilot whitelist ({pilot_symbols})"

    def _check_target_value_cap(self, target_value_pct: float) -> tuple:
        """Check if target value is within cap."""
        cap = float(self.config.get('PILOT_MAX_TARGET_VALUE_PCT', 0.005))

        if target_value_pct <= cap:
            return True, f"Target value {target_value_pct:.3f} within cap {cap:.3f}"
        else:
            return False, f"Target value {target_value_pct:.3f} EXCEEDS cap {cap:.3f}"

    def _check_orders_per_day_cap(self) -> tuple:
        """Check if daily orders cap has been reached."""
        max_orders = int(self.config.get('PILOT_MAX_ORDERS_PER_DAY', 3))

        # Count today's orders from receipts
        receipts_dir = Path('/home/davidsanker/platform/execution_receipts')
        today_str = datetime.utcnow().strftime('%Y-%m-%d')

        if receipts_dir.exists():
            today_orders = 0
            for receipt_file in receipts_dir.glob(f'*{today_str}*.json'):
                try:
                    import json
                    with open(receipt_file, 'r') as f:
                        receipt = json.load(f)
                        if receipt.get('status') in ['SUBMITTED', 'FILLED']:
                            today_orders += 1
                except:
                    pass

            if today_orders >= max_orders:
                return False, f"Daily orders cap reached ({today_orders}/{max_orders})"
            else:
                return True, f"Orders today: {today_orders}/{max_orders}"
        else:
            return True, "No orders yet today"

    def _check_market_hours(self) -> tuple:
        """Check if within market hours (if required)."""
        market_hours_only = self.config.get('PILOT_MARKET_HOURS_ONLY', 'false').lower() == 'true'

        if not market_hours_only:
            return True, "Market hours check disabled"

        # Simple check: weekday 9:30 AM - 4:00 PM ET
        now = datetime.utcnow()
        if now.weekday() >= 5:  # Saturday or Sunday
            return False, "Outside market hours (weekend)"

        # Convert to ET (UTC-5 or UTC-4)
        # For simplicity, assume market hours are 14:30-21:00 UTC (roughly 9:30-4:00 ET)
        hour = now.hour
        if hour < 14 or hour >= 21:
            return False, f"Outside market hours (hour: {hour} UTC)"

        return True, f"Within market hours (hour: {hour} UTC)"

    def _check_pilot_timeout(self) -> tuple:
        """Check if pilot period has ended."""
        end_time_str = self.config.get('PILOT_END_UTC')
        if not end_time_str:
            return True, "No pilot timeout set"

        try:
            end_time = datetime.fromisoformat(end_time_str)
            now = datetime.utcnow()

            if now > end_time:
                return False, f"Pilot period ended ({end_time_str})"
            else:
                remaining = (end_time - now).total_seconds()
                return True, f"Pilot active ({remaining:.0f}s remaining)"
        except Exception as e:
            return False, f"Error checking pilot timeout: {e}"

    def _check_kill_switch(self) -> tuple:
        """Check emergency kill switch."""
        kill_switch_file = Path('/home/davidsanker/platform/EMERGENCY_STOP')

        if kill_switch_file.exists():
            return False, "EMERGENCY STOP file exists - ALL TRADING HALTED"
        else:
            return True, "No emergency stop (trading allowed)"


def main():
    """Test guardrails."""
    guardrails = PilotGuardrails()

    # Test with SPY BUY order
    allowed, reason = guardrails.check_all_guards(
        symbol='SPY',
        action='BUY',
        target_value_pct=0.005
    )

    print(f"\nFinal Decision: {'ALLOW' if allowed else 'BLOCK'}")
    print(f"Reason: {reason}")

    return 0 if allowed else 1


if __name__ == "__main__":
    sys.exit(main())
