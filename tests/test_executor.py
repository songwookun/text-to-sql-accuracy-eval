import sqlite3
import time

import pytest

from text2sql.executor import QueryTimeout, execute


def test_returns_rows():
    assert execute("SELECT COUNT(*) FROM orders") == [(99441,)]


def test_read_only():
    with pytest.raises(sqlite3.OperationalError, match="readonly"):
        execute("CREATE TABLE x (a)")


def test_sql_error_passes_through():
    with pytest.raises(sqlite3.OperationalError, match="no such column"):
        execute("SELECT nope FROM orders")


def test_timeout():
    start = time.monotonic()
    with pytest.raises(QueryTimeout):
        execute("SELECT COUNT(*) FROM orders a, orders b", timeout=1.0)
    assert time.monotonic() - start < 2.0


def test_connection_reusable_after_timeout():
    with pytest.raises(QueryTimeout):
        execute("SELECT COUNT(*) FROM orders a, orders b", timeout=0.5)
    assert execute("SELECT 1") == [(1,)]
