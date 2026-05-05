"""
DVL Test Suite
==============
Tests the DVL verification engine and number parser against
the paper's known failure cases and tricky extraction inputs.

Usage: python -m test_dvl   (from backend/ directory)
"""

import sys
import os

# Ensure we can import from the app package
sys.path.insert(0, os.path.dirname(__file__))

from app.parser import extract_number, clean_llm_output
from app.dvl import full_verify, is_correct, format_correction_log


def test_extract_number():
    """Test extract_number on 10 tricky inputs."""
    cases = [
        # (input_text, expected_output)
        ("$1,234.56", 1234.56),
        ("-0.3411", -0.3411),
        ("(1234)", -1234.0),
        ("The answer is 42.5%", 42.5),
        ("Revenue was $12,345,678", 12345678.0),
        ("+0.07004", 0.07004),
        ("(56.78) million", -56.78),
        ("3.14159", 3.14159),
        ("-$999,999.99", -999999.99),
        ("0.001", 0.001),
    ]

    print("=" * 60)
    print("TEST: extract_number()")
    print("=" * 60)

    passed = 0
    for text, expected in cases:
        result = extract_number(text)
        ok = result is not None and abs(result - expected) < 1e-6
        status = "PASS" if ok else "FAIL"
        if ok:
            passed += 1
        print(f"  [{status}] extract_number(\"{text}\") = {result} (expected {expected})")

    print(f"\n  Results: {passed}/{len(cases)} passed\n")
    return passed == len(cases)


def test_dvl_cases():
    """
    Test full_verify on the 3 paper demonstration cases:

    1. CET1 ratio — reasoning error, DVL can't fix → unchanged
       predicted=0.07004, actual=0.10935 → no corrections, HIGH trust

    2. Class A shares — magnitude error → magnitude_x10 → 1040.0 ≈ 995.0
       predicted=104.0, actual=995.0

    3. HTM securities — compound error (scale + sign)
       predicted=-34.11, actual=0.34146
       → scale_div100: -34.11 → -0.3411
       → sign_corrected: -0.3411 → 0.3411
       Trust: LOW (compound correction)
    """

    print("=" * 60)
    print("TEST: full_verify() — Paper Failure Cases")
    print("=" * 60)

    cases = [
        {
            "name": "Case 1: CET1 ratio (reasoning error — should stay unchanged)",
            "question": "What was JPMorgan's CET1 ratio change?",
            "predicted": 0.07004,
            "actual": 0.10935,
            "expect_unchanged": True,
        },
        {
            "name": "Case 2: Class A shares (magnitude error — DVL should fix ×10)",
            "question": "What was the increase in Class A shares outstanding?",
            "predicted": 104.0,
            "actual": 995.0,
            "expect_unchanged": False,
            "expect_rule": "magnitude_x10",
            "expect_value_approx": 1040.0,
        },
        {
            "name": "Case 3: HTM securities (compound: scale_div100 + sign_corrected)",
            "question": "What was the percentage decrease in HTM securities?",
            "predicted": -34.11,
            "actual": 0.34146,
            "expect_unchanged": False,
            "expect_rules": ["scale_div100", "sign_corrected"],
            "expect_value_approx": 0.3411,
        },
    ]

    all_passed = True

    for case in cases:
        print(f"\n  {case['name']}")
        print(f"    Predicted: {case['predicted']} | Actual: {case['actual']}")

        verified, log, label, color = full_verify(
            case["question"], case["predicted"], case["actual"]
        )

        formatted = format_correction_log(log)

        if case["expect_unchanged"]:
            # DVL should NOT fix this — it's a reasoning error
            ok = len(log) == 0 or not is_correct(verified, case["actual"])
            status = "PASS" if ok else "FAIL"
            print(f"    [{status}] Verified: {verified} | Corrections: {len(log)}")
            print(f"    Trust: {label} ({color})")
            if not ok:
                all_passed = False
        elif "expect_rules" in case:
            # Compound correction — check all expected rules are present
            rules_found = [r for r in case["expect_rules"] if any(e["rule"] == r for e in log)]
            all_rules = len(rules_found) == len(case["expect_rules"])
            value_close = is_correct(verified, case["actual"])
            ok = all_rules and value_close
            status = "PASS" if ok else "FAIL"
            print(f"    [{status}] Verified: {verified} (expected ~{case['expect_value_approx']})")
            print(f"    Rules applied: {', '.join(e['rule'] for e in log)}")
            for r in case["expect_rules"]:
                found = r in [e["rule"] for e in log]
                print(f"      {r}: {'found' if found else 'NOT FOUND'}")
            print(f"    Trust: {label} ({color})")
            if not ok:
                all_passed = False
        else:
            # Single correction
            rule_found = any(e["rule"] == case["expect_rule"] for e in log)
            value_close = is_correct(verified, case["actual"])
            ok = rule_found and value_close
            status = "PASS" if ok else "FAIL"
            print(f"    [{status}] Verified: {verified} (expected ~{case['expect_value_approx']})")
            print(f"    Rule applied: {case['expect_rule']} → {'found' if rule_found else 'NOT FOUND'}")
            print(f"    Trust: {label} ({color})")
            if not ok:
                all_passed = False

        if formatted:
            print("    Correction log:")
            for entry in formatted:
                print(f"      • {entry['rule']}: {entry['before']} → {entry['after']}")
                print(f"        {entry['description']}")

    print(f"\n  {'ALL CASES PASSED' if all_passed else 'SOME CASES FAILED'}")
    return all_passed


def test_clean_llm_output():
    """Test LLM output cleaning."""
    print("\n" + "=" * 60)
    print("TEST: clean_llm_output()")
    print("=" * 60)

    cases = [
        ("Answer: 42.5", 42.5),
        ("The answer is $1,234", 1234.0),
        ("Therefore, (56.78)", -56.78),
        ("Question: blah\nAnswer: 0.3411", 0.3411),
    ]

    passed = 0
    for raw, expected in cases:
        cleaned, number = clean_llm_output(raw)
        ok = number is not None and abs(number - expected) < 1e-6
        status = "PASS" if ok else "FAIL"
        if ok:
            passed += 1
        print(f"  [{status}] clean_llm_output(\"{raw[:40]}...\") = {number} (expected {expected})")

    print(f"\n  Results: {passed}/{len(cases)} passed\n")
    return passed == len(cases)


def test_scale_ambiguous():
    """Test that ambiguous scale (1-100) is NOT auto-corrected without ground truth."""
    print("\n" + "=" * 60)
    print("TEST: Ambiguous Scale (no ground truth)")
    print("=" * 60)

    # CET1 ratio 10.935 without ground truth → should stay 10.935
    verified, log, label, color = full_verify(
        "What was JPMorgan's CET1 ratio?",
        10.935,
        None,  # no ground truth
    )
    ok = verified == 10.935 and len(log) == 0
    status = "PASS" if ok else "FAIL"
    print(f"  [{status}] CET1 ratio 10.935 (no actual) → {verified} | corrections: {len(log)}")
    print(f"    Trust: {label} ({color})")
    return ok


def test_query_classifier():
    """Test the query classifier."""
    print("\n" + "=" * 60)
    print("TEST: classify_query()")
    print("=" * 60)

    from app.router import classify_query

    cases = [
        ("What was the CET1 ratio?", "numerical"),
        ("Should I buy Apple stock?", "advisory"),
        ("What is JPMorgan's revenue growth?", "numerical"),
        ("Which stock should I invest in?", "advisory"),
        ("Tell me about quarterly reports", "general"),
        ("What was the YoY margin change?", "numerical"),
        ("Recommend a portfolio allocation", "advisory"),
    ]

    passed = 0
    for query, expected in cases:
        result = classify_query(query)
        ok = result == expected
        status = "PASS" if ok else "FAIL"
        if ok:
            passed += 1
        print(f"  [{status}] \"{query[:45]}\" → {result} (expected {expected})")

    print(f"\n  Results: {passed}/{len(cases)} passed\n")
    return passed == len(cases)


if __name__ == "__main__":
    print("\n" + "=" * 60)
    print("  FINVERIFY — DVL TEST SUITE")
    print("=" * 60 + "\n")

    r1 = test_extract_number()
    r2 = test_dvl_cases()
    r3 = test_clean_llm_output()
    r4 = test_scale_ambiguous()
    r5 = test_query_classifier()

    print("\n" + "=" * 60)
    print("  SUMMARY")
    print("=" * 60)
    print(f"  extract_number:    {'PASS' if r1 else 'FAIL'}")
    print(f"  full_verify (DVL): {'PASS' if r2 else 'FAIL'}")
    print(f"  clean_llm_output:  {'PASS' if r3 else 'FAIL'}")
    print(f"  ambiguous_scale:   {'PASS' if r4 else 'FAIL'}")
    print(f"  query_classifier:  {'PASS' if r5 else 'FAIL'}")
    print("=" * 60)

    if not (r1 and r2 and r3 and r4 and r5):
        sys.exit(1)
    print("\n  ✓ All tests passed — DVL engine validated.\n")
