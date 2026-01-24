#!/usr/bin/env python3
"""
Email Report Generator - Trading System Status
Generated: 2026-01-22 07:42:00 UTC
Purpose: Generate plaintext email report with portfolio, trades, bot status
"""

import os
import sys
import json
from datetime import datetime, timedelta

# Paths
PLATFORM_ROOT = "/home/davidsanker/platform"
VPA_STORAGE = f"{PLATFORM_ROOT}/vpa_storage"
EXECUTION_DIR = f"{PLATFORM_ROOT}/execution_receipts"
LOG_DIR = f"{PLATFORM_ROOT}/logs/quantum-engine"
INCIDENTS_DIR = f"{PLATFORM_ROOT}/logs/incidents"
CONFIG_FILE = f"{PLATFORM_ROOT}/config/quantum_runtime.env"

def get_timestamp():
    """Get current timestamp in UTC"""
    return datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')

def get_gateway_health():
    """Check IB Gateway health"""
    try:
        import subprocess
        result = subprocess.run(
            [f"{PLATFORM_ROOT}/bin/validate_ib_gateway.sh", "paper"],
            capture_output=True,
            text=True,
            timeout=5
        )
        if result.returncode == 0:
            return "✓ Healthy", ""
        else:
            return "⚠ Unhealthy", f"Exit code {result.returncode}"
    except Exception as e:
        return "⚠ Error", str(e)

def get_bot_service_status():
    """Get active bot service status"""
    try:
        import subprocess

        # Check which service is active
        services = [
            "trading-bot-quantum.service",
            "trading-bot.service",
            "trading-bot-mvp.service"
        ]

        active_service = None
        for svc in services:
            result = subprocess.run(
                ["systemctl", "--user", "is-active", svc],
                capture_output=True,
                text=True
            )
            if result.stdout.strip() == "active":
                active_service = svc
                break

        if not active_service:
            return "INACTIVE", "No active service", "", "", ""

        # Get service details
        result = subprocess.run(
            ["systemctl", "--user", "show", active_service,
             "--property=MainPID", "--property=ActiveState",
             "--property=SubState", "--property=ActiveEnterTimestamp"],
            capture_output=True,
            text=True
        )

        pid = ""
        state = ""
        substate = ""
        uptime_ts = ""

        for line in result.stdout.split('\n'):
            if line.startswith('MainPID='):
                pid = line.split('=', 1)[1]
            elif line.startswith('ActiveState='):
                state = line.split('=', 1)[1]
            elif line.startswith('SubState='):
                substate = line.split('=', 1)[1]
            elif line.startswith('ActiveEnterTimestamp='):
                uptime_ts = line.split('=', 1)[1]

        # Calculate uptime
        uptime_str = "Unknown"
        if uptime_ts:
            try:
                start_time = datetime.fromisoformat(uptime_ts)
                uptime = datetime.now() - start_time
                hours = int(uptime.total_seconds() // 3600)
                mins = int((uptime.total_seconds() % 3600) // 60)
                uptime_str = f"{hours}h {mins}m"
            except:
                pass

        return active_service, f"{state} ({substate})", pid, uptime_str, ""

    except Exception as e:
        return "ERROR", str(e), "", "", ""

def get_portfolio_snapshot():
    """Get portfolio snapshot from IB"""
    try:
        import subprocess
        result = subprocess.run(
            [f"{PLATFORM_ROOT}/bin/ib_account_snapshot.py"],
            capture_output=True,
            text=True,
            timeout=10
        )

        if result.returncode != 0:
            return None, result.stderr or "Snapshot failed"

        data = json.loads(result.stdout)

        if not data.get("connected"):
            return None, data.get("error", "Not connected")

        # Extract key metrics
        values = data.get("values", {})
        positions_count = data.get("positions_count", 0)
        open_orders = data.get("open_orders", 0)
        executions_count = data.get("executions_count", 0)

        return {
            "net_liquidation": values.get("NetLiquidation", "N/A"),
            "cash": values.get("TotalCashValue", "N/A"),
            "unrealized_pnl": values.get("UnrealizedPnL", "N/A"),
            "realized_pnl": values.get("RealizedPnL", "N/A"),
            "positions": positions_count,
            "open_orders": open_orders,
            "executions_24h": executions_count
        }, ""

    except Exception as e:
        return None, str(e)

def get_execution_receipts(count=5):
    """Get recent execution receipts"""
    try:
        import subprocess

        result = subprocess.run(
            ["find", EXECUTION_DIR, "-name", "*.json", "-type", "f",
             "-mtime", "-2", "-printf", '%T@ %p\n'],
            capture_output=True,
            text=True,
            timeout=5
        )

        if result.returncode != 0:
            return []

        # Sort by timestamp and get last N
        lines = sorted(result.stdout.strip().split('\n'),
                     key=lambda x: float(x.split()[0]) if x.split() else 0,
                     reverse=True)[:count]

        receipts = []
        for line in lines:
            if not line.strip():
                continue
            parts = line.split()
            if len(parts) < 2:
                continue

            filepath = parts[1]
            try:
                with open(filepath, 'r') as f:
                    data = json.load(f)

                timestamp = data.get("timestamp", "N/A")
                intent = data.get("intent", {})
                order_result = data.get("order_result", {})
                guardrail = data.get("guardrail_result", {})

                receipt = {
                    "timestamp": timestamp,
                    "action": intent.get("action", "N/A"),
                    "symbol": intent.get("symbol", "N/A"),
                    "confidence": intent.get("confidence", 0),
                    "status": order_result.get("status", "N/A"),
                    "dry_run": data.get("dry_run", True),
                    "blocked_reason": order_result.get("reason", guardrail.get("reason", ""))
                }
                receipts.append(receipt)
            except:
                continue

        return receipts

    except Exception as e:
        return []

def get_last_vpa():
    """Get last VPA decision"""
    try:
        import subprocess

        result = subprocess.run(
            ["find", VPA_STORAGE, "-name", "vpa_*.json", "-type", "f",
             "-printf", '%T@ %p\n'],
            capture_output=True,
            text=True,
            timeout=5
        )

        if result.returncode != 0:
            return None

        lines = sorted(result.stdout.strip().split('\n'),
                     key=lambda x: float(x.split()[0]) if x.split() else 0,
                     reverse=True)

        if not lines or not lines[0].strip():
            return None

        filepath = lines[0].split()[1]
        with open(filepath, 'r') as f:
            data = json.load(f)

        decision_plan = data.get("decision_plan", {})
        model_metadata = decision_plan.get("model_metadata", {})

        return {
            "timestamp": data.get("timestamp", "N/A"),
            "action": decision_plan.get("action", "N/A"),
            "symbol": decision_plan.get("symbol", "N/A"),
            "confidence": decision_plan.get("confidence", 0),
            "reasons": decision_plan.get("reasons", []),
            "dry_run": model_metadata.get("dry_run", True),
            "forecast_model": model_metadata.get("forecast_model", "N/A"),
            "signal_model": model_metadata.get("signal_model", "N/A")
        }

    except Exception as e:
        return None

def get_incidents_count(hours=24):
    """Count incidents in last N hours"""
    try:
        import subprocess

        # Find incident files modified in last N hours
        result = subprocess.run(
            ["find", INCIDENTS_DIR, "-name", "*.json", "-type", "f",
             "-mtime", f"-{hours/24:.1f}", "-print"],
            capture_output=True,
            text=True,
            timeout=5
        )

        if result.returncode != 0:
            return 0

        count = len([line for line in result.stdout.strip().split('\n') if line.strip()])
        return count

    except:
        return 0

def get_trading_gates():
    """Get execution gates status"""
    try:
        if not os.path.exists(CONFIG_FILE):
            return {}, "Config file not found"

        with open(CONFIG_FILE, 'r') as f:
            config = {}
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    key, value = line.split('=', 1)
                    config[key.strip()] = value.strip()

        return {
            "dry_run": config.get("QUANTUM_EXECUTION_DRY_RUN", "true"),
            "exec_enabled": config.get("QUANTUM_EXECUTION_ENABLED", "false"),
            "kill_switch": os.path.exists(f"{PLATFORM_ROOT}/EMERGENCY_STOP")
        }, ""

    except Exception as e:
        return {}, str(e)

def generate_report():
    """Generate complete email report"""
    lines = []
    lines.append("=" * 70)
    lines.append("TRADING SYSTEM REPORT")
    lines.append(f"Generated: {get_timestamp()}")
    lines.append(f"Host: {os.uname().nodename}")
    lines.append("=" * 70)
    lines.append("")

    # Gateway Health
    lines.append("GATEWAY HEALTH")
    lines.append("-" * 40)
    gateway_status, gateway_hint = get_gateway_health()
    lines.append(f"  Status: {gateway_status}")
    if gateway_hint:
        lines.append(f"  Note: {gateway_hint}")
    lines.append("")

    # Bot Service Status
    lines.append("BOT SERVICE")
    lines.append("-" * 40)
    service, state, pid, uptime, error = get_bot_service_status()
    lines.append(f"  Service: {service}")
    lines.append(f"  State: {state}")
    if pid:
        lines.append(f"  PID: {pid}")
    if uptime:
        lines.append(f"  Uptime: {uptime}")
    lines.append("")

    # Execution Gates
    lines.append("EXECUTION GATES")
    lines.append("-" * 40)
    gates, gates_error = get_trading_gates()
    if gates_error:
        lines.append(f"  Error: {gates_error}")
    else:
        dry_run = gates.get("dry_run", "true")
        exec_enabled = gates.get("exec_enabled", "false")
        kill_switch = gates.get("kill_switch", False)

        if dry_run == "false":
            lines.append(f"  DRY_RUN: false (orders can execute)")
        else:
            lines.append(f"  DRY_RUN: true (orders blocked)")

        lines.append(f"  Execution Enabled: {exec_enabled}")

        if kill_switch:
            lines.append(f"  Kill-Switch: 🛑 ACTIVE")
        else:
            lines.append(f"  Kill-Switch: ✓ Off")
    lines.append("")

    # Portfolio Snapshot
    lines.append("PORTFOLIO SNAPSHOT")
    lines.append("-" * 40)
    portfolio, portfolio_error = get_portfolio_snapshot()
    if portfolio_error:
        lines.append(f"  Status: Unavailable")
        lines.append(f"  Reason: {portfolio_error}")
    elif portfolio:
        lines.append(f"  Net Liquidation: {portfolio['net_liquidation']}")
        lines.append(f"  Cash: {portfolio['cash']}")
        lines.append(f"  Unrealized P&L: {portfolio['unrealized_pnl']}")
        lines.append(f"  Realized P&L: {portfolio['realized_pnl']}")
        lines.append(f"  Positions: {portfolio['positions']}")
        lines.append(f"  Open Orders: {portfolio['open_orders']}")
        lines.append(f"  Executions (24h): {portfolio['executions_24h']}")
    else:
        lines.append("  Status: Unavailable")
    lines.append("")

    # Recent Executions
    lines.append("RECENT EXECUTIONS (Last 5)")
    lines.append("-" * 40)
    receipts = get_execution_receipts(5)
    if not receipts:
        lines.append("  No recent executions")
    else:
        for receipt in receipts:
            ts = receipt.get("timestamp", "N/A")
            action = receipt.get("action", "N/A")
            symbol = receipt.get("symbol", "N/A")
            status = receipt.get("status", "N/A")
            dry = "DRY" if receipt.get("dry_run", True) else "LIVE"
            blocked = receipt.get("blocked_reason", "")

            lines.append(f"  {ts}")
            lines.append(f"    {action} {symbol} [{dry}] {status}")
            if blocked:
                lines.append(f"    → {blocked}")
    lines.append("")

    # Last VPA Decision
    lines.append("LAST VPA DECISION")
    lines.append("-" * 40)
    vpa = get_last_vpa()
    if not vpa:
        lines.append("  No VPA artifacts found")
    else:
        ts = vpa.get("timestamp", "N/A")
        action = vpa.get("action", "N/A")
        symbol = vpa.get("symbol", "N/A")
        conf = vpa.get("confidence", 0)
        reasons = vpa.get("reasons", [])
        dry = "DRY_RUN" if vpa.get("dry_run", True) else "LIVE"
        forecast = vpa.get("forecast_model", "N/A")
        signal = vpa.get("signal_model", "N/A")

        lines.append(f"  Timestamp: {ts}")
        lines.append(f"  Decision: {action} {symbol}")
        lines.append(f"  Confidence: {conf:.2%}")
        lines.append(f"  Mode: {dry}")
        lines.append(f"  Forecast: {forecast}")
        lines.append(f"  Signal: {signal}")
        if reasons:
            lines.append(f"  Reasons: {', '.join(reasons[:3])}")
    lines.append("")

    # Incidents
    lines.append("INCIDENTS (Last 24h)")
    lines.append("-" * 40)
    incident_count = get_incidents_count(24)
    lines.append(f"  Count: {incident_count}")
    lines.append("")

    # Footer
    lines.append("=" * 70)
    lines.append("END OF REPORT")
    lines.append("")

    return "\n".join(lines)

if __name__ == "__main__":
    report = generate_report()
    print(report)
