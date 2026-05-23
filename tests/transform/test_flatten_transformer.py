import datetime
import pytest

from agri_etl.ingestion.base_reader import SensorRecord
from agri_etl.transform.flatten_transformer import FlattenTransformer


TS = datetime.datetime(2024, 6, 1, 12, 0, 0)


def make_record(readings: dict) -> SensorRecord:
    return SensorRecord(sensor_id="s1", timestamp=TS, readings=readings)


# ---------------------------------------------------------------------------
# Init / validation
# ---------------------------------------------------------------------------

class TestFlattenTransformerInit:
    def test_missing_fields_raises(self):
        with pytest.raises(ValueError, match="requires 'fields'"):
            FlattenTransformer({})

    def test_empty_fields_raises(self):
        with pytest.raises(ValueError, match="non-empty list"):
            FlattenTransformer({"fields": []})

    def test_invalid_fields_type_raises(self):
        with pytest.raises(ValueError, match="non-empty list"):
            FlattenTransformer({"fields": "temperature"})

    def test_non_string_field_raises(self):
        with pytest.raises(ValueError, match="must be a string"):
            FlattenTransformer({"fields": [1, 2]})

    def test_invalid_separator_raises(self):
        with pytest.raises(ValueError, match="'separator' must be a string"):
            FlattenTransformer({"fields": ["nested"], "separator": 99})

    def test_invalid_drop_parent_raises(self):
        with pytest.raises(ValueError, match="'drop_parent' must be a boolean"):
            FlattenTransformer({"fields": ["nested"], "drop_parent": "yes"})

    def test_valid_config_accepted(self):
        t = FlattenTransformer({"fields": ["nested"]})
        assert t is not None


# ---------------------------------------------------------------------------
# Transform behaviour
# ---------------------------------------------------------------------------

class TestFlattenTransformerTransform:
    def test_nested_dict_flattened(self):
        t = FlattenTransformer({"fields": ["env"]})
        record = make_record({"env": {"temp": 22.0, "humidity": 80.0}})
        result = t.transform([record])
        assert len(result.passed) == 1
        r = result.passed[0]
        assert r.readings["env_temp"] == 22.0
        assert r.readings["env_humidity"] == 80.0
        assert "env" not in r.readings

    def test_custom_separator(self):
        t = FlattenTransformer({"fields": ["env"], "separator": "."})
        record = make_record({"env": {"temp": 5.0}})
        result = t.transform([record])
        assert "env.temp" in result.passed[0].readings

    def test_drop_parent_false_keeps_original(self):
        t = FlattenTransformer({"fields": ["env"], "drop_parent": False})
        record = make_record({"env": {"temp": 5.0}})
        result = t.transform([record])
        assert "env" in result.passed[0].readings
        assert "env_temp" in result.passed[0].readings

    def test_non_dict_field_skipped(self):
        t = FlattenTransformer({"fields": ["temperature"]})
        record = make_record({"temperature": 25.0})
        result = t.transform([record])
        assert result.passed[0].readings["temperature"] == 25.0

    def test_missing_field_skipped_gracefully(self):
        t = FlattenTransformer({"fields": ["missing"]})
        record = make_record({"temperature": 25.0})
        result = t.transform([record])
        assert len(result.passed) == 1
        assert len(result.failed) == 0

    def test_multiple_fields_flattened(self):
        t = FlattenTransformer({"fields": ["env", "soil"]})
        record = make_record({"env": {"temp": 20.0}, "soil": {"moisture": 0.4}})
        result = t.transform([record])
        r = result.passed[0]
        assert "env_temp" in r.readings
        assert "soil_moisture" in r.readings

    def test_empty_input_returns_empty(self):
        t = FlattenTransformer({"fields": ["env"]})
        result = t.transform([])
        assert result.passed == []
        assert result.failed == []
