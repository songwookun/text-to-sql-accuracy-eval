import json
from pathlib import Path

import pytest

from text2sql.lint import lint

GOLDEN = [json.loads(line) for line in Path("golden.jsonl").read_text().splitlines()]


def codes(sql: str, question: str = "") -> list[str]:
    return [i.code for i in lint(sql, question)]


@pytest.mark.parametrize("g", GOLDEN, ids=lambda g: g["id"])
def test_gold_has_no_issues(g):
    assert codes(g["sql"], g["question"]) == []


def test_fan_out_items_and_payments():
    sql = ("SELECT SUM(i.price) FROM orders o JOIN order_items i ON o.order_id = i.order_id "
           "JOIN order_payments p ON o.order_id = p.order_id WHERE o.order_status = 'delivered' AND p.payment_type = 'voucher'")
    assert "fan_out" in codes(sql, "바우처 매출")


def test_in_subquery_is_not_fan_out():
    sql = ("SELECT SUM(i.price) FROM orders o JOIN order_items i ON o.order_id = i.order_id "
           "WHERE o.order_status = 'delivered' AND o.order_id IN (SELECT order_id FROM order_payments WHERE payment_type = 'voucher')")
    assert codes(sql, "바우처 매출") == []


def test_count_dup_without_distinct():
    sql = "SELECT o.order_status, COUNT(o.order_id) FROM orders o JOIN order_reviews r ON o.order_id = r.order_id GROUP BY 1"
    assert codes(sql) == ["count_dup"]
    assert codes(sql.replace("COUNT(o.order_id)", "COUNT(DISTINCT o.order_id)")) == []


def test_revenue_with_payment_value():
    sql = "SELECT SUM(p.payment_value) FROM order_payments p JOIN orders o ON p.order_id = o.order_id WHERE o.order_status = 'delivered'"
    assert codes(sql, "2017년 매출은?") == ["metric_expr"]


def test_revenue_without_delivered_filter_unqualified_columns():
    sql = "SELECT SUM(price) FROM order_items JOIN orders USING (order_id)"
    assert codes(sql, "매출 알려줘") == ["metric_filter"]


def test_metric_rules_need_keyword():
    assert codes("SELECT SUM(payment_value) FROM order_payments", "결제 금액 합계") == []


def test_unparseable_sql_returns_empty():
    assert codes("SELEC nope") == []
