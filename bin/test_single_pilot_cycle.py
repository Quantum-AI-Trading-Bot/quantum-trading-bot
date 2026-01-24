#!/usr/bin/env python3
"""
Single Cycle Pilot Test
Run ONE trading cycle to verify the system works
"""

import sys
import os
import json
from pathlib import Path
from datetime import datetime
import logging

# Add platform to path
platform_path = Path(__file__).parent.parent
sys.path.insert(0, str(platform_path))

from bin.pilot_guardrails import PilotGuardrails

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)s | %(message)s'
)
logger = logging.getLogger(__name__)

def main():
    """Run single cycle test."""
    logger.info("=" * 80)
    logger.info("SINGLE CYCLE PILOT TEST")
    logger.info("=" * 80)

    guardrails = PilotGuardrails()

    # STEP 1: Check guardrails
    logger.info("\n[STEP 1] Checking pilot guardrails...")
    allowed, reason = guardrails.check_all_guards(
        symbol='SPY',
        action='BUY',
        target_value_pct=0.005
    )

    if not allowed:
        logger.error(f"❌ Guardrails blocked: {reason}")
        return 1

    logger.info("✅ Guardrails passed")

    # STEP 2: Fetch SPY data
    logger.info("\n[STEP 2] Fetching SPY market data...")
    try:
        import yfinance as yf
        ticker = yf.Ticker('SPY')
        data = ticker.history(period="60d", interval="1h")

        if data.empty:
            logger.error("No data available")
            return 1

        latest = data.iloc[-1]
        logger.info(f"  SPY Price: ${latest['Close']:.2f}")
        logger.info(f"  Volume: {latest['Volume']:,}")
        logger.info(f"  SMA-10: ${data['Close'].rolling(10).mean().iloc[-1]:.2f}")
        logger.info(f"  SMA-50: ${data['Close'].rolling(50).mean().iloc[-1]:.2f}")

    except Exception as e:
        logger.error(f"Error fetching data: {e}")
        return 1

    # STEP 3: Generate signal
    logger.info("\n[STEP 3] Generating trading signal...")
    try:
        from models.phase1.phase1_ma_crossover_signal import Phase1MACrossoverSignal

        config = {
            'short_window': 10,
            'long_window': 50,
            'model_id': 'phase1_ma_crossover'
        }

        model = Phase1MACrossoverSignal(config)

        features = {
            'symbol': 'SPY',
            'timestamp': datetime.utcnow().isoformat(),
            'Close': latest['Close'],
            'close': latest['Close'],
            'sma_10': data['Close'].rolling(10).mean().iloc[-1],
            'sma_50': data['Close'].rolling(50).mean().iloc[-1]
        }

        signal_result = model.generate_signal(features)

        logger.info(f"  Signal: {signal_result.action}")
        logger.info(f"  Confidence: {signal_result.confidence:.3f}")
        if signal_result.reasons:
            logger.info(f"  Reasons: {', '.join(signal_result.reasons)}")

        action = signal_result.action
        confidence = signal_result.confidence

    except Exception as e:
        logger.error(f"Error generating signal: {e}")
        import traceback
        traceback.print_exc()
        return 1

    # STEP 4: Check if action is viable
    if action == 'HOLD':
        logger.info("\n[STEP 4] Signal is HOLD - no order placed")
        logger.info("✅ Single cycle test complete")
        return 0

    if confidence < 0.65:
        logger.info(f"\n[STEP 4] Confidence too low ({confidence:.3f} < 0.65) - no order placed")
        logger.info("✅ Single cycle test complete")
        return 0

    # STEP 5: Attempt order
    logger.info(f"\n[STEP 5] Attempting {action} order...")
    logger.info("  Confidence exceeds threshold - proceeding with IBKR connection")

    try:
        from ib_insync import IB, Stock, MarketOrder

        ib = IB()
        ib.connect('127.0.0.1', 4002, clientId=502, timeout=10)
        logger.info("  ✅ Connected to IBKR paper trading (port 4002)")

        # Create contract
        contract = Stock('SPY', 'SMART', 'USD')

        # Get market data
        ticker = ib.reqMktData(contract, '', False, False)
        ib.sleep(2)

        if ticker.marketPrice() == 0:
            logger.warning("  Could not get market price - cancelling order")
            ib.disconnect()
            return 1

        price = ticker.marketPrice()
        logger.info(f"  Market Price: ${price:.2f}")

        # Calculate quantity
        target_value = 100000 * 0.005  # 0.5% of $100K
        quantity = int(target_value / price)

        if quantity < 1:
            logger.warning(f"  Quantity < 1 ({quantity}) - cancelling order")
            ib.disconnect()
            return 1

        logger.info(f"  Quantity: {quantity} shares")
        logger.info(f"  Target Value: ${target_value:.2f}")

        # Create order
        if action == 'BUY':
            order = MarketOrder('BUY', quantity)
        else:
            order = MarketOrder('SELL', quantity)

        order.orderType = 'MKT'
        order.tif = 'DAY'

        # Place order
        trade = ib.placeOrder(contract, order)
        logger.info(f"  ✅ Order placed: {action} {quantity} SPY @ MKT")

        # Wait for submission
        ib.sleep(3)

        status = trade.orderStatus.status
        logger.info(f"  Order Status: {status}")

        if status in ['Submitted', 'PreSubmitted']:
            logger.info(f"  ✅ Order successfully submitted (OrderId: {trade.order.orderId})")

            # Create receipt
            receipt = {
                'timestamp': datetime.utcnow().isoformat(),
                'symbol': 'SPY',
                'action': action,
                'quantity': quantity,
                'price': price,
                'order_id': trade.order.orderId,
                'status': status,
                'confidence': confidence,
                'target_value_pct': 0.005
            }

            receipts_dir = Path('/home/davidsanker/platform/execution_receipts')
            receipts_dir.mkdir(parents=True, exist_ok=True)

            receipt_file = receipts_dir / f"receipt_test_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.json"
            with open(receipt_file, 'w') as f:
                json.dump(receipt, f, indent=2)

            logger.info(f"  📄 Receipt written: {receipt_file}")

        ib.disconnect()
        logger.info("  ✅ Disconnected from IBKR")

    except Exception as e:
        logger.error(f"  ❌ Order failed: {e}")
        import traceback
        traceback.print_exc()
        return 1

    logger.info("\n" + "=" * 80)
    logger.info("✅ SINGLE CYCLE TEST COMPLETE")
    logger.info("=" * 80)
    return 0


if __name__ == "__main__":
    sys.exit(main())
