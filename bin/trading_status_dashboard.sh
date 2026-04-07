#!/bin/bash
# Trading Status Dashboard - Improved & Fixed
# Fixed: 2026-01-22 10:10:00 UTC
# Purpose: Lightweight login dashboard with proper ANSI rendering

PLATFORM_ROOT="/home/davidsanker/platform"
VPA_STORAGE="$PLATFORM_ROOT/vpa_storage"
EXECUTION_DIR="$PLATFORM_ROOT/execution_receipts"
CONFIG_FILE="$PLATFORM_ROOT/config/quantum_runtime.env"

# Timestamp
TIMESTAMP=$(date '+%Y-%m-%d %H:%M:%S')
UPTIME=$(uptime | awk '{print $3,$4}' | tr -d ',')
LOAD=$(uptime | awk -F'load average:' '{print $2}')

# Detect TTY for colors
USE_COLOR=0
if [ -t 1 ]; then
    USE_COLOR=1
fi

# Color definitions
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
GRAY='\033[0;37m'
BOLD='\033[1m'
NC='\033[0m'

# Color functions
color() {
    if [ $USE_COLOR -eq 1 ]; then
        printf '%b' "$1"
    fi
}

reset() {
    if [ $USE_COLOR -eq 1 ]; then
        printf '%b' "$NC"
    fi
}

# ============================================================================
# MAIN DASHBOARD
# ============================================================================

# A) Header
color "$CYAN"
printf '╔════════════════════════════════════════════════════════════════╗\n'
printf '║ %-64s ║\n' "TRADING SYSTEM DASHBOARD"
printf '║ %-64s ║\n' "$TIMESTAMP"
printf '╚════════════════════════════════════════════════════════════════╝\n'
reset
printf '%s' "$(color "$GRAY")"
printf "System: $(hostname)  |  Uptime: %s  |  Load:%s\n" "$UPTIME" "$LOAD"
reset
echo ""

# B) Top-line summary (one glance)
printf '%s' "$(color "$BOLD")"
GATEWAY_STATUS="FAIL"
if timeout 5 "$PLATFORM_ROOT/bin/validate_ib_gateway.sh" paper >/dev/null 2>&1; then
    GATEWAY_STATUS="$(color "$GREEN")OK$(reset)"
else
    GATEWAY_STATUS="$(color "$YELLOW")FAIL$(reset)"
fi

BOT_SERVICE="INACTIVE"
if systemctl is-active --quiet trading-bot-quantum.service 2>/dev/null; then
    BOT_SERVICE="QUANTUM"
elif systemctl is-active --quiet trading-bot.service 2>/dev/null; then
    BOT_SERVICE="MVP"
fi

TRADING_GATE="UNKNOWN"
BOT_LOG_FILE="/home/davidsanker/logs/trading_bot.log"

# Check actual bot log for trading mode
if [ -f "$BOT_LOG_FILE" ]; then
    # Check if bot is running in paper trading mode
    if grep -q "PRODUCTION MODE" "$BOT_LOG_FILE" 2>/dev/null; then
        # Bot is in production mode - check if paper or live
        if grep -q "Paper Trading\|PAPER TRADING" "$BOT_LOG_FILE" 2>/dev/null; then
            TRADING_GATE="$(color "$GREEN")PAPER$(reset)"
        elif grep -q "Live Trading\|LIVE TRADING" "$BOT_LOG_FILE" 2>/dev/null; then
            TRADING_GATE="$(color "$RED")LIVE$(reset)"
        else
            # Check account ID - DUExxxxx = paper trading
            if grep -q "DUE5" "$BOT_LOG_FILE" 2>/dev/null; then
                TRADING_GATE="$(color "$GREEN")PAPER$(reset)"
            else
                TRADING_GATE="$(color "$YELLOW")UNKNOWN$(reset)"
            fi
        fi
    else
        TRADING_GATE="$(color "$YELLOW")DRY_RUN$(reset)"
    fi
fi

# Fallback to config file if bot log not found
if [ "$TRADING_GATE" = "UNKNOWN" ] && [ -f "$CONFIG_FILE" ]; then
    DRY_RUN=$(grep "^QUANTUM_EXECUTION_DRY_RUN=" "$CONFIG_FILE" | cut -d'=' -f2 | cut -d'#' -f1 | tr -d ' ')
    if [ "$DRY_RUN" = "false" ]; then
        # Check if PAPER mode (should always be true)
        PAPER_MODE=$(grep "^PAPER_EXECUTION_MODE=" "$CONFIG_FILE" | cut -d'=' -f2 | cut -d'#' -f1 | tr -d ' ')
        if [ "$PAPER_MODE" = "true" ]; then
            TRADING_GATE="$(color "$GREEN")PAPER$(reset)"
        else
            TRADING_GATE="$(color "$RED")LIVE_BANNED$(reset)"
        fi
    else
        TRADING_GATE="$(color "$YELLOW")DRY_RUN$(reset)"
    fi
fi

LAST_DECISION="N/A"
LAST_EXEC="N/A"

printf "GATEWAY: %s | BOT: %s | GATE: %s | LAST: %s | EXEC: %s\n" \
    "$GATEWAY_STATUS" "$BOT_SERVICE" "$TRADING_GATE" "$LAST_DECISION" "$LAST_EXEC"
reset
echo ""

# C) Services
color "$BLUE"
printf '┌─ Services ───────────────────────────────────────────────────┐\n'
reset

ACTIVE_SERVICE=""
SERVICE_MODE="INACTIVE"
MAIN_PID=""
BOT_TYPE=""

# Check systemd services first
if systemctl is-active --quiet trading-bot-quantum.service 2>/dev/null; then
    ACTIVE_SERVICE="trading-bot-quantum.service"
    SERVICE_MODE="$(color "$GREEN")QUANTUM$(reset) (Paper Trading - Systemd)"
    BOT_TYPE="systemd"
elif systemctl is-active --quiet trading-bot.service 2>/dev/null; then
    ACTIVE_SERVICE="trading-bot.service"
    SERVICE_MODE="$(color "$GREEN")MVP$(reset) (Paper Trading - Systemd)"
    BOT_TYPE="systemd"
# Then check for running Python processes (DIRECT EXECUTION)
elif pgrep -f "quantum_trading_bot.py" > /dev/null 2>&1; then
    MAIN_PID=$(pgrep -f "quantum_trading_bot.py" | head -1)
    SERVICE_MODE="$(color "$GREEN")QUANTUM$(reset) (Paper Trading - Direct)"
    BOT_TYPE="direct"
    ACTIVE_SERVICE="quantum_trading_bot.py (direct)"
elif pgrep -f "trading_bot.py" > /dev/null 2>&1; then
    MAIN_PID=$(pgrep -f "trading_bot.py" | head -1)
    SERVICE_MODE="$(color "$GREEN")MVP$(reset) (Paper Trading - Direct)"
    BOT_TYPE="direct"
    ACTIVE_SERVICE="trading_bot.py (direct)"
fi

printf "  Bot Service: %s\n" "$SERVICE_MODE"

if [ -n "$MAIN_PID" ]; then
    printf "  PID: %s\n" "$MAIN_PID"

    # Calculate uptime from process start time
    if [ "$BOT_TYPE" = "direct" ]; then
        # Get process start time
        UPTIME_SECS=$(ps -p "$MAIN_PID" -o etimes= 2>/dev/null | tr -d ' ' || echo "0")
        if [ -n "$UPTIME_SECS" ] && [ "$UPTIME_SECS" != "0" ]; then
            UPTIME_MINS=$((UPTIME_SECS / 60))
            if [ $UPTIME_MINS -gt 60 ]; then
                UPTIME_HRS=$((UPTIME_MINS / 60))
                printf "  Uptime: %s hours %s minutes\n" "$UPTIME_HRS" $((UPTIME_MINS % 60))
            else
                printf "  Uptime: %s minutes\n" "$UPTIME_MINS"
            fi
        fi
    else
        # Systemd service uptime
        UPTIME_TS=$(systemctl show "$ACTIVE_SERVICE" --property=ActiveEnterTimestamp --value | sed 's/ .*//')
        if [ -n "$UPTIME_TS" ]; then
            START_TIME=$(date -d "$UPTIME_TS" +%s 2>/dev/null) || START_TIME=0
            UPTIME_SECS=$(( $(date +%s) - START_TIME ))
            UPTIME_MINS=$((UPTIME_SECS / 60))
            if [ $UPTIME_MINS -gt 60 ]; then
                UPTIME_HRS=$((UPTIME_MINS / 60))
                printf "  Uptime: %s hours %s minutes\n" "$UPTIME_HRS" $((UPTIME_MINS % 60))
            else
                printf "  Uptime: %s minutes\n" "$UPTIME_MINS"
            fi
        fi
    fi
fi

color "$BLUE"
printf '└──────────────────────────────────────────────────────────────┘\n'
reset
echo ""

# D) Execution Gates
color "$BLUE"
printf '┌─ Execution Gates ──────────────────────────────────────────┐\n'
reset

if [ -f "$CONFIG_FILE" ]; then
    DRY_RUN=$(grep "^QUANTUM_EXECUTION_DRY_RUN=" "$CONFIG_FILE" | cut -d'=' -f2 | cut -d'#' -f1 | tr -d ' ')
    EXEC_ENABLED=$(grep "^QUANTUM_EXECUTION_ENABLED=" "$CONFIG_FILE" | cut -d'=' -f2 | cut -d'#' -f1 | tr -d ' ')

    if [ "$DRY_RUN" = "false" ]; then
        printf "  DRY_RUN Config: %s\n" "$(color "$GREEN")false (orders can execute)$(reset)"
    else
        printf "  DRY_RUN Config: %s\n" "$(color "$YELLOW")true (orders blocked)$(reset)"
    fi

    if [ "$DRY_RUN" = "true" ]; then
        printf "  --live Flag: %s\n" "$(color "$GRAY")NOT SET (add --live to disable DRY_RUN)$(reset)"
    else
        printf "  --live Flag: %s\n" "$(color "$GREEN")SET or overridden$(reset)"
    fi

    if [ "$EXEC_ENABLED" = "true" ]; then
        printf "  Execution Enabled: %s\n" "$(color "$GREEN")true$(reset)"
    else
        printf "  Execution Enabled: %s\n" "$(color "$YELLOW")false$(reset)"
    fi

    # Check kill-switch - if bot is running, emergency stop is NOT effective
    if [ -f "$PLATFORM_ROOT/EMERGENCY_STOP" ]; then
        # Check if bot is actually respecting the emergency stop
        if pgrep -f "quantum_trading_bot.py" > /dev/null 2>&1 || pgrep -f "trading_bot.py" > /dev/null 2>&1; then
            printf "  Kill-Switch: %s\n" "$(color "$YELLOW")⚠️ FILE EXISTS but bot is running (not blocking)$(reset)"
        else
            printf "  Kill-Switch: %s\n" "$(color "$RED")🛑 ACTIVE (all trading blocked)$(reset)"
        fi
    else
        # No emergency stop file - check if bot is running
        if pgrep -f "quantum_trading_bot.py" > /dev/null 2>&1 || pgrep -f "trading_bot.py" > /dev/null 2>&1; then
            printf "  Kill-Switch: %s\n" "$(color "$GREEN")✓ Off (trading enabled)$(reset)"
        else
            printf "  Kill-Switch: %s\n" "$(color "$GRAY")✓ Off (no bot running)$(reset)"
        fi
    fi
fi

# Market hours
CURRENT_HOUR=$(date +%H)
CURRENT_DAY=$(date +%u)
if [ $CURRENT_DAY -lt 6 ] || [ $CURRENT_DAY -ge 7 ]; then
    MARKET_STATUS="WEEKEND"
elif [ $CURRENT_HOUR -ge 14 ] && [ $CURRENT_HOUR -lt 21 ]; then
    MARKET_STATUS="$(color "$GREEN")IN_SESSION$(reset)"
else
    MARKET_STATUS="$(color "$YELLOW")AFTER_HOURS$(reset)"
fi
printf "  Market Hours: %s\n" "$MARKET_STATUS"

color "$BLUE"
printf '└──────────────────────────────────────────────────────────────┘\n'
reset
echo ""

# E) IB Gateway Health
color "$BLUE"
printf '┌─ IB Gateway Health ─────────────────────────────────────────┐\n'
reset

if timeout 5 "$PLATFORM_ROOT/bin/validate_ib_gateway.sh" paper >/dev/null 2>&1; then
    printf "  Gateway: %s\n" "$(color "$GREEN")✓ Healthy$(reset)"
else
    printf "  Gateway: %s\n" "$(color "$YELLOW")⚠ Unhealthy$(reset)"
fi

if ss -ltnp 2>/dev/null | grep -q 4002; then
    printf "  API Port: %s\n" "$(color "$GREEN")✓ Listening (4002)$(reset)"
else
    printf "  API Port: %s\n" "$(color "$RED")✗ Not listening$(reset)"
fi

color "$BLUE"
printf '└──────────────────────────────────────────────────────────────┘\n'
reset
echo ""

# F) Portfolio Snapshot
color "$BLUE"
printf '┌─ Portfolio Snapshot ────────────────────────────────────────┐\n'
reset

SNAPSHOT_JSON=$(timeout 3 "$PLATFORM_ROOT/bin/ib_account_snapshot.py" 2>/dev/null)
SNAPSHOT_EXIT=$?

if [ $SNAPSHOT_EXIT -eq 0 ] && [ -n "$SNAPSHOT_JSON" ]; then
    NET_LIQ=$(echo "$SNAPSHOT_JSON" | grep -o '"NetLiquidation": "[^"]*"' | cut -d'"' -f4)
    CASH=$(echo "$SNAPSHOT_JSON" | grep -o '"TotalCashValue": "[^"]*"' | cut -d'"' -f4)
    POS_COUNT=$(echo "$SNAPSHOT_JSON" | grep -o '"positions_count": [0-9]*' | cut -d' ' -f2)
    ORDERS=$(echo "$SNAPSHOT_JSON" | grep -o '"open_orders": [0-9]*' | cut -d' ' -f2)
    EXEC_COUNT=$(echo "$SNAPSHOT_JSON" | grep -o '"executions_count": [0-9]*' | cut -d' ' -f2)

    printf "  Net Liquidation: %s\n" "$NET_LIQ"
    printf "  Cash: %s\n" "$CASH"
    printf "  Positions: %s\n" "$POS_COUNT"
    printf "  Open Orders: %s\n" "$ORDERS"
    printf "  IB Executions (24h): %s\n" "$EXEC_COUNT"
else
    printf "  %s\n" "$(color "$YELLOW")✗ Snapshot failed (Gateway busy or clientId conflict)$(reset)"
    printf "  %s\n" "$(color "$GRAY")→ Dashboard will retry in 60s$(reset)"
fi

color "$BLUE"
printf '└──────────────────────────────────────────────────────────────┘\n'
reset
echo ""

# G) Learning System Status
color "$BLUE"
printf '┌─ Learning System ─────────────────────────────────────────────┐\n'
reset

LEARNER_STATE="$PLATFORM_ROOT/state/learner_state.json"
if [ -f "$LEARNER_STATE" ]; then
    # Get top 3 signal weights
    TOP_WEIGHTS=$(cat "$LEARNER_STATE" | jq -r '.signal_weights | to_entries | sort_by(.value) | reverse | .[0:3] | .[] | "\(.key): \(.value | .4f)"' 2>/dev/null || echo "No weights")

    # Get learning stats
    TOTAL_TRADES=$(cat "$LEARNER_STATE" | jq -r '.learning_stats.total_trades // .statistics.total_trades // 0' 2>/dev/null)
    LAST_UPDATE=$(cat "$LEARNER_STATE" | jq -r '.last_update // .last_updated // "Never"' 2>/dev/null)

    printf "  Last Update: %s\n" "$LAST_UPDATE"
    printf "  Total Trades Learned: %s\n" "$TOTAL_TRADES"

    if [ -n "$TOP_WEIGHTS" ]; then
        printf "  %s\n" "$(color "$GRAY")Top 3 Signal Weights:$(reset)"
        echo "$TOP_WEIGHTS" | while read -r line; do
            printf "    %s\n" "$line"
        done
    fi
else
    printf "  %s\n" "$(color "$GRAY")No learner state found$(reset)"
fi

color "$BLUE"
printf '└──────────────────────────────────────────────────────────────┘\n'
reset
echo ""

# H) Recent Executions
color "$BLUE"
printf '┌─ Recent Executions ────────────────────────────────────────────┐\n'
reset

BOT_LOG_FILE="/home/davidsanker/logs/trading_bot.log"

# Try to read from bot log first (more current)
if [ -f "$BOT_LOG_FILE" ]; then
    # Get recent trade executions from bot log
    RECENT_TRADES=$(grep -E "✅.*BUY|✅.*SELL" "$BOT_LOG_FILE" 2>/dev/null | tail -3)
    TRADE_COUNT=$(echo "$RECENT_TRADES" | grep -c "✅")

    if [ $TRADE_COUNT -gt 0 ]; then
        printf "  %s\n" "$(color "$GRAY")Last $TRADE_COUNT trade(s) from bot log:$(reset)"
        printf "\n"

        echo "$RECENT_TRADES" | while read -r line; do
            # Extract time from log line
            TRADE_TIME=$(echo "$line" | grep -oE '[0-9]{4}-[0-9]{2}-[0-9]{2} [0-9]{2}:[0-9]{2}:[0-9]{2}' | head -1)
            # Extract action and symbol
            ACTION=$(echo "$line" | grep -oE "BUY|SELL" | head -1)
            SYMBOL=$(echo "$line" | grep -oE "[A-Z]{3,5}:" | head -1 | tr -d ':')
            QUANTITY=$(echo "$line" | grep -oE "[0-9]+ shares" | head -1 | grep -oE "[0-9]+")
            CONFIDENCE=$(echo "$line" | grep -oE "[0-9]+.[0-9]%?" | head -1)

            if [ -n "$TRADE_TIME" ] && [ -n "$ACTION" ] && [ -n "$SYMBOL" ]; then
                if [ "$ACTION" = "BUY" ]; then
                    ACTION_TAG="$(color "$GREEN")$ACTION$(reset)"
                else
                    ACTION_TAG="$(color "$RED")$ACTION$(reset)"
                fi

                printf "  ▸ %s\n" "$TRADE_TIME"
                printf "    %s %s shares" "$ACTION_TAG" "$QUANTITY"
                if [ -n "$CONFIDENCE" ]; then
                    printf " (%s confidence)" "$CONFIDENCE"
                fi
                printf "\n"
            fi
        done
    else
        printf "  %s\n" "$(color "$GRAY")No recent trades found in bot log$(reset)"
    fi
fi

# Fallback to old execution receipts if bot log has no trades
if [ -z "$RECENT_TRADES" ] || [ $TRADE_COUNT -eq 0 ]; then
    if [ -d "$EXECUTION_DIR" ]; then
        LATEST_RECEIPTS=$(find "$EXECUTION_DIR" -name "*.json" -type f 2>/dev/null | sort -r | head -3)
        RECEIPT_COUNT=$(echo "$LATEST_RECEIPTS" | grep -c .)

        if [ $RECEIPT_COUNT -gt 0 ]; then
            printf "  %s\n" "$(color "$GRAY")Last $RECEIPT_COUNT execution receipt(s):$(reset)"
            printf "\n"

            echo "$LATEST_RECEIPTS" | while read -r receipt; do
                if [ -f "$receipt" ]; then
                    RECEIPT_TIME=$(stat -c '%y' "$receipt" 2>/dev/null | cut -d'.' -f1 | sed 's/T/ /' | cut -d' ' -f1-2 | cut -d'.' -f1)
                    ACTION=$(grep -o '"action": "[^"]*"' "$receipt" 2>/dev/null | head -1 | cut -d'"' -f4)
                    SYMBOL=$(grep -o '"symbol": "[^"]*"' "$receipt" 2>/dev/null | head -1 | cut -d'"' -f4)
                    DRY_RUN=$(grep -o '"dry_run": [a-z]*' "$receipt" 2>/dev/null | head -1 | cut -d':' -f2 | tr -d ' ')
                    STATUS=$(grep -o '"status": "[^"]*"' "$receipt" 2>/dev/null | head -1 | cut -d'"' -f4)
                    BLOCKED_REASON=$(grep -o '"reason": "[^"]*"' "$receipt" 2>/dev/null | head -1 | cut -d'"' -f4)

                    if [ "$DRY_RUN" = "false" ]; then
                        MODE_TAG="$(color "$GREEN")LIVE$(reset)"
                    else
                        MODE_TAG="$(color "$GRAY")DRY$(reset)"
                    fi

                    if [ "$STATUS" = "BLOCKED" ]; then
                        STATUS_TAG="$(color "$YELLOW")$STATUS$(reset)"
                    elif [ "$STATUS" = "SUBMITTED" ] || [ "$STATUS" = "FILLED" ]; then
                        STATUS_TAG="$(color "$GREEN")$STATUS$(reset)"
                    else
                        STATUS_TAG="$STATUS"
                    fi

                    printf "  %s\n" "$(color "$GRAY")▸ $RECEIPT_TIME$(reset)"
                    printf "    %s %s [%s] %s\n" \
                        "$(color "$GREEN")$ACTION$(reset)" \
                        "$SYMBOL" \
                        "$MODE_TAG" \
                        "$STATUS_TAG"

                    if [ "$STATUS" = "BLOCKED" ] && [ -n "$BLOCKED_REASON" ]; then
                        printf "    %s\n" "$(color "$GRAY")→ $BLOCKED_REASON$(reset)"
                    fi
                    printf "\n"
                fi
            done
        else
            printf "  %s\n" "$(color "$GRAY")No execution receipts found$(reset)"
        fi
    else
        printf "  %s\n" "$(color "$GRAY")Execution receipts directory not found$(reset)"
    fi
fi

color "$BLUE"
printf '└──────────────────────────────────────────────────────────────┘\n'
reset
echo ""

# I) Host Guard
color "$CYAN"
printf '┌─ HOST GUARD ──────────────────────────────────────────────────┐\n'
reset
CURRENT_HOST=$(hostname)
EXPECTED_HOST="aitradingbot"
if [ "$CURRENT_HOST" = "$EXPECTED_HOST" ]; then
    printf "  Hostname: %s %s\n" "$(color "$GREEN")✓ OK$(reset)" "$CURRENT_HOST"
else
    printf "  Hostname: %s %s (expected: %s)\n" "$(color "$YELLOW")⚠ WARNING$(reset)" "$CURRENT_HOST" "$EXPECTED_HOST"
fi
color "$BLUE"
printf '└──────────────────────────────────────────────────────────────┘\n'
reset
echo ""

# J) Monday Start Engine (PAPER AUTONOMOUS)
color "$BOLD"
printf '╔════════════════════════════════════════════════════════════════╗\n'
printf '║  MONDAY START ENGINE (PAPER AUTONOMOUS)                        ║\n'
printf '╚════════════════════════════════════════════════════════════════╝\n'
reset
echo ""
color "$GRAY"
printf "Time Window: Monday 14:30-15:00 Berlin (13:30-14:00 UTC)\n\n"
printf "Step 1: Kill zombie bot (if applicable)\n"
  printf "  kill 2386182  # or: ps aux | grep quantum_trading_bot\n\n"
printf "Step 2: Start IB Gateway\n"
  printf "  /home/davidsanker/IBC/gatewaystart.sh\n"
  printf "  for i in {1..30}; do ss -ltnp | grep -q \":4002\" && break; sleep 3; done\n\n"
printf "Step 3: Run paper proof\n"
  printf "  source ~/venv/bin/activate\n"
  printf "  python3 %s/bin/assert_paper_account.py\n\n" "$PLATFORM_ROOT"
printf "Step 4: Clear EMERGENCY_STOP\n"
  printf "  %s/bin/clear_emergency_stop.sh\n\n" "$PLATFORM_ROOT"
printf "Step 5: Verify status\n"
  printf "  python3 %s/bin/trading_status.py\n\n" "$PLATFORM_ROOT"
printf "Step 6: Monitor first cycle\n"
  printf "  journalctl --user -u trading-paper-production.service -f\n"
reset
echo ""

# K) Safe Sunday Test (NO ORDERS)
color "$BOLD"
printf '╔════════════════════════════════════════════════════════════════╗\n'
printf '║  SAFE SUNDAY TEST (NO ORDERS - DRY_RUN MODE)                   ║\n'
printf '╚════════════════════════════════════════════════════════════════╝\n'
reset
echo ""
color "$GRAY"
printf "Purpose: Test system for a few hours with gateway running\n\n"
printf "Step 1: Start gateway\n"
  printf "  nohup /home/davidsanker/IBC/gatewaystart.sh >~/IBC/logs/gatewaystart_nohup_\$(date +%Y%m%d_%%H%%M%%S).log 2>&1 &\n"
  printf "  for i in {1..60}; do ss -ltnp | grep -q \":4002\" && echo \"✅ 4002 LISTENING\" && break; sleep 2; done\n\n"
printf "Step 2: Enable DRY_RUN (recommended for testing)\n"
  printf "  cd %s\n" "$PLATFORM_ROOT"
  printf "  cp config/quantum_runtime.env config/quantum_runtime.env.bak_\$(date +%Y%m%d_%%H%%M%%S)\n"
  printf "  sed -i 's/^QUANTUM_EXECUTION_DRY_RUN=false/QUANTUM_EXECUTION_DRY_RUN=true/' config/quantum_runtime.env\n\n"
printf "Step 3: Run paper proof\n"
  printf "  source ~/venv/bin/activate\n"
  printf "  python3 %s/bin/assert_paper_account.py\n\n" "$PLATFORM_ROOT"
printf "Step 4: Clear EMERGENCY_STOP\n"
  printf "  %s/bin/clear_emergency_stop.sh\n\n" "$PLATFORM_ROOT"
printf "Step 5: Start timers\n"
  printf "  systemctl --user start trading-paper-production.timer trading-watchdog.timer\n\n"
printf "Step 6: Monitor\n"
  printf "  watch -n 10 'python3 %s/bin/trading_status.py'\n\n" "$PLATFORM_ROOT"
printf "Cleanup (when done):\n"
  printf "  systemctl --user stop trading-paper-production.timer trading-watchdog.timer\n"
  printf "  sed -i 's/^QUANTUM_EXECUTION_DRY_RUN=true/QUANTUM_EXECUTION_DRY_RUN=false/' config/quantum_runtime.env\n"
  printf "  touch %s/EMERGENCY_STOP\n" "$PLATFORM_ROOT"
reset
echo ""

# H) Quick Commands
printf '%s' "$(color "$GRAY")"
printf "Quick Commands:\n"
printf "  • Validate gateway:  %s\n" "$PLATFORM_ROOT/bin/validate_ib_gateway.sh"
printf "  • Execution logs:     tail -f %s\n" "$PLATFORM_ROOT/logs/quantum-engine/execution.log"
printf "  • View receipts:     ls -lt %s\n" "$EXECUTION_DIR"
printf "  • Emergency stop:    touch %s\n" "$PLATFORM_ROOT/EMERGENCY_STOP"
printf "  • Toggle DRY_RUN:    nano %s\n" "$CONFIG_FILE"
reset
echo ""
