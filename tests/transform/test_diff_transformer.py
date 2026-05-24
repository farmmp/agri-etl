import pytest
from datetime import datetime, timezone
from agri_etl.ingestion.base_reader import SensorRecord
from agri_etl.transform.diff_transformer import DiffTransformer


TS = datetime(2024, 1, 1, tzinfo=timezone.utc)


def make_record(data, sensor_id="s1"):
    return SensorRecord(sensor_id=sensor_id, timestamp=TS, data=data)


# ---------------------------------------------------------------------------
# Init / validation
# ---------------------------------------------------------------------------

class TestDiffTransformerInit:
    def test_missing_fields_raises(self):
        with pytest.raises(ValueError, match="'fields'"):
            DiffTransformer({})

    def test_empty_fields_raises(self):
        with pytest.raises(ValueError, match="non-empty list"):
            DiffTransformer({"fields": []})

    def test_invalid_fields_type_raises(self):
        with pytest.raises(ValueError, match="non-empty list"):
            DiffTransformer({"fields": "temp"})

    def test_non_string_field_raises(self):
        with pytest.raises(ValueError, match="string"):
            DiffTransformer({"fields": [1, 2]})

    def test_invalid_order_zero_raises(self):
        with pytest.raises(ValueError, match="positive integer"):
            DiffTransformer({"fields": ["temp"], "order": 0})

    def test_invalid_order_negative_raises(self):
        with pytest.raises(ValueError, match="positive integer"):
            DiffTransformer({"fields": ["temp"], "order": -1})

    def test_valid_config_accepted(self):
        t = DiffTransformer({"fields": ["temp"], "order": 2})
        assert t is not None


# ---------------------------------------------------------------------------
# Behaviour
# ---------------------------------------------------------------------------

class TestDiffTransformerTransform:
    def test_first_record_dropped_order1(self):
        t = DiffTransformer({"fields": ["temp"]})
        result = t.transform([make_record({"temp": 10.0})])
        assert result.dropped == 1
        assert len(result.records) == 0

    def test_diff_computed_correctly(self):
        t = DiffTransformer({"fields": ["temp"]})
        r1 = make_record({"temp": 10.0})
        r2 = make_record({"temp": 13.0})
        result = t.transform([r1, r2])
        assert result.dropped == 1
        assert len(result.records) == 1
        assert result.records[0].data["temp"] == pytest.approx(3.0)

    def test_second_order_diff(self):
        t = DiffTransformer({"fields": ["temp"], "order": 2})
        records = [make_record({"temp": float(v)}) for v in [1, 3, 6, 10]]
        result = t.transform(records)
        # 1st diffs: 2, 3, 4  — 2nd diffs: 1, 1
        assert result.dropped == 2
        assert len(result.records) == 2
        assert result.records[0].data["temp"] == pytest.approx(1.0)
        assert result.records[1].data["temp"] == pytest.approx(1.0)

    def test_non_target_fields_preserved(self):
        t = DiffTransformer({"fields": ["temp"]})
        r1 = make_record({"temp": 5.0, "humidity": 80})
        r2 = make_record({"temp": 8.0, "humidity": 75})
        result = t.transform([r1, r2])
        assert result.records[0].data["humidity"] == 75

    def test_missing_field_in_record_skipped_gracefully(self):
        t = DiffTransformer({"fields": ["temp"]})
        r1 = make_record({"humidity": 80})
        r2 = make_record({"humidity": 75})
        result = t.transform([r1, r2])
        # field absent — no diff computed, records pass through
        assert len(result.records) == 2

    def test_state_persists_across_calls(self):
        t = DiffTransformer({"fields": ["temp"]})
        t.transform([make_record({"temp": 10.0})])
        result = t.transform([make_record({"temp": 15.0})])
        assert len(result.records) == 1
        assert result.records[0].data["temp"] == pytest.approx(5.0)
