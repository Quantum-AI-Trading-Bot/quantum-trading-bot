#!/usr/bin/env python3
"""
Phase 4B: Timeboxed Pilot Execution
Runs multiple trading cycles with full safety guardrails
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

# Pilot Configuration
CYCLE_INTERVAL_SEC = 300  # 5 minutes
MAX_CYCLES = 5  # Run max 5 cycles (25 minutes total)
PILOT_END_UTC = "2026-01-23T20:30:00"
PILOT_SYMBOL = 'SPY'

# Setup logging
SESSION_DIR = Path('/home/davidsanker/logs/paper_pilot_phase4B_20260123_182012')
LOG_FILE = SESSION_DIR / '01_pilot_execution_log.txt'

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)s | %(message)s',
    handlers=[
        logging.FileHandler(LOG_FILE),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class Phase4BPilot:
    """Execute Phase 4B timeboxed pilot."""

    def __init__(self):
        self.guardrails = PilotGuardrails()
        self.start_time = datetime.utcnow()
        self.end_time = datetime.fromisoformat(PILOT_END_UTC)
        self.cycle_count = 0
        self.orders_attempted = 0
        self.orders_executed = 0
        self.cycles_blocked = 0

        # Track receipts
        self.receipts_dir = Path('/home/davidsanker/platform/execution_receipts')
        self.initial_receipt_count = len(list(self.receipts_dir.glob('*.json'))) if self.receipts_dir.exists() else 0

        logger.info("=" * 80)
        logger.info("PHASE 4B: TIMEBOXED PILOT EXECUTION")
        logger.info("=" * 80)
        logger.info(f"Start Time: {self.start_time.isoformat()}")
        logger.info(f"End Time: {self.end_time.isoformat()}")
        logger.info(f"Max Cycles: {MAX_CYCLES}")
        logger.info(f"Cycle Interval: {CYCLE_INTERVAL_SEC}s ({CYCLE_INTERVAL_SEC/60:.1f} min)")
        logger.info(f"Symbol: {PILOT_SYMBOL}")
        logger.info(f"Initial Receipt Count: {self.initial_receipt_count}")
        logger.info("=" * 80)
        logger.info("")

    def _should_continue(self) -> bool:
        """Check if pilot should continue."""
        # Check 1: Max cycles reached
        if self.cycle_count >= MAX_CYCLES:
            logger.info(f"⏰ Max cycles reached ({MAX_CYCLES})")
            return False

        # Check 2: Pilot timeout
        if datetime.utcnow() > self.end_time:
            logger.info("⏰ Pilot end time reached")
            return False

        # Check 3: Kill switch
        kill_switch = Path('/home/davidsanker/platform/EMERGENCY_STOP')
        if kill_switch.exists():
            logger.error("🛑 EMERGENCY STOP file detected - HALTING PILOT")
            return False

        return True

    def _run_single_cycle(self) -> dict:
        """Run a single trading cycle."""
        cycle_start = datetime.utcnow()
        cycle_id = cycle_start.strftime('%Y%m%d_%H%M%S')
        self.cycle_count += 1

        logger.info("")
        logger.info("=" * 80)
        logger.info(f"CYCLE #{self.cycle_count} - {cycle_start.isoformat()}")
        logger.info("=" * 80)

        result = {
            'cycle': self.cycle_count,
            'cycle_id': cycle_id,
            'timestamp': cycle_start.isoformat(),
            'symbol': PILOT_SYMBOL,
            'guardrails_passed': False,
            'action': None,
            'confidence': None,
            'order_attempted': False,
            'order_status': None
        }

        # STEP 1: Check guardrails
        logger.info("\n[STEP 1] Checking pilot guardrails...")
        allowed, reason = self.guardrails.check_all_guards(
            symbol=PILOT_SYMBOL,
            action='BUY',  # Will check actual action later
            target_value_pct=0.005
        )

        result['guardrails_passed'] = allowed

        if not allowed:
            logger.warning(f"  ❌ GUARDRAILS BLOCKED: {reason}")
            self.cycles_blocked += 1
            return result

        logger.info("  ✅ GUARDRAILS PASSED")

        # STEP 2: Fetch market data and generate signal
        logger.info("\n[STEP 2] Generating trading signal...")
        try:
            import yfinance as yf

            # Fetch SPY data
            ticker = yf.Ticker(PILOT_SYMBOL)
            data = ticker.history(period="60d", interval="1h")

            if data.empty:
                logger.warning("  No market data available")
                return result

            latest = data.iloc[-1]
            logger.info(f"  SPY Price: ${latest['Close']:.2f}")
            logger.info(f"  SMA-10: ${data['Close'].rolling(10).mean().iloc[-1]:.2f}")
            logger.info(f"  SMA-50: ${data['Close'].rolling(50).mean().iloc[-1]:.2f}")

            # Generate signal based on MA crossover
            sma_short = data['Close'].rolling(10).mean().iloc[-1]
            sma_long = data['Close'].rolling(50).mean().iloc[-1]

            # Read threshold from environment (PILOT_MA_THRESHOLD_PCT), default to 0.006 (0.6%)
            threshold = float(os.environ.get('PILOT_MA_THRESHOLD_PCT', '0.006'))
            threshold_pct = threshold * 100

            if sma_short > sma_long * (1 + threshold):
                action = 'BUY'
                confidence = 0.80
                reasons = [f"Bullish crossover: SMA-10 ({sma_short:.2f}) > SMA-50 ({sma_long:.2f}) by >{threshold_pct:.1f}%"]
            elif sma_short < sma_long * (1 - threshold):
                action = 'SELL'
                confidence = 0.80
                reasons = [f"Bearish crossover: SMA-10 ({sma_short:.2f}) < SMA-50 ({sma_long:.2f}) by >{threshold_pct:.1f}%"]
            else:
                action = 'HOLD'
                confidence = 0.70
                pct_diff = abs((sma_short - sma_long) / sma_long) * 100
                reasons = [f"No crossover: SMA-10 and SMA-50 differ by {pct_diff:.2f}% (threshold: {threshold_pct:.1f}%)"]

            logger.info(f"  Signal: {action}")
            logger.info(f"  Confidence: {confidence:.3f}")
            logger.info(f"  Reason: {reasons[0]}")

            result['action'] = action
            result['confidence'] = confidence

        except Exception as e:
            logger.error(f"  Error generating signal: {e}")
            return result

        # STEP 3: Check if action is viable
        if action == 'HOLD':
            logger.info(f"\n[STEP 3] Signal is HOLD - no order placed")
            return result

        if confidence < 0.65:
            logger.info(f"\n[STEP 3] Confidence too low ({confidence:.3f} < 0.65) - no order placed")
            return result

        # STEP 4: Re-check guardrails with actual action
        logger.info(f"\n[STEP 4] Re-checking guardrails with actual action ({action})...")
        allowed, reason = self.guardrails.check_all_guards(
            symbol=PILOT_SYMBOL,
            action=action,
            target_value_pct=0.005
        )

        if not allowed:
            logger.warning(f"  ❌ GUARDRAILS BLOCKED: {reason}")
            self.cycles_blocked += 1
            result['guardrails_passed'] = False
            return result

        # STEP 5: Attempt order placement
        logger.info(f"\n[STEP 5] Attempting order placement...")
        logger.info(f"  Action: {action}")
        logger.info(f"  Symbol: {PILOT_SYMBOL}")
        logger.info(f"  Target Value: 0.5%")

        self.orders_attempted += 1
        result['order_attempted'] = True

        try:
            from ib_insync import IB, Stock, MarketOrder

            ib = IB()
            ib.connect('127.0.0.1', 4002, clientId=503, timeout=10)
            logger.info("  ✅ Connected to IBKR paper trading (port 4002)")

            # Create contract
            contract = Stock(PILOT_SYMBOL, 'SMART', 'USD')

            # Get market data
            ticker_obj = ib.reqMktData(contract, '', False, False)
            ib.sleep(2)

            if ticker_obj.marketPrice() == 0:
                logger.warning("  Could not get market price - cancelling order")
                ib.disconnect()
                result['order_status'] = 'NO_PRICE'
                return result

            price = ticker_obj.marketPrice()
            logger.info(f"  Market Price: ${price:.2f}")

            # Calculate quantity
            target_value = 100000 * 0.005  # 0.5% of $100K
            quantity = int(target_value / price)

            if quantity < 1:
                logger.warning(f"  Quantity < 1 ({quantity}) - cancelling order")
                ib.disconnect()
                result['order_status'] = 'QUANTITY_TOO_SMALL'
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
            ib.sleep(3)

            status = trade.orderStatus.status
            logger.info(f"  Order Status: {status}")

            if status in ['Submitted', 'PreSubmitted', 'Filled']:
                logger.info(f"  ✅ Order {status.lower()} (OrderId: {trade.order.orderId})")
                result['order_status'] = status.upper()
                self.orders_executed += 1

                # Create execution receipt
                receipt = {
                    'cycle': self.cycle_count,
                    'cycle_id': cycle_id,
                    'timestamp': cycle_start.isoformat(),
                    'symbol': PILOT_SYMBOL,
                    'action': action,
                    'quantity': quantity,
                    'price': price,
                    'order_id': trade.order.orderId,
                    'status': status.upper(),
                    'confidence': confidence,
                    'target_value_pct': 0.005,
                    'guardrails': 'PASSED'
                }

                receipt_file = self.receipts_dir / f"receipt_phase4b_{cycle_id}.json"
                with open(receipt_file, 'w') as f:
                    json.dump(receipt, f, indent=2)
                logger.info(f"  📄 Receipt written: {receipt_file}")

            ib.disconnect()
            logger.info("  ✅ Disconnected from IBKR")

        except Exception as e:
            logger.error(f"  ❌ Order placement failed: {e}")
            result['order_status'] = 'FAILED'
            import traceback
            logger.error(traceback.format_exc())

        return result

    def run_pilot(self):
        """Run the complete pilot."""
        logger.info("Starting Phase 4B pilot execution...")
        logger.info("")

        results = []

        while self._should_continue():
            try:
                result = self._run_single_cycle()
                results.append(result)

                # Log cycle summary
                logger.info("")
                logger.info("=" * 80)
                logger.info("CYCLE SUMMARY")
                logger.info("=" * 80)
                logger.info(f"Total Cycles: {self.cycle_count}/{MAX_CYCLES}")
                logger.info(f"Cycles Completed: {self.cycle_count - self.cycles_blocked}")
                logger.info(f"Cycles Blocked: {self.cycles_blocked}")
                logger.info(f"Orders Attempted: {self.orders_attempted}")
                logger.info(f"Orders Executed: {self.orders_executed}")
                logger.info("=" * 80)

            except KeyboardInterrupt:
                logger.info("\n⚠️ Pilot interrupted by user")
                break
            except Exception as e:
                logger.error(f"\n❌ Cycle error: {e}")
                import traceback
                logger.error(traceback.format_exc())

            # Wait for next cycle
            if self._should_continue():
                logger.info(f"\n⏳ Waiting {CYCLE_INTERVAL_SEC}s for next cycle...")
                logger.info("")
                time.sleep(CYCLE_INTERVAL_SEC)

        # Pilot complete
        self._write_final_report(results)

    def _write_final_report(self, results):
        """Write final pilot report."""
        end_time = datetime.utcnow()
        duration = (end_time - self.start_time).total_seconds()

        # Count final receipts
        final_receipt_count = len(list(self.receipts_dir.glob('*.json'))) if self.receipts_dir.exists() else 0
        new_receipts = final_receipt_count - self.initial_receipt_count

        logger.info("")
        logger.info("=" * 80)
        logger.info("PHASE 4B PILOT COMPLETE - FINAL REPORT")
        logger.info("=" * 80)
        logger.info(f"Start Time: {self.start_time.isoformat()}")
        logger.info(f"End Time: {end_time.isoformat()}")
        logger.info(f"Duration: {duration:.1f}s ({duration/60:.1f} min)")
        logger.info("")
        logger.info("Cycle Statistics:")
        logger.info(f"  Total Cycles Run: {self.cycle_count}/{MAX_CYCLES}")
        logger.info(f"  Successful Cycles: {self.cycle_count - self.cycles_blocked}")
        logger.info(f"  Blocked Cycles: {self.cycles_blocked}")
        logger.info("")
        logger.info("Order Statistics:")
        logger.info(f"  Orders Attempted: {self.orders_attempted}")
        logger.info(f"  Orders Executed: {self.orders_executed}")
        logger.info(f"  Success Rate: {self.orders_executed/max(self.orders_attempted,1)*100:.1f}%")
        logger.info("")
        logger.info("Receipt Statistics:")
        logger.info(f"  Initial Receipts: {self.initial_receipt_count}")
        logger.info(f"  Final Receipts: {final_receipt_count}")
        logger.info(f"  New Receipts: {new_receipts}")
        logger.info("")
        logger.info("Safety Status:")
        logger.info(f"  Kill Switch: {'ACTIVE' if Path('/home/davidsanker/platform/EMERGENCY_STOP').exists() else 'NOT ACTIVE'}")
        logger.info("=" * 80)

        # Write report file
        report_file = SESSION_DIR / '02_pilot_final_report.txt'
        with open(report_file, 'w') as f:
            f.write("PHASE 4B PILOT - FINAL REPORT\n")
            f.write("=" * 80 + "\n\n")
            f.write(f"Start Time: {self.start_time.isoformat()}\n")
            f.write(f"End Time: {end_time.isoformat()}\n")
            f.write(f"Duration: {duration:.1f}s ({duration/60:.1f} min)\n\n")
            f.write("Cycle Statistics:\n")
            f.write(f"  Total Cycles Run: {self.cycle_count}/{MAX_CYCLES}\n")
            f.write(f"  Successful Cycles: {self.cycle_count - self.cycles_blocked}\n")
            f.write(f"  Blocked Cycles: {self.cycles_blocked}\n\n")
            f.write("Order Statistics:\n")
            f.write(f"  Orders Attempted: {self.orders_attempted}\n")
            f.write(f"  Orders Executed: {self.orders_executed}\n")
            f.write(f"  Success Rate: {self.orders_executed/max(self.orders_attempted,1)*100:.1f}%\n\n")
            f.write("Receipt Statistics:\n")
            f.write(f"  Initial Receipts: {self.initial_receipt_count}\n")
            f.write(f"  Final Receipts: {final_receipt_count}\n")
            f.write(f"  New Receipts: {new_receipts}\n\n")
            f.write("Cycle Details:\n\n")
            for result in results:
                f.write(f"  Cycle {result['cycle']}: {result['action']} (confidence: {result.get('confidence', 0):.3f})")
                if result.get('order_attempted'):
                    f.write(f" - Order: {result.get('order_status', 'N/A')}")
                f.write("\n")
            f.write("\n" + "=" * 80 + "\n")

        logger.info(f"\n📄 Final report written: {report_file}")


def main():
    """Main entry point."""
    pilot = Phase4BPilot()
    pilot.run_pilot()
    return 0


if __name__ == "__main__":
    sys.exit(main())
