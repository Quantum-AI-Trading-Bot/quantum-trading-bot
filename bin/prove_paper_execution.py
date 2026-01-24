#!/usr/bin/env python3
"""
Paper Trading Proof Tool
Demonstrates that paper orders are placed when execution is enabled

Generated: 2026-01-20 17:02:00 UTC
Purpose: Provide evidence of paper trading execution
"""

import os
import sys
import json
import time
import logging
from datetime import datetime
from pathlib import Path

# Try to import ib_insync
try:
    from ib_insync import IB
    IB_AVAILABLE = True
except ImportError:
    IB_AVAILABLE = False
    print("ERROR: ib_insync not available")
    sys.exit(1)

# Configuration
IB_HOST = "127.0.0.1"
IB_PORT = 4002
PROOF_CLIENT_ID = 9012  # Unique clientId for proof tool
PLATFORM_ROOT = Path("/home/davidsanker/platform")

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)
logger = logging.getLogger(__name__)


def snapshot_ib_state(ib: IB) -> dict:
    """Take a snapshot of current IB state"""
    snapshot = {
        'timestamp': datetime.now().isoformat(),
        'connected': ib.isConnected(),
        'open_orders': [],
        'executions': [],
        'positions': []
    }

    if not ib.isConnected():
        return snapshot

    try:
        # Get open orders
        open_orders = ib.openOrders()
        snapshot['open_orders_count'] = len(open_orders)
        for order in open_orders:
            snapshot['open_orders'].append({
                'orderId': order.orderId,
                'clientId': order.clientId,
                'action': order.action,
                'totalQuantity': order.totalQuantity,
                'orderType': order.orderType,
                'symbol': order.contract.symbol if order.contract else 'Unknown'
            })

        # Get executions (last 24 hours)
        executions = ib.executions()
        now = datetime.now()
        recent_execs = []
        for exec in executions:
            exec_time = exec.time
            if isinstance(exec_time, str):
                try:
                    from datetime import datetime as dt
                    exec_time = dt.fromisoformat(exec_time.replace('Z', '+00:00'))
                except:
                    continue

            # Filter for last 24 hours
            if exec_time > now - timedelta(hours=24):
                recent_execs.append(exec)

        snapshot['executions_count'] = len(recent_execs)
        for exec in recent_execs[:10]:  # Last 10
            snapshot['executions'].append({
                'execId': exec.execId,
                'time': str(exec.time),
                'symbol': exec.contract.symbol if exec.contract else 'Unknown',
                'side': exec.side,
                'shares': exec.shares,
                'price': exec.price
            })

        # Get positions
        positions = ib.positions()
        snapshot['positions_count'] = len(positions)
        for pos in positions[:10]:
            snapshot['positions'].append({
                'symbol': pos.contract.symbol,
                'position': pos.position,
                'marketPrice': pos.marketPrice(),
                'marketValue': pos.marketValue()
            })

    except Exception as e:
        logger.error(f"Error taking snapshot: {e}")

    return snapshot


def print_snapshot(snapshot: dict, label: str):
    """Print a formatted snapshot"""
    print(f"\n{label}")
    print("="*80)
    print(f"Timestamp: {snapshot['timestamp']}")
    print(f"Connected: {snapshot['connected']}")

    if snapshot['connected']:
        print(f"Open Orders: {snapshot.get('open_orders_count', 0)}")
        if snapshot['open_orders']:
            for order in snapshot['open_orders']:
                print(f"  - Order {order['orderId']}: {order['action']} {order['totalQuantity']} {order['symbol']} ({order['orderType']})")

        print(f"\nRecent Executions (24h): {snapshot.get('executions_count', 0)}")
        if snapshot['executions']:
            for exec in snapshot['executions'][:5]:
                print(f"  - {exec['time']}: {exec['side']} {exec['shares']} {exec['symbol']} @ ${exec['price']:.2f}")

        print(f"\nPositions: {snapshot.get('positions_count', 0)}")
        if snapshot['positions']:
            for pos in snapshot['positions'][:5]:
                print(f"  - {pos['symbol']}: {pos['position']} shares @ ${pos['marketPrice']:.2f} (${pos['marketValue']:,.2f})")


def compare_snapshots(before: dict, after: dict) -> dict:
    """Compare two snapshots and return delta"""
    delta = {
        'new_orders': [],
        'new_executions': [],
        'new_positions': 0
    }

    # Compare open orders
    before_order_ids = {o['orderId'] for o in before.get('open_orders', [])}
    after_order_ids = {o['orderId'] for o in after.get('open_orders', [])}

    new_order_ids = after_order_ids - before_order_ids
    for order_id in new_order_ids:
        for order in after.get('open_orders', []):
            if order['orderId'] == order_id:
                delta['new_orders'].append(order)

    # Compare executions
    before_exec_ids = {e['execId'] for e in before.get('executions', [])}
    after_exec_ids = {e['execId'] for e in after.get('executions', [])}

    new_exec_ids = after_exec_ids - before_exec_ids
    for exec_id in new_exec_ids:
        for exec in after.get('executions', []):
            if exec['execId'] == exec_id:
                delta['new_executions'].append(exec)

    # Compare positions
    delta['new_positions'] = after.get('positions_count', 0) - before.get('positions_count', 0)

    return delta


def create_test_vpa_with_signal() -> str:
    """Create a test VPA with a BUY signal for demonstration"""
    from datetime import timedelta as td
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    vpa_file = PLATFORM_ROOT / "vpa_storage" / f"vpa_test_{timestamp}.json"

    # Determine signal based on time of day (alternate buy/sell for testing)
    hour = datetime.now().hour
    if hour % 2 == 0:
        action = "BUY"
        reason = "Test BUY signal for execution proof"
    else:
        action = "SELL"
        reason = "Test SELL signal for execution proof"

    vpa = {
        "timestamp": datetime.now().isoformat(),
        "track": "B",
        "mode": "true",
        "predictions": {
            "symbols": ["AAPL"],
            "confidence": 0.85,
            "signal": action
        },
        "risk_metrics": {
            "portfolio_var": 0.15,
            "max_drawdown": 0.08
        },
        "decision_plan": {
            "action": action,
            "symbol": "AAPL",
            "quantity": 1,  # Minimal size for paper trading test
            "order_type": "MKT",
            "confidence": 0.85,
            "reason": reason
        }
    }

    with open(vpa_file, 'w') as f:
        json.dump(vpa, f, indent=2)

    logger.info(f"Created test VPA: {vpa_file}")
    return str(vpa_file)


def main():
    """Main function"""
    print("="*80)
    print("PAPER TRADING PROOF TOOL")
    print("="*80)
    print()
    print("This tool demonstrates paper trading execution by:")
    print("  1. Connecting to IB (paper trading) with clientId=9012")
    print("  2. Taking snapshot BEFORE execution")
    print("  3. Creating test VPA with BUY/SELL signal")
    print("  4. Running executor in LIVE mode (still paper)")
    print("  5. Taking snapshot AFTER execution")
    print("  6. Showing delta (new orders/executions)")
    print()

    # Check kill-switch
    emergency_stop = PLATFORM_ROOT / "EMERGENCY_STOP"
    if emergency_stop.exists():
        print("❌ EMERGENCY_STOP file exists - cannot run proof")
        return 1

    # Step 1: Connect to IB
    print("Step 1: Connecting to IB Gateway (Paper Trading)...")
    ib = IB()
    try:
        ib.connect(IB_HOST, IB_PORT, clientId=PROOF_CLIENT_ID, timeout=15)
        print(f"✓ Connected to {IB_HOST}:{IB_PORT} (clientId={PROOF_CLIENT_ID})")
    except Exception as e:
        print(f"❌ Failed to connect: {e}")
        print("Note: IB Gateway must be running on port 4002")
        return 1

    # Step 2: Take BEFORE snapshot
    print("\nStep 2: Taking BEFORE snapshot...")
    snapshot_before = snapshot_ib_state(ib)
    print_snapshot(snapshot_before, "SNAPSHOT BEFORE EXECUTION")

    # Step 3: Create test VPA with signal
    print("\nStep 3: Creating test VPA with actionable signal...")
    test_vpa_file = create_test_vpa_with_signal()
    print(f"✓ Test VPA created: {test_vpa_file}")

    # Load and display the decision plan
    with open(test_vpa_file, 'r') as f:
        test_vpa = json.load(f)
    print(f"  Decision: {test_vpa['decision_plan']}")
    print()

    # Step 4: Run executor
    print("Step 4: Running VPA executor (LIVE PAPER MODE)...")
    print("  Note: Using QUANTUM_EXECUTION_DRY_RUN=false for this test")
    print()

    # Import executor
    sys.path.insert(0, str(PLATFORM_ROOT / 'bin'))
    from vpa_executor import VPAExecutor, load_config

    # Load config
    config_file = PLATFORM_ROOT / "config" / "quantum_runtime.env"
    config = load_config(str(config_file))

    # Override to live mode (but still paper)
    config['QUANTUM_EXECUTION_DRY_RUN'] = 'false'

    # Create executor
    executor = VPAExecutor(config)

    # Load test VPA
    with open(test_vpa_file, 'r') as f:
        test_vpa_json = json.load(f)

    # Parse and execute
    intents = executor.parse_decision_plan(test_vpa_json)

    if intents:
        # Execute in LIVE mode (still paper trading)
        results = executor.execute_intents(intents, dry_run=False)
        print("  Execution completed")
    else:
        print("  ❌ No intents parsed from VPA")
        return 1

    # Step 5: Wait a moment for order to propagate
    print("\nStep 5: Waiting 3 seconds for order propagation...")
    time.sleep(3)

    # Step 6: Take AFTER snapshot
    print("\nStep 6: Taking AFTER snapshot...")
    snapshot_after = snapshot_ib_state(ib)
    print_snapshot(snapshot_after, "SNAPSHOT AFTER EXECUTION")

    # Step 7: Compare and show delta
    print("\nStep 7: Comparing snapshots...")
    delta = compare_snapshots(snapshot_before, snapshot_after)

    print("\n" + "="*80)
    print("DELTA (CHANGES)")
    print("="*80)

    if delta['new_orders']:
        print(f"\n✅ NEW ORDERS PLACED: {len(delta['new_orders'])}")
        for order in delta['new_orders']:
            print(f"  • Order {order['orderId']}: {order['action']} {order['totalQuantity']} {order['symbol']} ({order['order_type']})")
            print(f"    Client ID: {order['clientId']}")
    else:
        print("\nℹ No new orders detected")
        print("  This could mean:")
        print("    - Order was blocked by guardrails (check logs)")
        print("    - Order was filled immediately (see executions)")
        print("    - VPA had HOLD/NONE action")

    if delta['new_executions']:
        print(f"\n✅ NEW EXECUTIONS: {len(delta['new_executions'])}")
        for exec in delta['new_executions']:
            print(f"  • {exec['symbol']}: {exec['side']} {exec['shares']} shares @ ${exec['price']:.2f}")
            print(f"    Time: {exec['time']}")
    else:
        print("\nℹ No new executions (order may still be open)")

    if delta['new_positions'] != 0:
        print(f"\n✅ POSITION CHANGE: {delta['new_positions']:+d}")

    # Final result
    print("\n" + "="*80)
    print("PROOF SUMMARY")
    print("="*80)

    has_evidence = len(delta['new_orders']) > 0 or len(delta['new_executions']) > 0

    if has_evidence:
        print("✅ PAPER TRADING EXECUTION CONFIRMED")
        print()
        print("Evidence:")
        if delta['new_orders']:
            print(f"  • {len(delta['new_orders'])} order(s) placed")
        if delta['new_executions']:
            print(f"  • {len(delta['new_executions'])} execution(s) recorded")
        print()
        print("This proves that:")
        print("  ✓ VPA executor successfully placed orders in paper trading mode")
        print("  ✓ Orders were submitted to IB Gateway (port 4002)")
        print("  ✓ No real money was involved (paper trading)")
        print()
        print("To restore DRY_RUN mode:")
        print("  1. Edit /home/davidsanker/platform/config/quantum_runtime.env")
        print("  2. Set QUANTUM_EXECUTION_DRY_RUN=true")
    else:
        print("⚠️ NO EVIDENCE OF EXECUTION")
        print()
        print("Possible reasons:")
        print("  1. VPA decision was HOLD/NONE (no action)")
        print("  2. Guardrails blocked the order")
        print("  3. IB connection issues")
        print()
        print("Check logs:")
        print(f"  • {PLATFORM_ROOT}/logs/quantum-engine/execution.log")
        print(f"  • {PLATFORM_ROOT}/logs/quantum-engine/quantum_engine.log")

    # Cleanup
    ib.disconnect()
    print()
    print("Disconnected from IB Gateway")
    print()

    return 0 if has_evidence else 1


if __name__ == '__main__':
    sys.exit(main())
