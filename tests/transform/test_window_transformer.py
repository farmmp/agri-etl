import pytest
from datetime import datetime, timezone

from agri_etl.ingestion.base_reader import SensorRecord
from agri_etl.transform.window_transformer import WindowTransformer


TS = datetime(2024, 1, 1, tzinfo=timezone.utc)


def make_record(readings: dict) -> SensorRecord:
    return SensorRecord(sensor_id="s1", timestamp=TS, readings=readings)


# ---------------------------------------------------------------------------
# Init / validation
# ---------------------------------------------------------------------------

class TestWindowTransformerInit:
    def test_missing_windows_raises(self):
        with pytest.raises(ValueError, match="requires 'windows'"):
            WindowTransformer({})

    def test_empty_windows_raises(self):
        with pytest.raises(ValueError, match="non-empty dict"):
            WindowTransformer({"windows": {}})

    def test_invalid_windows_type_raises(self):
        with pytest.raises(ValueError, match="non-empty dict"):
            WindowTransformer({"windows": ["temp"]})

    def test_invalid_spec_type_raises(self):
        with pytest.raises(ValueError, match="must be a dict"):
            WindowTransformer({"windows": {"temp": "mean"}})

    def test_invalid_size_raises(self):
        with pytest.raises(ValueError, match="int >= 1"):
            WindowTransformer({"windows": {"temp": {"size": 0, "function": "mean"}}})

    def test_unsupported_function_raises(self):
        with pytest.raises(ValueError, match="Unsupported function"):
            WindowTransformer({"windows": {"temp": {"size": 3, "function": "median"}}})

    def test_valid_config_accepted(self):
        t = WindowTransformer({"windows": {"temp": {"size": 3, "function": "mean"}}})
        assert t is not None

    def test_default_suffix(self):
        t = WindowTransformer({"windows": {"temp": {"size": 2, "function": "max"}}})
        assert t._suffix == "_window"

    def test_custom_suffix(self):
        t = WindowTransformer(
            {"windows": {"temp": {"size": 2, "function": "max"}}, "output_suffix": "_roll"}
        )
        assert t._suffix == "_roll"


# ---------------------------------------------------------------------------
# Transform behaviour
# ---------------------------------------------------------------------------

class TestWindowTransformerTransform:
    def _make(self, field="temp", size=3, func="mean"):
        return WindowTransformer({"windows": {field: {"size": size, "function": func}}})

    def test_mean_accumulates_correctly(self):
        t = self._make(size=3, func="mean")
        records = [
            make_record({"temp": 10}),
            make_record({"temp": 20}),
            make_record({"temp": 30}),
        ]
        result = t.transform(records)
        vals = [r.readings["temp_window"] for r in result.records]
        assert vals[0] == pytest.approx(10.0)
        assert vals[1] == pytest.approx(15.0)
        assert vals[2] == pytest.approx(20.0)

    def test_max_function(self):
        t = self._make(size=2, func="max")
        records = [make_record({"temp": v}) for v in [5, 15, 10]]
        result = t.transform(records)
        assert result.records[1].readings["temp_window"] == pytest.approx(15.0)
        assert result.records[2].readings["temp_window"] == pytest.approx(15.0)

    def test_min_function(self):
        t = self._make(size=2, func="min")
        records = [make_record({"temp": v}) for v in [10, 5, 8]]
        result = t.transform(records)
        assert result.records[2].readings["temp_window"] == pytest.approx(5.0)

    def test_sum_function(self):
        t = self._make(size=3, func="sum")
        records = [make_record({"temp": v}) for v in [1, 2, 3, 4]]
        result = t.transform(records)
        assert result.records[3].readings["temp_window"] == pytest.approx(9.0)

    def test_count_function(self):
        t = self._make(size=3, func="count")
        records = [make_record({"temp": v}) for v in [1, 2, 3, 4]]
        result = t.transform(records)
        assert result.records[0].readings["temp_window"] == pytest.approx(1.0)
        assert result.records[2].readings["temp_window"] == pytest.approx(3.0)
        assert result.records[3].readings["temp_window"] == pytest.approx(3.0)

    def test_missing_field_produces_error(self):
        t = self._make()
        result = t.transform([make_record({"humidity": 55})])
        assert len(result.errors) == 1
        assert "temp" in result.errors[0]

    def test_non_numeric_field_produces_error(self):
        t = self._make()
        result = t.transform([make_record({"temp": "hot"})])
        assert len(result.errors) == 1

    def test_original_readings_preserved(self):
        t = self._make(size=1, func="mean")
        result = t.transform([make_record({"temp": 42, "humidity": 80})])
        assert result.records[0].readings["humidity"] == 80

    def test_custom_suffix_applied(self):
        t = WindowTransformer(
            {"windows": {"temp": {"size": 1, "function": "mean"}}, "output_suffix": "_avg"}
        )
        result = t.transform([make_record({"temp": 10})])
        assert "temp_avg" in result.records[0].readings

    def test_empty_batch_returns_empty(self):
        t = self._make()
        result = t.transform([])
        assert result.records == []
        assert result.errors == []
