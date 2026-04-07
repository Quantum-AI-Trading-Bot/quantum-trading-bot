"""
Whitelist Profile Manager - Asset and Symbol Rollout Control

Enforces graduated rollout across asset classes with strict per-phase limits.
FAIL-CLOSED: If profile missing/invalid, all trading is blocked.

Author: Autonomous Trading System
Date: 2026-01-24
Purpose: Phase-based rollout with risk controls
"""

import os
import sys
from pathlib import Path
from typing import Dict, Any, Tuple, List
import yaml


class WhitelistManager:
    """
    Manages whitelist profiles for graduated asset/symbol rollout.

    Validates:
    - Asset class permissions
    - Symbol-specific permissions
    - Order quantity/size limits
    - Options/futures constraints
    """

    REASON_CODES = {
        'PROFILE_MISSING': 'Whitelist profile not found',
        'PROFILE_INVALID': 'Whitelist profile schema invalid',
        'ASSET_CLASS_BLOCKED': 'Asset class not allowed in current phase',
        'SYMBOL_NOT_WHITELISTED': 'Symbol not in whitelist',
        'MAX_ORDERS_EXCEEDED': 'Daily order limit exceeded',
        'POSITION_LIMIT_EXCEEDED': 'Position size limit exceeded',
        'OPTION_SHORT_PREMIUM': 'Short premium options not allowed',
        'OPTION_MAX_PREMIUM': 'Option premium limit exceeded',
        'FUTURE_NOT_MICRO': 'Only micro futures allowed',
        'FUTURE_WRONG_EXCHANGE': 'Futures exchange not allowed',
        'ALLOWED': 'Symbol and order allowed',
    }

    def __init__(self):
        """Load whitelist profile from environment or config."""
        self.platform_path = Path(__file__).parent.parent
        self.whitelists_dir = self.platform_path / 'config' / 'whitelists'

        # Get profile from environment
        profile_name = os.getenv('WHITELIST_PROFILE', 'phase0_stocks_us')
        self.profile_name = profile_name
        self.profile_path = self.whitelists_dir / f'{profile_name}.yaml'

        # Load profile
        self.profile = self._load_profile()

    def _load_profile(self) -> Dict[str, Any]:
        """Load and validate whitelist profile YAML."""
        if not self.profile_path.exists():
            return {
                '_error': 'PROFILE_MISSING',
                'profile_name': self.profile_name,
                'message': f'Whitelist profile not found: {self.profile_path}',
            }

        try:
            with open(self.profile_path, 'r') as f:
                profile = yaml.safe_load(f)

            # Validate schema
            required_fields = ['profile_name', 'asset_classes', 'symbols']
            for field in required_fields:
                if field not in profile:
                    return {
                        '_error': 'PROFILE_INVALID',
                        'message': f'Missing required field: {field}',
                    }

            return profile

        except Exception as e:
            return {
                '_error': 'PROFILE_INVALID',
                'message': f'Error loading whitelist profile: {e}',
            }

    def is_symbol_allowed(self, symbol: str, asset_class: str = None) -> Tuple[bool, str, Dict]:
        """
        Check if symbol is allowed for trading.

        Args:
            symbol: Trading symbol (e.g., 'SPY', 'AAPL')
            asset_class: Asset class (STOCK, ETF, OPTION, FUT)

        Returns:
            (allowed: bool, reason_code: str, details: dict)
        """
        # Check if profile has error
        if '_error' in self.profile:
            return (False, self.REASON_CODES[self.profile['_error']], self.profile)

        # Check 1: Asset class allowed
        allowed_asset_classes = self.profile.get('asset_classes', [])
        if asset_class and asset_class not in allowed_asset_classes:
            return (False, self.REASON_CODES['ASSET_CLASS_BLOCKED'], {
                'asset_class': asset_class,
                'allowed_classes': allowed_asset_classes,
                'symbol': symbol,
            })

        # Check 2: Symbol whitelisted
        allowed_symbols = self.profile.get('symbols', [])
        if symbol not in allowed_symbols:
            return (False, self.REASON_CODES['SYMBOL_NOT_WHITELISTED'], {
                'symbol': symbol,
                'allowed_symbols': allowed_symbols,
            })

        # All checks passed
        return (True, self.REASON_CODES['ALLOWED'], {
            'symbol': symbol,
            'asset_class': asset_class,
            'profile': self.profile_name,
        })

    def get_max_orders_per_day(self) -> int:
        """Get maximum orders per day for this profile."""
        return self.profile.get('max_orders_per_day', 20)

    def get_max_position_usd(self, symbol: str) -> float:
        """Get max position size in USD for a symbol."""
        return self.profile.get('max_position_usd_per_symbol', 50000)

    def get_max_order_notional_usd(self) -> float:
        """Get max order notional in USD."""
        return self.profile.get('max_order_notional_usd', 25000)

    def check_option_constraints(self, contracts: int, premium_usd: float) -> Tuple[bool, str, Dict]:
        """
        Check if options order complies with constraints.

        Returns:
            (allowed, reason_code, details)
        """
        # Check if options are even allowed in this profile
        if 'OPTION' not in self.profile.get('asset_classes', []):
            return (False, 'ASSET_CLASS_BLOCKED', {
                'message': 'Options not allowed in current whitelist profile',
            })

        option_config = self.profile.get('options', {})

        # Check 1: Long-only (no short premium)
        if not option_config.get('long_only', True):
            return (True, 'ALLOWED', {})  # Short premium allowed
        elif option_config.get('long_only', True):
            # For long-only, we'd need to know if this is short or long
            # For now, we check max premium
            pass

        # Check 2: Max premium per day
        max_premium = option_config.get('max_premium_usd_per_day', 2000)
        if premium_usd > max_premium:
            return (False, self.REASON_CODES['OPTION_MAX_PREMIUM'], {
                'premium_usd': premium_usd,
                'max_premium_usd': max_premium,
            })

        # Check 3: Max contracts per order
        max_contracts = option_config.get('max_contracts_per_order', 2)
        if contracts > max_contracts:
            return (False, 'OPTION_MAX_CONTRACTS', {
                'contracts': contracts,
                'max_contracts': max_contracts,
            })

        return (True, self.REASON_CODES['ALLOWED'], {})

    def check_future_constraints(self, symbol: str, contracts: int, exchange: str = None) -> Tuple[bool, str, Dict]:
        """
        Check if futures order complies with constraints.

        Returns:
            (allowed, reason_code, details)
        """
        # Check if futures are allowed
        if 'FUT' not in self.profile.get('asset_classes', []):
            return (False, 'ASSET_CLASS_BLOCKED', {
                'message': 'Futures not allowed in current whitelist profile',
            })

        future_config = self.profile.get('futures', {})

        # Check 1: Micro futures only
        if not future_config.get('allow_only_micro', True):
            return (False, 'FUTURE_NOT_MICRO', {
                'message': 'Only micro futures allowed',
            })

        # Check 2: Allowed roots/exchanges
        allowed_roots = future_config.get('allowed_roots', [])
        if allowed_roots and symbol not in allowed_roots:
            return (False, 'FUTURE_NOT_WHITELISTED', {
                'symbol': symbol,
                'allowed_roots': allowed_roots,
            })

        # Check 3: Exchange
        allowed_exchanges = future_config.get('allowed_exchanges', [])
        if exchange and allowed_exchanges and exchange not in allowed_exchanges:
            return (False, 'FUTURE_WRONG_EXCHANGE', {
                'exchange': exchange,
                'allowed_exchanges': allowed_exchanges,
            })

        # Check 4: Max contracts per order
        max_contracts = future_config.get('max_contracts_per_order', 1)
        if contracts > max_contracts:
            return (False, 'FUTURE_MAX_CONTRACTS', {
                'contracts': contracts,
                'max_contracts': max_contracts,
            })

        return (True, self.REASON_CODES['ALLOWED'], {})

    def validate_profile(self) -> Tuple[bool, str, Dict]:
        """
        Validate whitelist profile for Monday deployment.

        Returns:
            (valid, reason_code, details)
        """
        if '_error' in self.profile:
            return (False, self.profile['_error'], self.profile)

        # Check required fields
        required_fields = ['profile_name', 'asset_classes', 'symbols']
        for field in required_fields:
            if field not in self.profile:
                return (False, 'PROFILE_INVALID', {
                    'missing_field': field,
                })

        # Check that symbols list is not empty
        if not self.profile.get('symbols'):
            return (False, 'PROFILE_INVALID', {
                'message': 'Symbols list is empty',
            })

        # Check that phase 0 starts with safe instruments
        if self.profile_name == 'phase0_stocks_us':
            for symbol in self.profile['symbols']:
                if symbol not in ['SPY', 'QQQ', 'IWM', 'DIA', 'AAPL', 'MSFT', 'GOOGL', 'AMZN', 'TSLA', 'NVDA']:
                    return (False, 'PROFILE_INVALID', {
                        'message': f'Phase 0 should only include safe symbols, found: {symbol}',
                    })

        return (True, 'VALID', {
            'profile_name': self.profile_name,
            'asset_classes': len(self.profile.get('asset_classes', [])),
            'symbols_count': len(self.profile.get('symbols', [])),
            'phase': self.profile.get('phase', 0),
        })


def main():
    """CLI for testing whitelist."""
    import argparse

    parser = argparse.ArgumentParser(description='Check whitelist permissions')
    parser.add_argument('--symbol', required=True, help='Symbol to check')
    parser.add_argument('--asset-class', help='Asset class (STOCK, ETF, OPTION, FUT)')
    parser.add_argument('--validate', action='store_true', help='Validate profile instead')
    args = parser.parse_args()

    whitelist = WhitelistManager()

    if args.validate:
        valid, reason, details = whitelist.validate_profile()
        print(f"Profile Validation: {valid}")
        print(f"Reason: {reason}")
        print(f"Details: {details}")
        return 0 if valid else 1
    else:
        allowed, reason, details = whitelist.is_symbol_allowed(args.symbol, args.asset_class)
        print(f"Symbol {args.symbol} ({args.asset_class or 'ANY'}): {allowed}")
        print(f"Reason: {reason}")
        print(f"Details: {details}")
        return 0 if allowed else 1


if __name__ == '__main__':
    sys.exit(main())
