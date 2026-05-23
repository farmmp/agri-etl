"""HTTP/REST loader — posts TransformResult batches to a remote endpoint."""
from __future__ import annotations

import json
import logging
from typing import Any

import requests

from agri_etl.load.base_loader import BaseLoader, LoadResult
from agri_etl.transform.base_transformer import TransformResult

logger = logging.getLogger(__name__)


class HttpLoader(BaseLoader):
    """Sends records to an HTTP endpoint via POST requests."""

    def _validate_config(self) -> None:
        if "url" not in self.config:
            raise ValueError("HttpLoader requires 'url' in config")
        self.config.setdefault("timeout", 10)
        self.config.setdefault("headers", {"Content-Type": "application/json"})
        self.config.setdefault("batch_key", "records")
        self.config.setdefault("verify_ssl", True)

    def connect(self) -> None:
        self._session = requests.Session()
        self._session.headers.update(self.config["headers"])
        logger.info("HttpLoader session opened for %s", self.config["url"])

    def disconnect(self) -> None:
        if self._session:
            self._session.close()
            self._session = None
        logger.info("HttpLoader session closed")

    def write_batch(self, results: list[TransformResult]) -> LoadResult:
        if not self._session:
            raise RuntimeError("HttpLoader is not connected")

        records = [r.to_dict() for r in results]
        payload = {self.config["batch_key"]: records}

        try:
            response = self._session.post(
                self.config["url"],
                data=json.dumps(payload, default=str),
                timeout=self.config["timeout"],
                verify=self.config["verify_ssl"],
            )
            response.raise_for_status()
            logger.debug("HttpLoader posted %d records, status %s", len(records), response.status_code)
            return LoadResult(records_written=len(records), errors=[])
        except requests.RequestException as exc:
            logger.error("HttpLoader POST failed: %s", exc)
            return LoadResult(records_written=0, errors=[str(exc)])
