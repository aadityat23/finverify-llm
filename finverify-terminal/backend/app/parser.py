"""
Number Parser
=============
Extracts numerical values from raw LLM text output.
Handles currency symbols, percentages, parenthesized negatives,
and common LLM response artifacts.
"""

import re
from typing import Optional

from .dvl import RATIO_KEYWORDS

# ---------------------------------------------------------------------------
# Core extraction (matches notebook implementation exactly)
# ---------------------------------------------------------------------------

def extract_number(text: str) -> Optional[float]:
    """
    Extract a number from text, handling financial formatting.

    - Strips $, commas, %
    - Converts parenthesized numbers to negatives: (1234) → -1234
    - Returns the **last** number found (LLMs often restate the question
      before giving the answer, so the last number is usually the answer).
    """
    if not text:
        return None

    text = text.replace("$", "").replace(",", "").replace("%", "")
    # Convert accounting-style negatives: (1234.56) → -1234.56
    text = re.sub(r"\((\d+\.?\d*)\)", r"-\1", text)

    matches = re.findall(r"[-+]?\d*\.?\d+", text)
    return float(matches[-1]) if matches else None


# ---------------------------------------------------------------------------
# LLM output cleaning
# ---------------------------------------------------------------------------

_LLM_ARTIFACTS = [
    "the answer is",
    "therefore",
    "thus",
    "hence",
    "so the answer is",
    "final answer:",
    "result:",
    "= ",
]


def clean_llm_output(raw_text: str) -> tuple[str, Optional[float]]:
    """
    Clean raw LLM text and extract the predicted number.

    Returns
    -------
    cleaned_text : str
        The cleaned text fragment.
    extracted_number : float | None
        The number extracted from it, or None.
    """
    if not raw_text:
        return "", None

    # Take the part after "Answer:" if present
    if "Answer:" in raw_text:
        cleaned = raw_text.split("Answer:")[-1]
    elif "answer:" in raw_text:
        cleaned = raw_text.split("answer:")[-1]
    else:
        cleaned = raw_text

    cleaned = cleaned.strip()

    # Strip common LLM preamble artifacts
    lower = cleaned.lower()
    for artifact in _LLM_ARTIFACTS:
        if lower.startswith(artifact):
            cleaned = cleaned[len(artifact):].strip()
            lower = cleaned.lower()

    number = extract_number(cleaned)
    return cleaned, number


# ---------------------------------------------------------------------------
# Display formatting
# ---------------------------------------------------------------------------

def format_number_display(value: Optional[float], question: str) -> str:
    """
    Format a number for display in the terminal UI,
    adapting to the question context.
    """
    if value is None:
        return "N/A"

    q_lower = question.lower()
    is_ratio = any(kw in q_lower for kw in RATIO_KEYWORDS)

    if is_ratio:
        return f"{value:.2f}%"
    if abs(value) > 1e6:
        return f"{value:,.0f}"
    return f"{value:.4f}"
