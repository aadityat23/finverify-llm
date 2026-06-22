# finverify

> Deterministic verification for financial LLM outputs. 42× accuracy improvement on FinQA benchmark.

[![PyPI](https://img.shields.io/pypi/v/finverify)](https://pypi.org/project/finverify/)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](https://opensource.org/licenses/MIT)

## Install

```bash
pip install finverify              # local DVL only (zero dependencies)
pip install finverify[api]         # + async HTTP client (adds httpx)
```

## Quick Start

### Local verification (no API, no network)

```python
from finverify import verify_local

# Profit margin: 0.25 is clearly a decimal, not 25%
result = verify_local("What was the profit margin?", 0.2531)
print(result.verified_value)    # 25.31
print(result.trust_score)       # MEDIUM
print(result.correction_summary)  # scale_mul100

# P/E ratio: 28.5 is already correct (ambiguous range, no correction)
result = verify_local("What was the P/E ratio?", 28.5)
print(result.verified_value)    # 28.5
print(result.trust_score)       # HIGH
print(result.was_corrected)     # False
```

### Remote verification (via API)

```python
from finverify import FinVerifyClient

# Sync client (uses stdlib, zero dependencies)
client = FinVerifyClient()
result = client.verify("profit margin", 0.2531)
print(f"{result.verified_value}% — {result.trust_score}")
# 25.31% — MEDIUM

# With custom API endpoint
client = FinVerifyClient(
    api_url="http://localhost:8000",
    api_key="your-optional-key",
)
```

### Async verification

```python
import asyncio
from finverify import FinVerifyClient

async def main():
    client = FinVerifyClient()
    result = await client.averify("revenue growth rate", 0.0623)
    print(result.verified_value)   # 6.23
    print(result.trust_score)      # MEDIUM

asyncio.run(main())
```

## How It Works

The **Deterministic Verification Layer (DVL)** applies three ordered rules:

| Rule | Trigger | Example |
|---|---|---|
| **Scale** | Value < 1 with % keyword | `0.12` → `12.0%` |
| **Sign** | Positive keyword + negative value | `-0.34` → `+0.34` |
| **Magnitude** | Extreme values | `0.0001` → `0.1` |

```python
from finverify import verify_local

# Scale correction
r = verify_local("operating margin change", 0.1240)
# 0.1240 → 12.40 (scale_mul100, trust: MEDIUM)

# No correction needed (ambiguous range)
r = verify_local("CET1 ratio", 10.935)
# 10.935 → 10.935 (no correction, trust: HIGH)

# Sign correction
r = verify_local("revenue growth rate", -0.08)
# -0.08 → 8.0 (scale_mul100, sign_corrected → trust: MEDIUM)
```

## DVLResult Fields

| Field | Type | Description |
|---|---|---|
| `verified_value` | `float` | The corrected value |
| `trust_score` | `str` | `HIGH` / `MEDIUM` / `LOW` |
| `trust_color` | `str` | Hex color for UI rendering |
| `corrections` | `list[dict]` | Audit log of all corrections |
| `was_corrected` | `bool` | Whether any correction was applied |
| `correction_summary` | `str\|None` | e.g. `"scale_mul100 → sign_corrected"` |
| `delta_pct` | `float` | Percentage change from raw to verified |

## API Reference

**Default API endpoint:** `https://aadi2026-finverify-api.hf.space`

```
POST /v1/verify
{
  "question": "What was the profit margin?",
  "raw_value": 0.2531,
  "model_source": "gpt-4"  // optional
}
→ {
  "verified_value": 25.31,
  "trust_score": "MEDIUM",
  "correction_applied": "scale_mul100",
  "delta_pct": 9902.7678,
  "dvl_version": "1.0.0",
  "timestamp": "2026-05-22T12:00:00+00:00"
}
```

Rate limit: 100 requests/minute per IP.

## Research

Based on: *Modular Verification Outperforms Chain-of-Thought Reasoning in Small Financial LLMs*

- **42× accuracy** improvement on FinQA (1.00% → 42.61%)
- Evaluated on n=873 samples with 95% bootstrap confidence intervals
- [Live demo](https://finverify-llm.vercel.app) · [HuggingFace model](https://huggingface.co/aadi2026/finverify-lora)

## License

MIT
