#!/usr/bin/env python3
"""
Email Report Generator - Trading System Status (Enhanced)
Generated: 2026-01-22
Purpose: Generate plaintext email report with portfolio, trades, bot status, learning state
"""

import os
import sys
import json
import subprocess
from datetime import datetime, timedelta, timezone
from pathlib import Path

# Paths
PLATFORM_ROOT = Path("/home/davidsanker/platform")
VPA_STORAGE = PLATFORM_ROOT / "vpa_storage"
EXECUTION_DIR = PLATFORM_ROOT / "execution_receipts"
LOG_DIR = PLATFORM_ROOT / "logs/quantum-engine"
INCIDENTS_DIR = PLATFORM_ROOT / "logs/incidents"
CONFIG_FILE = PLATFORM_ROOT / "config/quantum_runtime.env"
LEARNER_STATE_FILE = PLATFORM_ROOT / "state/learner_state.json"

def get_timestamps():
    """Get current timestamp in UTC and Berlin"""
    utc_now = datetime.now(timezone.utc)
    berlin_tz = timezone(timedelta(hours=1))  # CET (CEST is +2, we'll handle DST simply)
    # Note: For proper DST handling, would use zoneinfo (Python 3.9+)
    # For now, using CET+1 as approximation

    utc_str = utc_now.strftime('%Y-%m-%d %H:%M:%S UTC')
    berlin_str = (utc_now + timedelta(hours=1)).strftime('%Y-%m-%d %H:%M:%S Berlin')

    return utc_str, berlin_str

def get_gateway_health():
    """Check IB Gateway health"""
    try:
        result = subprocess.run(
            [str(PLATFORM_ROOT / "bin/validate_ib_gateway.sh"), "paper"],
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

def get_services_status():
    """Get status of all trading services (checks both systemd and direct processes)"""
    services_status = {}

    # Check IB Gateway - prefer process detection over systemd
    try:
        result = subprocess.run(
            ["pgrep", "-f", "IbcGateway|ibgateway"],
            capture_output=True, text=True, timeout=3
        )
        if result.returncode == 0 and result.stdout.strip():
            pid = result.stdout.strip().split('\n')[0]
            services_status["ibgateway"] = f"active (pid {pid})"
        else:
            # Fallback to systemd check
            result = subprocess.run(
                ["systemctl", "is-active", "ibgateway.service"],
                capture_output=True, text=True, timeout=3
            )
            services_status["ibgateway"] = result.stdout.strip()
    except:
        services_status["ibgateway"] = "unknown"

    # Check Quantum Trading Bot - prefer process detection
    try:
        result = subprocess.run(
            ["pgrep", "-f", "quantum_trading_bot"],
            capture_output=True, text=True, timeout=3
        )
        if result.returncode == 0 and result.stdout.strip():
            pid = result.stdout.strip().split('\n')[0]
            services_status["quantum-bot"] = f"active (pid {pid})"
        else:
            services_status["quantum-bot"] = "inactive"
    except:
        services_status["quantum-bot"] = "unknown"

    # Check other user services
    user_services = [
        "trading-bot.service",
        "trading-watchdog.service"
    ]

    for svc in user_services:
        try:
            result = subprocess.run(
                ["systemctl", "--user", "is-active", svc],
                capture_output=True, text=True, timeout=3
            )
            services_status[svc] = result.stdout.strip()
        except:
            services_status[svc] = "unknown"

    return services_status

def get_active_bot_service():
    """Get active bot service details (checks direct processes first, then systemd)"""
    try:
        # First check for direct quantum bot process
        result = subprocess.run(
            ["pgrep", "-af", "quantum_trading_bot"],
            capture_output=True, text=True, timeout=3
        )
        if result.returncode == 0 and result.stdout.strip():
            line = result.stdout.strip().split('\n')[0]
            pid = line.split()[0]
            # Get process start time for uptime
            uptime_str = ""
            try:
                stat_result = subprocess.run(
                    ["ps", "-o", "etime=", "-p", pid],
                    capture_output=True, text=True, timeout=3
                )
                if stat_result.returncode == 0:
                    uptime_str = stat_result.stdout.strip()
            except:
                pass
            return "quantum-bot (process)", "active (running)", pid, uptime_str

        # Fallback: check systemd services
        services = [
            "trading-bot-quantum.service",
            "trading-bot.service",
            "trading-bot-mvp.service"
        ]

        active_service = None
        for svc in services:
            result = subprocess.run(
                ["systemctl", "--user", "is-active", svc],
                capture_output=True, text=True
            )
            if result.stdout.strip() == "active":
                active_service = svc
                break

        if not active_service:
            # Check day of week - if weekend, note it
            now = datetime.now()
            if now.weekday() >= 5:
                return "INACTIVE", "Weekend - markets closed", "", ""
            return "INACTIVE", "No active service", "", ""

        # Get service details
        result = subprocess.run(
            ["systemctl", "--user", "show", active_service,
             "--property=MainPID", "--property=ActiveState",
             "--property=SubState", "--property=ActiveEnterTimestamp"],
            capture_output=True, text=True
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
                uptime = datetime.now(timezone.utc) - start_time
                hours = int(uptime.total_seconds() // 3600)
                mins = int((uptime.total_seconds() % 3600) // 60)
                uptime_str = f"{hours}h {mins}m"
            except:
                pass

        return active_service, f"{state} ({substate})", pid, uptime_str

    except Exception as e:
        return "ERROR", str(e), "", ""

def get_portfolio_snapshot():
    """Get portfolio snapshot from IB with retries"""
    max_retries = 2
    retry_delay = 2

    for attempt in range(max_retries):
        try:
            result = subprocess.run(
                [str(PLATFORM_ROOT / "bin/ib_account_snapshot.py")],
                capture_output=True,
                text=True,
                timeout=15
            )

            if result.returncode != 0:
                if attempt < max_retries - 1:
                    import time
                    time.sleep(retry_delay)
                    continue
                return None, result.stderr or "Snapshot failed"

            data = json.loads(result.stdout)

            if not data.get("connected"):
                return None, data.get("error", "Not connected")

            # Extract key metrics
            values = data.get("values", {})
            positions = data.get("positions", [])
            positions_count = len(positions)

            # Get top 8 positions by value
            top_positions = []
            for pos in positions[:8]:
                symbol = pos.get("symbol", "N/A")
                quantity = pos.get("position", "N/A")
                market_price = pos.get("marketPrice", "N/A")
                market_value = pos.get("marketValue", "N/A")
                top_positions.append(f"{symbol}: {quantity} shares @ ${market_price} (${market_value})")

            return {
                "net_liquidation": values.get("NetLiquidation", "N/A"),
                "cash": values.get("TotalCashValue", "N/A"),
                "unrealized_pnl": values.get("UnrealizedPnL", "N/A"),
                "realized_pnl": values.get("RealizedPnL", "N/A"),
                "positions_count": positions_count,
                "top_positions": top_positions
            }, ""

        except subprocess.TimeoutExpired:
            if attempt < max_retries - 1:
                import time
                time.sleep(retry_delay)
                continue
            return None, "Timeout (IB Gateway busy?)"
        except Exception as e:
            return None, str(e)

    return None, "Max retries exceeded"

def get_execution_receipts(count=5):
    """Get recent execution receipts"""
    try:
        result = subprocess.run(
            ["find", str(EXECUTION_DIR), "-name", "*.json", "-type", "f",
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
        result = subprocess.run(
            ["find", str(VPA_STORAGE), "-name", "vpa_*.json", "-type", "f",
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

def get_learning_summary():
    """Get learning state summary"""
    try:
        if not LEARNER_STATE_FILE.exists():
            return None

        with open(LEARNER_STATE_FILE, 'r') as f:
            state = json.load(f)

        last_update = state.get("last_update", "Never")
        signal_weights = state.get("signal_weights", {})
        learning_stats = state.get("learning_stats", {})

        # Get top 3 weights
        sorted_weights = sorted(signal_weights.items(), key=lambda x: x[1], reverse=True)[:3]

        return {
            "last_update": last_update,
            "top_weights": sorted_weights,
            "total_trades": learning_stats.get("total_trades", 0)
        }

    except Exception as e:
        return None

def get_incidents_summary(hours=24):
    """Get incident summary for last N hours"""
    try:
        # Find incident files modified in last N hours
        result = subprocess.run(
            ["find", str(INCIDENTS_DIR), "-name", "*.json", "-type", "f",
             "-mtime", f"-{hours/24:.1f}", "-printf", '%T@ %p\n'],
            capture_output=True,
            text=True,
            timeout=5
        )

        if result.returncode != 0:
            return 0, None

        lines = sorted(result.stdout.strip().split('\n'),
                     key=lambda x: float(x.split()[0]) if x.split() else 0,
                     reverse=True)

        incident_files = [line.split()[1] for line in lines if line.strip()]
        count = len(incident_files)

        # Get newest incident details
        newest_incident = None
        if incident_files:
            try:
                with open(incident_files[0], 'r') as f:
                    data = json.load(f)
                newest_incident = {
                    "timestamp": data.get("timestamp", "N/A"),
                    "severity": data.get("severity", "unknown"),
                    "message": data.get("message", "")[:100]  # Truncate to 100 chars
                }
            except:
                pass

        return count, newest_incident

    except:
        return 0, None

def get_trading_gates():
    """Get execution gates status"""
    try:
        if not CONFIG_FILE.exists():
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
            "kill_switch": (PLATFORM_ROOT / "EMERGENCY_STOP").exists()
        }, ""

    except Exception as e:
        return {}, str(e)

def generate_report():
    """Generate complete email report"""
    lines = []

    utc_time, berlin_time = get_timestamps()

    lines.append("=" * 70)
    lines.append("TRADING SYSTEM REPORT")
    lines.append(f"Generated: {berlin_time} ({utc_time})")
    lines.append(f"Host: {os.uname().nodename}")
    lines.append("=" * 70)
    lines.append("")

    # Gateway Health
    lines.append("GATEWAY HEALTH")
    lines.append("-" * 40)
    gateway_status, gateway_hint = get_gateway_health()

    # Also check port 4002 (use ss to check if port is listening - nc fails with IB binary protocol)
    port_4002_open = False
    try:
        result = subprocess.run(
            ["ss", "-tlnH", "sport", "=", "4002"],
            capture_output=True,
            text=True,
            timeout=3
        )
        port_4002_open = bool(result.stdout.strip())
    except:
        # Fallback: try socket connect
        try:
            import socket
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.settimeout(2)
            s.connect(("127.0.0.1", 4002))
            s.close()
            port_4002_open = True
        except:
            pass

    lines.append(f"  Validator: {gateway_status}")
    lines.append(f"  Port 4002: {'✓ OPEN' if port_4002_open else '✗ CLOSED'}")
    if gateway_hint:
        lines.append(f"  Note: {gateway_hint}")
    lines.append("")

    # Services Status
    lines.append("SERVICES STATUS")
    lines.append("-" * 40)
    services = get_services_status()
    for svc, status in services.items():
        lines.append(f"  {svc}: {status}")
    lines.append("")

    # Bot Service Status
    lines.append("ACTIVE BOT SERVICE")
    lines.append("-" * 40)
    service, state, pid, uptime = get_active_bot_service()
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
        if "Timeout" in portfolio_error or "busy" in portfolio_error.lower():
            lines.append("  → Hint: IB Gateway may be busy, retry later")
    elif portfolio:
        lines.append(f"  Net Liquidation: ${portfolio['net_liquidation']}")
        lines.append(f"  Cash: ${portfolio['cash']}")
        lines.append(f"  Unrealized P&L: ${portfolio['unrealized_pnl']}")
        lines.append(f"  Realized P&L: ${portfolio['realized_pnl']}")
        lines.append(f"  Positions: {portfolio['positions_count']}")
        if portfolio['top_positions']:
            lines.append(f"  Top Positions:")
            for pos in portfolio['top_positions'][:8]:
                lines.append(f"    - {pos}")
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

    # Learning Summary
    lines.append("LEARNING STATE")
    lines.append("-" * 40)
    learning = get_learning_summary()
    if not learning:
        lines.append("  No learning state found")
    else:
        lines.append(f"  Last Update: {learning['last_update']}")
        lines.append(f"  Total Trades Learned: {learning['total_trades']}")
        if learning['top_weights']:
            lines.append(f"  Top Signal Weights:")
            for signal, weight in learning['top_weights']:
                lines.append(f"    - {signal}: {weight:.4f}")
    lines.append("")

    # Incidents
    lines.append("INCIDENTS (Last 24h)")
    lines.append("-" * 40)
    incident_count, newest_incident = get_incidents_summary(24)
    lines.append(f"  Count: {incident_count}")
    if newest_incident:
        lines.append(f"  Newest Incident:")
        lines.append(f"    Time: {newest_incident['timestamp']}")
        lines.append(f"    Severity: {newest_incident['severity']}")
        lines.append(f"    Message: {newest_incident['message']}")
    lines.append("")

    # Footer
    lines.append("=" * 70)
    lines.append("END OF REPORT")
    lines.append("")

    # Next action hints if unhealthy
    if gateway_status != "✓ Healthy" or not port_4002_open:
        lines.append("⚠ NEXT ACTION HINTS:")
        if gateway_status != "✓ Healthy":
            lines.append("  - Check IB Gateway: systemctl status ibgateway")
        if not port_4002_open:
            lines.append("  - Verify API port: netstat -tlnp | grep 4002")
        lines.append("")

    return "\n".join(lines)

if __name__ == "__main__":
    report = generate_report()
    print(report)
