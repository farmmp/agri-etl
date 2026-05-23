from __future__ import annotations

from typing import Any

from agri_etl.transform.base_transformer import BaseTransformer, TransformResult
from agri_etl.ingestion.base_reader import SensorRecord


class InterpolateTransformer(BaseTransformer):
    """Fill missing (None) numeric field values using linear interpolation
    across a rolling window of recent records."""

    def _validate_config(self) -> None:
        fields = self.config.get("fields")
        if fields is None:
            raise ValueError("InterpolateTransformer requires 'fields' in config")
        if not isinstance(fields, list) or len(fields) == 0:
            raise ValueError("'fields' must be a non-empty list")
        if not all(isinstance(f, str) for f in fields):
            raise ValueError("All entries in 'fields' must be strings")

        window = self.config.get("window_size", 10)
        if not isinstance(window, int) or window < 2:
            raise ValueError("'window_size' must be an integer >= 2")

    def __init__(self, config: dict[str, Any]) -> None:
        super().__init__(config)
        self._fields: list[str] = self.config["fields"]
        self._window: int = self.config.get("window_size", 10)
        # history[field] = list of (index, value) for non-None entries
        self._history: dict[str, list[tuple[int, float]]] = {f: [] for f in self._fields}
        self._counter: int = 0

    def transform(self, records: list[SensorRecord]) -> TransformResult:
        out: list[SensorRecord] = []
        errors: list[str] = []

        for record in records:
            new_readings = dict(record.readings)
            idx = self._counter
            self._counter += 1

            for field in self._fields:
                value = new_readings.get(field)
                if value is not None:
                    try:
                        new_readings[field] = float(value)
                        # Trim history to window
                        self._history[field].append((idx, float(value)))
                        self._history[field] = [
                            p for p in self._history[field]
                            if idx - p[0] < self._window
                        ]
                    except (TypeError, ValueError) as exc:
                        errors.append(f"Record {record.sensor_id}: {exc}")
                else:
                    hist = self._history[field]
                    if len(hist) >= 2:
                        x0, y0 = hist[-2]
                        x1, y1 = hist[-1]
                        if x1 != x0:
                            slope = (y1 - y0) / (x1 - x0)
                            new_readings[field] = y0 + slope * (idx - x0)
                        else:
                            new_readings[field] = y1
                    elif len(hist) == 1:
                        new_readings[field] = hist[-1][1]
                    # else: leave as None — no history available

            out.append(
                SensorRecord(
                    sensor_id=record.sensor_id,
                    timestamp=record.timestamp,
                    readings=new_readings,
                    meta=record.meta,
                )
            )

        return TransformResult(records=out, errors=errors)
