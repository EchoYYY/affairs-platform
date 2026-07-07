"""Thread-safe corpus sync used by the Sync button and the scheduled auto-ingest.

Both the on-demand API call and the background scheduler funnel through
`run_sync()`, which holds a process-wide lock so two ingests never overlap
(they'd contend on SQLite / the embedding model otherwise).
"""
from __future__ import annotations

import threading
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from .config import Settings, get_settings

_lock = threading.Lock()
_last: Dict[str, Any] = {"ran_at": None, "ingest": None, "interpret": None, "busy": False}


def last_status() -> Dict[str, Any]:
    return dict(_last, busy=_lock.locked())


def run_sync(interpret: bool = False, settings: Optional[Settings] = None) -> Dict[str, Any]:
    """Ingest new/changed files; optionally interpret new docs. Blocking."""
    settings = settings or get_settings()
    from .ingest.pipeline import ingest_corpus

    with _lock:
        _last["busy"] = True
        result: Dict[str, Any] = {"ingest": ingest_corpus(settings, verbose=False)}
        if interpret and settings.claude_enabled:
            from .nlp.interpret import interpret_corpus
            result["interpret"] = interpret_corpus(settings, verbose=False)
        _last.update(
            ran_at=datetime.now(timezone.utc).isoformat(),
            ingest=result.get("ingest"),
            interpret=result.get("interpret"),
            busy=False,
        )
    return result
