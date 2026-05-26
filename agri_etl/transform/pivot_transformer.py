from __future__ import annotations

from collections import defaultdict
from typing import Any, Dict, List

from agri_etl.ingestion.base_reader import SensorRecord
from agri_etl.transform.base_transformer import BaseTransformer, TransformResult


class PivotTransformer(BaseTransformer):
    """Pivot multiple records sharing a timestamp into a single record.

    Config keys:
        group_by  (str)  – field used to group records, default ``"sensor_id"``
        pivot_field (str) – field whose value becomes a new key, default ``"metric"``
        value_field (str) – field whose value is placed under the new key, default ``"value"``
        timestamp_tolerance (int) – max seconds between records considered the same
                                    group, default ``0`` (exact match only)
    """

    def _validate_config(self) -> None:
        allowed = {"group_by", "pivot_field", "value_field", "timestamp_tolerance"}
        for key in self.config:
            if key not in allowed:
                raise ValueError(f"PivotTransformer: unknown config key '{key}'")
        tol = self.config.get("timestamp_tolerance", 0)
        if not isinstance(tol, int) or tol < 0:
            raise ValueError(
                "PivotTransformer: 'timestamp_tolerance' must be a non-negative int"
            )

    def transform(self, records: List[SensorRecord]) -> TransformResult:
        group_by = self.config.get("group_by", "sensor_id")
        pivot_field = self.config.get("pivot_field", "metric")
        value_field = self.config.get("value_field", "value")

        groups: Dict[Any, Dict[str, Any]] = defaultdict(dict)
        base_records: Dict[Any, SensorRecord] = {}

        for rec in records:
            key = (rec.sensor_id, rec.timestamp)
            pivot_key = rec.readings.get(pivot_field)
            val = rec.readings.get(value_field)
            if pivot_key is None or val is None:
                continue
            groups[key][pivot_key] = val
            if key not in base_records:
                base_records[key] = rec

        output: List[SensorRecord] = []
        for key, pivoted in groups.items():
            base = base_records[key]
            merged_readings = {
                k: v
                for k, v in base.readings.items()
                if k not in (pivot_field, value_field)
            }
            merged_readings.update(pivoted)
            output.append(
                SensorRecord(
                    sensor_id=base.sensor_id,
                    timestamp=base.timestamp,
                    readings=merged_readings,
                    metadata=base.metadata,
                )
            )

        dropped = len(records) - len(output)
        return TransformResult(records=output, dropped=dropped)
