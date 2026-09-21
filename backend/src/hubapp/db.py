from contextlib import contextmanager
from pathlib import Path

import psycopg
from psycopg_pool import ConnectionPool
from ragapp.retrieval.store import init_schema as init_ragapp_schema

from hubapp.config import settings

SCHEMA_PATH = Path(__file__).parent / "schema.sql"

_pool: ConnectionPool | None = None


def _get_pool() -> ConnectionPool:
    global _pool
    if _pool is None:
        _pool = ConnectionPool(settings.database_url, min_size=1, max_size=5, kwargs={"autocommit": True})
    return _pool


@contextmanager
def get_connection():
    with _get_pool().connection() as conn:
        yield conn


def init_schema() -> None:
    # ragapp's schema (documents, chunks, query_logs) must exist first: this app's
    # product_documents.document_id is a real FK into ragapp's documents table.
    init_ragapp_schema()
    conn = psycopg.connect(settings.database_url, autocommit=True)
    try:
        conn.execute(SCHEMA_PATH.read_text())
    finally:
        conn.close()
