"""
Tests for finverify.dvl — Pure Python DVL verification
"""

import sys
import os

# Add SDK to path for local testing
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from finverify.dvl import verify_local, DVLResult


def test_scale_mul100_profit_margin():
    """Decimal profit margin should be scaled to percentage."""
    r = verify_local("What was the profit margin?", 0.2531)
    assert abs(r.verified_value - 25.31) < 0.01, f"Expected ~25.31, got {r.verified_value}"
    assert r.trust_score == "MEDIUM"
    assert r.was_corrected
    assert "scale_mul100" in r.correction_rules


def test_scale_mul100_revenue_growth():
    """Decimal revenue growth should be scaled to percentage."""
    r = verify_local("What was the revenue growth rate?", 0.0623)
    assert abs(r.verified_value - 6.23) < 0.01, f"Expected ~6.23, got {r.verified_value}"
    assert r.trust_score == "MEDIUM"
    assert "scale_mul100" in r.correction_rules


def test_scale_div100():
    """Value >100 with ratio keyword should be divided by 100."""
    r = verify_local("What was the growth rate?", 1240.0)
    assert abs(r.verified_value - 12.40) < 0.01, f"Expected ~12.40, got {r.verified_value}"
    assert r.trust_score == "MEDIUM"
    assert "scale_div100" in r.correction_rules


def test_no_correction_ambiguous_range():
    """Value in 1-100 range should NOT be auto-corrected."""
    r = verify_local("What was the CET1 ratio?", 10.935)
    assert abs(r.verified_value - 10.935) < 0.001, f"Expected 10.935, got {r.verified_value}"
    assert r.trust_score == "HIGH"
    assert not r.was_corrected


def test_no_correction_pe_ratio():
    """P/E ratio of 28.5 is already correct."""
    r = verify_local("What was the price to earnings ratio?", 28.5)
    assert abs(r.verified_value - 28.5) < 0.01
    assert r.trust_score == "HIGH"
    assert not r.was_corrected


def test_no_correction_non_ratio():
    """Non-ratio questions should not trigger scale correction."""
    r = verify_local("How many employees does the company have?", 0.5)
    assert abs(r.verified_value - 0.5) < 0.01
    assert r.trust_score == "HIGH"


def test_sign_correction_growth():
    """Negative value with 'growth' keyword should be corrected to positive."""
    r = verify_local("What was the revenue growth?", -0.08)
    # Should first mul100 (-0.08 → -8.0), then sign correct (-8.0 → 8.0)
    assert r.verified_value > 0, f"Expected positive, got {r.verified_value}"
    assert r.was_corrected


def test_sign_correction_decrease():
    """Positive value with 'decrease' keyword should be corrected to negative."""
    r = verify_local("What was the decrease in expenses?", 0.12)
    # Should mul100 (0.12 → 12.0), then sign correct (12.0 → -12.0)
    assert r.verified_value < 0, f"Expected negative, got {r.verified_value}"


def test_dvl_result_properties():
    """DVLResult dataclass properties should work correctly."""
    r = verify_local("margin", 0.25)
    assert isinstance(r, DVLResult)
    assert r.question == "margin"
    assert r.raw_value == 0.25
    assert r.delta_pct > 0
    assert r.correction_summary is not None


def test_zero_value():
    """Zero value should not cause division errors."""
    r = verify_local("What was the change?", 0.0)
    assert r.verified_value == 0.0
    assert r.trust_score == "HIGH"


def test_large_magnitude():
    """Very large values should trigger magnitude correction when extreme."""
    r = verify_local("total revenue", 1e12)
    # 1e12 is a plausible revenue, should not be corrected
    assert r.verified_value > 0


# ---------------------------------------------------------------------------
# Runner
# ---------------------------------------------------------------------------

def main():
    tests = [
        test_scale_mul100_profit_margin,
        test_scale_mul100_revenue_growth,
        test_scale_div100,
        test_no_correction_ambiguous_range,
        test_no_correction_pe_ratio,
        test_no_correction_non_ratio,
        test_sign_correction_growth,
        test_sign_correction_decrease,
        test_dvl_result_properties,
        test_zero_value,
        test_large_magnitude,
    ]

    passed = 0
    failed = 0

    print(f"\n{'='*50}")
    print(f"  finverify SDK — DVL Unit Tests")
    print(f"{'='*50}\n")

    for test in tests:
        try:
            test()
            print(f"  [PASS] {test.__name__}")
            passed += 1
        except AssertionError as e:
            print(f"  [FAIL] {test.__name__}: {e}")
            failed += 1
        except Exception as e:
            print(f"  [FAIL] {test.__name__}: EXCEPTION -- {e}")
            failed += 1

    print(f"\n{'='*50}")
    print(f"  Results: {passed}/{passed + failed} passed")
    if failed == 0:
        print(f"  All tests passed!")
    else:
        print(f"  {failed} test(s) failed")
    print(f"{'='*50}\n")

    return failed == 0


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
