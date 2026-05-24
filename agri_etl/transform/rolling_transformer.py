from __future__ import annotations

from collections import deque
from typing import Any, Deque, Dict, List

from agri_etl.transform.base_transformer import BaseTransformer, TransformResult
from agri_etl.ingestion.base_reader import SensorRecord

_SUPPORTED = {"mean", "min", "max", "sum", "count"}


class RollingTransformer(BaseTransformer):
    """Compute rolling-window statistics over specified numeric fields."""

    def _validate_config(self) -> None:
        windows = self.config.get("windows")
        if windows is None:
            raise ValueError("RollingTransformer requires 'windows' in config")
        if not isinstance(windows, dict) or not windows:
            raise ValueError("'windows' must be a non-empty dict")
        for field, spec in windows.items():
            if not isinstance(spec, dict):
                raise ValueError(f"spec for field '{field}' must be a dict")
            size = spec.get("size")
            if not isinstance(size, int) or size < 1:
                raise ValueError(f"'size' for field '{field}' must be a positive int")
            func = spec.get("function", "mean")
            if func not in _SUPPORTED:
                raise ValueError(
                    f"Unsupported function '{func}' for field '{field}'. "
                    f"Choose from {sorted(_SUPPORTED)}"
                )

    def __init__(self, config: Dict[str, Any]) -> None:
        super().__init__(config)
        self._buffers: Dict[str, Deque[float]] = {}
        for field, spec in self.config["windows"].items():
            self._buffers[field] = deque(maxlen=spec["size"])

    def transform(self, records: List[SensorRecord]) -> TransformResult:
        out: List[SensorRecord] = []
        errors: List[str] = []
        windows: Dict[str, Any] = self.config["windows"]

        for rec in records:
            new_readings = dict(rec.readings)
            for field, spec in windows.items():
                raw = rec.readings.get(field)
                if raw is None:
                    errors.append(
                        f"record {rec.sensor_id}@{rec.timestamp}: missing field '{field}'"
                    )
                    continue
                try:
                    val = float(raw)
                except (TypeError, ValueError):
                    errors.append(
                        f"record {rec.sensor_id}@{rec.timestamp}: "
                        f"cannot cast '{field}' to float"
                    )
                    continue

                buf = self._buffers[field]
                buf.append(val)
                func = spec.get("function", "mean")
                out_field = spec.get("output", f"{field}_rolling_{func}")

                if func == "mean":
                    new_readings[out_field] = sum(buf) / len(buf)
                elif func == "min":
                    new_readings[out_field] = min(buf)
                elif func == "max":
                    new_readings[out_field] = max(buf)
                elif func == "sum":
                    new_readings[out_field] = sum(buf)
                elif func == "count":
                    new_readings[out_field] = len(buf)

            out.append(
                SensorRecord(
                    sensor_id=rec.sensor_id,
                    timestamp=rec.timestamp,
                    readings=new_readings,
                    metadata=rec.metadata,
                )
            )

        return TransformResult(records=out, errors=errors)
