import pytest
from datetime import datetime, timezone

from agri_etl.ingestion.base_reader import SensorRecord
from agri_etl.transform.rolling_transformer import RollingTransformer


TS = datetime(2024, 1, 1, tzinfo=timezone.utc)


def make_record(readings: dict) -> SensorRecord:
    return SensorRecord(
        sensor_id="s1", timestamp=TS, readings=readings, metadata={}
    )


# ---------------------------------------------------------------------------
# Init / validation
# ---------------------------------------------------------------------------

class TestRollingTransformerInit:
    def test_missing_windows_raises(self):
        with pytest.raises(ValueError, match="requires 'windows'"):
            RollingTransformer({})

    def test_empty_windows_raises(self):
        with pytest.raises(ValueError, match="non-empty dict"):
            RollingTransformer({"windows": {}})

    def test_invalid_windows_type_raises(self):
        with pytest.raises(ValueError, match="non-empty dict"):
            RollingTransformer({"windows": ["temp"]})

    def test_invalid_spec_type_raises(self):
        with pytest.raises(ValueError, match="must be a dict"):
            RollingTransformer({"windows": {"temp": 3}})

    def test_invalid_size_raises(self):
        with pytest.raises(ValueError, match="positive int"):
            RollingTransformer({"windows": {"temp": {"size": 0}}})

    def test_non_int_size_raises(self):
        with pytest.raises(ValueError, match="positive int"):
            RollingTransformer({"windows": {"temp": {"size": "3"}}})

    def test_unsupported_function_raises(self):
        with pytest.raises(ValueError, match="Unsupported function"):
            RollingTransformer({"windows": {"temp": {"size": 3, "function": "median"}}})

    def test_valid_config_accepted(self):
        t = RollingTransformer({"windows": {"temp": {"size": 3}}})
        assert t is not None


# ---------------------------------------------------------------------------
# Functional tests
# ---------------------------------------------------------------------------

class TestRollingTransformerTransform:
    def _make(self, **kwargs):
        return RollingTransformer({"windows": kwargs})

    def test_rolling_mean_single_record(self):
        t = self._make(temp={"size": 3, "function": "mean"})
        result = t.transform([make_record({"temp": 10.0})])
        assert result.records[0].readings["temp_rolling_mean"] == pytest.approx(10.0)

    def test_rolling_mean_accumulates(self):
        t = self._make(temp={"size": 3, "function": "mean"})
        records = [make_record({"temp": float(v)}) for v in [10, 20, 30]]
        result = t.transform(records)
        assert result.records[-1].readings["temp_rolling_mean"] == pytest.approx(20.0)

    def test_rolling_mean_window_slides(self):
        t = self._make(temp={"size": 3, "function": "mean"})
        records = [make_record({"temp": float(v)}) for v in [10, 20, 30, 40]]
        result = t.transform(records)
        # last window: [20, 30, 40] -> mean 30
        assert result.records[-1].readings["temp_rolling_mean"] == pytest.approx(30.0)

    def test_rolling_min(self):
        t = self._make(temp={"size": 3, "function": "min"})
        records = [make_record({"temp": float(v)}) for v in [5, 3, 8]]
        result = t.transform(records)
        assert result.records[-1].readings["temp_rolling_min"] == pytest.approx(3.0)

    def test_rolling_max(self):
        t = self._make(temp={"size": 3, "function": "max"})
        records = [make_record({"temp": float(v)}) for v in [5, 3, 8]]
        result = t.transform(records)
        assert result.records[-1].readings["temp_rolling_max"] == pytest.approx(8.0)

    def test_rolling_sum(self):
        t = self._make(temp={"size": 3, "function": "sum"})
        records = [make_record({"temp": float(v)}) for v in [1, 2, 3]]
        result = t.transform(records)
        assert result.records[-1].readings["temp_rolling_sum"] == pytest.approx(6.0)

    def test_rolling_count(self):
        t = self._make(temp={"size": 3, "function": "count"})
        records = [make_record({"temp": float(v)}) for v in [1, 2]]
        result = t.transform(records)
        assert result.records[-1].readings["temp_rolling_count"] == 2

    def test_custom_output_field(self):
        t = self._make(temp={"size": 2, "function": "mean", "output": "t_avg"})
        result = t.transform([make_record({"temp": 5.0})])
        assert "t_avg" in result.records[0].readings

    def test_missing_field_recorded_as_error(self):
        t = self._make(temp={"size": 3, "function": "mean"})
        result = t.transform([make_record({"humidity": 50.0})])
        assert len(result.errors) == 1
        assert "missing field 'temp'" in result.errors[0]

    def test_non_numeric_field_recorded_as_error(self):
        t = self._make(temp={"size": 3, "function": "mean"})
        result = t.transform([make_record({"temp": "hot"})])
        assert len(result.errors) == 1
        assert "cannot cast" in result.errors[0]

    def test_original_readings_preserved(self):
        t = self._make(temp={"size": 2, "function": "mean"})
        result = t.transform([make_record({"temp": 7.0, "humidity": 80.0})])
        assert result.records[0].readings["humidity"] == 80.0
