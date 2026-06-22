"""
SQLite Database — FinVerify Fundamentals Store
================================================
Stores SEC filing metrics and transcript verification claims.
Schema supports both raw + DVL-verified values for full audit trail.
"""

import sqlite3
import logging
from pathlib import Path
from datetime import datetime, timezone
from typing import Optional

logger = logging.getLogger(__name__)

DB_PATH = Path(__file__).resolve().parent.parent / "data" / "fundamentals.db"


def get_connection() -> sqlite3.Connection:
    """Get a SQLite connection, creating the DB and tables if needed."""
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    _init_tables(conn)
    return conn


def _init_tables(conn: sqlite3.Connection) -> None:
    """Create tables if they don't exist."""
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS fundamentals (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ticker TEXT NOT NULL,
            metric_name TEXT NOT NULL,
            raw_value REAL,
            verified_value REAL,
            period TEXT,
            filing_date TEXT,
            source_url TEXT,
            dvl_trust TEXT,
            dvl_color TEXT,
            dvl_rule TEXT,
            ingested_at TEXT NOT NULL,
            UNIQUE(ticker, metric_name, period)
        );

        CREATE TABLE IF NOT EXISTS transcript_claims (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ticker TEXT NOT NULL,
            sentence TEXT,
            claim_match TEXT,
            claim_type TEXT,
            raw_value REAL,
            verified_value REAL,
            dvl_question TEXT,
            dvl_rule TEXT,
            dvl_trust TEXT,
            dvl_color TEXT,
            flagged INTEGER DEFAULT 0,
            source TEXT,
            ingested_at TEXT NOT NULL
        );

        CREATE INDEX IF NOT EXISTS idx_fundamentals_ticker ON fundamentals(ticker);
        CREATE INDEX IF NOT EXISTS idx_claims_ticker ON transcript_claims(ticker);
        CREATE INDEX IF NOT EXISTS idx_claims_flagged ON transcript_claims(flagged);
    """)
    conn.commit()


def upsert_fundamental(
    ticker: str,
    metric_name: str,
    raw_value: float,
    verified_value: float,
    period: str,
    filing_date: str,
    source_url: str,
    dvl_trust: str,
    dvl_color: str,
    dvl_rule: Optional[str] = None,
) -> None:
    """Insert or update a fundamental metric."""
    conn = get_connection()
    try:
        conn.execute("""
            INSERT INTO fundamentals (ticker, metric_name, raw_value, verified_value,
                                      period, filing_date, source_url, dvl_trust,
                                      dvl_color, dvl_rule, ingested_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(ticker, metric_name, period) DO UPDATE SET
                raw_value=excluded.raw_value,
                verified_value=excluded.verified_value,
                filing_date=excluded.filing_date,
                source_url=excluded.source_url,
                dvl_trust=excluded.dvl_trust,
                dvl_color=excluded.dvl_color,
                dvl_rule=excluded.dvl_rule,
                ingested_at=excluded.ingested_at
        """, (
            ticker, metric_name, raw_value, verified_value,
            period, filing_date, source_url, dvl_trust,
            dvl_color, dvl_rule,
            datetime.now(timezone.utc).isoformat(),
        ))
        conn.commit()
    finally:
        conn.close()


def get_fundamentals(ticker: str) -> list[dict]:
    """Get all fundamental metrics for a ticker."""
    conn = get_connection()
    try:
        rows = conn.execute(
            "SELECT * FROM fundamentals WHERE ticker = ? ORDER BY metric_name, period DESC",
            (ticker.upper(),)
        ).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


def insert_transcript_claim(
    ticker: str,
    sentence: str,
    claim_match: str,
    claim_type: str,
    raw_value: float,
    verified_value: float,
    dvl_question: str,
    dvl_rule: Optional[str],
    dvl_trust: str,
    dvl_color: str,
    flagged: bool,
    source: str,
) -> None:
    """Insert a transcript claim verification record."""
    conn = get_connection()
    try:
        conn.execute("""
            INSERT INTO transcript_claims (ticker, sentence, claim_match, claim_type,
                                           raw_value, verified_value, dvl_question,
                                           dvl_rule, dvl_trust, dvl_color, flagged,
                                           source, ingested_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            ticker, sentence, claim_match, claim_type,
            raw_value, verified_value, dvl_question,
            dvl_rule, dvl_trust, dvl_color, int(flagged),
            source, datetime.now(timezone.utc).isoformat(),
        ))
        conn.commit()
    finally:
        conn.close()


def get_transcript_claims(ticker: str, flagged_only: bool = False) -> list[dict]:
    """Get transcript claims for a ticker."""
    conn = get_connection()
    try:
        if flagged_only:
            rows = conn.execute(
                "SELECT * FROM transcript_claims WHERE ticker = ? AND flagged = 1 ORDER BY id DESC",
                (ticker.upper(),)
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT * FROM transcript_claims WHERE ticker = ? ORDER BY id DESC",
                (ticker.upper(),)
            ).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


def clear_claims(ticker: str) -> None:
    """Clear all claims for a ticker (for re-ingestion)."""
    conn = get_connection()
    try:
        conn.execute("DELETE FROM transcript_claims WHERE ticker = ?", (ticker.upper(),))
        conn.commit()
    finally:
        conn.close()
