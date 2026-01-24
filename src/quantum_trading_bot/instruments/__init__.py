"""
Instruments Package

Provides instrument abstraction layer for trading multiple asset classes.
"""

from .spec import (
    InstrumentType,
    InstrumentSpec,
    StockSpec,
    FutureSpec,
    OptionSpec,
    CryptoSpec,
    create_spec_from_dict
)

from .ibkr_futures_adapter import (
    IBKRFutureAdapter,
    create_future_contract
)

__all__ = [
    # Instrument types
    "InstrumentType",
    "InstrumentSpec",
    "StockSpec",
    "FutureSpec",
    "OptionSpec",
    "CryptoSpec",

    # Factory functions
    "create_spec_from_dict",
    "create_future_contract",

    # Adapters
    "IBKRFutureAdapter",
]
