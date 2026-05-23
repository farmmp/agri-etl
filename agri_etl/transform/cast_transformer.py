"""CastTransformer – coerce sensor reading fields to specified Python types."""
from __future__ import annotations

from typing import Any, Dict

from agri_etl.ingestion.base_reader import SensorRecord
from agri_etl.transform.base_transformer import BaseTransformer, TransformResult

_SUPPORTED_TYPES: Dict[str, type] = {
    "int": int,
    "float": float,
    "str": str,
    "bool": bool,
}


class CastTransformer(BaseTransformer):
    """Cast individual reading fields to a target Python type.

    Config keys
    -----------
    casts : dict[str, str]
        Mapping of field name → type name ("int", "float", "str", "bool").
    drop_on_error : bool, optional
        If *True* records that fail casting are dropped instead of being
        counted as errors.  Defaults to ``False``.
    """

    def _validate_config(self) -> None:
        casts = self.config.get("casts")
        if casts is None:
            raise ValueError("CastTransformer requires 'casts' in config")
        if not isinstance(casts, dict) or not casts:
            raise ValueError("'casts' must be a non-empty dict")
        for field, type_name in casts.items():
            if type_name not in _SUPPORTED_TYPES:
                raise ValueError(
                    f"Unsupported cast type '{type_name}' for field '{field}'. "
                    f"Supported: {sorted(_SUPPORTED_TYPES)}"
                )

    def transform(self, records: list[SensorRecord]) -> TransformResult:
        casts: Dict[str, str] = self.config["casts"]
        drop_on_error: bool = bool(self.config.get("drop_on_error", False))

        transformed: list[SensorRecord] = []
        errors: list[str] = []

        for record in records:
            new_readings: Dict[str, Any] = dict(record.readings)
            failed = False
            for field, type_name in casts.items():
                if field not in new_readings:
                    continue
                try:
                    new_readings[field] = _SUPPORTED_TYPES[type_name](new_readings[field])
                except (ValueError, TypeError) as exc:
                    msg = (
                        f"[{record.sensor_id}] Cannot cast field '{field}' "
                        f"to {type_name}: {exc}"
                    )
                    errors.append(msg)
                    failed = True
                    break

            if failed and drop_on_error:
                continue

            transformed.append(
                SensorRecord(
                    sensor_id=record.sensor_id,
                    timestamp=record.timestamp,
                    readings=new_readings,
                    metadata=record.metadata,
                )
            )

        return TransformResult(records=transformed, errors=errors)
