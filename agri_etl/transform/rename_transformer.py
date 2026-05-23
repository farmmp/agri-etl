"""Transformer that renames fields in SensorRecord measurements."""

from typing import Any

from agri_etl.ingestion.base_reader import SensorRecord
from agri_etl.transform.base_transformer import BaseTransformer, TransformResult


class RenameTransformer(BaseTransformer):
    """Renames measurement keys in a SensorRecord according to a mapping.

    Config keys:
        mappings (dict[str, str]): ``{old_name: new_name}`` pairs.
            Keys absent from a record are silently ignored.
    """

    def _validate_config(self) -> None:
        mappings = self.config.get("mappings")
        if mappings is None:
            raise ValueError("RenameTransformer requires 'mappings' in config")
        if not isinstance(mappings, dict):
            raise TypeError("'mappings' must be a dict")
        if not mappings:
            raise ValueError("'mappings' must not be empty")
        for old, new in mappings.items():
            if not isinstance(old, str) or not isinstance(new, str):
                raise TypeError(
                    f"All mapping keys and values must be strings, got {old!r}: {new!r}"
                )

    def transform(self, record: SensorRecord) -> TransformResult:
        """Return a new SensorRecord with renamed measurement keys.

        Args:
            record: The incoming sensor record.

        Returns:
            TransformResult with the renamed record and no errors.
        """
        mappings: dict[str, str] = self.config["mappings"]
        new_measurements: dict[str, Any] = {}
        for key, value in record.measurements.items():
            new_measurements[mappings.get(key, key)] = value

        renamed = SensorRecord(
            sensor_id=record.sensor_id,
            timestamp=record.timestamp,
            measurements=new_measurements,
            metadata=dict(record.metadata),
        )
        return TransformResult(record=renamed, errors=[])
