"""Exponentially Weighted Moving Average (EWMA) transformer."""

from typing import Any, Dict, List

from agri_etl.transform.base_transformer import BaseTransformer, TransformResult
from agri_etl.ingestion.base_reader import SensorRecord


class EwmaTransformer(BaseTransformer):
    """Apply exponentially weighted moving average smoothing to numeric fields.

    Config keys:
        fields (dict): Mapping of field name -> alpha (smoothing factor, 0 < alpha <= 1).
            Alpha close to 1 gives more weight to recent observations.
        output_suffix (str): Suffix appended to field name for the smoothed output.
            Defaults to "_ewma". Set to "" to overwrite in place.
    """

    def _validate_config(self) -> None:
        fields = self.config.get("fields")
        if fields is None:
            raise ValueError("EwmaTransformer requires 'fields' in config")
        if not isinstance(fields, dict) or len(fields) == 0:
            raise ValueError("'fields' must be a non-empty dict mapping field -> alpha")
        for field, alpha in fields.items():
            if not isinstance(alpha, (int, float)) or not (0 < alpha <= 1):
                raise ValueError(
                    f"Alpha for field '{field}' must be a float in (0, 1]; got {alpha!r}"
                )

    def __init__(self, config: Dict[str, Any]) -> None:
        super().__init__(config)
        self._state: Dict[str, float] = {}

    def transform(self, records: List[SensorRecord]) -> TransformResult:
        fields: Dict[str, float] = self.config["fields"]
        suffix: str = self.config.get("output_suffix", "_ewma")

        out: List[SensorRecord] = []
        errors: List[str] = []

        for record in records:
            new_readings = dict(record.readings)
            for field, alpha in fields.items():
                raw = record.readings.get(field)
                if raw is None:
                    continue
                try:
                    value = float(raw)
                except (TypeError, ValueError):
                    errors.append(
                        f"Record {record.sensor_id}@{record.timestamp}: "
                        f"cannot cast '{field}' value {raw!r} to float"
                    )
                    continue

                prev = self._state.get(field)
                smoothed = value if prev is None else alpha * value + (1 - alpha) * prev
                self._state[field] = smoothed

                out_key = f"{field}{suffix}" if suffix else field
                new_readings[out_key] = round(smoothed, 6)

            out.append(
                SensorRecord(
                    sensor_id=record.sensor_id,
                    timestamp=record.timestamp,
                    readings=new_readings,
                    meta=record.meta,
                )
            )

        return TransformResult(records=out, errors=errors)
