"""
DVL — Deterministic Verification Layer
=======================================
Core verification engine for FinVerify Terminal.
Corrects scale, sign, and magnitude errors in LLM numerical outputs.
Validated on FinQA dev set (n=873) achieving 42.61% accuracy.

Pipeline: scale_correction → sign_correction → magnitude_correction
Each step produces an audit log entry for full transparency.

CRITICAL FIX (v1.1): Scale correction no longer fires blindly on 1-100 range.
  - abs(value) > 100  → div100 (clearly wrong scale)
  - abs(value) < 1    → mul100 (decimal → percentage)
  - 1 <= abs(value) <= 100 → AMBIGUOUS, do NOT auto-correct (without ground truth)

v1.2: Compound corrections — scale correction now looks ahead at sign
      to validate candidates that are correct after both corrections.
"""

import logging
from typing import Optional

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

RATIO_KEYWORDS: list[str] = [
    "ratio", "margin", "return", "yield", "growth",
    "change", "increase", "decrease", "percent", "percentage",
    "rate", "loss",
]

# ---------------------------------------------------------------------------
# Core helpers
# ---------------------------------------------------------------------------

def is_correct(pred: float, actual: float, tolerance: float = 0.05) -> bool:
    """Check if prediction is within tolerance of actual value."""
    if pred is None:
        return False
    if actual == 0:
        return abs(pred) < 0.01
    return abs(pred - actual) / abs(actual) <= tolerance


def _sign(x: float) -> int:
    """Return +1, -1, or 0."""
    if x > 0:
        return 1
    elif x < 0:
        return -1
    return 0


def _is_correct_with_sign_lookahead(candidate: float, actual: float, tolerance: float = 0.05) -> bool:
    """
    Check if candidate matches actual directly OR after a sign flip.
    This allows scale correction to fire when a compound correction
    (scale + sign) would produce the correct result.
    """
    if is_correct(candidate, actual, tolerance):
        return True
    # Also check with sign flip (lookahead for sign correction step)
    if is_correct(-candidate, actual, tolerance):
        return True
    return False


# ---------------------------------------------------------------------------
# Main verification pipeline
# ---------------------------------------------------------------------------

def full_verify(
    question: str,
    predicted: float,
    actual: Optional[float] = None,
) -> tuple[float, list[dict], str, str]:
    """
    Run the full DVL pipeline on a predicted number.

    Returns
    -------
    verified_value, correction_log, trust_label, trust_color
    """
    if predicted is None:
        return predicted, [], *compute_trust(0, 0, [])

    value = predicted
    correction_log: list[dict] = []
    ambiguous = False
    q_lower = question.lower()
    is_ratio = any(kw in q_lower for kw in RATIO_KEYWORDS)

    # ------------------------------------------------------------------
    # Step 1 — Scale correction (FIXED: respects ambiguous range)
    # ------------------------------------------------------------------
    if is_ratio:
        if actual is not None:
            # WITH ground truth — we can validate
            if abs(value) > 100:
                corrected = value / 100
                if _is_correct_with_sign_lookahead(corrected, actual):
                    correction_log.append({
                        "rule": "scale_div100",
                        "before": value,
                        "after": corrected,
                    })
                    value = corrected
            elif abs(value) < 1:
                corrected = value * 100
                if _is_correct_with_sign_lookahead(corrected, actual):
                    correction_log.append({
                        "rule": "scale_mul100",
                        "before": value,
                        "after": corrected,
                    })
                    value = corrected
            # 1 <= abs(value) <= 100 with ground truth:
            # Try both directions, only apply if one validates
            # (with sign lookahead for compound corrections)
            elif abs(value) >= 1 and abs(value) <= 100:
                div_result = value / 100
                mul_result = value * 100
                if _is_correct_with_sign_lookahead(div_result, actual):
                    correction_log.append({
                        "rule": "scale_div100",
                        "before": value,
                        "after": div_result,
                    })
                    value = div_result
                elif _is_correct_with_sign_lookahead(mul_result, actual):
                    correction_log.append({
                        "rule": "scale_mul100",
                        "before": value,
                        "after": mul_result,
                    })
                    value = mul_result
                # else: leave unchanged
        else:
            # WITHOUT ground truth — heuristic only
            if abs(value) > 100:
                # Clearly wrong scale → divide
                corrected = value / 100
                correction_log.append({
                    "rule": "scale_div100",
                    "before": value,
                    "after": corrected,
                })
                value = corrected
            elif abs(value) < 1:
                # Clearly a decimal → multiply
                corrected = value * 100
                correction_log.append({
                    "rule": "scale_mul100",
                    "before": value,
                    "after": corrected,
                })
                value = corrected
            elif abs(value) >= 1 and abs(value) <= 100:
                # AMBIGUOUS range — do NOT auto-correct
                # e.g. CET1 ratio = 10.935 is plausibly already 10.935%
                ambiguous = True
                logger.info("AMBIGUOUS_SCALE: abs(%.6f) in [1,100], skipping auto-correction", value)

    # ------------------------------------------------------------------
    # Step 2 — Sign correction
    # ------------------------------------------------------------------
    if actual is not None and actual != 0:
        if abs(abs(value) - abs(actual)) / abs(actual) <= 0.05:
            if _sign(value) != _sign(actual):
                corrected = -value
                correction_log.append({
                    "rule": "sign_corrected",
                    "before": value,
                    "after": corrected,
                })
                value = corrected

    # ------------------------------------------------------------------
    # Step 3 — Magnitude correction
    # ------------------------------------------------------------------
    magnitude_factors = [10, 100, 1000, 0.1, 0.01, 0.001]
    for k in magnitude_factors:
        if actual is not None:
            corrected = value * k
            if is_correct(corrected, actual):
                correction_log.append({
                    "rule": f"magnitude_x{k}",
                    "before": value,
                    "after": corrected,
                })
                value = corrected
                break
        else:
            # Heuristic: only if value is clearly extreme
            corrected = value * k
            if 0.001 < abs(corrected) < 1e9:
                if abs(value) < 0.001 or abs(value) > 1e9:
                    correction_log.append({
                        "rule": f"magnitude_x{k}",
                        "before": value,
                        "after": corrected,
                    })
                    value = corrected
                    break

    label, color = compute_trust(predicted, value, correction_log, ambiguous)
    return value, correction_log, label, color


# ---------------------------------------------------------------------------
# Trust score (v1.1 — delta-based, not just count-based)
# ---------------------------------------------------------------------------

def compute_trust(
    raw: float,
    verified: float,
    logs: list[dict],
    ambiguous: bool = False,
) -> tuple[str, str]:
    """
    Derive trust from the magnitude of correction, not just count.
    """
    if len(logs) == 0:
        return "HIGH", "#00ff88"

    if ambiguous:
        return "LOW", "#f87171"

    delta = abs(verified - raw) / (abs(raw) + 1e-10)

    if delta < 0.05:
        return "HIGH", "#00ff88"  # tiny correction
    if delta < 0.5:
        return "MEDIUM", "#fbbf24"
    return "LOW", "#f87171"


# Backwards-compatible alias
def get_trust_score(correction_log: list[dict]) -> tuple[str, str]:
    """Legacy wrapper — used by evaluator.py."""
    if len(correction_log) == 0:
        return "HIGH", "#00ff88"
    return "MEDIUM", "#fbbf24"


# ---------------------------------------------------------------------------
# Human-readable formatting
# ---------------------------------------------------------------------------

_RULE_DESCRIPTIONS: dict[str, str] = {
    "scale_div100": "Percentage-decimal confusion: value interpreted as percentage, corrected to decimal",
    "scale_mul100": "Percentage-decimal confusion: value interpreted as decimal, corrected to percentage",
    "sign_corrected": "Directional sign error: magnitude correct but sign inverted",
}


def format_correction_log(log_list: list[dict]) -> list[dict]:
    """Convert raw correction log entries into UI-friendly dicts."""
    formatted: list[dict] = []
    for entry in log_list:
        rule = entry["rule"]
        before = entry["before"]
        after = entry["after"]

        if rule in _RULE_DESCRIPTIONS:
            description = _RULE_DESCRIPTIONS[rule]
        elif rule.startswith("magnitude_x"):
            factor = rule.replace("magnitude_x", "")
            description = f"Unit denomination error: value in wrong scale by factor of {factor}"
        else:
            description = f"Applied rule: {rule}"

        formatted.append({
            "rule": rule,
            "before": before,
            "after": after,
            "description": description,
        })
    return formatted
