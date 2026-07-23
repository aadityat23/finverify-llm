"""
Tests for the Financial Constraint Graph (FCG) constraint engine.

Covers all 8 hard constraints and 5 soft constraints with passing and
violating cases, the skipped behavior when required keys are missing,
and the overall trust classification logic (CONSISTENT / INCONSISTENT /
PARTIAL).

Usage: pytest tests/test_constraint_engine.py   (from backend/ directory)
"""

import pytest

from fcg.constraint_engine import FinancialConstraintGraph, ConstraintResult


@pytest.fixture
def fcg():
    return FinancialConstraintGraph()


# ---------------------------------------------------------------------------
# Hard constraints — passing cases
# ---------------------------------------------------------------------------


def test_fcg001_gross_profit_identity_pass(fcg):
    result = fcg.verify({"revenue": 100, "cogs": 40, "gross_profit": 60})
    assert "FCG-001" in result.passed
    assert result.trust == "CONSISTENT"


def test_fcg002_operating_income_identity_pass(fcg):
    result = fcg.verify({"gross_profit": 60, "operating_expenses": 20, "operating_income": 40})
    assert "FCG-002" in result.passed
    assert result.trust == "CONSISTENT"


def test_fcg003_net_income_identity_pass(fcg):
    result = fcg.verify({
        "operating_income": 40, "interest_expense": 5, "tax_expense": 7, "net_income": 28,
    })
    assert "FCG-003" in result.passed
    assert result.trust == "CONSISTENT"


def test_fcg004_balance_sheet_equation_pass(fcg):
    result = fcg.verify({"total_assets": 500, "total_liabilities": 300, "total_equity": 200})
    assert "FCG-004" in result.passed
    assert result.trust == "CONSISTENT"


def test_fcg005_eps_identity_pass(fcg):
    result = fcg.verify({"eps_diluted": 2.0, "net_income": 100, "diluted_shares": 50})
    assert "FCG-005" in result.passed
    assert result.trust == "CONSISTENT"


def test_fcg006_gross_margin_bounds_pass(fcg):
    result = fcg.verify({"gross_margin": 0.6})
    assert "FCG-006" in result.passed
    assert result.trust == "CONSISTENT"


def test_fcg007_gross_margin_consistency_pass(fcg):
    result = fcg.verify({"gross_margin": 0.6, "gross_profit": 60, "revenue": 100})
    assert "FCG-007" in result.passed
    assert result.trust == "CONSISTENT"


def test_fcg008_cash_flow_identity_pass(fcg):
    result = fcg.verify({
        "operating_cash_flow": 50, "investing_cash_flow": -20,
        "financing_cash_flow": 10, "net_cash_flow": 40,
    })
    assert "FCG-008" in result.passed
    assert result.trust == "CONSISTENT"


# ---------------------------------------------------------------------------
# Hard constraints — violating cases
# ---------------------------------------------------------------------------


def test_fcg001_gross_profit_identity_violation(fcg):
    result = fcg.verify({"revenue": 100, "cogs": 40, "gross_profit": 50})
    v = next(x for x in result.violations if x.constraint_id == "FCG-001")
    assert v.severity == "HARD"
    assert result.trust == "INCONSISTENT"


def test_fcg002_operating_income_identity_violation(fcg):
    result = fcg.verify({"gross_profit": 60, "operating_expenses": 20, "operating_income": 30})
    v = next(x for x in result.violations if x.constraint_id == "FCG-002")
    assert v.severity == "HARD"
    assert result.trust == "INCONSISTENT"


def test_fcg003_net_income_identity_violation(fcg):
    result = fcg.verify({
        "operating_income": 40, "interest_expense": 5, "tax_expense": 7, "net_income": 20,
    })
    v = next(x for x in result.violations if x.constraint_id == "FCG-003")
    assert v.severity == "HARD"
    assert result.trust == "INCONSISTENT"


def test_fcg004_balance_sheet_equation_violation(fcg):
    result = fcg.verify({"total_assets": 500, "total_liabilities": 300, "total_equity": 100})
    v = next(x for x in result.violations if x.constraint_id == "FCG-004")
    assert v.severity == "HARD"
    assert result.trust == "INCONSISTENT"


def test_fcg005_eps_identity_violation(fcg):
    result = fcg.verify({"eps_diluted": 5.0, "net_income": 100, "diluted_shares": 50})
    v = next(x for x in result.violations if x.constraint_id == "FCG-005")
    assert v.severity == "HARD"
    assert result.trust == "INCONSISTENT"


def test_fcg006_gross_margin_bounds_violation(fcg):
    result = fcg.verify({"gross_margin": 1.5})
    v = next(x for x in result.violations if x.constraint_id == "FCG-006")
    assert v.severity == "HARD"
    assert result.trust == "INCONSISTENT"


def test_fcg007_gross_margin_consistency_violation(fcg):
    result = fcg.verify({"gross_margin": 0.9, "gross_profit": 60, "revenue": 100})
    v = next(x for x in result.violations if x.constraint_id == "FCG-007")
    assert v.severity == "HARD"
    assert result.trust == "INCONSISTENT"


def test_fcg008_cash_flow_identity_violation(fcg):
    result = fcg.verify({
        "operating_cash_flow": 50, "investing_cash_flow": -20,
        "financing_cash_flow": 10, "net_cash_flow": 100,
    })
    v = next(x for x in result.violations if x.constraint_id == "FCG-008")
    assert v.severity == "HARD"
    assert result.trust == "INCONSISTENT"


# ---------------------------------------------------------------------------
# Soft constraints — passing cases
# ---------------------------------------------------------------------------


def test_fcg_s001_revenue_non_negative_pass(fcg):
    result = fcg.verify({"revenue": 100})
    assert "FCG-S001" in result.passed


def test_fcg_s002_revenue_growth_bounds_pass(fcg):
    result = fcg.verify({"revenue_growth": 0.15})
    assert "FCG-S002" in result.passed


def test_fcg_s003_pe_ratio_plausibility_pass(fcg):
    result = fcg.verify({"pe_ratio": 25, "net_income": 100})
    assert "FCG-S003" in result.passed


def test_fcg_s003_pe_ratio_skipped_when_loss(fcg):
    # net_income <= 0 means the check short-circuits to pass (no PE expectation)
    result = fcg.verify({"pe_ratio": 0, "net_income": -50})
    assert "FCG-S003" in result.passed


def test_fcg_s004_debt_to_equity_pass(fcg):
    result = fcg.verify({"total_liabilities": 300, "total_equity": 200})
    assert "FCG-S004" in result.passed


def test_fcg_s005_net_margin_bounds_pass(fcg):
    result = fcg.verify({"net_margin": 0.2})
    assert "FCG-S005" in result.passed


# ---------------------------------------------------------------------------
# Soft constraints — violating cases
# ---------------------------------------------------------------------------


def test_fcg_s001_revenue_negative_violation(fcg):
    result = fcg.verify({"revenue": -10})
    v = next(x for x in result.violations if x.constraint_id == "FCG-S001")
    assert v.severity == "SOFT"
    assert result.trust == "PARTIAL"


def test_fcg_s002_revenue_growth_out_of_bounds_violation(fcg):
    result = fcg.verify({"revenue_growth": 10.0})
    v = next(x for x in result.violations if x.constraint_id == "FCG-S002")
    assert v.severity == "SOFT"
    assert result.trust == "PARTIAL"


def test_fcg_s003_pe_ratio_out_of_range_violation(fcg):
    result = fcg.verify({"pe_ratio": 1000, "net_income": 100})
    v = next(x for x in result.violations if x.constraint_id == "FCG-S003")
    assert v.severity == "SOFT"
    assert result.trust == "PARTIAL"


def test_fcg_s004_debt_to_equity_violation(fcg):
    result = fcg.verify({"total_liabilities": 5000, "total_equity": 100})
    v = next(x for x in result.violations if x.constraint_id == "FCG-S004")
    assert v.severity == "SOFT"
    assert result.trust == "PARTIAL"


def test_fcg_s005_net_margin_out_of_bounds_violation(fcg):
    result = fcg.verify({"net_margin": 2.5})
    v = next(x for x in result.violations if x.constraint_id == "FCG-S005")
    assert v.severity == "SOFT"
    assert result.trust == "PARTIAL"


# ---------------------------------------------------------------------------
# Skipped behavior (missing required keys)
# ---------------------------------------------------------------------------


def test_constraint_skipped_when_required_key_missing(fcg):
    # FCG-001 requires revenue, cogs, gross_profit — only provide revenue.
    result = fcg.verify({"revenue": 100})
    assert "FCG-001" in result.skipped
    assert "FCG-001" not in result.passed
    assert "FCG-001" not in [v.constraint_id for v in result.violations]


def test_constraint_skipped_when_value_is_none(fcg):
    result = fcg.verify({"revenue": 100, "cogs": None, "gross_profit": 60})
    assert "FCG-001" in result.skipped


def test_all_constraints_skipped_on_empty_input(fcg):
    result = fcg.verify({})
    assert len(result.passed) == 0
    assert len(result.violations) == 0
    assert len(result.skipped) == len(fcg.HARD_CONSTRAINTS) + len(fcg.SOFT_CONSTRAINTS)
    assert result.trust == "CONSISTENT"


# ---------------------------------------------------------------------------
# Trust classification
# ---------------------------------------------------------------------------


def test_trust_consistent_no_violations(fcg):
    result = fcg.verify({"revenue": 100, "cogs": 40, "gross_profit": 60})
    assert result.trust == "CONSISTENT"


def test_trust_inconsistent_when_hard_violation(fcg):
    result = fcg.verify({"revenue": 100, "cogs": 40, "gross_profit": 50})
    assert result.trust == "INCONSISTENT"


def test_trust_partial_when_only_soft_violations(fcg):
    result = fcg.verify({"revenue": -10})
    assert result.trust == "PARTIAL"


def test_trust_inconsistent_when_both_hard_and_soft_violations(fcg):
    result = fcg.verify({"revenue": -10, "cogs": 40, "gross_profit": 50})
    assert result.trust == "INCONSISTENT"


def test_total_checked_excludes_skipped(fcg):
    result = fcg.verify({"revenue": 100, "cogs": 40, "gross_profit": 60})
    assert result.total_checked == len(result.passed) + len(result.violations)
    assert result.total_checked > 0


# ---------------------------------------------------------------------------
# to_dict serialization
# ---------------------------------------------------------------------------


def test_to_dict_consistent(fcg):
    result = fcg.verify({"revenue": 100, "cogs": 40, "gross_profit": 60})
    d = fcg.to_dict(result)
    assert d["trust"] == "CONSISTENT"
    assert d["violations"] == []
    assert "FCG-001" in d["passed"]


def test_to_dict_with_violation(fcg):
    result = fcg.verify({"revenue": 100, "cogs": 40, "gross_profit": 50})
    d = fcg.to_dict(result)
    assert d["trust"] == "INCONSISTENT"
    assert len(d["violations"]) >= 1
    v = d["violations"][0]
    assert "id" in v and "name" in v and "severity" in v
