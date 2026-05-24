import datetime
import pytest

from agri_etl.ingestion.base_reader import SensorRecord
from agri_etl.transform.threshold_transformer import ThresholdTransformer


TS = datetime.datetime(2024, 1, 1, 12, 0, 0)


def make_record(readings: dict) -> SensorRecord:
    return SensorRecord(sensor_id="s1", timestamp=TS, readings=readings)


# ---------------------------------------------------------------------------
# Init / validation
# ---------------------------------------------------------------------------

class TestThresholdTransformerInit:
    def test_missing_thresholds_raises(self):
        with pytest.raises(ValueError, match="thresholds"):
            ThresholdTransformer({})

    def test_empty_thresholds_raises(self):
        with pytest.raises(ValueError, match="must not be empty"):
            ThresholdTransformer({"thresholds": {}})

    def test_invalid_thresholds_type_raises(self):
        with pytest.raises(TypeError, match="must be a dict"):
            ThresholdTransformer({"thresholds": ["temp"]})

    def test_bounds_not_dict_raises(self):
        with pytest.raises(TypeError, match="must be a dict"):
            ThresholdTransformer({"thresholds": {"temp": [0, 100]}})

    def test_bounds_missing_min_and_max_raises(self):
        with pytest.raises(ValueError, match="at least 'min' or 'max'"):
            ThresholdTransformer({"thresholds": {"temp": {}}})

    def test_invalid_action_raises(self):
        with pytest.raises(ValueError, match="'action' must be"):
            ThresholdTransformer({"thresholds": {"temp": {"max": 50}}, "action": "warn"})

    def test_valid_config_accepted(self):
        t = ThresholdTransformer({"thresholds": {"temp": {"min": 0, "max": 50}}})
        assert t is not None

    def test_default_action_is_flag(self):
        t = ThresholdTransformer({"thresholds": {"temp": {"max": 50}}})
        assert t.config.get("action", "flag") == "flag"


# ---------------------------------------------------------------------------
# Behaviour — flag mode
# ---------------------------------------------------------------------------

class TestThresholdTransformerFlag:
    def setup_method(self):
        self.t = ThresholdTransformer(
            {"thresholds": {"temp": {"min": 0.0, "max": 40.0}}, "action": "flag"}
        )

    def test_within_bounds_no_flag(self):
        r = make_record({"temp": 20.0})
        result = self.t.transform([r])
        assert len(result.records) == 1
        assert "temp_threshold_breach" not in result.records[0].readings

    def test_above_max_adds_flag(self):
        r = make_record({"temp": 45.0})
        result = self.t.transform([r])
        assert result.records[0].readings["temp_threshold_breach"] is True

    def test_below_min_adds_flag(self):
        r = make_record({"temp": -5.0})
        result = self.t.transform([r])
        assert result.records[0].readings["temp_threshold_breach"] is True

    def test_missing_field_skipped(self):
        r = make_record({"humidity": 80.0})
        result = self.t.transform([r])
        assert len(result.records) == 1
        assert result.errors == []

    def test_non_numeric_field_adds_error(self):
        r = make_record({"temp": "hot"})
        result = self.t.transform([r])
        assert len(result.errors) == 1


# ---------------------------------------------------------------------------
# Behaviour — drop mode
# ---------------------------------------------------------------------------

class TestThresholdTransformerDrop:
    def setup_method(self):
        self.t = ThresholdTransformer(
            {"thresholds": {"temp": {"max": 40.0}}, "action": "drop"}
        )

    def test_within_bounds_kept(self):
        r = make_record({"temp": 30.0})
        result = self.t.transform([r])
        assert len(result.records) == 1
        assert len(result.dropped) == 0

    def test_breach_drops_record(self):
        r = make_record({"temp": 55.0})
        result = self.t.transform([r])
        assert len(result.records) == 0
        assert len(result.dropped) == 1

    def test_mixed_batch(self):
        records = [
            make_record({"temp": 25.0}),
            make_record({"temp": 99.0}),
            make_record({"temp": 38.0}),
        ]
        result = self.t.transform(records)
        assert len(result.records) == 2
        assert len(result.dropped) == 1
