from __future__ import annotations

import datetime
import pytest

from agri_etl.ingestion.base_reader import SensorRecord
from agri_etl.transform.smooth_transformer import SmoothTransformer

TS = datetime.datetime(2024, 1, 1, 12, 0, 0)


def make_record(readings: dict) -> SensorRecord:
    return SensorRecord(sensor_id="s1", timestamp=TS, readings=readings)


# ---------------------------------------------------------------------------
# Init / validation
# ---------------------------------------------------------------------------

class TestSmoothTransformerInit:
    def test_missing_fields_raises(self):
        with pytest.raises(ValueError, match="requires 'fields'"):
            SmoothTransformer({})

    def test_empty_fields_raises(self):
        with pytest.raises(ValueError, match="non-empty dict"):
            SmoothTransformer({"fields": {}})

    def test_invalid_fields_type_raises(self):
        with pytest.raises(ValueError, match="non-empty dict"):
            SmoothTransformer({"fields": ["temp"]})

    def test_window_too_small_raises(self):
        with pytest.raises(ValueError, match="integer >= 2"):
            SmoothTransformer({"fields": {"temp": 1}})

    def test_window_non_int_raises(self):
        with pytest.raises(ValueError, match="integer >= 2"):
            SmoothTransformer({"fields": {"temp": 3.0}})

    def test_invalid_fill_partial_raises(self):
        with pytest.raises(ValueError, match="fill_partial"):
            SmoothTransformer({"fields": {"temp": 3}, "fill_partial": "yes"})

    def test_valid_config_accepted(self):
        t = SmoothTransformer({"fields": {"temp": 3}, "fill_partial": True})
        assert t is not None


# ---------------------------------------------------------------------------
# Behaviour
# ---------------------------------------------------------------------------

class TestSmoothTransformerBehaviour:
    def _make(self, window: int = 3, fill_partial: bool = False) -> SmoothTransformer:
        return SmoothTransformer({"fields": {"temp": window}, "fill_partial": fill_partial})

    def test_records_dropped_until_window_full(self):
        t = self._make(window=3, fill_partial=False)
        r1 = make_record({"temp": 10.0})
        r2 = make_record({"temp": 20.0})
        result = t.transform([r1, r2])
        assert len(result.passed) == 0
        assert len(result.dropped) == 2

    def test_smoothed_value_after_window_full(self):
        t = self._make(window=3, fill_partial=False)
        records = [make_record({"temp": float(v)}) for v in [10, 20, 30]]
        result = t.transform(records)
        assert len(result.passed) == 1
        assert result.passed[0].readings["temp"] == pytest.approx(20.0)

    def test_fill_partial_emits_from_first_record(self):
        t = self._make(window=3, fill_partial=True)
        r = make_record({"temp": 15.0})
        result = t.transform([r])
        assert len(result.passed) == 1
        assert result.passed[0].readings["temp"] == pytest.approx(15.0)

    def test_sliding_window_advances(self):
        t = self._make(window=2, fill_partial=False)
        records = [make_record({"temp": float(v)}) for v in [10, 20, 30]]
        result = t.transform(records)
        assert len(result.passed) == 2
        assert result.passed[0].readings["temp"] == pytest.approx(15.0)
        assert result.passed[1].readings["temp"] == pytest.approx(25.0)

    def test_non_numeric_field_emits_error_and_passes_record(self):
        t = self._make(window=2, fill_partial=True)
        r = make_record({"temp": "hot"})
        result = t.transform([r])
        assert len(result.errors) == 1
        assert "not numeric" in result.errors[0]
        # record still passes (only smoothing skipped)
        assert len(result.passed) == 1

    def test_missing_field_in_record_is_ignored(self):
        t = self._make(window=2, fill_partial=True)
        r = make_record({"humidity": 55.0})  # no 'temp'
        result = t.transform([r])
        assert len(result.passed) == 1
        assert result.passed[0].readings["humidity"] == 55.0

    def test_other_readings_preserved(self):
        t = self._make(window=2, fill_partial=True)
        r = make_record({"temp": 20.0, "humidity": 80.0})
        result = t.transform([r])
        assert result.passed[0].readings["humidity"] == 80.0
