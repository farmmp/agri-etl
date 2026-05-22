"""Unit tests for CsvReader."""

import textwrap
from datetime import datetime
from pathlib import Path

import pytest

from agri_etl.ingestion.csv_reader import CsvReader


CSV_CONTENT = textwrap.dedent("""\
    sensor_id,timestamp,temperature,humidity
    sensor-01,2024-03-10T08:00:00,18.2,72
    sensor-01,2024-03-10T09:00:00,19.5,70
    sensor-02,2024-03-10T08:30:00,17.8,75
    sensor-01,2024-03-11T08:00:00,20.1,68
""")


@pytest.fixture()
def csv_file(tmp_path: Path) -> Path:
    p = tmp_path / "sensors.csv"
    p.write_text(CSV_CONTENT, encoding="utf-8")
    return p


@pytest.fixture()
def reader_config(csv_file: Path) -> dict:
    return {
        "file_path": str(csv_file),
        "timestamp_column": "timestamp",
        "source_id_column": "sensor_id",
    }


class TestCsvReader:
    def test_missing_config_raises(self):
        with pytest.raises(ValueError):
            CsvReader({"file_path": "/tmp/x.csv"})

    def test_connect_raises_when_file_missing(self, reader_config):
        reader_config["file_path"] = "/nonexistent/path.csv"
        reader = CsvReader(reader_config)
        with pytest.raises(FileNotFoundError):
            reader.connect()

    def test_read_batch_filters_by_time_window(self, reader_config):
        start = datetime(2024, 3, 10, 0, 0)
        end = datetime(2024, 3, 10, 23, 59)
        with CsvReader(reader_config) as r:
            records = list(r.read_batch(start, end))
        assert len(records) == 3
        assert all(r.timestamp.date().isoformat() == "2024-03-10" for r in records)

    def test_record_metrics_exclude_meta_columns(self, reader_config):
        start = datetime(2024, 3, 10, 8, 0)
        end = datetime(2024, 3, 10, 8, 1)
        with CsvReader(reader_config) as r:
            records = list(r.read_batch(start, end))
        assert len(records) == 1
        assert "temperature" in records[0].metrics
        assert "sensor_id" not in records[0].metrics
        assert "timestamp" not in records[0].metrics

    def test_read_without_connect_raises(self, reader_config):
        reader = CsvReader(reader_config)
        with pytest.raises(RuntimeError, match="not connected"):
            list(reader.read_batch(datetime(2024, 1, 1), datetime(2024, 12, 31)))
