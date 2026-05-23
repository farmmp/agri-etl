"""Transformer that drops specified fields from sensor records."""

from typing import Any

from agri_etl.transform.base_transformer import BaseTransformer, TransformResult
from agri_etl.ingestion.base_reader import SensorRecord


class DropTransformer(BaseTransformer):
    """Remove unwanted fields from sensor records.

    Config keys:
        fields (list[str]): Field names to drop from each record's readings.
    """

    def _validate_config(self) -> None:
        if "fields" not in self.config:
            raise KeyError("DropTransformer requires 'fields' in config")
        fields = self.config["fields"]
        if not isinstance(fields, list):
            raise TypeError("'fields' must be a list of strings")
        if not fields:
            raise ValueError("'fields' list must not be empty")
        for item in fields:
            if not isinstance(item, str):
                raise TypeError(f"Each field name must be a string, got {type(item)}")

    def transform(self, record: SensorRecord) -> TransformResult:
        """Return a new record with the specified fields removed."""
        fields_to_drop: list[str] = self.config["fields"]
        original_readings: dict[str, Any] = dict(record.readings)

        dropped: list[str] = []
        new_readings: dict[str, Any] = {}
        for key, value in original_readings.items():
            if key in fields_to_drop:
                dropped.append(key)
            else:
                new_readings[key] = value

        new_record = SensorRecord(
            sensor_id=record.sensor_id,
            timestamp=record.timestamp,
            readings=new_readings,
            metadata=dict(record.metadata),
        )
        notes = f"Dropped fields: {dropped}" if dropped else "No fields dropped"
        return TransformResult(record=new_record, dropped=False, notes=notes)
