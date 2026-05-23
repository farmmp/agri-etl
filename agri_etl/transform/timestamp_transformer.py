"""Transformer that normalises or shifts timestamp fields on SensorRecords."""

from __future__ import annotations

from datetime import datetime, timezone, timedelta
from typing import Any

from agri_etl.transform.base_transformer import BaseTransformer, TransformResult
from agri_etl.ingestion.base_reader import SensorRecord


class TimestampTransformer(BaseTransformer):
    """Normalise timestamps to UTC and/or apply a fixed offset in seconds.

    Config keys
    -----------
    to_utc : bool  (default True)
        Convert naive timestamps to UTC by assuming they are already UTC,
        or convert tz-aware timestamps to UTC.
    offset_seconds : int  (default 0)
        Shift every timestamp by this many seconds after normalisation.
    """

    def _validate_config(self, config: dict[str, Any]) -> None:
        to_utc = config.get("to_utc", True)
        if not isinstance(to_utc, bool):
            raise ValueError("'to_utc' must be a boolean")

        offset = config.get("offset_seconds", 0)
        if not isinstance(offset, (int, float)):
            raise ValueError("'offset_seconds' must be a number")

    def transform(self, records: list[SensorRecord]) -> TransformResult:
        to_utc: bool = self.config.get("to_utc", True)
        offset_secs: float = self.config.get("offset_seconds", 0)
        delta = timedelta(seconds=offset_secs)

        transformed: list[SensorRecord] = []
        errors: list[str] = []

        for record in records:
            try:
                ts = record.timestamp
                if to_utc:
                    if ts.tzinfo is None:
                        ts = ts.replace(tzinfo=timezone.utc)
                    else:
                        ts = ts.astimezone(timezone.utc)
                ts = ts + delta
                transformed.append(
                    SensorRecord(
                        sensor_id=record.sensor_id,
                        timestamp=ts,
                        readings=record.readings.copy(),
                        metadata=record.metadata.copy(),
                    )
                )
            except Exception as exc:  # pragma: no cover
                errors.append(f"Record {record.sensor_id}: {exc}")

        return TransformResult(
            records=transformed,
            dropped=len(records) - len(transformed),
            errors=errors,
        )
