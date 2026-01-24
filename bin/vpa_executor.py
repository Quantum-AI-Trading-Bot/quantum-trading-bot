#!/usr/bin/env python3
"""
VPA Executor - Safe Execution Adapter for Quantum Trading
Implements guardrails, duplicate prevention, and paper-only enforcement

Generated: 2026-01-20 16:55:00 UTC
Author: Claude Code (for David Sanker)
Version: 1.0
"""

import os
import sys
import json
import logging
import hashlib
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict
from typing import Dict, List, Optional, Tuple, Any
from pathlib import Path

# Try to import ib_insync
try:
    from ib_insync import IB, Stock, MarketOrder, LimitOrder
    IB_AVAILABLE = True
except ImportError:
    IB_AVAILABLE = False
    logging.warning("ib_insync not available - execution will be limited")

# Configuration paths
PLATFORM_ROOT = Path("/home/davidsanker/platform")
VPA_STORAGE = PLATFORM_ROOT / "vpa_storage"
EXECUTION_RECEIPTS_DIR = PLATFORM_ROOT / "execution_receipts"
STATE_DIR = PLATFORM_ROOT / "state"
EMERGENCY_STOP_FILE = PLATFORM_ROOT / "EMERGENCY_STOP"

# Create directories
EXECUTION_RECEIPTS_DIR.mkdir(parents=True, exist_ok=True)
STATE_DIR.mkdir(parents=True, exist_ok=True)

# Logging setup
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler(f"{PLATFORM_ROOT}/logs/quantum-engine/execution.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


@dataclass
class ExecutionIntent:
    """Structured execution intent from VPA decision plan"""

    # Required fields
    action: str              # BUY or SELL
    symbol: str              # e.g., "AAPL" or "MES"

    # Instrument type (optional, defaults to STOCK for backward compatibility)
    instrument_type: str = "STOCK"  # STOCK, FUT, OPT, CRYPTO

    # Contract metadata (required for FUT, optional for STOCK)
    contract_metadata: Optional[Dict[str, Any]] = None  # For futures: {expiry, exchange, multiplier}

    # Quantity (one required)
    quantity: Optional[int] = None          # Exact shares or contracts
    target_value_pct: Optional[float] = None  # % of portfolio

    # Order details
    order_type: str = "MKT"     # MKT or LMT
    limit_price: Optional[float] = None  # Required for LMT

    # Optional constraints
    time_in_force: str = "DAY"   # DAY or GTC
    max_slippage_pct: float = 0.01  # Default 1%

    # Metadata
    reason: str = ""            # Human-readable explanation
    confidence: float = 0.75    # Default confidence

    def __post_init__(self):
        """Validate intent"""
        if self.action not in ['BUY', 'SELL', 'HOLD']:
            raise ValueError(f"Invalid action: {self.action}")

        if self.order_type not in ['MKT', 'LMT']:
            raise ValueError(f"Invalid order type: {self.order_type}")

        if self.order_type == 'LMT' and self.limit_price is None:
            raise ValueError("LMT orders require limit_price")

        if self.quantity is None and self.target_value_pct is None:
            raise ValueError("Must specify quantity or target_value_pct")

        # Futures require contract_metadata
        if self.instrument_type == "FUT" and self.contract_metadata is None:
            raise ValueError(f"contract_metadata required for futures {self.symbol}")

        if self.action == 'HOLD':
            # HOLD is valid but not actionable
            pass

    def to_dict(self) -> dict:
        """Convert to dictionary"""
        return asdict(self)


@dataclass
class GuardrailResult:
    """Result of guardrail checks"""
    allowed: bool
    reason: str
    checks: Dict[str, str]

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class ExecutionResult:
    """Result of execution attempt"""
    intent: ExecutionIntent
    guardrail_result: GuardrailResult
    order_result: Optional[Dict[str, Any]]
    dry_run: bool

    def to_dict(self) -> dict:
        return {
            'intent': self.intent.to_dict(),
            'guardrail_result': self.guardrail_result.to_dict(),
            'order_result': self.order_result,
            'dry_run': self.dry_run
        }


class VPAExecutor:
    """Safe VPA execution adapter with guardrails"""

    def __init__(self, config: Dict[str, Any]):
        """
        Initialize executor with configuration

        Args:
            config: Configuration dict from quantum_runtime.env
        """
        self.config = config

        # Load configuration with defaults
        self.min_confidence = float(config.get('MIN_CONFIDENCE', 0.75))
        self.max_position_size = float(config.get('MAX_POSITION_SIZE', 0.15))
        self.quantum_client_id = int(config.get('QUANTUM_CLIENT_ID', 401))
        self.execution_timeout = int(config.get('QUANTUM_EXECUTION_TIMEOUT', 10))
        self.idempotency_ttl = int(config.get('QUANTUM_EXECUTION_IDEMPOTENCY_TTL', 600))
        self.allow_after_hours = config.get('QUANTUM_ALLOW_AFTER_HOURS', 'false').lower() == 'true'
        self.max_daily_trades = int(config.get('QUANTUM_MAX_DAILY_TRADES', 50))

        # IB connection (will connect when needed)
        self.ib = None

        logger.info(f"VPA Executor initialized")
        logger.info(f"  Min confidence: {self.min_confidence}")
        logger.info(f"  Max position size: {self.max_position_size}")
        logger.info(f"  Client ID: {self.quantum_client_id}")
        logger.info(f"  Timeout: {self.execution_timeout}s")

    def parse_decision_plan(self, vpa_json: Dict) -> List[ExecutionIntent]:
        """
        Parse VPA decision plan into execution intents

        Args:
            vpa_json: Loaded VPA JSON

        Returns:
            List of ExecutionIntent objects
        """
        intents = []

        try:
            decision_plan = vpa_json.get('decision_plan', {})

            # Check for intents array (multi-symbol)
            if 'intents' in decision_plan:
                for intent_dict in decision_plan['intents']:
                    intent = self._parse_single_intent(intent_dict)
                    if intent:
                        intents.append(intent)

            # Check for single decision
            elif 'action' in decision_plan:
                intent = self._parse_single_intent(decision_plan)
                if intent:
                    intents.append(intent)

            else:
                logger.warning("No actionable decision in VPA")

            logger.info(f"Parsed {len(intents)} execution intent(s)")
            return intents

        except Exception as e:
            logger.error(f"Error parsing decision plan: {e}")
            return []

    def _parse_single_intent(self, intent_dict: Dict) -> Optional[ExecutionIntent]:
        """Parse a single intent from dict"""
        try:
            action = intent_dict.get('action', 'HOLD').upper()

            if action == 'HOLD' or action == 'NONE':
                logger.info(f"Skipping HOLD/NONE action: {intent_dict.get('reason', 'No reason')}")
                return None

            # Create intent
            intent = ExecutionIntent(
                action=action,
                symbol=intent_dict.get('symbol', ''),
                quantity=intent_dict.get('quantity'),
                target_value_pct=intent_dict.get('target_value_pct'),
                order_type=intent_dict.get('order_type', 'MKT').upper(),
                limit_price=intent_dict.get('limit_price'),
                time_in_force=intent_dict.get('time_in_force', 'DAY').upper(),
                max_slippage_pct=intent_dict.get('max_slippage_pct', 0.01),
                reason=intent_dict.get('reason', ''),
                confidence=float(intent_dict.get('confidence', 0.75))
            )

            logger.info(f"Parsed intent: {intent.action} {intent.symbol}")
            return intent

        except Exception as e:
            logger.error(f"Error parsing intent: {e}")
            return None

    def enforce_guardrails(self, intent: ExecutionIntent, account_snapshot: Dict) -> GuardrailResult:
        """
        Enforce all safety guardrails

        Args:
            intent: ExecutionIntent to check
            account_snapshot: Account values from IB

        Returns:
            GuardrailResult with allowed status and reason
        """
        checks = {}
        reasons = []

        # 1. Kill-switch check
        if EMERGENCY_STOP_FILE.exists():
            checks['kill_switch'] = 'BLOCK'
            reasons.append("EMERGENCY_STOP file exists")
            logger.warning("BLOCKED: EMERGENCY_STOP file exists")
            return GuardrailResult(allowed=False, reason='; '.join(reasons), checks=checks)
        else:
            checks['kill_switch'] = 'PASS'

        # 2. Paper-only enforcement (check connection params)
        # In production, we'd verify the actual IB connection
        # For now, assume correct if we're connecting to port 4002
        ib_port = int(os.getenv('IB_PORT', 4002))
        if ib_port != 4002:
            checks['paper_only'] = 'BLOCK'
            reasons.append(f"Live trading port detected: {ib_port}")
            logger.error(f"BLOCKED: Live trading port {ib_port}")
            return GuardrailResult(allowed=False, reason='; '.join(reasons), checks=checks)
        else:
            checks['paper_only'] = 'PASS'

        # 3. Confidence threshold
        if intent.confidence < self.min_confidence:
            checks['confidence'] = 'BLOCK'
            reasons.append(f"Confidence too low: {intent.confidence:.2f} < {self.min_confidence:.2f}")
            logger.warning(f"BLOCKED: Confidence {intent.confidence:.2f} < {self.min_confidence:.2f}")
            return GuardrailResult(allowed=False, reason='; '.join(reasons), checks=checks)
        else:
            checks['confidence'] = 'PASS'

        # 4. Position size check
        if intent.target_value_pct and intent.target_value_pct > self.max_position_size:
            original_pct = intent.target_value_pct
            intent.target_value_pct = self.max_position_size
            checks['position_size'] = 'CLAMPED'
            reasons.append(f"Position size clamped: {original_pct:.2%} -> {self.max_position_size:.2%}")
            logger.warning(f"Clamped position size from {original_pct:.2%} to {self.max_position_size:.2%}")
        else:
            checks['position_size'] = 'PASS'

        # 5. Duplicate order prevention
        idempotency_key = self._compute_idempotency_key(intent)
        if self._is_duplicate_order(idempotency_key):
            checks['duplicate_check'] = 'BLOCK'
            reasons.append(f"Duplicate order: {idempotency_key}")
            logger.warning(f"BLOCKED: Duplicate order {idempotency_key}")
            return GuardrailResult(allowed=False, reason='; '.join(reasons), checks=checks)
        else:
            checks['duplicate_check'] = 'PASS'

        # 6. Market hours guard (optional)
        if not self.allow_after_hours and not self._is_market_hours():
            checks['market_hours'] = 'BLOCK'
            reasons.append("Outside market hours")
            logger.warning("BLOCKED: Outside market hours")
            return GuardrailResult(allowed=False, reason='; '.join(reasons), checks=checks)
        else:
            checks['market_hours'] = 'PASS'

        # All checks passed
        logger.info(f"Guardrails PASSED for {intent.symbol}")
        return GuardrailResult(allowed=True, reason='All checks passed', checks=checks)

    def _compute_idempotency_key(self, intent: ExecutionIntent) -> str:
        """Compute idempotency key for duplicate detection"""
        # Key: date + symbol + action + quantity
        today = datetime.now().strftime('%Y-%m-%d')
        key_data = f"{today}:{intent.symbol}:{intent.action}:{intent.quantity or intent.target_value_pct}"
        key_hash = hashlib.md5(key_data.encode()).hexdigest()[:8]
        return key_hash

    def _is_duplicate_order(self, idempotency_key: str) -> bool:
        """Check if order is a duplicate using idempotency key"""
        executed_keys_file = STATE_DIR / "executed_keys.json"

        # Load existing keys
        executed_keys = {}
        if executed_keys_file.exists():
            try:
                with open(executed_keys_file, 'r') as f:
                    executed_keys = json.load(f)
            except:
                logger.warning("Error loading executed keys file")

        # Check if key exists and is recent
        if idempotency_key in executed_keys:
            key_time = datetime.fromisoformat(executed_keys[idempotency_key])
            if datetime.now() - key_time < timedelta(seconds=self.idempotency_ttl):
                return True

        # Add current key
        executed_keys[idempotency_key] = datetime.now().isoformat()

        # Clean old keys
        cutoff = datetime.now() - timedelta(seconds=self.idempotency_ttl)
        executed_keys = {
            k: v for k, v in executed_keys.items()
            if datetime.fromisoformat(v) > cutoff
        }

        # Save
        with open(executed_keys_file, 'w') as f:
            json.dump(executed_keys, f, indent=2)

        return False

    def _is_market_hours(self) -> bool:
        """Check if current time is within market hours"""
        now = datetime.now()

        # Weekend check
        if now.weekday() >= 5:  # Saturday=5, Sunday=6
            return False

        # Market hours: 9:30 AM - 4:00 PM ET
        # Simplified: use UTC (EST = UTC-5, EDT = UTC-4)
        # 9:30 AM ET = 13:30 or 14:30 UTC
        # 4:00 PM ET = 20:00 or 21:00 UTC
        hour = now.hour
        minute = now.minute
        current_time = hour * 100 + minute

        # Approximate market hours in UTC (assuming EST)
        if 1330 <= current_time <= 2100:
            return True

        return False

    def build_ib_order(self, intent: ExecutionIntent) -> Tuple:
        """
        Build IB contract and order

        Supports both stocks and futures based on intent.instrument_type

        Returns:
            Tuple of (contract, order)
        """
        # Import Future if needed
        if intent.instrument_type == "FUT" and IB_AVAILABLE:
            from ib_insync import Future

        # Create contract based on instrument type
        if intent.instrument_type == "FUT":
            # Build futures contract
            if not intent.contract_metadata:
                raise ValueError(f"contract_metadata required for futures {intent.symbol}")

            metadata = intent.contract_metadata
            contract = Future(
                symbol=intent.symbol,
                lastTradeDateOrContractMonth=metadata.get("expiry"),
                exchange=metadata.get("exchange", "CME"),
                currency=metadata.get("currency", "USD")
            )

            logger.info(f"Built futures contract: {intent.symbol}{metadata.get('expiry')}")

        else:
            # Default: Stock contract (backward compatible)
            contract = Stock(intent.symbol, 'SMART', 'USD')

        # Create order
        if intent.order_type == 'LMT':
            order = LimitOrder(
                intent.action,
                intent.quantity or 100,  # Will be calculated later
                intent.limit_price
            )
            order.tif = intent.time_in_force
        else:
            order = MarketOrder(
                intent.action,
                intent.quantity or 100  # Will be calculated later
            )

        logger.info(f"Built order: {intent.action} {intent.symbol} {order}")

        return contract, order

    def execute_intents(self, intents: List[ExecutionIntent], dry_run: bool = True) -> List[ExecutionResult]:
        """
        Execute all intents with guardrails

        Args:
            intents: List of ExecutionIntent objects
            dry_run: If True, log but don't place orders

        Returns:
            List of ExecutionResult objects
        """
        results = []

        logger.info(f"\n{'='*80}")
        logger.info(f"VPA Execution - {'DRY RUN' if dry_run else 'LIVE (PAPER)'}")
        logger.info(f"{'='*80}")
        logger.info(f"Intents to process: {len(intents)}")

        # Connect to IB if not dry run
        if not dry_run and IB_AVAILABLE:
            try:
                self.ib = IB()
                ib_host = os.getenv('IB_HOST', '127.0.0.1')
                ib_port = int(os.getenv('IB_PORT', 4002))

                logger.info(f"Connecting to IB at {ib_host}:{ib_port}...")
                self.ib.connect(ib_host, ib_port, clientId=self.quantum_client_id, timeout=15)

                if not self.ib.isConnected():
                    logger.error("Failed to connect to IB")
                    # Fall back to dry run
                    dry_run = True
                    logger.warning("Falling back to DRY_RUN mode due to connection failure")

                # Get account snapshot
                account_snapshot = {}
                if self.ib.isConnected():
                    account_values = self.ib.accountSummary()
                    for val in account_values:
                        if val.tag == 'NetLiquidation':
                            account_snapshot['net_liquidation'] = float(val.value)

            except Exception as e:
                logger.error(f"IB connection error: {e}")
                dry_run = True
                logger.warning("Falling back to DRY_RUN mode due to connection error")
                account_snapshot = {}
        else:
            account_snapshot = {}

        # Process each intent
        for i, intent in enumerate(intents, 1):
            logger.info(f"\n--- Processing Intent {i}/{len(intents)} ---")
            logger.info(f"Action: {intent.action} {intent.symbol}")
            logger.info(f"Reason: {intent.reason}")
            logger.info(f"Confidence: {intent.confidence:.2%}")

            # Enforce guardrails
            guardrail_result = self.enforce_guardrails(intent, account_snapshot)

            # Prepare order result
            order_result = None

            if guardrail_result.allowed:
                if dry_run:
                    # DRY RUN - log what we would do
                    instrument_desc = intent.symbol
                    if intent.instrument_type == "FUT":
                        expiry = intent.contract_metadata.get("expiry", "UNKNOWN") if intent.contract_metadata else "UNKNOWN"
                        instrument_desc = f"{intent.symbol}{expiry} (FUT)"
                        logger.info(f"✓ DRY RUN: Would place futures order")
                    else:
                        logger.info(f"✓ DRY RUN: Would place stock order")

                    logger.info(f"  Action: {intent.action}")
                    logger.info(f"  Instrument: {instrument_desc}")
                    logger.info(f"  Type: {intent.instrument_type}")
                    logger.info(f"  Quantity: {intent.quantity or 'calculating from target_value_pct'}")
                    logger.info(f"  Order Type: {intent.order_type}")
                    if intent.order_type == 'LMT':
                        logger.info(f"  Limit Price: ${intent.limit_price:.2f}")
                    logger.info(f"  TIF: {intent.time_in_force}")

                    order_result = {
                        'status': 'WOULD_PLACE',
                        'note': 'DRY_RUN mode - no order placed',
                        'action': intent.action,
                        'symbol': intent.symbol,
                        'instrument_type': intent.instrument_type,
                        'order_type': intent.order_type
                    }

                    # Add contract details for futures
                    if intent.instrument_type == "FUT" and intent.contract_metadata:
                        order_result['contract_details'] = intent.contract_metadata

                else:
                    # LIVE PAPER TRADING
                    try:
                        # Calculate quantity if not specified
                        if intent.quantity is None and intent.target_value_pct:
                            account_value = account_snapshot.get('net_liquidation', 100000)
                            target_value = account_value * intent.target_value_pct

                            # Get current price (simplified - use account snapshot or fetch)
                            # For now, use a placeholder
                            current_price = 175.00  # Will be fetched from IB
                            intent.quantity = int(target_value / current_price)

                        # Build and place order
                        contract, order = self.build_ib_order(intent)

                        logger.info(f"Placing order with IB...")
                        trade = self.ib.placeOrder(contract, order)

                        logger.info(f"✓ Order placed")
                        logger.info(f"  Client ID: {self.quantum_client_id}")
                        logger.info(f"  Order ID: {order.orderId}")

                        order_result = {
                            'status': 'SUBMITTED',
                            'order_id': order.orderId,
                            'client_id': self.quantum_client_id,
                            'action': intent.action,
                            'symbol': intent.symbol,
                            'quantity': intent.quantity,
                            'order_type': intent.order_type
                        }

                    except Exception as e:
                        logger.error(f"❌ Order placement failed: {e}")
                        order_result = {
                            'status': 'FAILED',
                            'error': str(e)
                        }
            else:
                # Blocked by guardrails
                logger.warning(f"✗ BLOCKED: {guardrail_result.reason}")
                order_result = {
                    'status': 'BLOCKED',
                    'reason': guardrail_result.reason,
                    'checks': guardrail_result.checks
                }

            # Create execution result
            result = ExecutionResult(
                intent=intent,
                guardrail_result=guardrail_result,
                order_result=order_result,
                dry_run=dry_run
            )
            results.append(result)

            # Save execution receipt
            self._save_execution_receipt(result)

        # Disconnect from IB
        if self.ib and self.ib.isConnected():
            self.ib.disconnect()

        # Log summary
        logger.info(f"\n{'='*80}")
        logger.info("Execution Summary")
        logger.info(f"{'='*80}")
        logger.info(f"Total intents: {len(intents)}")
        logger.info(f"Allowed: {sum(1 for r in results if r.guardrail_result.allowed)}")
        logger.info(f"Blocked: {sum(1 for r in results if not r.guardrail_result.allowed)}")
        if dry_run:
            logger.info(f"Mode: DRY RUN (no orders placed)")
        else:
            logger.info(f"Mode: LIVE PAPER TRADING")

        return results

    def _save_execution_receipt(self, result: ExecutionResult):
        """Save execution receipt to file"""
        try:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S_%f')
            symbol = result.intent.symbol
            filename = f"{timestamp}_{symbol}.json"
            filepath = EXECUTION_RECEIPTS_DIR / filename

            receipt = {
                'timestamp': datetime.now().isoformat(),
                'intent': result.intent.to_dict(),
                'guardrail_result': result.guardrail_result.to_dict(),
                'order_result': result.order_result,
                'dry_run': result.dry_run
            }

            with open(filepath, 'w') as f:
                json.dump(receipt, f, indent=2)

            logger.debug(f"Saved execution receipt: {filepath}")

        except Exception as e:
            logger.error(f"Error saving execution receipt: {e}")


def load_latest_vpa() -> Optional[Dict]:
    """Load the latest VPA artifact"""
    try:
        vpa_files = sorted(VPA_STORAGE.glob('vpa_*.json'), reverse=True)
        if not vpa_files:
            logger.error("No VPA files found")
            return None

        latest_vpa = vpa_files[0]
        logger.info(f"Loading VPA: {latest_vpa}")

        with open(latest_vpa, 'r') as f:
            return json.load(f)

    except Exception as e:
        logger.error(f"Error loading VPA: {e}")
        return None


def load_config(config_file: str) -> Dict:
    """Load configuration from .env file"""
    config = {}

    try:
        with open(config_file, 'r') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    key, value = line.split('=', 1)
                    config[key.strip()] = value.strip()

    except Exception as e:
        logger.error(f"Error loading config: {e}")

    return config


def main():
    """Main entry point"""
    import argparse

    parser = argparse.ArgumentParser(description='VPA Executor - Safe Execution Adapter')
    parser.add_argument('--vpa-file', type=str, help='Path to VPA JSON file')
    parser.add_argument('--config', type=str,
                       default='/home/davidsanker/platform/config/quantum_runtime.env',
                       help='Path to config file')
    parser.add_argument('--dry-run', type=str, default='true',
                       help='Dry run mode (true/false)')

    args = parser.parse_args()

    # Load config
    config = load_config(args.config)

    # Override dry_run from command line
    dry_run = args.dry_run.lower() == 'true'
    config['DRY_RUN'] = str(dry_run)

    # Load VPA
    if args.vpa_file:
        with open(args.vpa_file, 'r') as f:
            vpa_json = json.load(f)
    else:
        vpa_json = load_latest_vpa()
        if not vpa_json:
            logger.error("No VPA file available")
            return 1

    # Create executor
    executor = VPAExecutor(config)

    # Parse intents
    intents = executor.parse_decision_plan(vpa_json)

    if not intents:
        logger.info("No actionable intents in VPA")
        return 0

    # Execute
    results = executor.execute_intents(intents, dry_run=dry_run)

    # Check if any executions failed
    if any(r.order_result and r.order_result.get('status') == 'FAILED' for r in results):
        return 1

    return 0


if __name__ == '__main__':
    sys.exit(main())
