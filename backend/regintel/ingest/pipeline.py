"""Corpus ingestion: walk the document library, extract, chunk, embed, store.

Idempotent: a file whose content hash already exists in the DB is skipped, so
re-running only picks up new or changed documents. This is the same path new
documents from the monitoring pillar (Phase 2) will flow through.
"""
from __future__ import annotations

import hashlib
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable, List, Optional

from ..config import Settings, get_settings
from ..db import connect, init_db
from ..embed.embedder import embed_texts, to_blob
from . import metadata
from .chunk import chunk_text
from .extract import extract


def _iter_documents(settings: Settings) -> Iterable[Path]:
    root = settings.corpus_root
    for path in sorted(root.rglob("*")):
        if not path.is_file():
            continue
        if path.suffix.lower() not in settings.SUPPORTED_EXTS:
            continue
        # skip anything inside ignored folders (the platform code, venv, etc.)
        rel_parts = {p.lower() for p in path.relative_to(root).parts[:-1]}
        if rel_parts & {d.lower() for d in settings.IGNORE_DIRS}:
            continue
        yield path


def _hash_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for block in iter(lambda: f.read(65536), b""):
            h.update(block)
    return h.hexdigest()


def _title_from(path: Path) -> str:
    return path.stem.replace("_", " ").replace("-", " ").strip()


def ingest_corpus(
    settings: Optional[Settings] = None,
    reembed: bool = False,
    limit: Optional[int] = None,
    verbose: bool = True,
) -> dict:
    settings = settings or get_settings()
    init_db(settings.db_path)
    conn = connect(settings.db_path)

    stats = {"scanned": 0, "ingested": 0, "skipped": 0, "flagged_scanned": 0, "errors": 0}
    now = datetime.now(timezone.utc).isoformat()

    try:
        existing = {
            row["content_hash"]: row["id"]
            for row in conn.execute("SELECT id, content_hash FROM documents")
        }

        for path in _iter_documents(settings):
            if limit and stats["ingested"] >= limit:
                break
            stats["scanned"] += 1
            try:
                content_hash = _hash_file(path)
                if content_hash in existing and not reembed:
                    stats["skipped"] += 1
                    continue

                text, page_count, is_scanned = extract(path)
                authority, region, category = metadata.derive(path, settings.corpus_root)
                rel_path = str(path.relative_to(settings.corpus_root))

                cur = conn.execute(
                    """INSERT OR REPLACE INTO documents
                       (path, rel_path, filename, title, authority, region, category,
                        ext, size_bytes, page_count, char_count, is_scanned,
                        content_hash, full_text, ingested_at)
                       VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                    (
                        str(path), rel_path, path.name, _title_from(path),
                        authority, region, category, path.suffix.lower(),
                        path.stat().st_size, page_count, len(text),
                        1 if is_scanned else 0, content_hash, text, now,
                    ),
                )
                doc_id = cur.lastrowid
                conn.execute("DELETE FROM chunks WHERE document_id = ?", (doc_id,))

                if is_scanned:
                    stats["flagged_scanned"] += 1
                    if verbose:
                        print(f"  ! scanned/empty (needs OCR): {rel_path}")
                else:
                    _embed_and_store_chunks(conn, doc_id, text, settings)

                conn.commit()
                stats["ingested"] += 1
                if verbose:
                    print(f"  + [{authority}] {rel_path} ({page_count}p, {len(text)} chars)")
            except Exception as exc:  # keep going on a single bad file
                stats["errors"] += 1
                conn.rollback()
                if verbose:
                    print(f"  x ERROR {path.name}: {exc}")
    finally:
        conn.close()
    return stats


def _embed_and_store_chunks(conn, doc_id: int, text: str, settings: Settings) -> None:
    chunks: List[str] = chunk_text(text)
    if not chunks:
        return
    vectors = embed_texts(chunks)
    rows = [
        (doc_id, i, chunk, to_blob(vectors[i]), int(vectors.shape[1]), settings.embed_model)
        for i, chunk in enumerate(chunks)
    ]
    conn.executemany(
        """INSERT INTO chunks (document_id, ordinal, text, embedding, dim, embed_model)
           VALUES (?,?,?,?,?,?)""",
        rows,
    )
