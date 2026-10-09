"""Small DB-API compatibility layer for local SQLite and hosted PostgreSQL."""
import os
import re
import sqlite3
from contextlib import contextmanager


class HybridRow(dict):
    """Allow existing row access by name and SQLite-style numeric index."""

    def __getitem__(self, key):
        if isinstance(key, int):
            return tuple(self.values())[key]
        return super().__getitem__(key)


class Connection:
    def __init__(self, connection, postgres):
        self._connection = connection
        self._postgres = postgres

    def execute(self, query, parameters=()):
        if self._postgres:
            query = re.sub(r"\?", "%s", query)
        return self._connection.execute(query, parameters)

    def commit(self):
        self._connection.commit()

    def rollback(self):
        self._connection.rollback()

    def close(self):
        self._connection.close()

    @property
    def is_postgres(self):
        return self._postgres


def database_url():
    return os.environ.get("DATABASE_URL", "").strip() or None


def using_postgres():
    return database_url() is not None


@contextmanager
def connect(db_path, timeout=10):
    url = database_url()
    if url is None:
        raw_connection = sqlite3.connect(str(db_path), timeout=timeout)
        raw_connection.row_factory = sqlite3.Row
        connection = Connection(raw_connection, postgres=False)
    else:
        import psycopg
        from psycopg.rows import dict_row

        def hybrid_row_factory(cursor):
            make_row = dict_row(cursor)
            return lambda values: HybridRow(make_row(values))

        raw_connection = psycopg.connect(
            url,
            connect_timeout=5,
            prepare_threshold=None,
            row_factory=hybrid_row_factory,
        )
        connection = Connection(raw_connection, postgres=True)

    try:
        yield connection
        connection.commit()
    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()
