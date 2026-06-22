"""
FCG Metric Name Normalizer — Session 1B
=========================================
LLMs output "net revenues", "total sales", "top-line" — all meaning "revenue".
This module normalizes raw metric names to canonical keys before FCG runs.

Pipeline: LLM Output → DVL (single-number) → **Normalizer** → FCG (relationships)
"""

from difflib import SequenceMatcher
from typing import Optional
import logging

logger = logging.getLogger(__name__)


# ═══════════════════════════════════════════════════════════════════
# Canonical Aliases
# ═══════════════════════════════════════════════════════════════════

METRIC_ALIASES: dict[str, list[str]] = {
    "revenue": [
        "net revenue", "total revenue", "net revenues", "total net revenues",
        "total sales", "net sales", "consolidated revenues", "net operating revenues",
        "total net sales", "top line", "sales revenue", "gross revenue",
    ],
    "cogs": [
        "cost of goods sold", "cost of revenues", "cost of sales",
        "cost of products sold", "cost of revenue",
    ],
    "gross_profit": [
        "gross profit", "gross income", "gross margin dollars",
    ],
    "operating_expenses": [
        "operating expenses", "total operating expenses", "opex",
        "selling general and administrative", "sg&a",
        "sga", "selling general administrative",
    ],
    "operating_income": [
        "operating income", "income from operations", "operating profit",
        "ebit", "earnings before interest and taxes",
    ],
    "interest_expense": [
        "interest expense", "interest and debt expense",
        "net interest expense", "finance costs",
    ],
    "tax_expense": [
        "tax expense", "income tax expense", "provision for income taxes",
        "income tax provision", "tax provision",
    ],
    "net_income": [
        "net income", "net earnings", "net profit", "net income attributable",
        "net income loss", "consolidated net income", "bottom line",
    ],
    "total_assets": [
        "total assets", "consolidated total assets",
    ],
    "total_liabilities": [
        "total liabilities", "total debt and liabilities",
    ],
    "total_equity": [
        "total equity", "shareholders equity", "stockholders equity",
        "total stockholders equity", "total shareholders equity",
        "shareholder equity", "stockholder equity",
    ],
    "eps_diluted": [
        "diluted eps", "diluted earnings per share", "eps diluted",
        "earnings per diluted share", "eps",
    ],
    "diluted_shares": [
        "diluted shares", "diluted weighted average shares",
        "diluted shares outstanding", "weighted average diluted shares",
        "shares outstanding diluted",
    ],
    "gross_margin": [
        "gross margin", "gross profit margin", "gross margin percentage",
        "gross margin %", "gross margin ratio",
    ],
    "net_margin": [
        "net margin", "net profit margin", "net income margin",
        "net margin percentage", "net margin %",
    ],
    "pe_ratio": [
        "pe ratio", "p/e ratio", "price to earnings", "price earnings ratio",
        "p/e", "trailing pe", "pe",
    ],
    "revenue_growth": [
        "revenue growth", "revenue growth rate", "yoy revenue growth",
        "year over year revenue growth", "revenue increase",
    ],
    "operating_cash_flow": [
        "operating cash flow", "cash from operations",
        "net cash from operating activities", "cash flow from operations",
    ],
    "investing_cash_flow": [
        "investing cash flow", "cash from investing",
        "net cash from investing activities", "cash used in investing",
    ],
    "financing_cash_flow": [
        "financing cash flow", "cash from financing",
        "net cash from financing activities", "cash used in financing",
    ],
    "net_cash_flow": [
        "net cash flow", "net change in cash", "change in cash",
        "net increase in cash", "net decrease in cash",
    ],
}

# Build reverse lookup for O(1) exact matching
_REVERSE_LOOKUP: dict[str, str] = {}
for _canonical, _aliases in METRIC_ALIASES.items():
    _REVERSE_LOOKUP[_canonical] = _canonical
    for _alias in _aliases:
        _REVERSE_LOOKUP[_alias] = _canonical


# ═══════════════════════════════════════════════════════════════════
# Normalization Functions
# ═══════════════════════════════════════════════════════════════════

def _clean(raw_name: str) -> str:
    """Clean raw metric name for matching."""
    return (
        raw_name.lower()
        .strip()
        .replace("-", " ")
        .replace("_", " ")
        .replace("  ", " ")
    )


def normalize_metric_name(raw_name: str) -> Optional[str]:
    """
    Normalize a raw metric name to its canonical form.

    Returns canonical name or None if no match found.

    Matching strategy:
    1. Exact match against canonical names and aliases (O(1) via reverse lookup)
    2. Fuzzy match using SequenceMatcher (threshold: 0.82)
    """
    clean = _clean(raw_name)

    # 1. Exact match (fast path)
    if clean in _REVERSE_LOOKUP:
        return _REVERSE_LOOKUP[clean]

    # 2. Fuzzy fallback
    best_match: Optional[str] = None
    best_score: float = 0.0

    for canonical, aliases in METRIC_ALIASES.items():
        for alias in [canonical] + aliases:
            score = SequenceMatcher(None, clean, alias).ratio()
            if score > best_score:
                best_score = score
                best_match = canonical

    if best_match and best_score > 0.82:
        logger.debug("Fuzzy matched '%s' → '%s' (score=%.3f)", raw_name, best_match, best_score)
        return best_match

    logger.debug("No match for metric name: '%s' (best score=%.3f)", raw_name, best_score)
    return None


def normalize_values_dict(raw_dict: dict[str, float]) -> dict[str, float]:
    """
    Takes {raw_metric_name: value} and returns {canonical_name: value}.

    Skips entries that can't be normalized.
    If multiple raw names map to the same canonical, the last one wins.
    """
    result: dict[str, float] = {}
    unmapped: list[str] = []

    for raw_name, value in raw_dict.items():
        canonical = normalize_metric_name(raw_name)
        if canonical:
            result[canonical] = value
        else:
            unmapped.append(raw_name)

    if unmapped:
        logger.info(
            "Normalizer: %d/%d metrics mapped, %d unmapped: %s",
            len(result), len(raw_dict), len(unmapped), unmapped
        )

    return result


def get_all_canonical_names() -> list[str]:
    """Return all supported canonical metric names."""
    return sorted(METRIC_ALIASES.keys())


def get_aliases_for(canonical: str) -> list[str]:
    """Return all aliases for a canonical metric name."""
    return METRIC_ALIASES.get(canonical, [])
