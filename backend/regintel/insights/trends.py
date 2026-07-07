"""Pillar 5 — predictive insights.

Aggregates two signals — the interpreted corpus (what the regulatory landscape looks
like now) and the monitoring stream (what is moving) — into trend series, then asks
Claude to project the regulatory horizon: likely shifts, emerging risks, and areas of
increasing scrutiny. Without a key it returns the quantitative trends plus a
heuristic briefing so the page is always useful.
"""
from __future__ import annotations

import json
from collections import Counter, defaultdict
from typing import Any, Dict, List

from ..config import get_settings
from ..db import connect
from ..profile import get_profile


def _loads(v, d):
    try:
        return json.loads(v) if v else d
    except (TypeError, ValueError):
        return d


def compute_trends() -> Dict[str, Any]:
    conn = connect()
    try:
        # area frequency across the interpreted corpus
        corpus_areas: Counter = Counter()
        for r in conn.execute("SELECT regulatory_areas FROM interpretations"):
            corpus_areas.update(_loads(r[0], []))

        # monitoring activity by month + area momentum from updates
        by_month: Counter = Counter()
        update_areas: Counter = Counter()
        by_authority: Counter = Counter()
        for a in conn.execute("SELECT areas, created_at FROM alerts"):
            update_areas.update(_loads(a["areas"], []))
        for u in conn.execute("SELECT published, authority FROM updates"):
            month = (u["published"] or "")[:7]
            if month:
                by_month[month] += 1
            if u["authority"]:
                by_authority[u["authority"]] += 1

        # risk mix of current alerts
        risk_mix: Counter = Counter()
        for r in conn.execute("SELECT risk FROM alerts"):
            risk_mix[r[0]] += 1

        total_updates = conn.execute("SELECT COUNT(*) FROM updates").fetchone()[0]

        return {
            "corpus_area_frequency": [
                {"label": k, "count": v} for k, v in corpus_areas.most_common(12)],
            "monitoring_by_month": [
                {"label": k, "count": v} for k, v in sorted(by_month.items())],
            "monitoring_area_momentum": [
                {"label": k, "count": v} for k, v in update_areas.most_common(12)],
            "monitoring_by_authority": [
                {"label": k, "count": v} for k, v in by_authority.most_common(10)],
            "alert_risk_mix": [{"label": k, "count": v} for k, v in risk_mix.items() if k],
            "total_updates": total_updates,
        }
    finally:
        conn.close()


def _recent_signal(conn, limit: int = 40) -> List[str]:
    rows = conn.execute(
        """SELECT u.authority, u.title, a.risk, a.relevance
           FROM updates u LEFT JOIN alerts a ON a.update_id = u.id
           ORDER BY u.id DESC LIMIT ?""", (limit,)).fetchall()
    return [f"[{r['authority']}] {r['title']} (risk={r['risk']}, rel={r['relevance']})"
            for r in rows]


_BRIEF_TOOL = {
    "name": "record_horizon",
    "description": "Record the predictive regulatory horizon briefing.",
    "input_schema": {
        "type": "object",
        "properties": {
            "predicted_shifts": {
                "type": "array",
                "items": {"type": "object", "properties": {
                    "trend": {"type": "string"}, "horizon": {"type": "string", "description": "e.g. 3-6 months, 6-12 months"},
                    "confidence": {"type": "string", "enum": ["Low", "Medium", "High"]},
                    "rationale": {"type": "string"}},
                    "required": ["trend", "horizon", "confidence"]},
            },
            "emerging_risks": {"type": "array", "items": {"type": "string"}},
            "areas_of_increasing_scrutiny": {"type": "array", "items": {"type": "string"}},
            "recommended_preparations": {"type": "array", "items": {"type": "string"}},
            "summary": {"type": "string"},
        },
        "required": ["predicted_shifts", "emerging_risks", "areas_of_increasing_scrutiny", "summary"],
    },
}


def horizon_briefing() -> Dict[str, Any]:
    settings = get_settings()
    trends = compute_trends()
    conn = connect()
    try:
        signal = _recent_signal(conn)
    finally:
        conn.close()
    profile = get_profile()

    if not settings.claude_enabled:
        top_areas = [x["label"] for x in trends["corpus_area_frequency"][:5]]
        return {
            "grounded": False,
            "summary": "Heuristic outlook (add ANTHROPIC_API_KEY for AI predictions). "
                       "Based on corpus concentration, the most active regulatory areas are: "
                       + ", ".join(top_areas) + ".",
            "predicted_shifts": [
                {"trend": f"Continued regulatory focus on {a}", "horizon": "6-12 months",
                 "confidence": "Medium", "rationale": "High representation in the current corpus."}
                for a in top_areas[:4]
            ],
            "emerging_risks": [x["label"] for x in trends["monitoring_area_momentum"][:4]],
            "areas_of_increasing_scrutiny": top_areas[:4],
            "recommended_preparations": [
                "Set up live monitoring sources to build predictive history.",
                "Define your product portfolio for targeted impact assessment.",
            ],
            "trends": trends,
        }

    from anthropic import Anthropic

    client = Anthropic(api_key=settings.anthropic_api_key)
    prompt = (
        "You are producing a forward-looking regulatory horizon briefing for a "
        "medical-device company.\n\n"
        f"Organization areas of interest: {profile.get('regulatory_areas')}\n"
        f"Markets: {profile.get('markets')}\n\n"
        f"Corpus area concentration: {trends['corpus_area_frequency']}\n"
        f"Monitoring momentum by area: {trends['monitoring_area_momentum']}\n"
        f"Monitoring volume by month: {trends['monitoring_by_month']}\n\n"
        "Recent monitored signals:\n" + "\n".join(signal[:30]) + "\n\n"
        "Project the regulatory horizon: predicted shifts (with time horizon and "
        "confidence), emerging compliance risks, areas of increasing scrutiny, and "
        "recommended preparations. Be specific and grounded in the signals above. "
        "Call record_horizon."
    )
    resp = client.messages.create(
        model=settings.model, max_tokens=2048,
        system="You are a regulatory strategy analyst who forecasts regulatory change "
               "for medical devices from observed signals. You are calibrated and avoid "
               "overconfident predictions.",
        tools=[_BRIEF_TOOL], tool_choice={"type": "tool", "name": "record_horizon"},
        messages=[{"role": "user", "content": prompt}],
    )
    for block in resp.content:
        if block.type == "tool_use":
            out = dict(block.input)
            out["grounded"] = True
            out["trends"] = trends
            return out
    return {"grounded": False, "summary": "No briefing produced.", "trends": trends}
