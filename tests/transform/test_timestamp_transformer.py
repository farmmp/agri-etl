"""Tests for TimestampTransformer."""

from __future__ import annotations

from datetime import datetime, timezone, timedelta

import pytest

from agri_etl.ingestion.base_reader import SensorRecord
from agri_etl.transform.timestamp_transformer import TimestampTransformer


def make_record(
    ts: datetime,
    sensor_id: str = "s1",
) -> SensorRecord:
    return SensorRecord(sensor_id=sensor_id, timestamp=ts, readings={"temp": 20.0})


# ---------------------------------------------------------------------------
# Init / validation
# ---------------------------------------------------------------------------

class TestTimestampTransformerInit:
    def test_invalid_to_utc_raises(self):
        with pytest.raises(ValueError, match="to_utc"):
            TimestampTransformer(config={"to_utc": "yes"})

    def test_invalid_offset_raises(self):
        with pytest.raises(ValueError, match="offset_seconds"):
            TimestampTransformer(config={"offset_seconds": "bad"})

    def test_defaults_accepted(self):
        t = TimestampTransformer(config={})
        assert t.config.get("to_utc", True) is True
        assert t.config.get("offset_seconds", 0) == 0


# ---------------------------------------------------------------------------
# Behaviour
# ---------------------------------------------------------------------------

class TestTimestampTransformerTransform:
    def test_naive_timestamp_gets_utc_tzinfo(self):
        naive_ts = datetime(2024, 6, 1, 12, 0, 0)  # no tzinfo
        record = make_record(naive_ts)
        t = TimestampTransformer(config={"to_utc": True})
        result = t.transform([record])
        assert result.records[0].timestamp.tzinfo == timezone.utc

    def test_aware_timestamp_converted_to_utc(self):
        tz_plus2 = timezone(timedelta(hours=2))
        aware_ts = datetime(2024, 6, 1, 14, 0, 0, tzinfo=tz_plus2)
        record = make_record(aware_ts)
        t = TimestampTransformer(config={"to_utc": True})
        result = t.transform([record])
        out_ts = result.records[0].timestamp
        assert out_ts.tzinfo == timezone.utc
        assert out_ts.hour == 12  # 14:00+02:00 == 12:00 UTC

    def test_offset_seconds_applied(self):
        naive_ts = datetime(2024, 6, 1, 12, 0, 0)
        record = make_record(naive_ts)
        t = TimestampTransformer(config={"to_utc": True, "offset_seconds": 3600})
        result = t.transform([record])
        assert result.records[0].timestamp.hour == 13

    def test_negative_offset(self):
        naive_ts = datetime(2024, 6, 1, 12, 0, 0)
        record = make_record(naive_ts)
        t = TimestampTransformer(config={"to_utc": True, "offset_seconds": -1800})
        result = t.transform([record])
        assert result.records[0].timestamp.minute == 30
        assert result.records[0].timestamp.hour == 11

    def test_to_utc_false_leaves_tzinfo_unchanged(self):
        naive_ts = datetime(2024, 6, 1, 12, 0, 0)
        record = make_record(naive_ts)
        t = TimestampTransformer(config={"to_utc": False})
        result = t.transform([record])
        assert result.records[0].timestamp.tzinfo is None

    def test_readings_and_metadata_preserved(self):
        naive_ts = datetime(2024, 6, 1, 12, 0, 0)
        record = SensorRecord(
            sensor_id="sensor-42",
            timestamp=naive_ts,
            readings={"humidity": 55.5},
            metadata={"location": "field-A"},
        )
        t = TimestampTransformer(config={})
        result = t.transform([record])
        out = result.records[0]
        assert out.sensor_id == "sensor-42"
        assert out.readings == {"humidity": 55.5}
        assert out.metadata == {"location": "field-A"}

    def test_empty_input_returns_empty(self):
        t = TimestampTransformer(config={})
        result = t.transform([])
        assert result.records == []
        assert result.dropped == 0

    def test_dropped_count_zero_on_success(self):
        records = [make_record(datetime(2024, 1, i + 1, 0, 0)) for i in range(5)]
        t = TimestampTransformer(config={})
        result = t.transform(records)
        assert result.dropped == 0
        assert len(result.records) == 5
