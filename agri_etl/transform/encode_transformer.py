from __future__ import annotations

from typing import Any, Dict, List

from agri_etl.ingestion.base_reader import SensorRecord
from agri_etl.transform.base_transformer import BaseTransformer, TransformResult

_SUPPORTED_STRATEGIES = ("onehot", "label")


class EncodeTransformer(BaseTransformer):
    """Encode categorical sensor reading fields as numeric values.

    Config keys:
        encodings (dict): Mapping of field name to strategy ("onehot" or "label").
            For "label" encoding, a ``classes`` list may be provided to fix the
            ordinal order; otherwise classes are assigned in encounter order.
    """

    def _validate_config(self) -> None:
        encodings = self.config.get("encodings")
        if encodings is None:
            raise ValueError("EncodeTransformer requires 'encodings' in config")
        if not isinstance(encodings, dict):
            raise TypeError("'encodings' must be a dict")
        if not encodings:
            raise ValueError("'encodings' must not be empty")
        for field, spec in encodings.items():
            if isinstance(spec, str):
                strategy = spec
            elif isinstance(spec, dict):
                strategy = spec.get("strategy", "label")
            else:
                raise TypeError(
                    f"Encoding spec for '{field}' must be a str or dict"
                )
            if strategy not in _SUPPORTED_STRATEGIES:
                raise ValueError(
                    f"Unsupported encoding strategy '{strategy}' for field '{field}'. "
                    f"Choose from {_SUPPORTED_STRATEGIES}"
                )

    def transform(self, records: List[SensorRecord]) -> TransformResult:
        encodings: Dict[str, Any] = self.config["encodings"]
        # Build label maps for label-encoding (stateful per transform call)
        label_maps: Dict[str, Dict[str, int]] = {}

        out: List[SensorRecord] = []
        errors: List[str] = []

        for record in records:
            readings = dict(record.readings)
            new_readings: Dict[str, Any] = {}

            for key, value in readings.items():
                if key not in encodings:
                    new_readings[key] = value
                    continue

                spec = encodings[key]
                if isinstance(spec, str):
                    strategy = spec
                    classes: List[str] = []
                else:
                    strategy = spec.get("strategy", "label")
                    classes = spec.get("classes", [])

                str_value = str(value)

                if strategy == "label":
                    if key not in label_maps:
                        label_maps[key] = {
                            c: i for i, c in enumerate(classes)
                        }
                    lmap = label_maps[key]
                    if str_value not in lmap:
                        lmap[str_value] = len(lmap)
                    new_readings[key] = lmap[str_value]

                elif strategy == "onehot":
                    known = classes if classes else sorted(
                        {str(r.readings.get(key, "")) for r in records}
                    )
                    for cls in known:
                        new_readings[f"{key}_{cls}"] = 1 if str_value == cls else 0

            out.append(
                SensorRecord(
                    sensor_id=record.sensor_id,
                    timestamp=record.timestamp,
                    readings=new_readings,
                    meta=record.meta,
                )
            )

        return TransformResult(records=out, errors=errors)
