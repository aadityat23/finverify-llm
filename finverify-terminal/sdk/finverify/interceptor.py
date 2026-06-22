"""
finverify.interceptor — FinVerify Interception SDK (Session 2A)
================================================================
Zero-friction LLM wrapper that automatically runs DVL + FCG on financial outputs.

One line of code wraps any LLM client. The user doesn't change how they call
their LLM — they just wrap it.

Usage:
    from finverify import FinVerifyInterceptor

    fv = FinVerifyInterceptor(financial_context="earnings analysis")

    # Original call:
    response = openai.chat.completions.create(model="gpt-4o", messages=[...])

    # Intercepted call — identical interface, verified output:
    response = fv.wrap(openai.chat.completions.create)(model="gpt-4o", messages=[...])

    # Check verification result:
    print(response._finverify.overall_trust)   # "CLEAN" | "CORRECTED" | "INCONSISTENT"
    print(response._finverify.corrections)     # list of DVL corrections applied
"""

import re
import logging
from typing import Any, Callable, Optional
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)

FINVERIFY_API = "https://huggingface.co/spaces/aadi2026/finverify-api"


# ═══════════════════════════════════════════════════════════════════
# Data Classes
# ═══════════════════════════════════════════════════════════════════

@dataclass
class VerificationResult:
    """Result of intercepting and verifying LLM financial output."""
    original_text: str
    verified_text: str          # text with corrected numbers substituted in
    corrections: list[dict] = field(default_factory=list)
    constraint_violations: list[dict] = field(default_factory=list)
    overall_trust: str = "CLEAN"   # "CLEAN" | "CORRECTED" | "INCONSISTENT"
    dvl_version: str = "1.0.0"
    numbers_found: int = 0
    metrics_identified: int = 0


class FinVerifyInconsistencyError(Exception):
    """Raised when FCG detects constraint violations (if raise_on_inconsistency=True)."""
    def __init__(self, violations: list[dict]):
        self.violations = violations
        names = [v.get("constraint_name", v.get("name", "?")) for v in violations]
        super().__init__(f"FCG constraint violations: {names}")


class VerifiedString(str):
    """A str subclass that can carry a _finverify attribute."""
    _finverify: Optional["VerificationResult"] = None


# ═══════════════════════════════════════════════════════════════════
# Financial Number Extraction
# ═══════════════════════════════════════════════════════════════════

# Patterns for common financial number formats
_FINANCIAL_NUMBER_PATTERNS = [
    # $1.2B or 1.2 billion
    (r'\$?([\d,]+\.?\d*)\s*(?:billion|B)\b', 1e9),
    # $450M or 450 million
    (r'\$?([\d,]+\.?\d*)\s*(?:million|M)\b', 1e6),
    # $12K or 12 thousand
    (r'\$?([\d,]+\.?\d*)\s*(?:thousand|K)\b', 1e3),
    # 24.5% (no multiplier, keep as-is)
    (r'([\d,]+\.?\d*)\s*%', 1),
    # (3.2) negative accounting notation
    (r'\(([\d,]+\.?\d*)\)', -1),
    # Decimals like 0.1231
    (r'\b(0\.\d+)\b', 1),
    # Formatted integers like 1,234,567.89
    (r'\b(\d{1,3}(?:,\d{3})+(?:\.\d+)?)\b', 1),
]


def _extract_financial_numbers(text: str) -> list[dict]:
    """
    Extract numbers from financial text with surrounding context.
    Handles: $1.2B, 24.5%, 0.1231, 12.4 million, (3.2) [negative in parens]
    """
    results = []
    seen_positions = set()

    for pattern, multiplier in _FINANCIAL_NUMBER_PATTERNS:
        for match in re.finditer(pattern, text, re.IGNORECASE):
            # Skip overlapping matches
            if match.start() in seen_positions:
                continue
            seen_positions.add(match.start())

            num_str = match.group(1).replace(",", "")
            try:
                value = float(num_str) * multiplier

                # Get surrounding context for sentence extraction
                ctx_start = max(0, match.start() - 150)
                ctx_end = min(len(text), match.end() + 150)
                context = text[ctx_start:ctx_end]
                sentence = _extract_sentence(context, match.start() - ctx_start)

                results.append({
                    "raw_str": match.group(0),
                    "value": value,
                    "position": match.start(),
                    "context_sentence": sentence,
                    "metric_name": _infer_metric_name(sentence),
                })
            except ValueError:
                pass

    # Sort by position for stable ordering
    results.sort(key=lambda x: x["position"])
    return results


def _extract_sentence(context: str, num_pos: int) -> str:
    """Extract the sentence containing the number from surrounding context."""
    sentences = re.split(r'[.!?\n]', context)
    pos = 0
    for s in sentences:
        if pos + len(s) >= num_pos:
            return s.strip()
        pos += len(s) + 1
    return context[:200].strip()


def _infer_metric_name(sentence: str) -> Optional[str]:
    """
    Try to infer a canonical metric name from the sentence context.
    Scans n-grams (4-word to 1-word) looking for known metric aliases.
    """
    try:
        from finverify.normalizer import normalize_metric_name
    except ImportError:
        return None

    words = sentence.lower().split()
    # Try longer phrases first (more specific)
    for n in range(4, 0, -1):
        for i in range(len(words) - n + 1):
            phrase = " ".join(words[i:i + n])
            canonical = normalize_metric_name(phrase)
            if canonical:
                return canonical
    return None


# ═══════════════════════════════════════════════════════════════════
# Core Interceptor
# ═══════════════════════════════════════════════════════════════════

class FinVerifyInterceptor:
    """
    Wraps any callable that returns a string (LLM output) and runs DVL+FCG.

    Usage:
        import openai
        from finverify import FinVerifyInterceptor

        fv = FinVerifyInterceptor(api_key="fv_...", financial_context="earnings")

        # Original:
        response = openai.chat.completions.create(model="gpt-4o", messages=[...])

        # Intercepted — identical interface, verified output:
        response = fv.wrap(openai.chat.completions.create)(model="gpt-4o", messages=[...])

        # Access verification metadata:
        print(response._finverify.overall_trust)
        print(response._finverify.corrections)
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        api_url: str = FINVERIFY_API,
        financial_context: str = "",
        auto_correct: bool = True,
        raise_on_inconsistency: bool = False,
        use_local_dvl: bool = False,
    ):
        """
        Args:
            api_key: FinVerify API key (optional for public endpoint).
            api_url: FinVerify API URL. Defaults to HuggingFace Spaces deployment.
            financial_context: Additional context hint for DVL (e.g. "earnings analysis").
            auto_correct: If True, replace numbers in text with DVL-corrected values.
            raise_on_inconsistency: If True, raise FinVerifyInconsistencyError on FCG violations.
            use_local_dvl: If True, skip API calls and use the embedded pure-Python DVL.
        """
        self.api_key = api_key
        self.api_url = api_url.rstrip("/")
        self.financial_context = financial_context
        self.auto_correct = auto_correct
        self.raise_on_inconsistency = raise_on_inconsistency
        self.use_local_dvl = use_local_dvl
        self._client = None  # lazy httpx init

    def _get_http_client(self):
        """Lazy-initialize httpx client."""
        if self._client is None:
            try:
                import httpx
                self._client = httpx.Client(timeout=10.0)
            except ImportError:
                logger.warning("httpx not installed — falling back to local DVL")
                self.use_local_dvl = True
        return self._client

    # ───────────────────────────────────────────────────────────
    # Public API
    # ───────────────────────────────────────────────────────────

    def wrap(self, llm_fn: Callable) -> Callable:
        """
        Returns a wrapped version of any LLM function.
        The wrapped function has an identical interface but runs DVL+FCG
        on the output before returning.
        """
        def wrapped(*args: Any, **kwargs: Any) -> Any:
            response = llm_fn(*args, **kwargs)
            text = self._extract_text(response)
            if text:
                result = self.verify_text(text)
                response = self._inject_verified_text(response, result)
                # Attach verification result to response object
                try:
                    response._finverify = result
                except AttributeError:
                    pass  # immutable response objects (e.g. frozen dataclasses)
            return response
        return wrapped

    def verify_text(self, text: str) -> VerificationResult:
        """
        Extract all numbers from financial text, run DVL on each,
        detect metric names from context, run FCG on the set.

        This is the core method — can be called standalone without wrapping.
        """
        numbers = _extract_financial_numbers(text)
        corrections = []
        verified_values: dict[str, float] = {}

        for num_info in numbers:
            dvl_result = self._call_dvl(
                question=num_info["context_sentence"],
                raw_value=num_info["value"],
            )

            if dvl_result.get("correction_applied") or dvl_result.get("was_corrected"):
                corrections.append({
                    "original": num_info["raw_str"],
                    "corrected": dvl_result.get("verified_value", num_info["value"]),
                    "rule": dvl_result.get("correction_applied",
                                          dvl_result.get("correction_summary", "")),
                    "trust": dvl_result.get("trust_score", "HIGH"),
                    "position": num_info["position"],
                })

            # Collect verified values for FCG
            metric_name = num_info.get("metric_name")
            if metric_name:
                verified_values[metric_name] = dvl_result.get(
                    "verified_value", num_info["value"]
                )

        # Run FCG if we have multiple named values
        constraint_violations = []
        if len(verified_values) >= 2:
            fcg_result = self._call_fcg(verified_values)
            constraint_violations = fcg_result.get("violations", [])

        # Build verified text with corrections applied
        verified_text = text
        if self.auto_correct and corrections:
            # Apply corrections in reverse position order to preserve indices
            for correction in sorted(corrections, key=lambda x: x["position"], reverse=True):
                pos = correction["position"]
                original = correction["original"]
                corrected_str = str(correction["corrected"])
                verified_text = (
                    verified_text[:pos]
                    + corrected_str
                    + verified_text[pos + len(original):]
                )

        # Determine overall trust
        if not corrections and not constraint_violations:
            trust = "CLEAN"
        elif constraint_violations:
            trust = "INCONSISTENT"
        else:
            trust = "CORRECTED"

        if self.raise_on_inconsistency and trust == "INCONSISTENT":
            raise FinVerifyInconsistencyError(constraint_violations)

        return VerificationResult(
            original_text=text,
            verified_text=verified_text,
            corrections=corrections,
            constraint_violations=constraint_violations,
            overall_trust=trust,
            dvl_version="1.0.0",
            numbers_found=len(numbers),
            metrics_identified=len(verified_values),
        )

    # ───────────────────────────────────────────────────────────
    # DVL / FCG Calls
    # ───────────────────────────────────────────────────────────

    def _call_dvl(self, question: str, raw_value: float) -> dict:
        """Call DVL — remote API or local fallback."""
        if self.use_local_dvl:
            return self._call_dvl_local(question, raw_value)

        try:
            client = self._get_http_client()
            if client is None:
                return self._call_dvl_local(question, raw_value)

            resp = client.post(
                f"{self.api_url}/v1/verify",
                json={"question": question, "raw_value": raw_value},
                headers={"X-FinVerify-Key": self.api_key or ""},
            )
            data = resp.json()
            return {
                "verified_value": data.get("verified_value", raw_value),
                "trust_score": data.get("trust", "HIGH"),
                "correction_applied": data.get("correction_log", [{}])[0].get("rule") if data.get("correction_log") else None,
                "was_corrected": bool(data.get("correction_log")),
            }
        except Exception as e:
            logger.debug("DVL API call failed, using local: %s", e)
            return self._call_dvl_local(question, raw_value)

    def _call_dvl_local(self, question: str, raw_value: float) -> dict:
        """Run DVL locally using the embedded pure-Python DVL."""
        from finverify.dvl import verify_local
        result = verify_local(question, raw_value)
        return {
            "verified_value": result.verified_value,
            "trust_score": result.trust_score,
            "correction_applied": result.correction_summary,
            "was_corrected": result.was_corrected,
            "correction_summary": result.correction_summary,
        }

    def _call_fcg(self, values: dict[str, float]) -> dict:
        """Call FCG — remote API or empty fallback."""
        if self.use_local_dvl:
            return self._call_fcg_local(values)

        try:
            client = self._get_http_client()
            if client is None:
                return self._call_fcg_local(values)

            resp = client.post(
                f"{self.api_url}/v1/fcg/verify",
                json={"values": values},
                headers={"X-FinVerify-Key": self.api_key or ""},
            )
            data = resp.json()
            cr = data.get("constraint_result", {})
            return {
                "trust": cr.get("trust", "CONSISTENT"),
                "violations": cr.get("violations", []),
                "passed": cr.get("passed", []),
            }
        except Exception as e:
            logger.debug("FCG API call failed: %s", e)
            return self._call_fcg_local(values)

    def _call_fcg_local(self, values: dict[str, float]) -> dict:
        """Run FCG locally if the constraint engine is available."""
        try:
            from fcg.constraint_engine import fcg
            result = fcg.verify(values)
            return {
                "trust": result.trust,
                "violations": [
                    {
                        "constraint_name": v.constraint_name,
                        "relationship": v.expected_relationship,
                        "delta_pct": v.delta_pct,
                        "severity": v.severity,
                    }
                    for v in result.violations
                ],
                "passed": result.passed,
            }
        except ImportError:
            return {"violations": [], "trust": "UNKNOWN"}

    # ───────────────────────────────────────────────────────────
    # Response Adapters (OpenAI, Anthropic, raw string)
    # ───────────────────────────────────────────────────────────

    def _extract_text(self, response: Any) -> Optional[str]:
        """Extract text from various LLM response formats."""
        # Raw string
        if isinstance(response, str):
            return response

        # OpenAI ChatCompletion
        if hasattr(response, "choices"):
            try:
                return response.choices[0].message.content
            except (IndexError, AttributeError):
                pass

        # Anthropic Message
        if hasattr(response, "content"):
            try:
                content = response.content
                if isinstance(content, list) and content:
                    return content[0].text
                if isinstance(content, str):
                    return content
            except (IndexError, AttributeError):
                pass

        # Dict response (generic)
        if isinstance(response, dict):
            return response.get("text") or response.get("content") or response.get("output")

        return None

    def _inject_verified_text(self, response: Any, result: VerificationResult) -> Any:
        """Patch the verified text back into the response object."""
        if isinstance(response, str):
            vs = VerifiedString(result.verified_text)
            vs._finverify = result
            return vs

        # OpenAI
        if hasattr(response, "choices"):
            try:
                response.choices[0].message.content = result.verified_text
            except (IndexError, AttributeError):
                pass

        # Anthropic
        if hasattr(response, "content") and isinstance(response.content, list):
            try:
                response.content[0].text = result.verified_text
            except (IndexError, AttributeError):
                pass

        # Dict
        if isinstance(response, dict):
            for key in ("text", "content", "output"):
                if key in response:
                    response[key] = result.verified_text
                    break

        return response
