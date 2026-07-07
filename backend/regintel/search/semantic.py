"""Semantic search + retrieval over chunk embeddings.

Brute-force cosine similarity in NumPy. Embeddings are already L2-normalized on
write, so a matrix-vector dot product gives cosine scores directly. At corpus
scale (thousands of chunks) this is sub-millisecond and needs no vector index.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional

import numpy as np

from ..db import connect
from ..embed.embedder import embed_query, from_blob

# module-level cache of the embedding matrix so repeated queries don't re-read the DB
_CACHE: Dict[str, Any] = {"matrix": None, "meta": None, "count": 0}


def _load_matrix(conn) -> None:
    rows = conn.execute(
        """SELECT c.id, c.document_id, c.ordinal, c.text, c.embedding,
                  d.title, d.authority, d.region, d.category, d.rel_path
           FROM chunks c JOIN documents d ON d.id = c.document_id"""
    ).fetchall()
    if not rows:
        _CACHE.update(matrix=np.zeros((0, 384), dtype=np.float32), meta=[], count=0)
        return
    mat = np.vstack([from_blob(r["embedding"]) for r in rows]).astype(np.float32)
    meta = [
        {
            "chunk_id": r["id"], "document_id": r["document_id"], "ordinal": r["ordinal"],
            "text": r["text"], "title": r["title"], "authority": r["authority"],
            "region": r["region"], "category": r["category"], "rel_path": r["rel_path"],
        }
        for r in rows
    ]
    _CACHE.update(matrix=mat, meta=meta, count=len(rows))


def invalidate_cache() -> None:
    _CACHE.update(matrix=None, meta=None, count=0)


def _ensure_loaded(conn) -> None:
    current = conn.execute("SELECT COUNT(*) FROM chunks").fetchone()[0]
    if _CACHE["matrix"] is None or _CACHE["count"] != current:
        _load_matrix(conn)


def search_chunks(
    query: str,
    top_k: int = 10,
    authority: Optional[str] = None,
    region: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """Return the top_k most relevant chunks, optionally filtered by jurisdiction."""
    conn = connect()
    try:
        _ensure_loaded(conn)
    finally:
        conn.close()

    mat, meta = _CACHE["matrix"], _CACHE["meta"]
    if mat is None or mat.shape[0] == 0:
        return []

    q = embed_query(query)
    scores = mat @ q  # cosine similarity (all vectors L2-normalized)

    # apply metadata filters by masking scores
    if authority or region:
        mask = np.ones(len(meta), dtype=bool)
        if authority:
            mask &= np.array([m["authority"] == authority for m in meta])
        if region:
            mask &= np.array([m["region"] == region for m in meta])
        scores = np.where(mask, scores, -np.inf)

    k = min(top_k, mat.shape[0])
    idx = np.argpartition(-scores, k - 1)[:k]
    idx = idx[np.argsort(-scores[idx])]

    results = []
    for i in idx:
        if not np.isfinite(scores[i]):
            continue
        m = dict(meta[i])
        m["score"] = float(scores[i])
        results.append(m)
    return results


def search_documents(
    query: str,
    top_k: int = 10,
    authority: Optional[str] = None,
    region: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """Document-level search: best chunk score per document, with a snippet."""
    chunk_hits = search_chunks(query, top_k=top_k * 4, authority=authority, region=region)
    by_doc: Dict[int, Dict[str, Any]] = {}
    for hit in chunk_hits:
        doc_id = hit["document_id"]
        if doc_id not in by_doc or hit["score"] > by_doc[doc_id]["score"]:
            by_doc[doc_id] = {
                "document_id": doc_id, "title": hit["title"], "authority": hit["authority"],
                "region": hit["region"], "category": hit["category"],
                "rel_path": hit["rel_path"], "score": hit["score"],
                "snippet": hit["text"][:400],
            }
    ranked = sorted(by_doc.values(), key=lambda d: -d["score"])
    return ranked[:top_k]
