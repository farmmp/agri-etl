"""Tests for RenameTransformer."""

import datetime
import pytest

from agri_etl.ingestion.base_reader import SensorRecord
from agri_etl.transform.rename_transformer import RenameTransformer


TS = datetime.datetime(2024, 6, 1, 12, 0, 0, tzinfo=datetime.timezone.utc)


def make_record(measurements: dict) -> SensorRecord:
    return SensorRecord(
        sensor_id="s1",
        timestamp=TS,
        measurements=measurements,
        metadata={},
    )


# ---------------------------------------------------------------------------
# Init / validation
# ---------------------------------------------------------------------------

class TestRenameTransformerInit:
    def test_missing_mappings_raises(self):
        with pytest.raises(ValueError, match="mappings"):
            RenameTransformer(config={})

    def test_empty_mappings_raises(self):
        with pytest.raises(ValueError, match="must not be empty"):
            RenameTransformer(config={"mappings": {}})

    def test_invalid_mappings_type_raises(self):
        with pytest.raises(TypeError, match="must be a dict"):
            RenameTransformer(config={"mappings": ["temp", "temperature"]})

    def test_non_string_key_raises(self):
        with pytest.raises(TypeError, match="strings"):
            RenameTransformer(config={"mappings": {1: "temperature"}})

    def test_valid_config_ok(self):
        t = RenameTransformer(config={"mappings": {"temp": "temperature"}})
        assert t is not None


# ---------------------------------------------------------------------------
# transform()
# ---------------------------------------------------------------------------

class TestRenameTransformerTransform:
    def setup_method(self):
        self.transformer = RenameTransformer(
            config={"mappings": {"temp": "temperature", "hum": "humidity"}}
        )

    def test_keys_are_renamed(self):
        record = make_record({"temp": 22.5, "hum": 60.0})
        result = self.transformer.transform(record)
        assert "temperature" in result.record.measurements
        assert "humidity" in result.record.measurements

    def test_values_are_preserved(self):
        record = make_record({"temp": 22.5, "hum": 60.0})
        result = self.transformer.transform(record)
        assert result.record.measurements["temperature"] == 22.5
        assert result.record.measurements["humidity"] == 60.0

    def test_unmapped_keys_are_kept(self):
        record = make_record({"temp": 22.5, "pressure": 1013.0})
        result = self.transformer.transform(record)
        assert "pressure" in result.record.measurements
        assert "temperature" in result.record.measurements

    def test_old_keys_removed(self):
        record = make_record({"temp": 22.5})
        result = self.transformer.transform(record)
        assert "temp" not in result.record.measurements

    def test_no_errors_returned(self):
        record = make_record({"temp": 22.5})
        result = self.transformer.transform(record)
        assert result.errors == []

    def test_metadata_preserved(self):
        record = SensorRecord(
            sensor_id="s2",
            timestamp=TS,
            measurements={"temp": 5.0},
            metadata={"source": "field_a"},
        )
        result = self.transformer.transform(record)
        assert result.record.metadata == {"source": "field_a"}
        assert result.record.sensor_id == "s2"
