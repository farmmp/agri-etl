from __future__ import annotations

from collections import defaultdict
from datetime import datetime, timezone
from typing import Any, Dict, List

from agri_etl.transform.base_transformer import BaseTransformer, TransformResult
from agri_etl.ingestion.base_reader import SensorRecord

_SUPPORTED_FUNCTIONS = {"mean", "min", "max", "sum", "last", "first"}


class ResampleTransformer(BaseTransformer):
    """Resample sensor records into fixed-width time buckets.

    Config keys:
        interval_seconds (int): bucket width in seconds (required, > 0).
        fields (list[str]): sensor fields to resample (required, non-empty).
        function (str): aggregation function – mean | min | max | sum | last | first
                        (default: "mean").
    """

    def _validate_config(self) -> None:
        interval = self.config.get("interval_seconds")
        if interval is None:
            raise ValueError("ResampleTransformer requires 'interval_seconds'")
        if not isinstance(interval, int) or interval <= 0:
            raise ValueError("'interval_seconds' must be a positive integer")

        fields = self.config.get("fields")
        if fields is None:
            raise ValueError("ResampleTransformer requires 'fields'")
        if not isinstance(fields, list) or len(fields) == 0:
            raise ValueError("'fields' must be a non-empty list")

        func = self.config.get("function", "mean")
        if func not in _SUPPORTED_FUNCTIONS:
            raise ValueError(
                f"Unsupported function '{func}'. Choose from {sorted(_SUPPORTED_FUNCTIONS)}"
            )

    def transform(self, records: List[SensorRecord]) -> TransformResult:
        interval: int = self.config["interval_seconds"]
        fields: List[str] = self.config["fields"]
        func: str = self.config.get("function", "mean")

        # bucket_key -> field -> list of values
        buckets: Dict[tuple, Dict[str, List[float]]] = defaultdict(lambda: defaultdict(list))
        bucket_meta: Dict[tuple, SensorRecord] = {}

        errors: List[str] = []

        for rec in records:
            ts_epoch = int(rec.timestamp.timestamp())
            bucket_ts = (ts_epoch // interval) * interval
            key = (rec.sensor_id, bucket_ts)
            for field in fields:
                value = rec.readings.get(field)
                if value is None:
                    continue
                try:
                    buckets[key][field].append(float(value))
                except (TypeError, ValueError) as exc:
                    errors.append(f"{rec.sensor_id}@{rec.timestamp}: {field} – {exc}")
            if key not in bucket_meta:
                bucket_meta[key] = rec

        output: List[SensorRecord] = []
        for key, field_values in sorted(buckets.items()):
            sensor_id, bucket_ts = key
            bucket_dt = datetime.fromtimestamp(bucket_ts, tz=timezone.utc)
            proto = bucket_meta[key]
            readings: Dict[str, Any] = {}
            for field, values in field_values.items():
                if func == "mean":
                    readings[field] = sum(values) / len(values)
                elif func == "min":
                    readings[field] = min(values)
                elif func == "max":
                    readings[field] = max(values)
                elif func == "sum":
                    readings[field] = sum(values)
                elif func == "first":
                    readings[field] = values[0]
                elif func == "last":
                    readings[field] = values[-1]
            output.append(
                SensorRecord(
                    sensor_id=sensor_id,
                    timestamp=bucket_dt,
                    readings=readings,
                    metadata={**proto.metadata, "resampled": True, "interval_seconds": interval},
                )
            )

        return TransformResult(records=output, errors=errors)
