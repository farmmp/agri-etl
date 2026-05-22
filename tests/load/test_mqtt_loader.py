"""Tests for MqttLoader."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from agri_etl.load.base_loader import LoadResult
from agri_etl.load.mqtt_loader import MqttLoader


def _make_result(sensor_id: str = "s1") -> LoadResult:
    return LoadResult(
        sensor_id=sensor_id,
        timestamp="2024-01-01T00:00:00",
        success=True,
        rows_written=1,
    )


@pytest.fixture()
def base_config() -> dict:
    return {"host": "localhost", "topic": "agri/sensors"}


@pytest.fixture()
def mock_mqtt():
    with patch("agri_etl.load.mqtt_loader.mqtt.Client") as mock_cls:
        client = MagicMock()
        mock_cls.return_value = client
        yield client


class TestMqttLoaderInit:
    def test_missing_host_raises(self):
        with pytest.raises(ValueError, match="host"):
            MqttLoader({"topic": "agri/sensors"})

    def test_missing_topic_raises(self):
        with pytest.raises(ValueError, match="topic"):
            MqttLoader({"host": "localhost"})

    def test_defaults_applied(self, base_config):
        loader = MqttLoader(base_config)
        assert loader.config["port"] == 1883
        assert loader.config["keepalive"] == 60
        assert loader.config["qos"] == 0
        assert loader.config["retain"] is False

    def test_custom_port_preserved(self, base_config):
        base_config["port"] = 8883
        loader = MqttLoader(base_config)
        assert loader.config["port"] == 8883


class TestMqttLoaderConnect:
    def test_connect_calls_broker(self, base_config, mock_mqtt):
        loader = MqttLoader(base_config)
        loader.connect()
        mock_mqtt.connect.assert_called_once_with("localhost", port=1883, keepalive=60)
        mock_mqtt.loop_start.assert_called_once()

    def test_disconnect_stops_loop(self, base_config, mock_mqtt):
        loader = MqttLoader(base_config)
        loader.connect()
        loader.disconnect()
        mock_mqtt.loop_stop.assert_called_once()
        mock_mqtt.disconnect.assert_called_once()

    def test_write_batch_without_connect_raises(self, base_config):
        loader = MqttLoader(base_config)
        with pytest.raises(RuntimeError, match="not connected"):
            loader.write_batch([_make_result()])


class TestMqttLoaderWriteBatch:
    def test_write_batch_returns_count(self, base_config, mock_mqtt):
        publish_info = MagicMock()
        publish_info.rc = 0  # MQTT_ERR_SUCCESS
        mock_mqtt.publish.return_value = publish_info

        loader = MqttLoader(base_config)
        loader.connect()
        written = loader.write_batch([_make_result("s1"), _make_result("s2")])
        assert written == 2
        assert mock_mqtt.publish.call_count == 2

    def test_failed_publish_not_counted(self, base_config, mock_mqtt):
        publish_info = MagicMock()
        publish_info.rc = 1  # error
        mock_mqtt.publish.return_value = publish_info

        loader = MqttLoader(base_config)
        loader.connect()
        written = loader.write_batch([_make_result()])
        assert written == 0

    def test_publish_uses_correct_topic(self, base_config, mock_mqtt):
        publish_info = MagicMock(rc=0)
        mock_mqtt.publish.return_value = publish_info

        loader = MqttLoader(base_config)
        loader.connect()
        loader.write_batch([_make_result()])
        call_args = mock_mqtt.publish.call_args
        assert call_args[0][0] == "agri/sensors"
