#!/usr/bin/env python3
"""
Connection Health Check Script
Monitors IB connection health and reports status

Usage:
    python3 check_connection_health.py [--json] [--alert]

Options:
    --json: Output in JSON format
    --alert: Send alert if connection is down

Author: David Sanker
Date: January 28, 2026
"""

import sys
import json
import argparse
import logging
from datetime import datetime

# Add paths
sys.path.insert(0, '/home/davidsanker/platform')
sys.path.insert(0, '/home/davidsanker/quantum-trading-bot-new')

from ib_insync import IB

# Configuration
IB_HOST = "127.0.0.1"
IB_PORT = 4002
TEST_CLIENT_ID = 997  # Dedicated client ID for health checks
TIMEOUT = 10

logging.basicConfig(level=logging.WARNING)
logger = logging.getLogger(__name__)


def check_ib_connection():
    """
    Check IB Gateway connection health

    Returns:
        dict: Health status information
    """
    status = {
        'timestamp': datetime.now().isoformat(),
        'host': IB_HOST,
        'port': IB_PORT,
        'is_connected': False,
        'is_healthy': False,
        'accounts': [],
        'positions_count': 0,
        'orders_count': 0,
        'error': None,
        'latency_ms': None
    }

    ib = IB()

    try:
        # Measure connection latency
        start_time = datetime.now()

        ib.connect(IB_HOST, IB_PORT, clientId=TEST_CLIENT_ID, timeout=TIMEOUT)

        connection_time = (datetime.now() - start_time).total_seconds() * 1000
        status['latency_ms'] = round(connection_time, 2)
        status['is_connected'] = True

        # Get account info
        accounts = ib.managedAccounts()
        status['accounts'] = accounts

        # Get positions
        positions = ib.positions()
        status['positions_count'] = len(positions)

        # Get orders
        orders = ib.openOrders()
        status['orders_count'] = len(orders)

        # Connection is healthy if we got this far
        status['is_healthy'] = True

        ib.disconnect()

    except Exception as e:
        status['error'] = str(e)
        status['is_healthy'] = False
        logger.error(f"Health check failed: {e}")

    return status


def format_status_human(status):
    """Format status for human-readable output"""
    output = []
    output.append("=" * 60)
    output.append("IB CONNECTION HEALTH CHECK")
    output.append("=" * 60)
    output.append(f"Timestamp: {status['timestamp']}")
    output.append(f"Target: {status['host']}:{status['port']}")
    output.append("")

    if status['is_healthy']:
        output.append("✅ STATUS: HEALTHY")
        output.append(f"   Latency: {status['latency_ms']}ms")
        output.append(f"   Accounts: {', '.join(status['accounts'])}")
        output.append(f"   Open Positions: {status['positions_count']}")
        output.append(f"   Open Orders: {status['orders_count']}")
    else:
        output.append("❌ STATUS: UNHEALTHY")
        if status['error']:
            output.append(f"   Error: {status['error']}")

    output.append("=" * 60)
    return "\n".join(output)


def send_alert(status):
    """Send alert if connection is down"""
    if not status['is_healthy']:
        # Here you could integrate with email, Slack, PagerDuty, etc.
        logger.warning(f"ALERT: IB Connection is DOWN - {status['error']}")

        # Write alert to file
        with open('/home/davidsanker/platform/logs/connection_alerts.log', 'a') as f:
            f.write(f"{status['timestamp']} - CONNECTION DOWN: {status['error']}\n")


def main():
    parser = argparse.ArgumentParser(description='Check IB connection health')
    parser.add_argument('--json', action='store_true', help='Output in JSON format')
    parser.add_argument('--alert', action='store_true', help='Send alert if unhealthy')
    args = parser.parse_args()

    # Run health check
    status = check_ib_connection()

    # Send alert if requested and unhealthy
    if args.alert and not status['is_healthy']:
        send_alert(status)

    # Output results
    if args.json:
        print(json.dumps(status, indent=2))
    else:
        print(format_status_human(status))

    # Exit code: 0 if healthy, 1 if unhealthy
    sys.exit(0 if status['is_healthy'] else 1)


if __name__ == "__main__":
    main()
