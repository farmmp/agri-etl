"""Tests for DeduplicateTransformer."""
from __future__ import annotations

import datetime
import pytest

from agri_etl.ingestion.base_reader import SensorRecord
from agri_etl.transform.deduplicate_transformer import DeduplicateTransformer

TS = datetime.datetime(2024, 6, 1, 12, 0, 0, tzinfo=datetime.timezone.utc)
TS2 = TS + datetime.timedelta(seconds=30)


def make_record(sensor_id: str = "s1", ts=TS) -> SensorRecord:
    return SensorRecord(sensor_id=sensor_id, timestamp=ts, readings={"temp": 20.0})


class TestDeduplicateTransformerInit:
    def test_default_config_accepted(self):
        t = DeduplicateTransformer(config={})
        assert t is not None

    def test_invalid_window_size_raises(self):
        with pytest.raises(ValueError, match="window_size"):
            DeduplicateTransformer(config={"window_size": 0})

    def test_non_int_window_size_raises(self):
        with pytest.raises(ValueError, match="window_size"):
            DeduplicateTransformer(config={"window_size": "large"})

    def test_custom_window_size_accepted(self):
        t = DeduplicateTransformer(config={"window_size": 50})
        assert t._window_size == 50


class TestDeduplicateTransformerBehaviour:
    def setup_method(self):
        self.t = DeduplicateTransformer(config={})

    def test_first_record_passes(self):
        result = self.t.transform(make_record())
        assert not result.dropped
        assert result.record is not None

    def test_duplicate_record_dropped(self):
        self.t.transform(make_record())
        result = self.t.transform(make_record())
        assert result.dropped
        assert "Duplicate" in result.error

    def test_different_timestamp_passes(self):
        self.t.transform(make_record(ts=TS))
        result = self.t.transform(make_record(ts=TS2))
        assert not result.dropped

    def test_different_sensor_id_passes(self):
        self.t.transform(make_record(sensor_id="s1"))
        result = self.t.transform(make_record(sensor_id="s2"))
        assert not result.dropped

    def test_window_eviction_allows_reinsert(self):
        """After window is full the oldest fingerprint is evicted."""
        t = DeduplicateTransformer(config={"window_size": 2})
        r0 = make_record(sensor_id="s0", ts=TS)
        r1 = make_record(sensor_id="s1", ts=TS)
        r2 = make_record(sensor_id="s2", ts=TS)

        t.transform(r0)  # seen: {s0}
        t.transform(r1)  # seen: {s0, s1}  — window full
        t.transform(r2)  # s0 evicted; seen: {s1, s2}

        # s0 should now be accepted again
        result = t.transform(r0)
        assert not result.dropped
