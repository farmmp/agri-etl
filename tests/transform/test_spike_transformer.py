import pytest
from datetime import datetime, timezone

from agri_etl.ingestion.base_reader import SensorRecord
from agri_etl.transform.spike_transformer import SpikeTransformer


TS = datetime(2024, 1, 1, tzinfo=timezone.utc)


def make_record(readings: dict, sensor_id: str = "s1") -> SensorRecord:
    return SensorRecord(sensor_id=sensor_id, timestamp=TS, readings=readings)


# ---------------------------------------------------------------------------
# Init / validation
# ---------------------------------------------------------------------------

class TestSpikeTransformerInit:
    def test_missing_thresholds_raises(self):
        with pytest.raises(ValueError, match="thresholds"):
            SpikeTransformer({})

    def test_empty_thresholds_raises(self):
        with pytest.raises(ValueError, match="non-empty dict"):
            SpikeTransformer({"thresholds": {}})

    def test_invalid_thresholds_type_raises(self):
        with pytest.raises(ValueError, match="non-empty dict"):
            SpikeTransformer({"thresholds": "temp:5"})

    def test_non_positive_threshold_raises(self):
        with pytest.raises(ValueError, match="positive number"):
            SpikeTransformer({"thresholds": {"temp": -1}})

    def test_zero_threshold_raises(self):
        with pytest.raises(ValueError, match="positive number"):
            SpikeTransformer({"thresholds": {"temp": 0}})

    def test_invalid_action_raises(self):
        with pytest.raises(ValueError, match="action"):
            SpikeTransformer({"thresholds": {"temp": 5}, "action": "flag"})

    def test_valid_config_accepted(self):
        t = SpikeTransformer({"thresholds": {"temp": 10.0}})
        assert t is not None

    def test_default_action_is_drop(self):
        t = SpikeTransformer({"thresholds": {"temp": 10.0}})
        assert t.config.get("action", "drop") == "drop"


# ---------------------------------------------------------------------------
# Behaviour
# ---------------------------------------------------------------------------

class TestSpikeTransformerTransform:
    def _make(self, action="drop"):
        return SpikeTransformer({"thresholds": {"temp": 5.0}, "action": action})

    def test_first_record_always_passes(self):
        t = self._make()
        r = make_record({"temp": 100.0})
        result = t.transform([r])
        assert len(result.passed) == 1
        assert len(result.dropped) == 0

    def test_non_spike_passes(self):
        t = self._make()
        r1 = make_record({"temp": 20.0})
        r2 = make_record({"temp": 22.0})
        result = t.transform([r1, r2])
        assert len(result.passed) == 2

    def test_spike_dropped_with_drop_action(self):
        t = self._make(action="drop")
        r1 = make_record({"temp": 20.0})
        r2 = make_record({"temp": 50.0})  # delta 30 > 5
        result = t.transform([r1, r2])
        assert len(result.passed) == 1
        assert len(result.dropped) == 1
        assert result.dropped[0].readings["temp"] == 50.0

    def test_spike_nulled_with_null_action(self):
        t = self._make(action="null")
        r1 = make_record({"temp": 20.0})
        r2 = make_record({"temp": 50.0})
        result = t.transform([r1, r2])
        assert len(result.passed) == 2
        assert result.passed[1].readings["temp"] is None

    def test_missing_field_skipped(self):
        t = self._make()
        r1 = make_record({"humidity": 50})
        r2 = make_record({"humidity": 51})
        result = t.transform([r1, r2])
        assert len(result.passed) == 2

    def test_state_persists_across_calls(self):
        t = self._make()
        t.transform([make_record({"temp": 20.0})])
        result = t.transform([make_record({"temp": 21.0})])
        assert len(result.passed) == 1

    def test_to_dict_structure(self):
        t = self._make()
        r = make_record({"temp": 20.0})
        result = t.transform([r])
        d = result.to_dict()
        assert "passed" in d and "dropped" in d
