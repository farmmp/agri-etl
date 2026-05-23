"""Tests for TagTransformer."""
from __future__ import annotations

import datetime
import pytest

from agri_etl.ingestion.base_reader import SensorRecord
from agri_etl.transform.tag_transformer import TagTransformer

TS = datetime.datetime(2024, 6, 1, tzinfo=datetime.timezone.utc)


def make_record(metadata: dict | None = None) -> SensorRecord:
    return SensorRecord(
        sensor_id="s1",
        timestamp=TS,
        readings={"temp": 20.0},
        metadata=metadata or {},
    )


class TestTagTransformerInit:
    def test_missing_tags_raises(self):
        with pytest.raises(ValueError, match="requires 'tags'"):
            TagTransformer({})

    def test_empty_tags_raises(self):
        with pytest.raises(ValueError, match="non-empty dict"):
            TagTransformer({"tags": {}})

    def test_invalid_tags_type_raises(self):
        with pytest.raises(ValueError, match="non-empty dict"):
            TagTransformer({"tags": ["region"]})

    def test_non_string_key_raises(self):
        with pytest.raises(ValueError, match="key must be a string"):
            TagTransformer({"tags": {1: "val"}})

    def test_invalid_value_type_raises(self):
        with pytest.raises(ValueError, match="str/int/float/bool"):
            TagTransformer({"tags": {"region": ["a", "b"]}})

    def test_valid_config_accepted(self):
        t = TagTransformer({"tags": {"region": "north", "version": 2}})
        assert t is not None


class TestTagTransformerTransform:
    def test_tags_injected_into_empty_metadata(self):
        t = TagTransformer({"tags": {"region": "north"}})
        result = t.transform([make_record()])
        assert result.errors == []
        assert result.records[0].metadata["region"] == "north"

    def test_existing_key_not_overwritten_by_default(self):
        t = TagTransformer({"tags": {"region": "south"}})
        result = t.transform([make_record({"region": "north"})])
        assert result.records[0].metadata["region"] == "north"

    def test_overwrite_true_replaces_existing(self):
        t = TagTransformer({"tags": {"region": "south"}, "overwrite": True})
        result = t.transform([make_record({"region": "north"})])
        assert result.records[0].metadata["region"] == "south"

    def test_multiple_tags_all_injected(self):
        t = TagTransformer({"tags": {"region": "east", "env": "prod", "v": 3}})
        result = t.transform([make_record()])
        md = result.records[0].metadata
        assert md["region"] == "east"
        assert md["env"] == "prod"
        assert md["v"] == 3

    def test_original_metadata_not_mutated(self):
        t = TagTransformer({"tags": {"region": "west"}})
        original = make_record({"existing": "val"})
        t.transform([original])
        assert "region" not in original.metadata

    def test_empty_records_returns_empty(self):
        t = TagTransformer({"tags": {"region": "north"}})
        result = t.transform([])
        assert result.records == []
        assert result.errors == []
