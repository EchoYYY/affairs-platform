"""Fetch adapters that normalize each source type into a common item shape.

Normalized item:
    {external_id, title, url, published (ISO or ""), summary_raw}
"""
from __future__ import annotations

from typing import Any, Dict, List

import httpx

USER_AGENT = "RegIntel-Monitor/0.1 (+regulatory-intelligence-platform)"
TIMEOUT = 20.0


def fetch_source(source: Dict[str, Any]) -> List[Dict[str, Any]]:
    stype = source["type"]
    if stype == "rss":
        return _fetch_rss(source["url"])
    if stype == "openfda":
        return _fetch_openfda(source["url"])
    if stype == "html":
        return _fetch_html(source["url"])
    raise ValueError(f"Unknown source type: {stype}")


# nav / breadcrumb link texts to skip when scraping FDA content pages
_HTML_NAV = {
    "medical devices news and events", "cdrh new - news and updates",
    "follow us on social media", "home", "medical devices",
}


_MONTHS = {m: i + 1 for i, m in enumerate(
    ["January", "February", "March", "April", "May", "June", "July", "August",
     "September", "October", "November", "December"])}
# a date inside a heading (e.g. "July 1, 2026</h2>") marks the group that follows
_DATE_HEADING = (
    r"(?P<date>(?:January|February|March|April|May|June|July|August|September|"
    r"October|November|December)\s+\d{1,2},\s+20\d{2})\s*</h[1-6]>")
_LINK = r'<a\b[^>]*href="(?P<href>/medical-devices/[^"#?]+)"[^>]*>(?P<title>.*?)</a>'
_TOKEN_RE = None  # compiled lazily


def _to_iso(datestr: str):
    import re
    m = re.match(r"(\w+)\s+(\d{1,2}),\s+(\d{4})", datestr)
    if not m:
        return ""
    mon = _MONTHS.get(m.group(1))
    if not mon:
        return ""
    return f"{m.group(3)}-{mon:02d}-{int(m.group(2)):02d}"


def _fetch_html(url: str) -> List[Dict[str, Any]]:
    """Scrape dated content items from an FDA (or similar) news page.

    The CDRH 'News and Updates' page has no RSS but groups items under dated
    headings, so we walk the page in order and stamp each item with the most
    recent heading date — giving accurate timeframe filtering downstream.
    """
    import re
    from urllib.parse import urljoin

    global _TOKEN_RE
    if _TOKEN_RE is None:
        _TOKEN_RE = re.compile(f"{_DATE_HEADING}|{_LINK}", re.S | re.I)

    resp = httpx.get(url, headers={"User-Agent": USER_AGENT}, timeout=TIMEOUT,
                     follow_redirects=True)
    resp.raise_for_status()
    html = resp.text

    items: List[Dict[str, Any]] = []
    seen = set()
    current_date = ""
    for m in _TOKEN_RE.finditer(html):
        if m.group("date"):
            current_date = _to_iso(m.group("date"))
            continue
        href = m.group("href")
        title = re.sub(r"<[^>]+>", "", m.group("title") or "")
        title = re.sub(r"\s+", " ", title).strip()
        if len(title) < 20 or title.lower() in _HTML_NAV or href.count("/") < 3:
            continue
        absu = urljoin(url, href)
        if absu in seen:
            continue
        seen.add(absu)
        items.append({
            "external_id": href, "title": title[:300], "url": absu,
            "published": current_date, "summary_raw": "",
        })
        if len(items) >= 60:
            break
    return items


def _fetch_rss(url: str) -> List[Dict[str, Any]]:
    import feedparser

    # Fetch with httpx first (feedparser's own fetch lacks a good UA / timeout).
    resp = httpx.get(url, headers={"User-Agent": USER_AGENT}, timeout=TIMEOUT,
                     follow_redirects=True)
    resp.raise_for_status()
    feed = feedparser.parse(resp.content)
    items: List[Dict[str, Any]] = []
    for e in feed.entries[:50]:
        published = ""
        if getattr(e, "published_parsed", None):
            import time
            published = time.strftime("%Y-%m-%dT%H:%M:%S", e.published_parsed)
        elif getattr(e, "updated_parsed", None):
            import time
            published = time.strftime("%Y-%m-%dT%H:%M:%S", e.updated_parsed)
        items.append({
            "external_id": getattr(e, "id", None) or getattr(e, "link", "") or e.get("title", ""),
            "title": (getattr(e, "title", "") or "").strip(),
            "url": getattr(e, "link", "") or "",
            "published": published,
            "summary_raw": (getattr(e, "summary", "") or "")[:2000],
        })
    return items


def _fetch_openfda(url: str) -> List[Dict[str, Any]]:
    resp = httpx.get(url, headers={"User-Agent": USER_AGENT}, timeout=TIMEOUT,
                     follow_redirects=True)
    resp.raise_for_status()
    data = resp.json()
    items: List[Dict[str, Any]] = []
    for r in data.get("results", []):
        rid = r.get("recall_number") or r.get("event_id") or r.get("id") or ""
        firm = r.get("recalling_firm", "")
        reason = r.get("reason_for_recall", "")
        product = r.get("product_description", "")
        title = f"Recall {rid}: {firm}".strip(": ").strip() or f"openFDA {rid}"
        published = r.get("report_date", "")
        if published and len(published) == 8:  # YYYYMMDD -> ISO
            published = f"{published[:4]}-{published[4:6]}-{published[6:]}"
        items.append({
            "external_id": rid or (firm + product)[:80],
            "title": title[:300],
            "url": "https://www.accessdata.fda.gov/scripts/ires/index.cfm",
            "published": published,
            "summary_raw": f"{product}\n\nReason: {reason}"[:2000],
        })
    return items
