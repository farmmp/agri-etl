"""Tests for PostgresLoader."""

from __future__ import annotations

from datetime import datetime, timezone
from unittest.mock import MagicMock, patch, call

import pytest

from agri_etl.transform.base_transformer import TransformResult
from agri_etl.ingestion.base_reader import SensorRecord


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

TS = datetime(2024, 6, 1, 12, 0, 0, tzinfo=timezone.utc)


def _make_result(sensor_id: str = "s1") -> TransformResult:
    record = SensorRecord(
        sensor_id=sensor_id,
        timestamp=TS,
        readings={"temp": 22.5},
        metadata={"unit": "C"},
    )
    return TransformResult(record=record, warnings=[])


@pytest.fixture()
def base_config() -> dict:
    return {"dsn": "postgresql://localhost/test", "table": "sensor_data"}


@pytest.fixture()
def mock_psycopg2():
    with patch("agri_etl.load.postgres_loader.psycopg2") as mock:
        mock_conn = MagicMock()
        mock.connect.return_value = mock_conn
        mock.extras = MagicMock()
        mock.extras.Json.side_effect = lambda x: x
        yield mock, mock_conn


# ---------------------------------------------------------------------------
# Init / validation
# ---------------------------------------------------------------------------

class TestPostgresLoaderInit:
    def test_missing_dsn_raises(self):
        from agri_etl.load.postgres_loader import PostgresLoader
        with pytest.raises(ValueError, match="dsn"):
            PostgresLoader({"table": "t"})

    def test_missing_table_raises(self):
        from agri_etl.load.postgres_loader import PostgresLoader
        with pytest.raises(ValueError, match="table"):
            PostgresLoader({"dsn": "postgresql://localhost/test"})

    def test_empty_table_raises(self):
        from agri_etl.load.postgres_loader import PostgresLoader
        with pytest.raises(ValueError, match="non-empty"):
            PostgresLoader({"dsn": "postgresql://localhost/test", "table": "  "})

    def test_defaults_applied(self, base_config):
        from agri_etl.load.postgres_loader import PostgresLoader
        loader = PostgresLoader(base_config)
        assert loader.config["batch_size"] == PostgresLoader.DEFAULT_BATCH_SIZE


# ---------------------------------------------------------------------------
# connect / disconnect
# ---------------------------------------------------------------------------

class TestPostgresLoaderConnection:
    def test_connect_calls_psycopg2(self, base_config, mock_psycopg2):
        from agri_etl.load.postgres_loader import PostgresLoader
        mock, mock_conn = mock_psycopg2
        loader = PostgresLoader(base_config)
        loader.connect()
        mock.connect.assert_called_once_with(base_config["dsn"])
        assert mock_conn.autocommit is False

    def test_disconnect_closes_connection(self, base_config, mock_psycopg2):
        from agri_etl.load.postgres_loader import PostgresLoader
        mock, mock_conn = mock_psycopg2
        loader = PostgresLoader(base_config)
        loader.connect()
        loader.disconnect()
        mock_conn.close.assert_called_once()
        assert loader._conn is None


# ---------------------------------------------------------------------------
# write_batch
# ---------------------------------------------------------------------------

class TestPostgresLoaderWriteBatch:
    def test_empty_batch_returns_zero(self, base_config, mock_psycopg2):
        from agri_etl.load.postgres_loader import PostgresLoader
        _, mock_conn = mock_psycopg2
        loader = PostgresLoader(base_config)
        loader.connect()
        result = loader.write_batch([])
        assert result.written == 0
        assert result.failed == 0

    def test_successful_write(self, base_config, mock_psycopg2):
        from agri_etl.load.postgres_loader import PostgresLoader
        mock, mock_conn = mock_psycopg2
        loader = PostgresLoader(base_config)
        loader.connect()
        records = [_make_result("s1"), _make_result("s2")]
        result = loader.write_batch(records)
        assert result.written == 2
        assert result.failed == 0
        mock_conn.commit.assert_called_once()

    def test_db_error_returns_failed(self, base_config, mock_psycopg2):
        from agri_etl.load.postgres_loader import PostgresLoader
        mock, mock_conn = mock_psycopg2
        mock_conn.cursor.return_value.__enter__.return_value.execute.side_effect = Exception("db error")
        mock.extras.execute_values.side_effect = Exception("db error")
        loader = PostgresLoader(base_config)
        loader.connect()
        result = loader.write_batch([_make_result()])
        assert result.failed == 1
        assert "db error" in result.errors[0]
        mock_conn.rollback.assert_called_once()
