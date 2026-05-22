"""Base loader interface for writing transformed agricultural sensor data."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any

from agri_etl.transform.base_transformer import TransformResult


@dataclass
class LoadResult:
    """Outcome of a single load operation."""

    records_written: int
    destination: str
    errors: list[str] = field(default_factory=list)

    @property
    def success(self) -> bool:
        return len(self.errors) == 0

    def to_dict(self) -> dict[str, Any]:
        return {
            "records_written": self.records_written,
            "destination": self.destination,
            "errors": self.errors,
            "success": self.success,
        }


class BaseLoader(ABC):
    """Abstract base class for all loaders."""

    def __init__(self, config: dict[str, Any]) -> None:
        if not isinstance(config, dict):
            raise TypeError("config must be a dict")
        self.config = config
        self._validate_config()

    def _validate_config(self) -> None:  # noqa: B027
        """Override in subclasses to enforce required config keys."""

    @abstractmethod
    def connect(self) -> None:
        """Open connection / initialise resources."""

    @abstractmethod
    def disconnect(self) -> None:
        """Close connection / release resources."""

    @abstractmethod
    def write_batch(self, result: TransformResult) -> LoadResult:
        """Persist a batch of transformed records and return a LoadResult."""
