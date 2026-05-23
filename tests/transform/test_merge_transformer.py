import pytest
from datetime import datetime, timezone

from agri_etl.ingestion.base_reader import SensorRecord
from agri_etl.transform.merge_transformer import MergeTransformer


TS = datetime(2024, 6, 1, 12, 0, 0, tzinfo=timezone.utc)


def make_record(readings=None):
    return SensorRecord(
        sensor_id="s1",
        timestamp=TS,
        readings=readings or {"a": 1, "b": 2, "c": 3},
    )


class TestMergeTransformerInit:
    def test_missing_merges_raises(self):
        with pytest.raises(ValueError, match="'merges'"):
            MergeTransformer({})

    def test_empty_merges_raises(self):
        with pytest.raises(ValueError, match="must not be empty"):
            MergeTransformer({"merges": {}})

    def test_invalid_merges_type_raises(self):
        with pytest.raises(TypeError, match="must be a dict"):
            MergeTransformer({"merges": ["a", "b"]})

    def test_invalid_sources_type_raises(self):
        with pytest.raises(ValueError, match="non-empty list"):
            MergeTransformer({"merges": {"ab": "a"}})

    def test_empty_sources_raises(self):
        with pytest.raises(ValueError, match="non-empty list"):
            MergeTransformer({"merges": {"ab": []}})

    def test_invalid_separator_raises(self):
        with pytest.raises(TypeError, match="'separator' must be a string"):
            MergeTransformer({"merges": {"ab": ["a", "b"]}, "separator": 42})

    def test_invalid_drop_sources_raises(self):
        with pytest.raises(TypeError, match="'drop_sources' must be a bool"):
            MergeTransformer({"merges": {"ab": ["a", "b"]}, "drop_sources": "yes"})

    def test_valid_config_accepted(self):
        t = MergeTransformer({"merges": {"ab": ["a", "b"]}})
        assert t is not None


class TestMergeTransformerTransform:
    def test_merge_creates_new_field(self):
        t = MergeTransformer({"merges": {"ab": ["a", "b"]}})
        result = t.transform([make_record()])
        assert result.records[0].readings["ab"] == "1,2"

    def test_custom_separator(self):
        t = MergeTransformer({"merges": {"ab": ["a", "b"]}, "separator": "|" })
        result = t.transform([make_record()])
        assert result.records[0].readings["ab"] == "1|2"

    def test_drop_sources_removes_fields(self):
        t = MergeTransformer({"merges": {"ab": ["a", "b"]}, "drop_sources": True})
        result = t.transform([make_record()])
        readings = result.records[0].readings
        assert "ab" in readings
        assert "a" not in readings
        assert "b" not in readings
        assert "c" in readings

    def test_missing_source_field_skipped(self):
        t = MergeTransformer({"merges": {"xz": ["x", "z"]}})
        result = t.transform([make_record()])
        assert result.records[0].readings["xz"] == ""

    def test_no_errors_on_valid_records(self):
        t = MergeTransformer({"merges": {"ab": ["a", "b"]}})
        result = t.transform([make_record(), make_record()])
        assert len(result.errors) == 0
        assert len(result.records) == 2

    def test_empty_input_returns_empty(self):
        t = MergeTransformer({"merges": {"ab": ["a", "b"]}})
        result = t.transform([])
        assert result.records == []
        assert result.errors == []
