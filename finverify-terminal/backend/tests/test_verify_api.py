"""
Tests for the /v1/verify standalone DVL API (pytest + TestClient).

Replaces the old test_verify_api.py that required a running server.
These tests exercise the FastAPI app in-process.

Usage: pytest tests/test_verify_api.py   (from backend/ directory)
"""

import pytest
from fastapi.testclient import TestClient

from app.main import app


@pytest.fixture
def client():
    return TestClient(app)


# ---------------------------------------------------------------------------
# /v1/verify endpoint cases
# ---------------------------------------------------------------------------


def test_v1_verify_scale_mul100_profit_margin(client):
    resp = client.post("/v1/verify", json={
        "question": "What was the profit margin?",
        "raw_value": 0.2531,
    })
    assert resp.status_code == 200
    data = resp.json()
    assert data["trust_score"] == "LOW"
    assert "scale_mul100" in data["correction_applied"]
    assert 25.0 < data["verified_value"] < 26.0
    assert data["delta_pct"] > 0
    for field in ["dvl_version", "timestamp", "trust_color"]:
        assert field in data


def test_v1_verify_cet1_ratio_no_correction(client):
    resp = client.post("/v1/verify", json={
        "question": "What was the CET1 ratio?",
        "raw_value": 10.935,
    })
    assert resp.status_code == 200
    data = resp.json()
    assert data["trust_score"] == "HIGH"
    assert data["correction_applied"] is None
    assert data["verified_value"] == pytest.approx(10.935, abs=1e-6)
    assert data["delta_pct"] == 0.0


def test_v1_verify_htm_decrease_no_correction(client):
    resp = client.post("/v1/verify", json={
        "question": "What was the percentage decrease in HTM securities?",
        "raw_value": -34.11,
    })
    assert resp.status_code == 200
    data = resp.json()
    # -34.11 is in the ambiguous [1,100] range, so DVL leaves it unchanged.
    assert data["trust_score"] == "HIGH"
    assert data["correction_applied"] is None
    assert data["verified_value"] == pytest.approx(-34.11, abs=1e-6)


def test_v1_verify_pe_ratio_no_correction(client):
    resp = client.post("/v1/verify", json={
        "question": "What was the price to earnings ratio?",
        "raw_value": 28.5,
    })
    assert resp.status_code == 200
    data = resp.json()
    assert data["trust_score"] == "HIGH"
    assert data["correction_applied"] is None
    assert data["verified_value"] == pytest.approx(28.5, abs=1e-6)


def test_v1_verify_revenue_growth_scale_mul100(client):
    resp = client.post("/v1/verify", json={
        "question": "What was the revenue growth rate?",
        "raw_value": 0.0623,
    })
    assert resp.status_code == 200
    data = resp.json()
    assert data["trust_score"] == "LOW"
    assert "scale_mul100" in data["correction_applied"]
    assert 6.0 < data["verified_value"] < 7.0


def test_v1_verify_missing_field_returns_422(client):
    resp = client.post("/v1/verify", json={"question": "What was revenue?"})
    assert resp.status_code == 422


def test_health_check_returns_ok(client):
    resp = client.get("/health")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "ok"
    assert data["dvl"] == "online"
    assert "llm" in data
