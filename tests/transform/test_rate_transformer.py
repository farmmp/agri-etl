"""Tests for RateTransformer."""
from __future__ import annotations

import pytest
from datetime import datetime, timezone, timedelta
from agri_etl.ingestion.base_reader import SensorRecord
from agri_etl.transform.rate_transformer import RateTransformer


def make_record(ts_offset_s: float, **readings) -> SensorRecord:
    base = datetime(2024, 1, 1, tzinfo=timezone.utc)
    return SensorRecord(
        sensor_id="s1",
        timestamp=base + timedelta(seconds=ts_offset_s),
        readings=readings,
    )


class TestRateTransformerInit:
    def test_missing_fields_raises(self):
        with pytest.raises(ValueError, match="fields"):
            RateTransformer({})

    def test_empty_fields_raises(self):
        with pytest.raises(ValueError, match="empty"):
            RateTransformer({"fields": []})

    def test_invalid_fields_type_raises(self):
        with pytest.raises(TypeError, match="list"):
            RateTransformer({"fields": "temp"})

    def test_non_str_field_entry_raises(self):
        with pytest.raises(TypeError, match="str"):
            RateTransformer({"fields": [1, 2]})

    def test_valid_config_accepted(self):
        t = RateTransformer({"fields": ["temp"]})
        assert t is not None


class TestRateTransformerTransform:
    def test_first_record_dropped_by_default(self):
        t = RateTransformer({"fields": ["temp"]})
        result = t.transform([make_record(0, temp=10.0)])
        assert result.records == []
        assert result.errors == []

    def test_first_record_kept_when_drop_first_false(self):
        t = RateTransformer({"fields": ["temp"], "drop_first": False})
        result = t.transform([make_record(0, temp=10.0)])
        assert len(result.records) == 1

    def test_rate_computed_correctly(self):
        t = RateTransformer({"fields": ["temp"]})
        records = [
            make_record(0, temp=10.0),
            make_record(10, temp=20.0),
        ]
        result = t.transform(records)
        assert len(result.records) == 1
        assert result.records[0].readings["temp_rate"] == pytest.approx(1.0)

    def test_custom_suffix(self):
        t = RateTransformer({"fields": ["humidity"], "output_suffix": "_d"})
        records = [
            make_record(0, humidity=50.0),
            make_record(5, humidity=55.0),
        ]
        result = t.transform(records)
        assert "humidity_d" in result.records[0].readings

    def test_missing_field_produces_error(self):
        t = RateTransformer({"fields": ["temp"]})
        records = [
            make_record(0, temp=10.0),
            make_record(10, humidity=50.0),  # no 'temp'
        ]
        result = t.transform(records)
        assert len(result.errors) == 1
        assert "temp" in result.errors[0]

    def test_non_positive_elapsed_skipped_with_error(self):
        t = RateTransformer({"fields": ["temp"]})
        base = datetime(2024, 1, 1, tzinfo=timezone.utc)
        r1 = SensorRecord(sensor_id="s1", timestamp=base, readings={"temp": 10.0})
        r2 = SensorRecord(sensor_id="s1", timestamp=base, readings={"temp": 20.0})
        result = t.transform([r1, r2])
        assert len(result.errors) == 1
        assert len(result.records) == 0

    def test_state_persists_across_calls(self):
        t = RateTransformer({"fields": ["temp"]})
        t.transform([make_record(0, temp=0.0)])
        result = t.transform([make_record(10, temp=10.0)])
        assert result.records[0].readings["temp_rate"] == pytest.approx(1.0)

    def test_original_readings_preserved(self):
        t = RateTransformer({"fields": ["temp"]})
        records = [
            make_record(0, temp=5.0, humidity=80.0),
            make_record(5, temp=10.0, humidity=85.0),
        ]
        result = t.transform(records)
        r = result.records[0]
        assert r.readings["temp"] == 10.0
        assert r.readings["humidity"] == 85.0
