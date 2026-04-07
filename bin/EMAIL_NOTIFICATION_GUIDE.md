# 📧 Quantum AI Trading Bot - Email Notification Guide

## ✅ Enhanced Email Notification System - ACTIVE

Your email notification system has been upgraded and is now fully operational!

---

## 📬 Your Email Schedule

### **Daily Reports**
- **06:00 UTC (07:00 CET)** - Morning daily report with full portfolio analysis
- **12:00 UTC (13:00 CET)** - Mid-day trading summary
- **18:00 UTC (19:00 CET)** - End-of-day trading summary

### **Hourly Updates (Trading Hours)**
- **Every hour 09:00-21:00 UTC** - Status updates during active trading

### **Weekly Reports**
- **Mondays 08:00 UTC** - Comprehensive weekly performance analysis

### **Immediate Alerts**
- **Every 15 minutes** - System health checks
- **Instant** - IB Gateway failure alerts
- **Instant** - Quantum Bot failure alerts

---

## 📧 Email Recipients

- **Primary**: david@sanker.at
- **Secondary**: miriam.sanker@gmail.com

---

## 🎯 What You'll Receive

### 1. **Daily Summary Reports** (3x daily)
- Current portfolio positions
- Unrealized P&L for each holding
- Total account value
- Recent trading activity
- System health status

### 2. **Hourly Status Updates** (Trading Hours)
- Bot operational status
- Active positions overview
- System resource usage
- Trading activity summary

### 3. **Weekly Performance Report** (Mondays)
- Weekly P&L breakdown
- Trading statistics
- Performance metrics
- AI learning improvements
- Next week's focus areas

### 4. **Immediate Alerts** (Real-time)
- System failure notifications
- Trading signal alerts (if configured)
- Error notifications
- Recovery confirmations

---

## 🛠️ Manual Commands

### Send immediate notification:
```bash
./platform/bin/enhanced_email_notifications.sh test
```

### Send daily report now:
```bash
./platform/bin/enhanced_email_notifications.sh daily
```

### Send weekly report now:
```bash
./platform/bin/enhanced_email_notifications.sh weekly
```

### Send custom alert:
```bash
# Trading signal alert
./platform/bin/enhanced_email_notifications.sh alert trading_signal "SPY showing strong buy pattern"

# Error alert
./platform/bin/enhanced_email_notifications.sh alert error "Manual test alert"

# Milestone alert
./platform/bin/enhanced_email_notifications.sh alert milestone "Reached 1000 trades milestone"
```

---

## 📊 Current Holdings Tracked

Your daily reports include these positions:
- **SPY** (S&P 500 ETF)
- **MSFT** (Microsoft)
- **AMZN** (Amazon)
- **AAPL** (Apple)
- **GOOGL** (Google/Alphabet)
- **NVDA** (NVIDIA)
- **TSLA** (Tesla)

---

## 🔍 View Logs

### Email notification log:
```bash
tail -f /home/davidsanker/platform/logs/enhanced_email_notifications.log
```

### Daily reporter log:
```bash
tail -f /home/davidsanker/platform/logs/quantum_daily_reporter.log
```

### Trading bot log:
```bash
tail -f /home/davidsanker/logs/trading_bot.log
```

---

## 📈 HTML Reports

View detailed HTML reports:
```bash
ls -lah /home/davidsanker/platform/reports/
```

Latest report: `quantim_report_YYYYMMDD.html`

---

## ⚙️ Configuration Files

### Main notification script:
`/home/davidsanker/platform/bin/enhanced_email_notifications.sh`

### Daily reporter:
`/home/davidsanker/quantum-trading-bot-new/bin/quantum_daily_reporter.py`

### Crontab:
View current schedule: `crontab -l`
Edit schedule: `crontab -e`

---

## 🚨 System Health Monitoring

The system automatically checks every 15 minutes and will email you if:

1. **IB Gateway stops running**
   - Immediate alert sent
   - Automatic restart attempted
   - Confirmation email when back online

2. **Quantum Trading Bot stops running**
   - Immediate alert sent
   - Diagnostic information included
   - Recovery recommendations provided

---

## 📅 Email Schedule Summary

| Time (UTC) | Time (CET) | Frequency | Report Type |
|------------|------------|-----------|-------------|
| 06:00 | 07:00 | Daily | Morning Summary |
| 09:00 | 10:00 | Hourly | Status Update |
| 10:00 | 11:00 | Hourly | Status Update |
| 11:00 | 12:00 | Hourly | Status Update |
| 12:00 | 13:00 | Daily | Mid-day Summary |
| 13:00 | 14:00 | Hourly | Status Update |
| 14:00 | 15:00 | Hourly | Status Update |
| 15:00 | 16:00 | Hourly | Status Update |
| 16:00 | 17:00 | Hourly | Status Update |
| 17:00 | 18:00 | Hourly | Status Update |
| 18:00 | 19:00 | Daily | End-of-day Summary |
| 19:00 | 20:00 | Hourly | Status Update |
| 20:00 | 21:00 | Hourly | Status Update |
| 21:00 | 22:00 | Hourly | Status Update |
| Mon 08:00 | Mon 09:00 | Weekly | Weekly Performance |

---

## ✅ System Status

**Last Test**: January 26, 2026
**Status**: All notifications working perfectly
**Emails Sent**: 3 test emails successfully delivered

---

## 💡 Tips

1. **Add to Safe Senders**: Add `david@sanker.at` to your email safe senders list
2. **Check Spam Folder**: Initially check spam/junk folder and mark as not spam
3. **Custom Alerts**: Use the alert command for important events
4. **Log Monitoring**: Check logs if you don't receive expected emails

---

## 🔄 Modify Schedule

To change email frequency:

```bash
# Edit crontab
crontab -e

# Example: Change hourly to every 2 hours
# Change: 0 9-21 * * *
# To: 0 9,11,13,15,17,19,21 * * *
```

---

## 📞 Support

If emails stop arriving:
1. Check logs: `tail -f /home/davidsanker/platform/logs/enhanced_email_notifications.log`
2. Verify SMTP: Test with `./platform/bin/enhanced_email_notifications.sh test`
3. Check crontab: `crontab -l`
4. Restart cron: `sudo systemctl restart cron`

---

**Generated**: January 26, 2026
**Version**: Enhanced Email Notification System v2.0
**Status**: ✅ Active and Operational
