# Regulatory Intelligence Platform

AI-driven interpretation, semantic search, and risk visualization over a global
medical-device regulatory corpus (FDA, EU MDR/MDCG, IMDRF, ISO, TGA, PMDA, …).

This is **Milestone 1 — the "corpus brain"**: it ingests your existing document
library, makes it semantically searchable, interprets each document with Claude
(key requirements, obligations, risk & urgency), and surfaces it all through a
dashboard. It's the foundation the later pillars (live monitoring, alerts, impact
assessment, predictive insights) plug into.

## Architecture

```
platform/
  backend/                 Python 3.9 + FastAPI
    regintel/
      config.py            env-driven settings
      db.py                SQLite schema (documents, chunks, interpretations,
                           requirements, obligations)
      ingest/              PDF/DOCX/XLSX extraction → metadata → chunking
      embed/               local embeddings (fastembed / ONNX, no PyTorch)
      search/              NumPy brute-force cosine semantic search
      nlp/                 Claude interpretation (forced tool-use → structured JSON)
      api/                 FastAPI routes, dashboard aggregations, RAG Q&A
    scripts/
      ingest_corpus.py     build the index from the corpus
      interpret_corpus.py  run Claude interpretation (needs API key)
  frontend/                React + TypeScript + Vite + Recharts
    src/pages/             Dashboard, Corpus, Search, Ask, DocumentDetail
```

**Design choices**
- *Local embeddings* (`BAAI/bge-small-en-v1.5` via fastembed) so search & ingest
  run fully offline with no second API key. Claude is reserved for reasoning.
- *SQLite + NumPy* vector search — no vector DB to operate; instant at this scale.
- The Claude NLP layer *degrades gracefully*: without a key, ingest and search
  still work; interpretation is simply skipped.

## Setup

### 1. Backend
```bash
cd platform/backend
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env          # then edit .env
```

Add your Claude API key to `.env` to unlock interpretation & synthesized Q&A:
```
ANTHROPIC_API_KEY=sk-ant-...
REGINTEL_MODEL=claude-opus-4-6
```
(Get a key at https://console.anthropic.com — ingest/search work without it.)

### 2. Ingest the corpus
```bash
python -m scripts.ingest_corpus          # walks the parent regulatory folders
```

### 3. Interpret with Claude (optional, needs key)
```bash
python -m scripts.interpret_corpus       # summaries, requirements, obligations, risk
python -m scripts.interpret_corpus --limit 3   # smoke test a few first
```

### 4. Run the API
```bash
python -m uvicorn regintel.api.main:app --port 8000
# docs at http://127.0.0.1:8000/docs
```

### 5. Run the frontend
```bash
cd platform/frontend
npm install
npm run dev                                # http://localhost:5173
```

### 6. Monitoring (Phase 2)
```bash
python -m scripts.monitor        # poll enabled sources once; score new items into alerts
```
Enabled sources ship real, key-free feeds (openFDA device recalls, MHRA safety alerts
& news). Enable/verify others (EMA, TGA) in the UI or the `sources` table. Run on a
schedule for continuous monitoring:
```
0 * * * *  cd /path/platform/backend && .venv/bin/python -m scripts.monitor
```

## The five capabilities

| # | Pillar | Where it lives |
|---|---|---|
| 1 | Automated global monitoring | `monitor/` — source registry, RSS/openFDA adapters, change detection |
| 2 | NLP understanding | `nlp/` — Claude interpretation (summaries, requirements, obligations, risk) |
| 3 | Intelligent alerts & categorization | `alerts/score.py` — relevance/risk/urgency vs the watch profile |
| 4 | Automated impact assessment | `impact.py` — maps updates onto the product portfolio + required actions |
| 5 | Predictive insights | `insights/trends.py` — trend series + Claude regulatory-horizon briefing |

The **watch profile** (`profile.py`: markets, areas, device classes, product portfolio)
is the backbone — it makes alerts relevant and gives impact assessment something to map
onto. Edit it in the **Profile & Portfolio** page.

## API surface
| Method | Path | Purpose |
|---|---|---|
| GET  | `/api/stats` | corpus + interpretation counts |
| GET  | `/api/facets` | filter values (authorities, regions, areas, risk) |
| GET  | `/api/dashboard` | aggregates for risk visualization |
| GET  | `/api/documents` · `/api/documents/{id}` | browse / detail + interpretation |
| POST | `/api/documents/{id}/interpret` | interpret one document on demand |
| POST | `/api/search` · `/api/ask` | semantic search · RAG Q&A with citations |
| GET/PUT | `/api/profile` · `/api/products` | watch profile & product portfolio |
| GET  | `/api/sources` · POST `/api/monitor/run` | monitoring sources · trigger a poll |
| GET  | `/api/alerts` · `/api/alerts/stats` | scored alerts feed · summary |
| POST | `/api/alerts/{id}/status` · `/api/alerts/rescore` | read/dismiss · re-score all |
| GET/POST | `/api/updates/{id}/impact` · `/assess` | impact assessment per update |
| GET  | `/api/insights/trends` · `/api/insights/briefing` | trend series · horizon forecast |

## Roadmap (further)
- Auto-download & ingest documents linked from monitored updates (they already flow
  through the same ingest → embed → interpret pipeline).
- Scheduled polling as a managed background worker; email/Slack alert delivery.
- Workflow/approvals: assign impact actions to owners, track to closure.
- Richer prediction once monitoring history accumulates over weeks/months.
