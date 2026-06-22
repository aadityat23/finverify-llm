"""
Supabase Client — Query History Persistence
=============================================
Connects to Supabase (free tier) for storing user query history.
Falls back gracefully if SUPABASE_URL / SUPABASE_KEY are not set.

Table schema (create in Supabase SQL editor):
  CREATE TABLE query_history (
    id          uuid DEFAULT gen_random_uuid() PRIMARY KEY,
    user_id     text NOT NULL,
    question    text NOT NULL,
    raw_value   double precision,
    verified_value double precision,
    trust       text NOT NULL DEFAULT 'HIGH',
    display_value text,
    correction_log jsonb DEFAULT '[]'::jsonb,
    timestamp   timestamptz DEFAULT now()
  );

  CREATE INDEX idx_query_history_user ON query_history(user_id);
  CREATE INDEX idx_query_history_trust ON query_history(trust);
"""

import os
import logging
from typing import Optional

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Supabase connection (lazy init)
# ---------------------------------------------------------------------------

_client = None
SUPABASE_AVAILABLE = False

SUPABASE_URL = os.getenv("SUPABASE_URL", "")
SUPABASE_KEY = os.getenv("SUPABASE_KEY", "")


def _get_client():
    """Lazy-initialize Supabase client."""
    global _client, SUPABASE_AVAILABLE
    if _client is not None:
        return _client
    if not SUPABASE_URL or not SUPABASE_KEY:
        logger.info("Supabase not configured — history stored locally only")
        return None
    try:
        from supabase import create_client
        _client = create_client(SUPABASE_URL, SUPABASE_KEY)
        SUPABASE_AVAILABLE = True
        logger.info("Supabase client initialized")
        return _client
    except ImportError:
        logger.warning("supabase-py not installed — pip install supabase")
        return None
    except Exception as e:
        logger.error("Supabase init failed: %s", e)
        return None


# ---------------------------------------------------------------------------
# CRUD Operations
# ---------------------------------------------------------------------------

def save_query(
    user_id: str,
    question: str,
    raw_value: Optional[float],
    verified_value: Optional[float],
    trust: str,
    display_value: str,
    correction_log: list,
) -> Optional[dict]:
    """Save a query result to Supabase. Returns the inserted row or None."""
    client = _get_client()
    if client is None:
        return None
    try:
        row = {
            "user_id": user_id,
            "question": question,
            "raw_value": raw_value,
            "verified_value": verified_value,
            "trust": trust,
            "display_value": display_value,
            "correction_log": correction_log,
        }
        result = client.table("query_history").insert(row).execute()
        return result.data[0] if result.data else None
    except Exception as e:
        logger.error("Failed to save query: %s", e)
        return None


def get_user_history(
    user_id: str,
    limit: int = 20,
    trust_filter: Optional[str] = None,
) -> list:
    """Fetch query history for a user. Optionally filter by trust level."""
    client = _get_client()
    if client is None:
        return []
    try:
        query = (
            client.table("query_history")
            .select("*")
            .eq("user_id", user_id)
            .order("timestamp", desc=True)
            .limit(limit)
        )
        if trust_filter and trust_filter in ("HIGH", "MEDIUM", "LOW"):
            query = query.eq("trust", trust_filter)
        result = query.execute()
        return result.data or []
    except Exception as e:
        logger.error("Failed to fetch history: %s", e)
        return []


def delete_user_history(user_id: str) -> bool:
    """Delete all history for a user."""
    client = _get_client()
    if client is None:
        return False
    try:
        client.table("query_history").delete().eq("user_id", user_id).execute()
        return True
    except Exception as e:
        logger.error("Failed to delete history: %s", e)
        return False
