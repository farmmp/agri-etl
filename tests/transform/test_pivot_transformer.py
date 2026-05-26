import pytest
from datetime import datetime, timezone

from agri_etl.ingestion.base_reader import SensorRecord
from agri_etl.transform.pivot_transformer import PivotTransformer


TS = datetime(2024, 6, 1, 12, 0, 0, tzinfo=timezone.utc)


def make_record(sensor_id, metric, value, extra=None):
    readings = {"metric": metric, "value": value}
    if extra:
        readings.update(extra)
    return SensorRecord(sensor_id=sensor_id, timestamp=TS, readings=readings)


class TestPivotTransformerInit:
    def test_default_config_accepted(self):
        t = PivotTransformer({})
        assert t is not None

    def test_unknown_key_raises(self):
        with pytest.raises(ValueError, match="unknown config key"):
            PivotTransformer({"bad_key": True})

    def test_negative_tolerance_raises(self):
        with pytest.raises(ValueError, match="timestamp_tolerance"):
            PivotTransformer({"timestamp_tolerance": -1})

    def test_non_int_tolerance_raises(self):
        with pytest.raises(ValueError, match="timestamp_tolerance"):
            PivotTransformer({"timestamp_tolerance": "0"})

    def test_zero_tolerance_accepted(self):
        t = PivotTransformer({"timestamp_tolerance": 0})
        assert t is not None


class TestPivotTransformerTransform:
    def test_pivots_two_metrics_same_sensor_and_ts(self):
        records = [
            make_record("s1", "temperature", 22.5),
            make_record("s1", "humidity", 60.0),
        ]
        result = PivotTransformer({}).transform(records)
        assert len(result.records) == 1
        r = result.records[0]
        assert r.readings["temperature"] == 22.5
        assert r.readings["humidity"] == 60.0

    def test_different_sensors_produce_separate_records(self):
        records = [
            make_record("s1", "temperature", 22.5),
            make_record("s2", "temperature", 18.0),
        ]
        result = PivotTransformer({}).transform(records)
        assert len(result.records) == 2

    def test_record_missing_pivot_field_is_dropped(self):
        r = SensorRecord(
            sensor_id="s1",
            timestamp=TS,
            readings={"value": 5.0},
        )
        result = PivotTransformer({}).transform([r])
        assert len(result.records) == 0
        assert result.dropped == 1

    def test_record_missing_value_field_is_dropped(self):
        r = SensorRecord(
            sensor_id="s1",
            timestamp=TS,
            readings={"metric": "temperature"},
        )
        result = PivotTransformer({}).transform([r])
        assert len(result.records) == 0

    def test_extra_fields_preserved_in_output(self):
        records = [
            make_record("s1", "temperature", 22.5, extra={"unit": "C"}),
        ]
        result = PivotTransformer({}).transform(records)
        assert result.records[0].readings.get("unit") == "C"

    def test_custom_pivot_and_value_fields(self):
        r = SensorRecord(
            sensor_id="s1",
            timestamp=TS,
            readings={"param": "pressure", "reading": 1013.25},
        )
        cfg = {"pivot_field": "param", "value_field": "reading"}
        result = PivotTransformer(cfg).transform([r])
        assert result.records[0].readings["pressure"] == 1013.25

    def test_empty_input_returns_empty(self):
        result = PivotTransformer({}).transform([])
        assert result.records == []
        assert result.dropped == 0
