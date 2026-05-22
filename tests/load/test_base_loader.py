"""Tests for agri_etl.load.base_loader."""

from __future__ import annotations

import pytest

from agri_etl.load.base_loader import BaseLoader, LoadResult
from agri_etl.transform.base_transformer import TransformResult


# ---------------------------------------------------------------------------
# Minimal concrete implementation used across tests
# ---------------------------------------------------------------------------

class _ConcreteLoader(BaseLoader):
    def connect(self) -> None:
        pass

    def disconnect(self) -> None:
        pass

    def write_batch(self, result: TransformResult) -> LoadResult:
        return LoadResult(records_written=len(result.records), destination="memory")


# ---------------------------------------------------------------------------
# LoadResult
# ---------------------------------------------------------------------------

class TestLoadResult:
    def test_success_when_no_errors(self):
        lr = LoadResult(records_written=3, destination="file.csv")
        assert lr.success is True

    def test_failure_when_errors_present(self):
        lr = LoadResult(records_written=0, destination="file.csv", errors=["oops"])
        assert lr.success is False

    def test_to_dict_contains_all_keys(self):
        lr = LoadResult(records_written=5, destination="out.csv")
        d = lr.to_dict()
        assert set(d.keys()) == {"records_written", "destination", "errors", "success"}


# ---------------------------------------------------------------------------
# BaseLoader
# ---------------------------------------------------------------------------

class TestBaseLoader:
    def test_non_dict_config_raises(self):
        with pytest.raises(TypeError, match="config must be a dict"):
            _ConcreteLoader(config="not-a-dict")  # type: ignore[arg-type]

    def test_accepts_valid_config(self):
        loader = _ConcreteLoader(config={"key": "value"})
        assert loader.config["key"] == "value"

    def test_write_batch_returns_load_result(self):
        loader = _ConcreteLoader(config={})
        tr = TransformResult(records=[], dropped=0, errors=[])
        result = loader.write_batch(tr)
        assert isinstance(result, LoadResult)
