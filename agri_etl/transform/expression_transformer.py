"""ExpressionTransformer – evaluate simple math expressions to derive new fields."""

from __future__ import annotations

import math
from typing import Any, Dict

from agri_etl.transform.base_transformer import BaseTransformer, TransformResult
from agri_etl.ingestion.base_reader import SensorRecord

# Safe names available inside expressions
_SAFE_GLOBALS: Dict[str, Any] = {
    "__builtins__": {},
    "abs": abs,
    "round": round,
    "min": min,
    "max": max,
    "sqrt": math.sqrt,
    "log": math.log,
    "exp": math.exp,
    "pi": math.pi,
    "e": math.e,
}


class ExpressionTransformer(BaseTransformer):
    """Derive new sensor reading fields by evaluating Python-like expressions.

    Config keys
    -----------
    expressions : dict[str, str]
        Mapping of ``new_field_name`` -> expression string.  The expression
        may reference any key already present in ``record.readings`` by name,
        plus the safe math helpers listed in ``_SAFE_GLOBALS``.

    Example
    -------
    ``{"expressions": {"temp_f": "temp_c * 9 / 5 + 32"}}``
    """

    def _validate_config(self) -> None:
        exprs = self.config.get("expressions")
        if exprs is None:
            raise ValueError("ExpressionTransformer requires 'expressions' in config")
        if not isinstance(exprs, dict):
            raise TypeError("'expressions' must be a dict mapping field names to expression strings")
        if not exprs:
            raise ValueError("'expressions' must not be empty")
        for key, expr in exprs.items():
            if not isinstance(key, str) or not key:
                raise ValueError("Expression keys must be non-empty strings")
            if not isinstance(expr, str) or not expr:
                raise ValueError(f"Expression for '{key}' must be a non-empty string")

    def transform(self, records: list[SensorRecord]) -> TransformResult:
        expressions: Dict[str, str] = self.config["expressions"]
        passed: list[SensorRecord] = []
        errors: list[str] = []

        for record in records:
            try:
                new_readings = dict(record.readings)
                local_ns = dict(new_readings)  # expose existing readings as variables
                for field, expr in expressions.items():
                    new_readings[field] = eval(expr, _SAFE_GLOBALS, local_ns)  # noqa: S307
                    local_ns[field] = new_readings[field]  # allow chaining
                passed.append(
                    SensorRecord(
                        sensor_id=record.sensor_id,
                        timestamp=record.timestamp,
                        readings=new_readings,
                        meta=record.meta,
                    )
                )
            except Exception as exc:  # noqa: BLE001
                errors.append(f"{record.sensor_id}@{record.timestamp}: {exc}")

        return TransformResult(passed=passed, failed=errors)
