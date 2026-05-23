from typing import Any
from agri_etl.transform.base_transformer import BaseTransformer, TransformResult
from agri_etl.ingestion.base_reader import SensorRecord


class ClampTransformer(BaseTransformer):
    """Clamp numeric sensor readings to [min, max] bounds per field."""

    def _validate_config(self) -> None:
        bounds = self.config.get("bounds")
        if bounds is None:
            raise ValueError("ClampTransformer requires 'bounds' in config")
        if not isinstance(bounds, dict) or not bounds:
            raise ValueError("'bounds' must be a non-empty dict")
        for field, limits in bounds.items():
            if not isinstance(limits, dict):
                raise ValueError(f"Bounds for '{field}' must be a dict with 'min'/'max'")
            if "min" not in limits and "max" not in limits:
                raise ValueError(f"Bounds for '{field}' must have at least 'min' or 'max'")
            lo = limits.get("min")
            hi = limits.get("max")
            if lo is not None and hi is not None and lo > hi:
                raise ValueError(
                    f"'min' ({lo}) must be <= 'max' ({hi}) for field '{field}'"
                )

    def transform(self, record: SensorRecord) -> TransformResult:
        bounds: dict[str, Any] = self.config["bounds"]
        new_readings = dict(record.readings)
        clamped_fields: list[str] = []

        for field, limits in bounds.items():
            if field not in new_readings:
                continue
            value = new_readings[field]
            if not isinstance(value, (int, float)):
                continue
            lo = limits.get("min")
            hi = limits.get("max")
            original = value
            if lo is not None:
                value = max(lo, value)
            if hi is not None:
                value = min(hi, value)
            if value != original:
                new_readings[field] = value
                clamped_fields.append(field)

        transformed = SensorRecord(
            sensor_id=record.sensor_id,
            timestamp=record.timestamp,
            readings=new_readings,
            metadata=record.metadata,
        )
        return TransformResult(
            record=transformed,
            dropped=False,
            notes=f"clamped: {clamped_fields}" if clamped_fields else "",
        )
