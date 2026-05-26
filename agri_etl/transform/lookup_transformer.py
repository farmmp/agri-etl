from __future__ import annotations

from typing import Any, Dict, List

from agri_etl.ingestion.base_reader import SensorRecord
from agri_etl.transform.base_transformer import BaseTransformer, TransformResult


class LookupTransformer(BaseTransformer):
    """Replace field values using a static lookup table.

    Config keys:
        lookups (dict): mapping of field_name -> {old_value -> new_value}.
            Values not present in the table are left unchanged.
        default (any, optional): fallback value when a match is not found.
            If omitted the original value is kept.
    """

    def _validate_config(self) -> None:
        lookups = self.config.get("lookups")
        if lookups is None:
            raise ValueError("LookupTransformer requires 'lookups' in config")
        if not isinstance(lookups, dict):
            raise TypeError("'lookups' must be a dict")
        if not lookups:
            raise ValueError("'lookups' must not be empty")
        for field, table in lookups.items():
            if not isinstance(table, dict):
                raise TypeError(
                    f"lookup table for field '{field}' must be a dict"
                )

    def transform(self, records: List[SensorRecord]) -> TransformResult:
        lookups: Dict[str, Dict[Any, Any]] = self.config["lookups"]
        has_default = "default" in self.config
        default = self.config.get("default")

        out: List[SensorRecord] = []
        for record in records:
            new_readings: Dict[str, Any] = dict(record.readings)
            for field, table in lookups.items():
                if field not in new_readings:
                    continue
                original = new_readings[field]
                if original in table:
                    new_readings[field] = table[original]
                elif has_default:
                    new_readings[field] = default
            out.append(
                SensorRecord(
                    sensor_id=record.sensor_id,
                    timestamp=record.timestamp,
                    readings=new_readings,
                    meta=record.meta,
                )
            )
        return TransformResult(records=out, dropped=0, errors=[])
