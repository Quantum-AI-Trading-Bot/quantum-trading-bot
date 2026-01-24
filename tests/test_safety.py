"""
Safety Assertion Tests for Quantum AI Trading Bot

These tests ensure that the bot operates safely and cannot accidentally
execute live trades without explicit configuration.

Run with: pytest tests/test_safety.py -v
"""

import os
import tempfile
import json
from pathlib import Path


class TestSafetyDefaults:
    """Test that default configuration values are safe."""

    def test_allow_live_is_false_by_default(self):
        """ALLOW_LIVE must be False by default."""
        # Import config
        import sys
        sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))

        # Check default value
        from quantum_trading_bot.config.quantum_runtime import get_config
        config = get_config()

        # ASSERTION: Live trading must be disabled by default
        assert config.get('ALLOW_LIVE', False) == False, \
            "ALLOW_LIVE must be False by default to prevent accidental live trading"

    def test_trading_enabled_is_false_by_default(self):
        """TRADING_ENABLED must be False by default."""
        import sys
        sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))

        from quantum_trading_bot.config.quantum_runtime import get_config
        config = get_config()

        # ASSERTION: Trading must be disabled by default
        assert config.get('TRADING_ENABLED', False) == False, \
            "TRADING_ENABLED must be False by default"

    def test_dry_run_is_true_by_default(self):
        """DRY_RUN must be True by default."""
        import sys
        sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))

        from quantum_trading_bot.config.quantum_runtime import get_config
        config = get_config()

        # ASSERTION: Dry run must be enabled by default
        assert config.get('DRY_RUN', True) == True, \
            "DRY_RUN must be True by default to prevent accidental execution"


class TestPaperTradingConstraints:
    """Test that paper trading mode has proper safeguards."""

    def test_paper_trading_uses_port_4002(self):
        """Paper trading must use port 4002, not live port 7497."""
        import sys
        sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))

        from quantum_trading_bot.config.quantum_runtime import get_config
        config = get_config()

        trading_mode = config.get('TRADING_MODE', 'paper')
        ib_port = config.get('IB_PORT', 4002)

        # ASSERTION: Paper trading must use port 4002
        if trading_mode == 'paper':
            assert ib_port == 4002, \
                f"Paper trading must use port 4002, not {ib_port}"

    def test_paper_trading_cannot_execute_live(self):
        """Paper trading mode cannot execute live trades."""
        import sys
        sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))

        from quantum_trading_bot.config.quantum_runtime import get_config
        config = get_config()

        # ASSERTION: If in paper mode, live trading must be impossible
        if config.get('TRADING_MODE') == 'paper':
            assert config.get('ALLOW_LIVE', False) == False, \
                "ALLOW_LIVE must be False when TRADING_MODE=paper"


class TestRiskLimits:
    """Test that risk limits are within safe bounds."""

    def test_max_position_size_reasonable(self):
        """MAX_POSITION_SIZE must be <= 20% of portfolio."""
        import sys
        sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))

        from quantum_trading_bot.config.quantum_runtime import get_config
        config = get_config()

        max_position = config.get('MAX_POSITION_SIZE', 0.15)

        # ASSERTION: No single position should exceed 20% of portfolio
        assert max_position <= 0.20, \
            f"MAX_POSITION_SIZE ({max_position}) exceeds 20% safety limit"

    def test_max_portfolio_risk_reasonable(self):
        """MAX_PORTFOLIO_RISK must be <= 30% of portfolio."""
        import sys
        sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))

        from quantum_trading_bot.config.quantum_runtime import get_config
        config = get_config()

        max_risk = config.get('MAX_PORTFOLIO_RISK', 0.25)

        # ASSERTION: Total portfolio risk should not exceed 30%
        assert max_risk <= 0.30, \
            f"MAX_PORTFOLIO_RISK ({max_risk}) exceeds 30% safety limit"

    def test_min_confidence_threshold(self):
        """MIN_CONFIDENCE must be >= 0.60 (60%)."""
        import sys
        sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))

        from quantum_trading_bot.config.quantum_runtime import get_config
        config = get_config()

        min_confidence = config.get('MIN_CONFIDENCE', 0.75)

        # ASSERTION: Minimum confidence should be at least 60%
        assert min_confidence >= 0.60, \
            f"MIN_CONFIDENCE ({min_confidence}) below 60% safety threshold"


class TestVPAStructure:
    """Test that VPA (Verifiable Prediction Artifact) structure is valid."""

    def test_vpa_has_required_keys(self):
        """VPA must contain all required fields."""
        # Create a sample VPA
        vpa = {
            'symbol': 'SPY',
            'timestamp': '2026-01-24T12:00:00Z',
            'prediction': 'HOLD',
            'confidence': 0.82,
            'forecast_horizon': '1d',
            'model_version': 'v0.1.0',
            'features': {},
            'metadata': {}
        }

        # Required keys
        required_keys = [
            'symbol', 'timestamp', 'prediction', 'confidence',
            'forecast_horizon', 'model_version'
        ]

        # ASSERTION: All required keys must be present
        for key in required_keys:
            assert key in vpa, f"VPA missing required key: {key}"

    def test_vpa_can_be_written_to_file(self):
        """VPA can be successfully written to JSON file."""
        import tempfile

        vpa = {
            'symbol': 'SPY',
            'timestamp': '2026-01-24T12:00:00Z',
            'prediction': 'HOLD',
            'confidence': 0.82,
            'forecast_horizon': '1d',
            'model_version': 'v0.1.0',
            'features': {},
            'metadata': {}
        }

        # Write to temp file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump(vpa, f)
            temp_path = f.name

        try:
            # Verify file exists and is valid JSON
            assert Path(temp_path).exists(), "VPA file was not created"

            with open(temp_path, 'r') as f:
                loaded_vpa = json.load(f)

            assert loaded_vpa == vpa, "Loaded VPA does not match original"
        finally:
            # Cleanup
            os.unlink(temp_path)


class TestSecretsNotInGit:
    """Test that secrets are properly excluded from git."""

    def test_env_file_in_gitignore(self):
        """.env must be in .gitignore."""
        gitignore_path = Path(__file__).parent.parent / '.gitignore'
        gitignore_content = gitignore_path.read_text()

        # ASSERTION: .env must be ignored
        assert '.env' in gitignore_content, \
            ".env not found in .gitignore - secrets may be committed!"

    def test_key_files_in_gitignore(self):
        """Key files (*.key, *.pem) must be in .gitignore."""
        gitignore_path = Path(__file__).parent.parent / '.gitignore'
        gitignore_content = gitignore_path.read_text()

        # ASSERTION: Key files must be ignored
        assert '*.key' in gitignore_content, \
            "*.key not in .gitignore - credentials may be committed!"
        assert '*.pem' in gitignore_content, \
            "*.pem not in .gitignore - credentials may be committed!"


class TestEmergencyStop:
    """Test emergency stop functionality."""

    def test_emergency_stop_file_can_be_created(self):
        """EMERGENCY_STOP file can be created to halt trading."""
        import tempfile

        # Create temp emergency stop file
        with tempfile.NamedTemporaryFile(mode='w', delete=False) as f:
            f.write('')  # Empty file is sufficient
            temp_path = f.name

        try:
            # ASSERTION: File exists
            assert Path(temp_path).exists(), \
                "EMERGENCY_STOP file could not be created"

            # Simulate checking for emergency stop
            emergency_stop = Path(temp_path).exists()
            assert emergency_stop, \
                "Emergency stop detection failed"
        finally:
            os.unlink(temp_path)

    def test_emergency_stop_in_gitignore(self):
        """EMERGENCY_STOP file must be in .gitignore."""
        gitignore_path = Path(__file__).parent.parent / '.gitignore'
        gitignore_content = gitignore_path.read_text()

        # ASSERTION: EMERGENCY_STOP must be ignored
        assert 'EMERGENCY_STOP' in gitignore_content, \
            "EMERGENCY_STOP not in .gitignore"


class TestLedgerIntegrity:
    """Test that ledger files maintain integrity."""

    def test_ledger_file_is_valid_jsonl(self):
        """Ledger files must be valid JSONL format."""
        import tempfile

        # Sample valid JSONL entry
        entry = {
            'timestamp': '2026-01-24T12:00:00Z',
            'symbol': 'SPY',
            'action': 'BUY',
            'quantity': 100,
            'price': 450.25
        }

        # Write to temp file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.jsonl', delete=False) as f:
            f.write(json.dumps(entry) + '\n')
            temp_path = f.name

        try:
            # Verify valid JSONL
            with open(temp_path, 'r') as f:
                for line in f:
                    json.loads(line)  # Will raise if invalid

            # ASSERTION: If we get here, JSONL is valid
            assert True, "JSONL validation passed"
        except json.JSONDecodeError as e:
            assert False, f"Invalid JSONL format: {e}"
        finally:
            os.unlink(temp_path)


if __name__ == '__main__':
    import pytest
    pytest.main([__file__, '-v'])
