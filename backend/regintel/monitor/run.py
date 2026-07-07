"""Poll enabled sources, detect new items, persist them, and score alerts.

Change detection is a content hash over (source_key + external_id + title). A hash
already present in `updates` is skipped, so re-polling only surfaces genuinely new
items — the same idempotent contract the corpus ingest uses.

Each newly stored update is immediately scored into an alert (Pillar 3) so the alert
feed stays current without a separate pass.
"""
from __future__ import annotations

import hashlib
from datetime import datetime, timezone
from typing import Dict, List, Optional

from ..db import connect
from . import fetch, sources


def _hash(source_key: str, external_id: str, title: str) -> str:
    return hashlib.sha256(f"{source_key}|{external_id}|{title}".encode("utf-8")).hexdigest()


def poll_all(score: bool = True, verbose: bool = True) -> Dict[str, int]:
    sources.seed_sources()
    conn = connect()
    stats = {"sources_ok": 0, "sources_error": 0, "new_updates": 0, "alerts_created": 0}
    new_update_ids: List[int] = []
    now = datetime.now(timezone.utc).isoformat()
    try:
        srcs = conn.execute("SELECT * FROM sources WHERE enabled = 1").fetchall()
        for s in srcs:
            src = dict(s)
            try:
                items = fetch.fetch_source(src)
                sources.mark_checked(conn, src["id"], f"ok ({len(items)} items)")
                stats["sources_ok"] += 1
                for it in items:
                    h = _hash(src["key"], it["external_id"], it["title"])
                    exists = conn.execute("SELECT 1 FROM updates WHERE content_hash = ?", (h,)).fetchone()
                    if exists:
                        continue
                    cur = conn.execute(
                        """INSERT INTO updates
                           (source_id, external_id, title, url, published, authority, region,
                            summary_raw, content_hash, fetched_at)
                           VALUES (?,?,?,?,?,?,?,?,?,?)""",
                        (src["id"], it["external_id"], it["title"], it["url"], it["published"],
                         src["authority"], src["region"], it["summary_raw"], h, now),
                    )
                    new_update_ids.append(cur.lastrowid)
                    stats["new_updates"] += 1
                conn.commit()
                if verbose:
                    print(f"  ✓ {src['name']}: {len(items)} items")
            except Exception as exc:
                stats["sources_error"] += 1
                sources.mark_checked(conn, src["id"], f"error: {exc}")
                conn.commit()
                if verbose:
                    print(f"  ✗ {src['name']}: {exc}")
    finally:
        conn.close()

    if score and new_update_ids:
        from ..alerts.score import score_updates
        stats["alerts_created"] = score_updates(new_update_ids, verbose=verbose)

    return stats
