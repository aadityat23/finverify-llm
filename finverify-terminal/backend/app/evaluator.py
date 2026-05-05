"""
Evaluator
=========
Orchestrates the full pipeline:
  LLM call → parse → DVL verify → format response.

Also provides a verify-only path for demo mode.
"""

from typing import Optional

from .dvl import full_verify, format_correction_log
from .parser import clean_llm_output, extract_number, format_number_display
from .models import QueryResponse, CorrectionEntry


def build_query_response(
    question: str,
    raw_text: Optional[str],
    raw_number: Optional[float],
    actual: Optional[float] = None,
) -> QueryResponse:
    """
    Run DVL on an already-parsed number and build the API response.
    """
    if raw_number is None:
        return QueryResponse(
            question=question,
            raw_text=raw_text,
            raw_number=None,
            verified_number=None,
            correction_log=[],
            trust_score="LOW",
            trust_color="#f87171",
            display_value="N/A — no number extracted",
        )

    verified, log, label, color = full_verify(question, raw_number, actual)
    formatted_log = format_correction_log(log)
    display = format_number_display(verified, question)

    return QueryResponse(
        question=question,
        raw_text=raw_text,
        raw_number=raw_number,
        verified_number=verified,
        correction_log=[CorrectionEntry(**e) for e in formatted_log],
        trust_score=label,
        trust_color=color,
        display_value=display,
    )
