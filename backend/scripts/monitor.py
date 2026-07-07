"""CLI: poll all enabled monitoring sources once, scoring new items into alerts.

Run on a schedule (cron / launchd / Task Scheduler) for continuous monitoring, e.g.
hourly:
    0 * * * *  cd /path/platform/backend && .venv/bin/python -m scripts.monitor

Usage:
    python -m scripts.monitor
"""
from __future__ import annotations

import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from regintel.monitor.run import poll_all


def main() -> None:
    t0 = time.time()
    print("Polling enabled sources…")
    stats = poll_all(score=True, verbose=True)
    print("-" * 60)
    print(f"Done in {time.time() - t0:.1f}s")
    for k, v in stats.items():
        print(f"  {k:16s}: {v}")


if __name__ == "__main__":
    main()
