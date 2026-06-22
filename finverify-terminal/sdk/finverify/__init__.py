"""
FinVerify — Deterministic Verification for Financial LLM Outputs
================================================================
Reduces numerical hallucination in financial LLMs through
deterministic correction (scale, sign, magnitude).

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
"""

from .dvl import verify_local, DVLResult
from .client import FinVerifyClient

__version__ = "0.1.0"
__all__ = ["FinVerifyClient", "verify_local", "DVLResult"]
