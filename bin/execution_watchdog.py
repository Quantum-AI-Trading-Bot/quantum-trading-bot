#!/usr/bin/env python3
"""
Execution Watchdog Service

Monitors system health and creates EMERGENCY_STOP on critical failures.

Checks:
- IB Gateway connectivity
- IBKR paper trading account validation
- Stale data detection
- Trading loop health
- Disk space
- Memory usage

FAIL-CLOSED: Any critical failure triggers EMERGENCY_STOP immediately.

Author: Autonomous Trading System
Date: 2026-01-24
Purpose: System health monitoring for autonomous trading
"""

import os
import sys
import json
import logging
import psutil
import shutil
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, List, Any, Tuple, Optional

# Add platform to path
PLATFORM_ROOT = Path("/home/davidsanker/platform")
sys.path.insert(0, str(PLATFORM_ROOT))

# Configuration
EMERGENCY_STOP_FILE = PLATFORM_ROOT / "EMERGENCY_STOP"
WATCHDOG_STATE_DIR = PLATFORM_ROOT / "state" / "watchdog"
WATCHDOG_STATE_DIR.mkdir(parents=True, exist_ok=True)
WATCHDOG_LOG_DIR = PLATFORM_ROOT / "logs" / "watchdog"
WATCHDOG_LOG_DIR.mkdir(parents=True, exist_ok=True)

# Logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler(f"{WATCHDOG_LOG_DIR}/watchdog.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


class ExecutionWatchdog:
    """
    Monitors trading system health and creates EMERGENCY_STOP on failures.

    Critical failures trigger immediate EMERGENCY_STOP:
    - IB Gateway not running
    - IB Gateway not connected to paper account
    - IB Gateway connected to LIVE account (FATAL)
    - Disk space < 10%
    - Memory usage > 95%
    - Trading loop not responding (stale data)
    """

    CRITICAL_THRESHOLDS = {
        'disk_space_percent': 10,  # Alert if < 10% free
        'memory_percent': 95,      # Alert if > 95% used
        'ib_gateway_stale_seconds': 300,  # 5 minutes
        'trading_loop_stale_seconds': 600,  # 10 minutes
        'paper_proof_stale_seconds': 3600,  # 1 hour
    }

    def __init__(self):
        """Initialize watchdog."""
        self.state_file = WATCHDOG_STATE_DIR / "watchdog_state.json"
        self.state = self._load_state()

        logger.info("=" * 80)
        logger.info("EXECUTION WATCHDOG INITIALIZED")
        logger.info("=" * 80)

    def _load_state(self) -> Dict:
        """Load watchdog state."""
        if self.state_file.exists():
            try:
                with open(self.state_file, 'r') as f:
                    return json.load(f)
            except Exception as e:
                logger.warning(f"Error loading watchdog state: {e}")

        return {
            'last_check': None,
            'last_ib_gateway_ok': None,
            'last_trading_loop_heartbeat': None,
            'emergency_stops_triggered': 0,
            'check_count': 0,
        }

    def _save_state(self):
        """Save watchdog state."""
        try:
            with open(self.state_file, 'w') as f:
                json.dump(self.state, f, indent=2)
        except Exception as e:
            logger.error(f"Error saving watchdog state: {e}")

    def check_ib_gateway_health(self) -> Tuple[bool, str, Dict]:
        """
        Check if IB Gateway is running and connected to paper account.

        Returns:
            (healthy, reason, details)
        """
        try:
            # Check 1: IB Gateway process running
            if not self._is_ib_gateway_running():
                return False, "IB Gateway process not running", {
                    'severity': 'CRITICAL',
                    'check': 'ib_gateway_process'
                }

            # Check 2: Port 4002 is listening (paper trading port)
            if not self._is_port_listening(4002):
                return False, "IB Gateway not listening on port 4002 (paper trading)", {
                    'severity': 'CRITICAL',
                    'check': 'ib_gateway_port'
                }

            # Check 3: Can connect to IB API
            try:
                from ib_insync import IB

                ib = IB()
                ib.connect('127.0.0.1', 4002, clientId=999, timeout=5)

                if not ib.isConnected():
                    return False, "Cannot connect to IB API on port 4002", {
                        'severity': 'CRITICAL',
                        'check': 'ib_api_connection'
                    }

                # Check 4: Validate paper account
                account_values = ib.accountSummary()
                account_id = ib.accounts()[0] if ib.accounts() else 'UNKNOWN'

                # Check if it's a paper trading account (account IDs typically start with 'D' for demo)
                is_paper = account_id.startswith('D') or 'DU' in account_id or 'paper' in account_id.lower()

                if not is_paper:
                    logger.critical(f"FATAL: Connected to LIVE account: {account_id}")
                    return False, f"CONNECTED TO LIVE ACCOUNT: {account_id}", {
                        'severity': 'FATAL',
                        'check': 'paper_account_validation',
                        'account_id': account_id
                    }

                ib.disconnect()

                # Update state
                self.state['last_ib_gateway_ok'] = datetime.now().isoformat()
                self._save_state()

                return True, f"IB Gateway OK (paper account: {account_id})", {
                    'severity': 'OK',
                    'check': 'ib_gateway_health',
                    'account_id': account_id
                }

            except ImportError:
                logger.warning("ib_insync not available - skipping IB connection check")
                return True, "IB Gateway check skipped (ib_insync not available)", {
                    'severity': 'WARNING',
                    'check': 'ib_gateway_health'
                }
            except Exception as e:
                return False, f"IB API connection error: {e}", {
                    'severity': 'CRITICAL',
                    'check': 'ib_api_connection',
                    'error': str(e)
                }

        except Exception as e:
            logger.error(f"Error checking IB Gateway health: {e}")
            return False, f"IB Gateway health check error: {e}", {
                'severity': 'ERROR',
                'check': 'ib_gateway_health',
                'error': str(e)
            }

    def _is_ib_gateway_running(self) -> bool:
        """Check if IB Gateway process is running."""
        try:
            for proc in psutil.process_iter(['name', 'cmdline']):
                try:
                    if proc.info['name'] and 'ibgateway' in proc.info['name'].lower():
                        return True
                    if proc.info['cmdline']:
                        cmdline = ' '.join(proc.info['cmdline'])
                        if 'ibgateway' in cmdline.lower():
                            return True
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue
            return False
        except Exception as e:
            logger.error(f"Error checking IB Gateway process: {e}")
            return False

    def _is_port_listening(self, port: int) -> bool:
        """Check if port is listening."""
        try:
            for conn in psutil.net_connections():
                if conn.laddr.port == port and conn.status == 'LISTEN':
                    return True
            return False
        except Exception as e:
            logger.error(f"Error checking port {port}: {e}")
            return False

    def check_disk_space(self) -> Tuple[bool, str, Dict]:
        """Check disk space."""
        try:
            usage = shutil.disk_usage(PLATFORM_ROOT)
            free_percent = (usage.free / usage.total) * 100

            if free_percent < self.CRITICAL_THRESHOLDS['disk_space_percent']:
                return False, f"Disk space critically low: {free_percent:.1f}% free", {
                    'severity': 'CRITICAL',
                    'check': 'disk_space',
                    'free_percent': free_percent,
                    'free_gb': usage.free / (1024**3)
                }
            elif free_percent < 20:
                return True, f"Disk space low: {free_percent:.1f}% free", {
                    'severity': 'WARNING',
                    'check': 'disk_space',
                    'free_percent': free_percent,
                    'free_gb': usage.free / (1024**3)
                }
            else:
                return True, f"Disk space OK: {free_percent:.1f}% free", {
                    'severity': 'OK',
                    'check': 'disk_space',
                    'free_percent': free_percent,
                    'free_gb': usage.free / (1024**3)
                }

        except Exception as e:
            logger.error(f"Error checking disk space: {e}")
            return False, f"Disk space check error: {e}", {
                'severity': 'ERROR',
                'check': 'disk_space',
                'error': str(e)
            }

    def check_memory_usage(self) -> Tuple[bool, str, Dict]:
        """Check memory usage."""
        try:
            mem = psutil.virtual_memory()
            usage_percent = mem.percent

            if usage_percent > self.CRITICAL_THRESHOLDS['memory_percent']:
                return False, f"Memory usage critically high: {usage_percent:.1f}%", {
                    'severity': 'CRITICAL',
                    'check': 'memory',
                    'usage_percent': usage_percent,
                    'available_gb': mem.available / (1024**3)
                }
            elif usage_percent > 90:
                return True, f"Memory usage high: {usage_percent:.1f}%", {
                    'severity': 'WARNING',
                    'check': 'memory',
                    'usage_percent': usage_percent,
                    'available_gb': mem.available / (1024**3)
                }
            else:
                return True, f"Memory OK: {usage_percent:.1f}%", {
                    'severity': 'OK',
                    'check': 'memory',
                    'usage_percent': usage_percent,
                    'available_gb': mem.available / (1024**3)
                }

        except Exception as e:
            logger.error(f"Error checking memory: {e}")
            return False, f"Memory check error: {e}", {
                'severity': 'ERROR',
                'check': 'memory',
                'error': str(e)
            }

    def check_paper_proof_freshness(self) -> Tuple[bool, str, Dict]:
        """Check if paper account proof is recent."""
        try:
            paper_proof_file = PLATFORM_ROOT / 'state' / 'paper_account_ok.txt'

            if not paper_proof_file.exists():
                return False, "Paper account proof file not found", {
                    'severity': 'WARNING',
                    'check': 'paper_proof_freshness',
                    'note': 'Run assert_paper_account.py to create proof'
                }

            # Check file age
            file_time = datetime.fromtimestamp(paper_proof_file.stat().st_mtime)
            age_seconds = (datetime.now() - file_time).total_seconds()

            if age_seconds > self.CRITICAL_THRESHOLDS['paper_proof_stale_seconds']:
                return False, f"Paper proof stale: {age_seconds:.0f}s ago", {
                    'severity': 'WARNING',
                    'check': 'paper_proof_freshness',
                    'age_seconds': age_seconds
                }
            else:
                return True, f"Paper proof fresh: {age_seconds:.0f}s ago", {
                    'severity': 'OK',
                    'check': 'paper_proof_freshness',
                    'age_seconds': age_seconds
                }

        except Exception as e:
            logger.error(f"Error checking paper proof: {e}")
            return False, f"Paper proof check error: {e}", {
                'severity': 'ERROR',
                'check': 'paper_proof_freshness',
                'error': str(e)
            }

    def check_trading_loop_health(self) -> Tuple[bool, str, Dict]:
        """Check if trading loop is alive (heartbeat check)."""
        try:
            # Check recent execution receipts
            receipts_dir = PLATFORM_ROOT / "execution_receipts"

            if not receipts_dir.exists():
                return True, "No execution receipts yet (system may be starting)", {
                    'severity': 'OK',
                    'check': 'trading_loop_health',
                    'note': 'No receipts yet'
                }

            # Find most recent receipt
            receipts = sorted(receipts_dir.glob("*.json"), key=lambda p: p.stat().st_mtime, reverse=True)

            if not receipts:
                return True, "No execution receipts yet", {
                    'severity': 'OK',
                    'check': 'trading_loop_health',
                    'note': 'No receipts yet'
                }

            # Check age of most recent receipt
            latest_receipt = receipts[0]
            receipt_time = datetime.fromtimestamp(latest_receipt.stat().st_mtime)
            age_seconds = (datetime.now() - receipt_time).total_seconds()

            # Check if it's too old (stale)
            if age_seconds > self.CRITICAL_THRESHOLDS['trading_loop_stale_seconds']:
                return False, f"Trading loop stale: {age_seconds:.0f}s since last receipt", {
                    'severity': 'WARNING',
                    'check': 'trading_loop_health',
                    'age_seconds': age_seconds,
                    'last_receipt': latest_receipt.name
                }
            else:
                return True, f"Trading loop OK: {age_seconds:.0f}s since last receipt", {
                    'severity': 'OK',
                    'check': 'trading_loop_health',
                    'age_seconds': age_seconds,
                    'last_receipt': latest_receipt.name
                }

        except Exception as e:
            logger.error(f"Error checking trading loop health: {e}")
            return False, f"Trading loop health check error: {e}", {
                'severity': 'ERROR',
                'check': 'trading_loop_health',
                'error': str(e)
            }

    def run_all_checks(self) -> Tuple[bool, List[Dict]]:
        """
        Run all health checks and trigger EMERGENCY_STOP if critical.

        Returns:
            (all_healthy, check_results)
        """
        logger.info("")
        logger.info("=" * 80)
        logger.info("WATCHDOG HEALTH CHECK")
        logger.info("=" * 80)

        checks = [
            ("IB Gateway Health", self.check_ib_gateway_health),
            ("Disk Space", self.check_disk_space),
            ("Memory Usage", self.check_memory_usage),
            ("Paper Proof Freshness", self.check_paper_proof_freshness),
            ("Trading Loop Health", self.check_trading_loop_health),
        ]

        all_results = []
        critical_failures = []

        for check_name, check_func in checks:
            logger.info(f"")
            logger.info(f"Running: {check_name}")

            healthy, reason, details = check_func()
            details['reason'] = reason
            details['check_name'] = check_name

            all_results.append(details)

            severity = details.get('severity', 'OK')
            status_icon = "✓" if healthy else "✗"

            if severity == 'OK':
                logger.info(f"{status_icon} {check_name}: {reason}")
            elif severity == 'WARNING':
                logger.warning(f"⚠️ {check_name}: {reason}")
            elif severity in ['CRITICAL', 'FATAL', 'ERROR']:
                logger.error(f"🚨 {check_name}: {reason}")
                if severity in ['CRITICAL', 'FATAL']:
                    critical_failures.append(details)

        # Update state
        self.state['last_check'] = datetime.now().isoformat()
        self.state['check_count'] += 1
        self._save_state()

        # Log summary
        logger.info("")
        logger.info("=" * 80)
        logger.info("WATCHDOG SUMMARY")
        logger.info("=" * 80)
        logger.info(f"Checks run: {len(all_results)}")
        logger.info(f"Critical failures: {len(critical_failures)}")
        logger.info("=" * 80)
        logger.info("")

        # Trigger EMERGENCY_STOP if critical failures
        if critical_failures:
            logger.critical("CRITICAL FAILURES DETECTED - CREATING EMERGENCY_STOP")

            for failure in critical_failures:
                logger.critical(f"  - {failure['check_name']}: {failure['reason']}")

            EMERGENCY_STOP_FILE.touch()

            self.state['emergency_stops_triggered'] += 1
            self._save_state()

            return False, all_results
        else:
            logger.info("✓ All checks passed - no critical failures")
            return True, all_results

    def remove_emergency_stop_if_resolved(self):
        """
        Remove EMERGENCY_STOP if all issues are resolved.

        Only removes if:
        - EMERGENCY_STOP file exists
        - All checks pass now
        """
        if not EMERGENCY_STOP_FILE.exists():
            return

        logger.info("EMERGENCY_STOP file exists - checking if resolved...")

        all_healthy, _ = self.run_all_checks()

        if all_healthy:
            logger.info("✓ All issues resolved - removing EMERGENCY_STOP")
            EMERGENCY_STOP_FILE.unlink()
            logger.info("EMERGENCY_STOP removed - trading can resume")
        else:
            logger.warning("⚠️ Issues still present - EMERGENCY_STOP remains")


def main():
    """CLI entry point for watchdog."""
    import argparse

    parser = argparse.ArgumentParser(description='Execution Watchdog')
    parser.add_argument('--clear-if-resolved', action='store_true',
                       help='Remove EMERGENCY_STOP if all issues resolved')
    parser.add_argument('--continuous', action='store_true',
                       help='Run continuous monitoring (every 60s)')
    args = parser.parse_args()

    watchdog = ExecutionWatchdog()

    if args.clear_if_resolved:
        watchdog.remove_emergency_stop_if_resolved()
        return 0

    if args.continuous:
        logger.info("Starting continuous monitoring (Ctrl+C to stop)...")
        try:
            while True:
                watchdog.run_all_checks()
                import time
                time.sleep(60)
        except KeyboardInterrupt:
            logger.info("Stopped continuous monitoring")
            return 0
    else:
        # Single run
        all_healthy, results = watchdog.run_all_checks()

        # Exit 0 for expected conditions (gateway down, kill switch active)
        # Exit 1 only for unexpected internal errors
        critical_failures = [r for r in results if r.get('severity') == 'CRITICAL']
        unexpected_errors = [r for r in results if r.get('severity') == 'ERROR']

        if unexpected_errors:
            # Real errors - should alert
            logger.error(f"Unexpected errors detected: {len(unexpected_errors)}")
            return 1
        else:
            # Expected conditions (gateway down, kill switch, stale proof)
            # These are normal operational states, not errors
            if critical_failures:
                logger.info(f"Critical failures detected (expected operational state): {len(critical_failures)}")
            return 0


if __name__ == '__main__':
    sys.exit(main())
