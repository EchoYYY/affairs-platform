"""Regulatory Horizon Scanning (Pillar 1 — forward-looking layer).

Where monitoring captures what has *already* published, horizon scanning looks
*ahead*: it surfaces upcoming and emerging regulation — consultations, draft and
proposed rules, and future effective dates / transition deadlines — before they
become binding, so teams can plan impact in advance.

Each signal is categorized and assigned a priority tier:
  * Actionable   — a binding change with a future deadline/effective date
  * Indicative   — a consultation / draft / proposal that may still change
  * Informative  — general forward-looking awareness

Runs offline on rule-based classification; a Claude key sharpens nothing here —
the value is deterministic surfacing of the pipeline.
"""
from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from .db import connect

# category -> keyword triggers (checked against title + summary, lowercased)
_CATEGORIES = [
    ("Consultation", [
        "consultation", "consult", "discussion paper", "call for evidence",
        "call for input", "comment period", "public consultation", "green paper",
        "white paper", "request for comment", "seeking views", "have your say",
    ]),
    ("Proposed / Draft", [
        "draft", "proposed", "proposal", "notice of proposed", "rulemaking",
        "rule-making", "pre-publication", "for comment", "interim final",
    ]),
    ("Deadline / Effective date", [
        "coming into force", "comes into force", "enters into force", "will apply",
        "applies from", "effective from", "effective date", "transition period",
        "transitional", "deadline", "comes into effect", "takes effect",
        "as of", "by 1 ", "from 1 ",
    ]),
]

# any hit here (without a stronger category) still flags an item as forward-looking
_GENERIC_FORWARD = [
    "upcoming", "will be required", "future", "roadmap", "planned", "expected to",
    "will introduce", "to be published", "forthcoming", "phased", "horizon",
]

_PRIORITY = {
    "Deadline / Effective date": "Actionable",
    "Proposed / Draft": "Indicative",
    "Consultation": "Indicative",
    "General": "Informative",
}

_last_scan: Optional[Dict[str, Any]] = None


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _classify(text: str) -> Optional[str]:
    t = text.lower()
    for cat, kws in _CATEGORIES:
        if any(k in t for k in kws):
            return cat
    if any(k in t for k in _GENERIC_FORWARD):
        return "General"
    return None


def _future_year(s: str, this_year: int) -> bool:
    """True if the date string references the current or a future year."""
    for y in re.findall(r"(20\d{2})", s or ""):
        if int(y) >= this_year:
            return True
    return False


def scan(poll: bool = True, verbose: bool = False) -> Dict[str, Any]:
    global _last_scan
    polled = None
    if poll:
        try:
            from .monitor.run import poll_all
            polled = poll_all(score=True, verbose=verbose)
        except Exception as exc:  # network may be unavailable; scan existing data
            polled = {"error": str(exc)}

    this_year = datetime.now(timezone.utc).year
    conn = connect()
    try:
        items: List[Dict[str, Any]] = []
        for u in conn.execute("SELECT * FROM updates ORDER BY id DESC LIMIT 400"):
            cat = _classify(f"{u['title']} {u['summary_raw'] or ''}")
            if not cat:
                continue
            items.append({
                "id": u["id"], "title": u["title"], "authority": u["authority"],
                "region": u["region"], "published": u["published"], "url": u["url"],
                "category": cat, "priority": _PRIORITY.get(cat, "Informative"),
                "snippet": (u["summary_raw"] or "")[:200],
            })

        # upcoming deadlines from interpreted documents' key_dates
        deadlines: List[Dict[str, Any]] = []
        for r in conn.execute(
            """SELECT i.key_dates, i.document_id, d.title, d.authority
               FROM interpretations i JOIN documents d ON d.id = i.document_id
               WHERE i.key_dates IS NOT NULL AND i.key_dates != '[]'"""):
            try:
                for kd in json.loads(r["key_dates"] or "[]"):
                    date = str(kd.get("date", ""))
                    if _future_year(date, this_year):
                        deadlines.append({
                            "date": date, "label": kd.get("label", ""),
                            "document_id": r["document_id"], "document_title": r["title"],
                            "authority": r["authority"],
                        })
            except (TypeError, ValueError):
                continue
        deadlines.sort(key=lambda d: d["date"])

        # counts + emerging by authority
        counts: Dict[str, int] = {"total": len(items)}
        by_auth: Dict[str, int] = {}
        for it in items:
            counts[it["category"]] = counts.get(it["category"], 0) + 1
            by_auth[it["authority"]] = by_auth.get(it["authority"], 0) + 1

        # priority ordering for the feed
        order = {"Actionable": 0, "Indicative": 1, "Informative": 2}
        items.sort(key=lambda x: (order.get(x["priority"], 3), -(x["id"])))

        consult = counts.get("Consultation", 0)
        draft = counts.get("Proposed / Draft", 0)
        dl = counts.get("Deadline / Effective date", 0)
        summary = (
            f"{len(items)} forward-looking signal{'s' if len(items) != 1 else ''} on the horizon: "
            f"{consult} consultation{'s' if consult != 1 else ''}, "
            f"{draft} proposed/draft, {dl} with a future deadline — "
            f"across {len(by_auth)} authorit{'ies' if len(by_auth) != 1 else 'y'}. "
            f"{len(deadlines)} upcoming date{'s' if len(deadlines) != 1 else ''} from interpreted documents."
        )

        result = {
            "scanned_at": _now(),
            "polled": polled,
            "summary": summary,
            "counts": counts,
            "items": items[:100],
            "upcoming_deadlines": deadlines[:50],
            "by_authority": sorted(
                ({"label": k, "count": v} for k, v in by_auth.items()),
                key=lambda x: -x["count"]),
        }
        _last_scan = result
        return result
    finally:
        conn.close()


def last() -> Optional[Dict[str, Any]]:
    return _last_scan
