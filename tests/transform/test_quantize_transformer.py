import pytest
from datetime import datetime, timezone

from agri_etl.ingestion.base_reader import SensorRecord
from agri_etl.transform.quantize_transformer import QuantizeTransformer


TS = datetime(2024, 6, 1, 12, 0, 0, tzinfo=timezone.utc)


def make_record(readings: dict) -> SensorRecord:
    return SensorRecord(
        sensor_id="s1",
        timestamp=TS,
        readings=readings,
        meta={},
    )


# ---------------------------------------------------------------------------
# Init / validation
# ---------------------------------------------------------------------------

class TestQuantizeTransformerInit:
    def test_missing_steps_raises(self):
        with pytest.raises(ValueError, match="requires 'steps'"):
            QuantizeTransformer({})

    def test_empty_steps_raises(self):
        with pytest.raises(ValueError, match="must not be empty"):
            QuantizeTransformer({"steps": {}})

    def test_invalid_steps_type_raises(self):
        with pytest.raises(TypeError, match="must be a dict"):
            QuantizeTransformer({"steps": ["temperature"]})

    def test_non_numeric_step_raises(self):
        with pytest.raises(TypeError, match="must be a number"):
            QuantizeTransformer({"steps": {"temperature": "0.5"}})

    def test_zero_step_raises(self):
        with pytest.raises(ValueError, match="must be positive"):
            QuantizeTransformer({"steps": {"temperature": 0}})

    def test_negative_step_raises(self):
        with pytest.raises(ValueError, match="must be positive"):
            QuantizeTransformer({"steps": {"temperature": -1.0}})

    def test_valid_config_accepted(self):
        t = QuantizeTransformer({"steps": {"temperature": 0.5}})
        assert t is not None


# ---------------------------------------------------------------------------
# Transform behaviour
# ---------------------------------------------------------------------------

class TestQuantizeTransformerTransform:
    def test_snaps_to_nearest_step(self):
        t = QuantizeTransformer({"steps": {"temperature": 0.5}})
        record = make_record({"temperature": 23.3})
        result = t.transform([record])
        assert result.errors == []
        assert result.records[0].readings["temperature"] == pytest.approx(23.5)

    def test_already_on_grid_unchanged(self):
        t = QuantizeTransformer({"steps": {"humidity": 1.0}})
        record = make_record({"humidity": 55.0})
        result = t.transform([record])
        assert result.records[0].readings["humidity"] == pytest.approx(55.0)

    def test_rounds_down_when_closer(self):
        t = QuantizeTransformer({"steps": {"pressure": 5.0}})
        record = make_record({"pressure": 102.1})
        result = t.transform([record])
        assert result.records[0].readings["pressure"] == pytest.approx(100.0)

    def test_missing_field_skipped_silently(self):
        t = QuantizeTransformer({"steps": {"temperature": 0.5}})
        record = make_record({"humidity": 40.0})
        result = t.transform([record])
        assert result.errors == []
        assert result.records[0].readings == {"humidity": 40.0}

    def test_non_numeric_field_produces_error(self):
        t = QuantizeTransformer({"steps": {"temperature": 0.5}})
        record = make_record({"temperature": "hot"})
        result = t.transform([record])
        assert len(result.errors) == 1
        assert result.errors[0]["field"] == "temperature"

    def test_multiple_fields_quantized(self):
        t = QuantizeTransformer({"steps": {"temperature": 0.5, "humidity": 2.0}})
        record = make_record({"temperature": 21.7, "humidity": 43.1})
        result = t.transform([record])
        assert result.records[0].readings["temperature"] == pytest.approx(22.0)
        assert result.records[0].readings["humidity"] == pytest.approx(44.0)

    def test_empty_input_returns_empty(self):
        t = QuantizeTransformer({"steps": {"temperature": 1.0}})
        result = t.transform([])
        assert result.records == []
        assert result.errors == []

    def test_original_record_not_mutated(self):
        t = QuantizeTransformer({"steps": {"temperature": 1.0}})
        record = make_record({"temperature": 23.7})
        original_value = record.readings["temperature"]
        t.transform([record])
        assert record.readings["temperature"] == original_value
