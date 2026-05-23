from typing import Any, Dict, List

from agri_etl.ingestion.base_reader import SensorRecord
from agri_etl.transform.base_transformer import BaseTransformer, TransformResult


class MergeTransformer(BaseTransformer):
    """Merges multiple sensor fields into a single new field using a separator.

    Config keys:
        merges (dict): Mapping of new_field -> list of source fields to join.
        separator (str): String used to join values. Default is ",".
        drop_sources (bool): Whether to remove source fields after merging. Default False.
    """

    def _validate_config(self) -> None:
        merges = self.config.get("merges")
        if merges is None:
            raise ValueError("MergeTransformer requires 'merges' in config")
        if not isinstance(merges, dict):
            raise TypeError("'merges' must be a dict")
        if not merges:
            raise ValueError("'merges' must not be empty")
        for new_field, sources in merges.items():
            if not isinstance(sources, list) or not sources:
                raise ValueError(
                    f"Sources for '{new_field}' must be a non-empty list"
                )
        separator = self.config.get("separator", ",")
        if not isinstance(separator, str):
            raise TypeError("'separator' must be a string")
        drop_sources = self.config.get("drop_sources", False)
        if not isinstance(drop_sources, bool):
            raise TypeError("'drop_sources' must be a bool")

    def transform(self, records: List[SensorRecord]) -> TransformResult:
        merges: Dict[str, List[str]] = self.config["merges"]
        separator: str = self.config.get("separator", ",")
        drop_sources: bool = self.config.get("drop_sources", False)

        transformed: List[SensorRecord] = []
        errors: List[Dict[str, Any]] = []

        for record in records:
            try:
                new_readings: Dict[str, Any] = dict(record.readings)
                for new_field, sources in merges.items():
                    parts = [str(new_readings[src]) for src in sources if src in new_readings]
                    new_readings[new_field] = separator.join(parts)
                    if drop_sources:
                        for src in sources:
                            new_readings.pop(src, None)
                transformed.append(
                    SensorRecord(
                        sensor_id=record.sensor_id,
                        timestamp=record.timestamp,
                        readings=new_readings,
                        meta=record.meta,
                    )
                )
            except Exception as exc:  # pragma: no cover
                errors.append({"record": record, "error": str(exc)})

        return TransformResult(records=transformed, errors=errors)
