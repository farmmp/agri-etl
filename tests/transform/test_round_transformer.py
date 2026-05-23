import pytest
from datetime import datetime, timezone

from agri_etl.ingestion.base_reader import SensorRecord
from agri_etl.transform.round_transformer import RoundTransformer


TS = datetime(2024, 6, 1, 12, 0, 0, tzinfo=timezone.utc)


def make_record(readings: dict) -> SensorRecord:
    return SensorRecord(
        sensor_id="s-01",
        timestamp=TS,
        readings=readings,
        meta={},
    )


class TestRoundTransformerInit:
    def test_missing_fields_raises(self):
        with pytest.raises(ValueError, match="'fields'"):
            RoundTransformer(config={})

    def test_empty_fields_raises(self):
        with pytest.raises(ValueError, match="non-empty dict"):
            RoundTransformer(config={"fields": {}})

    def test_invalid_fields_type_raises(self):
        with pytest.raises(ValueError, match="non-empty dict"):
            RoundTransformer(config={"fields": ["temp"]})

    def test_non_int_places_raises(self):
        with pytest.raises(ValueError, match="must be an int"):
            RoundTransformer(config={"fields": {"temp": 2.5}})

    def test_valid_config_ok(self):
        t = RoundTransformer(config={"fields": {"temp": 2}})
        assert t is not None


class TestRoundTransformerTransform:
    def test_rounds_to_given_decimal_places(self):
        t = RoundTransformer(config={"fields": {"temp": 2}})
        result = t.transform(make_record({"temp": 23.456789}))
        assert result.record.readings["temp"] == pytest.approx(23.46)
        assert not result.dropped
        assert result.errors == []

    def test_rounds_to_zero_decimal_places(self):
        t = RoundTransformer(config={"fields": {"humidity": 0}})
        result = t.transform(make_record({"humidity": 55.7}))
        assert result.record.readings["humidity"] == 56.0

    def test_negative_one_rounds_to_integer(self):
        t = RoundTransformer(config={"fields": {"pressure": -1}})
        result = t.transform(make_record({"pressure": 1013.7}))
        assert result.record.readings["pressure"] == 1014.0

    def test_missing_field_is_skipped_silently(self):
        t = RoundTransformer(config={"fields": {"wind_speed": 1}})
        result = t.transform(make_record({"temp": 20.5}))
        assert "wind_speed" not in result.record.readings
        assert result.errors == []

    def test_non_numeric_field_adds_error(self):
        t = RoundTransformer(config={"fields": {"label": 2}})
        result = t.transform(make_record({"label": "hot"}))
        assert len(result.errors) == 1
        assert "label" in result.errors[0]
        assert not result.dropped

    def test_unrelated_fields_preserved(self):
        t = RoundTransformer(config={"fields": {"temp": 1}})
        result = t.transform(make_record({"temp": 22.22, "co2": 400}))
        assert result.record.readings["co2"] == 400

    def test_integer_value_is_rounded_without_error(self):
        t = RoundTransformer(config={"fields": {"temp": 2}})
        result = t.transform(make_record({"temp": 25}))
        assert result.record.readings["temp"] == 25.0
        assert result.errors == []

    def test_original_record_not_mutated(self):
        t = RoundTransformer(config={"fields": {"temp": 1}})
        original = make_record({"temp": 22.567})
        t.transform(original)
        assert original.readings["temp"] == 22.567
