"""Z-score outlier detection transformer.

Marks or drops records whose sensor readings deviate from the mean by
more than a configurable number of standard deviations.
"""
from __future__ import annotations

import math
from typing import List

from agri_etl.transform.base_transformer import BaseTransformer, TransformResult
from agri_etl.ingestion.base_reader import SensorRecord


class ZScoreTransformer(BaseTransformer):
    """Filter or flag records that are statistical outliers per field.

    Config keys
    -----------
    fields : dict[str, float]
        Mapping of reading key -> maximum allowed absolute z-score.
    action : str
        ``"drop"`` (default) removes outlier records;
        ``"flag"`` keeps them and adds a ``"zscore_outlier"`` key set to
        ``True`` in ``readings``.
    """

    def _validate_config(self) -> None:
        fields = self.config.get("fields")
        if not fields:
            raise ValueError("ZScoreTransformer requires a non-empty 'fields' mapping.")
        if not isinstance(fields, dict):
            raise TypeError("'fields' must be a dict mapping field names to z-score thresholds.")
        for key, threshold in fields.items():
            if not isinstance(threshold, (int, float)) or threshold <= 0:
                raise ValueError(
                    f"Threshold for '{key}' must be a positive number, got {threshold!r}."
                )
        action = self.config.get("action", "drop")
        if action not in ("drop", "flag"):
            raise ValueError(f"'action' must be 'drop' or 'flag', got {action!r}.")

    def transform(self, records: List[SensorRecord]) -> TransformResult:
        if not records:
            return TransformResult(records=[], errors=[])

        fields: dict = self.config["fields"]
        action: str = self.config.get("action", "drop")

        # Compute per-field mean and std over the batch.
        stats: dict[str, tuple[float, float]] = {}
        for field in fields:
            values = [
                r.readings[field]
                for r in records
                if field in r.readings and isinstance(r.readings[field], (int, float))
            ]
            if len(values) < 2:
                stats[field] = (0.0, 0.0)
                continue
            mean = sum(values) / len(values)
            variance = sum((v - mean) ** 2 for v in values) / len(values)
            stats[field] = (mean, math.sqrt(variance))

        kept: List[SensorRecord] = []
        errors: List[str] = []

        for record in records:
            is_outlier = False
            for field, threshold in fields.items():
                mean, std = stats[field]
                value = record.readings.get(field)
                if value is None or not isinstance(value, (int, float)):
                    continue
                if std == 0.0:
                    continue
                z = abs((value - mean) / std)
                if z > threshold:
                    is_outlier = True
                    errors.append(
                        f"Record {record.sensor_id}@{record.timestamp}: "
                        f"field '{field}' z-score {z:.3f} exceeds threshold {threshold}."
                    )
                    break

            if is_outlier and action == "flag":
                record.readings["zscore_outlier"] = True
                kept.append(record)
            elif not is_outlier:
                kept.append(record)
            # action == "drop" and is_outlier -> silently excluded

        return TransformResult(records=kept, errors=errors)
