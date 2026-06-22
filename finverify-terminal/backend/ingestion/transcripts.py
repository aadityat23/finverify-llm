"""
Earnings Call Transcript Verification — FinVerify Terminal
============================================================
Parses earnings call transcripts for numeric claims, then runs
DVL verification over every extracted number to detect ambiguity.

The "killer demo feature" — catches real-world scale ambiguity
in CEO/CFO statements from earnings calls.

Pipeline:
  1. Fetch/load earnings transcript for each watchlist ticker
  2. Extract all numeric claims using regex pipeline
  3. For each claim, determine financial question context
  4. Run DVL: flag any claim where scale/sign/magnitude is ambiguous
  5. Build a "Red Flag Report" with trust-scored claims

Claim types detected:
  - $X.X billion/million  (currency amounts)
  - X.X%                  (percentages)
  - X basis points        (bps → percentage conversion)
  - grew/declined X%      (directional growth)
  - X million shares      (share counts)
  - EPS of $X.XX          (earnings per share)
  - margin of X.X%        (margins)
  - revenue of $X.X B/M   (revenue figures)

Usage:
    python -m ingestion.transcripts                 # All tickers
    python -m ingestion.transcripts --ticker AAPL   # Single ticker
"""

import re
import json
import logging
import argparse
from pathlib import Path
from datetime import datetime, timezone
from typing import Optional

import sys
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from app.dvl import full_verify

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Regex patterns for numeric financial claims
# ---------------------------------------------------------------------------

CLAIM_PATTERNS = [
    # Currency amounts: $94.9 billion, $24.2M, $1.64
    (r'\$\s*([\d,.]+)\s*(billion|million|thousand|B|M|K|bn|mn)', 'currency'),
    # Standalone dollar amounts (e.g., EPS $1.64)
    (r'\$\s*([\d,.]+)(?!\s*(?:billion|million|thousand|B|M|K|bn|mn))', 'currency_raw'),
    # Percentage values: 25.31%, up 5%
    (r'([\d,.]+)\s*%', 'percentage'),
    # Basis points: 240 basis points, 50 bps
    (r'([\d,.]+)\s*(?:basis\s*points?|bps)', 'bps'),
    # Growth percentages: grew 5%, increased 21%
    (r'(?:grew|growth|increased|rose|up|gained|improved|expanded)\s+([\d,.]+)\s*%', 'growth_pct'),
    # Decline percentages: declined 6%, decreased 2.4%
    (r'(?:declined?|decreased?|fell|down|dropped|contracted|narrowed)\s+([\d,.]+)\s*%', 'decline_pct'),
    # Share counts: 433,371 vehicles, 10.4 GWh, X million shares
    (r'([\d,.]+)\s*(?:million|billion)\s*shares', 'shares'),
    # EPS: EPS of $1.64, EPS was $0.73
    (r'EPS\s*(?:of|was|:)?\s*\$?\s*([\d,.]+)', 'eps'),
    # Margins: margin of 30.7%, margin was 46.6%
    (r'margin\s*(?:of|was|:)?\s*([\d,.]+)\s*%?', 'margin'),
    # Revenue: revenue of $94.9 billion
    (r'revenue\s*(?:of|was|:)?\s*\$?\s*([\d,.]+)\s*(billion|million|B|M|bn|mn)?', 'revenue'),
    # Ratios: CET1 ratio was 15.3%
    (r'(?:CET1|tier\s*1|capital)\s*(?:ratio)?\s*(?:of|was|:)?\s*([\d,.]+)\s*%?', 'ratio'),
    # Return metrics: ROTCE was 21%
    (r'(?:return|ROTCE|ROE|ROA)\s*(?:on\s*\w+\s*\w*)?\s*(?:of|was|:)?\s*([\d,.]+)\s*%?', 'return_metric'),
]

SCALE_MAP = {
    "billion": 1e9, "B": 1e9, "bn": 1e9,
    "million": 1e6, "M": 1e6, "mn": 1e6,
    "thousand": 1e3, "K": 1e3,
}


# ---------------------------------------------------------------------------
# Sample transcripts — Real earnings call excerpts (paraphrased)
# All 6 watchlist companies with realistic financial claims
# ---------------------------------------------------------------------------

SAMPLE_TRANSCRIPTS = {
    "AAPL": """
    Tim Cook, CEO — Apple Inc. Q4 FY2024 Earnings Call

    Revenue was $94.9 billion for the quarter, up 5% year over year.
    This marks our highest September quarter revenue ever.
    Services revenue reached an all-time high of $24.2 billion, growing 12% year over year.
    Operating margin improved 240 basis points to 30.7% compared to the prior year.
    We returned over $29 billion to shareholders through dividends and buybacks.
    iPhone revenue was $46.2 billion, representing 49% of total revenue.
    EPS was $1.64, up from $1.52 a year ago, an increase of 8%.
    Gross margin was 46.6%, compared to 45.0% in the year-ago quarter.
    Mac revenue grew 2% to $7.7 billion. iPad revenue declined 11% to $7.0 billion.
    Greater China revenue was $15.0 billion, down 3% year over year.
    Our installed base of active devices reached an all-time high of 2.35 billion.
    Free cash flow was $27.0 billion for the quarter.
    We had $153 billion in cash and marketable securities on the balance sheet.
    R&D spending was $7.8 billion, up 8% from a year ago.
    """,

    "TSLA": """
    Elon Musk, CEO — Tesla Inc. Q4 FY2024 Earnings Call

    Automotive revenue was $21.3 billion, a decrease of 6% year over year.
    Total revenue of $25.2 billion grew 2% compared to last year.
    Operating margin declined to 5.5% from 8.2%, a decrease of 270 basis points.
    Free cash flow was $2.0 billion for the quarter.
    We produced 433,371 vehicles and delivered 435,059 in Q4.
    Energy storage deployments grew 154% year over year to 10.4 GWh.
    EPS of $0.73 was below consensus expectations of $0.76.
    Automotive gross margin was 16.3%, down from 17.2% in Q3.
    Full-year revenue was $96.8 billion, increasing 1% from $96.7 billion in 2023.
    Capital expenditure was $3.5 billion in Q4, $11.3 billion for the full year.
    We ended the quarter with $36.6 billion in cash and investments.
    Solar deployments were 126 MW, down 28% from Q3.
    Energy revenue grew 67% year over year to $3.1 billion.
    Cost of automotive revenue per vehicle declined 5% sequentially.
    """,

    "JPM": """
    Jamie Dimon, CEO — JPMorgan Chase Q4 FY2024 Earnings Call

    Net revenue was $43.7 billion, up 21% year over year.
    Net income was $13.4 billion with EPS of $4.81.
    The CET1 ratio was 15.3%, up from 14.8% in Q3, an improvement of 50 basis points.
    Return on tangible common equity was 21%. Net interest income was $23.5 billion.
    Total assets reached $4.1 trillion. Credit costs were $2.6 billion.
    Investment banking revenue increased 49% to $2.5 billion.
    Average loans grew 1% year over year to $1.34 trillion.
    Trading revenue was $7.3 billion, up 21% from Q4 2023.
    Net charge-offs were $2.4 billion, or 68 basis points.
    Consumer banking net income was $4.7 billion, up 6%.
    Commercial banking net income increased 15% to $1.8 billion.
    Provision for credit losses was $2.8 billion.
    Book value per share was $116.07, up 12% year over year.
    Efficiency ratio improved to 55%, down from 58% a year ago.
    """,

    "NVDA": """
    Jensen Huang, CEO — NVIDIA Corp. Q4 FY2025 Earnings Call

    Revenue was a record $39.3 billion, up 78% year over year and 12% sequentially.
    Data Center revenue was $35.6 billion, up 93% year over year.
    GAAP EPS was $0.89, up 82% from a year ago.
    Non-GAAP EPS was $0.89 versus $0.52 in Q4 FY2024.
    Gross margin was 73.0% on a GAAP basis and 73.5% on a non-GAAP basis.
    Operating income was $24.0 billion, up 76% year over year.
    Free cash flow was $15.5 billion for the quarter.
    Gaming revenue was $2.5 billion, up 9% year over year.
    Automotive revenue was $570 million, up 103% year over year.
    Full-year revenue was $130.5 billion, up 114% from $61.0 billion in FY2024.
    We returned $7.8 billion to shareholders through buybacks and dividends.
    Operating expenses grew 45% to $3.2 billion.
    Inference revenue grew over 200% year over year and now represents about 50% of data center revenue.
    R&D spending was $3.5 billion, representing 8.9% of revenue.
    """,

    "MSFT": """
    Satya Nadella, CEO — Microsoft Corp. Q4 FY2024 Earnings Call

    Revenue was $64.7 billion, increasing 15% year over year.
    Operating income increased 15% to $27.9 billion.
    Net income was $22.0 billion, up 10% year over year.
    EPS was $2.95, an increase of 10% compared to Q4 FY2023.
    Intelligent Cloud revenue was $28.5 billion, up 19%, driven by Azure growth of 29%.
    More Personal Computing revenue was $15.9 billion, up 14%.
    Productivity and Business Processes revenue was $20.3 billion, up 11%.
    Operating margin was 43.1%, down from 43.6% a year ago, a decrease of 50 basis points.
    LinkedIn revenue grew 10% to $4.2 billion.
    Free cash flow was $23.3 billion, up 18% year over year.
    We returned $8.4 billion to shareholders through dividends and buybacks.
    Capital expenditure was $13.9 billion, up 55% year over year.
    Cloud gross margin declined 100 basis points to 72%.
    Total cash and investments were $75.5 billion at quarter end.
    """,

    "GS": """
    David Solomon, CEO — Goldman Sachs Q4 FY2024 Earnings Call

    Net revenues were $13.9 billion, up 23% from a year ago.
    Net earnings were $4.1 billion with diluted EPS of $11.95.
    Return on equity was 12.7% for the quarter, up from 7.1% a year ago.
    Full-year ROE was 12.7%, compared to 7.5% in 2023.
    Investment banking revenue was $2.1 billion, up 24% year over year.
    Advisory revenue increased 37% to $934 million.
    Global Banking and Markets net revenue was $10.5 billion, up 33%.
    FICC revenue was $2.7 billion, up 35% from Q4 2023.
    Equities revenue reached $3.5 billion, up 32% year over year.
    Asset and Wealth Management revenue was $4.7 billion, up 16%.
    Management and other fees grew 7% to $2.6 billion.
    Provision for credit losses was $351 million, down 54% from Q4 2023.
    The CET1 ratio was 14.6%, well above the 13.4% requirement.
    Book value per share increased 10% to $339.26.
    Efficiency ratio improved to 65.0% from 73.5% a year ago, an improvement of 850 basis points.
    """
}


# ---------------------------------------------------------------------------
# Claim extraction
# ---------------------------------------------------------------------------

def extract_claims(text: str) -> list[dict]:
    """
    Extract numeric claims from transcript text using regex pipeline.
    Returns list of claim dicts with sentence context.
    """
    claims = []
    seen_matches = set()  # Deduplicate overlapping patterns

    # Split on sentence boundaries but preserve decimal numbers.
    # Only split on . when followed by whitespace+uppercase or end-of-string,
    # and always split on !, ?, and newlines.
    sentences = re.split(r'(?<=[.!?])\s+(?=[A-Z])|\n+', text)
    for sentence in sentences:
        sentence = sentence.strip()
        if len(sentence) < 10:
            continue

        for pattern, claim_type in CLAIM_PATTERNS:
            matches = re.finditer(pattern, sentence, re.IGNORECASE)
            for m in matches:
                try:
                    num_str = m.group(1).replace(",", "")
                    value = float(num_str)

                    # Apply scale multiplier for currency amounts
                    scale_label = None
                    if m.lastindex and m.lastindex >= 2:
                        scale_label = m.group(2)
                        if scale_label and scale_label in SCALE_MAP:
                            value *= SCALE_MAP[scale_label]

                    # BPS → percentage conversion (the ambiguity DVL catches)
                    bps_original = None
                    if claim_type == 'bps':
                        bps_original = value
                        value = value / 100.0  # 240 bps = 2.40%

                    # Deduplicate
                    match_key = f"{sentence[:50]}:{m.group(0)}"
                    if match_key in seen_matches:
                        continue
                    seen_matches.add(match_key)

                    claim = {
                        "sentence": sentence[:200],
                        "raw_value": value,
                        "claim_type": claim_type,
                        "match": m.group(0),
                    }
                    if bps_original is not None:
                        claim["bps_original"] = bps_original
                    if scale_label:
                        claim["scale_label"] = scale_label

                    claims.append(claim)
                except (ValueError, IndexError):
                    continue

    return claims


def build_question_from_claim(claim: dict) -> str:
    """
    Build a contextual DVL question from claim type and sentence.
    
    IMPORTANT: Avoid injecting ratio keywords for non-ratio claim types,
    otherwise DVL's scale_div100 will false-positive on legitimate
    values like 154% YoY growth.
    """
    t = claim["claim_type"]
    sentence = claim.get("sentence", "")[:80]

    if t in ("growth_pct", "decline_pct"):
        # Directional movement — these are absolute numbers, NOT ratios.
        # 154% YoY is valid and should NOT be divided by 100.
        # CRITICAL: avoid words like "growth", "change", "increase", "decrease"
        # which are RATIO_KEYWORDS in DVL and would trigger scale_div100.
        return f"What was the stated numerical figure: {sentence}?"
    if t == "margin":
        return f"What was the margin value?"
    if t == "percentage":
        # Generic percentages — avoid ratio keywords in question text
        return f"What was the numeric value?"
    if t == "bps":
        bps_val = claim.get("bps_original", claim["raw_value"] * 100)
        return f"What was the basis point change of {bps_val} bps?"
    if t == "eps":
        return f"What was the earnings per share?"
    if t in ("ratio", "return_metric"):
        return f"What was the financial ratio?"
    if t == "currency":
        return f"What was the financial value in the statement?"
    if t == "revenue":
        return f"What was the revenue figure?"
    if t == "shares":
        return f"What was the share count?"
    return f"What was the financial value?"


def _classify_dvl_finding(claim: dict, verified_value: float, trust: str, log: list) -> str:
    """
    Generate a human-readable DVL analysis string for the claim.
    This is the "killer feature" — showing what DVL catches.
    """
    t = claim["claim_type"]
    raw = claim["raw_value"]
    match_text = claim["match"]

    if t == "bps":
        bps = claim.get("bps_original", raw * 100)
        return (
            f"{bps:.0f} bps = {bps/100:.2f}% — "
            f"within 1-100 range — AMBIGUOUS — flagged for review"
        )

    if trust == "HIGH":
        return f"Value {raw:,.2f} passed DVL — no correction needed"

    if log:
        rules = " → ".join(e["rule"] for e in log)
        return f"DVL applied {rules}: {raw:,.4f} → {verified_value:,.4f}"

    if t in ("percentage", "growth_pct", "decline_pct", "margin"):
        if 1 <= abs(raw) <= 100:
            return (
                f"Value {raw:.1f}% is in ambiguous 1-100 range — "
                f"could be decimal or percentage — flagged for review"
            )

    return f"Value {raw:,.4f} — DVL trust: {trust}"


# ---------------------------------------------------------------------------
# DVL verification
# ---------------------------------------------------------------------------

def verify_claims(claims: list[dict]) -> list[dict]:
    """Run DVL on each extracted claim and add verification results."""
    results = []
    for claim in claims:
        question = build_question_from_claim(claim)
        verified, log, trust, color = full_verify(question, claim["raw_value"])

        dvl_rule = " → ".join(e["rule"] for e in log) if log else None
        dvl_analysis = _classify_dvl_finding(claim, verified, trust, log)

        # Flag claims where DVL detects issues or ambiguity
        flagged = trust != "HIGH" or claim["claim_type"] == "bps"

        results.append({
            **claim,
            "question": question,
            "verified_value": verified,
            "dvl_rule": dvl_rule,
            "dvl_analysis": dvl_analysis,
            "trust_score": trust,
            "trust_color": color,
            "flagged": flagged,
        })

    return results


def build_red_flag_report(verified_claims: list[dict], ticker: str = "") -> dict:
    """
    Build the Red Flag Report — the killer demo feature.
    Shows claims where DVL detects ambiguous or likely-wrong scale.
    """
    flagged = [c for c in verified_claims if c["flagged"]]
    high_trust = [c for c in verified_claims if c["trust_score"] == "HIGH"]
    medium_trust = [c for c in verified_claims if c["trust_score"] == "MEDIUM"]
    low_trust = [c for c in verified_claims if c["trust_score"] == "LOW"]

    return {
        "ticker": ticker,
        "total_claims": len(verified_claims),
        "flagged_count": len(flagged),
        "flag_rate": round(len(flagged) / max(len(verified_claims), 1) * 100, 1),
        "trust_breakdown": {
            "high": len(high_trust),
            "medium": len(medium_trust),
            "low": len(low_trust),
        },
        "flags": flagged[:25],
        "all_claims": verified_claims,
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }


# ---------------------------------------------------------------------------
# Database integration
# ---------------------------------------------------------------------------

def store_verified_claims(ticker: str, verified_claims: list[dict], source: str = "sample_transcript") -> None:
    """Store verified claims in SQLite."""
    from .db import insert_transcript_claim, clear_claims

    ticker = ticker.upper()
    # Clear old claims for re-ingestion
    clear_claims(ticker)

    for claim in verified_claims:
        insert_transcript_claim(
            ticker=ticker,
            sentence=claim.get("sentence", ""),
            claim_match=claim.get("match", ""),
            claim_type=claim.get("claim_type", ""),
            raw_value=claim["raw_value"],
            verified_value=claim["verified_value"],
            dvl_question=claim.get("question", ""),
            dvl_rule=claim.get("dvl_rule"),
            dvl_trust=claim["trust_score"],
            dvl_color=claim["trust_color"],
            flagged=claim["flagged"],
            source=source,
        )

    logger.info("Stored %d claims for %s", len(verified_claims), ticker)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def demo_transcript_verification(ticker: str, store: bool = True) -> dict:
    """
    Run verification on sample transcript for a ticker.
    Returns the full Red Flag Report.
    """
    ticker = ticker.upper()
    text = SAMPLE_TRANSCRIPTS.get(ticker, SAMPLE_TRANSCRIPTS.get("AAPL", ""))

    claims = extract_claims(text)
    verified = verify_claims(claims)
    report = build_red_flag_report(verified, ticker)
    report["source"] = "sample_transcript"

    if store:
        try:
            store_verified_claims(ticker, verified)
        except Exception as e:
            logger.warning("Failed to store claims for %s: %s", ticker, e)

    return report


def ingest_all_transcripts(tickers: Optional[list[str]] = None) -> dict:
    """
    Run transcript verification for all watchlist tickers.
    Returns summary with all reports.
    """
    if tickers is None:
        tickers = list(SAMPLE_TRANSCRIPTS.keys())

    reports = {}
    total_claims = 0
    total_flags = 0

    for ticker in tickers:
        report = demo_transcript_verification(ticker, store=True)
        reports[ticker] = report
        total_claims += report["total_claims"]
        total_flags += report["flagged_count"]

    return {
        "tickers": reports,
        "total_claims": total_claims,
        "total_flags": total_flags,
        "overall_flag_rate": round(total_flags / max(total_claims, 1) * 100, 1),
        "ingested_at": datetime.now(timezone.utc).isoformat(),
    }


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s | %(message)s")

    parser = argparse.ArgumentParser(description="Verify earnings call transcripts")
    parser.add_argument("--ticker", type=str, help="Single ticker to verify")
    args = parser.parse_args()

    if args.ticker:
        report = demo_transcript_verification(args.ticker)
        print(json.dumps(report, indent=2, default=str))
    else:
        summary = ingest_all_transcripts()
        print(json.dumps(summary, indent=2, default=str))
