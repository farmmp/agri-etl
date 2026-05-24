from __future__ import annotations

from collections import deque
from typing import Any, Dict, List

from agri_etl.ingestion.base_reader import SensorRecord
from agri_etl.transform.base_transformer import BaseTransformer, TransformResult


class SmoothTransformer(BaseTransformer):
    """Apply a simple moving-average smoothing to numeric sensor fields.

    Config keys:
        fields   (dict, required): mapping of field name -> window size (int >= 2).
        fill_partial (bool, optional): if True, emit smoothed value even when the
                     window is not yet full (uses available samples). Default False.
    """

    def _validate_config(self) -> None:
        fields = self.config.get("fields")
        if fields is None:
            raise ValueError("SmoothTransformer requires 'fields' in config")
        if not isinstance(fields, dict) or len(fields) == 0:
            raise ValueError("'fields' must be a non-empty dict mapping field->window_size")
        for field, window in fields.items():
            if not isinstance(window, int) or window < 2:
                raise ValueError(
                    f"Window size for field '{field}' must be an integer >= 2, got {window!r}"
                )

        fill_partial = self.config.get("fill_partial", False)
        if not isinstance(fill_partial, bool):
            raise ValueError("'fill_partial' must be a bool")

        self._buffers: Dict[str, deque] = {
            f: deque(maxlen=w) for f, w in fields.items()
        }
        self._fill_partial: bool = fill_partial

    def transform(self, records: List[SensorRecord]) -> TransformResult:
        passed: List[SensorRecord] = []
        dropped: List[SensorRecord] = []
        errors: List[str] = []

        fields: Dict[str, int] = self.config["fields"]

        for record in records:
            new_readings: Dict[str, Any] = dict(record.readings)
            skip = False

            for field, window_size in fields.items():
                if field not in new_readings:
                    continue
                value = new_readings[field]
                if not isinstance(value, (int, float)):
                    errors.append(
                        f"record {record.sensor_id}@{record.timestamp}: "
                        f"field '{field}' is not numeric, skipping smoothing"
                    )
                    continue

                buf = self._buffers[field]
                buf.append(float(value))

                if len(buf) < window_size and not self._fill_partial:
                    skip = True
                    break

                new_readings[field] = sum(buf) / len(buf)

            if skip:
                dropped.append(record)
            else:
                passed.append(
                    SensorRecord(
                        sensor_id=record.sensor_id,
                        timestamp=record.timestamp,
                        readings=new_readings,
                        meta=record.meta,
                    )
                )

        return TransformResult(passed=passed, dropped=dropped, errors=errors)
