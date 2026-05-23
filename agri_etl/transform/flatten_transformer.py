from __future__ import annotations

from typing import Any, Dict, List

from agri_etl.ingestion.base_reader import SensorRecord
from agri_etl.transform.base_transformer import BaseTransformer, TransformResult


class FlattenTransformer(BaseTransformer):
    """Flatten nested dicts inside SensorRecord.readings into top-level keys.

    Config keys:
        fields (list[str]): reading keys whose values are dicts to flatten.
        separator (str, optional): separator between parent and child keys. Default "_".
        drop_parent (bool, optional): remove the original nested key. Default True.
    """

    def _validate_config(self) -> None:
        fields = self.config.get("fields")
        if fields is None:
            raise ValueError("FlattenTransformer requires 'fields' in config")
        if not isinstance(fields, list) or len(fields) == 0:
            raise ValueError("'fields' must be a non-empty list")
        for f in fields:
            if not isinstance(f, str):
                raise ValueError("Each entry in 'fields' must be a string")
        sep = self.config.get("separator", "_")
        if not isinstance(sep, str):
            raise ValueError("'separator' must be a string")
        drop = self.config.get("drop_parent", True)
        if not isinstance(drop, bool):
            raise ValueError("'drop_parent' must be a boolean")

    def transform(self, records: List[SensorRecord]) -> TransformResult:
        fields: List[str] = self.config["fields"]
        separator: str = self.config.get("separator", "_")
        drop_parent: bool = self.config.get("drop_parent", True)

        passed: List[SensorRecord] = []
        failed: List[Dict[str, Any]] = []

        for record in records:
            try:
                readings: Dict[str, Any] = dict(record.readings)
                for field in fields:
                    if field not in readings:
                        continue
                    value = readings[field]
                    if not isinstance(value, dict):
                        continue
                    for child_key, child_val in value.items():
                        flat_key = f"{field}{separator}{child_key}"
                        readings[flat_key] = child_val
                    if drop_parent:
                        del readings[field]
                passed.append(
                    SensorRecord(
                        sensor_id=record.sensor_id,
                        timestamp=record.timestamp,
                        readings=readings,
                        meta=record.meta,
                    )
                )
            except Exception as exc:  # noqa: BLE001
                failed.append({"record": record, "error": str(exc)})

        return TransformResult(passed=passed, failed=failed)
