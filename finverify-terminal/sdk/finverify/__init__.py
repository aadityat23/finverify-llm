"""
FinVerify — Deterministic Verification for Financial LLM Outputs
================================================================
Reduces numerical hallucination in financial LLMs through
deterministic correction (scale, sign, magnitude) + constraint graphs.

42× accuracy improvement on FinQA benchmark (n=873).

Quick start:
    from finverify import FinVerifyClient, verify_local

    # Remote (via API)
    client = FinVerifyClient()
    result = client.verify("profit margin", 0.2531)
    print(result.verified_value)  # 25.31
    print(result.trust_score)     # MEDIUM

    # Local (pure Python, no API call)
    result = verify_local("profit margin", 0.2531)
    print(result.verified_value)  # 25.31

    # LLM Interceptor (zero-friction)
    from finverify import FinVerifyInterceptor
    fv = FinVerifyInterceptor()
    verified_fn = fv.wrap(openai.chat.completions.create)
    response = verified_fn(model="gpt-4o", messages=[...])
    print(response._finverify.overall_trust)  # "CLEAN" | "CORRECTED" | "INCONSISTENT"
"""

from .dvl import verify_local, DVLResult
from .client import FinVerifyClient
from .interceptor import FinVerifyInterceptor, VerificationResult, FinVerifyInconsistencyError
from .normalizer import normalize_metric_name

__version__ = "0.2.0"
__all__ = [
    "FinVerifyClient",
    "FinVerifyInterceptor",
    "FinVerifyInconsistencyError",
    "VerificationResult",
    "verify_local",
    "DVLResult",
    "normalize_metric_name",
]
