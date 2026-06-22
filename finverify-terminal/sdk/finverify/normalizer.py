"""
finverify.normalizer — Metric Name Normalizer (SDK-embedded)
=============================================================
Standalone copy of the FCG normalizer for use in the SDK.
Maps raw LLM metric names to canonical keys.
"""

from difflib import SequenceMatcher
from typing import Optional


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
    ],
    "gross_margin": [
        "gross margin", "gross profit margin", "gross margin percentage",
        "gross margin %", "gross margin ratio",
    ],
    "net_margin": [
        "net margin", "net profit margin", "net income margin",
    ],
    "pe_ratio": [
        "pe ratio", "p/e ratio", "price to earnings", "price earnings ratio",
        "p/e", "trailing pe", "pe",
    ],
    "revenue_growth": [
        "revenue growth", "revenue growth rate", "yoy revenue growth",
        "year over year revenue growth",
    ],
}

# Build reverse lookup for O(1) exact matching
_REVERSE_LOOKUP: dict[str, str] = {}
for _canonical, _aliases in METRIC_ALIASES.items():
    _REVERSE_LOOKUP[_canonical] = _canonical
    for _alias in _aliases:
        _REVERSE_LOOKUP[_alias] = _canonical


def normalize_metric_name(raw_name: str) -> Optional[str]:
    """Normalize a raw metric name to its canonical form."""
    clean = raw_name.lower().strip().replace("-", " ").replace("_", " ").replace("  ", " ")

    # Exact match
    if clean in _REVERSE_LOOKUP:
        return _REVERSE_LOOKUP[clean]

    # Fuzzy fallback
    best_match: Optional[str] = None
    best_score: float = 0.0
    for canonical, aliases in METRIC_ALIASES.items():
        for alias in [canonical] + aliases:
            score = SequenceMatcher(None, clean, alias).ratio()
            if score > best_score:
                best_score = score
                best_match = canonical

    return best_match if best_match and best_score > 0.82 else None
