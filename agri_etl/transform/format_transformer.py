from __future__ import annotations

from typing import Any

from agri_etl.ingestion.base_reader import SensorRecord
from agri_etl.transform.base_transformer import BaseTransformer, TransformResult

_SUPPORTED_FORMATS: dict[str, str] = {
    "upper": "str.upper",
    "lower": "str.lower",
    "strip": "str.strip",
    "title": "str.title",
}


class FormatTransformer(BaseTransformer):
    """Apply string formatting operations to selected sensor record fields.

    Config keys:
        formats (dict): mapping of field name -> format operation.
            Supported operations: 'upper', 'lower', 'strip', 'title'.
    """

    def _validate_config(self) -> None:
        formats = self.config.get("formats")
        if formats is None:
            raise ValueError("FormatTransformer requires 'formats' in config")
        if not isinstance(formats, dict):
            raise TypeError("'formats' must be a dict")
        if not formats:
            raise ValueError("'formats' must not be empty")
        for field, op in formats.items():
            if op not in _SUPPORTED_FORMATS:
                raise ValueError(
                    f"Unsupported format operation '{op}' for field '{field}'. "
                    f"Supported: {sorted(_SUPPORTED_FORMATS)}"
                )

    def transform(self, records: list[SensorRecord]) -> TransformResult:
        formats: dict[str, str] = self.config["formats"]
        out: list[SensorRecord] = []
        errors: list[str] = []

        for record in records:
            new_readings: dict[str, Any] = dict(record.readings)
            for field, op in formats.items():
                if field not in new_readings:
                    continue
                value = new_readings[field]
                if not isinstance(value, str):
                    errors.append(
                        f"record {record.sensor_id}@{record.timestamp}: "
                        f"field '{field}' is not a string (got {type(value).__name__}), skipped"
                    )
                    continue
                if op == "upper":
                    new_readings[field] = value.upper()
                elif op == "lower":
                    new_readings[field] = value.lower()
                elif op == "strip":
                    new_readings[field] = value.strip()
                elif op == "title":
                    new_readings[field] = value.title()

            out.append(
                SensorRecord(
                    sensor_id=record.sensor_id,
                    timestamp=record.timestamp,
                    readings=new_readings,
                    meta=record.meta,
                )
            )

        return TransformResult(records=out, errors=errors)
