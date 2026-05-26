import pytest
from datetime import datetime, timezone

from agri_etl.ingestion.base_reader import SensorRecord
from agri_etl.transform.validate_transformer import ValidateTransformer


TS = datetime(2024, 6, 1, 12, 0, 0, tzinfo=timezone.utc)


def make_record(readings: dict, metadata: dict | None = None) -> SensorRecord:
    return SensorRecord(
        sensor_id="s1",
        timestamp=TS,
        readings=readings,
        metadata=metadata or {},
    )


# ---------------------------------------------------------------------------
# Init / config validation
# ---------------------------------------------------------------------------

class TestValidateTransformerInit:
    def test_missing_rules_raises(self):
        with pytest.raises(KeyError, match="rules"):
            ValidateTransformer({})

    def test_empty_rules_raises(self):
        with pytest.raises(ValueError, match="must not be empty"):
            ValidateTransformer({"rules": {}})

    def test_invalid_rules_type_raises(self):
        with pytest.raises(TypeError, match="must be a dict"):
            ValidateTransformer({"rules": ["temp"]})

    def test_invalid_on_fail_raises(self):
        with pytest.raises(ValueError, match="on_fail"):
            ValidateTransformer({"rules": {"temp": {}}, "on_fail": "ignore"})

    def test_valid_config_accepted(self):
        t = ValidateTransformer({"rules": {"temp": {"type": "float", "min": -50, "max": 100}}})
        assert t is not None


# ---------------------------------------------------------------------------
# transform — flag mode (default)
# ---------------------------------------------------------------------------

class TestValidateTransformerFlag:
    def _make(self, rules, on_fail="flag"):
        return ValidateTransformer({"rules": rules, "on_fail": on_fail})

    def test_valid_record_passes_unchanged(self):
        t = self._make({"temp": {"type": "float", "min": 0.0, "max": 50.0}})
        record = make_record({"temp": 25.0})
        result = t.transform([record])
        assert len(result.records) == 1
        assert result.dropped == 0
        assert result.metadata["flagged"] == 0

    def test_missing_required_field_flagged(self):
        t = self._make({"temp": {"required": True}})
        record = make_record({"humidity": 60.0})
        result = t.transform([record])
        assert len(result.records) == 1
        errors = result.records[0].metadata["_validation_errors"]
        assert any("temp" in e for e in errors)
        assert result.metadata["flagged"] == 1

    def test_optional_missing_field_passes(self):
        t = self._make({"temp": {"required": False}})
        record = make_record({"humidity": 60.0})
        result = t.transform([record])
        assert len(result.records) == 1
        assert "_validation_errors" not in result.records[0].metadata

    def test_type_mismatch_flagged(self):
        t = self._make({"temp": {"type": "float"}})
        record = make_record({"temp": "hot"})
        result = t.transform([record])
        assert result.metadata["flagged"] == 1

    def test_below_min_flagged(self):
        t = self._make({"temp": {"min": 0.0}})
        record = make_record({"temp": -5.0})
        result = t.transform([record])
        assert result.metadata["flagged"] == 1

    def test_above_max_flagged(self):
        t = self._make({"temp": {"max": 50.0}})
        record = make_record({"temp": 55.0})
        result = t.transform([record])
        assert result.metadata["flagged"] == 1


# ---------------------------------------------------------------------------
# transform — drop mode
# ---------------------------------------------------------------------------

class TestValidateTransformerDrop:
    def _make(self, rules):
        return ValidateTransformer({"rules": rules, "on_fail": "drop"})

    def test_invalid_record_dropped(self):
        t = self._make({"temp": {"max": 50.0}})
        records = [make_record({"temp": 99.0}), make_record({"temp": 20.0})]
        result = t.transform(records)
        assert len(result.records) == 1
        assert result.dropped == 1

    def test_all_valid_none_dropped(self):
        t = self._make({"temp": {"min": 0.0, "max": 50.0}})
        records = [make_record({"temp": 10.0}), make_record({"temp": 30.0})]
        result = t.transform(records)
        assert len(result.records) == 2
        assert result.dropped == 0


# ---------------------------------------------------------------------------
# transform — raise mode
# ---------------------------------------------------------------------------

class TestValidateTransformerRaise:
    def test_invalid_record_raises(self):
        t = ValidateTransformer({"rules": {"temp": {"min": 0.0}}, "on_fail": "raise"})
        with pytest.raises(ValueError, match="Validation failed"):
            t.transform([make_record({"temp": -1.0})])

    def test_valid_record_does_not_raise(self):
        t = ValidateTransformer({"rules": {"temp": {"min": 0.0}}, "on_fail": "raise"})
        result = t.transform([make_record({"temp": 10.0})])
        assert len(result.records) == 1
