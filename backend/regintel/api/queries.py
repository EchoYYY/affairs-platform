"""Read queries and dashboard aggregations over the SQLite store."""
from __future__ import annotations

import json
from typing import Any, Dict, List, Optional

from ..db import connect


def _loads(val, default):
    try:
        return json.loads(val) if val else default
    except (TypeError, ValueError):
        return default


def corpus_stats() -> Dict[str, Any]:
    conn = connect()
    try:
        g = lambda q: conn.execute(q).fetchone()[0]
        return {
            "documents": g("SELECT COUNT(*) FROM documents"),
            "chunks": g("SELECT COUNT(*) FROM chunks"),
            "interpreted": g("SELECT COUNT(*) FROM interpretations"),
            "scanned_needs_ocr": g("SELECT COUNT(*) FROM documents WHERE is_scanned=1"),
            "requirements": g("SELECT COUNT(*) FROM requirements"),
            "obligations": g("SELECT COUNT(*) FROM obligations"),
            "authorities": g("SELECT COUNT(DISTINCT authority) FROM documents"),
            "total_pages": g("SELECT COALESCE(SUM(page_count),0) FROM documents"),
        }
    finally:
        conn.close()


def facets() -> Dict[str, List[str]]:
    conn = connect()
    try:
        def col(q):
            return [r[0] for r in conn.execute(q).fetchall() if r[0]]
        areas = set()
        for r in conn.execute("SELECT regulatory_areas FROM interpretations"):
            areas.update(_loads(r[0], []))
        return {
            "authorities": col("SELECT DISTINCT authority FROM documents ORDER BY authority"),
            "regions": col("SELECT DISTINCT region FROM documents ORDER BY region"),
            "categories": col("SELECT DISTINCT category FROM documents ORDER BY category"),
            "risk_levels": ["Critical", "High", "Medium", "Low"],
            "regulatory_areas": sorted(areas),
        }
    finally:
        conn.close()


def list_documents(
    authority: Optional[str] = None,
    region: Optional[str] = None,
    category: Optional[str] = None,
    risk_level: Optional[str] = None,
    area: Optional[str] = None,
    q: Optional[str] = None,
    limit: int = 100,
    offset: int = 0,
) -> Dict[str, Any]:
    conn = connect()
    try:
        where, params = [], []
        if authority:
            where.append("d.authority = ?"); params.append(authority)
        if region:
            where.append("d.region = ?"); params.append(region)
        if category:
            where.append("d.category = ?"); params.append(category)
        if risk_level:
            where.append("i.risk_level = ?"); params.append(risk_level)
        if area:
            where.append("i.regulatory_areas LIKE ?"); params.append(f'%"{area}"%')
        if q:
            where.append("(d.title LIKE ? OR d.filename LIKE ?)")
            params.extend([f"%{q}%", f"%{q}%"])
        clause = ("WHERE " + " AND ".join(where)) if where else ""

        total = conn.execute(
            f"SELECT COUNT(*) FROM documents d LEFT JOIN interpretations i "
            f"ON i.document_id = d.id {clause}", params,
        ).fetchone()[0]

        rows = conn.execute(
            f"""SELECT d.id, d.title, d.authority, d.region, d.category, d.rel_path,
                       d.page_count, d.is_scanned, i.risk_level, i.urgency, i.summary,
                       i.regulatory_areas
                FROM documents d LEFT JOIN interpretations i ON i.document_id = d.id
                {clause}
                ORDER BY CASE i.risk_level WHEN 'Critical' THEN 0 WHEN 'High' THEN 1
                         WHEN 'Medium' THEN 2 WHEN 'Low' THEN 3 ELSE 4 END, d.authority, d.title
                LIMIT ? OFFSET ?""",
            params + [limit, offset],
        ).fetchall()

        items = []
        for r in rows:
            d = dict(r)
            d["regulatory_areas"] = _loads(d.pop("regulatory_areas"), [])
            d["interpreted"] = d.get("risk_level") is not None
            items.append(d)
        return {"total": total, "count": len(items), "offset": offset, "items": items}
    finally:
        conn.close()


def get_document(doc_id: int) -> Optional[Dict[str, Any]]:
    conn = connect()
    try:
        doc = conn.execute("SELECT * FROM documents WHERE id = ?", (doc_id,)).fetchone()
        if not doc:
            return None
        d = dict(doc)
        d.pop("full_text", None)  # too large for the detail payload
        d["char_count"] = doc["char_count"]

        interp = conn.execute(
            "SELECT * FROM interpretations WHERE document_id = ?", (doc_id,)
        ).fetchone()
        if interp:
            it = dict(interp)
            for f in ("regulatory_areas", "device_types", "key_dates"):
                it[f] = _loads(it.get(f), [])
            it.pop("raw_json", None)
            d["interpretation"] = it
        else:
            d["interpretation"] = None

        d["requirements"] = [dict(r) for r in conn.execute(
            "SELECT text, area, citation FROM requirements WHERE document_id = ?", (doc_id,))]
        d["obligations"] = [dict(r) for r in conn.execute(
            "SELECT text, actor, area, risk FROM obligations WHERE document_id = ?", (doc_id,))]
        return d
    finally:
        conn.close()


def dashboard() -> Dict[str, Any]:
    conn = connect()
    try:
        def group(sql):
            return [{"label": r[0], "count": r[1]} for r in conn.execute(sql).fetchall() if r[0]]

        by_authority = group(
            "SELECT authority, COUNT(*) FROM documents GROUP BY authority ORDER BY 2 DESC")
        by_region = group(
            "SELECT region, COUNT(*) FROM documents GROUP BY region ORDER BY 2 DESC")
        by_risk = group(
            "SELECT risk_level, COUNT(*) FROM interpretations GROUP BY risk_level")
        by_actor = group(
            "SELECT actor, COUNT(*) FROM obligations GROUP BY actor ORDER BY 2 DESC LIMIT 10")

        # regulatory area frequency (areas are JSON arrays)
        area_counts: Dict[str, int] = {}
        for r in conn.execute("SELECT regulatory_areas FROM interpretations"):
            for a in _loads(r[0], []):
                area_counts[a] = area_counts.get(a, 0) + 1
        by_area = sorted(
            [{"label": k, "count": v} for k, v in area_counts.items()],
            key=lambda x: -x["count"],
        )[:12]

        # highest-risk documents surfaced for the dashboard
        top_risk = [dict(r) for r in conn.execute(
            """SELECT d.id, d.title, d.authority, d.region, i.risk_level, i.urgency,
                      i.business_impact
               FROM interpretations i JOIN documents d ON d.id = i.document_id
               WHERE i.risk_level IN ('Critical','High')
               ORDER BY CASE i.risk_level WHEN 'Critical' THEN 0 ELSE 1 END,
                        CASE i.urgency WHEN 'High' THEN 0 WHEN 'Medium' THEN 1 ELSE 2 END
               LIMIT 12""")]

        # critical/high obligations for the compliance worklist
        critical_obligations = [dict(r) for r in conn.execute(
            """SELECT o.text, o.actor, o.area, o.risk, d.title, d.authority, d.id AS document_id
               FROM obligations o JOIN documents d ON d.id = o.document_id
               WHERE o.risk IN ('Critical','High')
               ORDER BY CASE o.risk WHEN 'Critical' THEN 0 ELSE 1 END LIMIT 20""")]

        return {
            "by_authority": by_authority, "by_region": by_region, "by_risk": by_risk,
            "by_area": by_area, "by_actor": by_actor, "top_risk_documents": top_risk,
            "critical_obligations": critical_obligations,
        }
    finally:
        conn.close()
