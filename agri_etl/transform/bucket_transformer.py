from typing import Any, Dict, List
from agri_etl.transform.base_transformer import BaseTransformer, TransformResult
from agri_etl.ingestion.base_reader import SensorRecord


class BucketTransformer(BaseTransformer):
    """Assigns numeric field values to named buckets (bins) based on range rules."""

    def _validate_config(self) -> None:
        buckets = self.config.get("buckets")
        if buckets is None:
            raise ValueError("BucketTransformer requires 'buckets' in config")
        if not isinstance(buckets, dict):
            raise TypeError("'buckets' must be a dict mapping field names to bucket specs")
        if not buckets:
            raise ValueError("'buckets' must not be empty")
        for field, specs in buckets.items():
            if not isinstance(specs, list) or not specs:
                raise ValueError(f"Bucket specs for '{field}' must be a non-empty list")
            for spec in specs:
                if not isinstance(spec, dict):
                    raise TypeError(f"Each bucket spec for '{field}' must be a dict")
                if "label" not in spec:
                    raise ValueError(f"Each bucket spec for '{field}' must have a 'label'")
                if "min" not in spec and "max" not in spec:
                    raise ValueError(
                        f"Each bucket spec for '{field}' must have at least 'min' or 'max'"
                    )

    def _assign_bucket(self, value: float, specs: List[Dict[str, Any]]) -> str:
        for spec in specs:
            low = spec.get("min", float("-inf"))
            high = spec.get("max", float("inf"))
            if low <= value < high:
                return spec["label"]
        return self.config.get("default_label", "unknown")

    def transform(self, records: List[SensorRecord]) -> TransformResult:
        buckets: Dict[str, List[Dict[str, Any]]] = self.config["buckets"]
        output_suffix: str = self.config.get("output_suffix", "_bucket")
        passed: List[SensorRecord] = []
        failed: List[SensorRecord] = []

        for record in records:
            try:
                new_readings = dict(record.readings)
                for field, specs in buckets.items():
                    if field in new_readings:
                        raw = new_readings[field]
                        if raw is None:
                            continue
                        new_readings[field + output_suffix] = self._assign_bucket(
                            float(raw), specs
                        )
                passed.append(
                    SensorRecord(
                        sensor_id=record.sensor_id,
                        timestamp=record.timestamp,
                        readings=new_readings,
                        meta=record.meta,
                    )
                )
            except Exception as exc:  # noqa: BLE001
                failed.append(record)

        return TransformResult(passed=passed, failed=failed)
