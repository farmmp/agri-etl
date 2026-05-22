"""Tests for agri_etl.load.csv_loader.CsvLoader."""

from __future__ import annotations

import csv
import os
from datetime import datetime, timezone

import pytest

from agri_etl.ingestion.base_reader import SensorRecord
from agri_etl.load.csv_loader import CsvLoader
from agri_etl.transform.base_transformer import TransformResult


@pytest.fixture()
def tmp_csv(tmp_path):
    return str(tmp_path / "output.csv")


def _make_result(*sensor_ids: str) -> TransformResult:
    ts = datetime(2024, 6, 1, 12, 0, 0, tzinfo=timezone.utc)
    records = [
        SensorRecord(timestamp=ts, sensor_id=sid, readings={"temp": 22.5, "humidity": 60.0})
        for sid in sensor_ids
    ]
    return TransformResult(records=records, dropped=0, errors=[])


class TestCsvLoaderInit:
    def test_missing_path_raises(self):
        with pytest.raises(ValueError, match="'path'"):
            CsvLoader(config={})

    def test_defaults_applied(self, tmp_csv):
        loader = CsvLoader(config={"path": tmp_csv})
        assert loader._delimiter == ","
        assert loader._write_header is True


class TestCsvLoaderWriteBatch:
    def test_write_batch_without_connect_raises(self, tmp_csv):
        loader = CsvLoader(config={"path": tmp_csv})
        with pytest.raises(RuntimeError, match="not connected"):
            loader.write_batch(_make_result("s1"))

    def test_records_written_count(self, tmp_csv):
        loader = CsvLoader(config={"path": tmp_csv})
        loader.connect()
        result = loader.write_batch(_make_result("s1", "s2"))
        loader.disconnect()
        assert result.records_written == 2
        assert result.success is True

    def test_csv_file_contains_header(self, tmp_csv):
        loader = CsvLoader(config={"path": tmp_csv})
        loader.connect()
        loader.write_batch(_make_result("s1"))
        loader.disconnect()
        with open(tmp_csv, newline="", encoding="utf-8") as fh:
            rows = list(csv.reader(fh))
        assert rows[0][0] == "timestamp"

    def test_no_duplicate_header_on_reconnect(self, tmp_csv):
        for _ in range(2):
            loader = CsvLoader(config={"path": tmp_csv})
            loader.connect()
            loader.write_batch(_make_result("s1"))
            loader.disconnect()
        with open(tmp_csv, newline="", encoding="utf-8") as fh:
            rows = list(csv.reader(fh))
        header_rows = [r for r in rows if r and r[0] == "timestamp"]
        assert len(header_rows) == 1

    def test_disconnect_closes_file(self, tmp_csv):
        loader = CsvLoader(config={"path": tmp_csv})
        loader.connect()
        loader.disconnect()
        assert loader._file is None
