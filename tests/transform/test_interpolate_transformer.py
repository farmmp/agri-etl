import pytest
from datetime import datetime, timezone

from agri_etl.ingestion.base_reader import SensorRecord
from agri_etl.transform.interpolate_transformer import InterpolateTransformer


TS = datetime(2024, 1, 1, tzinfo=timezone.utc)


def make_record(readings: dict, sensor_id: str = "s1") -> SensorRecord:
    return SensorRecord(sensor_id=sensor_id, timestamp=TS, readings=readings)


# ---------------------------------------------------------------------------
# Init / validation
# ---------------------------------------------------------------------------

class TestInterpolateTransformerInit:
    def test_missing_fields_raises(self):
        with pytest.raises(ValueError, match="'fields'"):
            InterpolateTransformer({"name": "t"})

    def test_empty_fields_raises(self):
        with pytest.raises(ValueError, match="non-empty list"):
            InterpolateTransformer({"name": "t", "fields": []})

    def test_invalid_fields_type_raises(self):
        with pytest.raises(ValueError, match="non-empty list"):
            InterpolateTransformer({"name": "t", "fields": "temp"})

    def test_non_string_field_raises(self):
        with pytest.raises(ValueError, match="strings"):
            InterpolateTransformer({"name": "t", "fields": [1, 2]})

    def test_invalid_window_size_raises(self):
        with pytest.raises(ValueError, match="window_size"):
            InterpolateTransformer({"name": "t", "fields": ["temp"], "window_size": 1})

    def test_non_int_window_size_raises(self):
        with pytest.raises(ValueError, match="window_size"):
            InterpolateTransformer({"name": "t", "fields": ["temp"], "window_size": "5"})

    def test_valid_config_accepted(self):
        t = InterpolateTransformer({"name": "t", "fields": ["temp"]})
        assert t is not None


# ---------------------------------------------------------------------------
# Behaviour
# ---------------------------------------------------------------------------

class TestInterpolateTransformerTransform:
    def _make(self, **kwargs) -> InterpolateTransformer:
        cfg = {"name": "interp", "fields": ["temp"], **kwargs}
        return InterpolateTransformer(cfg)

    def test_non_none_values_pass_through(self):
        t = self._make()
        result = t.transform([make_record({"temp": 20.0})])
        assert result.records[0].readings["temp"] == 20.0
        assert result.errors == []

    def test_none_with_no_history_stays_none(self):
        t = self._make()
        result = t.transform([make_record({"temp": None})])
        assert result.records[0].readings["temp"] is None

    def test_none_with_single_history_uses_last_value(self):
        t = self._make()
        t.transform([make_record({"temp": 10.0})])
        result = t.transform([make_record({"temp": None})])
        assert result.records[0].readings["temp"] == 10.0

    def test_linear_interpolation_between_two_points(self):
        t = self._make()
        t.transform([make_record({"temp": 10.0})])
        t.transform([make_record({"temp": 20.0})])
        # Next missing value should extrapolate: slope = 10 per step
        result = t.transform([make_record({"temp": None})])
        assert result.records[0].readings["temp"] == pytest.approx(30.0)

    def test_non_field_readings_unaffected(self):
        t = self._make()
        result = t.transform([make_record({"temp": 5.0, "humidity": None})])
        assert result.records[0].readings["humidity"] is None

    def test_multiple_records_in_batch(self):
        t = self._make()
        records = [
            make_record({"temp": 0.0}),
            make_record({"temp": None}),
            make_record({"temp": 4.0}),
        ]
        result = t.transform(records)
        assert result.records[0].readings["temp"] == 0.0
        assert result.records[1].readings["temp"] == pytest.approx(0.0)  # only one prior point
        assert result.records[2].readings["temp"] == 4.0

    def test_invalid_numeric_value_adds_error(self):
        t = self._make()
        result = t.transform([make_record({"temp": "not_a_number"})])
        assert len(result.errors) == 1
