import pytest
from datetime import datetime, timezone

from agri_etl.ingestion.base_reader import SensorRecord
from agri_etl.transform.split_transformer import SplitTransformer


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

class TestSplitTransformerInit:
    def test_missing_splits_raises(self):
        with pytest.raises(KeyError, match="splits"):
            SplitTransformer({})

    def test_empty_splits_raises(self):
        with pytest.raises(ValueError, match="must not be empty"):
            SplitTransformer({"splits": {}})

    def test_invalid_splits_type_raises(self):
        with pytest.raises(TypeError, match="must be a dict"):
            SplitTransformer({"splits": ["a"]})

    def test_spec_missing_delimiter_raises(self):
        with pytest.raises(KeyError, match="delimiter"):
            SplitTransformer({"splits": {"loc": {"targets": ["lat", "lon"]}}})

    def test_spec_missing_targets_raises(self):
        with pytest.raises(ValueError, match="targets"):
            SplitTransformer({"splits": {"loc": {"delimiter": ",", "targets": []}}})

    def test_invalid_on_error_raises(self):
        with pytest.raises(ValueError, match="on_error"):
            SplitTransformer({
                "splits": {"loc": {"delimiter": ",", "targets": ["a"]}},
                "on_error": "ignore",
            })

    def test_valid_config_accepted(self):
        t = SplitTransformer({
            "splits": {"loc": {"delimiter": ",", "targets": ["lat", "lon"]}}
        })
        assert t is not None


# ---------------------------------------------------------------------------
# Transform behaviour
# ---------------------------------------------------------------------------

class TestSplitTransformerTransform:
    def _make(self, **kwargs):
        base = {"splits": {"loc": {"delimiter": ",", "targets": ["lat", "lon"]}}}
        base.update(kwargs)
        return SplitTransformer(base)

    def test_basic_split(self):
        t = self._make()
        r = make_record({"loc": "12.5,45.3", "temp": 20.0})
        result = t.transform([r])
        assert len(result.records) == 1
        rec = result.records[0]
        assert rec.readings["lat"] == "12.5"
        assert rec.readings["lon"] == "45.3"

    def test_original_field_preserved(self):
        t = self._make()
        r = make_record({"loc": "12.5,45.3"})
        result = t.transform([r])
        assert "loc" in result.records[0].readings

    def test_missing_field_skip(self):
        t = self._make(on_error="skip")
        r = make_record({"temp": 20.0})
        result = t.transform([r])
        assert len(result.records) == 0

    def test_missing_field_null(self):
        t = self._make(on_error="null")
        r = make_record({"temp": 20.0})
        result = t.transform([r])
        assert len(result.records) == 1
        assert result.records[0].readings["lat"] is None
        assert result.records[0].readings["lon"] is None

    def test_missing_field_raise(self):
        t = self._make(on_error="raise")
        r = make_record({"temp": 20.0})
        with pytest.raises(ValueError, match="loc"):
            t.transform([r])

    def test_too_few_parts_skip(self):
        t = self._make(on_error="skip")
        r = make_record({"loc": "12.5"})
        result = t.transform([r])
        assert len(result.records) == 0
        assert len(result.errors) == 1

    def test_too_few_parts_null(self):
        t = self._make(on_error="null")
        r = make_record({"loc": "12.5"})
        result = t.transform([r])
        assert result.records[0].readings["lat"] == "12.5"
        assert result.records[0].readings["lon"] is None

    def test_extra_parts_ignored(self):
        t = self._make()
        r = make_record({"loc": "12.5,45.3,99.0"})
        result = t.transform([r])
        assert result.records[0].readings["lat"] == "12.5"
        assert result.records[0].readings["lon"] == "45.3"

    def test_empty_input(self):
        t = self._make()
        result = t.transform([])
        assert result.records == []
        assert result.errors == []
