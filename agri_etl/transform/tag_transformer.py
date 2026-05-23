"""TagTransformer – inject static key/value pairs into record metadata."""
from __future__ import annotations

from agri_etl.ingestion.base_reader import SensorRecord
from agri_etl.transform.base_transformer import BaseTransformer, TransformResult


class TagTransformer(BaseTransformer):
    """Merge a fixed set of tags into every record's *metadata* dict.

    Config keys
    -----------
    tags : dict[str, str | int | float | bool]
        Key/value pairs to inject.  Existing metadata keys are **not**
        overwritten unless ``overwrite`` is ``True``.
    overwrite : bool, optional
        Allow tags to overwrite existing metadata keys.  Defaults to
        ``False``.
    """

    def _validate_config(self) -> None:
        tags = self.config.get("tags")
        if tags is None:
            raise ValueError("TagTransformer requires 'tags' in config")
        if not isinstance(tags, dict) or not tags:
            raise ValueError("'tags' must be a non-empty dict")
        for k, v in tags.items():
            if not isinstance(k, str):
                raise ValueError(f"Tag key must be a string, got: {type(k).__name__}")
            if not isinstance(v, (str, int, float, bool)):
                raise ValueError(
                    f"Tag value for '{k}' must be str/int/float/bool, "
                    f"got: {type(v).__name__}"
                )

    def transform(self, records: list[SensorRecord]) -> TransformResult:
        tags: dict = self.config["tags"]
        overwrite: bool = bool(self.config.get("overwrite", False))

        transformed: list[SensorRecord] = []
        for record in records:
            merged = dict(record.metadata or {})
            for k, v in tags.items():
                if overwrite or k not in merged:
                    merged[k] = v
            transformed.append(
                SensorRecord(
                    sensor_id=record.sensor_id,
                    timestamp=record.timestamp,
                    readings=record.readings,
                    metadata=merged,
                )
            )
        return TransformResult(records=transformed, errors=[])
