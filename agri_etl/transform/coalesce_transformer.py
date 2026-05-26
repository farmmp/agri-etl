from __future__ import annotations

from typing import Any

from agri_etl.transform.base_transformer import BaseTransformer, TransformResult


class CoalesceTransformer(BaseTransformer):
    """Return the first non-null value from an ordered list of source fields,
    writing the result into a destination field.

    Config example::

        {
            "coalesces": {
                "temperature": ["temp_primary", "temp_backup", "temp_default"],
                "humidity": ["rh_sensor", "rh_estimated"]
            },
            "drop_sources": false
        }
    """

    def _validate_config(self) -> None:
        coalesces = self.config.get("coalesces")
        if coalesces is None:
            raise ValueError("CoalesceTransformer requires 'coalesces' in config")
        if not isinstance(coalesces, dict):
            raise TypeError("'coalesces' must be a dict")
        if not coalesces:
            raise ValueError("'coalesces' must not be empty")
        for dest, sources in coalesces.items():
            if not isinstance(sources, list) or not sources:
                raise ValueError(
                    f"Sources for '{dest}' must be a non-empty list"
                )

    def transform(self, records: list[Any]) -> TransformResult:
        coalesces: dict[str, list[str]] = self.config["coalesces"]
        drop_sources: bool = self.config.get("drop_sources", False)

        out = []
        errors: list[str] = []

        for record in records:
            data = dict(record.data)
            for dest, sources in coalesces.items():
                value = None
                for src in sources:
                    candidate = data.get(src)
                    if candidate is not None:
                        value = candidate
                        break
                data[dest] = value
                if drop_sources:
                    for src in sources:
                        data.pop(src, None)

            from agri_etl.ingestion.base_reader import SensorRecord
            out.append(
                SensorRecord(
                    sensor_id=record.sensor_id,
                    timestamp=record.timestamp,
                    data=data,
                    meta=record.meta,
                )
            )

        return TransformResult(records=out, errors=errors)
