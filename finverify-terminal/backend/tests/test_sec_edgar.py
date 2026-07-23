"""
Tests for SEC EDGAR ingestion fallback and XBRL extraction paths.

Covers the live-fetch fallback to FALLBACK_FILINGS, schema validation of
the fallback dataset, mocked XBRL parsing, and DVL verification over every
extracted metric before storage.

Usage: pytest tests/test_sec_edgar.py   (from backend/ directory)
"""

import json
from unittest.mock import MagicMock, patch

import pytest

from ingestion.sec_edgar import (
    FALLBACK_FILINGS,
    TICKER_TO_CIK,
    extract_xbrl_metrics,
    fetch_company_facts,
    ingest_ticker,
    verify_and_store_metrics,
)


# ---------------------------------------------------------------------------
# Fixture builders
# ---------------------------------------------------------------------------


def make_xbrl_fixture(ticker: str, values: dict) -> dict:
    """Build a minimal XBRL CompanyFacts JSON for extract_xbrl_metrics."""
    cik = TICKER_TO_CIK[ticker].lstrip("0")
    accn = f"0000{cik}-24-000123"
    base = {
        "cik": int(cik),
        "entityName": f"{ticker} INC",
        "facts": {
            "us-gaap": {},
        },
    }

    concept_map = {
        "net_income": "NetIncomeLoss",
        "revenue": "Revenues",
        "total_assets": "Assets",
        "eps_diluted": "EarningsPerShareDiluted",
        "operating_income": "OperatingIncomeLoss",
    }

    for metric_name, value in values.items():
        concept = concept_map.get(metric_name)
        if not concept:
            continue

        unit = "USD/shares" if metric_name == "eps_diluted" else "USD"
        base["facts"]["us-gaap"][concept] = {
            "label": concept,
            "description": f"{concept} for {ticker}",
            "units": {
                unit: [
                    {
                        "start": "2023-10-01",
                        "end": "2024-09-30",
                        "val": value,
                        "accn": accn,
                        "fy": 2024,
                        "fp": "FY",
                        "form": "10-K",
                        "filed": "2024-11-01",
                        "frame": "CY2024",
                    }
                ]
            },
        }

    return base


# ---------------------------------------------------------------------------
# Fallback data schema
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("ticker", list(TICKER_TO_CIK.keys()))
def test_fallback_filings_schema(ticker):
    """FALLBACK_FILINGS has required keys and valid metric entries for every watchlist ticker."""
    assert ticker in FALLBACK_FILINGS
    filing = FALLBACK_FILINGS[ticker]
    for key in ["filing_date", "period", "form_type", "source_url", "metrics"]:
        assert key in filing

    for metric_name, data in filing["metrics"].items():
        for key in ["value", "question"]:
            assert key in data
        assert isinstance(data["value"], (int, float))
        assert "{ticker}" not in data["question"]


def test_fallback_filings_cover_expected_metrics():
    """Each fallback filing covers the 5 standard SEC metrics."""
    expected = {"net_income", "revenue", "total_assets", "eps_diluted", "operating_income"}
    for ticker, filing in FALLBACK_FILINGS.items():
        assert set(filing["metrics"].keys()) == expected, f"{ticker} missing metrics"


# ---------------------------------------------------------------------------
# Ingest with fallback (fetch_company_facts returns None)
# ---------------------------------------------------------------------------


def _patch_dependencies(monkeypatch):
    """Avoid network and database side effects during ingest_ticker tests."""
    monkeypatch.setattr("ingestion.sec_edgar.time.sleep", lambda s: None)
    monkeypatch.setattr("ingestion.db.upsert_fundamental", lambda **kwargs: None)


@pytest.mark.parametrize("ticker", ["AAPL", "TSLA"])
def test_ingest_ticker_falls_back_when_fetch_returns_none(monkeypatch, ticker):
    _patch_dependencies(monkeypatch)
    monkeypatch.setattr("ingestion.sec_edgar.fetch_company_facts", lambda t: None)

    results = ingest_ticker(ticker)
    assert len(results) > 0

    fallback_metrics = FALLBACK_FILINGS[ticker]["metrics"]
    returned_names = {r["metric_name"] for r in results}
    assert returned_names == set(fallback_metrics.keys())

    for r in results:
        assert r["ticker"] == ticker
        assert "dvl_trust" in r
        assert "verified_value" in r
        assert r["source_url"] == FALLBACK_FILINGS[ticker]["source_url"]


# ---------------------------------------------------------------------------
# XBRL extraction with mocked HTTP
# ---------------------------------------------------------------------------


def test_extract_xbrl_metrics_parses_mocked_response():
    """A mocked XBRL CompanyFacts response is parsed into expected metric fields."""
    values = {
        "net_income": 93_736_000_000,
        "revenue": 391_035_000_000,
        "total_assets": 364_980_000_000,
        "eps_diluted": 6.11,
        "operating_income": 118_658_000_000,
    }
    fixture = make_xbrl_fixture("AAPL", values)
    results = extract_xbrl_metrics(fixture, "AAPL")

    assert len(results) == 5
    by_name = {r["metric_name"]: r for r in results}

    for metric_name, value in values.items():
        assert metric_name in by_name
        r = by_name[metric_name]
        assert r["raw_value"] == pytest.approx(value)
        assert r["period"] == "FY2024"
        assert r["filing_date"] == "2024-11-01"
        assert "source_url" in r
        assert r["source_url"].startswith("https://www.sec.gov/Archives/edgar/data/")
        assert "AAPL" in r["question"]


def test_extract_xbrl_metrics_returns_empty_on_missing_us_gaap():
    assert extract_xbrl_metrics({}, "AAPL") == []
    assert extract_xbrl_metrics({"facts": {}}, "AAPL") == []


# ---------------------------------------------------------------------------
# verify_and_store_metrics runs full_verify on every metric
# ---------------------------------------------------------------------------


def test_verify_and_store_metrics_calls_full_verify_for_each_metric(monkeypatch):
    """Every extracted or fallback metric is passed through full_verify before storage."""
    calls = []

    def fake_full_verify(question, predicted, actual=None):
        calls.append((question, predicted))
        return predicted * 2, [], "HIGH", "#00ff88"

    monkeypatch.setattr("ingestion.sec_edgar.full_verify", fake_full_verify)
    monkeypatch.setattr("ingestion.db.upsert_fundamental", lambda **kwargs: None)

    metrics = [
        {"metric_name": "revenue", "raw_value": 100, "question": "What was revenue?", "source_url": "x"},
        {"metric_name": "net_income", "raw_value": 50, "question": "What was net income?", "source_url": "x"},
    ]
    results = verify_and_store_metrics("AAPL", metrics)

    assert len(calls) == 2
    assert calls[0] == ("What was revenue?", 100)
    assert calls[1] == ("What was net income?", 50)

    for r in results:
        assert r["dvl_trust"] == "HIGH"
        assert "verified_value" in r


# ---------------------------------------------------------------------------
# End-to-end fallback path without network
# ---------------------------------------------------------------------------


def test_ingest_ticker_xbrl_path_skips_fallback(monkeypatch):
    """When XBRL returns metrics, the fallback data is not used."""
    _patch_dependencies(monkeypatch)

    values = {
        "net_income": 93_736_000_000,
        "revenue": 391_035_000_000,
        "total_assets": 364_980_000_000,
        "eps_diluted": 6.11,
        "operating_income": 118_658_000_000,
    }
    fixture = make_xbrl_fixture("AAPL", values)
    monkeypatch.setattr("ingestion.sec_edgar.fetch_company_facts", lambda t: fixture)

    results = ingest_ticker("AAPL")
    returned_names = {r["metric_name"] for r in results}
    assert returned_names == set(values.keys())

    # Source URL should point to the XBRL-derived accession, not the fallback URL.
    for r in results:
        assert "Archives/edgar/data" in r["source_url"]
        assert r["source_url"] != FALLBACK_FILINGS["AAPL"]["source_url"]
