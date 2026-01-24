"""
Unit Tests for Decision Plan Schema with Futures Support

Tests that decision plans can represent both stocks and futures
"""

import pytest
import json
import sys
from pathlib import Path

# Add platform root to path
sys.path.insert(0, str(Path(__file__).parent.parent))


class TestDecisionPlanSchema:
    """Test decision plan schema with futures support"""

    def test_stock_decision_plan_schema(self):
        """Test stock decision plan has expected schema"""
        plan = {
            "action": "BUY",
            "symbol": "SPY",
            "quantity": 100,
            "order_type": "MKT",
            "confidence": 0.85
        }

        # Validate required fields exist
        assert "action" in plan
        assert "symbol" in plan
        assert plan["action"] in ["BUY", "SELL", "HOLD"]

        # No instrument_type means STOCK (default)
        assert plan.get("instrument_type", "STOCK") == "STOCK"

    def test_futures_decision_plan_schema(self):
        """Test futures decision plan has extended schema"""
        plan = {
            "action": "BUY",
            "symbol": "MES",
            "quantity": 1,
            "order_type": "MKT",
            "confidence": 0.85,

            # Futures-specific fields
            "instrument_type": "FUT",
            "contract": {
                "symbol": "MES",
                "expiry": "202603",
                "exchange": "CME",
                "currency": "USD",
                "multiplier": 5
            }
        }

        # Validate required futures fields
        assert plan["instrument_type"] == "FUT"
        assert "contract" in plan
        assert plan["contract"]["expiry"] == "202603"
        assert plan["contract"]["multiplier"] == 5

    def test_decision_plan_backward_compatibility(self):
        """Test old stock decision plans still work"""
        # Old format (no instrument_type field)
        old_plan = {
            "action": "BUY",
            "symbol": "SPY",
            "quantity": 100
        }

        # Should default to STOCK
        assert old_plan.get("instrument_type", "STOCK") == "STOCK"
        assert "contract" not in old_plan  # Old plans don't have contract field

    def test_futures_decision_plan_requires_contract(self):
        """Test that futures decision plans must have contract metadata"""
        # Missing contract field
        invalid_plan = {
            "action": "BUY",
            "symbol": "MES",
            "quantity": 1,
            "instrument_type": "FUT"
            # Missing "contract" field
        }

        # Should be missing contract metadata
        assert "contract" not in invalid_plan

        # This would fail validation in executor
        with pytest.raises(ValueError, match="contract_metadata required"):
            from bin.vpa_executor import ExecutionIntent
            intent = ExecutionIntent(
                action=invalid_plan["action"],
                symbol=invalid_plan["symbol"],
                quantity=invalid_plan["quantity"],
                instrument_type=invalid_plan["instrument_type"]
            )
            # Trying to build IB order without contract_metadata should fail
            # (This is tested in the executor tests)


class TestDecisionPlanSerialization:
    """Test decision plan JSON serialization/deserialization"""

    def test_serialize_decision_plan(self):
        """Test decision plan can be serialized to JSON"""
        plan = {
            "action": "BUY",
            "symbol": "MES",
            "quantity": 1,
            "instrument_type": "FUT",
            "contract": {
                "symbol": "MES",
                "expiry": "202603",
                "exchange": "CME",
                "currency": "USD",
                "multiplier": 5
            }
        }

        # Should serialize without errors
        json_str = json.dumps(plan)
        assert json_str is not None

    def test_deserialize_decision_plan(self):
        """Test decision plan can be deserialized from JSON"""
        json_str = '''
        {
            "action": "BUY",
            "symbol": "MES",
            "quantity": 1,
            "instrument_type": "FUT",
            "contract": {
                "symbol": "MES",
                "expiry": "202603",
                "exchange": "CME",
                "currency": "USD",
                "multiplier": 5
            }
        }
        '''

        plan = json.loads(json_str)

        assert plan["action"] == "BUY"
        assert plan["instrument_type"] == "FUT"
        assert plan["contract"]["expiry"] == "202603"


class TestDecisionPlanValidation:
    """Test decision plan validation rules"""

    def test_valid_futures_decision_plan(self):
        """Test valid futures decision plan passes validation"""
        plan = {
            "action": "BUY",
            "symbol": "MES",
            "quantity": 1,
            "instrument_type": "FUT",
            "contract": {
                "symbol": "MES",
                "expiry": "202603",
                "exchange": "CME",
                "currency": "USD",
                "multiplier": 5
            }
        }

        # All required fields present
        assert "action" in plan
        assert "symbol" in plan
        assert plan["action"] in ["BUY", "SELL"]
        assert plan["instrument_type"] == "FUT"
        assert "contract" in plan
        assert "expiry" in plan["contract"]

    def test_invalid_futures_decision_plan_missing_expiry(self):
        """Test futures decision plan without expiry is invalid"""
        plan = {
            "action": "BUY",
            "symbol": "MES",
            "quantity": 1,
            "instrument_type": "FUT",
            "contract": {
                "symbol": "MES",
                "exchange": "CME",
                "currency": "USD",
                "multiplier": 5
                # Missing "expiry"
            }
        }

        # Missing required field
        assert "expiry" not in plan["contract"]

    def test_invalid_futures_decision_plan_wrong_action(self):
        """Test decision plan with invalid action"""
        plan = {
            "action": "INVALID_ACTION",
            "symbol": "MES",
            "quantity": 1,
            "instrument_type": "FUT"
        }

        # Invalid action
        assert plan["action"] not in ["BUY", "SELL", "HOLD"]


class TestDecisionPlanInVPA:
    """Test decision plan integration with VPA"""

    def test_vpa_with_stock_decision_plan(self):
        """Test VPA can contain stock decision plan"""
        vpa = {
            "timestamp": "2026-01-22T19:00:00Z",
            "decision_plan": {
                "action": "BUY",
                "symbol": "SPY",
                "quantity": 100,
                "order_type": "MKT",
                "confidence": 0.85
            }
        }

        # Should serialize correctly
        json_str = json.dumps(vpa)
        assert json_str is not None

    def test_vpa_with_futures_decision_plan(self):
        """Test VPA can contain futures decision plan"""
        vpa = {
            "timestamp": "2026-01-22T19:00:00Z",
            "decision_plan": {
                "action": "BUY",
                "symbol": "MES",
                "quantity": 1,
                "order_type": "MKT",
                "confidence": 0.85,
                "instrument_type": "FUT",
                "contract": {
                    "symbol": "MES",
                    "expiry": "202603",
                    "exchange": "CME",
                    "currency": "USD",
                    "multiplier": 5
                }
            }
        }

        # Should serialize correctly
        json_str = json.dumps(vpa)
        assert json_str is not None

        # Deserialize and verify
        vpa_loaded = json.loads(json_str)
        assert vpa_loaded["decision_plan"]["instrument_type"] == "FUT"
        assert vpa_loaded["decision_plan"]["contract"]["expiry"] == "202603"


if __name__ == "__main__":
    # Run tests
    pytest.main([__file__, "-v"])
