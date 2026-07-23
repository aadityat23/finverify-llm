"""
Tests for the FCG metric-name normalizer.

Covers the exact-match reverse lookup path (canonical names + aliases) and
the fuzzy-match fallback boundary behavior around the 0.82 threshold.

Usage: pytest tests/test_normalizer.py   (from backend/ directory)
"""

import pytest

from fcg.normalizer import (
    METRIC_ALIASES,
    normalize_metric_name,
    normalize_values_dict,
    get_all_canonical_names,
    get_aliases_for,
)


# ---------------------------------------------------------------------------
# Exact-match reverse lookup
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("canonical", list(METRIC_ALIASES.keys()))
def test_exact_match_canonical_name(canonical):
    """Every canonical name maps to itself via the exact-match path."""
    assert normalize_metric_name(canonical) == canonical


@pytest.mark.parametrize(
    "canonical,alias",
    [
        ("revenue", "net revenue"),
        ("revenue", "total sales"),
        ("revenue", "top line"),
        ("cogs", "cost of goods sold"),
        ("cogs", "cost of revenue"),
        ("gross_profit", "gross profit"),
        ("operating_expenses", "sg&a"),
        ("operating_expenses", "opex"),
        ("operating_income", "ebit"),
        ("net_income", "bottom line"),
        ("total_equity", "shareholders equity"),
        ("eps_diluted", "diluted eps"),
        ("pe_ratio", "p/e ratio"),
    ],
)
def test_exact_match_aliases(canonical, alias):
    """Registered aliases resolve to their canonical metric via exact match."""
    assert normalize_metric_name(alias) == canonical


def test_exact_match_is_case_insensitive():
    assert normalize_metric_name("Net Revenue") == "revenue"
    assert normalize_metric_name("TOTAL SALES") == "revenue"
    assert normalize_metric_name("Ebit") == "operating_income"


def test_exact_match_normalizes_separators():
    """Hyphens and underscores are treated as spaces before matching."""
    assert normalize_metric_name("net-revenue") == "revenue"
    assert normalize_metric_name("total_sales") == "revenue"
    assert normalize_metric_name("gross-profit") == "gross_profit"


def test_exact_match_strips_whitespace():
    assert normalize_metric_name("  net revenue  ") == "revenue"


# ---------------------------------------------------------------------------
# Fuzzy-match boundary behavior (threshold = 0.82)
# ---------------------------------------------------------------------------


def test_fuzzy_match_partial_string_above_threshold():
    """A truncated string close to a known alias should still fuzzy-match."""
    # "net revene" vs "net revenue" — truncated, similarity above 0.82.
    assert normalize_metric_name("net revene") == "revenue"


def test_fuzzy_match_typo_above_threshold():
    """A small typo on a known alias should fuzzy-match."""
    # "gross profet" vs "gross profit" — one char diff, well above 0.82.
    assert normalize_metric_name("gross profet") == "gross_profit"


def test_fuzzy_match_below_threshold_returns_none():
    """A string too dissimilar from every alias returns None."""
    # "banana smoothie" has no close match in the alias table.
    assert normalize_metric_name("banana smoothie") is None


def test_fuzzy_match_garbage_returns_none():
    assert normalize_metric_name("xyzzy frobnicate") is None


def test_fuzzy_match_empty_string_returns_none():
    assert normalize_metric_name("") is None


# ---------------------------------------------------------------------------
# normalize_values_dict
# ---------------------------------------------------------------------------


def test_normalize_values_dict_maps_known_names():
    raw = {"net revenue": 100, "cost of goods sold": 40, "banana": 5}
    result = normalize_values_dict(raw)
    assert result == {"revenue": 100, "cogs": 40}


def test_normalize_values_dict_last_wins_on_duplicate_canonical():
    raw = {"net revenue": 100, "total sales": 200}
    result = normalize_values_dict(raw)
    # Both map to "revenue"; last one wins.
    assert result == {"revenue": 200}


def test_normalize_values_dict_empty_input():
    assert normalize_values_dict({}) == {}


def test_normalize_values_dict_all_unmapped():
    assert normalize_values_dict({"banana": 1, "apple": 2}) == {}


# ---------------------------------------------------------------------------
# Helper functions
# ---------------------------------------------------------------------------


def test_get_all_canonical_names_sorted_and_complete():
    names = get_all_canonical_names()
    assert names == sorted(names)
    assert set(names) == set(METRIC_ALIASES.keys())


def test_get_aliases_for_known_canonical():
    aliases = get_aliases_for("revenue")
    assert "net revenue" in aliases
    assert "total sales" in aliases


def test_get_aliases_for_unknown_canonical_returns_empty():
    assert get_aliases_for("nonexistent_metric") == []
