import pytest
from datetime import datetime, timezone

from agri_etl.ingestion.base_reader import SensorRecord
from agri_etl.transform.scale_transformer import ScaleTransformer


TS = datetime(2024, 6, 1, 12, 0, 0, tzinfo=timezone.utc)


def make_record(readings: dict) -> SensorRecord:
    return SensorRecord(
        sensor_id="s1",
        timestamp=TS,
        readings=readings,
        metadata={},
    )


class TestScaleTransformerInit:
    def test_missing_scales_raises(self):
        with pytest.raises(ValueError, match="scales"):
            ScaleTransformer({})

    def test_empty_scales_raises(self):
        with pytest.raises(ValueError, match="must not be empty"):
            ScaleTransformer({"scales": {}})

    def test_invalid_scales_type_raises(self):
        with pytest.raises(TypeError, match="dict"):
            ScaleTransformer({"scales": ["temp"]})

    def test_non_numeric_factor_raises(self):
        with pytest.raises(TypeError, match="numeric"):
            ScaleTransformer({"scales": {"temp": "x2"}})

    def test_zero_factor_raises(self):
        with pytest.raises(ValueError, match="must not be zero"):
            ScaleTransformer({"scales": {"temp": 0}})

    def test_valid_config_accepted(self):
        t = ScaleTransformer({"scales": {"temp": 0.1}})
        assert t is not None


class TestScaleTransformerTransform:
    def test_scales_single_field(self):
        t = ScaleTransformer({"scales": {"temp": 10.0}})
        result = t.transform([make_record({"temp": 2.5})])
        assert result.records[0].readings["temp"] == pytest.approx(25.0)
        assert result.errors == []

    def test_scales_multiple_fields(self):
        t = ScaleTransformer({"scales": {"temp": 2.0, "humidity": 0.5}})
        result = t.transform([make_record({"temp": 10.0, "humidity": 80.0})])
        assert result.records[0].readings["temp"] == pytest.approx(20.0)
        assert result.records[0].readings["humidity"] == pytest.approx(40.0)

    def test_fractional_factor(self):
        t = ScaleTransformer({"scales": {"voltage": 0.001}})
        result = t.transform([make_record({"voltage": 3300.0})])
        assert result.records[0].readings["voltage"] == pytest.approx(3.3)

    def test_negative_factor(self):
        t = ScaleTransformer({"scales": {"offset": -1.0}})
        result = t.transform([make_record({"offset": 5.0})])
        assert result.records[0].readings["offset"] == pytest.approx(-5.0)

    def test_missing_field_records_error(self):
        t = ScaleTransformer({"scales": {"missing_field": 2.0}})
        result = t.transform([make_record({"temp": 10.0})])
        assert len(result.errors) == 1
        assert "missing_field" in result.errors[0]

    def test_skip_missing_suppresses_error(self):
        t = ScaleTransformer({"scales": {"missing_field": 2.0}, "skip_missing": True})
        result = t.transform([make_record({"temp": 10.0})])
        assert result.errors == []

    def test_non_numeric_field_records_error(self):
        t = ScaleTransformer({"scales": {"temp": 2.0}})
        result = t.transform([make_record({"temp": "hot"})])
        assert len(result.errors) == 1
        assert "not numeric" in result.errors[0]

    def test_unscaled_fields_preserved(self):
        t = ScaleTransformer({"scales": {"temp": 2.0}})
        result = t.transform([make_record({"temp": 5.0, "humidity": 60.0})])
        assert result.records[0].readings["humidity"] == 60.0

    def test_empty_input_returns_empty(self):
        t = ScaleTransformer({"scales": {"temp": 2.0}})
        result = t.transform([])
        assert result.records == []
        assert result.errors == []
