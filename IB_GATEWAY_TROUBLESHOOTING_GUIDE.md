# IB Gateway Troubleshooting Guide - Quantim AI Trading Bot
## Platform-Specific Knowledge Base

## 🚨 MOST COMMON ISSUE: SESSION CONFLICTS
### Recognition Pattern:
- Gateway shows "Loading" but no login
- API connections timeout
- Multiple Gateway windows visible
- "Existing session detected" warnings

### 🔧 IMMEDIATE SOLUTION:
```bash
# 1. Kill all IB processes
ps aux | grep java | awk '{print $2}' | xargs sudo kill -9

# 2. Clean temp files
rm -rf /home/davidsanker/IBGateway/*.tmp /home/davidsanker/IBGateway/*.lock

# 3. Start single clean instance
DISPLAY=:1 /home/davidsanker/IBGateway/ibgateway.bin &

# 4. Login via VNC and configure API
# VNC: vnc://localhost:5901
# Username: amakua444, Password: YOUR_IB_PASSWORD
```

## TROUBLESHOOTING FLOWCHART

### Problem: "IB Gateway not working"
1. Check for multiple processes: `ps aux | grep java`
   - If multiple → Apply session conflict fix above
   - If none → Start Gateway manually

2. Check VNC display: `DISPLAY=:1 xwininfo -tree -root | grep Gateway`
   - If multiple windows → Apply session conflict fix
   - If no windows → Check if Gateway process running

3. Check API port: `netstat -tlnp | grep 4002`
   - If listening but no connection → Gateway needs manual login via VNC
   - If not listening → Gateway not started or crashed

### Problem: "Trading bot can't connect"
1. Test API connection manually:
```bash
source venv/bin/activate && timeout 10 python3 -c "
from ib_insync import IB
import asyncio

async def test_connection():
    ib = IB()
    try:
        await ib.connectAsync('127.0.0.1', 4002, clientId=123, timeout=8)
        print('API working!')
        ib.disconnect()
    except Exception as e:
        print(f'API failed: {e}')

asyncio.run(test_connection())
"
```

2. If fails → Apply session conflict fix

## DIAGNOSTIC COMMANDS

### Check System Status:
```bash
# IB Processes
ps aux | grep -E "(java|ibgateway|IBC)" | grep -v grep

# Network Ports
netstat -tlnp | grep -E "(4000|4001|4002|7496)"

# VNC Windows
DISPLAY=:1 xwininfo -tree -root | grep -i "gateway\|login\|ibkr"

# Recent Logs
tail -20 /home/davidsanker/IBC/Logs/ibc-3.20.0_GATEWAY-1037_Friday.txt
```

### Complete Reset:
```bash
# Use built-in fix script
/home/davidsanker/platform/bin/fix_ib_gateway.sh

# Or manual reset
ps aux | grep java | awk '{print $2}' | xargs sudo kill -9
sleep 5
DISPLAY=:1 /home/davidsanker/IBGateway/ibgateway.bin &
```

## STARTUP SEQUENCE

### Fresh Start (after system reboot or issues):
1. Kill any existing processes
2. Clean temp files
3. Start single Gateway instance
4. Login via VNC
5. Configure API settings
6. Test API connection
7. Start trading bot

### Normal Daily Start:
1. Check if Gateway running: `ps aux | grep java`
2. If not running: `DISPLAY=:1 /home/davidsanker/IBGateway/ibgateway.bin &`
3. Start trading bot

## CONFIGURATION VERIFICATION

### IB Gateway Settings (via VNC):
- Configuration → API → Enable ActiveX and Socket Clients
- Socket port: 4002
- Read-Only API: unchecked (for trading)
- Accept incoming connections: yes

### File Configurations:
- `/home/davidsanker/IBGateway/jts.ini` - Gateway settings
- `/home/davidsanker/IBC/config.ini` - IBC automation settings

## CRITICAL SCRIPTS

### Main Fix Script:
`/home/davidsanker/platform/bin/fix_ib_gateway.sh`
- Comprehensive diagnosis and repair
- Tests API connectivity
- Handles restart procedures

### Manual Gateway Start:
`/home/davidsanker/IBGateway/ibgateway.bin`
- Use when automation fails
- Requires DISPLAY=:1 for VNC

### Trading Bot:
```bash
cd /home/davidsanker/investor_bot_migration_20251017_163810/investor
source ~/venv/bin/activate
python quantum_enhanced_trading_bot.py
```

## LOG LOCATIONS
- IBC Logs: `/home/davidsanker/IBC/Logs/`
- Gateway Logs: Check within Gateway application
- Fix Script Logs: `/home/davidsanker/platform/logs/ib-gateway/`
- Trading Bot Logs: `/home/davidsanker/platform/logs/trading-bot/`

## CONTACT SUPPORT
If issues persist after applying session conflict fix:
1. Check for VM/network issues
2. Verify IB credentials are valid
3. Consider contacting IBKR support
4. Check for system resource issues

## REMEMBER: 90% of IB Gateway issues on this system are session conflicts!