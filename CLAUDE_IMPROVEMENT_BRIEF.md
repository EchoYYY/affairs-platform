# AFFAIRS — Improvement Brief for an AI Coding Agent

**Audience:** a Claude (or other capable coding agent) working in this repository, in an unknown
harness. This brief assumes nothing about your tools, skills, memory, or IDE. It gives you enough
context to plan and land improvements as a **branch + pull request**, without guessing.

**Read this first, then confirm the deployment context (see §2) before treating any security item as
a blocker.**

---

## 1. What this project is

AFFAIRS is a **regulatory-intelligence platform** for medical-device regulations (FDA, EU MDR/MDCG,
IMDRF, ISO, TGA, PMDA…). It ingests a document corpus, makes it semantically searchable, interprets
each document with Claude, and layers on monitoring, alerts, impact assessment, and predictive
insights.

```
affairs-platform/
  backend/    Python 3.9 + FastAPI + SQLite (single file, WAL). No ORM — raw sqlite3.
    regintel/
      ingest/    extract (pdf/docx/xlsx) -> folder-based metadata -> word-window chunking
      embed/     local fastembed (BAAI/bge-small-en-v1.5, ONNX, CPU) — no API key needed
      search/    brute-force NumPy cosine over an in-process cached matrix
      nlp/       Claude forced-tool-use interpretation (structured JSON)
      monitor/   source registry + rss/openfda/html fetch adapters + dedup
      alerts/    rule + Claude scoring of monitored updates
      impact.py  per-product impact assessment (rule + Claude)
      insights/  trend aggregation + Claude "horizon briefing"
      api/       FastAPI routes (main.py = phase 1, routes_phase2.py = phase 2)
  frontend/   React + TypeScript + Vite + Recharts + react-simple-maps
    src/pages/  one self-contained component per screen; useState+useEffect+fetch, no state lib
```

**Two design choices to respect (don't undo them without asking the owner):**
- Local embeddings so ingest/search run offline; Claude is reserved for reasoning. Adding a second
  embedding API key would be a regression of intent.
- SQLite + NumPy brute-force search instead of a vector DB — a deliberate simplicity bet at the
  current corpus scale.

---

## 2. Before you start — confirm two things with the owner

1. **Deployment context.** Is this a local single-user tool, an internal-network tool, or
   hosted/client-facing? The security items in **Tier P2** are *notes* for a local tool and
   *blockers* for anything exposed. If you can't ask, implement them behind a clear
   "enable this if you expose the service" flag/config rather than forcing them on.
2. **PR shape.** Prefer **several small, reviewable PRs grouped by tier** (P0 fixes, then P1, then
   P2) over one giant branch — unless the owner wants a single branch. Each PR should stand alone and
   pass its checks.

---

## 3. How to work in this repo (setup-agnostic)

You may not have project-specific tooling wired up, so establish the basics yourself:

**Backend**
```bash
cd backend
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env            # ANTHROPIC_API_KEY is optional; ingest/search work without it
python -m uvicorn regintel.api.main:app --port 8000   # http://127.0.0.1:8000/docs
```
**Frontend**
```bash
cd frontend
npm install
npm run build      # runs `tsc -b` — types MUST stay in sync with backend response shapes
npm run dev        # proxies /api -> http://127.0.0.1:8000
```

**Ground rules**
- **There are no tests yet.** Do not claim a change works because it type-checks or looks right.
  Exercise the actual path (curl the endpoint, load the page) and, where you touch logic, add a test
  (see P1-#14). Prefer red→green: write the failing test first for bug fixes.
- **The frontend `types.ts` mirrors backend response shapes 1:1** and is used as generic params in
  `api.ts`. Any backend response-shape change must update `types.ts` or `tsc -b` fails.
- **Don't hardcode a Claude model ID from memory.** Read what's configured, and pin to a model ID you
  have verified is currently valid (see P0-#1). An invalid/retired ID fails at the first Claude call,
  not at startup — so it won't show up in a quick smoke test without a key set.
- Keep commits scoped and message them by tier/item (e.g. `fix(scoring): apply RELEVANCE_FLOOR`).
- If an item below turns out to be intentional, **stop and flag it** rather than "fixing" it.

---

## 4. The improvement backlog (tiered)

Line references are anchors from a read of the current tree — **verify each before editing**, since
line numbers drift.

### Tier P0 — correctness defects that already misbehave

**P0-1 · Dated Claude model ID.** `REGINTEL_MODEL` defaults to `claude-opus-4-6`
(`backend/regintel/config.py`), used across RAG (`api/rag.py`), interpretation (`nlp/interpret.py`),
scoring (`alerts/score.py`), and impact (`impact.py`). This string looks dated. **Verify it against
currently-available model IDs and pin to a valid current one.** Consider tiering by task: a strong
model for interpretation/impact quality, a cheaper/faster tier for high-volume scoring and RAG to
cut cost. Whatever you pick, confirm the exact ID string is live.

**P0-2 · Semantic search is built but unreachable from the UI.** `frontend/src/pages/Search.tsx` is
the only caller of `api.search()`, but it is **not routed** — the `/search` nav entry renders
`KnowledgeHub.tsx` (a registration-timeline lookup) instead. The product's headline capability
(semantic search over the corpus) has no front door. **Decide with the owner:** wire `Search.tsx`
into the nav/routes, or delete it as dead code. (Note: an "Ask the corpus" RAG widget *is* reachable
via `RegChat` embedded in Corpus — but keyword/semantic search itself is not.)

**P0-3 · Alert `region_match` ignores the profile.** In `alerts/score.py` the rule scorer treats an
update as region-relevant if its region is in the profile **or** literally one of
`("US","EU","UK","International")`. Those four always pass regardless of the org's configured markets,
inflating relevance for regions the org doesn't operate in. Make region match profile-driven (keep a
sensible default only if the profile is empty).

**P0-4 · `RELEVANCE_FLOOR` is dead code.** `alerts/score.py` defines `RELEVANCE_FLOOR = 0.15` and the
docstring says low-signal updates are "marked low-signal," but nothing applies it — **every** scored
update becomes an alert row. Either wire the floor in (filter or flag below-threshold alerts) or
remove the constant and correct the docstring. Confirm intended behavior with the owner first.

**P0-5 · `horizon_briefing()` has no graceful fallback.** In `insights/trends.py`, the Claude call in
`horizon_briefing()` is **not** wrapped in the try/except → rule-fallback pattern its siblings
(`alerts/score.py`, `impact.py`) use. A Claude API error takes down the insights endpoint instead of
degrading. Add the same fallback guard.

### Tier P1 — robustness & trust

**P1-6 · RAG citations are never validated.** `api/rag.py` trusts the model to emit `[n]` markers
matching the numbered passages; nothing parses the answer to confirm cited numbers exist. Parse the
`[n]` markers, drop/flag any that don't map to a real source, and return which sources were actually
cited. (Also: the `seen` set in `ask()` is built but never used — dead code; remove or use it for the
intended per-document source dedup.)

**P1-7 · Search cache can serve stale vectors.** `search/semantic.py` caches the embedding matrix and
invalidates only when the chunk **row count** changes. Editing a chunk's text/embedding without
changing the count serves stale vectors until restart. Key the cache on a content signature
(e.g. `COUNT(*)` + `MAX(rowid)`, or a version counter bumped on every write).

**P1-8 · Frontend swallows errors silently.** Almost every page does
`api.xxx().then(setX).catch(() => {})` (only `DocumentDetail.tsx` surfaces errors). Failures show as
blank screens. Introduce a small shared fetch/error hook (or at minimum a toast/banner) and adopt it
across pages.

**P1-9 · "Graceful degradation" without a key isn't true for interpretation.** The README says the
Claude layer degrades gracefully, but `interpret_corpus()`/`interpret_one()` **raise** without a key.
Either make interpretation a soft skip (log + continue) or fix the README and API error messaging so
behavior matches the promise. (Ingest/search genuinely do work without a key — that part is fine.)

**P1-10 · Fragile JSON filter.** The `area` facet filter in `api/queries.py` uses
`LIKE '%"area"%'` against the JSON-encoded `regulatory_areas` column — it can mis-match when one area
name is a substring of another. Use SQLite `json_each`/`json_extract` containment or a normalized
join table.

**P1-11 · Brittle HTML scrapers with silent failure.** `monitor/fetch.py`'s `html` adapter is a
hand-rolled regex tokenizer over 6 sites; any markup change breaks it silently. Surface per-source
`last_status`/failure counts to the UI and log parse failures, so breakage is visible rather than
"no new updates."

**P1-12 · Naming collision: two different "horizon" features.** Top-level `regintel/horizon.py` is a
rule-only forward-scanning pillar; `insights/trends.py::horizon_briefing()` is a Claude forecast.
Same word, different features, different determinism. Rename one and disambiguate the UI labels.

**P1-13 · Duplicated jurisdiction picker.** `pages/Monitoring.tsx` re-implements the picker inline
instead of using the shared `JurisdictionPicker.tsx` that `Alerts.tsx` uses. Consume the shared
component.

**P1-14 · No automated tests exist.** Add a starter suite so future changes are safe:
chunker boundaries/overlap, the rule scorer math (P0-3/P0-4 are perfect first tests), ingest
dedup/idempotency (content-hash skip), RAG no-hit and no-key fallbacks, and one API smoke test
(`/api/health`, `/api/stats`). Wire it into a minimal CI workflow if none exists.

### Tier P2 — architecture, scale & hardening ("do these if/when you expose or grow this")

**P2-15 · No authentication, open CORS, unguarded file serving.** There is no auth on any endpoint;
CORS is `allow_origins=["*"]`; and `GET /api/documents/{id}/file` serves the raw `documents.path`
with no check that it stays within `corpus_root`. **For a local tool these are acceptable.** If the
service will be exposed: add an API-key/token dependency, restrict CORS to known origins, and validate
the served path is inside `corpus_root` before `FileResponse`. Gate these behind config so the local
experience stays frictionless.

**P2-16 · No migration system.** Schema is `CREATE TABLE IF NOT EXISTS` only — every change is manual
and additive. Add a lightweight versioned-migration mechanism before the schema grows further.

**P2-17 · Brute-force vector search won't scale.** Fine at "thousands of chunks," but full-scan every
query. Document the crossover point and the swap path (sqlite-vec / FAISS / a real ANN index) so the
next person isn't surprised when it slows down.

**P2-18 · Cross-process ingest race.** `ingest_service.py`'s `threading.Lock` prevents overlap only
*within one process*. The CLI script and the API scheduler can still race on the same SQLite file.
Add a DB-level/single-writer guard if both run in the same deployment.

**P2-19 · Deprecated startup hook.** `@app.on_event("startup")` for the auto-ingest scheduler is
deprecated; move to FastAPI's `lifespan` context.

**P2-20 · No OCR for scanned PDFs.** Scanned docs are flagged `is_scanned` and then dropped (never
chunked or interpreted). If scanned regulatory PDFs matter, this is a coverage gap — note it or add an
OCR fallback.

**P2-21 · `raw_json` vs exploded columns must stay in lockstep.** `interpretations` stores both the
full Claude payload and columns exploded from it. Any prompt-schema change must update the tool schema
**and** the `_store()` column mapping together, or new fields silently live only in `raw_json`.
Document this contract near the code.

---

## 5. Suggested sequencing

1. **PR #1 (P0):** items 1–5. Small, high-value, low-risk. Add tests for #3 and #4 as you go.
2. **PR #2 (P1 trust):** items 6, 9, 11 (data/answer integrity) + starter tests (#14).
3. **PR #3 (P1 polish):** items 7, 8, 10, 12, 13.
4. **PR #4+ (P2):** only after confirming deployment context; security items (15) first if exposed.

For each PR: state what changed, why, how you verified it (commands + observed output), and anything
you deliberately left out. Flag anything that looked intentional so the owner can decide.
