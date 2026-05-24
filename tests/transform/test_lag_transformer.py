import datetime
import pytest

from agri_etl.ingestion.base_reader import SensorRecord
from agri_etl.transform.lag_transformer import LagTransformer

TS = datetime.datetime(2024, 1, 1, tzinfo=datetime.timezone.utc)


def make_record(readings, offset_s=0):
    return SensorRecord(
        sensor_id="s1",
        timestamp=TS + datetime.timedelta(seconds=offset_s),
        readings=readings,
    )


# ---------------------------------------------------------------------------
# Init / validation
# ---------------------------------------------------------------------------

class TestLagTransformerInit:
    def test_missing_fields_raises(self):
        with pytest.raises(ValueError, match="'fields'"):
            LagTransformer({})

    def test_empty_fields_raises(self):
        with pytest.raises(ValueError, match="non-empty dict"):
            LagTransformer({"fields": {}})

    def test_invalid_fields_type_raises(self):
        with pytest.raises(ValueError, match="non-empty dict"):
            LagTransformer({"fields": ["temperature"]})

    def test_zero_steps_raises(self):
        with pytest.raises(ValueError, match="positive integer"):
            LagTransformer({"fields": {"temperature": 0}})

    def test_negative_steps_raises(self):
        with pytest.raises(ValueError, match="positive integer"):
            LagTransformer({"fields": {"temperature": -1}})

    def test_non_int_steps_raises(self):
        with pytest.raises(ValueError, match="positive integer"):
            LagTransformer({"fields": {"temperature": 1.5}})

    def test_valid_config_accepted(self):
        t = LagTransformer({"fields": {"temperature": 1}})
        assert t is not None


# ---------------------------------------------------------------------------
# Behaviour
# ---------------------------------------------------------------------------

class TestLagTransformerBehaviour:
    def _make(self, fields, fill_value=None):
        cfg = {"fields": fields}
        if fill_value is not None:
            cfg["fill_value"] = fill_value
        return LagTransformer(cfg)

    def test_first_record_uses_fill_value(self):
        t = self._make({"temperature": 1})
        r = make_record({"temperature": 20.0})
        result = t.transform([r])
        assert result.passed[0].readings["temperature_lag1"] is None

    def test_custom_fill_value(self):
        t = LagTransformer({"fields": {"temperature": 1}, "fill_value": -999})
        r = make_record({"temperature": 20.0})
        result = t.transform([r])
        assert result.passed[0].readings["temperature_lag1"] == -999

    def test_lag1_returns_previous_value(self):
        t = self._make({"temperature": 1})
        r1 = make_record({"temperature": 10.0}, offset_s=0)
        r2 = make_record({"temperature": 20.0}, offset_s=1)
        result = t.transform([r1, r2])
        assert result.passed[1].readings["temperature_lag1"] == 10.0

    def test_lag2_waits_two_records(self):
        t = self._make({"temperature": 2})
        records = [make_record({"temperature": float(i)}, offset_s=i) for i in range(4)]
        result = t.transform(records)
        # first two should be fill (None)
        assert result.passed[0].readings["temperature_lag2"] is None
        assert result.passed[1].readings["temperature_lag2"] is None
        assert result.passed[2].readings["temperature_lag2"] == 0.0
        assert result.passed[3].readings["temperature_lag2"] == 1.0

    def test_original_field_preserved(self):
        t = self._make({"temperature": 1})
        r = make_record({"temperature": 42.0})
        result = t.transform([r])
        assert result.passed[0].readings["temperature"] == 42.0

    def test_multiple_fields(self):
        t = self._make({"temperature": 1, "humidity": 1})
        r1 = make_record({"temperature": 5.0, "humidity": 80.0})
        r2 = make_record({"temperature": 6.0, "humidity": 81.0})
        result = t.transform([r1, r2])
        assert result.passed[1].readings["temperature_lag1"] == 5.0
        assert result.passed[1].readings["humidity_lag1"] == 80.0

    def test_empty_input_returns_empty(self):
        t = self._make({"temperature": 1})
        result = t.transform([])
        assert result.passed == []
        assert result.failed == []

    def test_missing_field_stores_none_lag(self):
        """Field absent from a record -> current value is None, lag propagates None."""
        t = self._make({"temperature": 1})
        r1 = make_record({})
        r2 = make_record({"temperature": 5.0})
        result = t.transform([r1, r2])
        assert result.passed[1].readings["temperature_lag1"] is None
