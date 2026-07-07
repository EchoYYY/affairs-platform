"""Safety-information scan for the Intelligent Alerts module.

Given selected jurisdictions + a timeframe, returns per-jurisdiction safety
signals — recalls, field-safety notices and early alerts — captured from live
feeds (FDA recalls/CDRH, MHRA alerts), each as a link only (no detail body).
Every jurisdiction also carries its official safety-information page for
traceability, and IMDRF is the cross-jurisdiction gateway.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

from . import jurisdictions
from .db import connect

_SAFETY_KW = (
    "recall", "safety", "alert", "field safety", "fsca", "fsn", "hazard",
    "correction", "removal", "withdraw", "adverse", "defect", "early alert",
    "precautionary",
)

_last: Optional[Dict[str, Any]] = None


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _is_safety(text: str) -> bool:
    t = (text or "").lower()
    return any(k in t for k in _SAFETY_KW)


def scan(jurisdiction_keys: List[str], days: int = 30) -> Dict[str, Any]:
    global _last
    cutoff = (datetime.now(timezone.utc) - timedelta(days=days)).strftime("%Y-%m-%d")
    conn = connect()
    try:
        countries: List[Dict[str, Any]] = []
        for key in jurisdiction_keys:
            jur = jurisdictions.get(key)
            if not jur:
                continue
            auths, regions = jur["match_authorities"], jur["match_regions"]
            alerts: List[Dict[str, Any]] = []
            if auths or regions:
                for u in conn.execute("SELECT * FROM updates ORDER BY id DESC LIMIT 600"):
                    if u["authority"] not in auths and u["region"] not in regions:
                        continue
                    if not _is_safety(f"{u['title']} {u['summary_raw'] or ''}"):
                        continue
                    eff = (u["published"] or "")[:10] or (u["fetched_at"] or "")[:10]
                    if eff and eff < cutoff:
                        continue
                    alerts.append({
                        "title": u["title"], "url": u["url"],
                        "date": (u["published"] or "")[:10], "authority": u["authority"],
                    })
            countries.append({
                "key": key, "country": jur["country"], "region": jur["region"],
                "regulator": jur["regulator"], "abbrev": jur["abbrev"],
                "safety_url": jur["safety_url"], "count": len(alerts),
                "alerts": alerts[:30],
            })
        total = sum(c["count"] for c in countries)
        result = {
            "scanned_at": _now(), "timeframe_days": days,
            "jurisdictions": jurisdiction_keys, "total_alerts": total,
            "countries": countries,
        }
        _last = result
        return result
    finally:
        conn.close()


def last() -> Optional[Dict[str, Any]]:
    return _last
