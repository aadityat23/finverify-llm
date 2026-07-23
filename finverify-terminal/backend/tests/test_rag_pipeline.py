"""
Tests for the RAG pipeline fallback path.

Covers add_fallback_docs, _fallback_search, query (fallback path when
PINECONE_API_KEY is unset), seed_from_filings, seed_from_transcripts, and
get_index_stats. These exercise the keyword-overlap fallback that most
contributors hit locally without a Pinecone API key.

Usage: pytest tests/test_rag_pipeline.py   (from backend/ directory)
"""

import os
import pytest

import rag.pipeline as pipeline
from rag.pipeline import (
    _fallback_search,
    add_fallback_docs,
    get_index_stats,
    query,
    seed_from_filings,
    seed_from_transcripts,
)


@pytest.fixture(autouse=True)
def reset_fallback_docs(monkeypatch):
    """Clear the module-level fallback doc list before each test and force
    the fallback path by making _get_pinecone_index return None."""
    monkeypatch.setattr(pipeline, "_FALLBACK_DOCS", [])
    monkeypatch.setattr(pipeline, "_get_pinecone_index", lambda: None)
    # Also clear the cached index so a previous real connection can't leak in.
    monkeypatch.setattr(pipeline, "_pc_index", None)
    yield
    monkeypatch.setattr(pipeline, "_FALLBACK_DOCS", [])


# ---------------------------------------------------------------------------
# add_fallback_docs / _fallback_search
# ---------------------------------------------------------------------------


def test_add_fallback_docs_appends():
    docs = [{"text": "apple revenue grew", "metadata": {"ticker": "AAPL"}}]
    add_fallback_docs(docs)
    assert len(pipeline._FALLBACK_DOCS) == 1
    assert pipeline._FALLBACK_DOCS[0]["text"] == "apple revenue grew"


def test_fallback_search_ranks_by_word_overlap():
    add_fallback_docs([
        {"text": "apple revenue grew strongly", "metadata": {"ticker": "AAPL"}},
        {"text": "microsoft cloud sales expanded", "metadata": {"ticker": "MSFT"}},
        {"text": "apple margins compressed", "metadata": {"ticker": "AAPL"}},
    ])
    results = _fallback_search("apple revenue", top_k=3)
    # "apple revenue grew strongly" shares two query words -> rank 1
    assert results[0]["text"] == "apple revenue grew strongly"
    # "apple margins compressed" shares one query word -> rank 2
    assert results[1]["text"] == "apple margins compressed"
    # "microsoft cloud sales expanded" shares none -> filtered out (score 0)
    assert len(results) == 2


def test_fallback_search_empty_index_returns_empty():
    assert _fallback_search("anything", top_k=5) == []


def test_fallback_search_respects_top_k():
    docs = [{"text": f"doc {i} keyword", "metadata": {}} for i in range(10)]
    add_fallback_docs(docs)
    results = _fallback_search("keyword", top_k=3)
    assert len(results) == 3


def test_fallback_search_filters_zero_overlap():
    add_fallback_docs([
        {"text": "completely unrelated text", "metadata": {}},
    ])
    assert _fallback_search("apple revenue", top_k=5) == []


def test_fallback_search_is_case_insensitive():
    add_fallback_docs([
        {"text": "Apple Revenue Grew", "metadata": {}},
    ])
    results = _fallback_search("apple revenue", top_k=5)
    assert len(results) == 1
    assert results[0]["score"] > 0


def test_fallback_search_returns_metadata():
    add_fallback_docs([
        {"text": "apple revenue", "metadata": {"ticker": "AAPL", "source": "x"}},
    ])
    results = _fallback_search("apple", top_k=1)
    assert results[0]["metadata"]["ticker"] == "AAPL"


# ---------------------------------------------------------------------------
# query (fallback path)
# ---------------------------------------------------------------------------


def test_query_uses_fallback_when_pinecone_unavailable(monkeypatch):
    # _get_pinecone_index is stubbed to None via the autouse fixture, so
    # query() must route to _fallback_search.
    add_fallback_docs([
        {"text": "apple revenue grew", "metadata": {"ticker": "AAPL"}},
    ])
    results = query("apple revenue", top_k=5)
    assert len(results) == 1
    assert results[0]["text"] == "apple revenue grew"


def test_query_fallback_returns_empty_when_no_docs():
    assert query("anything", top_k=5) == []


def test_query_fallback_score_in_range():
    add_fallback_docs([
        {"text": "apple revenue grew", "metadata": {}},
    ])
    results = query("apple revenue", top_k=5)
    for r in results:
        assert 0.0 < r["score"] <= 1.0


# ---------------------------------------------------------------------------
# seed_from_filings / seed_from_transcripts
# ---------------------------------------------------------------------------


def test_seed_from_filings_builds_correct_doc_shape():
    fundamentals = [
        {
            "ticker": "AAPL",
            "metric_name": "revenue",
            "raw_value": 100,
            "verified_value": 100,
            "period": "2024 Q1",
            "filing_type": "10-K",
        }
    ]
    count = seed_from_filings(fundamentals)
    assert count == 1
    assert len(pipeline._FALLBACK_DOCS) == 1
    doc = pipeline._FALLBACK_DOCS[0]
    assert "AAPL" in doc["text"]
    assert "revenue" in doc["text"]
    assert doc["metadata"]["ticker"] == "AAPL"
    assert doc["metadata"]["metric"] == "revenue"
    assert doc["metadata"]["source"] == "sec_filing"


def test_seed_from_filings_handles_missing_fields():
    # Missing keys should not raise; defaults are empty strings.
    count = seed_from_filings([{}])
    assert count == 1
    doc = pipeline._FALLBACK_DOCS[0]
    assert doc["metadata"]["ticker"] == ""
    assert doc["metadata"]["source"] == "sec_filing"


def test_seed_from_transcripts_builds_correct_doc_shape():
    claims = [
        {
            "sentence": "We expect revenue to grow 15% next quarter.",
            "claim_type": "guidance",
            "raw_value": 15,
        }
    ]
    count = seed_from_transcripts(claims)
    assert count == 1
    assert len(pipeline._FALLBACK_DOCS) == 1
    doc = pipeline._FALLBACK_DOCS[0]
    assert doc["text"] == "We expect revenue to grow 15% next quarter."
    assert doc["metadata"]["claim_type"] == "guidance"
    assert doc["metadata"]["raw_value"] == 15
    assert doc["metadata"]["source"] == "earnings_transcript"


def test_seed_from_transcripts_handles_missing_fields():
    count = seed_from_transcripts([{}])
    assert count == 1
    doc = pipeline._FALLBACK_DOCS[0]
    assert doc["text"] == ""
    assert doc["metadata"]["claim_type"] == ""
    assert doc["metadata"]["raw_value"] == 0
    assert doc["metadata"]["source"] == "earnings_transcript"


def test_seed_methods_accumulate_in_fallback_index():
    seed_from_filings([{"ticker": "AAPL", "metric_name": "revenue"}])
    seed_from_transcripts([{"sentence": "guidance text", "claim_type": "g"}])
    assert len(pipeline._FALLBACK_DOCS) == 2


# ---------------------------------------------------------------------------
# get_index_stats
# ---------------------------------------------------------------------------


def test_get_index_stats_fallback_shape():
    add_fallback_docs([{"text": "a", "metadata": {}}, {"text": "b", "metadata": {}}])
    stats = get_index_stats()
    assert stats["backend"] == "fallback_keyword"
    assert stats["total_docs"] == 2
    assert stats["dimension"] == 0


def test_get_index_stats_fallback_empty():
    stats = get_index_stats()
    assert stats["backend"] == "fallback_keyword"
    assert stats["total_docs"] == 0


def test_get_index_stats_pinecone_shape(monkeypatch):
    # Force the Pinecone branch by stubbing _get_pinecone_index to a fake
    # index whose describe_index_stats returns a dict.
    class FakeIndex:
        def describe_index_stats(self):
            return {"total_vector_count": 42}

    monkeypatch.setattr(pipeline, "_get_pinecone_index", lambda: FakeIndex())
    stats = get_index_stats()
    assert stats["backend"] == "pinecone"
    assert stats["total_vectors"] == 42
    assert stats["dimension"] == pipeline.EMBEDDING_DIM
    assert stats["index"] == pipeline.PINECONE_INDEX_NAME
