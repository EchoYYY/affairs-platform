"""Country-level regulatory scan for the Global Monitoring page.

User picks jurisdictions + a timeframe (+ optional device FDA product code /
indication for use), then Scan produces one summary card per country. Each card
carries the regulator's official source link (traceability) plus any monitored
updates and library documents we hold for that jurisdiction within the window,
filtered to the product code / indication when supplied.

Deterministic and offline by default. When ANTHROPIC_API_KEY is set, each card is
enriched with a Claude web-search summary that cites live primary sources.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

from . import jurisdictions
from .config import get_settings
from .db import connect

_last: Optional[Dict[str, Any]] = None


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _matches_filter(text: str, product_code: str, indication: str) -> bool:
    """Relevance filter: keep the item only if it matches the code/indication."""
    if not product_code and not indication:
        return True
    t = (text or "").lower()
    if product_code and product_code.lower() in t:
        return True
    if indication:
        # match if any meaningful word from the indication appears
        words = [w for w in indication.lower().replace(",", " ").split() if len(w) > 3]
        if words and any(w in t for w in words):
            return True
    return False


def _local_data(jur: Dict[str, Any], cutoff: str, product_code: str,
                indication: str) -> Dict[str, List[Dict[str, Any]]]:
    conn = connect()
    try:
        updates, documents = [], []
        auths = jur["match_authorities"]
        regions = jur["match_regions"]
        if auths or regions:
            # monitored updates within the timeframe
            for u in conn.execute("SELECT * FROM updates ORDER BY id DESC LIMIT 500"):
                if u["authority"] not in auths and u["region"] not in regions:
                    continue
                # effective date: the item's own published date, else when we first
                # captured it — so undated items still respect the timeframe filter.
                eff_date = (u["published"] or "")[:10] or (u["fetched_at"] or "")[:10]
                if eff_date and eff_date < cutoff:
                    continue
                if not _matches_filter(f"{u['title']} {u['summary_raw'] or ''}", product_code, indication):
                    continue
                updates.append({"title": u["title"], "url": u["url"],
                                "published": u["published"], "authority": u["authority"]})
            # library documents (corpus)
            ph = ",".join("?" * len(auths)) if auths else "''"
            rows = conn.execute(
                f"SELECT id, title, authority, region, rel_path, full_text FROM documents "
                f"WHERE authority IN ({ph})" if auths else
                "SELECT id, title, authority, region, rel_path, full_text FROM documents WHERE region IN ({})".format(
                    ",".join("?" * len(regions))),
                (auths or regions),
            ).fetchall()
            for d in rows:
                if not _matches_filter(f"{d['title']} {(d['full_text'] or '')[:4000]}", product_code, indication):
                    continue
                documents.append({"id": d["id"], "title": d["title"],
                                  "authority": d["authority"], "rel_path": d["rel_path"]})
        return {"updates": updates[:25], "documents": documents[:25]}
    finally:
        conn.close()


def _claude_summary(jur, days, product_code, indication, settings) -> Dict[str, Any]:
    """Live web-search summary for one jurisdiction, with cited sources."""
    from anthropic import Anthropic

    client = Anthropic(api_key=settings.anthropic_api_key)
    focus = []
    if product_code:
        focus.append(f"FDA product code '{product_code}'")
    if indication:
        focus.append(f"indication for use: '{indication}'")
    focus_line = (" Focus specifically on: " + "; ".join(focus) + ".") if focus else ""
    prompt = (
        f"Search for medical-device regulatory developments from {jur['regulator']} "
        f"({jur['abbrev']}, {jur['country']}) over roughly the last {days} days — new or "
        f"upcoming regulations, guidance, consultations, safety notices and effective "
        f"dates.{focus_line} Give a concise country-level summary (4-6 sentences) for a "
        f"medical-device regulatory affairs team, and cite the primary sources you used. "
        f"Start from the official site {jur['url']} where relevant."
    )
    resp = client.messages.create(
        model=settings.model, max_tokens=1200,
        system="You are a medical-device regulatory intelligence analyst. Be factual, "
               "cite primary sources, and clearly say when you find nothing notable.",
        tools=[{"type": "web_search_20260209", "name": "web_search", "max_uses": 5}],
        messages=[{"role": "user", "content": prompt}],
    )
    text_parts, sources = [], []
    for block in resp.content:
        btype = getattr(block, "type", "")
        if btype == "text":
            text_parts.append(block.text)
            for cit in (getattr(block, "citations", None) or []):
                url = getattr(cit, "url", None)
                title = getattr(cit, "title", None) or url
                if url:
                    sources.append({"title": title, "url": url})
        elif "web_search_tool_result" in btype:
            for item in (getattr(block, "content", None) or []):
                url = getattr(item, "url", None)
                if url:
                    sources.append({"title": getattr(item, "title", None) or url, "url": url})
    # de-dupe sources by url
    seen, uniq = set(), []
    for s in sources:
        if s["url"] not in seen:
            seen.add(s["url"]); uniq.append(s)
    return {"summary": "".join(text_parts).strip(), "sources": uniq[:8], "ai": True}


def scan(jurisdiction_keys: List[str], days: int = 90,
         product_code: str = "", indication: str = "") -> Dict[str, Any]:
    global _last
    settings = get_settings()
    cutoff = (datetime.now(timezone.utc) - timedelta(days=days)).strftime("%Y-%m-%d")

    countries: List[Dict[str, Any]] = []
    for key in jurisdiction_keys:
        jur = jurisdictions.get(key)
        if not jur:
            continue
        local = _local_data(jur, cutoff, product_code, indication)
        card: Dict[str, Any] = {
            "key": key, "country": jur["country"], "region": jur["region"],
            "regulator": jur["regulator"], "abbrev": jur["abbrev"],
            "source_url": jur["url"], "updates": local["updates"],
            "documents": local["documents"], "ai": False, "sources": [],
        }
        n_u, n_d = len(local["updates"]), len(local["documents"])

        if settings.claude_enabled:
            try:
                enr = _claude_summary(jur, days, product_code, indication, settings)
                card.update(summary=enr["summary"], sources=enr["sources"], ai=True)
            except Exception as exc:
                card["summary"] = (f"{n_u} monitored update(s) and {n_d} library document(s) "
                                   f"in scope. (AI web-scan unavailable: {exc})")
        else:
            if n_u:
                card["summary"] = (
                    f"{n_u} monitored regulatory update(s) for {jur['abbrev']} within the last "
                    f"{days} days"
                    + (f" matching '{product_code or indication}'." if (product_code or indication) else "."))
            else:
                card["summary"] = (
                    f"No monitored updates in scope yet. Primary source linked for traceability; "
                    f"add ANTHROPIC_API_KEY to enable a live AI web-scan of {jur['abbrev']}.")
        countries.append(card)

    result = {
        "scanned_at": _now(), "timeframe_days": days,
        "filters": {"product_code": product_code, "indication": indication},
        "jurisdictions": jurisdiction_keys,
        "ai_enabled": settings.claude_enabled,
        "countries": countries,
    }
    _last = result
    return result


def last() -> Optional[Dict[str, Any]]:
    return _last
