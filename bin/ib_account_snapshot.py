#!/usr/bin/env python3
"""
IB Account Snapshot - Fast, Read-Only Portfolio Query with Retries
Generated: 2026-01-22 07:40:00 UTC
Purpose: Lightweight portfolio snapshot with retry logic and clientId rotation
"""

import sys
import os
import json
import time
from datetime import datetime, timedelta

# Try to find venv python
VENV_PATHS = [
    "/home/davidsanker/trading_bot_venv/bin/python",
    "/home/davidsanker/venv/bin/python",
    "python3"
]

def find_python():
    """Find available Python with ib_insync"""
    for path in VENV_PATHS:
        if os.path.exists(path):
            return path
    return "python3"

def get_snapshot_with_retry(client_ids=None, max_attempts=3, timeout_per_attempt=3):
    """
    Get IB account snapshot with retry logic

    Args:
        client_ids: List of clientIds to try (default: [9011, 9012, 9013])
        max_attempts: Maximum number of connection attempts
        timeout_per_attempt: Timeout in seconds for each attempt

    Returns:
        Dictionary with snapshot data or error
    """
    if client_ids is None:
        client_ids = [9011, 9012, 9013]

    last_error = None

    for attempt, client_id in enumerate(client_ids[:max_attempts], 1):
        try:
            from ib_insync import IB

            ib = IB()
            start_time = time.time()

            # Connect with timeout and specific clientId
            ib.connect('127.0.0.1', 4002, clientId=client_id, timeout=timeout_per_attempt)

            if not ib.isConnected():
                last_error = "Not connected"
                if attempt < max_attempts:
                    time.sleep(1)
                    continue
                else:
                    break

            # Get basic account info (count only, no IDs)
            managed_accounts = ib.managedAccounts()
            account_count = len(managed_accounts)

            # Get account values (key metrics only)
            account_summary = ib.accountSummary()
            values = {}
            for item in account_summary:
                tag = item.tag
                value = item.value
                if tag in ['NetLiquidation', 'TotalCashValue', 'UnrealizedPnL', 'RealizedPnL', 'EquityWithLoanValue']:
                    values[tag] = str(value)

            # Get positions (top 8, no account IDs)
            positions = ib.positions()
            position_list = []
            for pos in positions[:8]:
                position_list.append({
                    'symbol': pos.contract.symbol,
                    'position': pos.position,
                    'avgCost': f"{pos.averageCost:.2f}" if hasattr(pos, 'averageCost') else 'N/A',
                    'marketPrice': f"{pos.marketPrice():.2f}" if hasattr(pos, 'marketPrice') else 'N/A',
                    'marketValue': f"{pos.marketValue:.2f}" if hasattr(pos, 'marketValue') else 'N/A'
                })

            # Get open orders
            open_orders = ib.openOrders()
            open_orders_count = len(open_orders)

            # Get recent executions (last 24 hours or last 5)
            executions = ib.executions()
            now = datetime.now()
            recent_execs = []

            # Filter for last 24 hours
            for exec in executions:
                exec_time = exec.time
                if isinstance(exec_time, str):
                    try:
                        exec_time = datetime.fromisoformat(exec_time.replace('Z', '+00:00'))
                    except:
                        continue

                if exec_time > now - timedelta(hours=24):
                    recent_execs.append(exec)

            # Take last 5
            recent_execs = sorted(recent_execs, key=lambda x: x.time, reverse=True)[:5]

            execution_list = []
            for exec in recent_execs:
                execution_list.append({
                    'time': str(exec.time),
                    'symbol': exec.contract.symbol if exec.contract else 'N/A',
                    'side': exec.side,
                    'qty': exec.shares,
                    'price': f"{exec.price:.2f}" if hasattr(exec, 'price') else 'N/A'
                })

            # Disconnect
            ib.disconnect()

            return {
                "connected": True,
                "timestamp": datetime.now().isoformat(),
                "accounts": account_count,
                "values": values,
                "positions_count": len(positions),
                "positions": position_list,
                "open_orders": open_orders_count,
                "executions_count": len(execution_list),
                "executions": execution_list,
                "attempts": attempt,
                "client_id": client_id
            }

        except Exception as e:
            error_str = str(e)
            last_error = error_str

            # Check for specific error types
            if "clientId" in error_str and "in use" in error_str.lower():
                last_error = f"clientId {client_id} already in use"
            elif "timeout" in error_str.lower() or "timed out" in error_str.lower():
                last_error = f"Connection timeout (clientId {client_id})"
            else:
                last_error = f"Connection failed (clientId {client_id}): {error_str}"

            # Retry if not last attempt
            if attempt < max_attempts:
                time.sleep(1)
                continue

    # All attempts failed
    return {
        "error": last_error,
        "connected": False,
        "attempts": max_attempts
    }

if __name__ == "__main__":
    # Allow override via environment variable
    client_id_override = os.environ.get("CLIENT_ID_OVERRIDE")
    max_attempts_override = os.environ.get("MAX_ATTEMPTS", "3")
    timeout_override = os.environ.get("TIMEOUT_SECONDS", "3")

    # Build client ID list
    if client_id_override:
        client_ids = [int(client_id_override)]
    else:
        client_ids = [9011, 9012, 9013]

    # Get snapshot with retry
    result = get_snapshot_with_retry(
        client_ids=client_ids,
        max_attempts=int(max_attempts_override),
        timeout_per_attempt=int(timeout_override)
    )

    # Print compact JSON output
    print(json.dumps(result, indent=2))

    # Exit code based on connection
    if result.get("connected"):
        sys.exit(0)
    else:
        sys.exit(1)
