"""Tests for MqttReader."""

from __future__ import annotations

import json
import time
from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

from agri_etl.ingestion.mqtt_reader import MqttReader


@pytest.fixture()
def base_config() -> dict:
    return {
        "host": "localhost",
        "port": 1883,
        "topic": "sensors/#",
        "client_id": "test-client",
        "batch_timeout": 0.05,
    }


@pytest.fixture()
def mock_mqtt(base_config):
    """Patch paho.mqtt.client so no real broker is needed."""
    mock_client_instance = MagicMock()

    with patch.dict("sys.modules", {"paho": MagicMock(), "paho.mqtt": MagicMock(), "paho.mqtt.client": MagicMock()}):
        with patch("agri_etl.ingestion.mqtt_reader.MqttReader") as _:
            pass  # ensure module is importable

    with patch("agri_etl.ingestion.mqtt_reader.threading.Thread") as mock_thread:
        mock_thread.return_value = MagicMock()
        with patch("agri_etl.ingestion.mqtt_reader.MqttReader._client", create=True):
            reader = MqttReader(base_config)
            reader._client = mock_client_instance
            yield reader, mock_client_instance


class TestMqttReaderInit:
    def test_defaults_applied(self, base_config):
        reader = MqttReader(base_config)
        assert reader._host == "localhost"
        assert reader._port == 1883
        assert reader._topic == "sensors/#"
        assert reader._keepalive == 60
        assert reader._batch_timeout == 0.05

    def test_missing_host_raises(self):
        with pytest.raises(KeyError):
            MqttReader({"topic": "sensors/#"})

    def test_missing_topic_raises(self):
        with pytest.raises(KeyError):
            MqttReader({"host": "localhost"})


class TestMqttReaderParsePayload:
    def setup_method(self):
        self.reader = MqttReader({"host": "localhost", "topic": "t", "batch_timeout": 0.01})

    def test_parse_iso_timestamp(self):
        payload = {"sensor_id": "s1", "timestamp": "2024-06-01T12:00:00", "value": 22.5, "unit": "C"}
        record = self.reader._parse_payload(payload)
        assert record.sensor_id == "s1"
        assert record.value == 22.5
        assert record.unit == "C"
        assert record.timestamp.year == 2024

    def test_parse_unix_timestamp(self):
        ts = 1717243200.0  # 2024-06-01 12:00:00 UTC
        payload = {"sensor_id": "s2", "timestamp": ts, "value": 10.0, "unit": "mm"}
        record = self.reader._parse_payload(payload)
        assert record.timestamp == datetime.fromtimestamp(ts, tz=timezone.utc)

    def test_missing_timestamp_defaults_to_now(self):
        payload = {"sensor_id": "s3", "value": 1.0, "unit": "hPa"}
        before = datetime.now(tz=timezone.utc)
        record = self.reader._parse_payload(payload)
        after = datetime.now(tz=timezone.utc)
        assert before <= record.timestamp <= after

    def test_extra_fields_go_to_metadata(self):
        payload = {"sensor_id": "s4", "value": 5.0, "unit": "%", "farm": "north", "zone": "A"}
        record = self.reader._parse_payload(payload)
        assert record.metadata["farm"] == "north"
        assert record.metadata["zone"] == "A"


class TestMqttReaderReadBatch:
    def setup_method(self):
        self.reader = MqttReader({"host": "localhost", "topic": "t", "batch_timeout": 0.05})

    def _enqueue(self, payloads):
        for p in payloads:
            self.reader._message_queue.put(p)

    def test_returns_empty_when_queue_empty(self):
        assert self.reader.read_batch() == []

    def test_returns_all_queued_records(self):
        payloads = [{"sensor_id": f"s{i}", "value": float(i), "unit": "C"} for i in range(3)]
        self._enqueue(payloads)
        records = self.reader.read_batch(batch_size=10)
        assert len(records) == 3
        assert records[0].sensor_id == "s0"

    def test_batch_size_limits_records(self):
        payloads = [{"sensor_id": f"s{i}", "value": float(i), "unit": "C"} for i in range(5)]
        self._enqueue(payloads)
        records = self.reader.read_batch(batch_size=2)
        assert len(records) == 2


class TestMqttReaderOnMessage:
    def setup_method(self):
        self.reader = MqttReader({"host": "localhost", "topic": "t", "batch_timeout": 0.01})

    def _make_message(self, data):
        msg = SimpleNamespace(payload=json.dumps(data).encode())
        return msg

    def test_valid_message_enqueued(self):
        msg = self._make_message({"sensor_id": "s1", "value": 7.0, "unit": "lux"})
        self.reader._on_message(None, None, msg)
        assert not self.reader._message_queue.empty()

    def test_invalid_json_is_skipped(self):
        msg = SimpleNamespace(payload=b"not-json")
        self.reader._on_message(None, None, msg)  # should not raise
        assert self.reader._message_queue.empty()
