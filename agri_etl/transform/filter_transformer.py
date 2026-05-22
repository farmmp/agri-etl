"""Filter transformer: drops or flags SensorRecords based on value range rules."""

from __future__ import annotations

from typing import Any

from agri_etl.ingestion.base_reader import SensorRecord
from agri_etl.transform.base_transformer import BaseTransformer, TransformResult


class FilterTransformer(BaseTransformer):
    """Drops records whose sensor values fall outside configured min/max bounds.

    Config keys
    -----------
    rules : dict[str, dict]  # required
        Mapping of field name -> {"min": float, "max": float}.
        Either bound is optional (omit to skip that side of the check).
    drop_on_fail : bool  # default True
        When True, out-of-range records are excluded from *valid* output and
        appended to *errors*.  When False the record is kept but flagged via
        a "filter_warnings" key in its metadata.
    """

    def _validate_config(self) -> None:
        rules = self.config.get("rules")
        if not rules or not isinstance(rules, dict):
            raise ValueError("FilterTransformer requires a non-empty 'rules' dict in config.")
        for field, bounds in rules.items():
            if not isinstance(bounds, dict):
                raise ValueError(f"Rule for '{field}' must be a dict with optional 'min'/'max' keys.")
            for key in ("min", "max"):
                if key in bounds and not isinstance(bounds[key], (int, float)):
                    raise ValueError(f"Rule '{field}.{key}' must be numeric.")

    def transform(self, records: list[SensorRecord]) -> TransformResult:
        rules: dict[str, Any] = self.config["rules"]
        drop_on_fail: bool = self.config.get("drop_on_fail", True)

        valid: list[SensorRecord] = []
        errors: list[dict] = []

        for record in records:
            violations: list[str] = []
            for field, bounds in rules.items():
                value = record.values.get(field)
                if value is None:
                    continue
                lo = bounds.get("min")
                hi = bounds.get("max")
                if lo is not None and value < lo:
                    violations.append(f"{field}={value} < min={lo}")
                if hi is not None and value > hi:
                    violations.append(f"{field}={value} > max={hi}")

            if violations:
                if drop_on_fail:
                    errors.append(
                        {
                            "sensor_id": record.sensor_id,
                            "timestamp": record.timestamp.isoformat(),
                            "reason": "; ".join(violations),
                        }
                    )
                else:
                    record.metadata["filter_warnings"] = violations
                    valid.append(record)
            else:
                valid.append(record)

        return TransformResult(valid=valid, errors=errors)
