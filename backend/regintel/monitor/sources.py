"""Registry of monitored regulatory sources.

Curated with real, key-free feeds/APIs that are stable enough to ship. Each source
records last_status on every poll, so a feed that moves or breaks becomes visible in
the UI rather than failing silently. Users can enable/disable or add their own.

`type`:
  rss      - RSS/Atom feed (parsed with feedparser)
  openfda  - openFDA JSON API (https://open.fda.gov, no API key, rate-limited)
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any, Dict, List

from ..db import connect

# key, name, authority, region, type, url, areas, enabled
DEFAULT_SOURCES: List[Dict[str, Any]] = [
    {
        "key": "openfda-device-recalls",
        "name": "FDA Device Recalls / Enforcement (openFDA)",
        "authority": "FDA", "region": "US", "type": "openfda", "kind": "safety",
        "url": "https://api.fda.gov/device/enforcement.json?sort=report_date:desc&limit=25",
        "areas": ["Post-Market Surveillance", "Safety"], "enabled": 1,
    },
    {
        "key": "fda-cdrh-news",
        "name": "FDA CDRH News & Updates",
        "authority": "FDA", "region": "US", "type": "html", "kind": "regulatory",
        "url": "https://www.fda.gov/medical-devices/medical-devices-news-and-events/cdrh-new-news-and-updates",
        "content_path": "/medical-devices/",
        "areas": ["Guidance", "News"], "enabled": 1,
    },
    {
        "key": "fda-press-announcements",
        "name": "FDA Press Announcements",
        "authority": "FDA", "region": "US", "type": "html", "kind": "regulatory",
        "url": "https://www.fda.gov/news-events/fda-newsroom/press-announcements",
        "content_path": "/news-events/press-announcements/",
        "areas": ["News", "Regulatory"], "enabled": 1,
    },
    {
        "key": "fda-device-recalls-alerts",
        "name": "FDA Device Recalls & Early Alerts",
        "authority": "FDA", "region": "US", "type": "html", "kind": "safety",
        "url": "https://www.fda.gov/medical-devices/medical-device-safety/medical-device-recalls-and-early-alerts",
        "content_path": "/medical-devices/",
        "areas": ["Safety", "Post-Market Surveillance"], "enabled": 1,
    },
    {
        "key": "mhra-drug-device-alerts",
        "name": "MHRA Drug & Device Safety Alerts",
        "authority": "MHRA", "region": "UK", "type": "rss", "kind": "safety",
        "url": "https://www.gov.uk/drug-device-alerts.atom",
        "areas": ["Safety", "Post-Market Surveillance"], "enabled": 1,
    },
    {
        "key": "mhra-news",
        "name": "MHRA News & Guidance (gov.uk)",
        "authority": "MHRA", "region": "UK", "type": "rss", "kind": "regulatory",
        "url": "https://www.gov.uk/search/news-and-communications.atom?organisations%5B%5D=medicines-and-healthcare-products-regulatory-agency",
        "areas": ["Guidance"], "enabled": 1,
    },
    # Configurable placeholders — verify the URL for your region, then enable.
    {
        "key": "ema-news",
        "name": "EMA News (verify feed URL)",
        "authority": "EMA", "region": "EU", "type": "rss", "kind": "regulatory",
        "url": "https://www.ema.europa.eu/en/rss.xml",
        "areas": ["Guidance", "Safety"], "enabled": 0,
    },
    {
        "key": "tga-news",
        "name": "TGA News (verify feed URL)",
        "authority": "TGA", "region": "Australia", "type": "rss", "kind": "regulatory",
        "url": "https://www.tga.gov.au/rss.xml",
        "areas": ["Guidance", "Safety"], "enabled": 0,
    },
    # International guidance bodies
    {
        "key": "mdcg-guidance",
        "name": "MDCG Endorsed Guidance (EU Commission)",
        "authority": "MDCG", "region": "International", "type": "html", "kind": "regulatory",
        "url": "https://health.ec.europa.eu/medical-devices-sector/new-regulations/guidance-mdcg-endorsed-documents-and-other-guidance_en",
        "content_path": "/document/download/", "min_title_len": 6,
        "areas": ["Guidance"], "enabled": 1,
    },
    {
        "key": "imdrf-news",
        "name": "IMDRF News & Events",
        "authority": "IMDRF", "region": "International", "type": "html", "kind": "regulatory",
        "url": "https://www.imdrf.org/news-events",
        "content_path": "/news", "min_title_len": 15,
        "areas": ["Guidance", "News"], "enabled": 1,
    },
    {
        "key": "team-nb-news",
        "name": "Team-NB News (European Notified Bodies)",
        "authority": "Team-NB", "region": "International", "type": "html", "kind": "regulatory",
        "url": "https://www.team-nb.org/",
        "content_path": "https://www.team-nb.org/", "min_title_len": 15,
        "areas": ["Guidance", "News"], "enabled": 1,
    },
    # Third-party regulatory-intelligence aggregators — consolidated under "Other"
    {
        "key": "pacific-bridge",
        "name": "Pacific Bridge Medical — Resource Center",
        "authority": "Pacific Bridge Medical", "region": "Other", "type": "html", "kind": "regulatory",
        "url": "https://www.pacificbridgemedical.com/resource-center/",
        "content_path": "/news-brief/", "min_title_len": 15,
        "areas": ["News"], "enabled": 1,
    },
    {
        "key": "pure-global",
        "name": "Pure Global — Regulatory Updates",
        "authority": "Pure Global", "region": "Other", "type": "html", "kind": "regulatory",
        "url": "https://www.pureglobal.com/resources/regulatory-updates",
        "content_path": "/news/", "min_title_len": 15,
        "areas": ["News"], "enabled": 1,
    },
]

# kind lookup by source key — 'regulatory' (news/guidance/press) vs 'safety'
# (recalls/alerts). Global Monitoring shows regulatory; the Alerts safety scan
# shows safety.
SOURCE_KIND: Dict[str, str] = {s["key"]: s.get("kind", "regulatory") for s in DEFAULT_SOURCES}
_BY_KEY = {s["key"]: s for s in DEFAULT_SOURCES}


def by_key(key: str):
    return _BY_KEY.get(key)


def seed_sources() -> None:
    conn = connect()
    try:
        for s in DEFAULT_SOURCES:
            conn.execute(
                """INSERT INTO sources (key, name, authority, region, type, url, areas, enabled)
                   VALUES (?,?,?,?,?,?,?,?)
                   ON CONFLICT(key) DO NOTHING""",
                (s["key"], s["name"], s["authority"], s["region"], s["type"],
                 s["url"], json.dumps(s["areas"]), s["enabled"]),
            )
        conn.commit()
    finally:
        conn.close()


def list_sources() -> List[Dict[str, Any]]:
    seed_sources()
    conn = connect()
    try:
        out = []
        for r in conn.execute("SELECT * FROM sources ORDER BY enabled DESC, authority"):
            d = dict(r)
            try:
                d["areas"] = json.loads(d["areas"]) if d["areas"] else []
            except (TypeError, ValueError):
                d["areas"] = []
            out.append(d)
        return out
    finally:
        conn.close()


def set_enabled(source_id: int, enabled: bool) -> None:
    conn = connect()
    try:
        conn.execute("UPDATE sources SET enabled = ? WHERE id = ?", (1 if enabled else 0, source_id))
        conn.commit()
    finally:
        conn.close()


def mark_checked(conn, source_id: int, status: str) -> None:
    conn.execute(
        "UPDATE sources SET last_checked = ?, last_status = ? WHERE id = ?",
        (datetime.now(timezone.utc).isoformat(), status, source_id),
    )
