from __future__ import annotations

from typing import Any

from agri_etl.transform.base_transformer import BaseTransformer, TransformResult
from agri_etl.ingestion.base_reader import SensorRecord


class OutlierTransformer(BaseTransformer):
    """Removes or caps records whose field values fall outside an IQR-based fence.

    Config keys:
        fields      (list[str])  – sensor_data keys to inspect.
        strategy    (str)        – "drop" (default) or "cap".
        iqr_factor  (float)      – multiplier for IQR fence (default 1.5).
    """

    _SUPPORTED_STRATEGIES = {"drop", "cap"}

    def _validate_config(self) -> None:
        fields = self.config.get("fields")
        if not fields:
            raise ValueError("OutlierTransformer requires 'fields'")
        if not isinstance(fields, list) or not all(isinstance(f, str) for f in fields):
            raise ValueError("'fields' must be a list of strings")
        strategy = self.config.get("strategy", "drop")
        if strategy not in self._SUPPORTED_STRATEGIES:
            raise ValueError(
                f"'strategy' must be one of {self._SUPPORTED_STRATEGIES}, got '{strategy}'"
            )
        iqr_factor = self.config.get("iqr_factor", 1.5)
        if not isinstance(iqr_factor, (int, float)) or iqr_factor <= 0:
            raise ValueError("'iqr_factor' must be a positive number")

    def transform(self, records: list[SensorRecord]) -> TransformResult:
        if not records:
            return TransformResult(records=[], dropped=0, errors=[])

        fields: list[str] = self.config["fields"]
        strategy: str = self.config.get("strategy", "drop")
        iqr_factor: float = float(self.config.get("iqr_factor", 1.5))

        # Compute per-field IQR fences from the batch
        fences: dict[str, tuple[float, float]] = {}
        for field in fields:
            values = [
                float(r.sensor_data[field])
                for r in records
                if field in r.sensor_data and r.sensor_data[field] is not None
            ]
            if len(values) < 4:
                continue
            sorted_vals = sorted(values)
            n = len(sorted_vals)
            q1 = sorted_vals[n // 4]
            q3 = sorted_vals[(3 * n) // 4]
            iqr = q3 - q1
            fences[field] = (q1 - iqr_factor * iqr, q3 + iqr_factor * iqr)

        out: list[SensorRecord] = []
        dropped = 0
        for record in records:
            new_data: dict[str, Any] = dict(record.sensor_data)
            skip = False
            for field, (lo, hi) in fences.items():
                if field not in new_data or new_data[field] is None:
                    continue
                val = float(new_data[field])
                if val < lo or val > hi:
                    if strategy == "drop":
                        skip = True
                        break
                    else:  # cap
                        new_data[field] = max(lo, min(hi, val))
            if skip:
                dropped += 1
            else:
                out.append(
                    SensorRecord(
                        station_id=record.station_id,
                        timestamp=record.timestamp,
                        sensor_data=new_data,
                        metadata=record.metadata,
                    )
                )
        return TransformResult(records=out, dropped=dropped, errors=[])
