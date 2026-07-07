"""Claude-powered interpretation of regulatory documents (Pillar #2).

For each document we send its text (truncated/sampled to a token budget) to Claude
with a forced tool call, guaranteeing a structured result we can persist and query.
Degrades gracefully: if no ANTHROPIC_API_KEY is set, interpretation is skipped.
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from tenacity import retry, stop_after_attempt, wait_exponential

from ..config import Settings, get_settings
from ..db import connect
from . import prompts

# ~4 chars/token. Budget the document body to keep calls fast and affordable while
# staying well within the model context window.
MAX_DOC_CHARS = 140_000


def prepare_text(full_text: str, max_chars: int = MAX_DOC_CHARS) -> str:
    """Fit a long document into the char budget: head-weighted with sampled body.

    Regulatory docs front-load scope/definitions/essential requirements, so we keep
    a large head and then sample evenly through the remainder to catch later
    obligations and transition provisions.
    """
    if len(full_text) <= max_chars:
        return full_text
    head_len = int(max_chars * 0.6)
    rest_budget = max_chars - head_len
    head = full_text[:head_len]
    remainder = full_text[head_len:]
    # sample 4 evenly spaced windows from the remainder
    windows = 4
    win = rest_budget // windows
    step = max(1, len(remainder) // windows)
    samples = []
    for i in range(windows):
        start = i * step
        samples.append(remainder[start : start + win])
    return head + "\n\n[... sampled sections ...]\n\n" + "\n\n[...]\n\n".join(samples)


def _client(settings: Settings):
    from anthropic import Anthropic

    return Anthropic(api_key=settings.anthropic_api_key)


@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=2, min=2, max=30))
def _call_claude(settings: Settings, title, authority, region, category, text) -> Dict[str, Any]:
    client = _client(settings)
    resp = client.messages.create(
        model=settings.model,
        max_tokens=4096,
        system=prompts.SYSTEM,
        tools=[prompts.INTERPRET_TOOL],
        tool_choice={"type": "tool", "name": "record_interpretation"},
        messages=[{
            "role": "user",
            "content": prompts.build_user_prompt(title, authority, region, category, text),
        }],
    )
    for block in resp.content:
        if block.type == "tool_use" and block.name == "record_interpretation":
            return block.input
    raise RuntimeError("Model did not return a tool call")


def interpret_document(doc_row, settings: Settings) -> Optional[Dict[str, Any]]:
    text = prepare_text(doc_row["full_text"] or "")
    if not text.strip():
        return None
    return _call_claude(
        settings, doc_row["title"], doc_row["authority"],
        doc_row["region"], doc_row["category"], text,
    )


def _store(conn, doc_id: int, data: Dict[str, Any], model: str) -> None:
    now = datetime.now(timezone.utc).isoformat()
    conn.execute(
        """INSERT OR REPLACE INTO interpretations
           (document_id, summary, regulatory_areas, risk_level, urgency,
            business_impact, device_types, key_dates, model, created_at, raw_json)
           VALUES (?,?,?,?,?,?,?,?,?,?,?)""",
        (
            doc_id, data.get("summary", ""),
            json.dumps(data.get("regulatory_areas", [])),
            data.get("risk_level", "Medium"), data.get("urgency", "Medium"),
            data.get("business_impact", ""),
            json.dumps(data.get("device_types", [])),
            json.dumps(data.get("key_dates", [])),
            model, now, json.dumps(data),
        ),
    )
    conn.execute("DELETE FROM requirements WHERE document_id = ?", (doc_id,))
    conn.executemany(
        "INSERT INTO requirements (document_id, text, area, citation) VALUES (?,?,?,?)",
        [(doc_id, r.get("text", ""), r.get("area", ""), r.get("citation", ""))
         for r in data.get("key_requirements", [])],
    )
    conn.execute("DELETE FROM obligations WHERE document_id = ?", (doc_id,))
    conn.executemany(
        "INSERT INTO obligations (document_id, text, actor, area, risk) VALUES (?,?,?,?,?)",
        [(doc_id, o.get("text", ""), o.get("actor", ""), o.get("area", ""), o.get("risk", "Medium"))
         for o in data.get("obligations", [])],
    )


def interpret_corpus(
    settings: Optional[Settings] = None,
    limit: Optional[int] = None,
    reinterpret: bool = False,
    verbose: bool = True,
) -> Dict[str, int]:
    settings = settings or get_settings()
    if not settings.claude_enabled:
        raise RuntimeError(
            "ANTHROPIC_API_KEY is not set — cannot run interpretation. "
            "Add it to platform/backend/.env"
        )
    conn = connect(settings.db_path)
    stats = {"processed": 0, "skipped": 0, "errors": 0}
    try:
        done = {r["document_id"] for r in conn.execute("SELECT document_id FROM interpretations")}
        docs = conn.execute(
            "SELECT * FROM documents WHERE is_scanned = 0 AND char_count > 0 ORDER BY id"
        ).fetchall()
        for doc in docs:
            if limit and stats["processed"] >= limit:
                break
            if doc["id"] in done and not reinterpret:
                stats["skipped"] += 1
                continue
            try:
                data = interpret_document(doc, settings)
                if data is None:
                    stats["skipped"] += 1
                    continue
                _store(conn, doc["id"], data, settings.model)
                conn.commit()
                stats["processed"] += 1
                if verbose:
                    print(f"  ✓ [{data.get('risk_level'):8s}] {doc['rel_path']}")
            except Exception as exc:
                stats["errors"] += 1
                conn.rollback()
                if verbose:
                    print(f"  ✗ {doc['rel_path']}: {exc}")
    finally:
        conn.close()
    return stats


def interpret_one(document_id: int, settings: Optional[Settings] = None) -> Dict[str, Any]:
    """Interpret a single document on demand (used by the API)."""
    settings = settings or get_settings()
    if not settings.claude_enabled:
        raise RuntimeError("ANTHROPIC_API_KEY is not set")
    conn = connect(settings.db_path)
    try:
        doc = conn.execute("SELECT * FROM documents WHERE id = ?", (document_id,)).fetchone()
        if not doc:
            raise ValueError(f"No document {document_id}")
        data = interpret_document(doc, settings)
        if data:
            _store(conn, document_id, data, settings.model)
            conn.commit()
        return data or {}
    finally:
        conn.close()
