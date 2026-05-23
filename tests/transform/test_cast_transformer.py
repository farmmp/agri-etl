"""Tests for CastTransformer."""
from __future__ import annotations

import datetime
import pytest

from agri_etl.ingestion.base_reader import SensorRecord
from agri_etl.transform.cast_transformer import CastTransformer


TS = datetime.datetime(2024, 6, 1, 12, 0, 0, tzinfo=datetime.timezone.utc)


def make_record(readings: dict) -> SensorRecord:
    return SensorRecord(sensor_id="s1", timestamp=TS, readings=readings)


# ---------------------------------------------------------------------------
# Init / validation
# ---------------------------------------------------------------------------

class TestCastTransformerInit:
    def test_missing_casts_raises(self):
        with pytest.raises(ValueError, match="requires 'casts'"):
            CastTransformer({})

    def test_empty_casts_raises(self):
        with pytest.raises(ValueError, match="non-empty dict"):
            CastTransformer({"casts": {}})

    def test_invalid_casts_type_raises(self):
        with pytest.raises(ValueError, match="non-empty dict"):
            CastTransformer({"casts": ["temp"]})

    def test_unsupported_type_raises(self):
        with pytest.raises(ValueError, match="Unsupported cast type"):
            CastTransformer({"casts": {"temp": "decimal"}})

    def test_valid_config_accepted(self):
        t = CastTransformer({"casts": {"temp": "float", "count": "int"}})
        assert t is not None


# ---------------------------------------------------------------------------
# Casting behaviour
# ---------------------------------------------------------------------------

class TestCastTransformerTransform:
    def test_cast_str_to_float(self):
        t = CastTransformer({"casts": {"temp": "float"}})
        result = t.transform([make_record({"temp": "23.5"})])
        assert result.errors == []
        assert result.records[0].readings["temp"] == 23.5
        assert isinstance(result.records[0].readings["temp"], float)

    def test_cast_float_to_int(self):
        t = CastTransformer({"casts": {"count": "int"}})
        result = t.transform([make_record({"count": 7.9})])
        assert result.records[0].readings["count"] == 7

    def test_cast_int_to_str(self):
        t = CastTransformer({"casts": {"code": "str"}})
        result = t.transform([make_record({"code": 42})])
        assert result.records[0].readings["code"] == "42"

    def test_missing_field_skipped_gracefully(self):
        t = CastTransformer({"casts": {"temp": "float"}})
        result = t.transform([make_record({"humidity": "80"})])
        assert result.errors == []
        assert result.records[0].readings["humidity"] == "80"

    def test_cast_error_recorded(self):
        t = CastTransformer({"casts": {"temp": "float"}})
        result = t.transform([make_record({"temp": "hot"})])
        assert len(result.errors) == 1
        assert "temp" in result.errors[0]
        # record is still kept (drop_on_error=False)
        assert len(result.records) == 1

    def test_drop_on_error(self):
        t = CastTransformer({"casts": {"temp": "float"}, "drop_on_error": True})
        result = t.transform([make_record({"temp": "hot"})])
        assert len(result.records) == 0
        assert len(result.errors) == 1

    def test_multiple_records_partial_failure(self):
        t = CastTransformer({"casts": {"temp": "float"}, "drop_on_error": True})
        records = [
            make_record({"temp": "21.0"}),
            make_record({"temp": "bad"}),
            make_record({"temp": "19.5"}),
        ]
        result = t.transform(records)
        assert len(result.records) == 2
        assert len(result.errors) == 1

    def test_original_record_not_mutated(self):
        t = CastTransformer({"casts": {"temp": "float"}})
        original = make_record({"temp": "22.1"})
        t.transform([original])
        assert isinstance(original.readings["temp"], str)
