"""Abstract base class for all loaders."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class LoadResult:
    """Outcome of writing a single record."""

    sensor_id: str
    timestamp: str
    success: bool
    rows_written: int = 0
    error: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "sensor_id": self.sensor_id,
            "timestamp": self.timestamp,
            "success": self.success,
            "rows_written": self.rows_written,
            "error": self.error,
            "metadata": self.metadata,
        }


class BaseLoader:
    """Base class every loader must extend."""

    def __init__(self, config: dict[str, Any]) -> None:
        self.config: dict[str, Any] = dict(config)
        self._client: Any = None
        self._validate_config()

    # ------------------------------------------------------------------
    # Subclass interface
    # ------------------------------------------------------------------

    def _validate_config(self) -> None:  # pragma: no cover
        """Validate and apply defaults to *self.config*."""

    def connect(self) -> None:  # pragma: no cover
        raise NotImplementedError

    def disconnect(self) -> None:  # pragma: no cover
        raise NotImplementedError

    def write_batch(self, results: list[LoadResult]) -> int:  # pragma: no cover
        raise NotImplementedError

    # ------------------------------------------------------------------
    # Context-manager support
    # ------------------------------------------------------------------

    def __enter__(self) -> "BaseLoader":
        self.connect()
        return self

    def __exit__(self, *_: Any) -> None:
        self.disconnect()
