"""Tests for FilterTransformer."""

from __future__ import annotations

from datetime import datetime, timezone

import pytest

from agri_etl.ingestion.base_reader import SensorRecord
from agri_etl.transform.filter_transformer import FilterTransformer


TS = datetime(2024, 6, 1, 12, 0, 0, tzinfo=timezone.utc)


def make_record(values: dict, sensor_id: str = "s1") -> SensorRecord:
    return SensorRecord(sensor_id=sensor_id, timestamp=TS, values=values)


# ---------------------------------------------------------------------------
# Initialisation / validation
# ---------------------------------------------------------------------------

class TestFilterTransformerInit:
    def test_missing_rules_raises(self):
        with pytest.raises(ValueError, match="rules"):
            FilterTransformer(config={})

    def test_empty_rules_raises(self):
        with pytest.raises(ValueError, match="rules"):
            FilterTransformer(config={"rules": {}})

    def test_invalid_rules_type_raises(self):
        with pytest.raises(ValueError, match="rules"):
            FilterTransformer(config={"rules": "bad"})

    def test_non_dict_bound_raises(self):
        with pytest.raises(ValueError, match="must be a dict"):
            FilterTransformer(config={"rules": {"temp": "bad"}})

    def test_non_numeric_min_raises(self):
        with pytest.raises(ValueError, match="numeric"):
            FilterTransformer(config={"rules": {"temp": {"min": "cold"}}})

    def test_valid_config_accepted(self):
        t = FilterTransformer(config={"rules": {"temp": {"min": -10, "max": 60}}})
        assert t is not None


# ---------------------------------------------------------------------------
# transform() — drop_on_fail=True (default)
# ---------------------------------------------------------------------------

class TestFilterTransformerDrop:
    def setup_method(self):
        self.t = FilterTransformer(
            config={"rules": {"temp": {"min": 0.0, "max": 50.0}, "humidity": {"max": 100.0}}}
        )

    def test_in_range_record_passes(self):
        r = make_record({"temp": 25.0, "humidity": 60.0})
        result = self.t.transform([r])
        assert len(result.valid) == 1
        assert result.errors == []

    def test_below_min_dropped(self):
        r = make_record({"temp": -5.0})
        result = self.t.transform([r])
        assert result.valid == []
        assert len(result.errors) == 1
        assert "min" in result.errors[0]["reason"]

    def test_above_max_dropped(self):
        r = make_record({"temp": 55.0})
        result = self.t.transform([r])
        assert result.valid == []
        assert len(result.errors) == 1

    def test_missing_field_ignored(self):
        r = make_record({"humidity": 80.0})  # no 'temp' key
        result = self.t.transform([r])
        assert len(result.valid) == 1

    def test_mixed_batch(self):
        records = [
            make_record({"temp": 20.0}),
            make_record({"temp": 99.0}),
            make_record({"temp": 35.0}),
        ]
        result = self.t.transform(records)
        assert len(result.valid) == 2
        assert len(result.errors) == 1


# ---------------------------------------------------------------------------
# transform() — drop_on_fail=False (flag mode)
# ---------------------------------------------------------------------------

class TestFilterTransformerFlag:
    def setup_method(self):
        self.t = FilterTransformer(
            config={"rules": {"temp": {"min": 0.0, "max": 50.0}}, "drop_on_fail": False}
        )

    def test_out_of_range_kept_with_warning(self):
        r = make_record({"temp": -3.0})
        result = self.t.transform([r])
        assert len(result.valid) == 1
        assert result.errors == []
        assert "filter_warnings" in result.valid[0].metadata

    def test_in_range_has_no_warning(self):
        r = make_record({"temp": 25.0})
        result = self.t.transform([r])
        assert "filter_warnings" not in result.valid[0].metadata
