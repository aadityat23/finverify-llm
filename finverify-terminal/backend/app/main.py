"""
FastAPI Backend — FinVerify Terminal
====================================
Endpoints:
  POST /query                       — LLM inference + DVL verification
  POST /verify                      — DVL-only verification (no LLM call)
  POST /v1/verify                   — Standalone DVL API (rate-limited, public)
  GET  /health                      — Health check
  GET  /sample-queries              — Hardcoded sample questions
  GET  /market/quotes               — Live stock quotes
  GET  /market/indices              — Market index data
  GET  /market/verified-metrics     — DVL-verified financial metric
  GET  /market/metrics              — Alias for verified-metrics
  GET  /market/all-metrics          — All metrics for a symbol
  GET  /v1/fundamentals/{ticker}    — SEC filing metrics with DVL verification
  GET  /v1/earnings/{ticker}        — Earnings transcript verification report
  POST /v1/ingest/sec               — Trigger SEC EDGAR ingestion
  POST /v1/ingest/transcripts       — Trigger transcript ingestion
  WS   /ws/market                   — Real-time market data stream (5s interval)
"""

import os
import json
import asyncio
import logging
from datetime import datetime, timezone
from typing import Optional

import httpx
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect, Query, Request
from fastapi.middleware.cors import CORSMiddleware

# Rate limiting — optional import (graceful fallback)
RATE_LIMITING_AVAILABLE = False
_limiter = None
try:
    from slowapi import Limiter
    from slowapi.util import get_remote_address
    from slowapi.errors import RateLimitExceeded
    _limiter = Limiter(key_func=get_remote_address, default_limits=["100/minute"])
    RATE_LIMITING_AVAILABLE = True
except (ImportError, Exception) as _import_err:
    logging.getLogger(__name__).warning("slowapi not available — rate limiting disabled: %s", _import_err)

from .models import (
    QueryRequest,
    VerifyRequest,
    QueryResponse,
    HealthResponse,
    SampleQuery,
    V1VerifyRequest,
    V1VerifyResponse,
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
    version="1.2.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*", "X-FinVerify-Key"],
)

# Attach rate limiter if available
if RATE_LIMITING_AVAILABLE and _limiter is not None:
    app.state.limiter = _limiter
    try:
        from slowapi.middleware import SlowAPIMiddleware
        app.add_middleware(SlowAPIMiddleware)
    except ImportError:
        pass

    from starlette.responses import JSONResponse as _JSONResp

    @app.exception_handler(RateLimitExceeded)
    async def _rate_limit_handler(request: Request, exc: RateLimitExceeded):
        return _JSONResp(
            status_code=429,
            content={"detail": "Rate limit exceeded — 100 requests/minute. Please slow down."},
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


# ---------------------------------------------------------------------------
# V1 Standalone DVL API
# ---------------------------------------------------------------------------

@app.post("/v1/verify", response_model=V1VerifyResponse)
async def v1_verify_endpoint(req: V1VerifyRequest, request: Request):
    """
    Standalone DVL verification API.
    Any application can POST a question + raw_value and receive
    a verified result with trust score, correction info, and timestamp.

    Rate limited: 100 requests/minute per IP.
    Optional X-FinVerify-Key header for tracking (not enforced).
    """
    # Log API key if provided
    api_key = request.headers.get("X-FinVerify-Key", None)
    if api_key:
        logger.info("V1 verify called with API key: %s...", api_key[:8])
    else:
        logger.info("V1 verify called (no API key)")

    # Log model source if provided
    if req.model_source:
        logger.info("Model source: %s", req.model_source)

    # Run DVL pipeline
    verified_value, correction_log, trust_label, trust_color = full_verify(
        question=req.question,
        predicted=req.raw_value,
        actual=None,  # No ground truth in standalone mode
    )

    # Compute delta percentage
    delta_pct = 0.0
    if req.raw_value != 0:
        delta_pct = round(
            abs(verified_value - req.raw_value) / abs(req.raw_value) * 100, 4
        )

    # Determine correction applied
    correction_applied = None
    if correction_log:
        correction_applied = " → ".join(entry["rule"] for entry in correction_log)

    return V1VerifyResponse(
        question=req.question,
        raw_value=req.raw_value,
        verified_value=verified_value,
        correction_applied=correction_applied,
        trust_score=trust_label,
        trust_color=trust_color,
        delta_pct=delta_pct,
        dvl_version="1.0.0",
        timestamp=datetime.now(timezone.utc).isoformat(),
    )


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


# ---------------------------------------------------------------------------
# SEC EDGAR Fundamentals & Earnings Verification
# ---------------------------------------------------------------------------

@app.get("/v1/fundamentals/{ticker}")
async def get_fundamentals(ticker: str):
    """
    Get DVL-verified fundamental metrics from SEC EDGAR filings.
    Replaces hardcoded FALLBACK_METRICS on the frontend.
    
    If data is not yet ingested, triggers on-demand ingestion
    using fallback filing data (instant, no SEC API call).
    """
    ticker = ticker.upper()

    # Try to get from database first
    try:
        from ingestion.db import get_fundamentals as db_get_fundamentals
        metrics = db_get_fundamentals(ticker)
        if metrics:
            return {
                "ticker": ticker,
                "source": "sec_edgar",
                "metrics_count": len(metrics),
                "metrics": metrics,
            }
    except Exception as e:
        logger.warning("DB read failed for %s: %s", ticker, e)

    # On-demand ingestion if nothing in DB
    try:
        from ingestion.sec_edgar import ingest_ticker
        results = ingest_ticker(ticker)
        return {
            "ticker": ticker,
            "source": "sec_edgar_fresh",
            "metrics_count": len(results),
            "metrics": results,
        }
    except Exception as e:
        logger.error("Fundamentals ingestion failed for %s: %s", ticker, e)
        raise HTTPException(status_code=500, detail=f"Failed to fetch fundamentals: {e}")


@app.get("/v1/earnings/{ticker}")
async def get_earnings_verification(ticker: str):
    """
    Get earnings call transcript verification report.
    Returns DVL-verified numeric claims with Red Flag analysis.
    
    This is the killer demo feature — shows DVL catching
    real-world ambiguity in CEO/CFO earnings statements.
    """
    ticker = ticker.upper()

    try:
        from ingestion.transcripts import demo_transcript_verification
        report = demo_transcript_verification(ticker, store=True)
        return report
    except Exception as e:
        logger.error("Earnings verification failed for %s: %s", ticker, e)
        raise HTTPException(status_code=500, detail=f"Earnings verification failed: {e}")


@app.post("/v1/ingest/sec")
async def trigger_sec_ingestion(
    tickers: Optional[str] = Query(default=None, description="Comma-separated tickers")
):
    """
    Trigger SEC EDGAR filing ingestion for watchlist companies.
    If no tickers specified, ingests all 6 watchlist companies.
    """
    try:
        from ingestion.sec_edgar import ingest_all, ingest_ticker
        if tickers:
            ticker_list = [t.strip().upper() for t in tickers.split(",")]
            results = {}
            for t in ticker_list:
                results[t] = ingest_ticker(t)
            return {"status": "ok", "results": results}
        else:
            summary = ingest_all()
            return {"status": "ok", "summary": summary}
    except Exception as e:
        logger.error("SEC ingestion failed: %s", e)
        raise HTTPException(status_code=500, detail=f"Ingestion failed: {e}")


@app.post("/v1/ingest/transcripts")
async def trigger_transcript_ingestion(
    tickers: Optional[str] = Query(default=None, description="Comma-separated tickers")
):
    """
    Trigger earnings transcript verification for watchlist companies.
    """
    try:
        from ingestion.transcripts import ingest_all_transcripts, demo_transcript_verification
        if tickers:
            ticker_list = [t.strip().upper() for t in tickers.split(",")]
            results = {}
            for t in ticker_list:
                results[t] = demo_transcript_verification(t, store=True)
            return {"status": "ok", "results": results}
        else:
            summary = ingest_all_transcripts()
            return {"status": "ok", "summary": summary}
    except Exception as e:
        logger.error("Transcript ingestion failed: %s", e)
        raise HTTPException(status_code=500, detail=f"Ingestion failed: {e}")


# ═══════════════════════════════════════════════════════════════════
# RAG — Vector search endpoints
# ═══════════════════════════════════════════════════════════════════

@app.get("/v1/rag/stats")
async def rag_stats():
    """Get RAG index statistics."""
    try:
        from rag.pipeline import get_index_stats
        return get_index_stats()
    except Exception as e:
        return {"backend": "unavailable", "error": str(e)}


@app.post("/v1/rag/query")
async def rag_query(request: Request):
    """Query the RAG index for relevant context."""
    try:
        body = await request.json()
        question = body.get("question", "")
        top_k = min(body.get("top_k", 5), 20)

        from rag.pipeline import query as rag_search
        results = rag_search(question, top_k=top_k)
        return {
            "question": question,
            "results": results,
            "count": len(results),
        }
    except Exception as e:
        logger.error("RAG query failed: %s", e)
        raise HTTPException(status_code=500, detail=f"RAG query failed: {e}")


@app.post("/v1/rag/seed")
async def rag_seed():
    """Trigger RAG index seeding from SQLite data."""
    try:
        from rag.seed import main as run_seed
        run_seed()
        from rag.pipeline import get_index_stats
        return {"status": "ok", "stats": get_index_stats()}
    except Exception as e:
        logger.error("RAG seeding failed: %s", e)
        raise HTTPException(status_code=500, detail=f"Seeding failed: {e}")


# ═══════════════════════════════════════════════════════════════════
# Query History — Supabase Persistence (Session 12A)
# ═══════════════════════════════════════════════════════════════════

@app.get("/v1/history/{user_id}")
async def get_history(
    user_id: str,
    limit: int = Query(default=20, le=100),
    trust: Optional[str] = Query(default=None, description="Filter by trust: HIGH, MEDIUM, LOW"),
):
    """
    Get query history for an authenticated user.
    History is a 'sign in to save' feature — anonymous mode still works.
    """
    try:
        from .supabase_client import get_user_history
        entries = get_user_history(user_id, limit=limit, trust_filter=trust)
        return {"user_id": user_id, "count": len(entries), "entries": entries}
    except Exception as e:
        logger.error("History fetch failed for %s: %s", user_id, e)
        return {"user_id": user_id, "count": 0, "entries": [], "error": str(e)}


@app.post("/v1/history")
async def save_history(request: Request):
    """
    Save a query result to persistent history.
    Expects: { user_id, question, raw_value, verified_value, trust, display_value, correction_log }
    """
    try:
        body = await request.json()
        user_id = body.get("user_id")
        if not user_id:
            raise HTTPException(status_code=400, detail="user_id required")

        from .supabase_client import save_query
        result = save_query(
            user_id=user_id,
            question=body.get("question", ""),
            raw_value=body.get("raw_value"),
            verified_value=body.get("verified_value"),
            trust=body.get("trust", "HIGH"),
            display_value=body.get("display_value", ""),
            correction_log=body.get("correction_log", []),
        )
        return {"status": "ok", "saved": result is not None}
    except HTTPException:
        raise
    except Exception as e:
        logger.error("History save failed: %s", e)
        return {"status": "error", "error": str(e)}


@app.delete("/v1/history/{user_id}")
async def clear_history(user_id: str):
    """Delete all history for a user."""
    try:
        from .supabase_client import delete_user_history
        success = delete_user_history(user_id)
        return {"status": "ok" if success else "error", "cleared": success}
    except Exception as e:
        logger.error("History clear failed for %s: %s", user_id, e)
        return {"status": "error", "error": str(e)}


# ═══════════════════════════════════════════════════════════════════
# Financial Constraint Graph — Multi-Number Verification (Session 1A)
# ═══════════════════════════════════════════════════════════════════

@app.post("/v1/fcg/verify")
async def fcg_verify(request: Request):
    """
    Run Financial Constraint Graph verification on a set of financial values.

    Expects JSON body:
    {
        "values": {
            "revenue": 394328,
            "cogs": 223546,
            "gross_profit": 170782,
            "operating_expenses": 54847,
            "operating_income": 115935,
            ...
        }
    }

    Returns constraint results: passed, violations, and overall trust.
    This is the second-pass verification layer — runs AFTER DVL single-number correction.
    Pipeline: LLM Output → DVL (single-number) → FCG (relationships) → Trust Score
    """
    try:
        body = await request.json()
        values = body.get("values", {})

        if not values:
            raise HTTPException(status_code=400, detail="'values' dict required with financial metrics")

        # Ensure all values are floats
        float_values = {}
        for k, v in values.items():
            try:
                float_values[k] = float(v)
            except (TypeError, ValueError):
                continue  # skip non-numeric values

        if not float_values:
            raise HTTPException(status_code=400, detail="No valid numeric values found")

        from fcg.constraint_engine import fcg
        result = fcg.verify(float_values)

        return {
            "status": "ok",
            "input_count": len(float_values),
            "constraint_result": fcg.to_dict(result),
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error("FCG verification failed: %s", e)
        raise HTTPException(status_code=500, detail=f"FCG verification failed: {e}")


@app.get("/v1/fcg/constraints")
async def list_constraints():
    """List all available FCG constraints and their tolerances."""
    from fcg.constraint_engine import FinancialConstraintGraph

    constraints = []
    for c in FinancialConstraintGraph.HARD_CONSTRAINTS:
        constraints.append({
            "id": c["id"],
            "name": c["name"],
            "description": c["description"],
            "requires": list(c["requires"]),
            "tolerance_pct": c["tolerance"] * 100,
            "severity": "HARD",
        })
    for c in FinancialConstraintGraph.SOFT_CONSTRAINTS:
        constraints.append({
            "id": c["id"],
            "name": c["name"],
            "description": c["description"],
            "requires": list(c["requires"]),
            "tolerance_pct": c["tolerance"] * 100,
            "severity": "SOFT",
        })

    return {
        "total": len(constraints),
        "hard": len(FinancialConstraintGraph.HARD_CONSTRAINTS),
        "soft": len(FinancialConstraintGraph.SOFT_CONSTRAINTS),
        "constraints": constraints,
    }
