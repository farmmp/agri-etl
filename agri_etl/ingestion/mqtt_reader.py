"""MQTT-based sensor data reader for real-time agricultural sensor ingestion."""

from __future__ import annotations

import json
import logging
import queue
import threading
from datetime import datetime, timezone
from typing import Any

from agri_etl.ingestion.base_reader import BaseReader, SensorRecord

logger = logging.getLogger(__name__)


class MqttReader(BaseReader):
    """Reads sensor data published to an MQTT broker.

    Config keys:
        host (str): MQTT broker hostname.
        port (int): Broker port, default 1883.
        topic (str): Topic to subscribe to (supports wildcards).
        client_id (str): Optional MQTT client identifier.
        keepalive (int): Keepalive interval in seconds, default 60.
        batch_timeout (float): Seconds to wait when collecting a batch, default 1.0.
    """

    def __init__(self, config: dict[str, Any]) -> None:
        super().__init__(config)
        self._host: str = config["host"]
        self._port: int = int(config.get("port", 1883))
        self._topic: str = config["topic"]
        self._client_id: str = config.get("client_id", "agri-etl-mqtt")
        self._keepalive: int = int(config.get("keepalive", 60))
        self._batch_timeout: float = float(config.get("batch_timeout", 1.0))
        self._message_queue: queue.Queue[dict[str, Any]] = queue.Queue()
        self._client: Any = None
        self._thread: threading.Thread | None = None

    # ------------------------------------------------------------------
    # Connection lifecycle
    # ------------------------------------------------------------------

    def connect(self) -> None:
        try:
            import paho.mqtt.client as mqtt  # type: ignore[import]
        except ImportError as exc:  # pragma: no cover
            raise ImportError(
                "paho-mqtt is required for MqttReader. "
                "Install it with: pip install paho-mqtt"
            ) from exc

        self._client = mqtt.Client(client_id=self._client_id)
        self._client.on_connect = self._on_connect
        self._client.on_message = self._on_message
        self._client.connect(self._host, self._port, self._keepalive)
        self._thread = threading.Thread(target=self._client.loop_forever, daemon=True)
        self._thread.start()
        logger.info("MqttReader connected to %s:%s topic=%s", self._host, self._port, self._topic)

    def disconnect(self) -> None:
        if self._client is not None:
            self._client.disconnect()
            self._client = None
        logger.info("MqttReader disconnected")

    # ------------------------------------------------------------------
    # Reading
    # ------------------------------------------------------------------

    def read_batch(self, batch_size: int = 100) -> list[SensorRecord]:
        """Drain up to *batch_size* messages from the internal queue."""
        records: list[SensorRecord] = []
        deadline = self._batch_timeout
        while len(records) < batch_size:
            try:
                payload = self._message_queue.get(timeout=deadline)
                records.append(self._parse_payload(payload))
                deadline = 0.0  # subsequent gets are non-blocking
            except queue.Empty:
                break
        return records

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _on_connect(self, client: Any, userdata: Any, flags: Any, rc: int) -> None:
        if rc == 0:
            client.subscribe(self._topic)
        else:
            logger.error("MQTT connection failed with code %s", rc)

    def _on_message(self, client: Any, userdata: Any, message: Any) -> None:
        try:
            payload = json.loads(message.payload.decode())
            self._message_queue.put(payload)
        except (json.JSONDecodeError, UnicodeDecodeError) as exc:
            logger.warning("Skipping unparseable MQTT message: %s", exc)

    def _parse_payload(self, payload: dict[str, Any]) -> SensorRecord:
        ts_raw = payload.get("timestamp")
        if isinstance(ts_raw, str):
            timestamp = datetime.fromisoformat(ts_raw).replace(tzinfo=timezone.utc)
        elif isinstance(ts_raw, (int, float)):
            timestamp = datetime.fromtimestamp(ts_raw, tz=timezone.utc)
        else:
            timestamp = datetime.now(tz=timezone.utc)

        return SensorRecord(
            sensor_id=str(payload.get("sensor_id", "unknown")),
            timestamp=timestamp,
            value=float(payload["value"]),
            unit=str(payload.get("unit", "")),
            metadata={k: v for k, v in payload.items() if k not in {"sensor_id", "timestamp", "value", "unit"}},
        )
