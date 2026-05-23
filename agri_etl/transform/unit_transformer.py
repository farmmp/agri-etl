"""Transformer that converts sensor readings between physical units."""

from typing import Any

from agri_etl.ingestion.base_reader import SensorRecord
from agri_etl.transform.base_transformer import BaseTransformer, TransformResult

# Conversion functions keyed by (from_unit, to_unit)
_CONVERSIONS: dict[tuple[str, str], Any] = {
    ("celsius", "fahrenheit"): lambda v: v * 9 / 5 + 32,
    ("fahrenheit", "celsius"): lambda v: (v - 32) * 5 / 9,
    ("kpa", "hpa"): lambda v: v * 10,
    ("hpa", "kpa"): lambda v: v / 10,
    ("m/s", "km/h"): lambda v: v * 3.6,
    ("km/h", "m/s"): lambda v: v / 3.6,
    ("mm", "in"): lambda v: v / 25.4,
    ("in", "mm"): lambda v: v * 25.4,
}


class UnitTransformer(BaseTransformer):
    """Converts sensor values from one unit to another.

    Config keys:
        conversions (dict): mapping of field_name -> {"from": unit, "to": unit}
    """

    def _validate_config(self) -> None:
        if "conversions" not in self.config:
            raise ValueError("UnitTransformer requires 'conversions' in config")
        if not isinstance(self.config["conversions"], dict):
            raise TypeError("'conversions' must be a dict")
        for field_name, spec in self.config["conversions"].items():
            if not isinstance(spec, dict):
                raise TypeError(
                    f"Conversion spec for '{field_name}' must be a dict with 'from' and 'to' keys"
                )
            if "from" not in spec or "to" not in spec:
                raise ValueError(
                    f"Conversion spec for '{field_name}' must contain both 'from' and 'to' keys"
                )

    def transform(self, record: SensorRecord) -> TransformResult:
        transformed: dict[str, Any] = dict(record.values)
        warnings: list[str] = []

        for field_name, spec in self.config["conversions"].items():
            from_unit = spec.get("from", "").lower()
            to_unit = spec.get("to", "").lower()

            if field_name not in transformed:
                warnings.append(f"Field '{field_name}' not found in record")
                continue

            key = (from_unit, to_unit)
            if key not in _CONVERSIONS:
                warnings.append(
                    f"No conversion defined for {from_unit} -> {to_unit}"
                )
                continue

            original = transformed[field_name]
            try:
                transformed[field_name] = round(_CONVERSIONS[key](float(original)), 6)
            except (TypeError, ValueError) as exc:
                warnings.append(
                    f"Cannot convert field '{field_name}': {exc}"
                )

        return TransformResult(
            record=record,
            transformed=transformed,
            warnings=warnings,
        )
