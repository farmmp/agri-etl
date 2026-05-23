"""Tests for MaskTransformer."""

from __future__ import annotations

import datetime
import pytest

from agri_etl.ingestion.base_reader import SensorRecord
from agri_etl.transform.mask_transformer import MaskTransformer

_TS = datetime.datetime(2024, 1, 1, 12, 0, 0, tzinfo=datetime.timezone.utc)


def make_record(readings: dict) -> SensorRecord:
    return SensorRecord(sensor_id="s1", timestamp=_TS, readings=readings)


# ---------------------------------------------------------------------------
# Init / validation
# ---------------------------------------------------------------------------

class TestMaskTransformerInit:
    def test_missing_masks_raises(self):
        with pytest.raises(ValueError, match="'masks'"):
            MaskTransformer({})

    def test_empty_masks_raises(self):
        with pytest.raises(ValueError, match="non-empty list"):
            MaskTransformer({"masks": []})

    def test_invalid_masks_type_raises(self):
        with pytest.raises(ValueError, match="non-empty list"):
            MaskTransformer({"masks": "bad"})

    def test_rule_not_dict_raises(self):
        with pytest.raises(ValueError, match="must be a dict"):
            MaskTransformer({"masks": ["not-a-dict"]})

    def test_missing_field_raises(self):
        with pytest.raises(ValueError, match="missing 'field'"):
            MaskTransformer({"masks": [{"op": "gt", "threshold": 0}]})

    def test_unsupported_op_raises(self):
        with pytest.raises(ValueError, match="unsupported op"):
            MaskTransformer({"masks": [{"field": "temp", "op": "between", "threshold": 0}]})

    def test_missing_threshold_raises(self):
        with pytest.raises(ValueError, match="missing 'threshold'"):
            MaskTransformer({"masks": [{"field": "temp", "op": "gt"}]})

    def test_valid_config_accepted(self):
        t = MaskTransformer({"masks": [{"field": "temp", "op": "gt", "threshold": 50}]})
        assert t is not None


# ---------------------------------------------------------------------------
# Transform behaviour
# ---------------------------------------------------------------------------

class TestMaskTransformerTransform:
    def _make(self, **rule_kwargs) -> MaskTransformer:
        return MaskTransformer({"masks": [rule_kwargs]})

    def test_gt_masks_value(self):
        t = self._make(field="temp", op="gt", threshold=40)
        result = t.transform([make_record({"temp": 55.0})])
        assert result.records[0].readings["temp"] is None
        assert result.errors == []

    def test_gt_does_not_mask_below_threshold(self):
        t = self._make(field="temp", op="gt", threshold=40)
        result = t.transform([make_record({"temp": 30.0})])
        assert result.records[0].readings["temp"] == 30.0

    def test_custom_replacement_value(self):
        t = MaskTransformer(
            {"masks": [{"field": "temp", "op": "lt", "threshold": 0, "replacement": -9999}]}
        )
        result = t.transform([make_record({"temp": -5})])
        assert result.records[0].readings["temp"] == -9999

    def test_field_absent_leaves_record_unchanged(self):
        t = self._make(field="humidity", op="eq", threshold=100)
        result = t.transform([make_record({"temp": 22.0})])
        assert result.records[0].readings == {"temp": 22.0}

    def test_eq_op(self):
        t = self._make(field="status", op="eq", threshold=0)
        result = t.transform([make_record({"status": 0})])
        assert result.records[0].readings["status"] is None

    def test_neq_op(self):
        t = self._make(field="flag", op="neq", threshold=1)
        result = t.transform([make_record({"flag": 0})])
        assert result.records[0].readings["flag"] is None

    def test_multiple_rules_applied(self):
        t = MaskTransformer(
            {
                "masks": [
                    {"field": "temp", "op": "gt", "threshold": 50},
                    {"field": "humidity", "op": "lt", "threshold": 10},
                ]
            }
        )
        result = t.transform([make_record({"temp": 60, "humidity": 5})])
        r = result.records[0].readings
        assert r["temp"] is None
        assert r["humidity"] is None

    def test_original_record_not_mutated(self):
        t = self._make(field="temp", op="gte", threshold=0)
        original = make_record({"temp": 25.0})
        t.transform([original])
        assert original.readings["temp"] == 25.0

    def test_empty_input_returns_empty(self):
        t = self._make(field="temp", op="gt", threshold=0)
        result = t.transform([])
        assert result.records == []
        assert result.errors == []
