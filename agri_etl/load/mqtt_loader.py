"""MQTT loader — publishes LoadResult records to an MQTT broker."""

from __future__ import annotations

import json
import logging
from typing import Any

try:
    import paho.mqtt.client as mqtt
except ImportError as exc:  # pragma: no cover
    raise ImportError("paho-mqtt is required for MqttLoader") from exc

from agri_etl.load.base_loader import BaseLoader, LoadResult

logger = logging.getLogger(__name__)

_DEFAULTS: dict[str, Any] = {
    "port": 1883,
    "keepalive": 60,
    "qos": 0,
    "retain": False,
}


class MqttLoader(BaseLoader):
    """Publish transformed records to an MQTT topic."""

    def _validate_config(self) -> None:
        if "host" not in self.config:
            raise ValueError("MqttLoader requires 'host' in config")
        if "topic" not in self.config:
            raise ValueError("MqttLoader requires 'topic' in config")
        for key, value in _DEFAULTS.items():
            self.config.setdefault(key, value)

    def connect(self) -> None:
        self._client = mqtt.Client()
        self._client.connect(
            self.config["host"],
            port=self.config["port"],
            keepalive=self.config["keepalive"],
        )
        self._client.loop_start()
        logger.debug("MqttLoader connected to %s:%s", self.config["host"], self.config["port"])

    def disconnect(self) -> None:
        if self._client is not None:
            self._client.loop_stop()
            self._client.disconnect()
            self._client = None
            logger.debug("MqttLoader disconnected")

    def write_batch(self, results: list[LoadResult]) -> int:
        if self._client is None:
            raise RuntimeError("MqttLoader is not connected")
        written = 0
        topic = self.config["topic"]
        qos = self.config["qos"]
        retain = self.config["retain"]
        for result in results:
            payload = json.dumps(result.to_dict())
            info = self._client.publish(topic, payload, qos=qos, retain=retain)
            if info.rc == mqtt.MQTT_ERR_SUCCESS:
                written += 1
            else:
                logger.warning("Failed to publish record to %s (rc=%s)", topic, info.rc)
        return written
