from collections import deque
from typing import Any, Dict, List

from agri_etl.transform.base_transformer import BaseTransformer, TransformResult
from agri_etl.ingestion.base_reader import SensorRecord


class LagTransformer(BaseTransformer):
    """Adds lagged (previous-value) fields for specified sensor readings.

    Config keys:
        fields (dict): Mapping of field name -> lag steps (positive int).
                       e.g. {"temperature": 1, "humidity": 2}
        fill_value (any, optional): Value used when no previous record exists.
                                    Defaults to None.
    """

    def _validate_config(self) -> None:
        fields = self.config.get("fields")
        if fields is None:
            raise ValueError("LagTransformer requires 'fields' in config")
        if not isinstance(fields, dict) or not fields:
            raise ValueError("'fields' must be a non-empty dict")
        for key, steps in fields.items():
            if not isinstance(steps, int) or steps < 1:
                raise ValueError(
                    f"Lag steps for '{key}' must be a positive integer, got {steps!r}"
                )

    def __init__(self, config: Dict[str, Any]) -> None:
        super().__init__(config)
        self._fields: Dict[str, int] = self.config["fields"]
        self._fill: Any = self.config.get("fill_value", None)
        # One deque per field, sized to the required lag depth
        self._buffers: Dict[str, deque] = {
            field: deque(maxlen=steps)
            for field, steps in self._fields.items()
        }

    def transform(self, records: List[SensorRecord]) -> TransformResult:
        passed: List[SensorRecord] = []
        failed: List[Dict[str, Any]] = []

        for record in records:
            try:
                new_readings = dict(record.readings)
                for field, steps in self._fields.items():
                    buf = self._buffers[field]
                    current = record.readings.get(field)
                    # The lagged value is the oldest entry if buffer is full
                    lag_val = buf[0] if len(buf) == steps else self._fill
                    new_readings[f"{field}_lag{steps}"] = lag_val
                    buf.append(current)
                passed.append(
                    SensorRecord(
                        sensor_id=record.sensor_id,
                        timestamp=record.timestamp,
                        readings=new_readings,
                        meta=record.meta,
                    )
                )
            except Exception as exc:  # noqa: BLE001
                failed.append({"record": record, "error": str(exc)})

        return TransformResult(passed=passed, failed=failed)
