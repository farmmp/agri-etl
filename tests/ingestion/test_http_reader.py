"""Tests for HttpReader."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from agri_etl.ingestion.http_reader import HttpReader


@pytest.fixture()
def base_config() -> dict:
    return {
        "url": "https://api.example.com/sensors",
        "headers": {"Authorization": "Bearer test-token"},
        "timeout": 5,
        "batch_size": 10,
    }


@pytest.fixture()
def mock_session():
    with patch("agri_etl.ingestion.http_reader.requests.Session") as mock_cls:
        session = MagicMock()
        mock_cls.return_value = session
        yield session


class TestHttpReaderInit:
    def test_missing_url_raises(self):
        with pytest.raises(ValueError, match="url"):
            HttpReader({})

    def test_defaults_applied(self, base_config):
        reader = HttpReader({"url": "https://api.example.com/sensors"})
        assert reader._timeout == 10
        assert reader._batch_size == 100
        assert reader._headers == {}
        assert reader._params == {}

    def test_custom_config(self, base_config):
        reader = HttpReader(base_config)
        assert reader._timeout == 5
        assert reader._batch_size == 10


class TestHttpReaderConnect:
    def test_connect_creates_session(self, base_config, mock_session):
        reader = HttpReader(base_config)
        reader.connect()
        assert reader._session is not None

    def test_disconnect_closes_session(self, base_config, mock_session):
        reader = HttpReader(base_config)
        reader.connect()
        reader.disconnect()
        mock_session.close.assert_called_once()
        assert reader._session is None

    def test_read_batch_without_connect_raises(self, base_config):
        reader = HttpReader(base_config)
        with pytest.raises(RuntimeError, match="not connected"):
            list(reader.read_batch())


class TestHttpReaderReadBatch:
    def test_list_response_yields_records(self, base_config, mock_session):
        mock_response = MagicMock()
        mock_response.json.return_value = [
            {"sensor_id": "s1", "timestamp": 1700000000.0, "temperature": 22.5},
            {"sensor_id": "s2", "timestamp": 1700000001.0, "humidity": 60.0},
        ]
        mock_session.get.return_value = mock_response

        reader = HttpReader(base_config)
        reader.connect()
        records = list(reader.read_batch())

        assert len(records) == 2
        assert records[0].sensor_id == "s1"
        assert records[0].values["temperature"] == 22.5
        assert records[1].sensor_id == "s2"

    def test_dict_response_with_data_key(self, base_config, mock_session):
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "data": [{"sensor_id": "s3", "timestamp": 1700000002.0, "rainfall": 5.1}]
        }
        mock_session.get.return_value = mock_response

        reader = HttpReader(base_config)
        reader.connect()
        records = list(reader.read_batch())

        assert len(records) == 1
        assert records[0].sensor_id == "s3"
        assert records[0].source == base_config["url"]
