from __future__ import annotations

from typing import Any, Dict, List

from agri_etl.transform.base_transformer import BaseTransformer, TransformResult
from agri_etl.ingestion.base_reader import SensorRecord


class ValidateTransformer(BaseTransformer):
    """Validates sensor record fields against type and range constraints.

    Config keys:
        rules (dict): mapping of field name -> constraint dict.
            Each constraint may contain:
                - "type": one of "int", "float", "str", "bool"
                - "min": numeric lower bound (inclusive)
                - "max": numeric upper bound (inclusive)
                - "required": bool (default True)
        on_fail (str): "drop" | "flag" | "raise" (default "flag").
            drop  – exclude invalid records from output.
            flag  – add a "_validation_errors" key to metadata and pass through.
            raise – raise ValueError on first violation.
    """

    _SUPPORTED_TYPES: Dict[str, type] = {
        "int": int,
        "float": float,
        "str": str,
        "bool": bool,
    }

    def _validate_config(self) -> None:
        rules = self.config.get("rules")
        if rules is None:
            raise KeyError("ValidateTransformer requires 'rules' in config")
        if not isinstance(rules, dict):
            raise TypeError("'rules' must be a dict")
        if not rules:
            raise ValueError("'rules' must not be empty")
        on_fail = self.config.get("on_fail", "flag")
        if on_fail not in ("drop", "flag", "raise"):
            raise ValueError("'on_fail' must be 'drop', 'flag', or 'raise'")

    def _check_record(self, record: SensorRecord) -> List[str]:
        errors: List[str] = []
        rules: Dict[str, Any] = self.config["rules"]
        for field, constraint in rules.items():
            required = constraint.get("required", True)
            value = record.readings.get(field)
            if value is None:
                if required:
                    errors.append(f"missing required field '{field}'")
                continue
            expected_type_name = constraint.get("type")
            if expected_type_name:
                expected_type = self._SUPPORTED_TYPES.get(expected_type_name)
                if expected_type and not isinstance(value, expected_type):
                    errors.append(
                        f"field '{field}' expected {expected_type_name}, got {type(value).__name__}"
                    )
                    continue
            if "min" in constraint and value < constraint["min"]:
                errors.append(
                    f"field '{field}' value {value} below min {constraint['min']}"
                )
            if "max" in constraint and value > constraint["max"]:
                errors.append(
                    f"field '{field}' value {value} above max {constraint['max']}"
                )
        return errors

    def transform(self, records: List[SensorRecord]) -> TransformResult:
        on_fail: str = self.config.get("on_fail", "flag")
        passed: List[SensorRecord] = []
        dropped = 0
        flagged = 0

        for record in records:
            errors = self._check_record(record)
            if not errors:
                passed.append(record)
                continue
            if on_fail == "raise":
                raise ValueError(
                    f"Validation failed for sensor '{record.sensor_id}': {errors}"
                )
            if on_fail == "drop":
                dropped += 1
            else:  # flag
                meta = dict(record.metadata) if record.metadata else {}
                meta["_validation_errors"] = errors
                passed.append(
                    SensorRecord(
                        sensor_id=record.sensor_id,
                        timestamp=record.timestamp,
                        readings=record.readings,
                        metadata=meta,
                    )
                )
                flagged += 1

        return TransformResult(
            records=passed,
            dropped=dropped,
            metadata={"flagged": flagged},
        )
