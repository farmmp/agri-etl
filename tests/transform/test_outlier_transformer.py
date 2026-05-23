import pytest
from datetime import datetime, timezone

from agri_etl.ingestion.base_reader import SensorRecord
from agri_etl.transform.outlier_transformer import OutlierTransformer


TS = datetime(2024, 1, 1, tzinfo=timezone.utc)


def make_record(temp: float, humidity: float = 50.0) -> SensorRecord:
    return SensorRecord(
        station_id="s1",
        timestamp=TS,
        sensor_data={"temp": temp, "humidity": humidity},
    )


# ---------------------------------------------------------------------------
# Init / validation
# ---------------------------------------------------------------------------

class TestOutlierTransformerInit:
    def test_missing_fields_raises(self):
        with pytest.raises(ValueError, match="fields"):
            OutlierTransformer({})

    def test_empty_fields_raises(self):
        with pytest.raises(ValueError, match="fields"):
            OutlierTransformer({"fields": []})

    def test_invalid_fields_type_raises(self):
        with pytest.raises(ValueError, match="list of strings"):
            OutlierTransformer({"fields": "temp"})

    def test_invalid_strategy_raises(self):
        with pytest.raises(ValueError, match="strategy"):
            OutlierTransformer({"fields": ["temp"], "strategy": "flag"})

    def test_invalid_iqr_factor_raises(self):
        with pytest.raises(ValueError, match="iqr_factor"):
            OutlierTransformer({"fields": ["temp"], "iqr_factor": -1})

    def test_valid_config_accepted(self):
        t = OutlierTransformer({"fields": ["temp"], "strategy": "cap", "iqr_factor": 2.0})
        assert t is not None


# ---------------------------------------------------------------------------
# Behaviour
# ---------------------------------------------------------------------------

class TestOutlierTransformerTransform:
    def _normal_batch(self):
        """8 records clustered around 20 °C plus two extreme outliers."""
        temps = [18.0, 19.0, 20.0, 20.5, 21.0, 21.5, 22.0, 22.5, -50.0, 150.0]
        return [make_record(t) for t in temps]

    def test_empty_input_returns_empty(self):
        t = OutlierTransformer({"fields": ["temp"]})
        result = t.transform([])
        assert result.records == []
        assert result.dropped == 0

    def test_drop_strategy_removes_outliers(self):
        t = OutlierTransformer({"fields": ["temp"], "strategy": "drop"})
        result = t.transform(self._normal_batch())
        assert result.dropped == 2
        assert len(result.records) == 8
        temps = [r.sensor_data["temp"] for r in result.records]
        assert -50.0 not in temps
        assert 150.0 not in temps

    def test_cap_strategy_clamps_outliers(self):
        t = OutlierTransformer({"fields": ["temp"], "strategy": "cap"})
        result = t.transform(self._normal_batch())
        assert result.dropped == 0
        assert len(result.records) == 10
        temps = [r.sensor_data["temp"] for r in result.records]
        assert -50.0 not in temps
        assert 150.0 not in temps

    def test_no_outliers_passes_all(self):
        records = [make_record(float(t)) for t in range(20, 30)]
        t = OutlierTransformer({"fields": ["temp"]})
        result = t.transform(records)
        assert result.dropped == 0
        assert len(result.records) == 10

    def test_too_few_values_skips_fence(self):
        """Fewer than 4 values → no fence computed → nothing dropped."""
        records = [make_record(1000.0), make_record(20.0), make_record(21.0)]
        t = OutlierTransformer({"fields": ["temp"]})
        result = t.transform(records)
        assert result.dropped == 0

    def test_missing_field_in_record_ignored(self):
        records = [
            SensorRecord(station_id="s1", timestamp=TS, sensor_data={"humidity": 50.0})
        ] + [make_record(float(t)) for t in range(20, 28)]
        t = OutlierTransformer({"fields": ["temp"]})
        result = t.transform(records)
        # record without 'temp' should pass through
        assert any("temp" not in r.sensor_data for r in result.records)
