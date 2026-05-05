"""
Query Classifier
================
Classifies incoming queries into three modes:
  - numerical: run through DVL pipeline
  - advisory:  skip DVL, return LLM text unverified
  - general:   LLM response only
"""

# ---------------------------------------------------------------------------
# Keyword banks
# ---------------------------------------------------------------------------

NUMERICAL_KEYWORDS: list[str] = [
    "ratio", "margin", "growth", "change", "percent", "increase",
    "decrease", "yoy", "revenue", "income", "earnings", "eps",
    "yield", "return", "cet1", "roa", "roe", "ebitda",
]

ADVISORY_KEYWORDS: list[str] = [
    "invest", "buy", "sell", "should i", "recommend", "advice",
    "portfolio", "where", "which stock", "best", "worst",
]


# ---------------------------------------------------------------------------
# Classifier
# ---------------------------------------------------------------------------

def classify_query(query: str) -> str:
    """
    Classify a query string into one of three modes.

    Returns
    -------
    "advisory" | "numerical" | "general"
    """
    q = query.lower()
    if any(k in q for k in ADVISORY_KEYWORDS):
        return "advisory"
    if any(k in q for k in NUMERICAL_KEYWORDS):
        return "numerical"
    return "general"
