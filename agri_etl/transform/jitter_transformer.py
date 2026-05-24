from __future__ import annotations

import random
from typing import Any

from agri_etl.transform.base_transformer import BaseTransformer, TransformResult
from agri_etl.ingestion.base_reader import SensorRecord


class JitterTransformer(BaseTransformer):
    """Add small random noise to numeric sensor fields.

    Config keys:
        fields (dict): mapping of field name -> max_jitter magnitude (float).
        seed   (int, optional): random seed for reproducibility.
    """

    def _validate_config(self) -> None:
        fields = self.config.get("fields")
        if fields is None:
            raise ValueError("JitterTransformer requires 'fields' in config")
        if not isinstance(fields, dict):
            raise TypeError("'fields' must be a dict mapping field names to jitter magnitudes")
        if not fields:
            raise ValueError("'fields' must not be empty")
        for key, magnitude in fields.items():
            if not isinstance(magnitude, (int, float)):
                raise TypeError(
                    f"Jitter magnitude for '{key}' must be a number, got {type(magnitude).__name__}"
                )
            if magnitude < 0:
                raise ValueError(f"Jitter magnitude for '{key}' must be >= 0")

        seed = self.config.get("seed")
        if seed is not None and not isinstance(seed, int):
            raise TypeError("'seed' must be an integer")

    def transform(self, records: list[SensorRecord]) -> TransformResult:
        fields: dict[str, float] = self.config["fields"]
        seed: int | None = self.config.get("seed")
        rng = random.Random(seed)

        out: list[SensorRecord] = []
        errors: list[str] = []

        for rec in records:
            new_readings: dict[str, Any] = dict(rec.readings)
            for field, magnitude in fields.items():
                if field not in new_readings:
                    continue
                val = new_readings[field]
                if not isinstance(val, (int, float)):
                    errors.append(
                        f"record {rec.sensor_id}@{rec.timestamp}: "
                        f"field '{field}' is not numeric, skipping jitter"
                    )
                    continue
                noise = rng.uniform(-magnitude, magnitude)
                new_readings[field] = val + noise
            out.append(
                SensorRecord(
                    sensor_id=rec.sensor_id,
                    timestamp=rec.timestamp,
                    readings=new_readings,
                    meta=rec.meta,
                )
            )

        return TransformResult(records=out, errors=errors)
