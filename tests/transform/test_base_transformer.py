"""Tests for BaseTransformer abstract interface."""

import pytest
from datetime import datetime, timezone

from agri_etl.ingestion.base_reader import SensorRecord
from agri_etl.transform.base_transformer import BaseTransformer, TransformResult


class _ConcreteTransformer(BaseTransformer):
    """Minimal concrete transformer for testing."""

    def transform(self, record: SensorRecord) -> TransformResult:
        return TransformResult(record=record, transformed=dict(record.values))


@pytest.fixture
def sample_record() -> SensorRecord:
    return SensorRecord(
        sensor_id="s1",
        timestamp=datetime(2024, 1, 1, tzinfo=timezone.utc),
        values={"temperature": 20.0},
    )


class TestTransformResult:
    def test_to_dict_contains_all_keys(self, sample_record):
        result = TransformResult(
            record=sample_record,
            transformed={"temperature": 20.0},
            warnings=["w1"],
        )
        d = result.to_dict()
        assert "record" in d
        assert "transformed" in d
        assert "warnings" in d
        assert "dropped" in d

    def test_dropped_defaults_false(self, sample_record):
        result = TransformResult(record=sample_record)
        assert result.dropped is False


class TestBaseTransformer:
    def test_transform_batch_returns_all_results(self, sample_record):
        t = _ConcreteTransformer(config={})
        records = [sample_record, sample_record]
        results = t.transform_batch(records)
        assert len(results) == 2

    def test_transform_batch_empty(self):
        t = _ConcreteTransformer(config={})
        assert t.transform_batch([]) == []

    def test_config_stored(self):
        cfg = {"key": "value"}
        t = _ConcreteTransformer(config=cfg)
        assert t.config is cfg
