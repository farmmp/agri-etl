from __future__ import annotations

from typing import Any

from agri_etl.ingestion.base_reader import SensorRecord
from agri_etl.transform.base_transformer import BaseTransformer, TransformResult


class ConditionalTransformer(BaseTransformer):
    """Apply a static value or expression to a field only when a condition is met.

    Config keys:
        conditions (dict): mapping of output_field -> rule dict with keys:
            - field (str): source field to evaluate
            - op (str): one of 'eq', 'ne', 'gt', 'gte', 'lt', 'lte', 'in', 'not_in'
            - value: comparison value
            - then: value to assign when condition is True
            - else (optional): value to assign when condition is False
    """

    _SUPPORTED_OPS = {"eq", "ne", "gt", "gte", "lt", "lte", "in", "not_in"}

    def _validate_config(self) -> None:
        conditions = self.config.get("conditions")
        if conditions is None:
            raise ValueError("ConditionalTransformer requires 'conditions' in config")
        if not isinstance(conditions, dict):
            raise TypeError("'conditions' must be a dict")
        if not conditions:
            raise ValueError("'conditions' must not be empty")
        for out_field, rule in conditions.items():
            if not isinstance(rule, dict):
                raise TypeError(f"Rule for '{out_field}' must be a dict")
            for required in ("field", "op", "value", "then"):
                if required not in rule:
                    raise ValueError(
                        f"Rule for '{out_field}' missing required key '{required}'"
                    )
            if rule["op"] not in self._SUPPORTED_OPS:
                raise ValueError(
                    f"Unsupported op '{rule['op']}' for '{out_field}'. "
                    f"Choose from {sorted(self._SUPPORTED_OPS)}"
                )

    def _evaluate(self, field_val: Any, op: str, cmp_val: Any) -> bool:
        if op == "eq":
            return field_val == cmp_val
        if op == "ne":
            return field_val != cmp_val
        if op == "gt":
            return field_val > cmp_val
        if op == "gte":
            return field_val >= cmp_val
        if op == "lt":
            return field_val < cmp_val
        if op == "lte":
            return field_val <= cmp_val
        if op == "in":
            return field_val in cmp_val
        if op == "not_in":
            return field_val not in cmp_val
        return False  # pragma: no cover

    def transform(self, records: list[SensorRecord]) -> TransformResult:
        conditions: dict = self.config["conditions"]
        out: list[SensorRecord] = []
        errors: list[str] = []

        for rec in records:
            new_readings = dict(rec.readings)
            for out_field, rule in conditions.items():
                src = rule["field"]
                if src not in rec.readings:
                    errors.append(
                        f"record {rec.sensor_id}: field '{src}' not found"
                    )
                    continue
                try:
                    match = self._evaluate(rec.readings[src], rule["op"], rule["value"])
                except TypeError as exc:
                    errors.append(
                        f"record {rec.sensor_id}: comparison error for '{src}': {exc}"
                    )
                    continue
                if match:
                    new_readings[out_field] = rule["then"]
                elif "else" in rule:
                    new_readings[out_field] = rule["else"]
            out.append(
                SensorRecord(
                    sensor_id=rec.sensor_id,
                    timestamp=rec.timestamp,
                    readings=new_readings,
                    meta=rec.meta,
                )
            )
        return TransformResult(records=out, errors=errors)
