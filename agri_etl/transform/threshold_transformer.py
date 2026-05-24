from __future__ import annotations

from typing import Any

from agri_etl.transform.base_transformer import BaseTransformer, TransformResult
from agri_etl.ingestion.base_reader import SensorRecord


class ThresholdTransformer(BaseTransformer):
    """Flag or drop records whose field values exceed defined thresholds.

    Config keys:
        thresholds (dict): mapping of field name -> {"min": float, "max": float}.
            Either bound is optional.
        action (str): "flag" (default) adds a boolean ``<field>_threshold_breach``
            tag; "drop" discards the entire record when any breach is found.
    """

    def _validate_config(self) -> None:
        thresholds = self.config.get("thresholds")
        if thresholds is None:
            raise ValueError("ThresholdTransformer requires 'thresholds' in config")
        if not isinstance(thresholds, dict):
            raise TypeError("'thresholds' must be a dict")
        if not thresholds:
            raise ValueError("'thresholds' must not be empty")
        for field, bounds in thresholds.items():
            if not isinstance(bounds, dict):
                raise TypeError(
                    f"Bounds for field '{field}' must be a dict with 'min'/'max' keys"
                )
            if "min" not in bounds and "max" not in bounds:
                raise ValueError(
                    f"Bounds for field '{field}' must contain at least 'min' or 'max'"
                )
        action = self.config.get("action", "flag")
        if action not in ("flag", "drop"):
            raise ValueError("'action' must be 'flag' or 'drop'")

    def transform(self, records: list[SensorRecord]) -> TransformResult:
        thresholds: dict[str, dict[str, Any]] = self.config["thresholds"]
        action: str = self.config.get("action", "flag")

        passed: list[SensorRecord] = []
        dropped: list[SensorRecord] = []
        errors: list[str] = []

        for record in records:
            breached = False
            for field, bounds in thresholds.items():
                raw = record.readings.get(field)
                if raw is None:
                    continue
                try:
                    value = float(raw)
                except (TypeError, ValueError):
                    errors.append(
                        f"Record {record.sensor_id}: cannot cast '{field}' to float"
                    )
                    continue
                lo = bounds.get("min")
                hi = bounds.get("max")
                field_breach = (lo is not None and value < lo) or (
                    hi is not None and value > hi
                )
                if field_breach:
                    breached = True
                    if action == "flag":
                        record.readings[f"{field}_threshold_breach"] = True

            if action == "drop" and breached:
                dropped.append(record)
            else:
                passed.append(record)

        return TransformResult(records=passed, dropped=dropped, errors=errors)
