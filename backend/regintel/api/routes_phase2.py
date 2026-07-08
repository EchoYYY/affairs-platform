"""API routes for Phase 2 pillars: monitoring, alerts, profile, impact, insights."""
from __future__ import annotations

import json
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from .. import impact as impact_mod
from .. import profile as profile_mod
from ..db import connect
from ..insights import trends as trends_mod
from ..monitor import run as monitor_run
from ..monitor import sources as sources_mod

router = APIRouter(prefix="/api")


def _loads(v, d):
    try:
        return json.loads(v) if v else d
    except (TypeError, ValueError):
        return d


# ----------------------------- profile -----------------------------

class ProfileIn(BaseModel):
    org_name: Optional[str] = None
    markets: Optional[List[str]] = None
    regulatory_areas: Optional[List[str]] = None
    device_classes: Optional[List[str]] = None
    keywords: Optional[List[str]] = None
    processes: Optional[List[str]] = None


@router.get("/profile")
def get_profile():
    return profile_mod.get_profile()


@router.put("/profile")
def put_profile(body: ProfileIn):
    return profile_mod.update_profile({k: v for k, v in body.dict().items() if v is not None})


class ProductIn(BaseModel):
    name: str
    device_class: str = ""
    markets: List[str] = []
    regulatory_areas: List[str] = []
    description: str = ""


@router.get("/products")
def get_products():
    return profile_mod.list_products()


@router.post("/products")
def post_product(body: ProductIn):
    return profile_mod.add_product(body.dict())


@router.delete("/products/{product_id}")
def del_product(product_id: int):
    profile_mod.delete_product(product_id)
    return {"deleted": product_id}


# ----------------------------- sources / monitoring -----------------------------

@router.get("/sources")
def get_sources():
    return sources_mod.list_sources()


@router.post("/sources/{source_id}/toggle")
def toggle_source(source_id: int, enabled: bool = True):
    sources_mod.set_enabled(source_id, enabled)
    return {"source_id": source_id, "enabled": enabled}


@router.post("/monitor/run")
def run_monitor():
    """Poll all enabled sources now. (In production this runs on a schedule.)"""
    return monitor_run.poll_all(score=True, verbose=False)


@router.get("/jurisdictions")
def jurisdictions_list():
    from .. import jurisdictions
    return {"regions": jurisdictions.grouped()}


@router.get("/registration/facets")
def registration_facets():
    from .. import registration_data
    return registration_data.facets()


@router.get("/registration")
def registration():
    from .. import registration_data
    return registration_data.all_data()


class CountryScanReq(BaseModel):
    jurisdictions: List[str]
    days: int = 90
    product_code: str = ""
    indication: str = ""


@router.post("/monitor/country-scan")
async def country_scan(req: CountryScanReq):
    """Country-level regulatory scan: jurisdictions + timeframe + optional
    product-code / indication filter. Runs off the event loop."""
    import asyncio

    from .. import country_scan as cs
    if not req.jurisdictions:
        raise HTTPException(400, "Select at least one jurisdiction")
    return await asyncio.to_thread(
        cs.scan, req.jurisdictions, req.days, req.product_code.strip(), req.indication.strip())


@router.post("/monitor/horizon-scan")
async def horizon_scan(poll: bool = True):
    """Regulatory Horizon Scanning — the Scan button. Surfaces forward-looking
    signals (consultations, drafts, upcoming deadlines). Polls feeds off-thread."""
    import asyncio

    from .. import horizon
    return await asyncio.to_thread(horizon.scan, poll, False)


@router.get("/monitor/horizon")
def horizon_last():
    from .. import horizon
    return horizon.last() or {"scanned_at": None, "items": [], "summary": "Not scanned yet."}


@router.get("/updates")
def list_updates(authority: Optional[str] = None, limit: int = 100):
    conn = connect()
    try:
        where, params = [], []
        if authority:
            where.append("u.authority = ?"); params.append(authority)
        clause = ("WHERE " + " AND ".join(where)) if where else ""
        rows = conn.execute(
            f"""SELECT u.*, a.relevance, a.risk, a.urgency, a.status
                FROM updates u LEFT JOIN alerts a ON a.update_id = u.id
                {clause} ORDER BY u.id DESC LIMIT ?""", params + [limit]).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


# ----------------------------- alerts -----------------------------

@router.get("/alerts")
def list_alerts(
    status: Optional[str] = None, risk: Optional[str] = None,
    min_relevance: float = 0.0, authority: Optional[str] = None, limit: int = 100,
):
    conn = connect()
    try:
        where = ["a.relevance >= ?"]
        params: List[Any] = [min_relevance]
        if status:
            where.append("a.status = ?"); params.append(status)
        if risk:
            where.append("a.risk = ?"); params.append(risk)
        if authority:
            where.append("u.authority = ?"); params.append(authority)
        clause = "WHERE " + " AND ".join(where)
        rows = conn.execute(
            f"""SELECT a.*, u.title, u.url, u.authority, u.region, u.published, u.summary_raw
                FROM alerts a JOIN updates u ON u.id = a.update_id
                {clause}
                ORDER BY CASE a.risk WHEN 'Critical' THEN 0 WHEN 'High' THEN 1
                         WHEN 'Medium' THEN 2 ELSE 3 END, a.relevance DESC, a.id DESC
                LIMIT ?""", params + [limit]).fetchall()
        out = []
        for r in rows:
            d = dict(r)
            d["areas"] = _loads(d.get("areas"), [])
            d["matched_products"] = _loads(d.get("matched_products"), [])
            out.append(d)
        return out
    finally:
        conn.close()


class SafetyScanReq(BaseModel):
    jurisdictions: List[str]
    days: int = 30


@router.post("/alerts/safety-scan")
async def safety_scan(req: SafetyScanReq):
    """Safety-information scan across selected jurisdictions (links only)."""
    import asyncio

    from .. import safety_scan as ss
    if not req.jurisdictions:
        raise HTTPException(400, "Select at least one jurisdiction")
    return await asyncio.to_thread(ss.scan, req.jurisdictions, req.days)


@router.get("/alerts/stats")
def alert_stats():
    conn = connect()
    try:
        g = lambda q, p=(): conn.execute(q, p).fetchone()[0]
        by_status = {r[0]: r[1] for r in conn.execute(
            "SELECT status, COUNT(*) FROM alerts GROUP BY status")}
        by_risk = {r[0]: r[1] for r in conn.execute(
            "SELECT risk, COUNT(*) FROM alerts GROUP BY risk")}
        return {
            "total": g("SELECT COUNT(*) FROM alerts"),
            "new": by_status.get("new", 0),
            "high_or_critical": g("SELECT COUNT(*) FROM alerts WHERE risk IN ('High','Critical')"),
            "by_status": by_status, "by_risk": by_risk,
        }
    finally:
        conn.close()


class StatusIn(BaseModel):
    status: str  # read | dismissed | new


@router.post("/alerts/{alert_id}/status")
def set_alert_status(alert_id: int, body: StatusIn):
    if body.status not in ("new", "read", "dismissed"):
        raise HTTPException(400, "invalid status")
    conn = connect()
    try:
        conn.execute("UPDATE alerts SET status = ? WHERE id = ?", (body.status, alert_id))
        conn.commit()
    finally:
        conn.close()
    return {"alert_id": alert_id, "status": body.status}


@router.post("/alerts/rescore")
def rescore():
    from ..alerts.score import rescore_all
    return {"rescored": rescore_all(verbose=False)}


# ----------------------------- impact -----------------------------

@router.get("/updates/{update_id}/impact")
def get_impact(update_id: int):
    return impact_mod.get_impact(update_id)


@router.post("/updates/{update_id}/assess")
def assess(update_id: int):
    try:
        impact_mod.assess_update(update_id)
    except ValueError as e:
        raise HTTPException(404, str(e))
    return impact_mod.get_impact(update_id)


# ----------------------------- insights -----------------------------

@router.get("/insights/trends")
def insights_trends():
    return trends_mod.compute_trends()


@router.get("/insights/briefing")
def insights_briefing():
    return trends_mod.horizon_briefing()


# ----------------------------- workflow (pillar 7) -----------------------------

from .. import workflow as workflow_mod


class TaskIn(BaseModel):
    title: str
    description: str = ""
    owner: str = ""
    priority: str = "Medium"
    status: str = "todo"
    due_date: str = ""
    product: str = ""
    area: str = ""
    source_type: str = "manual"
    source_ref: str = ""
    document_id: Optional[int] = None


class TaskPatch(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    owner: Optional[str] = None
    priority: Optional[str] = None
    status: Optional[str] = None
    due_date: Optional[str] = None
    product: Optional[str] = None
    area: Optional[str] = None


@router.get("/tasks/board")
def tasks_board():
    return {"columns": workflow_mod.STATUSES, "board": workflow_mod.board(),
            "stats": workflow_mod.stats()}


@router.get("/tasks")
def tasks_list(status: Optional[str] = None):
    return workflow_mod.list_tasks(status=status)


@router.post("/tasks")
def tasks_create(body: TaskIn):
    return workflow_mod.create_task(body.dict())


@router.patch("/tasks/{task_id}")
def tasks_update(task_id: int, body: TaskPatch):
    task = workflow_mod.update_task(task_id, {k: v for k, v in body.dict().items() if v is not None})
    if not task:
        raise HTTPException(404, "Task not found")
    return task


@router.delete("/tasks/{task_id}")
def tasks_delete(task_id: int):
    workflow_mod.delete_task(task_id)
    return {"deleted": task_id}


@router.post("/tasks/seed")
def tasks_seed():
    return {"created": workflow_mod.seed_from_obligations()}
