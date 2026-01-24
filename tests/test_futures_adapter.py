"""
Unit Tests for Futures Adapter

Tests contract building and validation
"""

import pytest
import sys
from pathlib import Path

# Add platform root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from instruments.spec import (
    InstrumentType,
    FutureSpec,
    StockSpec,
    create_spec_from_dict
)
from instruments.ibkr_futures_adapter import IBKRFutureAdapter


class TestFutureSpec:
    """Test FutureSpec creation and validation"""

    def test_create_future_spec_basic(self):
        """Test creating a basic FutureSpec"""
        spec = FutureSpec(
            symbol="MES",
            expiry="202603",
            exchange="CME",
            currency="USD",
            multiplier=5
        )

        assert spec.symbol == "MES"
        assert spec.expiry == "202603"
        assert spec.exchange == "CME"
        assert spec.currency == "USD"
        assert spec.multiplier == 5
        assert spec.instrument_type == InstrumentType.FUT

    def test_future_spec_invalid_expiry_format(self):
        """Test that invalid expiry format raises error"""
        with pytest.raises(ValueError, match="Invalid expiry format"):
            FutureSpec(
                symbol="MES",
                expiry="2026",  # Wrong format (should be YYYYMM)
                exchange="CME",
                currency="USD",
                multiplier=5
            )

    def test_future_spec_invalid_multiplier(self):
        """Test that invalid multiplier raises error"""
        with pytest.raises(ValueError, match="Invalid multiplier"):
            FutureSpec(
                symbol="MES",
                expiry="202603",
                exchange="CME",
                currency="USD",
                multiplier=0  # Must be positive
            )

    def test_future_spec_to_ib_contract(self):
        """Test building IB contract from spec"""
        spec = FutureSpec(
            symbol="MES",
            expiry="202603",
            exchange="CME",
            currency="USD",
            multiplier=5
        )

        contract = spec.to_ib_contract()

        # Verify IB contract properties
        assert contract.symbol == "MES"
        assert contract.lastTradeDateOrContractMonth == "202603"
        assert contract.exchange == "CME"
        assert contract.currency == "USD"

    def test_future_spec_notional_value(self):
        """Test notional value calculation"""
        spec = FutureSpec(
            symbol="MES",
            expiry="202603",
            exchange="CME",
            currency="USD",
            multiplier=5
        )

        # MES at 5000: 5000 × $5 = $25,000 notional
        notional = spec.get_notional_value(5000.0)
        assert notional == 25000.0

    def test_future_spec_tick_value(self):
        """Test tick value calculation"""
        spec = FutureSpec(
            symbol="MES",
            expiry="202603",
            exchange="CME",
            currency="USD",
            multiplier=5
        )

        # MES: 0.25 tick × $5 multiplier = $1.25 per tick
        tick_value = spec.tick_value
        assert tick_value == 1.25

    def test_future_spec_string_representation(self):
        """Test string representation"""
        spec = FutureSpec(
            symbol="MES",
            expiry="202603",
            exchange="CME",
            currency="USD",
            multiplier=5
        )

        assert str(spec) == "Future(MES202603, mult=5)"


class TestStockSpec:
    """Test StockSpec for comparison"""

    def test_create_stock_spec(self):
        """Test creating a StockSpec"""
        spec = StockSpec(symbol="SPY")

        assert spec.symbol == "SPY"
        assert spec.exchange == "SMART"
        assert spec.currency == "USD"
        assert spec.instrument_type == InstrumentType.STOCK

    def test_stock_spec_to_ib_contract(self):
        """Test building IB contract from StockSpec"""
        spec = StockSpec(symbol="SPY")
        contract = spec.to_ib_contract()

        assert contract.symbol == "SPY"
        assert contract.exchange == "SMART"
        assert contract.currency == "USD"


class TestCreateSpecFromDict:
    """Test factory function for creating specs from dictionaries"""

    def test_create_future_spec_from_dict(self):
        """Test creating FutureSpec from dictionary"""
        spec_dict = {
            "instrument_type": "FUT",
            "symbol": "MES",
            "expiry": "202603",
            "exchange": "CME",
            "currency": "USD",
            "multiplier": 5
        }

        spec = create_spec_from_dict(spec_dict)

        assert isinstance(spec, FutureSpec)
        assert spec.symbol == "MES"
        assert spec.expiry == "202603"

    def test_create_stock_spec_from_dict(self):
        """Test creating StockSpec from dictionary"""
        spec_dict = {
            "instrument_type": "STOCK",
            "symbol": "SPY"
        }

        spec = create_spec_from_dict(spec_dict)

        assert isinstance(spec, StockSpec)
        assert spec.symbol == "SPY"

    def test_create_spec_defaults_to_stock(self):
        """Test that missing instrument_type defaults to STOCK"""
        spec_dict = {
            "symbol": "SPY"
        }

        spec = create_spec_from_dict(spec_dict)

        assert isinstance(spec, StockSpec)


class TestIBKRFutureAdapter:
    """Test IBKR futures adapter"""

    def test_adapter_initialization(self):
        """Test adapter can be initialized"""
        adapter = IBKRFutureAdapter()
        assert adapter.config_path is not None

    def test_build_contract_from_spec(self):
        """Test building IB contract from spec"""
        spec = FutureSpec(
            symbol="MES",
            expiry="202603",
            exchange="CME",
            currency="USD",
            multiplier=5
        )

        adapter = IBKRFutureAdapter()
        contract = adapter.build_contract(spec)

        assert contract.symbol == "MES"
        assert contract.lastTradeDateOrContractMonth == "202603"
        assert contract.exchange == "CME"
        assert contract.currency == "USD"

    def test_load_spec_from_config(self):
        """Test loading spec from config file"""
        adapter = IBKRFutureAdapter()

        # MES should be in config
        spec = adapter.load_spec_from_config("MES")

        assert spec.symbol == "MES"
        assert spec.instrument_type == InstrumentType.FUT
        assert spec.expiry == "202603"  # From config
        assert spec.multiplier == 5

    def test_get_available_instruments(self):
        """Test getting list of available instruments"""
        adapter = IBKRFutureAdapter()
        instruments = adapter.get_available_instruments()

        # Should have at least MES and MNQ
        assert "MES" in instruments
        assert "MNQ" in instruments

    def test_get_contract_metadata(self):
        """Test getting contract metadata"""
        adapter = IBKRFutureAdapter()
        metadata = adapter.get_contract_metadata("MES")

        assert metadata["symbol"] == "MES"
        assert metadata["instrument_type"] == "FUT"
        assert "multiplier" in metadata
        assert "expiry" in metadata

    def test_validate_spec_against_config(self):
        """Test that spec validation works"""
        adapter = IBKRFutureAdapter()

        # Valid spec should not raise
        spec = adapter.load_spec_from_config("MES")
        adapter.build_contract(spec)  # Should not raise

        # Invalid spec should raise
        invalid_spec = FutureSpec(
            symbol="MES",
            expiry="202606",  # Wrong expiry
            exchange="CME",
            currency="USD",
            multiplier=10  # Wrong multiplier
        )

        with pytest.raises(ValueError, match="Multiplier mismatch"):
            adapter.build_contract(invalid_spec)


class TestContractBuilding:
    """Integration tests for contract building"""

    def test_mes_contract_structure(self):
        """Test MES contract has correct structure"""
        spec = FutureSpec(
            symbol="MES",
            expiry="202603",
            exchange="CME",
            currency="USD",
            multiplier=5
        )

        contract = spec.to_ib_contract()

        # Verify all required fields
        assert contract.symbol == "MES"
        assert contract.lastTradeDateOrContractMonth == "202603"
        assert contract.exchange == "CME"
        assert contract.currency == "USD"
        assert contract.secType == "FUT"  # IB security type

    def test_mnq_contract_structure(self):
        """Test MNQ contract has correct structure"""
        spec = FutureSpec(
            symbol="MNQ",
            expiry="202603",
            exchange="CME",
            currency="USD",
            multiplier=2
        )

        contract = spec.to_ib_contract()

        assert contract.symbol == "MNQ"
        # Note: IB Future contracts don't expose .multiplier attribute directly
        # The multiplier is used for notional value calculation in the spec
        assert contract.secType == "FUT"


if __name__ == "__main__":
    # Run tests
    pytest.main([__file__, "-v"])
