"""Tests for SchemaTransformer."""
from __future__ import annotations

import datetime
import pytest

from agri_etl.ingestion.base_reader import SensorRecord
from agri_etl.transform.schema_transformer import SchemaTransformer

TS = datetime.datetime(2024, 6, 1, 12, 0, 0, tzinfo=datetime.timezone.utc)


def make_record(readings: dict) -> SensorRecord:
    return SensorRecord(sensor_id="s1", timestamp=TS, readings=readings)


# ---------------------------------------------------------------------------
# Init / validation
# ---------------------------------------------------------------------------

class TestSchemaTransformerInit:
    def test_missing_fields_raises(self):
        with pytest.raises(KeyError, match="fields"):
            SchemaTransformer(config={})

    def test_empty_fields_raises(self):
        with pytest.raises(ValueError, match="non-empty list"):
            SchemaTransformer(config={"fields": []})

    def test_invalid_fields_type_raises(self):
        with pytest.raises(ValueError, match="non-empty list"):
            SchemaTransformer(config={"fields": "temperature"})

    def test_non_string_entries_raises(self):
        with pytest.raises(ValueError, match="strings"):
            SchemaTransformer(config={"fields": ["temperature", 42]})

    def test_valid_config_accepted(self):
        t = SchemaTransformer(config={"fields": ["temperature", "humidity"]})
        assert t is not None


# ---------------------------------------------------------------------------
# Strict mode (default)
# ---------------------------------------------------------------------------

class TestSchemaTransformerStrict:
    def setup_method(self):
        self.t = SchemaTransformer(
            config={"fields": ["temperature", "humidity"], "strict": True}
        )

    def test_valid_record_passes(self):
        r = make_record({"temperature": 22.0, "humidity": 60.0})
        result = self.t.transform(r)
        assert not result.dropped
        assert result.record is not None

    def test_extra_field_drops_record(self):
        r = make_record({"temperature": 22.0, "humidity": 60.0, "wind": 5.0})
        result = self.t.transform(r)
        assert result.dropped
        assert "unexpected fields" in result.error

    def test_missing_required_field_passes_when_require_all_false(self):
        """By default require_all=False, so missing fields are OK."""
        r = make_record({"temperature": 22.0})
        result = self.t.transform(r)
        assert not result.dropped

    def test_missing_required_field_drops_when_require_all_true(self):
        t = SchemaTransformer(
            config={"fields": ["temperature", "humidity"], "require_all": True}
        )
        r = make_record({"temperature": 22.0})
        result = t.transform(r)
        assert result.dropped
        assert "missing required fields" in result.error


# ---------------------------------------------------------------------------
# Non-strict mode
# ---------------------------------------------------------------------------

class TestSchemaTransformerNonStrict:
    def setup_method(self):
        self.t = SchemaTransformer(
            config={"fields": ["temperature"], "strict": False}
        )

    def test_extra_field_not_dropped(self):
        r = make_record({"temperature": 22.0, "wind": 5.0})
        result = self.t.transform(r)
        assert not result.dropped
        assert result.record is not None

    def test_warning_tag_added(self):
        r = make_record({"temperature": 22.0, "wind": 5.0})
        result = self.t.transform(r)
        assert "_schema_warnings" in result.record.readings
        assert "unexpected fields" in result.record.readings["_schema_warnings"]

    def test_clean_record_has_no_warning_tag(self):
        r = make_record({"temperature": 22.0})
        result = self.t.transform(r)
        assert "_schema_warnings" not in result.record.readings
