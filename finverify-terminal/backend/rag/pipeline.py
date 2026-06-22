"""
RAG Pipeline — Pinecone Vector Search
=======================================
Replaces in-memory FAISS with Pinecone for persistent vector storage.
Falls back to simple keyword matching if Pinecone is unavailable.

Setup:
    pip install pinecone-client sentence-transformers
    Set PINECONE_API_KEY in environment/.env

Index config: dimension=384 (all-MiniLM-L6-v2), metric=cosine
"""

import os
import logging
import hashlib
from typing import Optional

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Optional imports (graceful fallback)
# ---------------------------------------------------------------------------

try:
    from pinecone import Pinecone, ServerlessSpec
    PINECONE_AVAILABLE = True
except ImportError:
    PINECONE_AVAILABLE = False
    logger.info("pinecone-client not installed -- using fallback search")

try:
    from sentence_transformers import SentenceTransformer
    EMBEDDER_AVAILABLE = True
except ImportError:
    EMBEDDER_AVAILABLE = False
    logger.info("sentence-transformers not installed -- embeddings unavailable")


# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

PINECONE_INDEX_NAME = "finverify-rag"
EMBEDDING_MODEL = "all-MiniLM-L6-v2"
EMBEDDING_DIM = 384
TOP_K = 5

_pc_index = None
_embedder = None


# ---------------------------------------------------------------------------
# Initialization
# ---------------------------------------------------------------------------

def _get_embedder():
    global _embedder
    if _embedder is None and EMBEDDER_AVAILABLE:
        logger.info("Loading embedding model: %s", EMBEDDING_MODEL)
        _embedder = SentenceTransformer(EMBEDDING_MODEL)
    return _embedder


def _get_pinecone_index():
    """Get or create Pinecone index."""
    global _pc_index
    if _pc_index is not None:
        return _pc_index

    api_key = os.getenv("PINECONE_API_KEY")
    if not api_key or not PINECONE_AVAILABLE:
        return None

    try:
        pc = Pinecone(api_key=api_key)
        existing = [idx.name for idx in pc.list_indexes()]

        if PINECONE_INDEX_NAME not in existing:
            logger.info("Creating Pinecone index: %s", PINECONE_INDEX_NAME)
            pc.create_index(
                name=PINECONE_INDEX_NAME,
                dimension=EMBEDDING_DIM,
                metric="cosine",
                spec=ServerlessSpec(cloud="aws", region="us-east-1"),
            )

        _pc_index = pc.Index(PINECONE_INDEX_NAME)
        stats = _pc_index.describe_index_stats()
        logger.info(
            "Pinecone connected: %s (%d vectors)",
            PINECONE_INDEX_NAME,
            stats.get("total_vector_count", 0),
        )
        return _pc_index
    except Exception as e:
        logger.warning("Pinecone init failed: %s", e)
        return None


def is_pinecone_available() -> bool:
    """Check if Pinecone is configured and reachable."""
    return _get_pinecone_index() is not None


# ---------------------------------------------------------------------------
# Embedding
# ---------------------------------------------------------------------------

def embed(text: str) -> Optional[list[float]]:
    """Generate embedding vector for text."""
    embedder = _get_embedder()
    if embedder is None:
        return None
    return embedder.encode(text).tolist()


def _text_id(text: str) -> str:
    """Generate stable ID for a text chunk."""
    return hashlib.md5(text.encode()).hexdigest()[:16]


# ---------------------------------------------------------------------------
# Upsert / Query
# ---------------------------------------------------------------------------

def upsert_documents(documents: list[dict]):
    """
    Upsert documents into Pinecone.
    Each doc: {"text": str, "metadata": dict}
    """
    index = _get_pinecone_index()
    embedder = _get_embedder()
    if index is None or embedder is None:
        logger.warning("Cannot upsert: Pinecone or embedder unavailable")
        return 0

    vectors = []
    texts = [d["text"] for d in documents]
    embeddings = embedder.encode(texts).tolist()

    for doc, emb in zip(documents, embeddings):
        vec_id = _text_id(doc["text"])
        metadata = {
            "text": doc["text"][:1000],
            **(doc.get("metadata", {})),
        }
        vectors.append({"id": vec_id, "values": emb, "metadata": metadata})

    # Upsert in batches of 100
    batch_size = 100
    total = 0
    for i in range(0, len(vectors), batch_size):
        batch = vectors[i:i + batch_size]
        index.upsert(vectors=batch)
        total += len(batch)
        logger.info("Upserted batch %d-%d (%d total)", i, i + len(batch), total)

    return total


def query(question: str, top_k: int = TOP_K) -> list[dict]:
    """
    Query Pinecone for relevant documents.
    Returns list of {text, score, metadata}.
    Falls back to empty list if unavailable.
    """
    index = _get_pinecone_index()
    if index is None:
        return _fallback_search(question, top_k)

    vector = embed(question)
    if vector is None:
        return _fallback_search(question, top_k)

    try:
        results = index.query(
            vector=vector,
            top_k=top_k,
            include_metadata=True,
        )
        return [
            {
                "text": match.metadata.get("text", ""),
                "score": match.score,
                "metadata": match.metadata,
            }
            for match in results.matches
        ]
    except Exception as e:
        logger.warning("Pinecone query failed: %s", e)
        return _fallback_search(question, top_k)


# ---------------------------------------------------------------------------
# Fallback: simple keyword search
# ---------------------------------------------------------------------------

_FALLBACK_DOCS: list[dict] = []


def add_fallback_docs(docs: list[dict]):
    """Add documents to fallback keyword search index."""
    global _FALLBACK_DOCS
    _FALLBACK_DOCS.extend(docs)


def _fallback_search(question: str, top_k: int = 5) -> list[dict]:
    """Simple keyword overlap search when Pinecone is unavailable."""
    if not _FALLBACK_DOCS:
        return []

    q_words = set(question.lower().split())
    scored = []
    for doc in _FALLBACK_DOCS:
        text = doc.get("text", "").lower()
        doc_words = set(text.split())
        overlap = len(q_words & doc_words) / max(len(q_words), 1)
        scored.append((overlap, doc))

    scored.sort(key=lambda x: x[0], reverse=True)
    return [
        {"text": doc["text"], "score": score, "metadata": doc.get("metadata", {})}
        for score, doc in scored[:top_k]
        if score > 0
    ]


# ---------------------------------------------------------------------------
# Seeding helpers
# ---------------------------------------------------------------------------

def seed_from_filings(fundamentals: list[dict]):
    """Seed RAG index with filing-extracted fundamentals."""
    docs = []
    for f in fundamentals:
        text = (
            f"{f.get('ticker', '')} {f.get('metric_name', '')}: "
            f"raw {f.get('raw_value', '')} verified {f.get('verified_value', '')} "
            f"({f.get('period', '')} {f.get('filing_type', '')})"
        )
        docs.append({
            "text": text,
            "metadata": {
                "ticker": f.get("ticker", ""),
                "metric": f.get("metric_name", ""),
                "source": "sec_filing",
            },
        })

    if is_pinecone_available():
        return upsert_documents(docs)
    else:
        add_fallback_docs(docs)
        return len(docs)


def seed_from_transcripts(claims: list[dict]):
    """Seed RAG index with earnings transcript claims."""
    docs = []
    for c in claims:
        docs.append({
            "text": c.get("sentence", ""),
            "metadata": {
                "claim_type": c.get("claim_type", ""),
                "raw_value": c.get("raw_value", 0),
                "source": "earnings_transcript",
            },
        })

    if is_pinecone_available():
        return upsert_documents(docs)
    else:
        add_fallback_docs(docs)
        return len(docs)


def get_index_stats() -> dict:
    """Get current index statistics."""
    index = _get_pinecone_index()
    if index is not None:
        try:
            stats = index.describe_index_stats()
            return {
                "backend": "pinecone",
                "index": PINECONE_INDEX_NAME,
                "total_vectors": stats.get("total_vector_count", 0),
                "dimension": EMBEDDING_DIM,
            }
        except Exception:
            pass

    return {
        "backend": "fallback_keyword",
        "total_docs": len(_FALLBACK_DOCS),
        "dimension": 0,
    }
