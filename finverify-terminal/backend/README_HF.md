---
title: FinVerify Terminal API
emoji: 📊
colorFrom: green
colorTo: black
sdk: docker
pinned: false
---

# FinVerify Terminal API

FastAPI backend for the FinVerify Terminal — a Bloomberg-dark financial LLM verification system with a Deterministic Verification Layer (DVL) engine.

## Routes

| Method | Path | Description |
|--------|------|-------------|
| POST | `/query` | LLM inference + DVL verification |
| POST | `/verify` | DVL-only verification (no LLM call) |
| GET | `/health` | Health check |
| GET | `/sample-queries` | Sample questions from the paper |
| GET | `/market/quotes` | Live stock quotes via yfinance |
| GET | `/market/indices` | S&P 500, NASDAQ, VIX index data |
| GET | `/market/verified-metrics` | DVL-verified financial metrics |
| GET | `/market/all-metrics` | All 5 metrics for a symbol |
| WS | `/ws/market` | Real-time market data stream (5s) |

## DVL Engine

Corrects scale, sign, and magnitude errors in LLM numerical outputs.  
Validated on FinQA dev set (n=873) achieving **42.61% accuracy** — a **42× improvement** over baseline.

## Model

[aadi2026/finverify-lora](https://huggingface.co/aadi2026/finverify-lora) — Mistral-7B + QLoRA (4-bit NF4)
