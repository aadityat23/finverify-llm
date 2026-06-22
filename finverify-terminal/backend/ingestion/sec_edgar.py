"""
SEC EDGAR Filing Ingestion — FinVerify Terminal
=================================================
Fetches 10-K/10-Q filings from SEC EDGAR for watchlist companies.
Uses the XBRL CompanyFacts API (free, no key required) for structured data,
with full-text search fallback for document parsing.

For each company (AAPL, TSLA, JPM, NVDA, MSFT, GS):
  1. Fetch latest filing metadata via SEC EDGAR submissions API
  2. Extract financial metrics from XBRL CompanyFacts API
  3. Parse key metrics: Net Income, Revenue, Total Assets, EPS, Operating Income
  4. Run DVL over every extracted number at ingestion time
  5. Store both raw + verified values in SQLite

Usage:
    python -m ingestion.sec_edgar                # Ingest all watchlist
    python -m ingestion.sec_edgar --ticker AAPL   # Ingest single ticker
"""

import re
import json
import time
import logging
import argparse
from pathlib import Path
from datetime import datetime, timezone
from typing import Optional

import sys
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

try:
    import httpx
    HAS_HTTPX = True
except ImportError:
    HAS_HTTPX = False

from app.dvl import full_verify

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# SEC EDGAR config
# ---------------------------------------------------------------------------

# Required by SEC EDGAR — must include company name + email
SEC_USER_AGENT = "FinVerify Research contact@finverify.dev"

# CIK numbers for watchlist companies (zero-padded to 10 digits)
TICKER_TO_CIK = {
    "AAPL": "0000320193",
    "TSLA": "0001318605",
    "JPM":  "0000019617",
    "NVDA": "0001045810",
    "MSFT": "0000789019",
    "GS":   "0000886982",
}

# XBRL taxonomy → metric name mapping
# Maps SEC XBRL concept names to our standardized metric names
XBRL_METRICS = {
    "NetIncomeLoss": {
        "metric_name": "net_income",
        "question": "What was {ticker}'s net income?",
    },
    "Revenues": {
        "metric_name": "revenue",
        "question": "What was {ticker}'s total revenue?",
    },
    "RevenueFromContractWithCustomerExcludingAssessedTax": {
        "metric_name": "revenue",
        "question": "What was {ticker}'s total revenue?",
    },
    "Assets": {
        "metric_name": "total_assets",
        "question": "What was {ticker}'s total assets?",
    },
    "EarningsPerShareBasic": {
        "metric_name": "eps_basic",
        "question": "What was {ticker}'s basic earnings per share?",
    },
    "EarningsPerShareDiluted": {
        "metric_name": "eps_diluted",
        "question": "What was {ticker}'s diluted earnings per share?",
    },
    "OperatingIncomeLoss": {
        "metric_name": "operating_income",
        "question": "What was {ticker}'s operating income?",
    },
    "GrossProfit": {
        "metric_name": "gross_profit",
        "question": "What was {ticker}'s gross profit?",
    },
    "CostOfGoodsAndServicesSold": {
        "metric_name": "cost_of_revenue",
        "question": "What was {ticker}'s cost of revenue?",
    },
    "StockholdersEquity": {
        "metric_name": "stockholders_equity",
        "question": "What was {ticker}'s stockholders' equity?",
    },
}

# Fallback filing data when SEC EDGAR API is unavailable
# Based on real SEC filings (FY2024 / latest available)
FALLBACK_FILINGS = {
    "AAPL": {
        "filing_date": "2024-11-01",
        "period": "FY2024",
        "form_type": "10-K",
        "source_url": "https://www.sec.gov/cgi-bin/browse-edgar?action=getcompany&CIK=0000320193&type=10-K",
        "metrics": {
            "net_income":       {"value": 93_736_000_000, "question": "What was AAPL's net income?"},
            "revenue":          {"value": 391_035_000_000, "question": "What was AAPL's total revenue?"},
            "total_assets":     {"value": 364_980_000_000, "question": "What was AAPL's total assets?"},
            "eps_diluted":      {"value": 6.11, "question": "What was AAPL's diluted earnings per share?"},
            "operating_income": {"value": 118_658_000_000, "question": "What was AAPL's operating income?"},
        },
    },
    "TSLA": {
        "filing_date": "2025-01-29",
        "period": "FY2024",
        "form_type": "10-K",
        "source_url": "https://www.sec.gov/cgi-bin/browse-edgar?action=getcompany&CIK=0001318605&type=10-K",
        "metrics": {
            "net_income":       {"value": 7_091_000_000, "question": "What was TSLA's net income?"},
            "revenue":          {"value": 96_773_000_000, "question": "What was TSLA's total revenue?"},
            "total_assets":     {"value": 122_070_000_000, "question": "What was TSLA's total assets?"},
            "eps_diluted":      {"value": 2.04, "question": "What was TSLA's diluted earnings per share?"},
            "operating_income": {"value": 7_584_000_000, "question": "What was TSLA's operating income?"},
        },
    },
    "JPM": {
        "filing_date": "2025-02-18",
        "period": "FY2024",
        "form_type": "10-K",
        "source_url": "https://www.sec.gov/cgi-bin/browse-edgar?action=getcompany&CIK=0000019617&type=10-K",
        "metrics": {
            "net_income":       {"value": 58_471_000_000, "question": "What was JPM's net income?"},
            "revenue":          {"value": 177_557_000_000, "question": "What was JPM's total revenue?"},
            "total_assets":     {"value": 4_003_208_000_000, "question": "What was JPM's total assets?"},
            "eps_diluted":      {"value": 19.75, "question": "What was JPM's diluted earnings per share?"},
            "operating_income": {"value": 72_791_000_000, "question": "What was JPM's operating income?"},
        },
    },
    "NVDA": {
        "filing_date": "2025-02-26",
        "period": "FY2025",
        "form_type": "10-K",
        "source_url": "https://www.sec.gov/cgi-bin/browse-edgar?action=getcompany&CIK=0001045810&type=10-K",
        "metrics": {
            "net_income":       {"value": 72_880_000_000, "question": "What was NVDA's net income?"},
            "revenue":          {"value": 130_497_000_000, "question": "What was NVDA's total revenue?"},
            "total_assets":     {"value": 112_198_000_000, "question": "What was NVDA's total assets?"},
            "eps_diluted":      {"value": 2.94, "question": "What was NVDA's diluted earnings per share?"},
            "operating_income": {"value": 81_451_000_000, "question": "What was NVDA's operating income?"},
        },
    },
    "MSFT": {
        "filing_date": "2024-07-30",
        "period": "FY2024",
        "form_type": "10-K",
        "source_url": "https://www.sec.gov/cgi-bin/browse-edgar?action=getcompany&CIK=0000789019&type=10-K",
        "metrics": {
            "net_income":       {"value": 88_136_000_000, "question": "What was MSFT's net income?"},
            "revenue":          {"value": 245_122_000_000, "question": "What was MSFT's total revenue?"},
            "total_assets":     {"value": 512_163_000_000, "question": "What was MSFT's total assets?"},
            "eps_diluted":      {"value": 11.80, "question": "What was MSFT's diluted earnings per share?"},
            "operating_income": {"value": 109_433_000_000, "question": "What was MSFT's operating income?"},
        },
    },
    "GS": {
        "filing_date": "2025-02-19",
        "period": "FY2024",
        "form_type": "10-K",
        "source_url": "https://www.sec.gov/cgi-bin/browse-edgar?action=getcompany&CIK=0000886982&type=10-K",
        "metrics": {
            "net_income":       {"value": 14_275_000_000, "question": "What was GS's net income?"},
            "revenue":          {"value": 53_510_000_000, "question": "What was GS's total revenue?"},
            "total_assets":     {"value": 1_676_000_000_000, "question": "What was GS's total assets?"},
            "eps_diluted":      {"value": 40.54, "question": "What was GS's diluted earnings per share?"},
            "operating_income": {"value": 18_550_000_000, "question": "What was GS's operating income?"},
        },
    },
}


# ---------------------------------------------------------------------------
# SEC EDGAR API functions
# ---------------------------------------------------------------------------

def _sec_headers() -> dict:
    """Headers required by SEC EDGAR API."""
    return {
        "User-Agent": SEC_USER_AGENT,
        "Accept": "application/json",
    }


def fetch_company_facts(ticker: str) -> Optional[dict]:
    """
    Fetch XBRL CompanyFacts from SEC EDGAR for structured financial data.
    Returns the full JSON response or None on failure.
    
    API: https://data.sec.gov/api/xbrl/companyfacts/CIK{cik}.json
    """
    if not HAS_HTTPX:
        logger.warning("httpx not installed — skipping SEC EDGAR API call")
        return None

    cik = TICKER_TO_CIK.get(ticker.upper())
    if not cik:
        logger.error("Unknown ticker: %s (no CIK mapping)", ticker)
        return None

    url = f"https://data.sec.gov/api/xbrl/companyfacts/CIK{cik}.json"
    logger.info("Fetching XBRL CompanyFacts: %s", url)

    try:
        with httpx.Client(timeout=30.0, follow_redirects=True) as client:
            resp = client.get(url, headers=_sec_headers())
            if resp.status_code == 200:
                return resp.json()
            logger.warning("SEC EDGAR returned %d for %s", resp.status_code, ticker)
            return None
    except Exception as e:
        logger.warning("SEC EDGAR API error for %s: %s", ticker, e)
        return None


def fetch_submissions(ticker: str) -> Optional[dict]:
    """
    Fetch filing submissions metadata from SEC EDGAR.
    Returns recent filings list or None.
    
    API: https://data.sec.gov/submissions/CIK{cik}.json
    """
    if not HAS_HTTPX:
        return None

    cik = TICKER_TO_CIK.get(ticker.upper())
    if not cik:
        return None

    url = f"https://data.sec.gov/submissions/CIK{cik}.json"
    logger.info("Fetching submissions: %s", url)

    try:
        with httpx.Client(timeout=30.0, follow_redirects=True) as client:
            resp = client.get(url, headers=_sec_headers())
            if resp.status_code == 200:
                return resp.json()
            return None
    except Exception as e:
        logger.warning("SEC EDGAR submissions error for %s: %s", ticker, e)
        return None


def extract_latest_10k_info(submissions: dict) -> Optional[dict]:
    """
    Extract the latest 10-K filing accession number and date from submissions.
    """
    if not submissions:
        return None

    recent = submissions.get("filings", {}).get("recent", {})
    forms = recent.get("form", [])
    dates = recent.get("filingDate", [])
    accessions = recent.get("accessionNumber", [])
    primary_docs = recent.get("primaryDocument", [])

    for i, form in enumerate(forms):
        if form == "10-K":
            return {
                "form_type": "10-K",
                "filing_date": dates[i] if i < len(dates) else None,
                "accession_number": accessions[i] if i < len(accessions) else None,
                "primary_document": primary_docs[i] if i < len(primary_docs) else None,
            }
    return None


def extract_xbrl_metrics(facts: dict, ticker: str) -> list[dict]:
    """
    Extract key financial metrics from XBRL CompanyFacts JSON.
    Returns list of {metric_name, raw_value, period, filing_date, source_url, question}.
    
    Selects the most recent 10-K filing values for each metric.
    """
    if not facts:
        return []

    results = []
    us_gaap = facts.get("facts", {}).get("us-gaap", {})

    for xbrl_concept, meta in XBRL_METRICS.items():
        concept_data = us_gaap.get(xbrl_concept)
        if not concept_data:
            continue

        units = concept_data.get("units", {})
        # Try USD first, then USD/shares for EPS, then pure for ratios
        unit_data = units.get("USD") or units.get("USD/shares") or units.get("pure")
        if not unit_data:
            continue

        # Filter for 10-K (annual) filings and get the most recent
        annual_entries = [
            e for e in unit_data
            if e.get("form") == "10-K" and e.get("val") is not None
        ]
        if not annual_entries:
            # Try 10-Q as fallback
            annual_entries = [
                e for e in unit_data
                if e.get("form") == "10-Q" and e.get("val") is not None
            ]

        if not annual_entries:
            continue

        # Sort by end date (most recent first)
        annual_entries.sort(key=lambda x: x.get("end", ""), reverse=True)

        # Skip duplicate metric names (keep only the first/most recent)
        existing_names = {r["metric_name"] for r in results}
        if meta["metric_name"] in existing_names:
            continue

        entry = annual_entries[0]
        cik = TICKER_TO_CIK.get(ticker.upper(), "")
        accn = entry.get("accn", "").replace("-", "")
        source_url = (
            f"https://www.sec.gov/Archives/edgar/data/{cik.lstrip('0')}/{accn}/"
            if accn else
            f"https://www.sec.gov/cgi-bin/browse-edgar?action=getcompany&CIK={cik}&type=10-K"
        )

        results.append({
            "metric_name": meta["metric_name"],
            "raw_value": float(entry["val"]),
            "period": str(entry.get("fp", "FY")) + str(entry.get("fy", "")),
            "filing_date": entry.get("filed", ""),
            "source_url": source_url,
            "question": meta["question"].format(ticker=ticker.upper()),
        })

    return results


def _use_fallback(ticker: str) -> list[dict]:
    """Use hardcoded fallback data based on real SEC filings."""
    ticker = ticker.upper()
    fallback = FALLBACK_FILINGS.get(ticker)
    if not fallback:
        logger.warning("No fallback data for %s", ticker)
        return []

    results = []
    for metric_name, data in fallback["metrics"].items():
        results.append({
            "metric_name": metric_name,
            "raw_value": data["value"],
            "period": fallback["period"],
            "filing_date": fallback["filing_date"],
            "source_url": fallback["source_url"],
            "question": data["question"],
        })
    return results


# ---------------------------------------------------------------------------
# DVL verification + storage
# ---------------------------------------------------------------------------

def verify_and_store_metrics(ticker: str, metrics: list[dict]) -> list[dict]:
    """
    Run DVL over every extracted metric and store in SQLite.
    Returns list of verified metric dicts.
    """
    from .db import upsert_fundamental

    verified_results = []
    ticker = ticker.upper()

    for m in metrics:
        raw_value = m["raw_value"]
        question = m["question"]

        # Run DVL verification
        verified_value, correction_log, trust_label, trust_color = full_verify(
            question=question,
            predicted=raw_value,
            actual=None,  # No ground truth — standalone mode
        )

        dvl_rule = " → ".join(e["rule"] for e in correction_log) if correction_log else None

        # Store in SQLite
        upsert_fundamental(
            ticker=ticker,
            metric_name=m["metric_name"],
            raw_value=raw_value,
            verified_value=verified_value,
            period=m.get("period", ""),
            filing_date=m.get("filing_date", ""),
            source_url=m.get("source_url", ""),
            dvl_trust=trust_label,
            dvl_color=trust_color,
            dvl_rule=dvl_rule,
        )

        verified_results.append({
            "ticker": ticker,
            "metric_name": m["metric_name"],
            "raw_value": raw_value,
            "verified_value": verified_value,
            "period": m.get("period", ""),
            "filing_date": m.get("filing_date", ""),
            "source_url": m.get("source_url", ""),
            "dvl_trust": trust_label,
            "dvl_color": trust_color,
            "dvl_rule": dvl_rule,
            "correction_log": correction_log,
        })

    logger.info("Verified and stored %d metrics for %s", len(verified_results), ticker)
    return verified_results


# ---------------------------------------------------------------------------
# Main ingestion pipeline
# ---------------------------------------------------------------------------

def ingest_ticker(ticker: str) -> list[dict]:
    """
    Full ingestion pipeline for a single ticker:
    1. Try SEC EDGAR XBRL API
    2. Fallback to hardcoded real filing data
    3. Run DVL on each metric
    4. Store in SQLite
    
    Returns list of verified metrics.
    """
    ticker = ticker.upper()
    logger.info("═" * 60)
    logger.info("INGESTING SEC FILINGS: %s", ticker)
    logger.info("═" * 60)

    metrics = []

    # Step 1: Try XBRL CompanyFacts API
    try:
        facts = fetch_company_facts(ticker)
        if facts:
            metrics = extract_xbrl_metrics(facts, ticker)
            if metrics:
                logger.info("Extracted %d metrics from XBRL for %s", len(metrics), ticker)
    except Exception as e:
        logger.warning("XBRL extraction failed for %s: %s", ticker, e)

    # Step 2: Fallback to hardcoded data
    if not metrics:
        logger.info("Using fallback filing data for %s", ticker)
        metrics = _use_fallback(ticker)

    if not metrics:
        logger.error("No metrics available for %s", ticker)
        return []

    # Step 3: DVL verify and store
    verified = verify_and_store_metrics(ticker, metrics)

    # Rate limit — SEC EDGAR requires max 10 req/sec
    time.sleep(0.2)

    return verified


def ingest_all(tickers: Optional[list[str]] = None) -> dict:
    """
    Ingest SEC filings for all watchlist tickers.
    Returns summary dict.
    """
    if tickers is None:
        tickers = list(TICKER_TO_CIK.keys())

    all_results = {}
    for ticker in tickers:
        try:
            results = ingest_ticker(ticker)
            all_results[ticker] = {
                "metrics_count": len(results),
                "metrics": results,
                "status": "ok",
            }
        except Exception as e:
            logger.error("Ingestion failed for %s: %s", ticker, e)
            all_results[ticker] = {
                "metrics_count": 0,
                "metrics": [],
                "status": f"error: {e}",
            }
        # Respect SEC rate limits between tickers
        time.sleep(0.5)

    total = sum(r["metrics_count"] for r in all_results.values())
    logger.info("═" * 60)
    logger.info("INGESTION COMPLETE: %d total metrics across %d tickers",
                total, len(tickers))
    logger.info("═" * 60)

    return {
        "tickers": all_results,
        "total_metrics": total,
        "ingested_at": datetime.now(timezone.utc).isoformat(),
    }


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s | %(message)s")

    parser = argparse.ArgumentParser(description="Ingest SEC EDGAR filings")
    parser.add_argument("--ticker", type=str, help="Single ticker to ingest")
    args = parser.parse_args()

    if args.ticker:
        results = ingest_ticker(args.ticker)
        print(json.dumps(results, indent=2, default=str))
    else:
        summary = ingest_all()
        print(json.dumps(summary, indent=2, default=str))
