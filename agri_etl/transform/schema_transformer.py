"""Schema validation transformer — rejects or flags records with unexpected fields."""
from __future__ import annotations

from typing import Any

from agri_etl.ingestion.base_reader import SensorRecord
from agri_etl.transform.base_transformer import BaseTransformer, TransformResult


class SchemaTransformer(BaseTransformer):
    """Validate that each record's readings conform to an expected field schema.

    Config keys:
        fields (list[str])  – required; the allowed reading keys.
        strict  (bool)      – optional (default True); if True, records with
                              extra or missing fields are dropped; if False they
                              are passed through with a warning tag.
        require_all (bool)  – optional (default False); when True every field
                              listed must be present in the record.
    """

    def _validate_config(self) -> None:
        fields = self.config.get("fields")
        if fields is None:
            raise KeyError("SchemaTransformer requires 'fields' in config")
        if not isinstance(fields, list) or len(fields) == 0:
            raise ValueError("'fields' must be a non-empty list of strings")
        if not all(isinstance(f, str) for f in fields):
            raise ValueError("All entries in 'fields' must be strings")

    def transform(self, record: SensorRecord) -> TransformResult:
        allowed: set[str] = set(self.config["fields"])
        strict: bool = self.config.get("strict", True)
        require_all: bool = self.config.get("require_all", False)

        present = set(record.readings.keys())
        extra = present - allowed
        missing = allowed - present if require_all else set()

        violations: list[str] = []
        if extra:
            violations.append(f"unexpected fields: {sorted(extra)}")
        if missing:
            violations.append(f"missing required fields: {sorted(missing)}")

        if violations:
            if strict:
                return TransformResult(
                    record=None,
                    dropped=True,
                    error="Schema violation — " + "; ".join(violations),
                )
            # Non-strict: pass through but tag the record
            tagged_readings = dict(record.readings)
            tagged_readings["_schema_warnings"] = "; ".join(violations)
            record = SensorRecord(
                sensor_id=record.sensor_id,
                timestamp=record.timestamp,
                readings=tagged_readings,
                meta=record.meta,
            )

        return TransformResult(record=record, dropped=False, error=None)
