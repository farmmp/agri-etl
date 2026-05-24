from __future__ import annotations

from typing import Any

from agri_etl.ingestion.base_reader import SensorRecord
from agri_etl.transform.base_transformer import BaseTransformer, TransformResult


class ScaleTransformer(BaseTransformer):
    """Multiply or divide sensor reading fields by a constant scale factor.

    Config keys:
        scales (dict[str, float]): mapping of field name -> scale factor.
            The field value is multiplied by the factor.  Use a factor of
            e.g. 0.001 to convert millivolts to volts.
        skip_missing (bool): if True, silently skip fields absent from the
            record rather than raising.  Defaults to False.
    """

    def _validate_config(self) -> None:
        scales = self.config.get("scales")
        if scales is None:
            raise ValueError("ScaleTransformer requires 'scales' in config")
        if not isinstance(scales, dict):
            raise TypeError("'scales' must be a dict mapping field names to numeric factors")
        if not scales:
            raise ValueError("'scales' must not be empty")
        for field, factor in scales.items():
            if not isinstance(factor, (int, float)):
                raise TypeError(
                    f"Scale factor for field '{field}' must be numeric, got {type(factor).__name__}"
                )
            if factor == 0:
                raise ValueError(f"Scale factor for field '{field}' must not be zero")

    def transform(self, records: list[SensorRecord]) -> TransformResult:
        scales: dict[str, float] = self.config["scales"]
        skip_missing: bool = self.config.get("skip_missing", False)

        out: list[SensorRecord] = []
        errors: list[str] = []

        for rec in records:
            readings: dict[str, Any] = dict(rec.readings)
            for field, factor in scales.items():
                if field not in readings:
                    if skip_missing:
                        continue
                    errors.append(
                        f"record {rec.sensor_id}@{rec.timestamp}: field '{field}' not found"
                    )
                    continue
                value = readings[field]
                if not isinstance(value, (int, float)):
                    errors.append(
                        f"record {rec.sensor_id}@{rec.timestamp}: field '{field}' is not numeric"
                    )
                    continue
                readings[field] = value * factor
            out.append(
                SensorRecord(
                    sensor_id=rec.sensor_id,
                    timestamp=rec.timestamp,
                    readings=readings,
                    metadata=rec.metadata,
                )
            )

        return TransformResult(records=out, errors=errors)
