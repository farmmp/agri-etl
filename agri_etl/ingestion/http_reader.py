"""HTTP/REST reader for fetching sensor data from web APIs."""

from __future__ import annotations

import time
from typing import Any, Generator

import requests

from agri_etl.ingestion.base_reader import BaseReader, SensorRecord


class HttpReader(BaseReader):
    """Reads sensor data from an HTTP/REST endpoint."""

    REQUIRED_CONFIG_KEYS = ("url",)

    def __init__(self, config: dict[str, Any]) -> None:
        super().__init__(config)
        missing = [k for k in self.REQUIRED_CONFIG_KEYS if k not in config]
        if missing:
            raise ValueError(f"HttpReader missing required config keys: {missing}")

        self._url: str = config["url"]
        self._headers: dict[str, str] = config.get("headers", {})
        self._timeout: int = int(config.get("timeout", 10))
        self._batch_size: int = int(config.get("batch_size", 100))
        self._params: dict[str, Any] = config.get("params", {})
        self._session: requests.Session | None = None

    def connect(self) -> None:
        """Initialise a persistent HTTP session."""
        self._session = requests.Session()
        self._session.headers.update(self._headers)
        self.logger.info("HttpReader connected to %s", self._url)

    def disconnect(self) -> None:
        """Close the HTTP session."""
        if self._session is not None:
            self._session.close()
            self._session = None
        self.logger.info("HttpReader disconnected")

    def read_batch(self) -> Generator[SensorRecord, None, None]:
        """Fetch one batch of records from the remote endpoint."""
        if self._session is None:
            raise RuntimeError("HttpReader is not connected. Call connect() first.")

        params = {**self._params, "limit": self._batch_size}
        response = self._session.get(self._url, params=params, timeout=self._timeout)
        response.raise_for_status()

        payload = response.json()
        records: list[dict[str, Any]] = (
            payload if isinstance(payload, list) else payload.get("data", [])
        )

        for item in records:
            yield SensorRecord(
                sensor_id=str(item.get("sensor_id", "unknown")),
                timestamp=float(item.get("timestamp", time.time())),
                values={k: v for k, v in item.items() if k not in ("sensor_id", "timestamp")},
                source=self._url,
            )
