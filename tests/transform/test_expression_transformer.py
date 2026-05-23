"""Tests for ExpressionTransformer."""

from __future__ import annotations

import datetime
import pytest

from agri_etl.ingestion.base_reader import SensorRecord
from agri_etl.transform.expression_transformer import ExpressionTransformer

TS = datetime.datetime(2024, 6, 1, 12, 0, 0, tzinfo=datetime.timezone.utc)


def make_record(readings: dict) -> SensorRecord:
    return SensorRecord(sensor_id="s1", timestamp=TS, readings=readings)


# ---------------------------------------------------------------------------
# Init / validation
# ---------------------------------------------------------------------------

class TestExpressionTransformerInit:
    def test_missing_expressions_raises(self):
        with pytest.raises(ValueError, match="expressions"):
            ExpressionTransformer({})

    def test_empty_expressions_raises(self):
        with pytest.raises(ValueError, match="empty"):
            ExpressionTransformer({"expressions": {}})

    def test_invalid_expressions_type_raises(self):
        with pytest.raises(TypeError, match="dict"):
            ExpressionTransformer({"expressions": ["temp_f = temp_c * 1.8"]})

    def test_empty_key_raises(self):
        with pytest.raises(ValueError, match="keys"):
            ExpressionTransformer({"expressions": {"": "temp_c * 2"}})

    def test_empty_expr_raises(self):
        with pytest.raises(ValueError, match="non-empty string"):
            ExpressionTransformer({"expressions": {"temp_f": ""}})

    def test_valid_config_accepted(self):
        t = ExpressionTransformer({"expressions": {"temp_f": "temp_c * 9 / 5 + 32"}})
        assert t is not None


# ---------------------------------------------------------------------------
# Transform behaviour
# ---------------------------------------------------------------------------

class TestExpressionTransformerTransform:
    def test_derived_field_added(self):
        t = ExpressionTransformer({"expressions": {"temp_f": "temp_c * 9 / 5 + 32"}})
        record = make_record({"temp_c": 0.0})
        result = t.transform([record])
        assert len(result.passed) == 1
        assert result.passed[0].readings["temp_f"] == pytest.approx(32.0)

    def test_original_fields_preserved(self):
        t = ExpressionTransformer({"expressions": {"temp_f": "temp_c * 9 / 5 + 32"}})
        record = make_record({"temp_c": 100.0, "humidity": 55.0})
        result = t.transform([record])
        readings = result.passed[0].readings
        assert readings["temp_c"] == 100.0
        assert readings["humidity"] == 55.0
        assert readings["temp_f"] == pytest.approx(212.0)

    def test_chained_expressions(self):
        t = ExpressionTransformer({
            "expressions": {
                "temp_f": "temp_c * 9 / 5 + 32",
                "temp_k": "temp_c + 273.15",
            }
        })
        record = make_record({"temp_c": 25.0})
        result = t.transform([record])
        readings = result.passed[0].readings
        assert readings["temp_f"] == pytest.approx(77.0)
        assert readings["temp_k"] == pytest.approx(298.15)

    def test_math_helpers_available(self):
        t = ExpressionTransformer({"expressions": {"root": "sqrt(value)"}})
        record = make_record({"value": 9.0})
        result = t.transform([record])
        assert result.passed[0].readings["root"] == pytest.approx(3.0)

    def test_bad_expression_goes_to_failed(self):
        t = ExpressionTransformer({"expressions": {"bad": "undefined_var * 2"}})
        record = make_record({"temp_c": 20.0})
        result = t.transform([record])
        assert len(result.passed) == 0
        assert len(result.failed) == 1

    def test_empty_batch_returns_empty(self):
        t = ExpressionTransformer({"expressions": {"x": "1 + 1"}})
        result = t.transform([])
        assert result.passed == []
        assert result.failed == []
