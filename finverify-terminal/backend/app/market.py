"""
Market Data Module — FinVerify Terminal
========================================
Fetches live market data via yfinance (Yahoo Finance unofficial API).
Provides quotes, indices, and DVL-verified financial metrics.

IMPORTANT RULES:
  - NEVER run DVL on raw stock prices (price, volume, market_cap) — ground truth
  - ONLY run DVL on DERIVED financial metrics (ratios, margins, growth rates)
  - Rate limit: max 1 yfinance call per symbol per 10 seconds (in-memory cache)
  - If yfinance fails, return cached last-known value with a "stale" flag
"""

import time
import logging
import threading
from typing import Optional

import yfinance as yf

from .dvl import full_verify, format_correction_log

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# In-memory cache  (thread-safe via lock)
# ---------------------------------------------------------------------------

_lock = threading.Lock()
_cache: dict[str, dict] = {}          # symbol → {data, timestamp}
_info_cache: dict[str, dict] = {}     # symbol → {info_dict, timestamp}
CACHE_TTL = 10                         # seconds — rate limit per symbol

DEFAULT_WATCHLIST = ["AAPL", "TSLA", "JPM", "NVDA", "MSFT", "GS"]
ALL_SYMBOLS = ["AAPL", "TSLA", "JPM", "NVDA", "MSFT", "GOOGL", "GS", "BAC", "WFC", "C"]
INDEX_SYMBOLS = ["SPY", "QQQ", "^VIX"]

METRIC_MAP = {
    "pe_ratio": {
        "key": "trailingPE",
        "label": "P/E Ratio",
        "question": "What is {symbol}'s P/E ratio?",
    },
    "profit_margin": {
        "key": "profitMargins",
        "label": "Profit Margin",
        "question": "What is {symbol}'s profit margin?",
    },
    "revenue_growth": {
        "key": "revenueGrowth",
        "label": "Revenue Growth",
        "question": "What is {symbol}'s revenue growth rate?",
    },
    "roe": {
        "key": "returnOnEquity",
        "label": "Return on Equity",
        "question": "What is {symbol}'s return on equity?",
    },
    "debt_to_equity": {
        "key": "debtToEquity",
        "label": "Debt to Equity",
        "question": "What is {symbol}'s debt to equity ratio?",
    },
}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _is_stale(symbol: str, cache: dict) -> bool:
    """Check if cached data is older than CACHE_TTL."""
    entry = cache.get(symbol)
    if not entry:
        return True
    return (time.time() - entry.get("timestamp", 0)) > CACHE_TTL


def _safe_get(obj, *keys, default=0):
    """
    Safely extract a value from an object that may support dict-style or
    attribute-style access (yfinance fast_info changed between versions).
    Tries each key in order; returns default if none found.
    """
    for key in keys:
        # Dict-style
        if isinstance(obj, dict):
            val = obj.get(key)
            if val is not None:
                return val
        else:
            # Attribute-style (yfinance fast_info in newer versions)
            try:
                val = getattr(obj, key, None)
                if val is not None:
                    return val
            except Exception:
                pass
            # Also try dict-style on non-dict objects (some versions support both)
            try:
                val = obj[key]
                if val is not None:
                    return val
            except (KeyError, TypeError, IndexError):
                pass
    return default


def _get_ticker_fast(symbol: str) -> Optional[dict]:
    """
    Get fast quote data for a symbol with caching.
    Returns dict with price, prev_close, change, change_pct, volume, market_cap.
    Respects 10-second rate limit per symbol.
    """
    with _lock:
        if not _is_stale(symbol, _cache):
            return {**_cache[symbol]["data"], "stale": False}

    try:
        ticker = yf.Ticker(symbol)

        # ── Try fast_info first (lightweight call) ──
        try:
            fi = ticker.fast_info
            price = float(_safe_get(fi, "lastPrice", "last_price", "regularMarketPrice", default=0))
            prev_close = float(_safe_get(fi, "previousClose", "previous_close", "regularMarketPreviousClose", default=0))
            volume = int(_safe_get(fi, "lastVolume", "last_volume", "regularMarketVolume", default=0))
            market_cap = int(_safe_get(fi, "marketCap", "market_cap", default=0))
        except Exception:
            price = prev_close = 0
            volume = market_cap = 0

        # ── Fallback to full .info if fast_info returned zeros ──
        if price == 0 and prev_close == 0:
            try:
                full_info = ticker.info or {}
                price = float(full_info.get("currentPrice", 0)
                              or full_info.get("regularMarketPrice", 0)
                              or full_info.get("navPrice", 0) or 0)
                prev_close = float(full_info.get("previousClose", 0)
                                   or full_info.get("regularMarketPreviousClose", 0) or 0)
                if volume == 0:
                    volume = int(full_info.get("volume", 0)
                                 or full_info.get("regularMarketVolume", 0) or 0)
                if market_cap == 0:
                    market_cap = int(full_info.get("marketCap", 0) or 0)
            except Exception as e:
                logger.debug("full .info fallback also failed for %s: %s", symbol, e)

        # ── Compute derived fields ──
        change = round(price - prev_close, 2) if prev_close else 0.0
        change_pct = round((change / prev_close) * 100, 2) if prev_close else 0.0

        data = {
            "symbol": symbol,
            "price": round(price, 2),
            "prev_close": round(prev_close, 2),
            "change": change,
            "change_pct": change_pct,
            "volume": volume,
            "market_cap": market_cap,
        }

        with _lock:
            _cache[symbol] = {"data": data, "timestamp": time.time()}
        return {**data, "stale": False}

    except Exception as e:
        logger.warning("yfinance quote failed for %s: %s", symbol, e)
        # Return cached value if available
        with _lock:
            if symbol in _cache:
                return {**_cache[symbol]["data"], "stale": True}
        # Return zeros as ultimate fallback
        return {
            "symbol": symbol, "price": 0, "prev_close": 0,
            "change": 0, "change_pct": 0, "volume": 0, "market_cap": 0,
            "stale": True,
        }


def _get_info(symbol: str) -> dict:
    """
    Get full .info dict with caching (slower call — separate cache).
    Used for derived financial metrics only.
    """
    with _lock:
        if not _is_stale(symbol, _info_cache):
            return _info_cache[symbol]["data"]

    try:
        ticker = yf.Ticker(symbol)
        info = ticker.info or {}
        with _lock:
            _info_cache[symbol] = {"data": info, "timestamp": time.time()}
        return info
    except Exception as e:
        logger.warning("yfinance info failed for %s: %s", symbol, e)
        with _lock:
            if symbol in _info_cache:
                return _info_cache[symbol]["data"]
        return {}


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def get_quotes(symbols: list[str]) -> list[dict]:
    """
    Get quotes for a list of symbols.
    Returns: list of {symbol, price, prev_close, change, change_pct, volume, market_cap, stale}
    DVL is NOT applied — these are ground-truth market prices.
    """
    return [_get_ticker_fast(s) for s in symbols]


def get_market_indices() -> list[dict]:
    """
    Get S&P 500 (SPY proxy), NASDAQ (QQQ proxy), VIX.
    Returns: list of {symbol, display_name, price, change, change_pct, ...}
    """
    display_names = {"SPY": "S&P 500", "QQQ": "NASDAQ", "^VIX": "VIX"}
    results = []
    for sym in INDEX_SYMBOLS:
        q = _get_ticker_fast(sym)
        if q:
            q["display_name"] = display_names.get(sym, sym)
        results.append(q)
    return results


def compute_financial_metric(symbol: str, metric_type: str) -> dict:
    """
    Fetch a DERIVED financial metric and run it through DVL for verification.

    DVL ONLY runs on derived metrics (ratios, margins, growth rates) — never
    on raw prices/volume/market_cap which are ground truth.

    Returns dict with: symbol, metric, label, raw_value, question_text,
                       verified_value, correction_log, trust_score, trust_color
    """
    if metric_type not in METRIC_MAP:
        return {"error": f"Unknown metric: {metric_type}. Valid: {list(METRIC_MAP.keys())}"}

    meta = METRIC_MAP[metric_type]
    info = _get_info(symbol)
    stale = False

    # Check if we got stale info (empty dict from cache fallback)
    if not info:
        stale = True

    raw_value = info.get(meta["key"])
    question_text = meta["question"].format(symbol=symbol)

    if raw_value is None:
        return {
            "symbol": symbol,
            "metric": metric_type,
            "label": meta["label"],
            "raw_value": None,
            "question_text": question_text,
            "verified_value": None,
            "correction_log": [],
            "trust_score": "N/A",
            "trust_color": "#888888",
            "stale": stale,
        }

    raw_value = float(raw_value)

    # ── Run through DVL ──
    verified, logs, trust_score, trust_color = full_verify(question_text, raw_value)
    formatted_log = format_correction_log(logs)

    return {
        "symbol": symbol,
        "metric": metric_type,
        "label": meta["label"],
        "raw_value": raw_value,
        "question_text": question_text,
        "verified_value": verified,
        "correction_log": formatted_log,
        "trust_score": trust_score,
        "trust_color": trust_color,
        "stale": stale,
    }


def get_all_metrics(symbol: str) -> list[dict]:
    """Get all 5 DVL-verified financial metrics for a symbol."""
    return [compute_financial_metric(symbol, m) for m in METRIC_MAP]
