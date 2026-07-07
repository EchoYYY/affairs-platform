"""CLI: run Claude interpretation over ingested documents (needs ANTHROPIC_API_KEY).

Usage:
    python -m scripts.interpret_corpus                # all un-interpreted docs
    python -m scripts.interpret_corpus --limit 3      # first N (smoke test)
    python -m scripts.interpret_corpus --reinterpret  # redo everything
"""
from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from regintel.config import get_settings
from regintel.nlp.interpret import interpret_corpus


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=None)
    ap.add_argument("--reinterpret", action="store_true")
    ap.add_argument("--quiet", action="store_true")
    args = ap.parse_args()

    settings = get_settings()
    if not settings.claude_enabled:
        print("ERROR: ANTHROPIC_API_KEY not set. Add it to platform/backend/.env")
        sys.exit(1)

    print(f"Model: {settings.model}")
    print("-" * 60)
    t0 = time.time()
    stats = interpret_corpus(
        settings, limit=args.limit, reinterpret=args.reinterpret, verbose=not args.quiet
    )
    print("-" * 60)
    print(f"Done in {time.time() - t0:.1f}s")
    for k, v in stats.items():
        print(f"  {k:12s}: {v}")


if __name__ == "__main__":
    main()
