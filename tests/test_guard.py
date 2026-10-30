import sqlite3

import pytest

from text2sql.guard import UnsafeSQLError, guard

DB = "file:data/olist.db?mode=ro"


def run(sql):
    conn = sqlite3.connect(DB, uri=True)
    try:
        return conn.execute(sql).fetchall()
    finally:
        conn.close()


# 기본 동작
@pytest.mark.parametrize("sql", [
    "SELECT 1",
    "select 1;",
    "  WITH t AS (SELECT 1) SELECT * FROM t  ",
    "SELECT * FROM orders LIMIT 10 OFFSET 5",
])
def test_allows_select(sql):
    run(guard(sql))


@pytest.mark.parametrize("sql", [
    "DELETE FROM orders",
    "DROP TABLE orders",
    "SELECT 1; DROP TABLE orders",
    "selection",
])
def test_rejects_non_select(sql):
    with pytest.raises(UnsafeSQLError):
        guard(sql)


def test_adds_limit():
    assert len(run(guard("SELECT * FROM orders"))) == 1000


def test_limit_survives_trailing_comment():
    assert len(run(guard("SELECT * FROM orders -- 전체 주문"))) == 1000


# 정규식 한계 — sqlglot 교체 후 통과해야 함
def test_semicolon_inside_string_is_ok():
    run(guard("SELECT * FROM customers WHERE customer_city = 'a;b'"))


def test_rejects_cte_wrapped_delete():
    with pytest.raises(UnsafeSQLError):
        guard("WITH x AS (SELECT 1) DELETE FROM orders")


def test_rejects_unknown_table():
    with pytest.raises(UnsafeSQLError):
        guard("SELECT * FROM sqlite_master")


def test_caps_huge_limit():
    assert len(run(guard("SELECT * FROM order_items LIMIT 99999999"))) == 1000


def test_limit_in_comment_does_not_count():
    assert len(run(guard("SELECT * FROM orders -- LIMIT 5"))) == 1000
