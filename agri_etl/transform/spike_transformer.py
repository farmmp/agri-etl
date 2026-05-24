from __future__ import annotations

from typing import Any

from agri_etl.transform.base_transformer import BaseTransformer, TransformResult
from agri_etl.ingestion.base_reader import SensorRecord


class SpikeTransformer(BaseTransformer):
    """Remove or flag single-sample spikes using a delta threshold per field.

    Config keys:
        thresholds (dict): mapping of field name -> max allowed absolute delta
                           from the previous value.
        action (str): 'drop' (default) removes the record;
                      'null' replaces the spiking field value with None.
    """

    def _validate_config(self) -> None:
        thresholds = self.config.get("thresholds")
        if thresholds is None:
            raise ValueError("SpikeTransformer requires 'thresholds' in config")
        if not isinstance(thresholds, dict) or not thresholds:
            raise ValueError("'thresholds' must be a non-empty dict")
        for field, limit in thresholds.items():
            if not isinstance(limit, (int, float)) or limit <= 0:
                raise ValueError(
                    f"Threshold for '{field}' must be a positive number, got {limit!r}"
                )
        action = self.config.get("action", "drop")
        if action not in ("drop", "null"):
            raise ValueError(f"'action' must be 'drop' or 'null', got {action!r}")

    def __init__(self, config: dict[str, Any]) -> None:
        super().__init__(config)
        self._prev: dict[str, float] = {}

    def transform(
        self, records: list[SensorRecord]
    ) -> TransformResult:
        thresholds: dict[str, float] = self.config["thresholds"]
        action: str = self.config.get("action", "drop")

        passed: list[SensorRecord] = []
        dropped: list[SensorRecord] = []

        for record in records:
            is_spike = False
            spike_fields: list[str] = []

            for field, limit in thresholds.items():
                raw = record.readings.get(field)
                if raw is None:
                    continue
                try:
                    value = float(raw)
                except (TypeError, ValueError):
                    continue

                if field in self._prev:
                    if abs(value - self._prev[field]) > limit:
                        is_spike = True
                        spike_fields.append(field)
                    else:
                        self._prev[field] = value
                else:
                    self._prev[field] = value

            if is_spike:
                if action == "drop":
                    dropped.append(record)
                else:  # null
                    new_readings = dict(record.readings)
                    for f in spike_fields:
                        new_readings[f] = None
                    passed.append(
                        SensorRecord(
                            sensor_id=record.sensor_id,
                            timestamp=record.timestamp,
                            readings=new_readings,
                            meta=record.meta,
                        )
                    )
            else:
                passed.append(record)

        return TransformResult(passed=passed, dropped=dropped)
