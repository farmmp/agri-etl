"""CSV file reader for agricultural sensor data exports."""

import csv
import logging
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Iterator

from agri_etl.ingestion.base_reader import BaseReader, SensorRecord

logger = logging.getLogger(__name__)

REQUIRED_CONFIG = ["file_path", "timestamp_column", "source_id_column"]


class CsvReader(BaseReader):
    """
    Reads sensor records from a CSV file.

    Config keys:
        file_path (str): Path to the CSV file.
        timestamp_column (str): Column name for the timestamp.
        source_id_column (str): Column name for the sensor/station ID.
        timestamp_format (str): strptime format string (default ISO-8601).
        delimiter (str): CSV delimiter (default ',').
    """

    def __init__(self, config: Dict[str, Any]) -> None:
        super().__init__(config)
        self.validate_config(REQUIRED_CONFIG)
        self._file_path = Path(config["file_path"])
        self._ts_col = config["timestamp_column"]
        self._id_col = config["source_id_column"]
        self._ts_fmt = config.get("timestamp_format", None)
        self._delimiter = config.get("delimiter", ",")

    def connect(self) -> None:
        if not self._file_path.exists():
            raise FileNotFoundError(f"CSV file not found: {self._file_path}")
        self._connected = True
        logger.info("CsvReader connected to %s", self._file_path)

    def disconnect(self) -> None:
        self._connected = False
        logger.info("CsvReader disconnected")

    def _parse_timestamp(self, value: str) -> datetime:
        if self._ts_fmt:
            return datetime.strptime(value, self._ts_fmt)
        return datetime.fromisoformat(value)

    def read_batch(self, start: datetime, end: datetime) -> Iterator[SensorRecord]:
        if not self._connected:
            raise RuntimeError("Reader is not connected. Call connect() first.")

        with self._file_path.open(newline="", encoding="utf-8") as fh:
            reader = csv.DictReader(fh, delimiter=self._delimiter)
            for row in reader:
                ts = self._parse_timestamp(row[self._ts_col])
                if not (start <= ts <= end):
                    continue
                metrics = {
                    k: v for k, v in row.items()
                    if k not in (self._ts_col, self._id_col)
                }
                yield SensorRecord(
                    source_id=row[self._id_col],
                    timestamp=ts,
                    metrics=metrics,
                    raw=dict(row),
                )
