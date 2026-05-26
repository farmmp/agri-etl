import datetime
import pytest

from agri_etl.ingestion.base_reader import SensorRecord
from agri_etl.transform.coalesce_transformer import CoalesceTransformer


TS = datetime.datetime(2024, 6, 1, 12, 0, 0)


def make_record(data: dict) -> SensorRecord:
    return SensorRecord(sensor_id="s1", timestamp=TS, data=data)


# ---------------------------------------------------------------------------
# Init / validation
# ---------------------------------------------------------------------------

class TestCoalesceTransformerInit:
    def test_missing_coalesces_raises(self):
        with pytest.raises(ValueError, match="coalesces"):
            CoalesceTransformer({})

    def test_empty_coalesces_raises(self):
        with pytest.raises(ValueError, match="must not be empty"):
            CoalesceTransformer({"coalesces": {}})

    def test_invalid_coalesces_type_raises(self):
        with pytest.raises(TypeError, match="dict"):
            CoalesceTransformer({"coalesces": ["a", "b"]})

    def test_empty_source_list_raises(self):
        with pytest.raises(ValueError, match="non-empty list"):
            CoalesceTransformer({"coalesces": {"temp": []}})

    def test_non_list_sources_raises(self):
        with pytest.raises(ValueError, match="non-empty list"):
            CoalesceTransformer({"coalesces": {"temp": "temp_primary"}})

    def test_valid_config_accepted(self):
        t = CoalesceTransformer({"coalesces": {"temp": ["a", "b"]}})
        assert t is not None


# ---------------------------------------------------------------------------
# Functional behaviour
# ---------------------------------------------------------------------------

class TestCoalesceTransformerTransform:
    def _make(self, coalesces, drop_sources=False):
        return CoalesceTransformer(
            {"coalesces": coalesces, "drop_sources": drop_sources}
        )

    def test_picks_first_non_null(self):
        t = self._make({"temp": ["t1", "t2", "t3"]})
        rec = make_record({"t1": None, "t2": 22.5, "t3": 10.0})
        result = t.transform([rec])
        assert result.records[0].data["temp"] == 22.5

    def test_picks_first_field_when_all_present(self):
        t = self._make({"temp": ["t1", "t2"]})
        rec = make_record({"t1": 18.0, "t2": 22.5})
        result = t.transform([rec])
        assert result.records[0].data["temp"] == 18.0

    def test_null_when_all_sources_null(self):
        t = self._make({"temp": ["t1", "t2"]})
        rec = make_record({"t1": None, "t2": None})
        result = t.transform([rec])
        assert result.records[0].data["temp"] is None

    def test_null_when_sources_missing(self):
        t = self._make({"temp": ["t1", "t2"]})
        rec = make_record({"humidity": 55.0})
        result = t.transform([rec])
        assert result.records[0].data["temp"] is None

    def test_drop_sources_removes_fields(self):
        t = self._make({"temp": ["t1", "t2"]}, drop_sources=True)
        rec = make_record({"t1": None, "t2": 22.5})
        result = t.transform([rec])
        data = result.records[0].data
        assert "temp" in data
        assert "t1" not in data
        assert "t2" not in data

    def test_sources_preserved_when_drop_false(self):
        t = self._make({"temp": ["t1", "t2"]}, drop_sources=False)
        rec = make_record({"t1": 5.0, "t2": 10.0})
        result = t.transform([rec])
        data = result.records[0].data
        assert "t1" in data
        assert "t2" in data

    def test_multiple_dest_fields(self):
        t = self._make({"temp": ["t1", "t2"], "humidity": ["rh1", "rh2"]})
        rec = make_record({"t1": None, "t2": 21.0, "rh1": 60.0})
        result = t.transform([rec])
        data = result.records[0].data
        assert data["temp"] == 21.0
        assert data["humidity"] == 60.0

    def test_empty_batch_returns_empty(self):
        t = self._make({"temp": ["t1"]})
        result = t.transform([])
        assert result.records == []
        assert result.errors == []
