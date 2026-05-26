import pytest
from datetime import datetime, timezone

from agri_etl.ingestion.base_reader import SensorRecord
from agri_etl.transform.lookup_transformer import LookupTransformer


TS = datetime(2024, 6, 1, 12, 0, 0, tzinfo=timezone.utc)


def make_record(**readings) -> SensorRecord:
    return SensorRecord(
        sensor_id="s1",
        timestamp=TS,
        readings=readings,
        meta={},
    )


# ---------------------------------------------------------------------------
# Init / validation
# ---------------------------------------------------------------------------

class TestLookupTransformerInit:
    def test_missing_lookups_raises(self):
        with pytest.raises(ValueError, match="'lookups'"):
            LookupTransformer({})

    def test_empty_lookups_raises(self):
        with pytest.raises(ValueError, match="must not be empty"):
            LookupTransformer({"lookups": {}})

    def test_invalid_lookups_type_raises(self):
        with pytest.raises(TypeError, match="must be a dict"):
            LookupTransformer({"lookups": ["status", "ok"]})

    def test_invalid_table_type_raises(self):
        with pytest.raises(TypeError, match="lookup table for field 'status'"):
            LookupTransformer({"lookups": {"status": ["a", "b"]}})

    def test_valid_config_accepted(self):
        t = LookupTransformer({"lookups": {"status": {"0": "off", "1": "on"}}})
        assert t is not None

    def test_valid_config_with_default_accepted(self):
        t = LookupTransformer(
            {"lookups": {"status": {"0": "off"}}, "default": "unknown"}
        )
        assert t is not None


# ---------------------------------------------------------------------------
# Transform behaviour
# ---------------------------------------------------------------------------

class TestLookupTransformerTransform:
    def test_value_replaced_when_found(self):
        t = LookupTransformer({"lookups": {"status": {"0": "off", "1": "on"}}})
        result = t.transform([make_record(status="1")])
        assert result.records[0].readings["status"] == "on"

    def test_value_unchanged_when_not_in_table_no_default(self):
        t = LookupTransformer({"lookups": {"status": {"0": "off"}}})
        result = t.transform([make_record(status="99")])
        assert result.records[0].readings["status"] == "99"

    def test_default_applied_when_not_in_table(self):
        t = LookupTransformer(
            {"lookups": {"status": {"0": "off"}}, "default": "unknown"}
        )
        result = t.transform([make_record(status="99")])
        assert result.records[0].readings["status"] == "unknown"

    def test_field_not_in_record_is_skipped(self):
        t = LookupTransformer({"lookups": {"missing_field": {"a": "b"}}})
        result = t.transform([make_record(temp=22.0)])
        assert "missing_field" not in result.records[0].readings
        assert result.records[0].readings["temp"] == 22.0

    def test_multiple_fields_replaced(self):
        t = LookupTransformer(
            {
                "lookups": {
                    "status": {"0": "off", "1": "on"},
                    "mode": {"A": "auto", "M": "manual"},
                }
            }
        )
        result = t.transform([make_record(status="0", mode="A")])
        r = result.records[0].readings
        assert r["status"] == "off"
        assert r["mode"] == "auto"

    def test_empty_batch_returns_empty(self):
        t = LookupTransformer({"lookups": {"status": {"0": "off"}}})
        result = t.transform([])
        assert result.records == []
        assert result.dropped == 0

    def test_original_record_not_mutated(self):
        t = LookupTransformer({"lookups": {"status": {"1": "on"}}})
        original = make_record(status="1")
        t.transform([original])
        assert original.readings["status"] == "1"

    def test_numeric_key_lookup(self):
        t = LookupTransformer({"lookups": {"code": {1: "active", 0: "idle"}}})
        result = t.transform([make_record(code=1)])
        assert result.records[0].readings["code"] == "active"
