"""Load package — loaders for persisting transformed sensor records."""

from agri_etl.load.base_loader import BaseLoader, LoadResult
from agri_etl.load.csv_loader import CsvLoader

try:
    from agri_etl.load.postgres_loader import PostgresLoader
except ImportError:  # psycopg2 not installed
    PostgresLoader = None  # type: ignore[assignment,misc]

__all__ = [
    "BaseLoader",
    "LoadResult",
    "CsvLoader",
    "PostgresLoader",
]
