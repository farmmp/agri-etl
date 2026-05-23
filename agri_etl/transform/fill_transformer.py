"""Fill transformer: replaces missing (None) sensor reading values with a
fallback strategy — either a fixed constant or forward-fill from the previous
record in the batch."""

from __future__ import annotations

from typing import Any

from agri_etl.ingestion.base_reader import SensorRecord
from agri_etl.transform.base_transformer import BaseTransformer, TransformResult

_SUPPORTED_STRATEGIES = ("constant", "forward_fill")


class FillTransformer(BaseTransformer):
    """Replace None values in sensor readings.

    Config keys
    -----------
    fields : list[str]
        Which reading keys to inspect and fill.
    strategy : str
        ``"constant"`` – replace with *value*.
        ``"forward_fill"`` – replace with the last seen non-None value.
    value : Any, optional
        Required when *strategy* is ``"constant"``.
    """

    def _validate_config(self) -> None:
        if "fields" not in self.config:
            raise KeyError("FillTransformer config missing 'fields'")
        if not isinstance(self.config["fields"], list) or not self.config["fields"]:
            raise ValueError("'fields' must be a non-empty list")

        strategy = self.config.get("strategy", "constant")
        if strategy not in _SUPPORTED_STRATEGIES:
            raise ValueError(
                f"Unsupported strategy '{strategy}'. "
                f"Choose from {_SUPPORTED_STRATEGIES}."
            )
        if strategy == "constant" and "value" not in self.config:
            raise KeyError("FillTransformer config missing 'value' for constant strategy")

    def transform(self, records: list[SensorRecord]) -> TransformResult:
        strategy: str = self.config.get("strategy", "constant")
        fields: list[str] = self.config["fields"]
        fill_value: Any = self.config.get("value")

        filled: list[SensorRecord] = []
        errors: list[str] = []
        last_seen: dict[str, Any] = {}

        for rec in records:
            new_readings = dict(rec.readings)
            for field in fields:
                if new_readings.get(field) is None:
                    if strategy == "constant":
                        new_readings[field] = fill_value
                    else:  # forward_fill
                        if field in last_seen:
                            new_readings[field] = last_seen[field]
                        else:
                            errors.append(
                                f"No prior value for '{field}' in record "
                                f"sensor_id={rec.sensor_id} ts={rec.timestamp}"
                            )
                else:
                    last_seen[field] = new_readings[field]

            filled.append(
                SensorRecord(
                    sensor_id=rec.sensor_id,
                    timestamp=rec.timestamp,
                    readings=new_readings,
                    metadata=rec.metadata,
                )
            )

        return TransformResult(records=filled, errors=errors)
