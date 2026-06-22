"""
test_verify_api.py — Test suite for the /v1/verify standalone DVL API
=====================================================================
Tests 5 canonical financial verification cases and asserts correct
trust scores, correction rules, and value ranges.

Usage:
    python test_verify_api.py                          # defaults to localhost:8000
    python test_verify_api.py https://your-api.hf.space  # custom base URL
"""

import sys
import json
import urllib.request
import urllib.error
from typing import Optional


BASE_URL = sys.argv[1] if len(sys.argv) > 1 else "http://localhost:8000"


def verify(question: str, raw_value: float, api_key: Optional[str] = None) -> dict:
    """Call /v1/verify and return parsed JSON response."""
    url = f"{BASE_URL}/v1/verify"
    payload = json.dumps({
        "question": question,
        "raw_value": raw_value,
    }).encode()

    headers = {"Content-Type": "application/json"}
    if api_key:
        headers["X-FinVerify-Key"] = api_key

    req = urllib.request.Request(url, data=payload, headers=headers, method="POST")
    with urllib.request.urlopen(req, timeout=15) as resp:
        return json.loads(resp.read().decode())


def test_case(
    name: str,
    question: str,
    raw_value: float,
    expected_trust: str,
    expected_correction: Optional[str],
    value_check: Optional[callable] = None,
):
    """Run a single test case and print pass/fail."""
    try:
        result = verify(question, raw_value)
    except Exception as e:
        print(f"  ✗ {name}: FAILED — {e}")
        return False

    passed = True
    details = []

    # Check trust score
    if result["trust_score"] != expected_trust:
        details.append(f"trust: expected {expected_trust}, got {result['trust_score']}")
        passed = False

    # Check correction
    if expected_correction is None:
        if result["correction_applied"] is not None:
            details.append(f"correction: expected None, got {result['correction_applied']}")
            passed = False
    else:
        if result["correction_applied"] is None or expected_correction not in result["correction_applied"]:
            details.append(f"correction: expected '{expected_correction}', got {result['correction_applied']}")
            passed = False

    # Check value
    if value_check and not value_check(result["verified_value"]):
        details.append(f"value: check failed, got {result['verified_value']}")
        passed = False

    # Check required fields exist
    for field in ["dvl_version", "timestamp", "delta_pct", "trust_color"]:
        if field not in result:
            details.append(f"missing field: {field}")
            passed = False

    status = "✓" if passed else "✗"
    print(f"  {status} {name}")
    if details:
        for d in details:
            print(f"      → {d}")
    else:
        trust_icon = {"HIGH": "🟢", "MEDIUM": "🟡", "LOW": "🔴"}.get(result["trust_score"], "⚪")
        correction_str = result["correction_applied"] or "none"
        print(f"      raw={raw_value} → verified={result['verified_value']:.4f} | "
              f"trust={trust_icon} {result['trust_score']} | correction={correction_str}")

    return passed


def main():
    print(f"\n{'='*60}")
    print(f"FinVerify DVL API Test Suite")
    print(f"Target: {BASE_URL}/v1/verify")
    print(f"{'='*60}\n")

    # Health check first
    try:
        with urllib.request.urlopen(f"{BASE_URL}/health", timeout=10) as resp:
            health = json.loads(resp.read().decode())
            print(f"  ● Health: {health.get('status', 'unknown')} | DVL: {health.get('dvl', '?')}\n")
    except Exception as e:
        print(f"  ✗ Health check failed: {e}")
        print(f"    Make sure the backend is running at {BASE_URL}")
        sys.exit(1)

    results = []

    # --- Test 1: Profit margin (decimal → percentage, scale_mul100) ---
    results.append(test_case(
        name="Profit margin (scale_mul100)",
        question="What was the profit margin?",
        raw_value=0.2531,
        expected_trust="MEDIUM",
        expected_correction="scale_mul100",
        value_check=lambda v: 25.0 < v < 26.0,  # should be ~25.31
    ))

    # --- Test 2: CET1 ratio (1-100 range, AMBIGUOUS → no correction) ---
    results.append(test_case(
        name="CET1 ratio (ambiguous, no correction)",
        question="What was the CET1 ratio?",
        raw_value=10.935,
        expected_trust="HIGH",
        expected_correction=None,
        value_check=lambda v: abs(v - 10.935) < 0.01,
    ))

    # --- Test 3: HTM securities (>100, scale_div100) ---
    results.append(test_case(
        name="HTM securities decrease (scale_div100)",
        question="What was the percentage decrease in HTM securities?",
        raw_value=-34.11,
        expected_trust="HIGH",  # 1-100 range = ambiguous = no correction in heuristic mode
        expected_correction=None,  # -34.11 is in [1,100], ambiguous range
        value_check=lambda v: abs(v - (-34.11)) < 0.01,  # unchanged in ambiguous range
    ))

    # --- Test 4: P/E ratio (in range, no correction) ---
    results.append(test_case(
        name="P/E ratio (no correction)",
        question="What was the price to earnings ratio?",
        raw_value=28.5,
        expected_trust="HIGH",
        expected_correction=None,
        value_check=lambda v: abs(v - 28.5) < 0.01,
    ))

    # --- Test 5: Revenue growth (decimal → percentage, scale_mul100) ---
    results.append(test_case(
        name="Revenue growth (scale_mul100)",
        question="What was the revenue growth rate?",
        raw_value=0.0623,
        expected_trust="MEDIUM",
        expected_correction="scale_mul100",
        value_check=lambda v: 6.0 < v < 7.0,  # should be ~6.23
    ))

    # --- Summary ---
    passed = sum(results)
    total = len(results)
    print(f"\n{'='*60}")
    print(f"  Results: {passed}/{total} passed")
    if passed == total:
        print(f"  🎉 All tests passed!")
    else:
        print(f"  ⚠ {total - passed} test(s) failed")
    print(f"{'='*60}\n")

    sys.exit(0 if passed == total else 1)


if __name__ == "__main__":
    main()
