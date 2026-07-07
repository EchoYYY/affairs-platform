"""SQLite storage layer.

Raw sqlite3 (stdlib) keeps the dependency surface small. Embeddings are stored
as float32 BLOBs on the chunks table; at corpus scale (a few thousand chunks) a
NumPy brute-force cosine scan is more than fast enough, so no vector DB needed.
"""
from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Optional

from .config import get_settings

SCHEMA = """
CREATE TABLE IF NOT EXISTS documents (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    path          TEXT UNIQUE NOT NULL,
    rel_path      TEXT,
    filename      TEXT,
    title         TEXT,
    authority     TEXT,          -- top-level folder: FDA, EU, IMDRF, ISO, TGA, Japan, Clinical Evaluation
    region        TEXT,          -- normalized: US, EU, International, Japan, Australia, ...
    category      TEXT,          -- sub-folder grouping, e.g. Cybersecurity, AI, MDR
    ext           TEXT,
    size_bytes    INTEGER,
    page_count    INTEGER,
    char_count    INTEGER,
    is_scanned    INTEGER DEFAULT 0,   -- 1 = little/no extractable text (needs OCR)
    content_hash  TEXT,
    full_text     TEXT,
    ingested_at   TEXT
);

CREATE INDEX IF NOT EXISTS idx_documents_authority ON documents(authority);
CREATE INDEX IF NOT EXISTS idx_documents_region    ON documents(region);
CREATE INDEX IF NOT EXISTS idx_documents_category  ON documents(category);

CREATE TABLE IF NOT EXISTS chunks (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    document_id  INTEGER NOT NULL,
    ordinal      INTEGER,
    text         TEXT,
    embedding    BLOB,
    dim          INTEGER,
    embed_model  TEXT,
    FOREIGN KEY(document_id) REFERENCES documents(id) ON DELETE CASCADE
);
CREATE INDEX IF NOT EXISTS idx_chunks_document ON chunks(document_id);

CREATE TABLE IF NOT EXISTS interpretations (
    document_id       INTEGER PRIMARY KEY,
    summary           TEXT,
    regulatory_areas  TEXT,     -- JSON array
    risk_level        TEXT,     -- Low | Medium | High | Critical
    urgency           TEXT,     -- Low | Medium | High
    business_impact   TEXT,
    device_types      TEXT,     -- JSON array
    key_dates         TEXT,     -- JSON array of {date,label}
    model             TEXT,
    created_at        TEXT,
    raw_json          TEXT,
    FOREIGN KEY(document_id) REFERENCES documents(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS requirements (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    document_id  INTEGER NOT NULL,
    text         TEXT,
    area         TEXT,
    citation     TEXT,
    FOREIGN KEY(document_id) REFERENCES documents(id) ON DELETE CASCADE
);
CREATE INDEX IF NOT EXISTS idx_requirements_document ON requirements(document_id);

CREATE TABLE IF NOT EXISTS obligations (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    document_id  INTEGER NOT NULL,
    text         TEXT,
    actor        TEXT,          -- who must act: manufacturer, notified body, sponsor, ...
    area         TEXT,
    risk         TEXT,
    FOREIGN KEY(document_id) REFERENCES documents(id) ON DELETE CASCADE
);
CREATE INDEX IF NOT EXISTS idx_obligations_document ON obligations(document_id);

-- ============================================================================
-- Phase 2: monitoring, alerts, impact assessment, predictive insights
-- ============================================================================

-- Singleton (id=1) organizational watch profile. Drives relevance scoring,
-- alert filtering, and impact assessment.
CREATE TABLE IF NOT EXISTS watch_profile (
    id                INTEGER PRIMARY KEY CHECK (id = 1),
    org_name          TEXT,
    markets           TEXT,   -- JSON array of regions/countries in scope
    regulatory_areas  TEXT,   -- JSON array of areas of interest
    device_classes    TEXT,   -- JSON array (e.g. 'Class II', 'Class III', 'SaMD')
    keywords          TEXT,   -- JSON array of watch keywords
    processes         TEXT,   -- JSON array of internal processes (for impact mapping)
    updated_at        TEXT
);

-- The organization's product portfolio — what regulatory changes get mapped onto.
CREATE TABLE IF NOT EXISTS products (
    id                INTEGER PRIMARY KEY AUTOINCREMENT,
    name              TEXT NOT NULL,
    device_class      TEXT,
    markets           TEXT,   -- JSON array
    regulatory_areas  TEXT,   -- JSON array
    description       TEXT,
    created_at        TEXT
);

-- Monitored sources (health-authority feeds / APIs / pages).
CREATE TABLE IF NOT EXISTS sources (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    key           TEXT UNIQUE,     -- stable identifier for seeding/upsert
    name          TEXT,
    authority     TEXT,
    region        TEXT,
    type          TEXT,            -- rss | openfda | html
    url           TEXT,
    areas         TEXT,            -- JSON array of default topical areas
    enabled       INTEGER DEFAULT 1,
    last_checked  TEXT,
    last_status   TEXT
);

-- Normalized stream of items discovered by monitoring.
CREATE TABLE IF NOT EXISTS updates (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    source_id     INTEGER,
    external_id   TEXT,            -- feed guid / stable id
    title         TEXT,
    url           TEXT,
    published     TEXT,            -- ISO date if available
    authority     TEXT,
    region        TEXT,
    summary_raw   TEXT,
    content_hash  TEXT UNIQUE,     -- dedup key
    document_id   INTEGER,         -- set if the linked doc was ingested
    fetched_at    TEXT,
    FOREIGN KEY(source_id) REFERENCES sources(id) ON DELETE SET NULL,
    FOREIGN KEY(document_id) REFERENCES documents(id) ON DELETE SET NULL
);
CREATE INDEX IF NOT EXISTS idx_updates_source ON updates(source_id);

-- One scored alert per update (relevance/risk/urgency vs the watch profile).
CREATE TABLE IF NOT EXISTS alerts (
    id               INTEGER PRIMARY KEY AUTOINCREMENT,
    update_id        INTEGER UNIQUE,
    relevance        REAL,          -- 0..1 relevance to the profile
    risk             TEXT,          -- Low | Medium | High | Critical
    urgency          TEXT,          -- Low | Medium | High
    business_impact  TEXT,
    areas            TEXT,          -- JSON array of matched regulatory areas
    matched_products TEXT,          -- JSON array of product ids/names
    rationale        TEXT,
    scored_by        TEXT,          -- 'claude' | 'rules'
    status           TEXT DEFAULT 'new',   -- new | read | dismissed
    created_at       TEXT,
    FOREIGN KEY(update_id) REFERENCES updates(id) ON DELETE CASCADE
);
CREATE INDEX IF NOT EXISTS idx_alerts_status ON alerts(status);

-- Impact of an update on a specific product.
CREATE TABLE IF NOT EXISTS impact_assessments (
    id               INTEGER PRIMARY KEY AUTOINCREMENT,
    update_id        INTEGER,
    product_id       INTEGER,
    impact_level     TEXT,          -- None | Low | Medium | High
    affected_areas   TEXT,          -- JSON array
    required_actions TEXT,          -- JSON array of {action, owner, priority}
    rationale        TEXT,
    assessed_by      TEXT,
    created_at       TEXT,
    FOREIGN KEY(update_id) REFERENCES updates(id) ON DELETE CASCADE,
    FOREIGN KEY(product_id) REFERENCES products(id) ON DELETE CASCADE
);
CREATE INDEX IF NOT EXISTS idx_impact_update ON impact_assessments(update_id);
CREATE INDEX IF NOT EXISTS idx_impact_product ON impact_assessments(product_id);

-- Pillar 7: compliance workflow — tasks & approvals derived from obligations,
-- impact actions, or created manually.
CREATE TABLE IF NOT EXISTS tasks (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    title         TEXT NOT NULL,
    description   TEXT,
    source_type   TEXT,          -- obligation | impact | update | manual
    source_ref    TEXT,          -- free-form reference back to the origin
    document_id   INTEGER,       -- optional link to a source document
    product       TEXT,          -- affected product name (optional)
    area          TEXT,          -- regulatory area
    owner         TEXT,          -- responsible person/team
    priority      TEXT DEFAULT 'Medium',   -- Low | Medium | High | Critical
    status        TEXT DEFAULT 'todo',     -- todo | in_progress | review | done
    due_date      TEXT,
    created_at    TEXT,
    updated_at    TEXT,
    FOREIGN KEY(document_id) REFERENCES documents(id) ON DELETE SET NULL
);
CREATE INDEX IF NOT EXISTS idx_tasks_status ON tasks(status);
"""


def connect(db_path: Optional[Path] = None) -> sqlite3.Connection:
    path = db_path or get_settings().db_path
    conn = sqlite3.connect(str(path))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL;")
    conn.execute("PRAGMA foreign_keys=ON;")
    return conn


def init_db(db_path: Optional[Path] = None) -> None:
    conn = connect(db_path)
    try:
        conn.executescript(SCHEMA)
        conn.commit()
    finally:
        conn.close()


if __name__ == "__main__":
    init_db()
    print(f"Initialized DB at {get_settings().db_path}")
