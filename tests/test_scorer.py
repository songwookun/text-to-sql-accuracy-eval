import json
from pathlib import Path

import pytest

from text2sql.scorer import is_lenient_correct, normalize, same_on_shared_columns, score

GOLDEN = {
    g["id"]: g["sql"]
    for g in map(json.loads, Path("golden.jsonl").read_text().splitlines())
}


def test_normalize_rounds_and_unifies_numbers():
    assert normalize([(5, 4.08642)], ordered=True) == [(5.0, 4.09)]


def test_normalize_sorts_mixed_types():
    assert normalize([(None,), (1,), ("a",)], ordered=False)


@pytest.mark.parametrize("gid", sorted(GOLDEN))
def test_gold_vs_gold_is_correct(gid):
    assert score(GOLDEN[gid], GOLDEN[gid]).label == "correct"


@pytest.mark.parametrize("gid, pred, label", [
    ("Q17", "SELECT SUM(i.price) FROM orders o JOIN order_items i ON o.order_id = i.order_id "
            "JOIN order_payments p ON o.order_id = p.order_id "
            "WHERE o.order_status = 'delivered' AND p.payment_type = 'voucher'", "silent_wrong"),
    ("Q18", "SELECT COUNT(DISTINCT customer_id) FROM orders "
            "WHERE order_purchase_timestamp LIKE '2018%'", "silent_wrong"),
    ("Q03", "SELECT ROUND(AVG(review_score), 2) FROM order_reviews", "correct"),
    ("Q02", "SELECT payment_type AS t, COUNT(*) AS cnt FROM order_payments "
            "GROUP BY 1 ORDER BY cnt DESC", "correct"),
    ("Q05", "SELECT seller_state, COUNT(*) n FROM sellers GROUP BY 1 ORDER BY n ASC LIMIT 3", "silent_wrong"),
    ("Q05", "SELECT seller_state FROM sellers GROUP BY 1 ORDER BY COUNT(*) DESC LIMIT 3", "silent_wrong"),
    ("Q20", "SELECT * FROM orders WHERE order_purchase_timestamp >= '2019-01-01'", "correct"),
    ("Q20", "SELECT COUNT(*) FROM orders WHERE order_purchase_timestamp >= '2019-01-01'", "silent_wrong"),
    ("Q01", "SELECT COUNT(*) FROM orders WHERE status = 1", "error"),
    ("Q01", "DELETE FROM orders", "error"),
    ("Q01", "SELECT COUNT(*) FROM sales", "error"),
])
def test_traps(gid, pred, label):
    assert score(GOLDEN[gid], pred).label == label


def test_shared_columns_missing_count_column():
    assert same_on_shared_columns([("a", 3), ("b", 2)], [("a",), ("b",)], ordered=True)


def test_shared_columns_wrong_order_is_not_lenient():
    assert not same_on_shared_columns([("a", 3), ("b", 2)], [("b",), ("a",)], ordered=True)


def test_shared_columns_same_width_is_not_lenient():
    assert not same_on_shared_columns([(1,)], [(2,)], ordered=True)


def test_lenient_q13_names_only():
    pred = ("SELECT t.product_category_name_english FROM customers c JOIN orders o ON c.customer_id = o.customer_id "
            "JOIN order_items i ON o.order_id = i.order_id JOIN products p ON i.product_id = p.product_id "
            "JOIN product_category_name_translation t ON p.product_category_name = t.product_category_name "
            "WHERE c.customer_state = 'SP' GROUP BY 1 ORDER BY COUNT(*) DESC LIMIT 5")
    assert score(GOLDEN["Q13"], pred).label == "silent_wrong"
    assert is_lenient_correct(GOLDEN["Q13"], pred)


def test_lenient_does_not_forgive_wrong_values():
    pred = "SELECT SUM(payment_value) FROM order_payments"
    assert not is_lenient_correct(GOLDEN["Q19"], pred)
