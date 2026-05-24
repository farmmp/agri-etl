"""Tests for EwmaTransformer."""

import pytest
from datetime import datetime, timezone

from agri_etl.ingestion.base_reader import SensorRecord
from agri_etl.transform.ewma_transformer import EwmaTransformer


TS = datetime(2024, 6, 1, 12, 0, 0, tzinfo=timezone.utc)


def make_record(readings, sensor_id="s1"):
    return SensorRecord(sensor_id=sensor_id, timestamp=TS, readings=readings, meta={})


# ---------------------------------------------------------------------------
# Init / validation
# ---------------------------------------------------------------------------

class TestEwmaTransformerInit:
    def test_missing_fields_raises(self):
        with pytest.raises(ValueError, match="requires 'fields'"):
            EwmaTransformer({})

    def test_empty_fields_raises(self):
        with pytest.raises(ValueError, match="non-empty dict"):
            EwmaTransformer({"fields": {}})

    def test_invalid_fields_type_raises(self):
        with pytest.raises(ValueError, match="non-empty dict"):
            EwmaTransformer({"fields": ["temp"]})

    def test_alpha_zero_raises(self):
        with pytest.raises(ValueError, match="Alpha for field 'temp'"):
            EwmaTransformer({"fields": {"temp": 0}})

    def test_alpha_above_one_raises(self):
        with pytest.raises(ValueError, match="Alpha for field 'temp'"):
            EwmaTransformer({"fields": {"temp": 1.5}})

    def test_alpha_one_accepted(self):
        t = EwmaTransformer({"fields": {"temp": 1.0}})
        assert t is not None

    def test_valid_config_accepted(self):
        t = EwmaTransformer({"fields": {"temp": 0.3, "humidity": 0.5}})
        assert t is not None


# ---------------------------------------------------------------------------
# Transform behaviour
# ---------------------------------------------------------------------------

class TestEwmaTransformerTransform:
    def test_first_record_equals_raw_value(self):
        t = EwmaTransformer({"fields": {"temp": 0.5}})
        result = t.transform([make_record({"temp": 20.0})])
        assert result.records[0].readings["temp_ewma"] == pytest.approx(20.0)

    def test_smoothing_applied_on_second_record(self):
        t = EwmaTransformer({"fields": {"temp": 0.5}})
        t.transform([make_record({"temp": 20.0})])
        result = t.transform([make_record({"temp": 30.0})])
        # 0.5 * 30 + 0.5 * 20 = 25
        assert result.records[0].readings["temp_ewma"] == pytest.approx(25.0)

    def test_state_persists_across_calls(self):
        t = EwmaTransformer({"fields": {"temp": 0.2}})
        records = [make_record({"temp": float(v)}) for v in [10, 20, 30]]
        result = t.transform(records)
        # manual: s0=10, s1=0.2*20+0.8*10=12, s2=0.2*30+0.8*12=15.6
        readings = [r.readings["temp_ewma"] for r in result.records]
        assert readings[0] == pytest.approx(10.0)
        assert readings[1] == pytest.approx(12.0)
        assert readings[2] == pytest.approx(15.6)

    def test_custom_suffix(self):
        t = EwmaTransformer({"fields": {"temp": 0.5}, "output_suffix": "_smooth"})
        result = t.transform([make_record({"temp": 10.0})])
        assert "temp_smooth" in result.records[0].readings

    def test_empty_suffix_overwrites_in_place(self):
        t = EwmaTransformer({"fields": {"temp": 1.0}, "output_suffix": ""})
        result = t.transform([make_record({"temp": 42.0})])
        assert result.records[0].readings["temp"] == pytest.approx(42.0)

    def test_missing_field_skipped_silently(self):
        t = EwmaTransformer({"fields": {"temp": 0.5}})
        result = t.transform([make_record({"humidity": 55.0})])
        assert result.errors == []
        assert "temp_ewma" not in result.records[0].readings

    def test_non_numeric_value_recorded_as_error(self):
        t = EwmaTransformer({"fields": {"temp": 0.5}})
        result = t.transform([make_record({"temp": "hot"})])
        assert len(result.errors) == 1
        assert "temp" in result.errors[0]

    def test_empty_batch_returns_empty(self):
        t = EwmaTransformer({"fields": {"temp": 0.5}})
        result = t.transform([])
        assert result.records == []
        assert result.errors == []
