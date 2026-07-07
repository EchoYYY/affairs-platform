"""Central configuration for the Regulatory Intelligence Platform.

Values come from environment variables (optionally loaded from a .env file).
Everything has a sensible default so the app runs out of the box; the only
thing that unlocks the Claude-powered NLP layer is ANTHROPIC_API_KEY.
"""
from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path

from dotenv import load_dotenv

# backend/ directory (this file lives at backend/regintel/config.py)
BACKEND_DIR = Path(__file__).resolve().parent.parent
# platform/ directory
PLATFORM_DIR = BACKEND_DIR.parent
# repo root — the existing corpus of regulatory PDFs lives here
REPO_ROOT = PLATFORM_DIR.parent

load_dotenv(BACKEND_DIR / ".env")


class Settings:
    """Runtime settings resolved from the environment."""

    def __init__(self) -> None:
        self.anthropic_api_key: str = os.getenv("ANTHROPIC_API_KEY", "").strip()
        self.model: str = os.getenv("REGINTEL_MODEL", "claude-opus-4-6").strip()
        self.embed_model: str = os.getenv(
            "REGINTEL_EMBED_MODEL", "BAAI/bge-small-en-v1.5"
        ).strip()

        corpus = os.getenv("REGINTEL_CORPUS_ROOT", "").strip()
        self.corpus_root: Path = Path(corpus) if corpus else REPO_ROOT

        db = os.getenv("REGINTEL_DB_PATH", "").strip()
        self.db_path: Path = Path(db) if db else (BACKEND_DIR / "data" / "regintel.db")
        self.db_path.parent.mkdir(parents=True, exist_ok=True)

        # Auto-ingest: re-scan the corpus every N minutes so new files appear
        # without a manual command. 0 disables the scheduler (the Sync button
        # and CLI still work). New files are cheap to detect (hash-based skip).
        try:
            self.autoingest_minutes: int = int(os.getenv("REGINTEL_AUTOINGEST_MINUTES", "15"))
        except ValueError:
            self.autoingest_minutes = 15
        # Whether the scheduled auto-ingest should also run Claude interpretation
        # on newly added docs (only when a key is set; can add cost).
        self.autoingest_interpret: bool = os.getenv(
            "REGINTEL_AUTOINGEST_INTERPRET", "false").strip().lower() in ("1", "true", "yes")

    @property
    def claude_enabled(self) -> bool:
        return bool(self.anthropic_api_key)

    # Folders inside the corpus root we never want to ingest.
    IGNORE_DIRS = {"platform", ".git", "node_modules", "__pycache__", ".venv"}

    # File extensions we know how to extract text from.
    SUPPORTED_EXTS = {".pdf", ".docx", ".xlsx"}


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
