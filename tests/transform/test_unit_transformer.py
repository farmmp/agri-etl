"""Tests for UnitTransformer."""

import pytest
from datetime import datetime, timezone

from agri_etl.ingestion.base_reader import SensorRecord
from agri_etl.transform.unit_transformer import UnitTransformer


@pytest.fixture
def ts():
    return datetime(2024, 6, 1, tzinfo=timezone.utc)


def make_record(values, sensor_id="s1", ts=None):
    if ts is None:
        ts = datetime(2024, 6, 1, tzinfo=timezone.utc)
    return SensorRecord(sensor_id=sensor_id, timestamp=ts, values=values)


class TestUnitTransformerInit:
    def test_missing_conversions_raises(self):
        with pytest.raises(ValueError, match="conversions"):
            UnitTransformer(config={})

    def test_invalid_conversions_type_raises(self):
        with pytest.raises(TypeError):
            UnitTransformer(config={"conversions": "bad"})

    def test_valid_config_accepted(self):
        t = UnitTransformer(config={"conversions": {}})
        assert t.config["conversions"] == {}


class TestUnitTransformerTransform:
    def test_celsius_to_fahrenheit(self):
        t = UnitTransformer(
            config={"conversions": {"temp": {"from": "celsius", "to": "fahrenheit"}}}
        )
        record = make_record({"temp": 0.0})
        result = t.transform(record)
        assert result.transformed["temp"] == pytest.approx(32.0)
        assert result.warnings == []

    def test_ms_to_kmh(self):
        t = UnitTransformer(
            config={"conversions": {"wind": {"from": "m/s", "to": "km/h"}}}
        )
        record = make_record({"wind": 10.0})
        result = t.transform(record)
        assert result.transformed["wind"] == pytest.approx(36.0)

    def test_missing_field_adds_warning(self):
        t = UnitTransformer(
            config={"conversions": {"humidity": {"from": "kpa", "to": "hpa"}}}
        )
        record = make_record({"temp": 20.0})
        result = t.transform(record)
        assert any("humidity" in w for w in result.warnings)
        assert "temp" in result.transformed

    def test_unknown_conversion_adds_warning(self):
        t = UnitTransformer(
            config={"conversions": {"temp": {"from": "kelvin", "to": "rankine"}}}
        )
        record = make_record({"temp": 300.0})
        result = t.transform(record)
        assert any("kelvin" in w for w in result.warnings)

    def test_non_numeric_value_adds_warning(self):
        t = UnitTransformer(
            config={"conversions": {"temp": {"from": "celsius", "to": "fahrenheit"}}}
        )
        record = make_record({"temp": "hot"})
        result = t.transform(record)
        assert any("temp" in w for w in result.warnings)

    def test_original_record_unchanged(self):
        t = UnitTransformer(
            config={"conversions": {"temp": {"from": "celsius", "to": "fahrenheit"}}}
        )
        record = make_record({"temp": 100.0})
        result = t.transform(record)
        assert record.values["temp"] == 100.0
        assert result.transformed["temp"] != 100.0
