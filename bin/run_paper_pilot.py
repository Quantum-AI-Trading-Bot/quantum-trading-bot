#!/usr/bin/env python3
"""
Paper Trading Pilot Execution
Runs controlled pilot with real paper orders via IBKR
"""

import sys
import os
import json
import time
from pathlib import Path
from datetime import datetime, timedelta
import logging

# Add platform to path
platform_path = Path(__file__).parent.parent
sys.path.insert(0, str(platform_path))

from bin.pilot_guardrails import PilotGuardrails

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)s | %(message)s',
    handlers=[
        logging.FileHandler('/home/davidsanker/logs/paper_pilot_20260123_140951/03_pilot_run_log.txt'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Pilot Configuration
CYCLE_INTERVAL_SEC = 300  # 5 minutes
MAX_PILOT_DURATION_SEC = 7200  # 2 hours
PILOT_END_UTC = "2026-01-23T16:13:15"
PILOT_SYMBOL = 'SPY'

class PaperPilotExecutor:
    """Execute paper trading pilot with comprehensive safety."""

    def __init__(self):
        self.guardrails = PilotGuardrails()
        self.start_time = datetime.utcnow()
        self.end_time = datetime.fromisoformat(PILOT_END_UTC)
        self.cycles_completed = 0
        self.cycles_blocked = 0
        self.orders_attempted = 0
        self.orders_executed = 0

        # Create receipts directory
        self.receipts_dir = Path('/home/davidsanker/platform/execution_receipts')
        self.receipts_dir.mkdir(parents=True, exist_ok=True)

        logger.info("=" * 80)
        logger.info("PAPER TRADING PILOT EXECUTION")
        logger.info("=" * 80)
        logger.info(f"Start Time: {self.start_time.isoformat()}")
        logger.info(f"End Time: {self.end_time.isoformat()}")
        logger.info(f"Max Duration: {MAX_PILOT_DURATION_SEC}s ({MAX_PILOT_DURATION_SEC/60:.1f} min)")
        logger.info(f"Cycle Interval: {CYCLE_INTERVAL_SEC}s ({CYCLE_INTERVAL_SEC/60:.1f} min)")
        logger.info(f"Symbol: {PILOT_SYMBOL}")
        logger.info("=" * 80)
        logger.info("")

    def _should_continue_pilot(self) -> bool:
        """Check if pilot should continue."""
        now = datetime.utcnow()

        # Check 1: Time expired
        if now > self.end_time:
            logger.info("⏰ Pilot end time reached")
            return False

        # Check 2: Max duration reached
        elapsed = (now - self.start_time).total_seconds()
        if elapsed >= MAX_PILOT_DURATION_SEC:
            logger.info(f"⏰ Max pilot duration reached ({elapsed:.0f}s)")
            return False

        # Check 3: Kill switch
        kill_switch = Path('/home/davidsanker/platform/EMERGENCY_STOP')
        if kill_switch.exists():
            logger.error("🛑 EMERGENCY STOP file detected - HALTING PILOT")
            return False

        return True

    def _run_single_cycle(self) -> dict:
        """
        Run a single trading cycle.

        Returns:
            dict with cycle results
        """
        cycle_start = datetime.utcnow()
        cycle_id = cycle_start.strftime('%Y%m%d_%H%M%S')
        logger.info("")
        logger.info("=" * 80)
        logger.info(f"CYCLE #{self.cycles_completed + 1} - {cycle_start.isoformat()}")
        logger.info("=" * 80)

        result = {
            'cycle_id': cycle_id,
            'timestamp': cycle_start.isoformat(),
            'symbol': PILOT_SYMBOL,
            'guardrails_passed': False,
            'action': None,
            'confidence': None,
            'order_attempted': False,
            'order_status': None
        }

        # STEP 1: Fetch market data
        logger.info("\n[STEP 1] Fetching market data...")
        try:
            import yfinance as yf

            # Fetch current SPY data
            ticker = yf.Ticker(PILOT_SYMBOL)
            data = ticker.history(period="1d", interval="1m")

            if data.empty:
                logger.warning("No market data available")
                return result

            latest = data.iloc[-1]
            logger.info(f"  {PILOT_SYMBOL} Price: ${latest['Close']:.2f}")
            logger.info(f"  Volume: {latest['Volume']:,}")

        except Exception as e:
            logger.error(f"  Error fetching market data: {e}")
            return result

        # STEP 2: Generate signal
        logger.info("\n[STEP 2] Generating trading signal...")
        try:
            # Load Phase 1 MA crossover strategy
            from models.phase1.phase1_ma_crossover_signal import Phase1MACrossoverSignal
            from models.registry import get_signal_model

            # Get model from registry
            model = get_signal_model('phase1_ma_crossover')
            if not model:
                logger.error("Could not load signal model")
                return result

            # Generate features (simplified for pilot)
            features = {
                'symbol': PILOT_SYMBOL,
                'timestamp': cycle_start.isoformat(),
                'close': latest['Close'],
                'volume': latest['Volume'],
                'sma_10': data['Close'].rolling(10).mean().iloc[-1],
                'sma_50': data['Close'].rolling(50).mean().iloc[-1]
            }

            signal_result = model.generate_signal(features)
            action = signal_result.action
            confidence = signal_result.confidence

            logger.info(f"  Signal: {action}")
            logger.info(f"  Confidence: {confidence:.3f}")
            logger.info(f"  Reason: {signal_result.reason}")

            result['action'] = action
            result['confidence'] = confidence

        except Exception as e:
            logger.error(f"  Error generating signal: {e}")
            return result

        # STEP 3: Check guardrails
        logger.info("\n[STEP 3] Checking pilot guardrails...")

        # Calculate target value (0.5% of portfolio)
        target_value_pct = 0.005

        allowed, reason = self.guardrails.check_all_guards(
            symbol=PILOT_SYMBOL,
            action=action,
            target_value_pct=target_value_pct
        )

        result['guardrails_passed'] = allowed

        if not allowed:
            logger.warning(f"  ❌ GUARDRAILS BLOCKED: {reason}")
            self.cycles_blocked += 1
            return result

        logger.info("  ✅ GUARDRAILS PASSED")

        # STEP 4: Only proceed if BUY/SELL with sufficient confidence
        if action == 'HOLD' or confidence < 0.65:
            logger.info(f"\n[STEP 4] No action needed (action={action}, confidence={confidence:.3f})")
            return result

        # STEP 5: Attempt order placement
        logger.info(f"\n[STEP 5] Attempting order placement...")
        logger.info(f"  Action: {action}")
        logger.info(f"  Symbol: {PILOT_SYMBOL}")
        logger.info(f"  Target Value: {target_value_pct:.1%}")

        self.orders_attempted += 1
        result['order_attempted'] = True

        try:
            # Connect to IBKR paper trading
            from ib_insync import IB, Stock, MarketOrder

            ib = IB()
            ib.connect('127.0.0.1', 4002, clientId=501, timeout=10)

            # Create contract
            contract = Stock(PILOT_SYMBOL, 'SMART', 'USD')

            # Get current price
            ticker = ib.reqMktData(contract, '', False, False)
            ib.sleep(1)

            if ticker.marketPrice() == 0:
                logger.warning("  Could not get market price")
                ib.disconnect()
                return result

            price = ticker.marketPrice()
            logger.info(f"  Market Price: ${price:.2f}")

            # Calculate quantity (0.5% of $100K portfolio = $500)
            target_value = 100000 * target_value_pct
            quantity = int(target_value / price)

            if quantity < 1:
                logger.warning(f"  Calculated quantity < 1 ({quantity})")
                ib.disconnect()
                return result

            logger.info(f"  Quantity: {quantity} shares")

            # Create order
            if action == 'BUY':
                order = MarketOrder('BUY', quantity)
            else:  # SELL
                order = MarketOrder('SELL', quantity)

            order.orderType = 'MKT'
            order.tif = 'DAY'

            # Place order
            trade = ib.placeOrder(contract, order)
            logger.info(f"  ✅ Order placed: {action} {quantity} {PILOT_SYMBOL} @ MKT")

            # Wait for submission
            ib.sleep(2)

            if trade.orderStatus.status == 'Submitted':
                logger.info(f"  ✅ Order submitted (OrderId: {trade.order.orderId})")
                result['order_status'] = 'SUBMITTED'
                self.orders_executed += 1

                # Create execution receipt
                receipt = {
                    'cycle_id': cycle_id,
                    'timestamp': cycle_start.isoformat(),
                    'symbol': PILOT_SYMBOL,
                    'action': action,
                    'quantity': quantity,
                    'price': price,
                    'order_id': trade.order.orderId,
                    'status': 'SUBMITTED',
                    'confidence': confidence,
                    'target_value_pct': target_value_pct,
                    'guardrails': 'PASSED'
                }

                receipt_file = self.receipts_dir / f"receipt_{cycle_id}.json"
                with open(receipt_file, 'w') as f:
                    json.dump(receipt, f, indent=2)
                logger.info(f"  📄 Receipt written: {receipt_file}")

            ib.disconnect()

        except Exception as e:
            logger.error(f"  ❌ Order placement failed: {e}")
            result['order_status'] = 'FAILED'
            return result

        self.cycles_completed += 1

        cycle_end = datetime.utcnow()
        cycle_duration = (cycle_end - cycle_start).total_seconds()
        logger.info(f"\n  ⏱️ Cycle duration: {cycle_duration:.1f}s")

        return result

    def run_pilot(self):
        """Run the complete pilot."""
        logger.info("Starting pilot execution loop...")
        logger.info("")

        cycle_num = 0

        while self._should_continue_pilot():
            cycle_num += 1

            try:
                result = self._run_single_cycle()

                # Log cycle summary
                logger.info("")
                logger.info("=" * 80)
                logger.info("CYCLE SUMMARY")
                logger.info("=" * 80)
                logger.info(f"Total Cycles: {cycle_num}")
                logger.info(f"Completed: {self.cycles_completed}")
                logger.info(f"Blocked: {self.cycles_blocked}")
                logger.info(f"Orders Attempted: {self.orders_attempted}")
                logger.info(f"Orders Executed: {self.orders_executed}")
                logger.info("=" * 80)

            except KeyboardInterrupt:
                logger.info("\n⚠️ Pilot interrupted by user")
                break
            except Exception as e:
                logger.error(f"\n❌ Cycle error: {e}")
                import traceback
                traceback.print_exc()

            # Wait for next cycle
            if self._should_continue_pilot():
                logger.info(f"\n⏳ Waiting {CYCLE_INTERVAL_SEC}s for next cycle...")
                logger.info("")
                time.sleep(CYCLE_INTERVAL_SEC)

        # Pilot complete
        self._write_final_report()

    def _write_final_report(self):
        """Write final pilot report."""
        end_time = datetime.utcnow()
        duration = (end_time - self.start_time).total_seconds()

        logger.info("")
        logger.info("=" * 80)
        logger.info("PILOT COMPLETE - FINAL REPORT")
        logger.info("=" * 80)
        logger.info(f"Start Time: {self.start_time.isoformat()}")
        logger.info(f"End Time: {end_time.isoformat()}")
        logger.info(f"Duration: {duration:.1f}s ({duration/60:.1f} min)")
        logger.info("")
        logger.info("Cycle Statistics:")
        logger.info(f"  Total Cycles Run: {self.cycles_completed + self.cycles_blocked}")
        logger.info(f"  Successful Cycles: {self.cycles_completed}")
        logger.info(f"  Blocked Cycles: {self.cycles_blocked}")
        logger.info("")
        logger.info("Order Statistics:")
        logger.info(f"  Orders Attempted: {self.orders_attempted}")
        logger.info(f"  Orders Executed: {self.orders_executed}")
        logger.info(f"  Success Rate: {self.orders_executed/max(self.orders_attempted,1)*100:.1f}%")
        logger.info("")
        logger.info("Safety Status:")
        logger.info(f"  Kill Switch: {'ACTIVE' if Path('/home/davidsanker/platform/EMERGENCY_STOP').exists() else 'NOT ACTIVE'}")
        logger.info("=" * 80)

        # Write report file
        report_file = Path('/home/davidsanker/logs/paper_pilot_20260123_140951/04_pilot_final_report.txt')
        with open(report_file, 'w') as f:
            f.write("PAPER TRADING PILOT - FINAL REPORT\n")
            f.write("=" * 80 + "\n\n")
            f.write(f"Start Time: {self.start_time.isoformat()}\n")
            f.write(f"End Time: {end_time.isoformat()}\n")
            f.write(f"Duration: {duration:.1f}s ({duration/60:.1f} min)\n\n")
            f.write("Cycle Statistics:\n")
            f.write(f"  Total Cycles Run: {self.cycles_completed + self.cycles_blocked}\n")
            f.write(f"  Successful Cycles: {self.cycles_completed}\n")
            f.write(f"  Blocked Cycles: {self.cycles_blocked}\n\n")
            f.write("Order Statistics:\n")
            f.write(f"  Orders Attempted: {self.orders_attempted}\n")
            f.write(f"  Orders Executed: {self.orders_executed}\n")
            f.write(f"  Success Rate: {self.orders_executed/max(self.orders_attempted,1)*100:.1f}%\n\n")
            f.write("Safety Status:\n")
            f.write(f"  Kill Switch: {'ACTIVE' if Path('/home/davidsanker/platform/EMERGENCY_STOP').exists() else 'NOT ACTIVE'}\n")
            f.write("\n" + "=" * 80 + "\n")

        logger.info(f"\n📄 Final report written: {report_file}")


def main():
    """Main entry point."""
    executor = PaperPilotExecutor()
    executor.run_pilot()
    return 0


if __name__ == "__main__":
    sys.exit(main())
