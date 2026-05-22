"""CSV file loader — appends transformed records to a CSV file."""

from __future__ import annotations

import csv
import os
from typing import Any

from agri_etl.load.base_loader import BaseLoader, LoadResult
from agri_etl.transform.base_transformer import TransformResult

_REQUIRED_FIELDS = ["timestamp", "sensor_id", "readings"]


class CsvLoader(BaseLoader):
    """Writes :class:`TransformResult` records to a CSV file.

    Config keys:
        path (str): Destination file path.  Required.
        delimiter (str): Field delimiter.  Default ``","``.
        write_header (bool): Write header row when file is new.  Default ``True``.
    """

    def _validate_config(self) -> None:
        if "path" not in self.config:
            raise ValueError("CsvLoader config must include 'path'")

    def __init__(self, config: dict[str, Any]) -> None:
        super().__init__(config)
        self._path: str = self.config["path"]
        self._delimiter: str = self.config.get("delimiter", ",")
        self._write_header: bool = self.config.get("write_header", True)
        self._file = None
        self._writer = None

    def connect(self) -> None:
        os.makedirs(os.path.dirname(self._path) or ".", exist_ok=True)
        file_exists = os.path.isfile(self._path)
        self._file = open(self._path, "a", newline="", encoding="utf-8")  # noqa: WPS515
        self._writer = csv.writer(self._file, delimiter=self._delimiter)
        if self._write_header and not file_exists:
            self._writer.writerow(["timestamp", "sensor_id", "metric", "value", "unit", "meta"])

    def disconnect(self) -> None:
        if self._file and not self._file.closed:
            self._file.close()
        self._file = None
        self._writer = None

    def write_batch(self, result: TransformResult) -> LoadResult:
        if self._writer is None:
            raise RuntimeError("CsvLoader is not connected. Call connect() first.")
        errors: list[str] = []
        written = 0
        for record in result.records:
            try:
                for metric, value in record.readings.items():
                    unit = (record.meta or {}).get("unit", "")
                    self._writer.writerow(
                        [record.timestamp.isoformat(), record.sensor_id, metric, value, unit, record.meta]
                    )
                written += 1
            except Exception as exc:  # noqa: BLE001
                errors.append(f"sensor={record.sensor_id}: {exc}")
        self._file.flush()
        return LoadResult(records_written=written, destination=self._path, errors=errors)
