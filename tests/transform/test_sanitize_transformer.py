import pytest
from datetime import datetime, timezone

from agri_etl.ingestion.base_reader import SensorRecord
from agri_etl.transform.sanitize_transformer import SanitizeTransformer


TS = datetime(2024, 1, 1, tzinfo=timezone.utc)


def make_record(readings: dict) -> SensorRecord:
    return SensorRecord(sensor_id="s1", timestamp=TS, readings=readings)


# ---------------------------------------------------------------------------
# Init / validation
# ---------------------------------------------------------------------------

class TestSanitizeTransformerInit:
    def test_missing_fields_raises(self):
        with pytest.raises(ValueError, match="fields"):
            SanitizeTransformer({"sentinels": [-999]})

    def test_empty_fields_raises(self):
        with pytest.raises(ValueError):
            SanitizeTransformer({"fields": [], "sentinels": [-999]})

    def test_invalid_fields_type_raises(self):
        with pytest.raises(TypeError, match="list"):
            SanitizeTransformer({"fields": "temp", "sentinels": [-999]})

    def test_missing_sentinels_raises(self):
        with pytest.raises(ValueError, match="sentinels"):
            SanitizeTransformer({"fields": ["temp"]})

    def test_invalid_sentinels_type_raises(self):
        with pytest.raises(TypeError, match="list"):
            SanitizeTransformer({"fields": ["temp"], "sentinels": -999})

    def test_valid_config_accepted(self):
        t = SanitizeTransformer({"fields": ["temp"], "sentinels": [-999, None]})
        assert t is not None


# ---------------------------------------------------------------------------
# Behaviour
# ---------------------------------------------------------------------------

class TestSanitizeTransformerTransform:
    def test_sentinel_key_dropped_by_default(self):
        t = SanitizeTransformer({"fields": ["temp"], "sentinels": [-999]})
        result = t.transform([make_record({"temp": -999, "hum": 55})])
        assert "temp" not in result.records[0].readings
        assert result.records[0].readings["hum"] == 55

    def test_sentinel_replaced_when_replacement_given(self):
        t = SanitizeTransformer(
            {"fields": ["temp"], "sentinels": [-999], "replacement": 0.0}
        )
        result = t.transform([make_record({"temp": -999})])
        assert result.records[0].readings["temp"] == 0.0

    def test_non_sentinel_value_unchanged(self):
        t = SanitizeTransformer({"fields": ["temp"], "sentinels": [-999]})
        result = t.transform([make_record({"temp": 22.5})])
        assert result.records[0].readings["temp"] == 22.5

    def test_multiple_sentinels(self):
        t = SanitizeTransformer(
            {"fields": ["temp"], "sentinels": [-999, None, ""]}
        )
        for bad in [-999, None, ""]:
            result = t.transform([make_record({"temp": bad})])
            assert "temp" not in result.records[0].readings

    def test_unknown_field_skipped_by_default(self):
        t = SanitizeTransformer({"fields": ["missing"], "sentinels": [-999]})
        result = t.transform([make_record({"temp": 22})])
        assert result.errors == []

    def test_unknown_field_strict_mode_records_error(self):
        t = SanitizeTransformer(
            {"fields": ["missing"], "sentinels": [-999], "strict": True}
        )
        result = t.transform([make_record({"temp": 22})])
        assert len(result.errors) == 1
        assert "missing" in result.errors[0]

    def test_empty_input_returns_empty(self):
        t = SanitizeTransformer({"fields": ["temp"], "sentinels": [-999]})
        result = t.transform([])
        assert result.records == []
        assert result.errors == []

    def test_multiple_records_processed(self):
        t = SanitizeTransformer({"fields": ["temp"], "sentinels": [-999]})
        records = [
            make_record({"temp": -999}),
            make_record({"temp": 20.0}),
        ]
        result = t.transform(records)
        assert "temp" not in result.records[0].readings
        assert result.records[1].readings["temp"] == 20.0
