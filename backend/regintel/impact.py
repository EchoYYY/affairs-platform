"""Pillar 4 — automated impact assessment.

Maps a regulatory update onto the organization's product portfolio: for each product
it produces an impact level, the affected regulatory areas, and concrete required
actions with an owner and priority. Claude when a key is set; a deterministic rule
mapping otherwise (area/market overlap between the update and each product).
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any, Dict, List

from .config import get_settings
from .db import connect
from .profile import get_profile, list_products


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _rule_impact(update: Dict[str, Any], product: Dict[str, Any],
                 alert: Dict[str, Any]) -> Dict[str, Any]:
    text = f"{update.get('title','')} {update.get('summary_raw','')}".lower()
    p_areas = set(a.lower() for a in product.get("regulatory_areas", []))
    hit_areas = [a for a in product.get("regulatory_areas", []) if a.lower() in text]
    market_hit = update.get("region") in product.get("markets", [])

    overlap = len(hit_areas)
    if overlap >= 2 and market_hit:
        level = "High"
    elif overlap >= 1 or market_hit:
        level = "Medium"
    elif p_areas:
        level = "Low"
    else:
        level = "None"

    actions = []
    if level in ("High", "Medium"):
        for a in (hit_areas or ["Regulatory"]):
            actions.append({
                "action": f"Review {a} controls for {product['name']} against this update",
                "owner": "Regulatory Affairs", "priority": "High" if level == "High" else "Medium",
            })
    return {
        "product_id": product["id"], "impact_level": level,
        "affected_areas": hit_areas, "required_actions": actions,
        "rationale": f"{overlap} area overlap; market {'match' if market_hit else 'no match'}.",
        "assessed_by": "rules",
    }


_IMPACT_TOOL = {
    "name": "record_impact",
    "description": "Record per-product impact of a regulatory update.",
    "input_schema": {
        "type": "object",
        "properties": {
            "impacts": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "product_name": {"type": "string"},
                        "impact_level": {"type": "string", "enum": ["None", "Low", "Medium", "High"]},
                        "affected_areas": {"type": "array", "items": {"type": "string"}},
                        "required_actions": {
                            "type": "array",
                            "items": {
                                "type": "object",
                                "properties": {
                                    "action": {"type": "string"},
                                    "owner": {"type": "string"},
                                    "priority": {"type": "string", "enum": ["Low", "Medium", "High"]},
                                },
                                "required": ["action", "owner", "priority"],
                            },
                        },
                        "rationale": {"type": "string"},
                    },
                    "required": ["product_name", "impact_level", "rationale"],
                },
            },
        },
        "required": ["impacts"],
    },
}


def _claude_impact(update, products, settings) -> List[Dict[str, Any]]:
    from anthropic import Anthropic

    client = Anthropic(api_key=settings.anthropic_api_key)
    prod_lines = "\n".join(
        f"- {p['name']} (class {p.get('device_class','')}; markets {p.get('markets',[])}; "
        f"areas {p.get('regulatory_areas',[])}): {p.get('description','')}" for p in products)
    prompt = (
        f"Regulatory update:\n  Authority: {update.get('authority')} ({update.get('region')})\n"
        f"  Title: {update.get('title')}\n  Summary: {update.get('summary_raw')}\n\n"
        f"Product portfolio:\n{prod_lines}\n\n"
        "For EACH product, assess the impact of this update. Be concrete about required "
        "actions and honest when impact is None. Call record_impact."
    )
    resp = client.messages.create(
        model=settings.model, max_tokens=2048,
        system="You are a medical-device regulatory affairs lead performing change-impact "
               "assessment against a product portfolio.",
        tools=[_IMPACT_TOOL], tool_choice={"type": "tool", "name": "record_impact"},
        messages=[{"role": "user", "content": prompt}],
    )
    name_to_id = {p["name"]: p["id"] for p in products}
    out = []
    for block in resp.content:
        if block.type == "tool_use":
            for imp in block.input.get("impacts", []):
                out.append({
                    "product_id": name_to_id.get(imp.get("product_name")),
                    "impact_level": imp.get("impact_level", "None"),
                    "affected_areas": imp.get("affected_areas", []),
                    "required_actions": imp.get("required_actions", []),
                    "rationale": imp.get("rationale", ""),
                    "assessed_by": "claude",
                })
    return out


def assess_update(update_id: int) -> List[Dict[str, Any]]:
    settings = get_settings()
    products = list_products()
    conn = connect()
    try:
        u = conn.execute("SELECT * FROM updates WHERE id = ?", (update_id,)).fetchone()
        if not u:
            raise ValueError(f"No update {update_id}")
        update = dict(u)
        alert = conn.execute("SELECT * FROM alerts WHERE update_id = ?", (update_id,)).fetchone()
        alert = dict(alert) if alert else {}

        try:
            if settings.claude_enabled and products:
                results = _claude_impact(update, products, settings)
            else:
                results = [_rule_impact(update, p, alert) for p in products]
        except Exception:
            results = [_rule_impact(update, p, alert) for p in products]

        conn.execute("DELETE FROM impact_assessments WHERE update_id = ?", (update_id,))
        for r in results:
            if not r.get("product_id"):
                continue
            conn.execute(
                """INSERT INTO impact_assessments
                   (update_id, product_id, impact_level, affected_areas, required_actions,
                    rationale, assessed_by, created_at)
                   VALUES (?,?,?,?,?,?,?,?)""",
                (update_id, r["product_id"], r["impact_level"],
                 json.dumps(r.get("affected_areas", [])),
                 json.dumps(r.get("required_actions", [])),
                 r.get("rationale", ""), r["assessed_by"], _now()),
            )
        conn.commit()
        return results
    finally:
        conn.close()


def get_impact(update_id: int) -> List[Dict[str, Any]]:
    conn = connect()
    try:
        rows = conn.execute(
            """SELECT ia.*, p.name AS product_name, p.device_class
               FROM impact_assessments ia JOIN products p ON p.id = ia.product_id
               WHERE ia.update_id = ?
               ORDER BY CASE ia.impact_level WHEN 'High' THEN 0 WHEN 'Medium' THEN 1
                        WHEN 'Low' THEN 2 ELSE 3 END""",
            (update_id,),
        ).fetchall()
        out = []
        for r in rows:
            d = dict(r)
            d["affected_areas"] = json.loads(d["affected_areas"]) if d["affected_areas"] else []
            d["required_actions"] = json.loads(d["required_actions"]) if d["required_actions"] else []
            out.append(d)
        return out
    finally:
        conn.close()
