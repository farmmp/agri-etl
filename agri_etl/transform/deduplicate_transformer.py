"""Deduplication transformer — drops records already seen within a window."""
from __future__ import annotations

from collections import deque
from typing import Any

from agri_etl.ingestion.base_reader import SensorRecord
from agri_etl.transform.base_transformer import BaseTransformer, TransformResult


class DeduplicateTransformer(BaseTransformer):
    """Drop duplicate records based on (sensor_id, timestamp) pairs.

    Config keys:
        window_size (int) – optional (default 1000); maximum number of
                            (sensor_id, timestamp) fingerprints held in memory.
    """

    def _validate_config(self) -> None:
        window_size = self.config.get("window_size", 1000)
        if not isinstance(window_size, int) or window_size < 1:
            raise ValueError("'window_size' must be a positive integer")

    def __init__(self, config: dict[str, Any]) -> None:
        super().__init__(config)
        window_size: int = self.config.get("window_size", 1000)
        self._seen: set[tuple[str, str]] = set()
        self._order: deque[tuple[str, str]] = deque(maxlen=window_size)
        self._window_size = window_size

    def _fingerprint(self, record: SensorRecord) -> tuple[str, str]:
        return (record.sensor_id, record.timestamp.isoformat())

    def transform(self, record: SensorRecord) -> TransformResult:
        fp = self._fingerprint(record)
        if fp in self._seen:
            return TransformResult(
                record=None,
                dropped=True,
                error=f"Duplicate record: sensor_id={record.sensor_id} "
                      f"timestamp={record.timestamp.isoformat()}",
            )

        # Evict oldest entry when window is full
        if len(self._order) == self._window_size:
            oldest = self._order[0]  # deque will auto-evict on append
            self._seen.discard(oldest)

        self._order.append(fp)
        self._seen.add(fp)
        return TransformResult(record=record, dropped=False, error=None)
