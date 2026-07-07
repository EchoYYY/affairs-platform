"""Pillar 3 — score monitored updates for relevance, risk and urgency.

Two scorers behind one interface:
  * Claude scorer (when ANTHROPIC_API_KEY is set): reads the update against the full
    watch profile + portfolio and returns calibrated relevance/risk/urgency plus a
    rationale and matched products.
  * Rule scorer (always available): keyword/area/region overlap against the profile.
    Deterministic, offline, and used as the fallback so the alert feed is never empty.

Only updates above a relevance floor become surfaced alerts — that is the noise filter.
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from ..config import get_settings
from ..db import connect
from ..profile import get_profile, list_products

RELEVANCE_FLOOR = 0.15  # below this we still store the alert but mark it low-signal


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


# ---------------------------------------------------------------- rule scorer

def _rule_score(update: Dict[str, Any], profile: Dict[str, Any],
                products: List[Dict[str, Any]]) -> Dict[str, Any]:
    text = f"{update.get('title','')} {update.get('summary_raw','')}".lower()

    areas = [a for a in profile.get("regulatory_areas", []) if a.lower() in text]
    kw_hits = [k for k in profile.get("keywords", []) if k.lower() in text]
    region_match = update.get("region") in profile.get("markets", []) or \
        update.get("region") in ("US", "EU", "UK", "International")

    matched_products = []
    for p in products:
        p_areas = set(a.lower() for a in p.get("regulatory_areas", []))
        if p_areas & set(a.lower() for a in areas):
            matched_products.append(p["name"])
        if p.get("region") in (update.get("region"),):
            matched_products.append(p["name"])
    matched_products = sorted(set(matched_products))

    # relevance: weighted overlap
    score = 0.0
    score += min(len(areas), 3) * 0.18
    score += min(len(kw_hits), 3) * 0.12
    score += 0.15 if region_match else 0.0
    score += 0.1 if matched_products else 0.0
    relevance = min(1.0, round(score, 2))

    # risk heuristic from safety-signal words
    high_risk_words = ("recall", "death", "serious injury", "safety alert", "field safety",
                       "urgent", "class i recall", "hazard")
    med_risk_words = ("guidance", "requirement", "obligation", "deadline", "mandatory", "consultation")
    if any(w in text for w in high_risk_words):
        risk, urgency = "High", "High"
    elif any(w in text for w in med_risk_words):
        risk, urgency = "Medium", "Medium"
    else:
        risk, urgency = "Low", "Low"

    return {
        "relevance": relevance, "risk": risk, "urgency": urgency,
        "business_impact": ("Potentially affects " + ", ".join(matched_products)) if matched_products
                            else "General regulatory awareness item.",
        "areas": areas or ([update.get("region", "")] if update.get("region") else []),
        "matched_products": matched_products,
        "rationale": f"Rule match: {len(areas)} area(s), {len(kw_hits)} keyword(s), "
                     f"region {'in' if region_match else 'not in'} scope.",
        "scored_by": "rules",
    }


# ---------------------------------------------------------------- claude scorer

_SCORE_TOOL = {
    "name": "record_alert_score",
    "description": "Record the relevance and risk scoring of a regulatory update.",
    "input_schema": {
        "type": "object",
        "properties": {
            "relevance": {"type": "number", "description": "0.0-1.0 relevance to THIS organization's profile and products."},
            "risk": {"type": "string", "enum": ["Low", "Medium", "High", "Critical"]},
            "urgency": {"type": "string", "enum": ["Low", "Medium", "High"]},
            "business_impact": {"type": "string", "description": "1-2 sentences on the concrete impact."},
            "areas": {"type": "array", "items": {"type": "string"}, "description": "Regulatory areas this update touches."},
            "matched_products": {"type": "array", "items": {"type": "string"}, "description": "Names of the org's products likely affected."},
            "rationale": {"type": "string", "description": "Why this score — 1-2 sentences."},
        },
        "required": ["relevance", "risk", "urgency", "business_impact", "areas", "rationale"],
    },
}


def _claude_score(update, profile, products, settings) -> Dict[str, Any]:
    from anthropic import Anthropic

    client = Anthropic(api_key=settings.anthropic_api_key)
    prod_lines = "\n".join(
        f"- {p['name']} ({p.get('device_class','')}; markets {p.get('markets',[])}; "
        f"areas {p.get('regulatory_areas',[])})" for p in products) or "(none defined)"
    prompt = (
        "Organization watch profile:\n"
        f"  Markets: {profile.get('markets')}\n"
        f"  Regulatory areas of interest: {profile.get('regulatory_areas')}\n"
        f"  Device classes: {profile.get('device_classes')}\n"
        f"  Keywords: {profile.get('keywords')}\n\n"
        f"Product portfolio:\n{prod_lines}\n\n"
        "Regulatory update to score:\n"
        f"  Authority: {update.get('authority')} ({update.get('region')})\n"
        f"  Title: {update.get('title')}\n"
        f"  Summary: {update.get('summary_raw')}\n\n"
        "Score this update for THIS organization. Be strict about relevance — an "
        "unrelated jurisdiction or device type should score low. Call record_alert_score."
    )
    resp = client.messages.create(
        model=settings.model, max_tokens=1024,
        system="You are a regulatory affairs analyst triaging incoming regulatory "
               "updates for a medical-device company. You filter noise aggressively.",
        tools=[_SCORE_TOOL], tool_choice={"type": "tool", "name": "record_alert_score"},
        messages=[{"role": "user", "content": prompt}],
    )
    for block in resp.content:
        if block.type == "tool_use":
            d = dict(block.input)
            d["matched_products"] = d.get("matched_products", [])
            d["scored_by"] = "claude"
            return d
    raise RuntimeError("No tool call returned")


# ---------------------------------------------------------------- driver

def score_updates(update_ids: List[int], verbose: bool = False) -> int:
    settings = get_settings()
    profile = get_profile()
    products = list_products()
    conn = connect()
    created = 0
    try:
        for uid in update_ids:
            u = conn.execute("SELECT * FROM updates WHERE id = ?", (uid,)).fetchone()
            if not u:
                continue
            update = dict(u)
            try:
                if settings.claude_enabled:
                    result = _claude_score(update, profile, products, settings)
                else:
                    result = _rule_score(update, profile, products)
            except Exception:
                result = _rule_score(update, profile, products)  # fall back on any API error

            conn.execute(
                """INSERT INTO alerts
                   (update_id, relevance, risk, urgency, business_impact, areas,
                    matched_products, rationale, scored_by, status, created_at)
                   VALUES (?,?,?,?,?,?,?,?,?, 'new', ?)
                   ON CONFLICT(update_id) DO UPDATE SET
                     relevance=excluded.relevance, risk=excluded.risk, urgency=excluded.urgency,
                     business_impact=excluded.business_impact, areas=excluded.areas,
                     matched_products=excluded.matched_products, rationale=excluded.rationale,
                     scored_by=excluded.scored_by""",
                (uid, result["relevance"], result["risk"], result["urgency"],
                 result["business_impact"], json.dumps(result["areas"]),
                 json.dumps(result.get("matched_products", [])), result["rationale"],
                 result["scored_by"], _now()),
            )
            conn.commit()
            created += 1
            if verbose:
                print(f"    alert: [{result['risk']}/{result['relevance']}] {update['title'][:60]}")
    finally:
        conn.close()
    return created


def rescore_all(verbose: bool = False) -> int:
    conn = connect()
    try:
        ids = [r[0] for r in conn.execute("SELECT id FROM updates")]
    finally:
        conn.close()
    return score_updates(ids, verbose=verbose)
