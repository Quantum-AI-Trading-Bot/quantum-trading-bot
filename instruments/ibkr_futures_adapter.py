"""
IBKR Futures Adapter

Purpose: Build IBKR Future contract objects from FutureSpec
         Handles contract metadata and validation

Usage:
    adapter = IBKRFutureAdapter()
    spec = FutureSpec(symbol="MES", expiry="202603", exchange="CME", currency="USD", multiplier=5)
    contract = adapter.build_contract(spec)
"""

from typing import Dict, Any, Optional
from pathlib import Path
import yaml

from .spec import FutureSpec, InstrumentSpec


class IBKRFutureAdapter:
    """
    Adapter for building IBKR Future contracts.

    This adapter:
    1. Takes a FutureSpec object
    2. Validates the contract details
    3. Builds an ib_insync.Future object
    4. Optionally loads contract metadata from config
    """

    def __init__(self, config_path: Optional[Path] = None):
        """
        Initialize the adapter.

        Args:
            config_path: Path to instruments.yaml config file
        """
        if config_path is None:
            config_path = Path("/home/davidsanker/platform/config/instruments.yaml")

        self.config_path = config_path
        self.config = self._load_config()

    def _load_config(self) -> Dict[str, Any]:
        """Load instruments configuration from YAML."""
        if not self.config_path.exists():
            return {}

        with open(self.config_path, 'r') as f:
            return yaml.safe_load(f) or {}

    def build_contract(self, spec: FutureSpec):
        """
        Build IBKR Future contract from spec.

        Args:
            spec: FutureSpec object

        Returns:
            ib_insync.Future object
        """
        # Validate spec against config (if available)
        if spec.symbol in self.config:
            self._validate_spec(spec, self.config[spec.symbol])

        # Build contract using spec's to_ib_contract method
        return spec.to_ib_contract()

    def _validate_spec(self, spec: FutureSpec, config: Dict[str, Any]) -> None:
        """
        Validate FutureSpec against config.

        Raises:
            ValueError: If spec doesn't match config
        """
        # Check exchange matches
        if spec.exchange != config.get("exchange"):
            raise ValueError(
                f"Exchange mismatch for {spec.symbol}: "
                f"spec has {spec.exchange}, config has {config.get('exchange')}"
            )

        # Check currency matches
        if spec.currency != config.get("currency"):
            raise ValueError(
                f"Currency mismatch for {spec.symbol}: "
                f"spec has {spec.currency}, config has {config.get('currency')}"
            )

        # Check multiplier matches
        if spec.multiplier != config.get("multiplier"):
            raise ValueError(
                f"Multiplier mismatch for {spec.symbol}: "
                f"spec has {spec.multiplier}, config has {config.get('multiplier')}"
            )

    def load_spec_from_config(self, symbol: str) -> FutureSpec:
        """
        Load FutureSpec from config.

        Args:
            symbol: Instrument symbol (e.g., "MES", "MNQ")

        Returns:
            FutureSpec object

        Raises:
            KeyError: If symbol not found in config
            ValueError: If config is invalid
        """
        if symbol not in self.config:
            raise KeyError(f"Instrument {symbol} not found in {self.config_path}")

        config = self.config[symbol]

        # Validate config has required fields
        required_fields = ["symbol", "exchange", "currency", "multiplier", "expiry"]
        for field in required_fields:
            if field not in config:
                raise ValueError(f"Missing required field '{field}' in config for {symbol}")

        # Build spec
        return FutureSpec(
            symbol=config["symbol"],
            expiry=config["expiry"],
            exchange=config["exchange"],
            currency=config["currency"],
            multiplier=config["multiplier"]
        )

    def get_available_instruments(self) -> list:
        """
        Get list of available futures instruments from config.

        Returns:
            List of instrument symbols (e.g., ["MES", "MNQ"])
        """
        return [
            symbol for symbol, config in self.config.items()
            if config.get("instrument_type") == "FUT"
        ]

    def get_contract_metadata(self, symbol: str) -> Dict[str, Any]:
        """
        Get contract metadata from config.

        Args:
            symbol: Instrument symbol

        Returns:
            Dictionary with contract metadata
        """
        if symbol not in self.config:
            raise KeyError(f"Instrument {symbol} not found in config")

        return self.config[symbol]


def create_future_contract(
    symbol: str,
    expiry: Optional[str] = None,
    exchange: Optional[str] = None,
    currency: str = "USD",
    config_path: Optional[Path] = None
) -> Any:
    """
    Convenience function to create a futures contract.

    Args:
        symbol: Futures symbol (e.g., "MES", "MNQ")
        expiry: Contract expiry (YYYYMM). If None, loads from config.
        exchange: Exchange code. If None, loads from config.
        currency: Contract currency (default: "USD")
        config_path: Path to instruments.yaml

    Returns:
        ib_insync.Future object

    Example:
        # Load from config
        contract = create_future_contract("MES")

        # Override expiry
        contract = create_future_contract("MES", expiry="202606")

        # Full specification
        contract = create_future_contract(
            symbol="MES",
            expiry="202603",
            exchange="CME",
            currency="USD"
        )
    """
    adapter = IBKRFutureAdapter(config_path)

    # If only symbol provided, load from config
    if expiry is None and exchange is None:
        spec = adapter.load_spec_from_config(symbol)
    else:
        # Build spec from parameters
        if expiry is None:
            raise ValueError(f"Must specify expiry for {symbol}")
        if exchange is None:
            raise ValueError(f"Must specify exchange for {symbol}")

        spec = FutureSpec(
            symbol=symbol,
            expiry=expiry,
            exchange=exchange,
            currency=currency
        )

    return adapter.build_contract(spec)
