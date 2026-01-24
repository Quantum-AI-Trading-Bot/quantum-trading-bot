#!/usr/bin/env python3
"""
Economic Calendar Monitor and Alert System
Monitors key economic events and provides trading recommendations
"""

import asyncio
import json
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional
from dataclasses import dataclass
import logging

sys.path.append('/home/davidsanker/platform')

@dataclass
class EconomicEvent:
    """Economic event with trading implications"""
    name: str
    date: datetime
    impact: str  # 'high', 'medium', 'low'
    expected_value: Optional[float]
    previous_value: Optional[float]
    description: str
    trading_implications: List[str]
    affected_markets: List[str]

class EconomicCalendarMonitor:
    """Monitors economic calendar and provides trading recommendations"""

    def __init__(self):
        self.events = []
        self.logger = logging.getLogger(__name__)
        self.impact_factors = {
            'high': 2.0,
            'medium': 1.3,
            'low': 1.0
        }

    def generate_economic_calendar(self, fred_data: Dict) -> List[EconomicEvent]:
        """Generate economic calendar from FRED data patterns"""
        current_time = datetime.now(timezone.utc)
        events = []

        # GDP events
        gdp_data = fred_data.get('fred', {}).get('GDP', {})
        if gdp_data:
            latest_date = gdp_data.get('latest_value', {}).get('date')
            if latest_date:
                last_gdp = datetime.fromisoformat(latest_date.replace('Z', '+00:00'))
                next_gdp = self._estimate_next_release(last_gdp, 'quarterly')

                events.append(EconomicEvent(
                    name="GDP Release",
                    date=next_gdp,
                    impact="high",
                    expected_value=None,
                    previous_value=gdp_data.get('latest_value', {}).get('value'),
                    description="US Gross Domestic Product - key economic growth indicator",
                    trading_implications=[
                        "GDP beat expectation → bullish for equities",
                        "GDP miss expectation → bearish for equities",
                        "High impact on market indices and forex"
                    ],
                    affected_markets=["SPY", "QQQ", "IWM", "USDCAD", "USDJPY"]
                ))

        # Unemployment Rate events
        unemployment_data = fred_data.get('fred', {}).get('UNRATE', {})
        if unemployment_data:
            latest_date = unemployment_data.get('latest_value', {}).get('date')
            if latest_date:
                last_unemp = datetime.fromisoformat(latest_date.replace('Z', '+00:00'))
                next_unemp = self._estimate_next_release(last_unemp, 'monthly')

                events.append(EconomicEvent(
                    name="Unemployment Rate",
                    date=next_unemp,
                    impact="high",
                    expected_value=None,
                    previous_value=unemployment_data.get('latest_value', {}).get('value'),
                    description="US Unemployment Rate - key labor market indicator",
                    trading_implications=[
                        "Rate decreasing → bullish for equities",
                        "Rate increasing → bearish for equities",
                        "High impact on consumer discretionary stocks"
                    ],
                    affected_markets=["SPY", "QQQ", "XLY", "DIA"]
                ))

        # Federal Funds Rate events (FOMC meetings)
        fed_rate_data = fred_data.get('fred', {}).get('DFF', {})
        if fed_rate_data:
            # FOMC meetings typically every 6 weeks on Wednesdays
            next_fomc = self._estimate_next_fomc_meeting()

            events.append(EconomicEvent(
                name="FOMC Interest Rate Decision",
                date=next_fomc,
                impact="high",
                expected_value=None,
                previous_value=fed_rate_data.get('latest_value', {}).get('value'),
                description="Federal Reserve FOMC Meeting - interest rate policy decision",
                trading_implications=[
                    "Rate hike → negative for growth stocks, positive for financials",
                    "Rate cut → positive for growth stocks, negative for financials",
                    "Maximum market volatility expected"
                ],
                affected_markets=["SPY", "QQQ", "XLF", "KBE", "GLD", "TLT"]
            ))

        # CPI Inflation events
        cpi_data = fred_data.get('fred', {}).get('CPIAUCSL', {})
        if cpi_data:
            latest_date = cpi_data.get('latest_value', {}).get('date')
            if latest_date:
                last_cpi = datetime.fromisoformat(latest_date.replace('Z', '+00:00'))
                next_cpi = self._estimate_next_release(last_cpi, 'monthly')

                events.append(EconomicEvent(
                    name="Consumer Price Index (CPI)",
                    date=next_cpi,
                    impact="high",
                    expected_value=None,
                    previous_value=cpi_data.get('latest_value', {}).get('value'),
                    description="Consumer Price Index - key inflation indicator",
                    trading_implications=[
                        "Higher CPI → bearish (rate hike expectations)",
                        "Lower CPI → bullish (rate cut expectations)",
                        "High impact on real estate and utilities"
                    ],
                    affected_markets=["SPY", "QQQ", "XLRE", "XLU", "GLD", "TIP"]
                ))

        # Treasury Yield events
        treasury_data = fred_data.get('fred', {}).get('DGS10', {})
        if treasury_data:
            latest_date = treasury_data.get('latest_value', {}).get('date')
            if latest_date:
                last_treasury = datetime.fromisoformat(latest_date.replace('Z', '+00:00'))
                next_treasury = last_treasury + timedelta(days=1)  # Daily updates

                events.append(EconomicEvent(
                    name="10-Year Treasury Yield",
                    date=next_treasury,
                    impact="medium",
                    expected_value=None,
                    previous_value=treasury_data.get('latest_value', {}).get('value'),
                    description="10-Year Treasury Note Yield - benchmark interest rate",
                    trading_implications=[
                        "Yield rising → bearish for bonds, mixed for equities",
                        "Yield falling → bullish for bonds, positive for equities",
                        "Important for tech stock valuation"
                    ],
                    affected_markets=["TLT", "IEF", "QQQ", "SPY", "XLK"]
                ))

        return sorted(events, key=lambda x: x.date)

    def _estimate_next_release(self, last_release: datetime, frequency: str) -> datetime:
        """Estimate next release date based on frequency"""
        if frequency == 'quarterly':
            # Quarterly releases (every 3 months)
            next_date = last_release + timedelta(days=90)
        elif frequency == 'monthly':
            # Monthly releases
            next_date = last_release + timedelta(days=30)
        else:  # daily
            next_date = last_release + timedelta(days=1)

        return next_date

    def _estimate_next_fomc_meeting(self) -> datetime:
        """Estimate next FOMC meeting date (simplified)"""
        current_time = datetime.now(timezone.utc)

        # FOMC meets every 6 weeks on Wednesday
        # This is a simplified estimation
        weeks_since_last_meeting = (current_time.day % 6)
        next_fomc = current_time + timedelta(days=42 - (weeks_since_last_meeting * 7))

        # Ensure it's on a Wednesday
        while next_fomc.weekday() != 2:  # Wednesday is weekday 2
            next_fomc += timedelta(days=1)

        return next_fomc

    def get_upcoming_events(self, days_ahead: int = 7) -> List[EconomicEvent]:
        """Get upcoming economic events"""
        current_time = datetime.now(timezone.utc)
        cutoff_date = current_time + timedelta(days=days_ahead)

        upcoming = []
        for event in self.events:
            if current_time <= event.date <= cutoff_date:
                upcoming.append(event)

        return sorted(upcoming, key=lambda x: x.date)

    def get_trading_recommendations(self, events: List[EconomicEvent]) -> Dict[str, List[str]]:
        """Generate trading recommendations based on upcoming events"""
        recommendations = {
            'before_events': [],
            'during_events': [],
            'general_strategies': []
        }

        current_time = datetime.now(timezone.utc)

        for event in events:
            hours_until = (event.date - current_time).total_seconds() / 3600

            if hours_until < 24:  # Within 24 hours
                recommendations['during_events'].extend([
                    f"🚨 {event.name} in {hours_until:.0f} hours",
                    "⚠️ Reduce position sizes before event",
                    "🔄 Consider tightening stop losses",
                    f"📊 Monitor {', '.join(event.affected_markets[:3])}"
                ])
            elif hours_until < 72:  # Within 3 days
                recommendations['before_events'].extend([
                    f"⏰ {event.name} in {hours_until/24:.1f} days",
                    f"📈 {event.impact} impact expected",
                    f"🎯 Focus on: {', '.join(event.affected_markets[:2])}"
                ])

        # General strategies
        if any(e.impact == 'high' for e in events):
            recommendations['general_strategies'].extend([
                "🛡️ Increase cash allocation before high-impact events",
                "📊 Consider volatility ETFs (VXX, UVXY) as hedge",
                "💰 Have option positions ready for volatility spikes"
            ])

        return recommendations

class AlertNotificationSystem:
    """Alert notification system for economic events"""

    def __init__(self):
        self.alert_history = []
        self.logger = logging.getLogger(__name__)

    def check_market_open_close_alerts(self) -> List[Dict]:
        """Check for market open/close alerts"""
        alerts = []
        current_time = datetime.now(timezone.utc)

        # Convert to EST (UTC-5 or UTC-4 for daylight saving)
        est_offset = 5 if self._is_standard_time() else 4
        est_time = current_time - timedelta(hours=est_offset)

        # Market open alert (9:30 AM EST)
        if est_time.hour == 9 and est_time.minute == 30 and est_time.weekday() < 5:
            alerts.append({
                'type': 'market_open',
                'message': '📈 US Market Opening - Increased volume and volatility expected',
                'action': 'Review positions, consider trading breakouts',
                'impact': 'medium'
            })

        # Market close alert (4:00 PM EST)
        if est_time.hour == 16 and est_time.minute == 0 and est_time.weekday() < 5:
            alerts.append({
                'type': 'market_close',
                'message': '📉 US Market Closing - Time to review and adjust positions',
                'action': 'Consider taking profits, tighten stops for overnight',
                'impact': 'low'
            })

        return alerts

    def check_fed_schedule_alerts(self) -> List[Dict]:
        """Check for Federal Reserve schedule alerts"""
        alerts = []
        current_time = datetime.now(timezone.utc)

        # Check if it's FOMC week (simplified)
        if current_time.day <= 7 and current_time.weekday() == 2:  # First week of month, Wednesday
            alerts.append({
                'type': 'fomc_week',
                'message': '🏛️ FOMC Meeting Week - Expect increased market volatility',
                'action': 'Monitor economic indicators, reduce speculative positions',
                'impact': 'high',
                'affected_markets': ['SPY', 'QQQ', 'XLF', 'TLT', 'GLD']
            })

        # Check for Fed Beige Book release (typically 2 weeks before FOMC)
        if current_time.day >= 7 and current_time.day <= 14 and current_time.weekday() == 3:  # Second week, Thursday
            alerts.append({
                'type': 'beige_book',
                'message': '📖 Fed Beige Book Release - Economic assessment data',
                'action': 'Watch for regional economic trends, adjust sector allocations',
                'impact': 'medium'
            })

        return alerts

    def _is_standard_time(self) -> bool:
        """Check if currently in standard time (winter months)"""
        month = datetime.now().month
        return month in [11, 12, 1, 2, 3]  # Nov-Mar is standard time

    def generate_alert_summary(self, alerts: List[Dict]) -> str:
        """Generate human-readable alert summary"""
        if not alerts:
            return "✅ No active alerts - normal market conditions expected"

        summary_lines = ["🚨 TRADING ALERTS ACTIVE:"]

        high_impact_alerts = [a for a in alerts if a.get('impact') == 'high']
        medium_impact_alerts = [a for a in alerts if a.get('impact') == 'medium']

        if high_impact_alerts:
            summary_lines.append("\n🔴 HIGH IMPACT ALERTS:")
            for alert in high_impact_alerts:
                summary_lines.append(f"  • {alert.get('message', 'High impact alert')}")
                if 'action' in alert:
                    summary_lines.append(f"    Action: {alert['action']}")

        if medium_impact_alerts:
            summary_lines.append("\n🟡 MEDIUM IMPACT ALERTS:")
            for alert in medium_impact_alerts:
                summary_lines.append(f"  • {alert.get('message', 'Medium impact alert')}")
                if 'action' in alert:
                    summary_lines.append(f"    Action: {alert['action']}")

        summary_lines.append("\n💡 TRADING RECOMMENDATIONS:")
        summary_lines.append("  • Review position sizes before trading")
        summary_lines.append("  • Tighten stop losses during high volatility")
        summary_lines.append("  • Monitor affected markets closely")
        summary_lines.append("  • Consider hedging with volatility ETFs")

        return "\n".join(summary_lines)

# Main monitoring system
class TradingAlertMonitor:
    """Main trading alert and economic calendar monitoring system"""

    def __init__(self):
        self.calendar_monitor = EconomicCalendarMonitor()
        self.notification_system = AlertNotificationSystem()
        self.logger = logging.getLogger(__name__)

    async def update_calendar(self, fred_data: Dict):
        """Update economic calendar with latest data"""
        try:
            self.calendar_monitor.events = self.calendar_monitor.generate_economic_calendar(fred_data)
            self.logger.info(f"Updated economic calendar with {len(self.calendar_monitor.events)} events")
        except Exception as e:
            self.logger.error(f"Error updating calendar: {e}")

    async def get_comprehensive_alerts(self, fred_data: Dict = None) -> Dict:
        """Get comprehensive alert information"""
        # Update calendar if data provided
        if fred_data:
            await self.update_calendar(fred_data)

        # Get upcoming economic events
        upcoming_events = self.calendar_monitor.get_upcoming_events(days_ahead=7)

        # Get trading recommendations
        recommendations = self.calendar_monitor.get_trading_recommendations(upcoming_events)

        # Get system alerts
        market_alerts = self.notification_system.check_market_open_close_alerts()
        fed_alerts = self.notification_system.check_fed_schedule_alerts()
        all_system_alerts = market_alerts + fed_alerts

        # Combine all alerts
        all_alerts = all_system_alerts
        for event in upcoming_events:
            hours_until = (event.date - datetime.now(timezone.utc)).total_seconds() / 3600
            if hours_until < 48:  # Only show alerts for events within 48 hours
                all_alerts.append({
                    'type': 'economic_event',
                    'name': event.name,
                    'date': event.date,
                    'impact': event.impact,
                    'hours_until': hours_until,
                    'message': f"📊 {event.name} in {hours_until:.0f} hours ({event.impact} impact)",
                    'affected_markets': event.affected_markets
                })

        return {
            'upcoming_events': upcoming_events[:5],  # Top 5 upcoming events
            'trading_recommendations': recommendations,
            'active_alerts': all_alerts[:10],  # Top 10 alerts
            'alert_summary': self.notification_system.generate_alert_summary(all_alerts)
        }

# Example usage
async def main():
    """Example of how to use the economic calendar monitor"""
    print("📅 ECONOMIC CALENDAR & ALERT MONITOR")
    print("=" * 50)

    # Initialize the monitor
    monitor = TradingAlertMonitor()

    # Get sample FRED data (in real usage, this would come from your data source)
    sample_fred_data = {
        'fred': {
            'GDP': {
                'latest_value': {'value': 30485.73, 'date': '2025-04-01'},
                'trend': 'up'
            },
            'UNRATE': {
                'latest_value': {'value': 4.3, 'date': '2025-08-01'},
                'trend': 'stable'
            },
            'DFF': {
                'latest_value': {'value': 3.87, 'date': '2025-11-06'},
                'trend': 'down'
            }
        }
    }

    # Get comprehensive alerts
    alerts = await monitor.get_comprehensive_alerts(sample_fred_data)

    # Display results
    print("\n📅 UPCOMING ECONOMIC EVENTS:")
    for event in alerts['upcoming_events']:
        days_until = (event.date - datetime.now(timezone.utc)).days
        print(f"  📊 {event.name} - {days_until} days away ({event.impact} impact)")

    print("\n🚨 ACTIVE ALERTS:")
    if alerts['active_alerts']:
        for alert in alerts['active_alerts'][:5]:  # Show top 5
            print(f"  {alert.get('message', 'Alert')}")
    else:
        print("  ✅ No active alerts")

    print(f"\n{alerts['alert_summary']}")

    print("\n📈 TRADING RECOMMENDATIONS:")
    for rec_type, recommendations in alerts['trading_recommendations'].items():
        if recommendations:
            print(f"  {rec_type.title()}:")
            for rec in recommendations[:3]:  # Show top 3
                print(f"    • {rec}")

    print("\n✅ Economic Calendar Monitor Ready!")
    print("   • Automatic event detection")
    print("   • Real-time alert generation")
    print("   • Trading impact analysis")
    print("   • Risk management recommendations")

if __name__ == "__main__":
    asyncio.run(main())