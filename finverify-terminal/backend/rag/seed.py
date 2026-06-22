"""
RAG Index Seeder — Seeds Pinecone with FinQA + SEC + Transcript data
=====================================================================
Run: python -m rag.seed

Sources:
1. SEC filing fundamentals from SQLite (ingested by sec_edgar.py)
2. Transcript claims from SQLite (ingested by transcripts.py)
3. Built-in FinQA-style question templates

If PINECONE_API_KEY is set, seeds Pinecone index.
Otherwise, seeds the in-memory fallback index (useful for local dev).
"""

import sys
import os
import sqlite3
import logging
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from rag.pipeline import (
    upsert_documents,
    add_fallback_docs,
    is_pinecone_available,
    get_index_stats,
    seed_from_filings,
    seed_from_transcripts,
)

logging.basicConfig(level=logging.INFO, format="%(levelname)s | %(message)s")
logger = logging.getLogger(__name__)

DB_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "fundamentals.db")

# ── FinQA-style template documents ──
FINQA_TEMPLATES = [
    {"text": "To calculate profit margin, divide net income by revenue. Profit margin = net_income / revenue * 100.", "metadata": {"source": "finqa_template", "topic": "profit_margin"}},
    {"text": "Return on equity (ROE) equals net income divided by shareholders equity. ROE = net_income / equity * 100.", "metadata": {"source": "finqa_template", "topic": "roe"}},
    {"text": "Earnings per share (EPS) is calculated as net income divided by weighted average shares outstanding.", "metadata": {"source": "finqa_template", "topic": "eps"}},
    {"text": "Revenue growth rate is (current_revenue - prior_revenue) / prior_revenue * 100.", "metadata": {"source": "finqa_template", "topic": "revenue_growth"}},
    {"text": "Operating margin = operating_income / revenue * 100. Measures operational efficiency.", "metadata": {"source": "finqa_template", "topic": "operating_margin"}},
    {"text": "Gross margin = gross_profit / revenue * 100. Shows profitability after cost of goods.", "metadata": {"source": "finqa_template", "topic": "gross_margin"}},
    {"text": "Price to earnings ratio (P/E) = stock_price / earnings_per_share. Measures valuation.", "metadata": {"source": "finqa_template", "topic": "pe_ratio"}},
    {"text": "Debt to equity ratio = total_liabilities / shareholders_equity. Measures leverage.", "metadata": {"source": "finqa_template", "topic": "debt_equity"}},
    {"text": "Current ratio = current_assets / current_liabilities. Measures short-term liquidity.", "metadata": {"source": "finqa_template", "topic": "current_ratio"}},
    {"text": "Free cash flow = operating_cash_flow - capital_expenditures. Measures available cash.", "metadata": {"source": "finqa_template", "topic": "fcf"}},
    {"text": "Book value per share = shareholders_equity / shares_outstanding.", "metadata": {"source": "finqa_template", "topic": "bvps"}},
    {"text": "Asset turnover = revenue / total_assets. Measures efficiency of asset use.", "metadata": {"source": "finqa_template", "topic": "asset_turnover"}},
    {"text": "Net income margin shows what percentage of revenue becomes profit after all expenses.", "metadata": {"source": "finqa_template", "topic": "net_margin"}},
    {"text": "Year-over-year growth compares a metric to the same period in the prior year.", "metadata": {"source": "finqa_template", "topic": "yoy_growth"}},
    {"text": "Basis points (bps) measure small changes. 100 basis points = 1 percentage point.", "metadata": {"source": "finqa_template", "topic": "bps"}},
]


def load_fundamentals_from_db() -> list[dict]:
    """Load SEC filing fundamentals from SQLite."""
    if not os.path.exists(DB_PATH):
        logger.warning("Database not found: %s", DB_PATH)
        return []

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    rows = conn.execute("SELECT * FROM fundamentals").fetchall()
    conn.close()
    return [dict(r) for r in rows]


def load_claims_from_db() -> list[dict]:
    """Load transcript claims from SQLite."""
    if not os.path.exists(DB_PATH):
        return []

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    rows = conn.execute("SELECT * FROM transcript_claims").fetchall()
    conn.close()
    return [dict(r) for r in rows]


def main():
    t0 = time.time()
    logger.info("=" * 60)
    logger.info("RAG INDEX SEEDER")
    logger.info("=" * 60)

    backend = "pinecone" if is_pinecone_available() else "fallback_keyword"
    logger.info("Backend: %s", backend)

    total = 0

    # 1. FinQA templates
    logger.info("\n--- Seeding FinQA templates (%d docs) ---", len(FINQA_TEMPLATES))
    if is_pinecone_available():
        total += upsert_documents(FINQA_TEMPLATES)
    else:
        add_fallback_docs(FINQA_TEMPLATES)
        total += len(FINQA_TEMPLATES)

    # 2. SEC fundamentals
    fundamentals = load_fundamentals_from_db()
    logger.info("\n--- Seeding SEC fundamentals (%d rows) ---", len(fundamentals))
    total += seed_from_filings(fundamentals)

    # 3. Transcript claims
    claims = load_claims_from_db()
    logger.info("\n--- Seeding transcript claims (%d rows) ---", len(claims))
    total += seed_from_transcripts(claims)

    elapsed = time.time() - t0
    stats = get_index_stats()

    logger.info("\n" + "=" * 60)
    logger.info("SEEDING COMPLETE")
    logger.info("  Total documents seeded: %d", total)
    logger.info("  Backend: %s", stats.get("backend", "unknown"))
    logger.info("  Index vectors: %s", stats.get("total_vectors", stats.get("total_docs", 0)))
    logger.info("  Time: %.1fs", elapsed)
    logger.info("=" * 60)


if __name__ == "__main__":
    main()
