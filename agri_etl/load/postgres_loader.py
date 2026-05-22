"""PostgreSQL loader for writing sensor records to a Postgres database."""

from __future__ import annotations

from typing import Any

try:
    import psycopg2
    import psycopg2.extras
except ImportError as exc:  # pragma: no cover
    raise ImportError("psycopg2 is required for PostgresLoader") from exc

from agri_etl.load.base_loader import BaseLoader, LoadResult
from agri_etl.transform.base_transformer import TransformResult


class PostgresLoader(BaseLoader):
    """Writes TransformResult records into a PostgreSQL table."""

    REQUIRED_CONFIG_KEYS = ("dsn", "table")
    DEFAULT_BATCH_SIZE = 500

    def _validate_config(self) -> None:
        for key in self.REQUIRED_CONFIG_KEYS:
            if key not in self.config:
                raise ValueError(f"PostgresLoader requires '{key}' in config")
        if not isinstance(self.config["table"], str) or not self.config["table"].strip():
            raise ValueError("'table' must be a non-empty string")
        self.config.setdefault("batch_size", self.DEFAULT_BATCH_SIZE)

    def connect(self) -> None:
        self._conn = psycopg2.connect(self.config["dsn"])
        self._conn.autocommit = False

    def disconnect(self) -> None:
        if self._conn:
            self._conn.close()
            self._conn = None

    def write_batch(self, results: list[TransformResult]) -> LoadResult:
        if not results:
            return LoadResult.success(written=0)

        table = self.config["table"]
        rows = []
        for r in results:
            d = r.to_dict()
            rows.append(
                (
                    d["sensor_id"],
                    d["timestamp"],
                    psycopg2.extras.Json(d["readings"]),
                    psycopg2.extras.Json(d["metadata"]),
                )
            )

        sql = (
            f"INSERT INTO {table} (sensor_id, timestamp, readings, metadata) "
            "VALUES %s ON CONFLICT DO NOTHING"
        )
        try:
            with self._conn.cursor() as cur:
                psycopg2.extras.execute_values(
                    cur, sql, rows, page_size=self.config["batch_size"]
                )
            self._conn.commit()
        except Exception as exc:  # noqa: BLE001
            self._conn.rollback()
            return LoadResult(written=0, failed=len(rows), errors=[str(exc)])

        return LoadResult.success(written=len(rows))
