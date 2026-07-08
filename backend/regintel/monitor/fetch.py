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
        return _fetch_html(source)
    raise ValueError(f"Unknown source type: {stype}")


# nav / breadcrumb link texts to skip when scraping content pages
_HTML_NAV = {
    "medical devices news and events", "cdrh new - news and updates",
    "follow us on social media", "home", "medical devices",
    "read more news", "team-nb documents", "private part", "all news",
    "obsolete guidance is available here",
}


import re as _re

_MONTHS = {m: i + 1 for i, m in enumerate(
    ["January", "February", "March", "April", "May", "June", "July", "August",
     "September", "October", "November", "December"])}
_MONTH_ALT = "|".join(_MONTHS)
# a full date inside a heading (e.g. "July 1, 2026</h2>") groups the items after it
_DATE_HEADING = rf"(?P<date>(?:{_MONTH_ALT})\s+\d{{1,2}},\s+20\d{{2}})\s*</h[1-6]>"
# a date prefix inside a title (e.g. "July 1, 2026 - FDA Approves ...")
_INLINE_DATE = _re.compile(rf"^((?:{_MONTH_ALT})\s+\d{{1,2}},\s+20\d{{2}})\s*[-–—:]\s*(.+)$")


def _to_iso(datestr: str):
    m = _re.match(r"(\w+)\s+(\d{1,2}),\s+(\d{4})", datestr or "")
    if not m or m.group(1) not in _MONTHS:
        return ""
    return f"{m.group(3)}-{_MONTHS[m.group(1)]:02d}-{int(m.group(2)):02d}"


def _nearby_date(html: str, start: int, end: int) -> str:
    """Find a publication date near a content link (listing pages put the date in
    a sibling element just before/after the link — e.g. <time datetime=...> or a
    'July 7, 2026' div). Returns ISO yyyy-mm-dd or ''."""
    window = html[max(0, start - 320): end + 360]
    m = _re.search(r'datetime="(\d{4}-\d{2}-\d{2})', window)
    if m:
        return m.group(1)
    m = _re.search(rf"(?:{_MONTH_ALT})\s+\d{{1,2}},\s+20\d{{2}}", window)
    if m:
        return _to_iso(m.group(0))
    m = _re.search(rf"(\d{{1,2}})\s+({_MONTH_ALT})\s+(20\d{{2}})", window)
    if m:
        return f"{m.group(3)}-{_MONTHS[m.group(2)]:02d}-{int(m.group(1)):02d}"
    return ""


def _fetch_html(source: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Scrape dated content items from an FDA (or similar) news page.

    Handles both layouts: items grouped under dated headings (CDRH News), and
    items whose title is prefixed with a date (Press Announcements). `content_path`
    restricts which links count as content (e.g. '/news-events/press-announcements/').
    """
    from urllib.parse import urljoin

    import html as _html

    url = source["url"]
    path = source.get("content_path", "/medical-devices/")
    min_len = int(source.get("min_title_len", 15))
    # match any anchor, then keep those whose href contains content_path — handles
    # both relative (/news/…) and absolute (https://site/news-brief/…) links.
    link_pat = r'<a\b[^>]*href="(?P<href>[^"#]+)"[^>]*>(?P<title>.*?)</a>'
    token = _re.compile(f"{_DATE_HEADING}|{link_pat}", _re.S | _re.I)

    resp = httpx.get(url, headers={"User-Agent": USER_AGENT}, timeout=TIMEOUT,
                     follow_redirects=True)
    resp.raise_for_status()
    html = resp.text

    items: List[Dict[str, Any]] = []
    seen = set()
    current_date = ""
    for m in token.finditer(html):
        if m.group("date"):
            current_date = _to_iso(m.group("date"))
            continue
        href = m.group("href")
        if path not in href:
            continue
        if "/author/" in href or "/tag/" in href or "/category/" in href:
            continue
        title = _html.unescape(_re.sub(r"<[^>]+>", "", m.group("title") or ""))
        title = _re.sub(r"\s+", " ", title).strip()
        # date priority: grouped heading > date near the link > none
        published = current_date or _nearby_date(html, m.start(), m.end())
        inline = _INLINE_DATE.match(title)
        if inline:  # date embedded in the title (e.g. press announcements)
            published = _to_iso(inline.group(1))
            title = inline.group(2).strip()
        if len(title) < min_len or title.lower() in _HTML_NAV:
            continue
        absu = urljoin(url, href)
        if absu in seen:
            continue
        seen.add(absu)
        items.append({
            "external_id": href, "title": title[:300], "url": absu,
            "published": published, "summary_raw": "",
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
