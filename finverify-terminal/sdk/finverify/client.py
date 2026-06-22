"""
finverify.client — HTTP client for the FinVerify /v1/verify API
================================================================
Both sync and async versions for maximum flexibility.

Usage:
    # Synchronous
    from finverify import FinVerifyClient
    client = FinVerifyClient()
    result = client.verify("profit margin", 0.2531)
    print(result.verified_value)  # 25.31

    # Async
    import asyncio
    result = asyncio.run(client.averify("profit margin", 0.2531))
"""

import json
import urllib.request
import urllib.error
from dataclasses import dataclass
from typing import Optional

# Async support — optional import
try:
    import httpx
    _HTTPX_AVAILABLE = True
except ImportError:
    _HTTPX_AVAILABLE = False


@dataclass
class VerifyResult:
    """Result from the /v1/verify API."""
    question: str
    raw_value: float
    verified_value: float
    correction_applied: Optional[str]
    trust_score: str
    trust_color: str
    delta_pct: float
    dvl_version: str
    timestamp: str

    @property
    def was_corrected(self) -> bool:
        return self.correction_applied is not None

    @classmethod
    def from_dict(cls, data: dict) -> "VerifyResult":
        return cls(
            question=data["question"],
            raw_value=data["raw_value"],
            verified_value=data["verified_value"],
            correction_applied=data.get("correction_applied"),
            trust_score=data["trust_score"],
            trust_color=data["trust_color"],
            delta_pct=data["delta_pct"],
            dvl_version=data.get("dvl_version", "unknown"),
            timestamp=data.get("timestamp", ""),
        )


class FinVerifyClient:
    """
    Client for the FinVerify DVL API.

    Parameters
    ----------
    api_url : str
        Base URL of the FinVerify API.
    api_key : str, optional
        API key for the X-FinVerify-Key header (optional, for tracking).
    timeout : float
        Request timeout in seconds.

    Examples
    --------
    >>> client = FinVerifyClient()
    >>> result = client.verify("profit margin", 0.2531)
    >>> print(f"{result.verified_value}% — trust: {result.trust_score}")
    25.31% — trust: MEDIUM

    >>> # With custom API endpoint
    >>> client = FinVerifyClient(api_url="http://localhost:8000")
    >>> result = client.verify("P/E ratio", 28.5)
    >>> result.trust_score
    'HIGH'
    """

    def __init__(
        self,
        api_url: str = "https://aadi2026-finverify-api.hf.space",
        api_key: Optional[str] = None,
        timeout: float = 15.0,
    ):
        self.api_url = api_url.rstrip("/")
        self.api_key = api_key
        self.timeout = timeout

    def _build_headers(self) -> dict:
        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["X-FinVerify-Key"] = self.api_key
        return headers

    # ----- Synchronous (stdlib only, no dependencies) -----

    def verify(
        self,
        question: str,
        raw_value: float,
        model_source: Optional[str] = None,
    ) -> VerifyResult:
        """
        Verify a financial number through the DVL API (synchronous).

        Parameters
        ----------
        question : str
            Financial question for keyword detection.
        raw_value : float
            Raw number to verify.
        model_source : str, optional
            Identifier for the source model.

        Returns
        -------
        VerifyResult
        """
        url = f"{self.api_url}/v1/verify"
        payload: dict = {"question": question, "raw_value": raw_value}
        if model_source:
            payload["model_source"] = model_source

        data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            url,
            data=data,
            headers=self._build_headers(),
            method="POST",
        )

        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                body = json.loads(resp.read().decode("utf-8"))
                return VerifyResult.from_dict(body)
        except urllib.error.HTTPError as e:
            error_body = e.read().decode("utf-8") if e.fp else ""
            raise RuntimeError(
                f"FinVerify API error (HTTP {e.code}): {error_body}"
            ) from e
        except urllib.error.URLError as e:
            raise ConnectionError(
                f"Cannot connect to FinVerify API at {self.api_url}: {e.reason}"
            ) from e

    def health(self) -> dict:
        """Check API health status."""
        url = f"{self.api_url}/health"
        req = urllib.request.Request(url)
        with urllib.request.urlopen(req, timeout=self.timeout) as resp:
            return json.loads(resp.read().decode("utf-8"))

    # ----- Async (requires httpx) -----

    async def averify(
        self,
        question: str,
        raw_value: float,
        model_source: Optional[str] = None,
    ) -> VerifyResult:
        """
        Verify a financial number through the DVL API (async).

        Requires `httpx` — install with: pip install httpx

        Parameters
        ----------
        question : str
            Financial question for keyword detection.
        raw_value : float
            Raw number to verify.
        model_source : str, optional
            Identifier for the source model.

        Returns
        -------
        VerifyResult
        """
        if not _HTTPX_AVAILABLE:
            raise ImportError(
                "Async support requires httpx. Install with: pip install httpx"
            )

        url = f"{self.api_url}/v1/verify"
        payload: dict = {"question": question, "raw_value": raw_value}
        if model_source:
            payload["model_source"] = model_source

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            resp = await client.post(
                url,
                json=payload,
                headers=self._build_headers(),
            )
            resp.raise_for_status()
            return VerifyResult.from_dict(resp.json())

    async def ahealth(self) -> dict:
        """Check API health status (async)."""
        if not _HTTPX_AVAILABLE:
            raise ImportError("Async support requires httpx.")

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            resp = await client.get(f"{self.api_url}/health")
            resp.raise_for_status()
            return resp.json()
