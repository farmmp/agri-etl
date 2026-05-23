from __future__ import annotations

from typing import Any

from agri_etl.transform.base_transformer import BaseTransformer, TransformResult
from agri_etl.ingestion.base_reader import SensorRecord


class SanitizeTransformer(BaseTransformer):
    """Replace or remove sensor readings that match a set of sentinel values.

    Config keys:
        fields      (list[str])  – fields to inspect.
        sentinels   (list)       – values treated as invalid (e.g. -999, None, "").
        replacement (any|None)   – value to substitute; if None the key is dropped.
                                   Defaults to None.
        strict      (bool)       – if True, raise on unknown fields. Default False.
    """

    def _validate_config(self) -> None:
        fields = self.config.get("fields")
        if not fields:
            raise ValueError("SanitizeTransformer requires 'fields'")
        if not isinstance(fields, list):
            raise TypeError("'fields' must be a list")
        if not fields:
            raise ValueError("'fields' must not be empty")

        sentinels = self.config.get("sentinels")
        if sentinels is None:
            raise ValueError("SanitizeTransformer requires 'sentinels'")
        if not isinstance(sentinels, list):
            raise TypeError("'sentinels' must be a list")

    def transform(self, records: list[SensorRecord]) -> TransformResult:
        fields: list[str] = self.config["fields"]
        sentinels: list[Any] = self.config["sentinels"]
        replacement: Any = self.config.get("replacement", None)
        drop_key: bool = replacement is None
        strict: bool = bool(self.config.get("strict", False))

        out: list[SensorRecord] = []
        errors: list[str] = []

        for rec in records:
            new_readings = dict(rec.readings)
            for field in fields:
                if field not in new_readings:
                    if strict:
                        errors.append(
                            f"record {rec.sensor_id}@{rec.timestamp}: "
                            f"unknown field '{field}'"
                        )
                    continue
                if new_readings[field] in sentinels:
                    if drop_key:
                        del new_readings[field]
                    else:
                        new_readings[field] = replacement
            out.append(
                SensorRecord(
                    sensor_id=rec.sensor_id,
                    timestamp=rec.timestamp,
                    readings=new_readings,
                    meta=rec.meta,
                )
            )

        return TransformResult(records=out, errors=errors)
