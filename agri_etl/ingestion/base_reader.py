"""Base class for all data source readers in the agri-etl pipeline."""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, Iterator, List, Optional


@dataclass
class SensorRecord:
    """Represents a single sensor or weather station reading."""

    source_id: str
    timestamp: datetime
    metrics: Dict[str, Any]
    station_id: Optional[str] = None
    raw: Optional[Dict[str, Any]] = field(default=None, repr=False)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "source_id": self.source_id,
            "timestamp": self.timestamp.isoformat(),
            "station_id": self.station_id,
            "metrics": self.metrics,
        }


class BaseReader(ABC):
    """Abstract base class that all ingestion readers must implement."""

    def __init__(self, config: Dict[str, Any]) -> None:
        self.config = config
        self._connected = False

    @abstractmethod
    def connect(self) -> None:
        """Establish connection to the data source."""

    @abstractmethod
    def disconnect(self) -> None:
        """Release connection resources."""

    @abstractmethod
    def read_batch(self, start: datetime, end: datetime) -> Iterator[SensorRecord]:
        """Yield SensorRecord objects for the given time window."""

    def validate_config(self, required_keys: List[str]) -> None:
        missing = [k for k in required_keys if k not in self.config]
        if missing:
            raise ValueError(f"Missing required config keys: {missing}")

    def __enter__(self) -> "BaseReader":
        self.connect()
        return self

    def __exit__(self, *args: Any) -> None:
        self.disconnect()
