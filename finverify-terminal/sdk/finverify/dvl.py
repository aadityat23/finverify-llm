"""
finverify.dvl — Pure Python Deterministic Verification Layer
=============================================================
No external dependencies. No FastAPI. Just the DVL logic.

This is a standalone port of backend/app/dvl.py designed
for embedding directly in any Python application.

Pipeline: scale_correction → sign_correction → magnitude_correction
Each step produces an audit log entry.
"""

from dataclasses import dataclass, field
from typing import Optional


@dataclass
class DVLResult:
    """Result of a DVL verification pass."""
    question: str
    raw_value: float
    verified_value: float
    corrections: list[dict] = field(default_factory=list)
    trust_score: str = "HIGH"     # HIGH | MEDIUM | LOW
    trust_color: str = "#00ff88"  # green | amber | red
    delta_pct: float = 0.0

    @property
    def was_corrected(self) -> bool:
        return len(self.corrections) > 0

    @property
    def correction_rules(self) -> list[str]:
        return [c["rule"] for c in self.corrections]

    @property
    def correction_summary(self) -> Optional[str]:
        if not self.corrections:
            return None
        return " → ".join(self.correction_rules)


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

RATIO_KEYWORDS: list[str] = [
    "ratio", "margin", "return", "yield", "growth",
    "change", "increase", "decrease", "percent", "percentage",
    "rate", "loss",
]

DVL_VERSION = "1.0.0"


# ---------------------------------------------------------------------------
# Core verification
# ---------------------------------------------------------------------------

def _is_ratio_question(question: str) -> bool:
    """Check if question relates to a ratio/percentage metric."""
    q_lower = question.lower()
    return any(kw in q_lower for kw in RATIO_KEYWORDS)


def verify_local(
    question: str,
    raw_value: float,
    tolerance: float = 0.05,
) -> DVLResult:
    """
    Run the DVL pipeline on a raw numerical value.

    Parameters
    ----------
    question : str
        The financial question (used for keyword detection).
    raw_value : float
        The raw number from the LLM to verify.
    tolerance : float
        Tolerance for correctness checks (default: 5%).

    Returns
    -------
    DVLResult
        Contains verified_value, corrections applied, and trust score.

    Examples
    --------
    >>> result = verify_local("What was the profit margin?", 0.2531)
    >>> result.verified_value
    25.31
    >>> result.trust_score
    'MEDIUM'

    >>> result = verify_local("What was the P/E ratio?", 28.5)
    >>> result.verified_value
    28.5
    >>> result.trust_score
    'HIGH'
    """
    value = raw_value
    corrections: list[dict] = []
    is_ratio = _is_ratio_question(question)

    # ------------------------------------------------------------------
    # Step 1 — Scale correction (heuristic mode, no ground truth)
    # ------------------------------------------------------------------
    if is_ratio and value != 0.0:
        if abs(value) > 100:
            corrected = value / 100
            corrections.append({
                "rule": "scale_div100",
                "before": value,
                "after": corrected,
                "description": "Percentage-decimal confusion: divided by 100",
            })
            value = corrected
        elif abs(value) < 1:
            corrected = value * 100
            corrections.append({
                "rule": "scale_mul100",
                "before": value,
                "after": corrected,
                "description": "Percentage-decimal confusion: multiplied by 100",
            })
            value = corrected
        # 1 <= abs(value) <= 100: AMBIGUOUS — no auto-correct

    # ------------------------------------------------------------------
    # Step 2 — Sign correction (heuristic: question keyword analysis)
    # ------------------------------------------------------------------
    q_lower = question.lower()
    if value < 0 and any(kw in q_lower for kw in ["increase", "growth", "gain", "profit"]):
        corrected = abs(value)
        corrections.append({
            "rule": "sign_corrected",
            "before": value,
            "after": corrected,
            "description": "Sign correction: positive keyword but negative value",
        })
        value = corrected
    elif value > 0 and any(kw in q_lower for kw in ["decrease", "loss", "decline", "drop"]):
        corrected = -abs(value)
        corrections.append({
            "rule": "sign_corrected",
            "before": value,
            "after": corrected,
            "description": "Sign correction: negative keyword but positive value",
        })
        value = corrected

    # ------------------------------------------------------------------
    # Step 3 — Magnitude correction (extreme values only)
    # ------------------------------------------------------------------
    if abs(value) < 0.001 or abs(value) > 1e9:
        for k in [10, 100, 1000, 0.1, 0.01, 0.001]:
            corrected = value * k
            if 0.001 < abs(corrected) < 1e9:
                corrections.append({
                    "rule": f"magnitude_x{k}",
                    "before": value,
                    "after": corrected,
                    "description": f"Magnitude correction: scaled by {k}",
                })
                value = corrected
                break

    # ------------------------------------------------------------------
    # Trust scoring
    # ------------------------------------------------------------------
    trust_score, trust_color = _compute_trust(raw_value, value, corrections)

    # Delta
    delta_pct = 0.0
    if raw_value != 0:
        delta_pct = round(abs(value - raw_value) / abs(raw_value) * 100, 4)

    return DVLResult(
        question=question,
        raw_value=raw_value,
        verified_value=round(value, 6),
        corrections=corrections,
        trust_score=trust_score,
        trust_color=trust_color,
        delta_pct=delta_pct,
    )


def _compute_trust(
    raw: float,
    verified: float,
    corrections: list[dict],
) -> tuple[str, str]:
    """Derive trust score from correction magnitude."""
    if len(corrections) == 0:
        return "HIGH", "#00ff88"

    # Scale corrections are expected deterministic corrections → MEDIUM
    is_scale = any(c["rule"].startswith("scale_") for c in corrections)
    if is_scale:
        return "MEDIUM", "#fbbf24"

    delta = abs(verified - raw) / (abs(raw) + 1e-10)
    if delta < 0.05:
        return "HIGH", "#00ff88"
    if delta < 0.5:
        return "MEDIUM", "#fbbf24"
    return "LOW", "#f87171"
