from __future__ import annotations

from collections import deque
from typing import Any, Deque, Dict, List

from agri_etl.ingestion.base_reader import SensorRecord
from agri_etl.transform.base_transformer import BaseTransformer, TransformResult

_SUPPORTED_FUNCTIONS = {"mean", "min", "max", "sum", "count"}


class WindowTransformer(BaseTransformer):
    """Compute rolling-window statistics over numeric sensor fields.

    Config keys:
        windows (dict): Mapping of field name -> {"size": int, "function": str}.
            ``size``     – number of records in the sliding window (>= 1).
            ``function`` – aggregation function: mean | min | max | sum | count.
        output_suffix (str): Suffix appended to the field name for the new
            computed column.  Defaults to ``"_window"``.
    """

    def _validate_config(self) -> None:
        windows = self.config.get("windows")
        if windows is None:
            raise ValueError("WindowTransformer requires 'windows' in config")
        if not isinstance(windows, dict) or len(windows) == 0:
            raise ValueError("'windows' must be a non-empty dict")
        for field, spec in windows.items():
            if not isinstance(spec, dict):
                raise ValueError(f"Window spec for '{field}' must be a dict")
            size = spec.get("size", 1)
            if not isinstance(size, int) or size < 1:
                raise ValueError(f"Window size for '{field}' must be an int >= 1")
            func = spec.get("function", "mean")
            if func not in _SUPPORTED_FUNCTIONS:
                raise ValueError(
                    f"Unsupported function '{func}' for field '{field}'. "
                    f"Choose from {sorted(_SUPPORTED_FUNCTIONS)}"
                )

    def __init__(self, config: Dict[str, Any]) -> None:
        super().__init__(config)
        self._buffers: Dict[str, Deque[float]] = {
            field: deque(maxlen=spec.get("size", 1))
            for field, spec in self.config["windows"].items()
        }
        self._suffix: str = self.config.get("output_suffix", "_window")

    def transform(self, records: List[SensorRecord]) -> TransformResult:
        out: List[SensorRecord] = []
        errors: List[str] = []
        windows: Dict[str, Dict[str, Any]] = self.config["windows"]

        for rec in records:
            new_readings = dict(rec.readings)
            for field, spec in windows.items():
                raw = rec.readings.get(field)
                if raw is None:
                    errors.append(
                        f"Record {rec.sensor_id}@{rec.timestamp}: "
                        f"field '{field}' missing, skipping window calc"
                    )
                    continue
                try:
                    value = float(raw)
                except (TypeError, ValueError):
                    errors.append(
                        f"Record {rec.sensor_id}@{rec.timestamp}: "
                        f"field '{field}' non-numeric, skipping window calc"
                    )
                    continue

                buf = self._buffers[field]
                buf.append(value)
                func = spec.get("function", "mean")
                vals = list(buf)
                if func == "mean":
                    result = sum(vals) / len(vals)
                elif func == "min":
                    result = min(vals)
                elif func == "max":
                    result = max(vals)
                elif func == "sum":
                    result = sum(vals)
                else:  # count
                    result = float(len(vals))
                new_readings[f"{field}{self._suffix}"] = result

            out.append(
                SensorRecord(
                    sensor_id=rec.sensor_id,
                    timestamp=rec.timestamp,
                    readings=new_readings,
                    metadata=rec.metadata,
                )
            )
        return TransformResult(records=out, errors=errors)
