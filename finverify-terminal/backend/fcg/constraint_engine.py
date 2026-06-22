"""
Financial Constraint Graph (FCG) — Constraint Engine
=====================================================
Session 1A: Multi-number relationship verification.

The DVL verifies individual numbers (scale/sign/magnitude).
The FCG extends DVL to verify *relationships* between numbers —
accounting identities, ratio consistency, and sanity bounds.

Pipeline:  LLM Output → DVL (single-number) → FCG (relationships) → Trust Score

Hard constraints = accounting identities (must hold exactly, ≤1-2% tolerance)
Soft constraints = ratio bounds / sanity checks (flagged as warnings)
"""

from dataclasses import dataclass, field
from typing import Optional
import logging

logger = logging.getLogger(__name__)


# ═══════════════════════════════════════════════════════════════════
# Data Classes
# ═══════════════════════════════════════════════════════════════════

@dataclass
class ConstraintViolation:
    constraint_id: str
    constraint_name: str
    expected_relationship: str   # human-readable: "Revenue - COGS = Gross Profit"
    lhs_value: float             # what the relationship evaluates to
    rhs_value: float             # what it should equal
    delta_pct: float             # relative error as percentage
    severity: str                # "HARD" (accounting identity) | "SOFT" (ratio bound)


@dataclass
class ConstraintResult:
    passed: list[str] = field(default_factory=list)       # constraint IDs that passed
    violations: list[ConstraintViolation] = field(default_factory=list)
    skipped: list[str] = field(default_factory=list)      # constraints skipped (missing data)
    trust: str = "CONSISTENT"    # "CONSISTENT" | "INCONSISTENT" | "PARTIAL"
    total_checked: int = 0


# ═══════════════════════════════════════════════════════════════════
# Constraint Helpers
# ═══════════════════════════════════════════════════════════════════

def _has_keys(values: dict, *keys: str) -> bool:
    """Check if all required keys are present and non-None in the values dict."""
    return all(k in values and values[k] is not None for k in keys)


def _safe_div(numerator: float, denominator: float, fallback: float = 0.0) -> float:
    """Safe division with fallback for zero denominators."""
    if abs(denominator) < 1e-12:
        return fallback
    return numerator / denominator


# ═══════════════════════════════════════════════════════════════════
# Financial Constraint Graph
# ═══════════════════════════════════════════════════════════════════

class FinancialConstraintGraph:
    """
    Encodes fundamental accounting equations as executable constraints.
    When an LLM outputs multiple financial numbers, runs all relevant
    constraints and flags any that are violated beyond a configurable tolerance.

    Usage:
        fcg = FinancialConstraintGraph()
        result = fcg.verify({
            "revenue": 394328,
            "cogs": 223546,
            "gross_profit": 170782,
            "operating_expenses": 54847,
            "operating_income": 115935,
            ...
        })
        if result.trust == "INCONSISTENT":
            print("⚠️ Accounting identity violations detected!")
    """

    # ───────────────────────────────────────────────────────────
    # HARD CONSTRAINTS — Accounting identities (must hold)
    # ───────────────────────────────────────────────────────────

    HARD_CONSTRAINTS = [
        # Income Statement Identities
        {
            "id": "FCG-001",
            "name": "Gross profit identity",
            "requires": ("revenue", "cogs", "gross_profit"),
            "check": lambda v: abs(
                (v["revenue"] - v["cogs"]) - v["gross_profit"]
            ),
            "ref_key": "revenue",
            "description": "Revenue - COGS = Gross Profit",
            "tolerance": 0.01,   # 1% relative tolerance for rounding
        },
        {
            "id": "FCG-002",
            "name": "Operating income identity",
            "requires": ("gross_profit", "operating_expenses", "operating_income"),
            "check": lambda v: abs(
                (v["gross_profit"] - v["operating_expenses"]) - v["operating_income"]
            ),
            "ref_key": "gross_profit",
            "description": "Gross Profit - OpEx = Operating Income",
            "tolerance": 0.01,
        },
        {
            "id": "FCG-003",
            "name": "Net income identity",
            "requires": ("operating_income", "interest_expense", "tax_expense", "net_income"),
            "check": lambda v: abs(
                (v["operating_income"] - v["interest_expense"] - v["tax_expense"])
                - v["net_income"]
            ),
            "ref_key": "operating_income",
            "description": "Operating Income - Interest - Tax = Net Income",
            "tolerance": 0.02,   # slightly looser — more line items can be missing
        },

        # Balance Sheet Identity
        {
            "id": "FCG-004",
            "name": "Balance sheet equation",
            "requires": ("total_assets", "total_liabilities", "total_equity"),
            "check": lambda v: abs(
                v["total_assets"] - v["total_liabilities"] - v["total_equity"]
            ),
            "ref_key": "total_assets",
            "description": "Total Assets = Total Liabilities + Total Equity",
            "tolerance": 0.005,  # very tight — this must always hold exactly
        },

        # Per-Share Identities
        {
            "id": "FCG-005",
            "name": "EPS identity",
            "requires": ("eps_diluted", "net_income", "diluted_shares"),
            "check": lambda v: abs(
                v["eps_diluted"] - _safe_div(v["net_income"], v["diluted_shares"])
            ),
            "ref_key": "eps_diluted",
            "description": "EPS = Net Income / Diluted Shares Outstanding",
            "tolerance": 0.05,   # loose — share count rounding
        },

        # Margin Consistency
        {
            "id": "FCG-006",
            "name": "Gross margin bounds",
            "requires": ("gross_margin",),
            "check": lambda v: 0.0 if 0 <= v["gross_margin"] <= 1 else 1.0,
            "ref_key": "gross_margin",
            "description": "Gross margin must be between 0% and 100%",
            "tolerance": 0.001,
        },
        {
            "id": "FCG-007",
            "name": "Gross margin consistency",
            "requires": ("gross_margin", "gross_profit", "revenue"),
            "check": lambda v: abs(
                v["gross_margin"] - _safe_div(v["gross_profit"], v["revenue"])
            ),
            "ref_key": "gross_margin",
            "description": "Gross Margin = Gross Profit / Revenue",
            "tolerance": 0.01,
        },

        # Cash Flow Identity
        {
            "id": "FCG-008",
            "name": "Total cash flow identity",
            "requires": ("operating_cash_flow", "investing_cash_flow", "financing_cash_flow", "net_cash_flow"),
            "check": lambda v: abs(
                (v["operating_cash_flow"] + v["investing_cash_flow"] + v["financing_cash_flow"])
                - v["net_cash_flow"]
            ),
            "ref_key": "operating_cash_flow",
            "description": "OCF + ICF + FCF = Net Change in Cash",
            "tolerance": 0.02,
        },
    ]

    # ───────────────────────────────────────────────────────────
    # SOFT CONSTRAINTS — Sanity bounds (warnings)
    # ───────────────────────────────────────────────────────────

    SOFT_CONSTRAINTS = [
        {
            "id": "FCG-S001",
            "name": "Revenue non-negative",
            "requires": ("revenue",),
            "check": lambda v: 0.0 if v["revenue"] >= 0 else 1.0,
            "ref_key": "revenue",
            "description": "Revenue should not be negative",
            "tolerance": 0,
        },
        {
            "id": "FCG-S002",
            "name": "Revenue growth bounds",
            "requires": ("revenue_growth",),
            "check": lambda v: 0.0 if -0.8 <= v["revenue_growth"] <= 5.0 else 1.0,
            "ref_key": "revenue_growth",
            "description": "YoY revenue growth should be between -80% and +500%",
            "tolerance": 0,
        },
        {
            "id": "FCG-S003",
            "name": "PE ratio plausibility",
            "requires": ("pe_ratio", "net_income"),
            "check": lambda v: 0.0 if (
                v["net_income"] <= 0 or 1 <= v["pe_ratio"] <= 500
            ) else 1.0,
            "ref_key": "pe_ratio",
            "description": "P/E ratio should be 1-500 for profitable companies",
            "tolerance": 0,
        },
        {
            "id": "FCG-S004",
            "name": "Debt-to-equity plausibility",
            "requires": ("total_liabilities", "total_equity"),
            "check": lambda v: 0.0 if (
                _safe_div(v["total_liabilities"], v["total_equity"]) <= 20
            ) else 1.0,
            "ref_key": "total_liabilities",
            "description": "Debt-to-Equity ratio should be ≤ 20x",
            "tolerance": 0,
        },
        {
            "id": "FCG-S005",
            "name": "Net margin bounds",
            "requires": ("net_margin",),
            "check": lambda v: 0.0 if -2.0 <= v["net_margin"] <= 1.0 else 1.0,
            "ref_key": "net_margin",
            "description": "Net margin should be between -200% and 100%",
            "tolerance": 0,
        },
    ]

    # ───────────────────────────────────────────────────────────
    # Core Engine
    # ───────────────────────────────────────────────────────────

    def verify(self, values: dict[str, float]) -> ConstraintResult:
        """
        Run all applicable constraints against a dict of financial values.

        Args:
            values: dict mapping metric_name → verified_float_value
                    (after DVL single-number correction — FCG is a second pass)

        Returns:
            ConstraintResult with passed/violated/skipped constraint IDs
            and an overall trust classification.

        Only runs constraints where ALL required values are present.
        """
        passed = []
        violations = []
        skipped = []

        all_constraints = self.HARD_CONSTRAINTS + self.SOFT_CONSTRAINTS

        for constraint in all_constraints:
            cid = constraint["id"]
            required_keys = constraint.get("requires", ())

            # Skip if required values are missing
            if not _has_keys(values, *required_keys):
                skipped.append(cid)
                continue

            try:
                # Evaluate the constraint check function
                error_value = constraint["check"](values)

                # Compute relative error against reference value
                ref_key = constraint.get("ref_key", required_keys[0] if required_keys else None)
                ref_value = abs(values.get(ref_key, 1.0)) if ref_key else 1.0
                ref_value = max(ref_value, 1e-10)  # prevent division by zero

                relative_error = error_value / ref_value

                if relative_error > constraint["tolerance"]:
                    severity = "HARD" if cid.startswith("FCG-0") else "SOFT"
                    violations.append(ConstraintViolation(
                        constraint_id=cid,
                        constraint_name=constraint["name"],
                        expected_relationship=constraint["description"],
                        lhs_value=round(error_value, 6),
                        rhs_value=0.0,
                        delta_pct=round(relative_error * 100, 4),
                        severity=severity,
                    ))
                    logger.debug(
                        "FCG VIOLATION: %s — %s (%.4f%% error)",
                        cid, constraint["name"], relative_error * 100
                    )
                else:
                    passed.append(cid)

            except (KeyError, ZeroDivisionError, TypeError, ValueError) as e:
                logger.warning("FCG constraint %s skipped due to error: %s", cid, e)
                skipped.append(cid)

        # Classify overall trust
        total_checked = len(passed) + len(violations)
        if not violations:
            trust = "CONSISTENT"
        elif any(v.severity == "HARD" for v in violations):
            trust = "INCONSISTENT"
        else:
            trust = "PARTIAL"

        logger.info(
            "FCG result: %d passed, %d violations, %d skipped → %s",
            len(passed), len(violations), len(skipped), trust
        )

        return ConstraintResult(
            passed=passed,
            violations=violations,
            skipped=skipped,
            trust=trust,
            total_checked=total_checked,
        )

    def to_dict(self, result: ConstraintResult) -> dict:
        """Serialize ConstraintResult for API responses."""
        return {
            "trust": result.trust,
            "total_checked": result.total_checked,
            "passed": result.passed,
            "skipped": result.skipped,
            "violations": [
                {
                    "id": v.constraint_id,
                    "name": v.constraint_name,
                    "relationship": v.expected_relationship,
                    "error_value": v.lhs_value,
                    "delta_pct": v.delta_pct,
                    "severity": v.severity,
                }
                for v in result.violations
            ],
        }


# ═══════════════════════════════════════════════════════════════════
# Module-level singleton
# ═══════════════════════════════════════════════════════════════════

fcg = FinancialConstraintGraph()
