"""Tests for NormalizeTransformer."""
from __future__ import annotations

import datetime
import pytest

from agri_etl.ingestion.base_reader import SensorRecord
from agri_etl.transform.normalize_transformer import NormalizeTransformer

TS = datetime.datetime(2024, 1, 1, 12, 0, 0, tzinfo=datetime.timezone.utc)


def make_record(readings: dict) -> SensorRecord:
    return SensorRecord(sensor_id="s1", timestamp=TS, readings=readings)


class TestNormalizeTransformerInit:
    def test_missing_bounds_raises(self):
        with pytest.raises(ValueError, match="'bounds'"):
            NormalizeTransformer({})

    def test_empty_bounds_raises(self):
        with pytest.raises(ValueError, match="non-empty dict"):
            NormalizeTransformer({"bounds": {}})

    def test_invalid_bounds_type_raises(self):
        with pytest.raises(ValueError, match="non-empty dict"):
            NormalizeTransformer({"bounds": "bad"})

    def test_missing_min_key_raises(self):
        with pytest.raises(ValueError, match="'min' and 'max'"):
            NormalizeTransformer({"bounds": {"temp": {"min": 0}}})

    def test_min_gte_max_raises(self):
        with pytest.raises(ValueError, match="strictly less than"):
            NormalizeTransformer({"bounds": {"temp": {"min": 10, "max": 10}}})

    def test_invalid_clip_type_raises(self):
        with pytest.raises(ValueError, match="'clip' must be a boolean"):
            NormalizeTransformer({"bounds": {"temp": {"min": 0, "max": 100}}, "clip": "yes"})

    def test_valid_config_accepted(self):
        t = NormalizeTransformer({"bounds": {"temp": {"min": 0, "max": 100}}})
        assert t is not None


class TestNormalizeTransformerTransform:
    def _make_transformer(self, clip=False):
        return NormalizeTransformer({
            "bounds": {
                "temp": {"min": 0.0, "max": 100.0},
                "humidity": {"min": 20.0, "max": 80.0},
            },
            "clip": clip,
        })

    def test_midpoint_normalizes_to_half(self):
        t = self._make_transformer()
        result = t.transform(make_record({"temp": 50.0}))
        assert result.record.readings["temp"] == pytest.approx(0.5)

    def test_min_value_normalizes_to_zero(self):
        t = self._make_transformer()
        result = t.transform(make_record({"temp": 0.0}))
        assert result.record.readings["temp"] == pytest.approx(0.0)

    def test_max_value_normalizes_to_one(self):
        t = self._make_transformer()
        result = t.transform(make_record({"temp": 100.0}))
        assert result.record.readings["temp"] == pytest.approx(1.0)

    def test_multiple_fields_normalized(self):
        t = self._make_transformer()
        result = t.transform(make_record({"temp": 25.0, "humidity": 50.0}))
        assert result.record.readings["temp"] == pytest.approx(0.25)
        assert result.record.readings["humidity"] == pytest.approx(0.5)

    def test_out_of_range_without_clip(self):
        t = self._make_transformer(clip=False)
        result = t.transform(make_record({"temp": 150.0}))
        assert result.record.readings["temp"] == pytest.approx(1.5)

    def test_out_of_range_with_clip(self):
        t = self._make_transformer(clip=True)
        result = t.transform(make_record({"temp": 150.0}))
        assert result.record.readings["temp"] == pytest.approx(1.0)

    def test_below_range_with_clip(self):
        t = self._make_transformer(clip=True)
        result = t.transform(make_record({"temp": -10.0}))
        assert result.record.readings["temp"] == pytest.approx(0.0)

    def test_non_numeric_field_adds_error(self):
        t = self._make_transformer()
        result = t.transform(make_record({"temp": "hot"}))
        assert len(result.errors) == 1
        assert "temp" in result.errors[0]
        assert result.dropped is False

    def test_missing_field_is_skipped_silently(self):
        t = self._make_transformer()
        result = t.transform(make_record({"humidity": 50.0}))
        assert "temp" not in result.record.readings
        assert result.errors == []

    def test_metadata_and_sensor_id_preserved(self):
        t = self._make_transformer()
        record = SensorRecord("sensor-99", TS, {"temp": 50.0}, {"station": "A"})
        result = t.transform(record)
        assert result.record.sensor_id == "sensor-99"
        assert result.record.meta == {"station": "A"}
