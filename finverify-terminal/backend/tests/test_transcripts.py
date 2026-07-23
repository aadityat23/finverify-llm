"""
Tests for earnings-transcript claim extraction regex pipeline.

Covers all 12 CLAIM_PATTERNS, end-to-end extract_claims against sample
transcripts, build_question_from_claim safety, and build_red_flag_report
math.

Usage: pytest tests/test_transcripts.py   (from backend/ directory)
"""

import pytest

from ingestion.transcripts import (
    CLAIM_PATTERNS,
    SAMPLE_TRANSCRIPTS,
    SCALE_MAP,
    extract_claims,
    build_question_from_claim,
    build_red_flag_report,
)

# RATIO_KEYWORDS mirror app/dvl.py — these are what build_question_from_claim
# must avoid injecting for growth_pct / decline_pct.
RATIO_KEYWORDS = [
    "ratio", "margin", "return", "yield", "growth",
    "change", "increase", "decrease", "percent", "percentage",
    "rate", "loss",
]


# ---------------------------------------------------------------------------
# Pattern helpers
# ---------------------------------------------------------------------------


def _find_claims_by_type(claims, claim_type):
    return [c for c in claims if c["claim_type"] == claim_type]


def _all_sample_claims():
    """Run extract_claims over every sample transcript."""
    all_claims = []
    for text in SAMPLE_TRANSCRIPTS.values():
        all_claims.extend(extract_claims(text))
    return all_claims


# ---------------------------------------------------------------------------
# 1. Each of the 12 CLAIM_PATTERNS has at least one positive test case
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("pattern,claim_type", CLAIM_PATTERNS)
def test_claim_pattern_matches_expected_text(pattern, claim_type):
    """Every pattern matches a representative string (from samples or synthetic)."""
    text_by_type = {
        "currency": "Revenue was $94.9 billion for the quarter",
        "currency_raw": "EPS was $1.64, up from $1.52",
        "percentage": "Gross margin was 46.6%",
        "bps": "Operating margin improved 240 basis points",
        "growth_pct": "Revenue grew 15% year over year",
        "decline_pct": "iPad revenue declined 11% year over year",
        "shares": "We had 10.4 million shares outstanding",
        "eps": "GAAP EPS was $0.89",
        "margin": "Operating margin was 43.1%",
        "revenue": "Total revenue of $25.2 billion grew 2%",
        "ratio": "The CET1 ratio was 15.3%",
        "return_metric": "Return on equity was 12.7%",
    }
    text = text_by_type[claim_type]
    claims = extract_claims(text)
    matches = [c for c in claims if c["claim_type"] == claim_type]
    assert len(matches) >= 1, f"Pattern {claim_type} did not match: {text!r}"


def test_all_claim_types_present_across_sample_transcripts():
    """Across all SAMPLE_TRANSCRIPTS every claim type except 'shares' appears.
    'shares' is covered by the parametrized synthetic test above."""
    all_claims = _all_sample_claims()
    found_types = {c["claim_type"] for c in all_claims}
    expected = {ct for _, ct in CLAIM_PATTERNS}
    # shares has no match in sample transcripts, but is tested separately.
    assert expected - found_types == {"shares"}, f"Missing types: {expected - found_types}"


# ---------------------------------------------------------------------------
# 2. extract_claims end-to-end on AAPL sample transcript
# ---------------------------------------------------------------------------


def test_extract_claims_aapl_minimum_count():
    claims = extract_claims(SAMPLE_TRANSCRIPTS["AAPL"])
    assert len(claims) >= 30


def test_extract_claims_aapl_revenue_94_9_billion():
    claims = extract_claims(SAMPLE_TRANSCRIPTS["AAPL"])
    revenue_claims = [c for c in claims if abs(c["raw_value"] - 94_900_000_000) < 1]
    assert len(revenue_claims) >= 1
    for c in revenue_claims:
        assert c["claim_type"] in ("currency", "revenue")
        assert c.get("scale_label") == "billion"


def test_extract_claims_aapl_240_bps():
    claims = extract_claims(SAMPLE_TRANSCRIPTS["AAPL"])
    bps_claims = [c for c in claims if c.get("bps_original") == 240.0]
    assert len(bps_claims) == 1
    assert bps_claims[0]["claim_type"] == "bps"
    assert bps_claims[0]["raw_value"] == pytest.approx(2.4)


def test_extract_claims_scale_multiplier_applied():
    claims = extract_claims("Revenue was $24.2 billion")
    # currency, revenue, and a spurious currency_raw match all coexist.
    scaled = [c for c in claims if c["raw_value"] == pytest.approx(24_200_000_000.0)]
    assert len(scaled) >= 2
    for c in scaled:
        assert c.get("scale_label") == "billion"


def test_extract_claims_deduplicates_overlapping_patterns():
    # "Revenue was $94.9 billion" matches both currency and revenue, but only
    # one entry per unique (sentence, match) should be kept.
    claims = extract_claims(SAMPLE_TRANSCRIPTS["AAPL"])
    keys = [(c["sentence"], c["match"]) for c in claims]
    assert len(keys) == len(set(keys))


def test_extract_claims_ignores_short_segments():
    # Only long enough sentences are scanned; "$5" alone is skipped.
    claims = extract_claims("Hi. $5.")
    assert len(claims) == 0  # "$5" is 2 chars, skipped


# ---------------------------------------------------------------------------
# 3. build_question_from_claim does not inject RATIO_KEYWORDS for growth/decline/percentage
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("claim_type", ["growth_pct", "decline_pct", "percentage"])
def test_build_question_avoids_ratio_keywords(claim_type):
    claim = {
        "claim_type": claim_type,
        "raw_value": 15.0,
        "sentence": "Revenue grew 15% year over year",
    }
    question = build_question_from_claim(claim)
    q_lower = question.lower()
    for kw in RATIO_KEYWORDS:
        assert kw not in q_lower, f"Question for {claim_type} contains ratio keyword '{kw}': {question}"


def test_build_question_growth_pct_format():
    claim = {"claim_type": "growth_pct", "raw_value": 154.0, "sentence": "Energy storage deployments grew 154%"}
    question = build_question_from_claim(claim)
    assert "stated numerical figure" in question.lower()


def test_build_question_bps_uses_original_value():
    claim = {"claim_type": "bps", "raw_value": 2.4, "bps_original": 240.0, "sentence": "margin improved 240 bps"}
    question = build_question_from_claim(claim)
    assert "240.0 bps" in question


def test_build_question_eps():
    claim = {"claim_type": "eps", "raw_value": 1.64, "sentence": "EPS was $1.64"}
    question = build_question_from_claim(claim)
    assert "earnings per share" in question.lower()


# ---------------------------------------------------------------------------
# 4. build_red_flag_report math
# ---------------------------------------------------------------------------


def test_build_red_flag_report_flag_rate_and_breakdown():
    verified = [
        {"trust_score": "HIGH", "flagged": False},
        {"trust_score": "HIGH", "flagged": False},
        {"trust_score": "MEDIUM", "flagged": True},
        {"trust_score": "LOW", "flagged": True},
    ]
    report = build_red_flag_report(verified, ticker="AAPL")

    assert report["ticker"] == "AAPL"
    assert report["total_claims"] == 4
    assert report["flagged_count"] == 2
    assert report["flag_rate"] == 50.0
    assert report["trust_breakdown"] == {"high": 2, "medium": 1, "low": 1}
    assert len(report["flags"]) == 2
    assert "generated_at" in report


def test_build_red_flag_report_empty_claims():
    report = build_red_flag_report([], ticker="X")
    assert report["total_claims"] == 0
    assert report["flagged_count"] == 0
    assert report["flag_rate"] == 0.0
    assert report["trust_breakdown"] == {"high": 0, "medium": 0, "low": 0}
    assert report["flags"] == []


def test_build_red_flag_report_limits_flags_to_25():
    verified = [{"trust_score": "LOW", "flagged": True} for _ in range(50)]
    report = build_red_flag_report(verified)
    assert report["flagged_count"] == 50
    assert len(report["flags"]) == 25
    assert report["flag_rate"] == 100.0
