from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict

import pytest

from agri_etl.ingestion.base_reader import SensorRecord
from agri_etl.transform.resample_transformer import ResampleTransformer


def make_record(
    ts: datetime,
    readings: Dict[str, Any],
    sensor_id: str = "s1",
) -> SensorRecord:
    return SensorRecord(sensor_id=sensor_id, timestamp=ts, readings=readings)


T0 = datetime(2024, 1, 1, 0, 0, 0, tzinfo=timezone.utc)
T30 = datetime(2024, 1, 1, 0, 0, 30, tzinfo=timezone.utc)
T60 = datetime(2024, 1, 1, 0, 1, 0, tzinfo=timezone.utc)
T90 = datetime(2024, 1, 1, 0, 1, 30, tzinfo=timezone.utc)


class TestResampleTransformerInit:
    def test_missing_interval_raises(self):
        with pytest.raises(ValueError, match="interval_seconds"):
            ResampleTransformer({"fields": ["temp"]})

    def test_invalid_interval_zero_raises(self):
        with pytest.raises(ValueError, match="positive integer"):
            ResampleTransformer({"interval_seconds": 0, "fields": ["temp"]})

    def test_invalid_interval_negative_raises(self):
        with pytest.raises(ValueError, match="positive integer"):
            ResampleTransformer({"interval_seconds": -60, "fields": ["temp"]})

    def test_missing_fields_raises(self):
        with pytest.raises(ValueError, match="fields"):
            ResampleTransformer({"interval_seconds": 60})

    def test_empty_fields_raises(self):
        with pytest.raises(ValueError, match="non-empty list"):
            ResampleTransformer({"interval_seconds": 60, "fields": []})

    def test_unsupported_function_raises(self):
        with pytest.raises(ValueError, match="Unsupported function"):
            ResampleTransformer({"interval_seconds": 60, "fields": ["temp"], "function": "median"})

    def test_valid_config_accepted(self):
        t = ResampleTransformer({"interval_seconds": 60, "fields": ["temp"]})
        assert t is not None


class TestResampleTransformerTransform:
    def _make_transformer(self, func: str = "mean", interval: int = 60):
        return ResampleTransformer({"interval_seconds": interval, "fields": ["temp", "humidity"], "function": func})

    def test_two_records_same_bucket_mean(self):
        t = self._make_transformer("mean")
        records = [
            make_record(T0, {"temp": 10.0, "humidity": 80.0}),
            make_record(T30, {"temp": 20.0, "humidity": 60.0}),
        ]
        result = t.transform(records)
        assert len(result.records) == 1
        assert result.records[0].readings["temp"] == pytest.approx(15.0)
        assert result.records[0].readings["humidity"] == pytest.approx(70.0)

    def test_two_buckets_produced(self):
        t = self._make_transformer("mean")
        records = [
            make_record(T0, {"temp": 10.0}),
            make_record(T60, {"temp": 30.0}),
        ]
        result = t.transform(records)
        assert len(result.records) == 2

    def test_function_min(self):
        t = self._make_transformer("min")
        records = [
            make_record(T0, {"temp": 5.0}),
            make_record(T30, {"temp": 15.0}),
        ]
        result = t.transform(records)
        assert result.records[0].readings["temp"] == pytest.approx(5.0)

    def test_function_max(self):
        t = self._make_transformer("max")
        records = [
            make_record(T0, {"temp": 5.0}),
            make_record(T30, {"temp": 15.0}),
        ]
        result = t.transform(records)
        assert result.records[0].readings["temp"] == pytest.approx(15.0)

    def test_function_sum(self):
        t = self._make_transformer("sum")
        records = [
            make_record(T0, {"temp": 5.0}),
            make_record(T30, {"temp": 15.0}),
        ]
        result = t.transform(records)
        assert result.records[0].readings["temp"] == pytest.approx(20.0)

    def test_function_first(self):
        t = self._make_transformer("first")
        records = [
            make_record(T0, {"temp": 5.0}),
            make_record(T30, {"temp": 15.0}),
        ]
        result = t.transform(records)
        assert result.records[0].readings["temp"] == pytest.approx(5.0)

    def test_function_last(self):
        t = self._make_transformer("last")
        records = [
            make_record(T0, {"temp": 5.0}),
            make_record(T30, {"temp": 15.0}),
        ]
        result = t.transform(records)
        assert result.records[0].readings["temp"] == pytest.approx(15.0)

    def test_missing_field_skipped_no_error(self):
        t = self._make_transformer("mean")
        records = [make_record(T0, {"temp": 10.0})]
        result = t.transform(records)
        assert "humidity" not in result.records[0].readings
        assert result.errors == []

    def test_resampled_metadata_flag(self):
        t = self._make_transformer("mean")
        records = [make_record(T0, {"temp": 10.0})]
        result = t.transform(records)
        assert result.records[0].metadata["resampled"] is True
        assert result.records[0].metadata["interval_seconds"] == 60

    def test_empty_input_returns_empty(self):
        t = self._make_transformer("mean")
        result = t.transform([])
        assert result.records == []
        assert result.errors == []

    def test_multiple_sensors_bucketed_separately(self):
        t = self._make_transformer("mean")
        records = [
            make_record(T0, {"temp": 10.0}, sensor_id="s1"),
            make_record(T0, {"temp": 20.0}, sensor_id="s2"),
        ]
        result = t.transform(records)
        assert len(result.records) == 2
        temps = {r.sensor_id: r.readings["temp"] for r in result.records}
        assert temps["s1"] == pytest.approx(10.0)
        assert temps["s2"] == pytest.approx(20.0)
