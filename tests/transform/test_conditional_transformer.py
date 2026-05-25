import pytest
from datetime import datetime, timezone

from agri_etl.ingestion.base_reader import SensorRecord
from agri_etl.transform.conditional_transformer import ConditionalTransformer


TS = datetime(2024, 1, 1, tzinfo=timezone.utc)


def make_record(readings: dict) -> SensorRecord:
    return SensorRecord(sensor_id="s1", timestamp=TS, readings=readings)


# ---------------------------------------------------------------------------
# Init / validation
# ---------------------------------------------------------------------------

class TestConditionalTransformerInit:
    def test_missing_conditions_raises(self):
        with pytest.raises(ValueError, match="conditions"):
            ConditionalTransformer({})

    def test_empty_conditions_raises(self):
        with pytest.raises(ValueError, match="must not be empty"):
            ConditionalTransformer({"conditions": {}})

    def test_invalid_conditions_type_raises(self):
        with pytest.raises(TypeError, match="must be a dict"):
            ConditionalTransformer({"conditions": ["bad"]})

    def test_rule_not_dict_raises(self):
        with pytest.raises(TypeError, match="must be a dict"):
            ConditionalTransformer({"conditions": {"flag": "bad"}})

    def test_missing_required_rule_key_raises(self):
        with pytest.raises(ValueError, match="missing required key 'then'"):
            ConditionalTransformer({
                "conditions": {
                    "flag": {"field": "temp", "op": "gt", "value": 30}
                }
            })

    def test_unsupported_op_raises(self):
        with pytest.raises(ValueError, match="Unsupported op"):
            ConditionalTransformer({
                "conditions": {
                    "flag": {"field": "temp", "op": "between", "value": 30, "then": 1}
                }
            })

    def test_valid_config_accepted(self):
        t = ConditionalTransformer({
            "conditions": {
                "flag": {"field": "temp", "op": "gt", "value": 30, "then": 1, "else": 0}
            }
        })
        assert t is not None


# ---------------------------------------------------------------------------
# Transform behaviour
# ---------------------------------------------------------------------------

class TestConditionalTransformerTransform:
    def _make(self, conditions):
        return ConditionalTransformer({"conditions": conditions})

    def test_then_applied_when_condition_true(self):
        t = self._make({"alert": {"field": "temp", "op": "gt", "value": 30, "then": "HIGH"}})
        result = t.transform([make_record({"temp": 35})])
        assert result.records[0].readings["alert"] == "HIGH"
        assert not result.errors

    def test_else_applied_when_condition_false(self):
        t = self._make({"alert": {"field": "temp", "op": "gt", "value": 30, "then": "HIGH", "else": "OK"}})
        result = t.transform([make_record({"temp": 20})])
        assert result.records[0].readings["alert"] == "OK"

    def test_no_else_leaves_field_absent_when_false(self):
        t = self._make({"alert": {"field": "temp", "op": "gt", "value": 30, "then": "HIGH"}})
        result = t.transform([make_record({"temp": 20})])
        assert "alert" not in result.records[0].readings

    def test_eq_op(self):
        t = self._make({"match": {"field": "status", "op": "eq", "value": "ok", "then": True}})
        result = t.transform([make_record({"status": "ok"})])
        assert result.records[0].readings["match"] is True

    def test_in_op(self):
        t = self._make({"cat": {"field": "code", "op": "in", "value": [1, 2, 3], "then": "valid"}})
        result = t.transform([make_record({"code": 2})])
        assert result.records[0].readings["cat"] == "valid"

    def test_not_in_op(self):
        t = self._make({"cat": {"field": "code", "op": "not_in", "value": [1, 2], "then": "other"}})
        result = t.transform([make_record({"code": 5})])
        assert result.records[0].readings["cat"] == "other"

    def test_missing_source_field_records_error(self):
        t = self._make({"flag": {"field": "humidity", "op": "lt", "value": 50, "then": 1}})
        result = t.transform([make_record({"temp": 20})])
        assert len(result.errors) == 1
        assert "humidity" in result.errors[0]

    def test_original_readings_preserved(self):
        t = self._make({"flag": {"field": "temp", "op": "gte", "value": 0, "then": 1}})
        result = t.transform([make_record({"temp": 10, "humidity": 80})])
        assert result.records[0].readings["temp"] == 10
        assert result.records[0].readings["humidity"] == 80

    def test_empty_batch_returns_empty(self):
        t = self._make({"flag": {"field": "temp", "op": "gt", "value": 0, "then": 1}})
        result = t.transform([])
        assert result.records == []
        assert result.errors == []
