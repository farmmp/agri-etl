"""MaskTransformer: redact or replace sensor field values matching a condition."""

from __future__ import annotations

from typing import Any, Dict, List

from agri_etl.ingestion.base_reader import SensorRecord
from agri_etl.transform.base_transformer import BaseTransformer, TransformResult

_SUPPORTED_OPS = {"eq", "neq", "gt", "gte", "lt", "lte"}


class MaskTransformer(BaseTransformer):
    """Replace field values with a mask value when a condition is met.

    Config keys:
        masks (list[dict]): Each entry must contain:
            - field (str): field name in SensorRecord.readings
            - op (str): comparison operator (eq, neq, gt, gte, lt, lte)
            - threshold (float | int | str): value to compare against
            - replacement: value to write when condition is True (default None)
    """

    def _validate_config(self) -> None:
        masks = self.config.get("masks")
        if masks is None:
            raise ValueError("MaskTransformer requires 'masks' in config")
        if not isinstance(masks, list) or len(masks) == 0:
            raise ValueError("'masks' must be a non-empty list")
        for i, rule in enumerate(masks):
            if not isinstance(rule, dict):
                raise ValueError(f"masks[{i}] must be a dict")
            if "field" not in rule:
                raise ValueError(f"masks[{i}] missing 'field'")
            op = rule.get("op")
            if op not in _SUPPORTED_OPS:
                raise ValueError(
                    f"masks[{i}] unsupported op '{op}'; choose from {_SUPPORTED_OPS}"
                )
            if "threshold" not in rule:
                raise ValueError(f"masks[{i}] missing 'threshold'")

    def _matches(self, value: Any, op: str, threshold: Any) -> bool:
        try:
            v, t = float(value), float(threshold)
        except (TypeError, ValueError):
            v, t = value, threshold  # type: ignore[assignment]
        ops = {
            "eq": lambda a, b: a == b,
            "neq": lambda a, b: a != b,
            "gt": lambda a, b: a > b,
            "gte": lambda a, b: a >= b,
            "lt": lambda a, b: a < b,
            "lte": lambda a, b: a <= b,
        }
        return ops[op](v, t)

    def transform(self, records: List[SensorRecord]) -> TransformResult:
        masks: List[Dict[str, Any]] = self.config["masks"]
        out, errors = [], []
        for rec in records:
            try:
                new_readings = dict(rec.readings)
                for rule in masks:
                    field = rule["field"]
                    if field in new_readings and self._matches(
                        new_readings[field], rule["op"], rule["threshold"]
                    ):
                        new_readings[field] = rule.get("replacement", None)
                out.append(
                    SensorRecord(
                        sensor_id=rec.sensor_id,
                        timestamp=rec.timestamp,
                        readings=new_readings,
                        meta=rec.meta,
                    )
                )
            except Exception as exc:  # noqa: BLE001
                errors.append(f"{rec.sensor_id}: {exc}")
        return TransformResult(records=out, errors=errors)
