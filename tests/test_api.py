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
