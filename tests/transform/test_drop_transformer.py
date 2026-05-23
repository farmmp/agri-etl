"""Tests for DropTransformer."""

import datetime
import pytest

from agri_etl.ingestion.base_reader import SensorRecord
from agri_etl.transform.drop_transformer import DropTransformer


TS = datetime.datetime(2024, 6, 1, 12, 0, 0, tzinfo=datetime.timezone.utc)


def make_record(readings: dict) -> SensorRecord:
    return SensorRecord(
        sensor_id="s1",
        timestamp=TS,
        readings=readings,
        metadata={},
    )


class TestDropTransformerInit:
    def test_missing_fields_raises(self):
        with pytest.raises(KeyError, match="fields"):
            DropTransformer(config={})

    def test_empty_fields_raises(self):
        with pytest.raises(ValueError, match="empty"):
            DropTransformer(config={"fields": []})

    def test_invalid_fields_type_raises(self):
        with pytest.raises(TypeError, match="list"):
            DropTransformer(config={"fields": "temperature"})

    def test_non_string_field_raises(self):
        with pytest.raises(TypeError, match="string"):
            DropTransformer(config={"fields": ["temp", 42]})

    def test_valid_config_ok(self):
        t = DropTransformer(config={"fields": ["humidity"]})
        assert t is not None


class TestDropTransformerTransform:
    def test_drops_specified_field(self):
        t = DropTransformer(config={"fields": ["humidity"]})
        record = make_record({"temperature": 22.5, "humidity": 60.0})
        result = t.transform(record)
        assert "humidity" not in result.record.readings
        assert "temperature" in result.record.readings

    def test_drops_multiple_fields(self):
        t = DropTransformer(config={"fields": ["humidity", "pressure"]})
        record = make_record({"temperature": 22.5, "humidity": 60.0, "pressure": 1013.0})
        result = t.transform(record)
        assert set(result.record.readings.keys()) == {"temperature"}

    def test_missing_field_is_ignored(self):
        t = DropTransformer(config={"fields": ["nonexistent"]})
        record = make_record({"temperature": 22.5})
        result = t.transform(record)
        assert "temperature" in result.record.readings
        assert result.dropped is False

    def test_notes_report_dropped_fields(self):
        t = DropTransformer(config={"fields": ["humidity"]})
        record = make_record({"temperature": 22.5, "humidity": 60.0})
        result = t.transform(record)
        assert "humidity" in result.notes

    def test_notes_when_nothing_dropped(self):
        t = DropTransformer(config={"fields": ["nonexistent"]})
        record = make_record({"temperature": 22.5})
        result = t.transform(record)
        assert "No fields dropped" in result.notes

    def test_original_record_unchanged(self):
        t = DropTransformer(config={"fields": ["humidity"]})
        original_readings = {"temperature": 22.5, "humidity": 60.0}
        record = make_record(original_readings)
        t.transform(record)
        assert "humidity" in record.readings

    def test_result_not_dropped(self):
        t = DropTransformer(config={"fields": ["humidity"]})
        record = make_record({"temperature": 22.5, "humidity": 60.0})
        result = t.transform(record)
        assert result.dropped is False
