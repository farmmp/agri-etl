from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from agri_etl.ingestion.base_reader import SensorRecord


@dataclass
class TransformResult:
    """Container returned by every transformer."""

    records: list[SensorRecord] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "records": [r.to_dict() for r in self.records],
            "errors": self.errors,
        }


class BaseTransformer:
    """Abstract base for all transformers.

    Subclasses must implement:
        _validate_config(self) -> None
        transform(self, records: list[SensorRecord]) -> TransformResult
    """

    def __init__(self, config: dict[str, Any]) -> None:
        self.config = config or {}
        self._validate_config()

    def _validate_config(self) -> None:  # pragma: no cover
        raise NotImplementedError

    def transform(
        self, records: list[SensorRecord]
    ) -> TransformResult:  # pragma: no cover
        raise NotImplementedError

    # ------------------------------------------------------------------
    # helpers
    # ------------------------------------------------------------------

    def _require(self, key: str, expected_type: type | None = None) -> Any:
        """Retrieve a required config key, optionally checking its type."""
        if key not in self.config:
            raise ValueError(
                f"{self.__class__.__name__} requires '{key}' in config"
            )
        value = self.config[key]
        if expected_type is not None and not isinstance(value, expected_type):
            raise TypeError(
                f"'{key}' must be a {expected_type.__name__}, "
                f"got {type(value).__name__}"
            )
        return value
