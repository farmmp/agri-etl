from __future__ import annotations

import hashlib
from typing import Any

from agri_etl.transform.base_transformer import BaseTransformer, TransformResult
from agri_etl.ingestion.base_reader import SensorRecord


class HashTransformer(BaseTransformer):
    """Replace specified field values with their cryptographic hash.

    Config keys:
        fields (dict): mapping of field name -> algorithm (md5, sha1, sha256).
        prefix (str, optional): string prepended to the output field name.
            Defaults to "" (overwrite in place).
    """

    SUPPORTED = {"md5", "sha1", "sha256"}

    def _validate_config(self) -> None:
        fields = self.config.get("fields")
        if not fields:
            raise ValueError("HashTransformer requires a non-empty 'fields' mapping")
        if not isinstance(fields, dict):
            raise TypeError("'fields' must be a dict mapping field names to algorithm names")
        for field, algo in fields.items():
            if algo not in self.SUPPORTED:
                raise ValueError(
                    f"Unsupported algorithm '{algo}' for field '{field}'. "
                    f"Choose from: {sorted(self.SUPPORTED)}"
                )

    def transform(self, records: list[SensorRecord]) -> TransformResult:
        fields: dict[str, str] = self.config["fields"]
        prefix: str = self.config.get("prefix", "")

        transformed: list[SensorRecord] = []
        errors: list[dict[str, Any]] = []

        for record in records:
            try:
                new_readings = dict(record.readings)
                for field, algo in fields.items():
                    if field not in new_readings:
                        continue
                    raw = str(new_readings[field]).encode()
                    digest = hashlib.new(algo, raw).hexdigest()
                    out_key = f"{prefix}{field}" if prefix else field
                    new_readings[out_key] = digest
                    if prefix and out_key != field:
                        del new_readings[field]
                transformed.append(
                    SensorRecord(
                        sensor_id=record.sensor_id,
                        timestamp=record.timestamp,
                        readings=new_readings,
                        metadata=record.metadata,
                    )
                )
            except Exception as exc:  # noqa: BLE001
                errors.append({"record": record, "error": str(exc)})

        return TransformResult(transformed=transformed, errors=errors)
