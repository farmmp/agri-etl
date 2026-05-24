from __future__ import annotations

import pytest
from datetime import datetime, timezone

from agri_etl.ingestion.base_reader import SensorRecord
from agri_etl.transform.jitter_transformer import JitterTransformer


TS = datetime(2024, 6, 1, 12, 0, 0, tzinfo=timezone.utc)


def make_record(readings: dict) -> SensorRecord:
    return SensorRecord(sensor_id="s1", timestamp=TS, readings=readings)


# ---------------------------------------------------------------------------
# Init / validation
# ---------------------------------------------------------------------------

class TestJitterTransformerInit:
    def test_missing_fields_raises(self):
        with pytest.raises(ValueError, match="'fields'"):
            JitterTransformer({})

    def test_empty_fields_raises(self):
        with pytest.raises(ValueError, match="must not be empty"):
            JitterTransformer({"fields": {}})

    def test_invalid_fields_type_raises(self):
        with pytest.raises(TypeError, match="dict"):
            JitterTransformer({"fields": ["temp"]})

    def test_negative_magnitude_raises(self):
        with pytest.raises(ValueError, match=">= 0"):
            JitterTransformer({"fields": {"temp": -1.0}})

    def test_non_numeric_magnitude_raises(self):
        with pytest.raises(TypeError, match="number"):
            JitterTransformer({"fields": {"temp": "big"}})

    def test_non_int_seed_raises(self):
        with pytest.raises(TypeError, match="integer"):
            JitterTransformer({"fields": {"temp": 0.5}, "seed": "abc"})

    def test_valid_config_accepted(self):
        t = JitterTransformer({"fields": {"temp": 1.0}, "seed": 42})
        assert t is not None


# ---------------------------------------------------------------------------
# Behaviour
# ---------------------------------------------------------------------------

class TestJitterTransformerBehaviour:
    def test_zero_magnitude_leaves_value_unchanged(self):
        t = JitterTransformer({"fields": {"temp": 0.0}, "seed": 0})
        rec = make_record({"temp": 25.0})
        result = t.transform([rec])
        assert result.records[0].readings["temp"] == pytest.approx(25.0)

    def test_noise_applied_within_bounds(self):
        magnitude = 2.0
        t = JitterTransformer({"fields": {"temp": magnitude}, "seed": 7})
        rec = make_record({"temp": 20.0})
        result = t.transform([rec])
        jittered = result.records[0].readings["temp"]
        assert 20.0 - magnitude <= jittered <= 20.0 + magnitude

    def test_seed_produces_deterministic_output(self):
        cfg = {"fields": {"temp": 5.0}, "seed": 99}
        records = [make_record({"temp": float(i)}) for i in range(10)]
        r1 = JitterTransformer(cfg).transform(records)
        r2 = JitterTransformer(cfg).transform(records)
        vals1 = [r.readings["temp"] for r in r1.records]
        vals2 = [r.readings["temp"] for r in r2.records]
        assert vals1 == vals2

    def test_missing_field_skipped_silently(self):
        t = JitterTransformer({"fields": {"humidity": 1.0}, "seed": 0})
        rec = make_record({"temp": 25.0})
        result = t.transform([rec])
        assert "humidity" not in result.records[0].readings
        assert result.errors == []

    def test_non_numeric_field_logged_as_error(self):
        t = JitterTransformer({"fields": {"status": 1.0}, "seed": 0})
        rec = make_record({"status": "ok"})
        result = t.transform([rec])
        assert len(result.errors) == 1
        assert "status" in result.errors[0]

    def test_other_fields_preserved(self):
        t = JitterTransformer({"fields": {"temp": 1.0}, "seed": 0})
        rec = make_record({"temp": 20.0, "humidity": 55.0})
        result = t.transform([rec])
        assert result.records[0].readings["humidity"] == pytest.approx(55.0)

    def test_empty_input_returns_empty(self):
        t = JitterTransformer({"fields": {"temp": 1.0}})
        result = t.transform([])
        assert result.records == []
        assert result.errors == []
