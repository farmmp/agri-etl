"""RateTransformer — computes per-second rate of change between consecutive records."""
from __future__ import annotations

from typing import Any, Dict, List

from agri_etl.transform.base_transformer import BaseTransformer, TransformResult
from agri_etl.ingestion.base_reader import SensorRecord


class RateTransformer(BaseTransformer):
    """Emit rate-of-change (delta / elapsed_seconds) for specified numeric fields.

    Config keys:
        fields (list[str]): field names to differentiate.
        output_suffix (str): suffix appended to field name for the new column (default "_rate").
        drop_first (bool): whether to drop the first record (no previous value). Default True.
    """

    def _validate_config(self) -> None:
        fields = self.config.get("fields")
        if not fields:
            raise ValueError("RateTransformer requires 'fields'")
        if not isinstance(fields, list):
            raise TypeError("'fields' must be a list")
        if len(fields) == 0:
            raise ValueError("'fields' must not be empty")
        for f in fields:
            if not isinstance(f, str):
                raise TypeError("each entry in 'fields' must be a str")

    def __init__(self, config: Dict[str, Any]) -> None:
        super().__init__(config)
        self._prev: SensorRecord | None = None

    def transform(self, records: List[SensorRecord]) -> TransformResult:
        fields: List[str] = self.config["fields"]
        suffix: str = self.config.get("output_suffix", "_rate")
        drop_first: bool = self.config.get("drop_first", True)

        out: List[SensorRecord] = []
        errors: List[str] = []

        for rec in records:
            if self._prev is None:
                self._prev = rec
                if not drop_first:
                    out.append(rec)
                continue

            elapsed = (rec.timestamp - self._prev.timestamp).total_seconds()
            if elapsed <= 0:
                errors.append(
                    f"Non-positive elapsed time for record {rec.sensor_id} at {rec.timestamp}; skipped"
                )
                self._prev = rec
                continue

            new_readings: Dict[str, Any] = dict(rec.readings)
            for field in fields:
                prev_val = self._prev.readings.get(field)
                curr_val = rec.readings.get(field)
                if prev_val is None or curr_val is None:
                    errors.append(
                        f"Missing field '{field}' for rate calculation at {rec.timestamp}"
                    )
                    continue
                try:
                    new_readings[f"{field}{suffix}"] = (float(curr_val) - float(prev_val)) / elapsed
                except (TypeError, ValueError) as exc:
                    errors.append(f"Cannot compute rate for '{field}': {exc}")

            out.append(
                SensorRecord(
                    sensor_id=rec.sensor_id,
                    timestamp=rec.timestamp,
                    readings=new_readings,
                    meta=rec.meta,
                )
            )
            self._prev = rec

        return TransformResult(records=out, errors=errors)
