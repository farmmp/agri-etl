from __future__ import annotations

from typing import Any

from agri_etl.transform.base_transformer import BaseTransformer, TransformResult
from agri_etl.ingestion.base_reader import SensorRecord


class RoundTransformer(BaseTransformer):
    """Round numeric sensor reading values to a specified number of decimal places.

    Config keys:
        fields (dict[str, int]): mapping of field name -> decimal places.
            Use -1 to round to the nearest integer.
    """

    def _validate_config(self) -> None:
        fields = self.config.get("fields")
        if fields is None:
            raise ValueError("RoundTransformer requires 'fields' in config")
        if not isinstance(fields, dict) or len(fields) == 0:
            raise ValueError("'fields' must be a non-empty dict")
        for key, places in fields.items():
            if not isinstance(key, str):
                raise ValueError("'fields' keys must be strings")
            if not isinstance(places, int):
                raise ValueError(
                    f"Decimal places for '{key}' must be an int, got {type(places).__name__}"
                )

    def transform(self, record: SensorRecord) -> TransformResult:
        fields: dict[str, int] = self.config["fields"]
        readings: dict[str, Any] = dict(record.readings)
        errors: list[str] = []

        for field, places in fields.items():
            if field not in readings:
                continue
            value = readings[field]
            if not isinstance(value, (int, float)):
                errors.append(
                    f"Field '{field}' is not numeric (got {type(value).__name__}); skipped"
                )
                continue
            readings[field] = round(float(value), places if places >= 0 else 0)

        rounded_record = SensorRecord(
            sensor_id=record.sensor_id,
            timestamp=record.timestamp,
            readings=readings,
            meta=record.meta,
        )
        return TransformResult(
            record=rounded_record,
            errors=errors,
            dropped=False,
        )
