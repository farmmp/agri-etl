import pytest
from datetime import datetime, timezone
from unittest.mock import MagicMock, patch, call

from agri_etl.ingestion.base_reader import SensorRecord
from agri_etl.load.base_loader import LoadResult
from agri_etl.pipeline import Pipeline


TS = datetime(2024, 1, 1, tzinfo=timezone.utc)


def _record(sid: str = "s1") -> SensorRecord:
    return SensorRecord(sensor_id=sid, timestamp=TS, readings={"temp": 20.0}, metadata={})


def _mock_reader(batches):
    reader = MagicMock()
    reader.read_batch.side_effect = batches
    return reader


def _mock_loader(written: int = 1):
    loader = MagicMock()
    loader.write_batch.return_value = LoadResult(records_written=written, errors=[])
    return loader


class TestPipelineInit:
    def test_invalid_batch_size_raises(self):
        with pytest.raises(ValueError, match="batch_size"):
            Pipeline(reader=MagicMock(), transformers=[], loader=MagicMock(), batch_size=0)

    def test_defaults_applied(self):
        p = Pipeline(reader=MagicMock(), transformers=[], loader=MagicMock())
        assert p.batch_size == 100


class TestPipelineRun:
    def test_empty_reader_returns_zero_counts(self):
        reader = _mock_reader([[]])
        loader = _mock_loader()
        p = Pipeline(reader=reader, transformers=[], loader=loader)
        summary = p.run()
        assert summary == {"records_read": 0, "records_written": 0, "records_dropped": 0}

    def test_records_passed_through_without_transformers(self):
        records = [_record(), _record()]
        reader = _mock_reader([records, []])
        loader = _mock_loader(written=2)
        p = Pipeline(reader=reader, transformers=[], loader=loader)
        summary = p.run()
        assert summary["records_read"] == 2
        assert summary["records_written"] == 2
        assert summary["records_dropped"] == 0

    def test_dropped_records_not_written(self):
        from agri_etl.transform.base_transformer import TransformResult
        record = _record()
        reader = _mock_reader([[record], []])
        loader = _mock_loader(written=0)
        transformer = MagicMock()
        transformer.transform.return_value = TransformResult(record=record, dropped=True, notes="filtered")
        p = Pipeline(reader=reader, transformers=[transformer], loader=loader)
        summary = p.run()
        assert summary["records_dropped"] == 1
        assert summary["records_written"] == 0
        loader.write_batch.assert_not_called()

    def test_connect_and_disconnect_called(self):
        reader = _mock_reader([[]])
        loader = _mock_loader()
        p = Pipeline(reader=reader, transformers=[], loader=loader)
        p.run()
        reader.connect.assert_called_once()
        reader.disconnect.assert_called_once()
        loader.connect.assert_called_once()
        loader.disconnect.assert_called_once()

    def test_disconnect_called_even_on_error(self):
        reader = MagicMock()
        reader.read_batch.side_effect = RuntimeError("boom")
        loader = _mock_loader()
        p = Pipeline(reader=reader, transformers=[], loader=loader)
        with pytest.raises(RuntimeError):
            p.run()
        reader.disconnect.assert_called_once()
        loader.disconnect.assert_called_once()

    def test_multiple_batches_accumulated(self):
        reader = _mock_reader([[_record()], [_record(), _record()], []])
        loader = MagicMock()
        loader.write_batch.side_effect = [
            LoadResult(records_written=1, errors=[]),
            LoadResult(records_written=2, errors=[]),
        ]
        p = Pipeline(reader=reader, transformers=[], loader=loader)
        summary = p.run()
        assert summary["records_read"] == 3
        assert summary["records_written"] == 3
