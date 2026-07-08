"""Registration timeline & government-fee dataset (Knowledge Hub).

Source of truth: `regintel/data/registration.json`, generated from
`Medical_Device_Timelines_and_Fees_Combined.xlsx` — two sheets:
  • Registration Timelines: country · device class (pathway) · official /
    realistic / accelerated timelines · what unlocks the accelerated route
  • Government Fees: country · fee item · local currency · USD · notes

Per market we precompute two headline metrics used by the Time and Cost
filters on the page:
  • fastest  — the pathway with the shortest realistic timeline
  • cheapest — the lowest upfront government/registration fee (recurring
               items such as annual/maintenance/renewal/GMP are excluded)
"""
from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Any, Dict, List, Optional

_DATA_FILE = Path(__file__).parent / "data" / "registration.json"
_PROFILE_FILE = Path(__file__).parent / "data" / "market_profiles.json"

# Filter buckets surfaced to the UI ------------------------------------------
# max is inclusive.
TIME_BUCKETS = [
    {"key": "2w", "label": "≤ 2 weeks", "max_months": 0.5},
    {"key": "1m", "label": "≤ 1 month", "max_months": 1.0},
    {"key": "3m", "label": "≤ 3 months", "max_months": 3.0},
    {"key": "6m", "label": "≤ 6 months", "max_months": 6.0},
    {"key": "1y", "label": "≤ 1 year", "max_months": 12.0},
    {"key": "2y", "label": "≤ 2 years", "max_months": 24.0},
]
COST_BUCKETS = [
    {"key": "free", "label": "Free", "max_usd": 0.0},
    {"key": "500", "label": "≤ $500", "max_usd": 500.0},
    {"key": "1k", "label": "≤ $1,000", "max_usd": 1000.0},
    {"key": "5k", "label": "≤ $5,000", "max_usd": 5000.0},
    {"key": "20k", "label": "≤ $20,000", "max_usd": 20000.0},
    {"key": "100k", "label": "≤ $100,000", "max_usd": 100000.0},
]


@lru_cache(maxsize=1)
def _load() -> Dict[str, Any]:
    with _DATA_FILE.open() as f:
        return json.load(f)


@lru_cache(maxsize=1)
def _profiles() -> Dict[str, Any]:
    if not _PROFILE_FILE.exists():
        return {}
    with _PROFILE_FILE.open(encoding="utf-8") as f:
        return json.load(f)


@lru_cache(maxsize=1)
def _markets_with_profiles() -> List[Dict[str, Any]]:
    profs = _profiles()
    out = []
    for m in _load()["markets"]:
        out.append({**m, "profile": profs.get(m["country"])})
    return out


def markets() -> List[Dict[str, Any]]:
    return _markets_with_profiles()


def facets() -> Dict[str, Any]:
    ms = markets()
    return {
        "countries": [m["country"] for m in ms],
        "regions": sorted({m["region"] for m in ms}),
        "time_buckets": TIME_BUCKETS,
        "cost_buckets": COST_BUCKETS,
    }


def all_data() -> Dict[str, Any]:
    """Full payload for the page: every market with timelines + fees + metrics."""
    return {"markets": markets(), "facets": facets()}


# Back-compat shim (older callers) -------------------------------------------
def query(country: Optional[str] = None, region: Optional[str] = None,
          **_ignored: Any) -> List[Dict[str, Any]]:
    ms = markets()
    if country:
        ms = [m for m in ms if m["country"].lower() == country.lower()]
    if region:
        ms = [m for m in ms if m["region"] == region]
    return ms
