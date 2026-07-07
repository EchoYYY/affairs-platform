"""Organizational watch profile + product portfolio.

The profile is what turns raw monitoring into *intelligence*: it defines which
markets, regulatory areas and device classes matter, so alerts can be scored for
relevance and changes can be mapped onto real products for impact assessment.

A sensible default is seeded on first use from the shape of the existing corpus
(medical devices / SaMD, US + EU + international, the areas present in the library),
and is fully editable via the API/UI.
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from .db import connect


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _loads(v, default):
    try:
        return json.loads(v) if v else default
    except (TypeError, ValueError):
        return default


DEFAULT_PROFILE = {
    "org_name": "My MedTech Organization",
    "markets": ["US", "EU", "Australia", "Japan", "International"],
    "regulatory_areas": [
        "Clinical Evaluation", "Cybersecurity", "Software/SaMD",
        "Post-Market Surveillance", "Risk Management", "UDI", "Usability",
        "Quality System", "AI/Machine Learning",
    ],
    "device_classes": ["Class IIa", "Class IIb", "Class III", "SaMD"],
    "keywords": [
        "software as a medical device", "cybersecurity", "clinical evaluation",
        "post-market surveillance", "artificial intelligence", "MDR", "510(k)",
    ],
    "processes": [
        "Design & Development", "Clinical Affairs", "Post-Market Surveillance",
        "Quality Management", "Regulatory Submissions", "Labeling",
    ],
}

DEFAULT_PRODUCTS = [
    {
        "name": "Example SaMD Diagnostic App", "device_class": "Class IIa",
        "markets": ["US", "EU"], "regulatory_areas": ["Software/SaMD", "AI/Machine Learning", "Cybersecurity"],
        "description": "AI-assisted diagnostic software as a medical device.",
    },
    {
        "name": "Example Connected Monitor", "device_class": "Class IIb",
        "markets": ["US", "EU", "Australia"], "regulatory_areas": ["Cybersecurity", "Post-Market Surveillance", "Usability"],
        "description": "Network-connected patient monitoring device.",
    },
]


def get_profile() -> Dict[str, Any]:
    conn = connect()
    try:
        row = conn.execute("SELECT * FROM watch_profile WHERE id = 1").fetchone()
        if not row:
            _seed_profile(conn)
            row = conn.execute("SELECT * FROM watch_profile WHERE id = 1").fetchone()
        p = dict(row)
        for f in ("markets", "regulatory_areas", "device_classes", "keywords", "processes"):
            p[f] = _loads(p.get(f), [])
        return p
    finally:
        conn.close()


def _seed_profile(conn) -> None:
    d = DEFAULT_PROFILE
    conn.execute(
        """INSERT OR REPLACE INTO watch_profile
           (id, org_name, markets, regulatory_areas, device_classes, keywords, processes, updated_at)
           VALUES (1,?,?,?,?,?,?,?)""",
        (d["org_name"], json.dumps(d["markets"]), json.dumps(d["regulatory_areas"]),
         json.dumps(d["device_classes"]), json.dumps(d["keywords"]),
         json.dumps(d["processes"]), _now()),
    )
    if not conn.execute("SELECT COUNT(*) FROM products").fetchone()[0]:
        for p in DEFAULT_PRODUCTS:
            conn.execute(
                """INSERT INTO products (name, device_class, markets, regulatory_areas, description, created_at)
                   VALUES (?,?,?,?,?,?)""",
                (p["name"], p["device_class"], json.dumps(p["markets"]),
                 json.dumps(p["regulatory_areas"]), p["description"], _now()),
            )
    conn.commit()


def update_profile(data: Dict[str, Any]) -> Dict[str, Any]:
    get_profile()  # ensure seeded
    conn = connect()
    try:
        fields, params = [], []
        for f in ("org_name",):
            if f in data:
                fields.append(f"{f} = ?"); params.append(data[f])
        for f in ("markets", "regulatory_areas", "device_classes", "keywords", "processes"):
            if f in data:
                fields.append(f"{f} = ?"); params.append(json.dumps(data[f]))
        fields.append("updated_at = ?"); params.append(_now())
        conn.execute(f"UPDATE watch_profile SET {', '.join(fields)} WHERE id = 1", params)
        conn.commit()
    finally:
        conn.close()
    return get_profile()


# ----- products -----

def list_products() -> List[Dict[str, Any]]:
    get_profile()
    conn = connect()
    try:
        out = []
        for r in conn.execute("SELECT * FROM products ORDER BY name"):
            d = dict(r)
            d["markets"] = _loads(d.get("markets"), [])
            d["regulatory_areas"] = _loads(d.get("regulatory_areas"), [])
            out.append(d)
        return out
    finally:
        conn.close()


def add_product(data: Dict[str, Any]) -> Dict[str, Any]:
    conn = connect()
    try:
        cur = conn.execute(
            """INSERT INTO products (name, device_class, markets, regulatory_areas, description, created_at)
               VALUES (?,?,?,?,?,?)""",
            (data.get("name", "Unnamed"), data.get("device_class", ""),
             json.dumps(data.get("markets", [])), json.dumps(data.get("regulatory_areas", [])),
             data.get("description", ""), _now()),
        )
        conn.commit()
        pid = cur.lastrowid
    finally:
        conn.close()
    return {"id": pid, **data}


def delete_product(product_id: int) -> None:
    conn = connect()
    try:
        conn.execute("DELETE FROM products WHERE id = ?", (product_id,))
        conn.commit()
    finally:
        conn.close()
