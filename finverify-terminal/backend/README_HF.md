---
title: FinVerify API
emoji: 📊
colorFrom: green
colorTo: black
sdk: docker
pinned: false
app_port: 7860
---

# FinVerify Terminal API

FastAPI backend for the FinVerify Terminal — a Bloomberg-dark financial LLM verification system with a Deterministic Verification Layer (DVL) engine.

## Modes

| Mode | HF_TOKEN | DVL | LLM |
|------|----------|-----|-----|
| **DVL-only** | ❌ Not set | ✅ Online | ❌ Offline |
| **Full** | ✅ Set | ✅ Online | ✅ Online |

## Routes

| Method | Path | Description | Requires Token |
|--------|------|-------------|----------------|
| POST | `/query` | LLM inference + DVL verification | ✅ Yes |
| POST | `/verify` | DVL-only verification (no LLM call) | ❌ No |
| GET | `/health` | Health check | ❌ No |
| GET | `/sample-queries` | Sample questions from the paper | ❌ No |
| GET | `/market/quotes` | Live stock quotes via yfinance | ❌ No |
| GET | `/market/indices` | S&P 500, NASDAQ, VIX index data | ❌ No |
| GET | `/market/verified-metrics` | DVL-verified financial metrics | ❌ No |
| GET | `/market/all-metrics` | All 5 metrics for a symbol | ❌ No |
| WS | `/ws/market` | Real-time market data stream (5s) | ❌ No |

## DVL Engine

Corrects scale, sign, and magnitude errors in LLM numerical outputs.  
Validated on FinQA dev set (n=873) achieving **42.61% accuracy** — a **42× improvement** over baseline.

## Model

[aadi2026/finverify-lora](https://huggingface.co/aadi2026/finverify-lora) — Mistral-7B + QLoRA (4-bit NF4)
