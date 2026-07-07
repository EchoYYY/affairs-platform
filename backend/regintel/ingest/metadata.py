"""Derive structured metadata (authority, region) from a document's location.

The existing corpus is organized by health-authority folder, so the first path
segment under the corpus root is a strong signal for jurisdiction.
"""
from __future__ import annotations

from pathlib import Path
from typing import Tuple

# Top-level folder -> (authority label, region label)
AUTHORITY_REGION = {
    "fda": ("FDA", "US"),
    "eu": ("EU", "EU"),
    "imdrf": ("IMDRF", "International"),
    "iso": ("ISO", "International"),
    "japan": ("PMDA/MHLW", "Japan"),
    "tga": ("TGA", "Australia"),
    "clinical evaluation": ("Clinical Evaluation", "EU"),
}


def derive(path: Path, corpus_root: Path) -> Tuple[str, str, str]:
    """Return (authority, region, category) for a file path within the corpus."""
    try:
        rel = path.relative_to(corpus_root)
    except ValueError:
        rel = Path(path.name)

    parts = rel.parts
    top = parts[0] if len(parts) > 1 else ""
    authority, region = AUTHORITY_REGION.get(
        top.lower(), (top or "Unknown", "Unknown")
    )

    # category = the immediate sub-folder, if any (e.g. FDA/Cybersecurity -> Cybersecurity)
    category = parts[1] if len(parts) > 2 else "General"
    return authority, region, category.strip()
