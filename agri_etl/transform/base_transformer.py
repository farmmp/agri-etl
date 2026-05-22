"""Base transformer interface for the agri-etl pipeline."""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any

from agri_etl.ingestion.base_reader import SensorRecord


@dataclass
class TransformResult:
    """Holds the outcome of a transform operation."""

    record: SensorRecord
    transformed: dict[str, Any] = field(default_factory=dict)
    warnings: list[str] = field(default_factory=list)
    dropped: bool = False

    def to_dict(self) -> dict[str, Any]:
        return {
            "record": self.record.to_dict(),
            "transformed": self.transformed,
            "warnings": self.warnings,
            "dropped": self.dropped,
        }


class BaseTransformer(ABC):
    """Abstract base class for all transformers."""

    def __init__(self, config: dict[str, Any]) -> None:
        self.config = config
        self._validate_config()

    def _validate_config(self) -> None:
        """Override to enforce required config keys."""

    @abstractmethod
    def transform(self, record: SensorRecord) -> TransformResult:
        """Transform a single SensorRecord."""

    def transform_batch(
        self, records: list[SensorRecord]
    ) -> list[TransformResult]:
        """Transform a batch of records, skipping dropped ones."""
        results = []
        for record in records:
            result = self.transform(record)
            results.append(result)
        return results
