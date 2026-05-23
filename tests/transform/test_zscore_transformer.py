"""Tests for ZScoreTransformer."""
from __future__ import annotations

import pytest
from datetime import datetime, timezone

from agri_etl.ingestion.base_reader import SensorRecord
from agri_etl.transform.zscore_transformer import ZScoreTransformer


TS = datetime(2024, 1, 1, tzinfo=timezone.utc)


def make_record(sensor_id: str, **readings) -> SensorRecord:
    return SensorRecord(sensor_id=sensor_id, timestamp=TS, readings=dict(readings))


# ---------------------------------------------------------------------------
# Init / validation
# ---------------------------------------------------------------------------

class TestZScoreTransformerInit:
    def test_missing_fields_raises(self):
        with pytest.raises(ValueError, match="non-empty 'fields'"):
            ZScoreTransformer(config={})

    def test_empty_fields_raises(self):
        with pytest.raises(ValueError, match="non-empty 'fields'"):
            ZScoreTransformer(config={"fields": {}})

    def test_invalid_fields_type_raises(self):
        with pytest.raises(TypeError, match="dict"):
            ZScoreTransformer(config={"fields": ["temp"]})

    def test_non_positive_threshold_raises(self):
        with pytest.raises(ValueError, match="positive number"):
            ZScoreTransformer(config={"fields": {"temp": 0}})

    def test_negative_threshold_raises(self):
        with pytest.raises(ValueError, match="positive number"):
            ZScoreTransformer(config={"fields": {"temp": -1.5}})

    def test_invalid_action_raises(self):
        with pytest.raises(ValueError, match="action"):
            ZScoreTransformer(config={"fields": {"temp": 2.0}, "action": "ignore"})

    def test_valid_config_accepted(self):
        t = ZScoreTransformer(config={"fields": {"temp": 2.5}})
        assert t is not None


# ---------------------------------------------------------------------------
# Behaviour
# ---------------------------------------------------------------------------

class TestZScoreTransform:
    def _make_transformer(self, threshold=2.0, action="drop"):
        return ZScoreTransformer(config={"fields": {"temp": threshold}, "action": action})

    def test_empty_records_returns_empty(self):
        t = self._make_transformer()
        result = t.transform([])
        assert result.records == []
        assert result.errors == []

    def test_no_outliers_all_kept(self):
        records = [make_record(f"s{i}", temp=float(20 + i)) for i in range(5)]
        t = self._make_transformer(threshold=3.0)
        result = t.transform(records)
        assert len(result.records) == 5

    def test_outlier_dropped_by_default(self):
        # 4 normal values + 1 extreme outlier
        records = [
            make_record("s1", temp=20.0),
            make_record("s2", temp=21.0),
            make_record("s3", temp=20.5),
            make_record("s4", temp=19.5),
            make_record("outlier", temp=200.0),
        ]
        t = self._make_transformer(threshold=2.0, action="drop")
        result = t.transform(records)
        ids = [r.sensor_id for r in result.records]
        assert "outlier" not in ids
        assert len(result.errors) == 1

    def test_outlier_flagged_when_action_flag(self):
        records = [
            make_record("s1", temp=20.0),
            make_record("s2", temp=21.0),
            make_record("s3", temp=20.5),
            make_record("s4", temp=19.5),
            make_record("outlier", temp=200.0),
        ]
        t = self._make_transformer(threshold=2.0, action="flag")
        result = t.transform(records)
        assert len(result.records) == 5
        outlier_rec = next(r for r in result.records if r.sensor_id == "outlier")
        assert outlier_rec.readings.get("zscore_outlier") is True

    def test_missing_field_in_record_not_flagged(self):
        records = [
            make_record("s1", temp=20.0),
            make_record("s2", temp=21.0),
            make_record("no_temp", humidity=55.0),  # no 'temp' key
        ]
        t = self._make_transformer(threshold=2.0)
        result = t.transform(records)
        # record without the field should pass through
        ids = [r.sensor_id for r in result.records]
        assert "no_temp" in ids

    def test_single_record_not_dropped(self):
        # std == 0 when only one value; should not be dropped
        records = [make_record("s1", temp=999.0)]
        t = self._make_transformer(threshold=2.0)
        result = t.transform(records)
        assert len(result.records) == 1
