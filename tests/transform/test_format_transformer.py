import pytest
from datetime import datetime, timezone

from agri_etl.ingestion.base_reader import SensorRecord
from agri_etl.transform.format_transformer import FormatTransformer


TS = datetime(2024, 6, 1, 12, 0, 0, tzinfo=timezone.utc)


def make_record(readings: dict) -> SensorRecord:
    return SensorRecord(
        sensor_id="s1",
        timestamp=TS,
        readings=readings,
        meta={},
    )


class TestFormatTransformerInit:
    def test_missing_formats_raises(self):
        with pytest.raises(ValueError, match="'formats'"):
            FormatTransformer({})

    def test_empty_formats_raises(self):
        with pytest.raises(ValueError, match="must not be empty"):
            FormatTransformer({"formats": {}})

    def test_invalid_formats_type_raises(self):
        with pytest.raises(TypeError, match="must be a dict"):
            FormatTransformer({"formats": ["upper"]})

    def test_unsupported_operation_raises(self):
        with pytest.raises(ValueError, match="Unsupported format operation"):
            FormatTransformer({"formats": {"label": "capitalize"}})

    def test_valid_config_accepted(self):
        t = FormatTransformer({"formats": {"label": "upper"}})
        assert t is not None


class TestFormatTransformerTransform:
    def test_upper(self):
        t = FormatTransformer({"formats": {"label": "upper"}})
        rec = make_record({"label": "hello world"})
        result = t.transform([rec])
        assert result.records[0].readings["label"] == "HELLO WORLD"
        assert result.errors == []

    def test_lower(self):
        t = FormatTransformer({"formats": {"label": "lower"}})
        rec = make_record({"label": "SENSOR_A"})
        result = t.transform([rec])
        assert result.records[0].readings["label"] == "sensor_a"

    def test_strip(self):
        t = FormatTransformer({"formats": {"label": "strip"}})
        rec = make_record({"label": "  padded  "})
        result = t.transform([rec])
        assert result.records[0].readings["label"] == "padded"

    def test_title(self):
        t = FormatTransformer({"formats": {"label": "title"}})
        rec = make_record({"label": "soil moisture sensor"})
        result = t.transform([rec])
        assert result.records[0].readings["label"] == "Soil Moisture Sensor"

    def test_non_string_field_skipped_with_error(self):
        t = FormatTransformer({"formats": {"value": "upper"}})
        rec = make_record({"value": 42.0})
        result = t.transform([rec])
        assert result.records[0].readings["value"] == 42.0
        assert len(result.errors) == 1
        assert "not a string" in result.errors[0]

    def test_missing_field_silently_skipped(self):
        t = FormatTransformer({"formats": {"absent": "upper"}})
        rec = make_record({"label": "foo"})
        result = t.transform([rec])
        assert result.records[0].readings["label"] == "foo"
        assert result.errors == []

    def test_multiple_fields(self):
        t = FormatTransformer({"formats": {"a": "upper", "b": "lower"}})
        rec = make_record({"a": "hello", "b": "WORLD"})
        result = t.transform([rec])
        assert result.records[0].readings["a"] == "HELLO"
        assert result.records[0].readings["b"] == "world"

    def test_empty_batch(self):
        t = FormatTransformer({"formats": {"label": "upper"}})
        result = t.transform([])
        assert result.records == []
        assert result.errors == []

    def test_original_record_not_mutated(self):
        t = FormatTransformer({"formats": {"label": "upper"}})
        rec = make_record({"label": "original"})
        t.transform([rec])
        assert rec.readings["label"] == "original"
