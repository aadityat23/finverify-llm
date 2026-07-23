"""
In-process integration tests for the FastAPI backend.

Uses fastapi.testclient.TestClient so no running server is required.
Covers /health, /verify, and /v1/fcg/verify endpoints.

Usage: pytest tests/test_app_integration.py   (from backend/ directory)
"""

import pytest
from fastapi.testclient import TestClient

from app.main import app


@pytest.fixture
def client():
    return TestClient(app)


# ---------------------------------------------------------------------------
# /health
# ---------------------------------------------------------------------------


def test_health_endpoint(client):
    resp = client.get("/health")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "ok"
    assert data["dvl"] == "online"
    assert "llm" in data
    assert "model" in data


# ---------------------------------------------------------------------------
# /verify (DVL-only, no LLM call)
# ---------------------------------------------------------------------------


def test_verify_endpoint_scale_mul100(client):
    resp = client.post("/verify", json={
        "question": "What was the revenue growth rate?",
        "raw_number": 0.152,
    })
    assert resp.status_code == 200
    data = resp.json()
    assert data["verified_number"] == pytest.approx(15.2, abs=1e-2)
    assert data["trust_score"] == "LOW"
    assert data["mode"] in ("numerical", "ratio")
    assert data["verified"] is True


def test_verify_endpoint_zero_still_valid(client):
    resp = client.post("/verify", json={
        "question": "What was the revenue growth rate?",
        "raw_number": 0.0,
    })
    assert resp.status_code == 200
    data = resp.json()
    assert data["trust_score"] == "HIGH"
    assert data["verified_number"] == pytest.approx(0.0, abs=1e-9)
    assert data["display_value"].startswith("0.00%")


def test_verify_endpoint_422_on_missing_raw_number(client):
    resp = client.post("/verify", json={"question": "What was revenue?"})
    assert resp.status_code == 422


# ---------------------------------------------------------------------------
# /v1/fcg/verify
# ---------------------------------------------------------------------------


def test_fcg_verify_consistent(client):
    resp = client.post("/v1/fcg/verify", json={
        "values": {
            "revenue": 100,
            "cogs": 40,
            "gross_profit": 60,
            "operating_expenses": 20,
            "operating_income": 40,
        }
    })
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "ok"
    assert data["constraint_result"]["trust"] == "CONSISTENT"
    assert "FCG-001" in data["constraint_result"]["passed"]
    assert "FCG-002" in data["constraint_result"]["passed"]


def test_fcg_verify_inconsistent(client):
    resp = client.post("/v1/fcg/verify", json={
        "values": {
            "revenue": 100,
            "cogs": 40,
            "gross_profit": 50,  # should be 60
        }
    })
    assert resp.status_code == 200
    data = resp.json()
    assert data["constraint_result"]["trust"] == "INCONSISTENT"
    violations = {v["id"] for v in data["constraint_result"]["violations"]}
    assert "FCG-001" in violations


def test_fcg_verify_partial_soft_violation(client):
    resp = client.post("/v1/fcg/verify", json={
        "values": {
            "revenue": -10,  # negative revenue is a SOFT violation
        }
    })
    assert resp.status_code == 200
    data = resp.json()
    assert data["constraint_result"]["trust"] == "PARTIAL"
    violations = {v["id"] for v in data["constraint_result"]["violations"]}
    assert "FCG-S001" in violations


def test_fcg_verify_missing_values_dict(client):
    resp = client.post("/v1/fcg/verify", json={})
    assert resp.status_code == 400


def test_fcg_verify_empty_values(client):
    resp = client.post("/v1/fcg/verify", json={"values": {"foo": "not a number"}})
    assert resp.status_code == 400


def test_fcg_verify_normalization_map(client):
    resp = client.post("/v1/fcg/verify", json={
        "values": {
            "net revenues": 100,
            "cost of goods sold": 40,
            "gross profit": 60,
        }
    })
    assert resp.status_code == 200
    data = resp.json()
    assert data["constraint_result"]["trust"] == "CONSISTENT"
    assert "normalization_map" in data
    assert data["normalization_map"]["net revenues"] == "revenue"
