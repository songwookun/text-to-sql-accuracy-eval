import pytest
from fastapi.testclient import TestClient

import api


@pytest.fixture
def client(monkeypatch):
    monkeypatch.setattr(api, "MOCK_LLM", True)
    return TestClient(api.app)


def test_ask_golden_question(client):
    r = client.post("/api/ask", json={"question": "배송 완료된 주문은 몇 건이야?"}).json()
    assert r["rows"] == [[96478]] and r["error"] is None and r["mock"]


def test_ask_returns_columns(client):
    r = client.post("/api/ask", json={"question": "판매자가 가장 많은 주(state) 상위 3개 알려줘"}).json()
    assert r["columns"] == ["seller_state", "n"] and len(r["rows"]) == 3


def test_unsafe_sql_is_reported(client, monkeypatch):
    monkeypatch.setattr(api, "GOLDEN", {"지워줘": "DELETE FROM orders"})
    r = client.post("/api/ask", json={"question": "지워줘"}).json()
    assert r["error_type"] == "unsafe" and r["rows"] == []


def test_empty_question_rejected(client):
    assert client.post("/api/ask", json={"question": ""}).status_code == 422


def test_split_comments():
    notes, sql = api.split_comments("-- 해석: 상품 개수 기준\n-- 정의 밖: 고객 이탈률, 활성 판매자\nSELECT 1")
    assert notes == {"해석": "상품 개수 기준", "정의 밖": "고객 이탈률, 활성 판매자"} and sql == "SELECT 1"
    assert api.split_comments("SELECT 1") == ({}, "SELECT 1")


def test_parse_terms():
    assert api.parse_terms("고객 이탈률, 활성 판매자") == ["고객 이탈률", "활성 판매자"]
    assert api.parse_terms("없음") == [] and api.parse_terms("") == []


def test_undefined_terms_in_response(client, monkeypatch):
    monkeypatch.setattr(api, "GOLDEN", {"이탈률은?": "-- 해석: x\n-- 정의 밖: 고객 이탈률\nSELECT 1"})
    r = client.post("/api/ask", json={"question": "이탈률은?"}).json()
    assert r["undefined_terms"] == ["고객 이탈률"] and r["interpretation"] == "x" and r["sql"] == "SELECT 1"


def test_demo_rules_only_in_demo_prompt():
    from text2sql.prompt import build_prompt
    plain, demo = build_prompt("q", "v3"), build_prompt("q", "v3", api.DEMO_RULES)
    assert "Output rules" not in plain and demo.endswith("## Question\nq")


def test_lint_warnings_in_response(client, monkeypatch):
    monkeypatch.setattr(api, "GOLDEN", {"2017년 매출은?": "SELECT SUM(payment_value) FROM order_payments"})
    r = client.post("/api/ask", json={"question": "2017년 매출은?"}).json()
    assert r["rows"] and len(r["warnings"]) == 2
