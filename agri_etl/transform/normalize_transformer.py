"""Min-max normalization transformer for sensor readings."""
from __future__ import annotations

from typing import Any

from agri_etl.ingestion.base_reader import SensorRecord
from agri_etl.transform.base_transformer import BaseTransformer, TransformResult


class NormalizeTransformer(BaseTransformer):
    """Normalize numeric fields to [0, 1] using per-field min/max bounds.

    Config keys:
        bounds (dict): mapping of field name to {"min": float, "max": float}.
        clip (bool): if True, values outside [min, max] are clipped to 0 or 1.
                     Defaults to False (values may exceed [0, 1]).
    """

    def _validate_config(self) -> None:
        bounds = self.config.get("bounds")
        if bounds is None:
            raise ValueError("NormalizeTransformer requires 'bounds' in config")
        if not isinstance(bounds, dict) or len(bounds) == 0:
            raise ValueError("'bounds' must be a non-empty dict")
        for field, limits in bounds.items():
            if not isinstance(limits, dict):
                raise ValueError(f"bounds['{field}'] must be a dict with 'min' and 'max'")
            if "min" not in limits or "max" not in limits:
                raise ValueError(f"bounds['{field}'] must contain 'min' and 'max' keys")
            if limits["min"] >= limits["max"]:
                raise ValueError(
                    f"bounds['{field}']: 'min' must be strictly less than 'max'"
                )
        clip = self.config.get("clip", False)
        if not isinstance(clip, bool):
            raise ValueError("'clip' must be a boolean")

    def transform(self, record: SensorRecord) -> TransformResult:
        bounds: dict[str, dict[str, Any]] = self.config["bounds"]
        clip: bool = self.config.get("clip", False)

        new_readings: dict[str, Any] = dict(record.readings)
        errors: list[str] = []

        for field, limits in bounds.items():
            if field not in new_readings:
                continue
            value = new_readings[field]
            if not isinstance(value, (int, float)):
                errors.append(f"Field '{field}' is not numeric; skipping normalization")
                continue
            lo, hi = limits["min"], limits["max"]
            normalized = (value - lo) / (hi - lo)
            if clip:
                normalized = max(0.0, min(1.0, normalized))
            new_readings[field] = normalized

        normalized_record = SensorRecord(
            sensor_id=record.sensor_id,
            timestamp=record.timestamp,
            readings=new_readings,
            meta=record.meta,
        )
        return TransformResult(
            record=normalized_record,
            errors=errors,
            dropped=False,
        )
