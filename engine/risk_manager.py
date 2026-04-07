"""
Portfolio Risk Manager - USD Notional Normalization

Enforces portfolio-level risk limits with USD notional calculations.
FAIL-CLOSED: If equity/positions unavailable or stale, all trading is blocked.

Author: Autonomous Trading System
Date: 2026-01-24
Purpose: Portfolio risk management for autonomous trading
"""

import os
import sys
import json
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, Any, Tuple, Optional
import yaml


class PortfolioRiskManager:
    """
    Manages portfolio risk limits and USD notional calculations.

    Enforces:
    - Gross/net exposure limits
    - Per-symbol position limits
    - Daily loss limits
    - Drawdown limits
    - Order size limits
    """

    REASON_CODES = {
        'EQUITY_UNAVAILABLE': 'Account equity unavailable or stale',
        'POSITIONS_UNAVAILABLE': 'Position data unavailable or stale',
        'EXCEEDS_GROSS_EXPOSURE': 'Order would exceed gross exposure limit',
        'EXCEEDS_NET_EXPOSURE': 'Order would exceed net exposure limit',
        'EXCEEDS_DAILY_LOSS': 'Daily loss limit exceeded',
        'EXCEEDS_DRAWDOWN': 'Drawdown limit exceeded',
        'EXCEEDS_POSITION_LIMIT': 'Order would exceed per-symbol position limit',
        'EXCEEDS_ORDER_LIMIT': 'Order notional exceeds limit',
        'MAX_ORDERS_EXCEEDED': 'Daily order limit exceeded',
        'IN_COOLDOWN': 'System in cooldown after loss',
        'INSTRUMENT_NO_MULTIPLIER': 'Instrument missing multiplier (required for futures/options)',
        'ALLOWED': 'Order within risk limits',
    }

    def __init__(self):
        """Load risk limits and initialize state."""
        self.platform_path = Path(__file__).parent.parent
        self.config_path = self.platform_path / 'config' / 'risk_limits.yaml'
        self.state_path = self.platform_path / 'state' / 'risk_state.json'

        # Load config
        self.config = self._load_config()

        # Load state
        self.state = self._load_state()

    def _load_config(self) -> Dict[str, Any]:
        """Load risk limits YAML config."""
        if not self.config_path.exists():
            # Fail-closed defaults
            return {
                'max_gross_exposure_usd': 250000,
                'max_net_exposure_usd': 150000,
                'max_daily_loss_usd': 5000,
                'max_drawdown_usd': 25000,
                'max_position_usd_per_symbol': 50000,
                'max_order_notional_usd': 25000,
                'max_orders_per_day_global': 50,
                'cooldown_minutes_after_loss': 30,
            }

        try:
            with open(self.config_path, 'r') as f:
                return yaml.safe_load(f)
        except Exception as e:
            print(f"ERROR: Failed to load risk config: {e}", file=sys.stderr)
            return {'_error': str(e)}

    def _load_state(self) -> Dict[str, Any]:
        """Load risk state (rolling peaks, cooldowns, etc.)."""
        if not self.state_path.exists():
            return {
                'rolling_equity_peak': 1000000,  # Starting baseline
                'last_update': datetime.utcnow().isoformat(),
                'orders_today': 0,
                'last_reset_date': datetime.utcnow().date().isoformat(),
                'daily_loss_usd': 0,
                'in_cooldown_until': None,
                'last_order_timestamp': None,
            }

        try:
            with open(self.state_path, 'r') as f:
                return json.load(f)
        except Exception as e:
            print(f"ERROR: Failed to load risk state: {e}", file=sys.stderr)
            return {'_error': str(e)}

    def _save_state(self):
        """Save risk state atomically."""
        try:
            self.state['last_update'] = datetime.utcnow().isoformat()
            temp_path = self.state_path.with_suffix('.tmp')
            with open(temp_path, 'w') as f:
                json.dump(self.state, f, indent=2)
            temp_path.rename(self.state_path)
        except Exception as e:
            print(f"ERROR: Failed to save risk state: {e}", file=sys.stderr)

    def check_order(self,
                   account_equity: Optional[float],
                   positions: Dict[str, Dict],
                   symbol: str,
                   side: str,
                   quantity: float,
                   price: float,
                   asset_class: str,
                   multiplier: float = 1.0) -> Tuple[bool, str, Dict]:
        """
        Check if order is within risk limits.

        Args:
            account_equity: Total account equity in USD
            positions: Dict of current positions {symbol: {'quantity': qty, 'price': price, ...}}
            symbol: Trading symbol
            side: 'BUY' or 'SELL'
            quantity: Order quantity
            price: Estimated price
            asset_class: STOCK, ETF, OPTION, FUT
            multiplier: Contract multiplier (for futures/options)

        Returns:
            (allowed: bool, reason_code: str, details: dict)
        """
        # Check 1: Account equity available
        if account_equity is None:
            return (False, self.REASON_CODES['EQUITY_UNAVAILABLE'], {
                'message': 'Account equity unavailable - cannot compute risk',
            })

        # Check 2: Positions available
        if positions is None:
            return (False, self.REASON_CODES['POSITIONS_UNAVAILABLE'], {
                'message': 'Position data unavailable - cannot compute risk',
            })

        # Check 3: Cooldown active
        if self.state.get('in_cooldown_until'):
            cooldown_end = datetime.fromisoformat(self.state['in_cooldown_until'])
            if datetime.utcnow() < cooldown_end:
                return (False, self.REASON_CODES['IN_COOLDOWN'], {
                    'in_cooldown_until': self.state['in_cooldown_until'],
                    'reason': self.state.get('cooldown_reason', 'Daily loss limit exceeded'),
                })
            else:
                # Cooldown expired
                self.state['in_cooldown_until'] = None
                self._save_state()

        # Check 4: Daily order limit
        today = datetime.utcnow().date().isoformat()
        if self.state.get('last_reset_date') != today:
            # Reset daily counters
            self.state['last_reset_date'] = today
            self.state['orders_today'] = 0
            self.state['daily_loss_usd'] = 0
            self._save_state()

        max_orders = self.config.get('max_orders_per_day_global', 50)
        if self.state['orders_today'] >= max_orders:
            return (False, self.REASON_CODES['MAX_ORDERS_EXCEEDED'], {
                'orders_today': self.state['orders_today'],
                'max_orders': max_orders,
            })

        # Check 5: Order notional limit
        notional_usd = self._calculate_notional(quantity, price, multiplier, asset_class)
        max_order_notional = self.config.get('max_order_notional_usd', 25000)
        if notional_usd > max_order_notional:
            return (False, self.REASON_CODES['EXCEEDS_ORDER_LIMIT'], {
                'notional_usd': notional_usd,
                'max_notional_usd': max_order_notional,
            })

        # Check 6: Per-symbol position limit
        current_position_notional = 0
        if symbol in positions:
            pos = positions[symbol]
            current_position_notional = abs(pos['quantity'] * pos['price'] * pos.get('multiplier', 1.0))

        new_position_notional = current_position_notional + notional_usd
        max_position_notional = self.config.get('max_position_usd_per_symbol', 50000)
        if new_position_notional > max_position_notional:
            return (False, self.REASON_CODES['EXCEEDS_POSITION_LIMIT'], {
                'symbol': symbol,
                'current_notional': current_position_notional,
                'new_notional': new_position_notional,
                'max_notional': max_position_notional,
            })

        # Check 7: Gross exposure limit
        gross_exposure = self._calculate_gross_exposure(positions)
        new_gross_exposure = gross_exposure + notional_usd
        max_gross = self.config.get('max_gross_exposure_usd', 250000)
        if new_gross_exposure > max_gross:
            return (False, self.REASON_CODES['EXCEEDS_GROSS_EXPOSURE'], {
                'current_gross': gross_exposure,
                'new_gross': new_gross_exposure,
                'max_gross': max_gross,
            })

        # Check 8: Net exposure limit
        net_exposure = self._calculate_net_exposure(positions)
        if side == 'BUY':
            new_net_exposure = net_exposure + notional_usd
        else:  # SELL
            new_net_exposure = net_exposure - notional_usd

        max_net = self.config.get('max_net_exposure_usd', 150000)
        if abs(new_net_exposure) > max_net:
            return (False, self.REASON_CODES['EXCEEDS_NET_EXPOSURE'], {
                'current_net': net_exposure,
                'new_net': new_net_exposure,
                'max_net': max_net,
            })

        # Check 9: Daily loss limit
        daily_loss = self.state.get('daily_loss_usd', 0)
        max_daily_loss = self.config.get('max_daily_loss_usd', 5000)
        if daily_loss >= max_daily_loss:
            # Enter cooldown
            cooldown_end = datetime.utcnow() + timedelta(minutes=self.config.get('cooldown_minutes_after_loss', 30))
            self.state['in_cooldown_until'] = cooldown_end.isoformat()
            self.state['cooldown_reason'] = 'Daily loss limit exceeded'
            self._save_state()

            return (False, self.REASON_CODES['EXCEEDS_DAILY_LOSS'], {
                'daily_loss_usd': daily_loss,
                'max_daily_loss_usd': max_daily_loss,
                'cooldown_until': self.state['in_cooldown_until'],
            })

        # Check 10: Drawdown limit (if tracking enabled)
        if self.config.get('enable_drawdown_tracking', True):
            peak = self.state.get('rolling_equity_peak', account_equity)
            if account_equity > peak:
                self.state['rolling_equity_peak'] = account_equity
                self._save_state()

            drawdown = peak - account_equity
            max_drawdown = self.config.get('max_drawdown_usd', 25000)
            if drawdown > max_drawdown:
                return (False, self.REASON_CODES['EXCEEDS_DRAWDOWN'], {
                    'current_drawdown': drawdown,
                    'max_drawdown': max_drawdown,
                    'peak_equity': peak,
                })

        # All checks passed
        return (True, self.REASON_CODES['ALLOWED'], {
            'notional_usd': notional_usd,
            'account_equity': account_equity,
            'gross_exposure': gross_exposure,
            'net_exposure': net_exposure,
            'orders_today': self.state['orders_today'],
        })

    def _calculate_notional(self, quantity: float, price: float, multiplier: float, asset_class: str) -> float:
        """Calculate USD notional value of order."""
        if asset_class in ['FUT', 'OPTION']:
            return quantity * price * multiplier
        else:  # STOCK, ETF
            return quantity * price

    def _calculate_gross_exposure(self, positions: Dict) -> float:
        """Calculate gross exposure (sum of absolute position values)."""
        gross = 0.0
        for symbol, pos in positions.items():
            qty = pos.get('quantity', 0)
            price = pos.get('price', 0)
            multiplier = pos.get('multiplier', 1.0)
            asset_class = pos.get('asset_class', 'STOCK')
            gross += abs(self._calculate_notional(qty, price, multiplier, asset_class))
        return gross

    def _calculate_net_exposure(self, positions: Dict) -> float:
        """Calculate net exposure (long - short)."""
        net = 0.0
        for symbol, pos in positions.items():
            qty = pos.get('quantity', 0)
            price = pos.get('price', 0)
            multiplier = pos.get('multiplier', 1.0)
            asset_class = pos.get('asset_class', 'STOCK')
            notional = self._calculate_notional(qty, price, multiplier, asset_class)

            # Long positions add, short positions subtract
            if qty >= 0:
                net += notional
            else:
                net -= notional
        return net

    def record_order(self, order_id: str, symbol: str, notional_usd: float):
        """Record an order for daily tracking."""
        self.state['orders_today'] = self.state.get('orders_today', 0) + 1
        self.state['last_order_timestamp'] = datetime.utcnow().isoformat()
        self._save_state()

    def record_loss(self, loss_usd: float):
        """Record a realized loss."""
        self.state['daily_loss_usd'] = self.state.get('daily_loss_usd', 0) + loss_usd
        self._save_state()


def main():
    """CLI for testing risk manager."""
    import argparse

    parser = argparse.ArgumentParser(description='Check portfolio risk')
    parser.add_argument('--equity', type=float, help='Account equity in USD')
    parser.add_argument('--symbol', help='Symbol to trade')
    parser.add_argument('--side', choices=['BUY', 'SELL'], help='Order side')
    parser.add_argument('--qty', type=float, help='Order quantity')
    parser.add_argument('--price', type=float, help='Estimated price')
    parser.add_argument('--asset-class', help='Asset class')
    parser.add_argument('--multiplier', type=float, default=1.0, help='Contract multiplier')
    args = parser.parse_args()

    risk_mgr = PortfolioRiskManager()

    # Mock positions if not provided
    positions = {
        'SPY': {'quantity': 100, 'price': 450.0, 'asset_class': 'ETF', 'multiplier': 1.0},
        'AAPL': {'quantity': 50, 'price': 180.0, 'asset_class': 'STOCK', 'multiplier': 1.0},
    }

    allowed, reason, details = risk_mgr.check_order(
        account_equity=args.equity or 1000000,
        positions=positions,
        symbol=args.symbol,
        side=args.side,
        quantity=args.qty,
        price=args.price,
        asset_class=args.asset_class,
        multiplier=args.multiplier,
    )

    print(f"Order Check: {allowed}")
    print(f"Reason: {reason}")
    print(f"Details: {details}")
    return 0 if allowed else 1


if __name__ == '__main__':
    sys.exit(main())
