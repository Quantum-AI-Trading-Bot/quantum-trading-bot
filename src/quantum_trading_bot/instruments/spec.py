"""
Instrument Specification Abstraction

Purpose: Provide instrument-agnostic interface for trading multiple asset classes
         (stocks, futures, options, crypto) through a unified API

Design: Base class InstrumentSpec with subclasses for each instrument type
        Each subclass knows how to build its IB contract object

Usage:
    spec = FutureSpec(symbol="MES", expiry="202603", exchange="CME", currency="USD", multiplier=5)
    ib_contract = spec.to_ib_contract()  # Returns ib_insync.Future object
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import Enum
from typing import Optional


class InstrumentType(Enum):
    """Instrument types supported by the trading system"""
    STOCK = "STOCK"
    FUT = "FUT"
    OPT = "OPT"
    CRYPTO = "CRYPTO"


class InstrumentSpec(ABC):
    """
    Base class for instrument specifications.

    All instrument types inherit from this and implement to_ib_contract().

    Note: This is NOT a dataclass to avoid field ordering issues in subclasses.
          Each subclass defines its own fields.
    """

    @abstractmethod
    def to_ib_contract(self):
        """
        Build IB contract object for this instrument.

        Returns:
            ib_insync.Contract object (Stock, Future, Option, etc.)
        """
        pass

    @abstractmethod
    def __str__(self) -> str:
        """Human-readable representation"""
        pass


@dataclass
class StockSpec(InstrumentSpec):
    """
    Stock (equity) instrument specification.

    Example:
        spec = StockSpec(symbol="SPY", exchange="SMART", currency="USD")
        contract = spec.to_ib_contract()  # Stock("SPY", "SMART", "USD")
    """
    symbol: str
    exchange: str = "SMART"  # IB's smart routing
    currency: str = "USD"

    def __post_init__(self):
        # Set instrument type
        object.__setattr__(self, 'instrument_type', InstrumentType.STOCK)

    def to_ib_contract(self):
        """Build IB Stock contract"""
        from ib_insync import Stock
        return Stock(
            symbol=self.symbol,
            exchange=self.exchange,
            currency=self.currency
        )

    def __str__(self) -> str:
        return f"Stock({self.symbol})"


@dataclass
class FutureSpec(InstrumentSpec):
    """
    Futures contract specification.

    Example:
        spec = FutureSpec(
            symbol="MES",
            expiry="202603",  # March 2026
            exchange="CME"
        )
        contract = spec.to_ib_contract()  # Future("MES", "202603", "CME", "USD")

    Args:
        symbol: Futures symbol (e.g., "MES", "MNQ", "ES")
        expiry: Contract expiry in YYYYMM format (e.g., "202603")
        exchange: Exchange code (e.g., "CME", "CBOT", "NYMEX")
        currency: Contract currency (e.g., "USD", "EUR")
        multiplier: Contract multiplier (e.g., 5 for MES, 2 for MNQ)
        contract_id: Optional IB con_id (if known)
    """
    symbol: str
    expiry: str  # Format: YYYYMM
    exchange: str
    currency: str = "USD"
    multiplier: int = 1  # Default, should be overridden
    contract_id: Optional[int] = None

    def __post_init__(self):
        # Set instrument type
        object.__setattr__(self, 'instrument_type', InstrumentType.FUT)

        # Ensure expiry is a string (YAML may load as int)
        if isinstance(self.expiry, int):
            object.__setattr__(self, 'expiry', str(self.expiry))

        # Validate expiry format (now that it's guaranteed to be a string)
        if not self.expiry or len(self.expiry) != 6 or not self.expiry.isdigit():
            raise ValueError(f"Invalid expiry format: {self.expiry}. Expected YYYYMM.")

        # Validate multiplier
        if self.multiplier <= 0:
            raise ValueError(f"Invalid multiplier: {self.multiplier}. Must be positive.")

    def to_ib_contract(self):
        """Build IB Future contract"""
        from ib_insync import Future
        return Future(
            symbol=self.symbol,
            lastTradeDateOrContractMonth=self.expiry,
            exchange=self.exchange,
            currency=self.currency
        )

    def __str__(self) -> str:
        return f"Future({self.symbol}{self.expiry}, mult={self.multiplier})"

    def get_notional_value(self, current_price: float) -> float:
        """
        Calculate notional value of one contract.

        Args:
            current_price: Current futures price

        Returns:
            Notional value = price × multiplier
        """
        return current_price * self.multiplier

    @property
    def tick_value(self) -> float:
        """
        Calculate value of one tick.

        CME futures typically have 0.25 tick size.
        MES: 0.25 × $5 = $1.25 per tick
        MNQ: 0.25 × $2 = $0.50 per tick
        """
        return 0.25 * self.multiplier


@dataclass
class OptionSpec(InstrumentSpec):
    """
    Options contract specification (for future implementation).

    Not implemented in Phase FUT-1.0.
    """
    symbol: str
    expiry: str
    strike: float
    right: str  # "CALL" or "PUT"
    exchange: str = "SMART"
    currency: str = "USD"
    multiplier: int = 100  # Standard for US equity options

    def __post_init__(self):
        self.instrument_type = InstrumentType.OPT

    def to_ib_contract(self):
        """Build IB Option contract"""
        from ib_insync import Option
        return Option(
            symbol=self.symbol,
            lastTradeDateOrContractMonth=self.expiry,
            strike=self.strike,
            right=self.right,
            exchange=self.exchange,
            currency=self.currency,
            multiplier=self.multiplier
        )

    def __str__(self) -> str:
        return f"Option({self.symbol} {self.expiry} {self.strike} {self.right})"


@dataclass
class CryptoSpec(InstrumentSpec):
    """
    Cryptocurrency specification (for future implementation).

    Not implemented in Phase FUT-1.0.
    """
    symbol: str
    exchange: str = "PAXOS"  # IB's crypto exchange
    currency: str = "USD"

    def __post_init__(self):
        self.instrument_type = InstrumentType.CRYPTO

    def to_ib_contract(self):
        """Build IB Crypto contract"""
        from ib_insync import Crypto
        return Crypto(
            symbol=self.symbol,
            exchange=self.exchange,
            currency=self.currency
        )

    def __str__(self) -> str:
        return f"Crypto({self.symbol})"


def create_spec_from_dict(spec_dict: dict) -> InstrumentSpec:
    """
    Factory function to create InstrumentSpec from dictionary.

    Useful for loading from YAML config or JSON decision plans.

    Args:
        spec_dict: Dictionary with instrument metadata

    Returns:
        Appropriate InstrumentSpec subclass instance

    Example:
        spec_dict = {
            "instrument_type": "FUT",
            "symbol": "MES",
            "expiry": "202603",
            "exchange": "CME",
            "currency": "USD",
            "multiplier": 5
        }
        spec = create_spec_from_dict(spec_dict)
    """
    instrument_type = spec_dict.get("instrument_type", "STOCK")

    if instrument_type == "STOCK":
        return StockSpec(
            symbol=spec_dict["symbol"],
            exchange=spec_dict.get("exchange", "SMART"),
            currency=spec_dict.get("currency", "USD")
        )

    elif instrument_type == "FUT":
        return FutureSpec(
            symbol=spec_dict["symbol"],
            expiry=spec_dict["expiry"],
            exchange=spec_dict["exchange"],
            currency=spec_dict.get("currency", "USD"),
            multiplier=spec_dict.get("multiplier", 1)
        )

    elif instrument_type == "OPT":
        return OptionSpec(
            symbol=spec_dict["symbol"],
            expiry=spec_dict["expiry"],
            strike=spec_dict["strike"],
            right=spec_dict["right"],
            exchange=spec_dict.get("exchange", "SMART"),
            currency=spec_dict.get("currency", "USD")
        )

    elif instrument_type == "CRYPTO":
        return CryptoSpec(
            symbol=spec_dict["symbol"],
            exchange=spec_dict.get("exchange", "PAXOS"),
            currency=spec_dict.get("currency", "USD")
        )

    else:
        raise ValueError(f"Unknown instrument type: {instrument_type}")
