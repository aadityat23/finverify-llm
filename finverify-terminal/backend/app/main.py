"""
FastAPI Backend — FinVerify Terminal
====================================
Endpoints:
  POST /query                       — LLM inference + DVL verification
  POST /verify                      — DVL-only verification (no LLM call)
  GET  /health                      — Health check
  GET  /sample-queries              — Hardcoded sample questions
  GET  /market/quotes               — Live stock quotes
  GET  /market/indices              — Market index data
  GET  /market/verified-metrics     — DVL-verified financial metric
  GET  /market/metrics              — Alias for verified-metrics
  GET  /market/all-metrics          — All metrics for a symbol
  WS   /ws/market                   — Real-time market data stream (5s interval)
"""

import os
import json
import asyncio
import logging
from typing import Optional

import httpx
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect, Query
from fastapi.middleware.cors import CORSMiddleware

from .models import (
    QueryRequest,
    VerifyRequest,
    QueryResponse,
    HealthResponse,
    SampleQuery,
)
from .parser import clean_llm_output, format_number_display
from .dvl import full_verify, format_correction_log
from .models import CorrectionEntry
from .evaluator import build_query_response
from .router import classify_query
from .market import (
    get_quotes,
    get_market_indices,
    compute_financial_metric,
    get_all_metrics,
    DEFAULT_WATCHLIST,
)

load_dotenv()
logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# App
# ---------------------------------------------------------------------------

app = FastAPI(
    title="FinVerify Terminal API",
    description="Bloomberg-dark financial LLM verification system with DVL engine",
    version="1.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------------------------------------------------------------------
# HuggingFace Inference
# ---------------------------------------------------------------------------

HF_MODEL = "aadi2026/finverify-lora"
HF_API_URL = f"https://api-inference.huggingface.co/models/{HF_MODEL}"
_raw_token = os.getenv("HF_TOKEN", None)
HF_TOKEN: str | None = _raw_token if _raw_token else None
LLM_AVAILABLE: bool = HF_TOKEN is not None

logger.info("HF_TOKEN %s — LLM mode: %s",
            "detected" if LLM_AVAILABLE else "NOT SET",
            "full" if LLM_AVAILABLE else "dvl-only")


async def call_hf_inference(question: str) -> str:
    """Call HuggingFace Inference API and return raw text."""
    headers = {"Authorization": f"Bearer {HF_TOKEN}"}
    payload = {
        "inputs": f"Question: {question}\nAnswer:",
        "parameters": {
            "max_new_tokens": 50,
            "do_sample": False,
        },
    }

    async with httpx.AsyncClient(timeout=60.0) as client:
        resp = await client.post(HF_API_URL, json=payload, headers=headers)

    if resp.status_code != 200:
        raise HTTPException(
            status_code=resp.status_code,
            detail=f"HuggingFace API error: {resp.text}",
        )

    data = resp.json()
    # HF returns a list of dicts: [{"generated_text": "..."}]
    if isinstance(data, list) and len(data) > 0:
        return data[0].get("generated_text", "")
    return str(data)


# ---------------------------------------------------------------------------
# DVL Routes
# ---------------------------------------------------------------------------

@app.post("/query")
async def query_endpoint(req: QueryRequest):
    """Full pipeline: classify -> LLM -> parse -> DVL -> response."""

    # --- If no HF token, return graceful offline response ---------------
    if not LLM_AVAILABLE:
        return {
            "error": "LLM offline",
            "mode": "dvl_only",
            "message": "DVL verification available. LLM inference requires API token.",
        }

    mode = classify_query(req.question)

    # Advisory queries — skip DVL entirely
    if mode == "advisory":
        try:
            raw_text = await call_hf_inference(req.question)
        except Exception:
            raw_text = (
                "Advisory queries are not verified by the DVL engine. "
                "This response is unverified LLM output."
            )
        return QueryResponse(
            question=req.question,
            raw_text=raw_text,
            raw_number=None,
            verified_number=None,
            correction_log=[],
            trust_score="N/A",
            trust_color="#888888",
            display_value="Advisory — not verified",
            mode=mode,
            verified=False,
        )

    # Numerical / general queries — full pipeline
    try:
        raw_text = await call_hf_inference(req.question)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"LLM inference failed: {e}")

    cleaned, raw_number = clean_llm_output(raw_text)
    resp = build_query_response(
        question=req.question,
        raw_text=raw_text,
        raw_number=raw_number,
    )
    resp.mode = mode
    resp.verified = mode == "numerical" and resp.trust_score != "N/A"
    return resp


@app.post("/verify", response_model=QueryResponse)
async def verify_endpoint(req: VerifyRequest):
    """DVL-only verification — no LLM call."""
    resp = build_query_response(
        question=req.question,
        raw_text=None,
        raw_number=req.raw_number,
    )
    resp.mode = classify_query(req.question)
    resp.verified = True
    return resp


@app.get("/health")
async def health():
    """Health check — reports DVL and LLM availability."""
    if LLM_AVAILABLE:
        return {
            "status": "ok",
            "dvl": "online",
            "llm": "online",
            "model": HF_MODEL,
        }
    return {
        "status": "ok",
        "dvl": "online",
        "llm": "offline",
        "model": "dvl-only-mode",
    }


@app.get("/sample-queries", response_model=list[SampleQuery])
async def sample_queries():
    """Hardcoded sample questions from the paper's failure-case analysis."""
    return [
        SampleQuery(
            question="What was JPMorgan's CET1 ratio change?",
            actual=0.10935,
            category="ratio",
        ),
        SampleQuery(
            question="What was the increase in Class A shares outstanding?",
            actual=995.0,
            category="magnitude",
        ),
        SampleQuery(
            question="What was the percentage decrease in HTM securities?",
            actual=0.34146,
            category="sign",
        ),
        SampleQuery(
            question="What was Apple's YoY revenue growth rate?",
            actual=None,
            category="ratio",
        ),
        SampleQuery(
            question="What was the operating margin change?",
            actual=None,
            category="ratio",
        ),
        SampleQuery(
            question="What was the net income increase?",
            actual=None,
            category="magnitude",
        ),
    ]


# ---------------------------------------------------------------------------
# Market Data Routes
# ---------------------------------------------------------------------------

@app.get("/market/quotes")
async def market_quotes(symbols: str = Query(default=",".join(DEFAULT_WATCHLIST))):
    """Get live quotes for given symbols (comma-separated)."""
    symbol_list = [s.strip().upper() for s in symbols.split(",") if s.strip()]
    return get_quotes(symbol_list)


@app.get("/market/indices")
async def market_indices():
    """Get S&P 500, NASDAQ, VIX index data."""
    return get_market_indices()


@app.get("/market/verified-metrics")
async def market_verified_metrics(
    symbol: str = Query(default="AAPL"),
    metric: str = Query(default="profit_margin"),
):
    """Get a DVL-verified financial metric for a symbol."""
    return compute_financial_metric(symbol.upper(), metric)


# Backward-compat alias
@app.get("/market/metrics")
async def market_metrics_alias(
    symbol: str = Query(default="AAPL"),
    metric: str = Query(default="profit_margin"),
):
    """Alias for /market/verified-metrics."""
    return compute_financial_metric(symbol.upper(), metric)


@app.get("/market/all-metrics")
async def market_all_metrics(symbol: str = Query(default="AAPL")):
    """Get all DVL-verified financial metrics for a symbol."""
    return get_all_metrics(symbol.upper())


# ---------------------------------------------------------------------------
# WebSocket — Real-time market data
# ---------------------------------------------------------------------------

@app.websocket("/ws/market")
async def websocket_market(websocket: WebSocket):
    """Push live market quotes every 5 seconds."""
    await websocket.accept()
    logger.info("WebSocket client connected")

    try:
        while True:
            try:
                quotes = get_quotes(DEFAULT_WATCHLIST)
                await websocket.send_text(json.dumps(quotes))
            except Exception as e:
                logger.warning("WebSocket data fetch error: %s", e)
                await websocket.send_text(json.dumps({"error": str(e)}))
            await asyncio.sleep(5)
    except WebSocketDisconnect:
        logger.info("WebSocket client disconnected")
    except Exception as e:
        logger.warning("WebSocket error: %s", e)
