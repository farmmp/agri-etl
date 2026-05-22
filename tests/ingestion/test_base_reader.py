"""Unit tests for BaseReader and SensorRecord."""

from datetime import datetime
from typing import Any, Dict, Iterator

import pytest

from agri_etl.ingestion.base_reader import BaseReader, SensorRecord


class _ConcreteReader(BaseReader):
    """Minimal concrete implementation for testing."""

    def connect(self) -> None:
        self._connected = True

    def disconnect(self) -> None:
        self._connected = False

    def read_batch(self, start: datetime, end: datetime) -> Iterator[SensorRecord]:
        yield SensorRecord(
            source_id="test-sensor",
            timestamp=datetime(2024, 1, 1, 12, 0),
            metrics={"temp": 22.5},
        )


class TestSensorRecord:
    def test_to_dict_contains_required_keys(self):
        record = SensorRecord(
            source_id="s1",
            timestamp=datetime(2024, 6, 1, 8, 0),
            metrics={"humidity": 65},
            station_id="station-A",
        )
        d = record.to_dict()
        assert d["source_id"] == "s1"
        assert d["station_id"] == "station-A"
        assert d["metrics"] == {"humidity": 65}
        assert "T" in d["timestamp"]


class TestBaseReader:
    def test_context_manager_sets_connected(self):
        reader = _ConcreteReader({})
        with reader as r:
            assert r._connected is True
        assert reader._connected is False

    def test_validate_config_raises_on_missing_keys(self):
        reader = _ConcreteReader({"key_a": 1})
        with pytest.raises(ValueError, match="key_b"):
            reader.validate_config(["key_a", "key_b"])

    def test_validate_config_passes_when_all_present(self):
        reader = _ConcreteReader({"a": 1, "b": 2})
        reader.validate_config(["a", "b"])  # should not raise

    def test_read_batch_yields_record(self):
        reader = _ConcreteReader({})
        reader.connect()
        records = list(reader.read_batch(datetime(2024, 1, 1), datetime(2024, 1, 2)))
        assert len(records) == 1
        assert records[0].source_id == "test-sensor"
