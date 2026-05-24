from __future__ import annotations

from typing import Any

from agri_etl.ingestion.base_reader import SensorRecord
from agri_etl.transform.base_transformer import BaseTransformer, TransformResult


class QuantizeTransformer(BaseTransformer):
    """Round sensor readings to the nearest multiple of a specified step.

    Config keys:
        steps (dict[str, float]): mapping of field name -> quantization step.
            Each numeric field value is snapped to the nearest multiple of its
            step.  Non-numeric fields are left unchanged.

    Example config::

        {
            "steps": {
                "temperature": 0.5,
                "humidity": 1.0
            }
        }
    """

    def _validate_config(self) -> None:
        if "steps" not in self.config:
            raise ValueError("QuantizeTransformer requires 'steps' in config")
        steps = self.config["steps"]
        if not isinstance(steps, dict):
            raise TypeError("'steps' must be a dict")
        if not steps:
            raise ValueError("'steps' must not be empty")
        for field, step in steps.items():
            if not isinstance(step, (int, float)):
                raise TypeError(
                    f"Step for field '{field}' must be a number, got {type(step).__name__}"
                )
            if step <= 0:
                raise ValueError(
                    f"Step for field '{field}' must be positive, got {step}"
                )

    def transform(self, records: list[SensorRecord]) -> TransformResult:
        steps: dict[str, float] = self.config["steps"]
        out: list[SensorRecord] = []
        errors: list[dict[str, Any]] = []

        for record in records:
            new_readings: dict[str, Any] = dict(record.readings)
            for field, step in steps.items():
                if field not in new_readings:
                    continue
                value = new_readings[field]
                if not isinstance(value, (int, float)):
                    errors.append(
                        {
                            "record_id": record.sensor_id,
                            "field": field,
                            "error": f"Cannot quantize non-numeric value: {value!r}",
                        }
                    )
                    continue
                new_readings[field] = round(round(value / step) * step, 10)
            out.append(
                SensorRecord(
                    sensor_id=record.sensor_id,
                    timestamp=record.timestamp,
                    readings=new_readings,
                    meta=record.meta,
                )
            )

        return TransformResult(records=out, errors=errors)
