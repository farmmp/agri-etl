from __future__ import annotations

from typing import Any

from agri_etl.transform.base_transformer import BaseTransformer, TransformResult
from agri_etl.ingestion.base_reader import SensorRecord


class SplitTransformer(BaseTransformer):
    """Split a single string field into multiple fields by a delimiter.

    Config keys:
        splits (dict): mapping of source_field -> {delimiter, targets}
            targets is a list of new field names for each part.
        on_error (str): 'skip' | 'null' | 'raise'  (default 'skip')
    """

    def _validate_config(self) -> None:
        splits = self.config.get("splits")
        if splits is None:
            raise KeyError("SplitTransformer requires 'splits' in config")
        if not isinstance(splits, dict):
            raise TypeError("'splits' must be a dict")
        if not splits:
            raise ValueError("'splits' must not be empty")
        for field, spec in splits.items():
            if not isinstance(spec, dict):
                raise TypeError(f"split spec for '{field}' must be a dict")
            if "delimiter" not in spec:
                raise KeyError(f"split spec for '{field}' missing 'delimiter'")
            if "targets" not in spec or not isinstance(spec["targets"], list) or not spec["targets"]:
                raise ValueError(f"split spec for '{field}' must have non-empty 'targets' list")
        on_error = self.config.get("on_error", "skip")
        if on_error not in ("skip", "null", "raise"):
            raise ValueError("'on_error' must be 'skip', 'null', or 'raise'")

    def transform(self, records: list[SensorRecord]) -> TransformResult:
        splits: dict[str, Any] = self.config["splits"]
        on_error: str = self.config.get("on_error", "skip")

        out: list[SensorRecord] = []
        errors: list[str] = []

        for record in records:
            readings = dict(record.readings)
            skip_record = False

            for field, spec in splits.items():
                delimiter: str = spec["delimiter"]
                targets: list[str] = spec["targets"]
                raw = readings.get(field)

                if raw is None:
                    if on_error == "raise":
                        raise ValueError(f"Field '{field}' not found in record {record.sensor_id}")
                    elif on_error == "null":
                        for t in targets:
                            readings[t] = None
                    else:
                        skip_record = True
                    continue

                parts = str(raw).split(delimiter)
                if len(parts) < len(targets):
                    msg = (
                        f"Field '{field}' split into {len(parts)} parts, "
                        f"expected at least {len(targets)} in record {record.sensor_id}"
                    )
                    errors.append(msg)
                    if on_error == "raise":
                        raise ValueError(msg)
                    elif on_error == "null":
                        for i, t in enumerate(targets):
                            readings[t] = parts[i] if i < len(parts) else None
                    else:
                        skip_record = True
                    continue

                for i, t in enumerate(targets):
                    readings[t] = parts[i]

            if not skip_record:
                out.append(SensorRecord(
                    sensor_id=record.sensor_id,
                    timestamp=record.timestamp,
                    readings=readings,
                    meta=record.meta,
                ))

        return TransformResult(records=out, errors=errors)
