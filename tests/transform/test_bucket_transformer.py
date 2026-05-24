import pytest
from datetime import datetime, timezone
from agri_etl.ingestion.base_reader import SensorRecord
from agri_etl.transform.bucket_transformer import BucketTransformer


TS = datetime(2024, 6, 1, 12, 0, 0, tzinfo=timezone.utc)


def make_record(readings: dict) -> SensorRecord:
    return SensorRecord(sensor_id="s1", timestamp=TS, readings=readings)


BUCKET_SPECS = [
    {"label": "low", "min": 0, "max": 20},
    {"label": "medium", "min": 20, "max": 40},
    {"label": "high", "min": 40, "max": 100},
]


class TestBucketTransformerInit:
    def test_missing_buckets_raises(self):
        with pytest.raises(ValueError, match="'buckets'"):
            BucketTransformer({})

    def test_empty_buckets_raises(self):
        with pytest.raises(ValueError, match="must not be empty"):
            BucketTransformer({"buckets": {}})

    def test_invalid_buckets_type_raises(self):
        with pytest.raises(TypeError, match="must be a dict"):
            BucketTransformer({"buckets": "bad"})

    def test_empty_spec_list_raises(self):
        with pytest.raises(ValueError, match="non-empty list"):
            BucketTransformer({"buckets": {"temp": []}})

    def test_spec_missing_label_raises(self):
        with pytest.raises(ValueError, match="'label'"):
            BucketTransformer({"buckets": {"temp": [{"min": 0, "max": 10}]}})

    def test_spec_missing_min_and_max_raises(self):
        with pytest.raises(ValueError, match="'min' or 'max'"):
            BucketTransformer({"buckets": {"temp": [{"label": "x"}]}})

    def test_valid_config_accepted(self):
        t = BucketTransformer({"buckets": {"temp": BUCKET_SPECS}})
        assert t is not None


class TestBucketTransformerTransform:
    def _make_transformer(self, extra=None):
        cfg = {"buckets": {"temp": BUCKET_SPECS}}
        if extra:
            cfg.update(extra)
        return BucketTransformer(cfg)

    def test_assigns_low_bucket(self):
        t = self._make_transformer()
        result = t.transform([make_record({"temp": 10.0})])
        assert len(result.passed) == 1
        assert result.passed[0].readings["temp_bucket"] == "low"

    def test_assigns_medium_bucket(self):
        t = self._make_transformer()
        result = t.transform([make_record({"temp": 25.0})])
        assert result.passed[0].readings["temp_bucket"] == "medium"

    def test_assigns_high_bucket(self):
        t = self._make_transformer()
        result = t.transform([make_record({"temp": 55.0})])
        assert result.passed[0].readings["temp_bucket"] == "high"

    def test_default_label_for_unmatched(self):
        t = self._make_transformer({"default_label": "out_of_range"})
        result = t.transform([make_record({"temp": 200.0})])
        assert result.passed[0].readings["temp_bucket"] == "out_of_range"

    def test_custom_output_suffix(self):
        t = BucketTransformer({"buckets": {"temp": BUCKET_SPECS}, "output_suffix": "_bin"})
        result = t.transform([make_record({"temp": 10.0})])
        assert "temp_bin" in result.passed[0].readings

    def test_missing_field_skipped(self):
        t = self._make_transformer()
        result = t.transform([make_record({"humidity": 50.0})])
        assert len(result.passed) == 1
        assert "temp_bucket" not in result.passed[0].readings

    def test_none_value_skipped(self):
        t = self._make_transformer()
        result = t.transform([make_record({"temp": None})])
        assert len(result.passed) == 1

    def test_original_readings_preserved(self):
        t = self._make_transformer()
        result = t.transform([make_record({"temp": 15.0, "humidity": 80.0})])
        assert result.passed[0].readings["humidity"] == 80.0
        assert result.passed[0].readings["temp"] == 15.0

    def test_empty_input_returns_empty(self):
        t = self._make_transformer()
        result = t.transform([])
        assert result.passed == []
        assert result.failed == []
