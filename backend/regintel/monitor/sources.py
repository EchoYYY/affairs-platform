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
        "authority": "FDA", "region": "US", "type": "openfda",
        "url": "https://api.fda.gov/device/enforcement.json?sort=report_date:desc&limit=25",
        "areas": ["Post-Market Surveillance", "Safety"], "enabled": 1,
    },
    {
        "key": "fda-cdrh-news",
        "name": "FDA CDRH News & Updates",
        "authority": "FDA", "region": "US", "type": "html",
        "url": "https://www.fda.gov/medical-devices/medical-devices-news-and-events/cdrh-new-news-and-updates",
        "areas": ["Guidance", "News", "Safety"], "enabled": 1,
    },
    {
        "key": "fda-device-recalls-alerts",
        "name": "FDA Device Recalls & Early Alerts",
        "authority": "FDA", "region": "US", "type": "html",
        "url": "https://www.fda.gov/medical-devices/medical-device-safety/medical-device-recalls-and-early-alerts",
        "areas": ["Safety", "Post-Market Surveillance"], "enabled": 1,
    },
    {
        "key": "mhra-drug-device-alerts",
        "name": "MHRA Drug & Device Safety Alerts",
        "authority": "MHRA", "region": "UK", "type": "rss",
        "url": "https://www.gov.uk/drug-device-alerts.atom",
        "areas": ["Safety", "Post-Market Surveillance"], "enabled": 1,
    },
    {
        "key": "mhra-news",
        "name": "MHRA News & Guidance (gov.uk)",
        "authority": "MHRA", "region": "UK", "type": "rss",
        "url": "https://www.gov.uk/search/news-and-communications.atom?organisations%5B%5D=medicines-and-healthcare-products-regulatory-agency",
        "areas": ["Guidance"], "enabled": 1,
    },
    # Configurable placeholders — verify the URL for your region, then enable.
    {
        "key": "ema-news",
        "name": "EMA News (verify feed URL)",
        "authority": "EMA", "region": "EU", "type": "rss",
        "url": "https://www.ema.europa.eu/en/rss.xml",
        "areas": ["Guidance", "Safety"], "enabled": 0,
    },
    {
        "key": "tga-news",
        "name": "TGA News (verify feed URL)",
        "authority": "TGA", "region": "Australia", "type": "rss",
        "url": "https://www.tga.gov.au/rss.xml",
        "areas": ["Guidance", "Safety"], "enabled": 0,
    },
]


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
