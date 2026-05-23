"""Tests for HttpLoader."""
from __future__ import annotations

from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

import pytest
import requests

from agri_etl.load.http_loader import HttpLoader
from agri_etl.transform.base_transformer import TransformResult
from agri_etl.ingestion.base_reader import SensorRecord

_TS = datetime(2024, 6, 1, 12, 0, 0, tzinfo=timezone.utc)


def _make_result(sensor_id: str = "s1", value: float = 22.5) -> TransformResult:
    record = SensorRecord(sensor_id=sensor_id, timestamp=_TS, payload={"temp": value})
    return TransformResult(record=record, transformed_payload={"temp_c": value}, errors=[])


@pytest.fixture()
def base_config() -> dict:
    return {"url": "http://example.com/api/ingest"}


@pytest.fixture()
def mock_session():
    with patch("agri_etl.load.http_loader.requests.Session") as mock_cls:
        session = MagicMock()
        mock_cls.return_value = session
        resp = MagicMock()
        resp.status_code = 200
        resp.raise_for_status.return_value = None
        session.post.return_value = resp
        yield session


class TestHttpLoaderInit:
    def test_missing_url_raises(self):
        with pytest.raises(ValueError, match="url"):
            HttpLoader(config={})

    def test_defaults_applied(self, base_config):
        loader = HttpLoader(config=base_config)
        assert loader.config["timeout"] == 10
        assert loader.config["batch_key"] == "records"
        assert loader.config["verify_ssl"] is True
        assert "Content-Type" in loader.config["headers"]

    def test_custom_timeout(self, base_config):
        base_config["timeout"] = 30
        loader = HttpLoader(config=base_config)
        assert loader.config["timeout"] == 30


class TestHttpLoaderConnection:
    def test_connect_creates_session(self, base_config, mock_session):
        loader = HttpLoader(config=base_config)
        loader.connect()
        assert loader._session is not None

    def test_disconnect_closes_session(self, base_config, mock_session):
        loader = HttpLoader(config=base_config)
        loader.connect()
        loader.disconnect()
        mock_session.close.assert_called_once()
        assert loader._session is None

    def test_write_batch_without_connect_raises(self, base_config):
        loader = HttpLoader(config=base_config)
        with pytest.raises(RuntimeError, match="not connected"):
            loader.write_batch([_make_result()])


class TestHttpLoaderWriteBatch:
    def test_successful_post(self, base_config, mock_session):
        loader = HttpLoader(config=base_config)
        loader.connect()
        result = loader.write_batch([_make_result(), _make_result("s2")])
        assert result.records_written == 2
        assert result.errors == []
        mock_session.post.assert_called_once()

    def test_http_error_returns_load_result_with_errors(self, base_config, mock_session):
        mock_session.post.side_effect = requests.RequestException("connection refused")
        loader = HttpLoader(config=base_config)
        loader.connect()
        result = loader.write_batch([_make_result()])
        assert result.records_written == 0
        assert len(result.errors) == 1
        assert "connection refused" in result.errors[0]

    def test_custom_batch_key_used(self, base_config, mock_session):
        import json
        base_config["batch_key"] = "data"
        loader = HttpLoader(config=base_config)
        loader.connect()
        loader.write_batch([_make_result()])
        call_kwargs = mock_session.post.call_args
        body = json.loads(call_kwargs.kwargs["data"])
        assert "data" in body
