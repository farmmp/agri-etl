import pytest
from datetime import datetime, timezone
from agri_etl.ingestion.base_reader import SensorRecord
from agri_etl.transform.clamp_transformer import ClampTransformer


TS = datetime(2024, 6, 1, 12, 0, 0, tzinfo=timezone.utc)


def make_record(readings: dict) -> SensorRecord:
    return SensorRecord(
        sensor_id="s1",
        timestamp=TS,
        readings=readings,
        metadata={},
    )


class TestClampTransformerInit:
    def test_missing_bounds_raises(self):
        with pytest.raises(ValueError, match="'bounds'"):
            ClampTransformer(config={})

    def test_empty_bounds_raises(self):
        with pytest.raises(ValueError, match="non-empty dict"):
            ClampTransformer(config={"bounds": {}})

    def test_invalid_bounds_type_raises(self):
        with pytest.raises(ValueError, match="non-empty dict"):
            ClampTransformer(config={"bounds": "bad"})

    def test_bounds_missing_min_and_max_raises(self):
        with pytest.raises(ValueError, match="at least 'min' or 'max'"):
            ClampTransformer(config={"bounds": {"temp": {}}})

    def test_min_greater_than_max_raises(self):
        with pytest.raises(ValueError, match="must be <= 'max'"):
            ClampTransformer(config={"bounds": {"temp": {"min": 50, "max": 10}}})

    def test_valid_config_ok(self):
        t = ClampTransformer(config={"bounds": {"temp": {"min": 0, "max": 100}}})
        assert t is not None


class TestClampTransformerTransform:
    def setup_method(self):
        self.transformer = ClampTransformer(
            config={"bounds": {"temp": {"min": -10.0, "max": 50.0}, "humidity": {"min": 0.0, "max": 100.0}}}
        )

    def test_value_within_bounds_unchanged(self):
        result = self.transformer.transform(make_record({"temp": 25.0}))
        assert result.record.readings["temp"] == 25.0
        assert not result.dropped
        assert "temp" not in result.notes or "clamped" not in result.notes

    def test_value_above_max_clamped(self):
        result = self.transformer.transform(make_record({"temp": 99.0}))
        assert result.record.readings["temp"] == 50.0
        assert "temp" in result.notes

    def test_value_below_min_clamped(self):
        result = self.transformer.transform(make_record({"temp": -50.0}))
        assert result.record.readings["temp"] == -10.0

    def test_multiple_fields_clamped(self):
        result = self.transformer.transform(make_record({"temp": 200.0, "humidity": -5.0}))
        assert result.record.readings["temp"] == 50.0
        assert result.record.readings["humidity"] == 0.0

    def test_unknown_field_ignored(self):
        result = self.transformer.transform(make_record({"pressure": 9999.0}))
        assert result.record.readings["pressure"] == 9999.0

    def test_non_numeric_field_ignored(self):
        result = self.transformer.transform(make_record({"temp": "hot"}))
        assert result.record.readings["temp"] == "hot"

    def test_sensor_id_and_timestamp_preserved(self):
        result = self.transformer.transform(make_record({"temp": 25.0}))
        assert result.record.sensor_id == "s1"
        assert result.record.timestamp == TS

    def test_only_min_bound(self):
        t = ClampTransformer(config={"bounds": {"temp": {"min": 0.0}}})
        result = t.transform(make_record({"temp": -5.0}))
        assert result.record.readings["temp"] == 0.0

    def test_only_max_bound(self):
        t = ClampTransformer(config={"bounds": {"temp": {"max": 40.0}}})
        result = t.transform(make_record({"temp": 99.0}))
        assert result.record.readings["temp"] == 40.0
