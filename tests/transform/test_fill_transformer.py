"""Tests for FillTransformer."""

from __future__ import annotations

from datetime import datetime, timezone

import pytest

from agri_etl.ingestion.base_reader import SensorRecord
from agri_etl.transform.fill_transformer import FillTransformer


TS = datetime(2024, 6, 1, 12, 0, 0, tzinfo=timezone.utc)


def make_record(readings: dict) -> SensorRecord:
    return SensorRecord(sensor_id="s1", timestamp=TS, readings=readings)


# ---------------------------------------------------------------------------
# Init / validation
# ---------------------------------------------------------------------------

class TestFillTransformerInit:
    def test_missing_fields_raises(self):
        with pytest.raises(KeyError, match="fields"):
            FillTransformer({"strategy": "constant", "value": 0})

    def test_empty_fields_raises(self):
        with pytest.raises(ValueError, match="non-empty list"):
            FillTransformer({"fields": [], "strategy": "constant", "value": 0})

    def test_invalid_strategy_raises(self):
        with pytest.raises(ValueError, match="Unsupported strategy"):
            FillTransformer({"fields": ["temp"], "strategy": "median"})

    def test_constant_strategy_missing_value_raises(self):
        with pytest.raises(KeyError, match="value"):
            FillTransformer({"fields": ["temp"], "strategy": "constant"})

    def test_valid_constant_config(self):
        t = FillTransformer({"fields": ["temp"], "strategy": "constant", "value": -999})
        assert t is not None

    def test_valid_forward_fill_config(self):
        t = FillTransformer({"fields": ["temp"], "strategy": "forward_fill"})
        assert t is not None


# ---------------------------------------------------------------------------
# Constant fill
# ---------------------------------------------------------------------------

class TestConstantFill:
    def _transformer(self, value=0.0):
        return FillTransformer({"fields": ["temp", "humidity"], "strategy": "constant", "value": value})

    def test_none_replaced_with_constant(self):
        t = self._transformer(value=-999)
        result = t.transform([make_record({"temp": None, "humidity": 55.0})])
        assert result.records[0].readings["temp"] == -999
        assert result.records[0].readings["humidity"] == 55.0

    def test_non_none_values_unchanged(self):
        t = self._transformer(value=0)
        result = t.transform([make_record({"temp": 22.5, "humidity": None})])
        assert result.records[0].readings["temp"] == 22.5
        assert result.records[0].readings["humidity"] == 0

    def test_no_errors_on_constant_fill(self):
        t = self._transformer()
        result = t.transform([make_record({"temp": None})])
        assert result.errors == []


# ---------------------------------------------------------------------------
# Forward fill
# ---------------------------------------------------------------------------

class TestForwardFill:
    def _transformer(self):
        return FillTransformer({"fields": ["temp"], "strategy": "forward_fill"})

    def test_forward_fill_uses_previous_value(self):
        t = self._transformer()
        records = [
            make_record({"temp": 20.0}),
            make_record({"temp": None}),
        ]
        result = t.transform(records)
        assert result.records[1].readings["temp"] == 20.0

    def test_forward_fill_no_prior_value_records_error(self):
        t = self._transformer()
        result = t.transform([make_record({"temp": None})])
        assert result.records[0].readings["temp"] is None
        assert len(result.errors) == 1
        assert "temp" in result.errors[0]

    def test_forward_fill_chain(self):
        t = self._transformer()
        records = [
            make_record({"temp": 18.0}),
            make_record({"temp": None}),
            make_record({"temp": None}),
        ]
        result = t.transform(records)
        assert result.records[1].readings["temp"] == 18.0
        assert result.records[2].readings["temp"] == 18.0
