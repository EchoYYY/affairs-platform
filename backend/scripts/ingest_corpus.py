"""CLI: ingest the regulatory document corpus into the local database.

Usage:
    python -m scripts.ingest_corpus                 # full corpus
    python -m scripts.ingest_corpus --limit 5       # first N new docs (smoke test)
    python -m scripts.ingest_corpus --reembed       # re-extract & re-embed everything
"""
from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from regintel.config import get_settings
from regintel.ingest.pipeline import ingest_corpus


def main() -> None:
    ap = argparse.ArgumentParser(description="Ingest the regulatory corpus")
    ap.add_argument("--limit", type=int, default=None, help="max new docs to ingest")
    ap.add_argument("--reembed", action="store_true", help="re-process existing docs")
    ap.add_argument("--quiet", action="store_true")
    args = ap.parse_args()

    settings = get_settings()
    print(f"Corpus root : {settings.corpus_root}")
    print(f"Database    : {settings.db_path}")
    print(f"Embed model : {settings.embed_model}")
    print(f"Claude NLP  : {'enabled' if settings.claude_enabled else 'DISABLED (no ANTHROPIC_API_KEY)'}")
    print("-" * 60)

    t0 = time.time()
    stats = ingest_corpus(
        settings, reembed=args.reembed, limit=args.limit, verbose=not args.quiet
    )
    dt = time.time() - t0

    print("-" * 60)
    print(f"Done in {dt:.1f}s")
    for k, v in stats.items():
        print(f"  {k:16s}: {v}")


if __name__ == "__main__":
    main()
