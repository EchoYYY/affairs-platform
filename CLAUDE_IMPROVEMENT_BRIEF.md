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
- **Don't hardcode a Claude model ID from memory.** Read what's configured (`REGINTEL_MODEL`); if you
  change it, verify the exact string against the current Anthropic model catalog first. The configured
  default `claude-opus-4-6` is valid today — see P1-5 for the model/SDK details. (An invalid/retired
  ID would fail at the first Claude call, not at startup, so it wouldn't surface in a quick smoke test
  run without an API key.)
- Keep commits scoped and message them by tier/item (e.g. `fix(scoring): apply RELEVANCE_FLOOR`).
- If an item below turns out to be intentional, **stop and flag it** rather than "fixing" it.

---

## 4. The improvement backlog (tiered)

Line references are anchors from a read of the current tree — **verify each before editing**, since
line numbers drift.

### Tier P0 — correctness defects that already misbehave

**P0-1 · Semantic search is built but unreachable from the UI.** `frontend/src/pages/Search.tsx` is
the only caller of `api.search()`, but it is **not routed** — the `/search` nav entry renders
`KnowledgeHub.tsx` (a registration-timeline lookup) instead. The product's headline capability
(semantic search over the corpus) has no front door. **Decide with the owner:** wire `Search.tsx`
into the nav/routes, or delete it as dead code. (Note: RAG Q&A *is* reachable — via a dedicated
**Ask the Corpus** page at `/ask` *and* the `RegChat` widget embedded in Corpus — but keyword/semantic
search itself is not.)

**P0-2 · Alert `region_match` ignores the profile.** In `alerts/score.py` the rule scorer treats an
update as region-relevant if its region is in the profile **or** literally one of
`("US","EU","UK","International")`. Those four always pass regardless of the org's configured markets,
inflating relevance for regions the org doesn't operate in. Make region match profile-driven (keep a
sensible default only if the profile is empty).

**P0-3 · `RELEVANCE_FLOOR` is dead code.** `alerts/score.py` defines `RELEVANCE_FLOOR = 0.15` and the
docstring says low-signal updates are "marked low-signal," but nothing applies it — **every** scored
update becomes an alert row. Either wire the floor in (filter or flag below-threshold alerts) or
remove the constant and correct the docstring. Confirm intended behavior with the owner first.

**P0-4 · `horizon_briefing()` has no graceful fallback.** In `insights/trends.py`, the Claude call in
`horizon_briefing()` is **not** wrapped in the try/except → rule-fallback pattern its siblings
(`alerts/score.py`, `impact.py`) use. A Claude API error takes down the insights endpoint instead of
degrading. Add the same fallback guard.

### Tier P1 — robustness & trust

**P1-5 · Stale `anthropic` SDK + a model generation behind (verified, not a blocker).** Two related
findings, checked against the current Anthropic model catalog + SDK reference:
- **Model:** `REGINTEL_MODEL` defaults to `claude-opus-4-6` (`backend/regintel/config.py`), used by
  RAG (`api/rag.py`), interpretation (`nlp/interpret.py`), scoring (`alerts/score.py`), impact
  (`impact.py`), and country-scan (`country_scan.py`). **This is a real, currently-active model and
  the code runs on it as-is** — the calls set no `thinking`/`budget_tokens`, no `temperature`/`top_p`,
  and no assistant prefill, so none of the Opus 4.7/4.8 breaking changes apply. It's simply a
  generation behind current (Opus 4.8). Upgrading these calls to `claude-opus-4-8` is a **pure
  model-string swap, no code change**. Optional but recommended for quality; also consider a cheaper
  tier (Sonnet 5 / Haiku 4.5) for the high-volume scoring and RAG paths to cut cost.
- **SDK:** the pin is `anthropic==0.42.0` (`backend/requirements.txt`), which is old. `country_scan.py`
  declares the current server-side web-search tool (`web_search_20260209`) — the tool *string* is
  valid and compatible with Opus 4.6 — but server tools serialize as plain dicts regardless of SDK
  version, so the real risk is the **old SDK deserializing the response**: `country_scan.py` reads
  `block.citations` off `web_search_tool_result` blocks, which that SDK version predates. **Bump
  `anthropic` to a current release and test the country-scan path end-to-end** before relying on it.
  Re-pin only after confirming the interpret/RAG/score paths still parse (SDK response models change
  across majors).

**P1-6 · RAG citations are never validated.** `api/rag.py` trusts the model to emit `[n]` markers
matching the numbered passages; nothing parses the answer to confirm cited numbers exist. Parse the
`[n]` markers, drop/flag any that don't map to a real source, and return which sources were actually
cited. (Also: the `seen` set in `ask()` is built but never used — dead code; remove or use it for the
intended per-document source dedup.)

**P1-7 · Search cache can serve stale vectors.** `search/semantic.py` caches the embedding matrix and
invalidates only when the chunk **row count** changes. Editing a chunk's text/embedding without
changing the count serves stale vectors until restart. Key the cache on a content signature
(e.g. `COUNT(*)` + `MAX(rowid)`, or a version counter bumped on every write). (Verified: an
`invalidate_cache()` helper exists in `search/semantic.py` but is **called nowhere** in the backend —
dead code today; the row-count check is the only invalidation path.)

**P1-8 · Frontend swallows errors silently.** Almost every page does
`api.xxx().then(setX).catch(() => {})` (only `DocumentDetail.tsx` surfaces errors). Failures show as
blank screens. Introduce a small shared fetch/error hook (or at minimum a toast/banner) and adopt it
across pages.

**P1-9 · Interpretation raises on a *direct* call without a key (minor — README is essentially accurate).**
`interpret_corpus()`/`interpret_one()` do raise a `RuntimeError` when no key is set — but the user-facing
paths already degrade cleanly: `ingest_service.run_sync()` gates interpretation on `claude_enabled` (silent
skip), and `POST /api/documents/{id}/interpret` returns a clean `400`. So the README's "interpretation is
simply skipped" holds for normal use; the only rough edge is a bare `RuntimeError` if code calls the
corpus-interpret functions *directly* (e.g. a CLI/script) without first checking `claude_enabled`. Low
priority: either soft-skip inside those functions too, or leave as-is (the raised message is explicit).
(Ingest/search genuinely work without a key.) *[Downgraded from the original "degradation isn't true"
framing after 2026-07-17 verification — see the log below.]*

**P1-10 · Fragile JSON filter (rationale corrected 2026-07-17).** The `area` facet filter in
`api/queries.py` matches `regulatory_areas LIKE '%"area"%'` against the JSON-encoded column. The
double-quote bounding **does** prevent the naive "one area name is a substring of another" case (the stored
element `"Software/SaMD"` does not contain the literal `"Software"`), so that specific failure mode from the
original write-up does not actually occur. The genuine fragility is different: `LIKE` treats any `%` or `_`
inside an area name as a wildcard, and the match depends on the exact JSON serialization (spacing/escaping).
The fix is the same regardless — use SQLite `json_each`/`json_extract` containment or a normalized join
table instead of `LIKE` over serialized JSON.

**P1-11 · Brittle HTML scrapers with silent failure.** `monitor/fetch.py`'s `html` adapter is a
hand-rolled regex tokenizer over 8 HTML-type sources; any markup change breaks it silently. Surface per-source
`last_status`/failure counts to the UI and log parse failures, so breakage is visible rather than
"no new updates."

**P1-12 · Naming collision: two different "horizon" features.** Top-level `regintel/horizon.py` is a
rule-only forward-scanning pillar; `insights/trends.py::horizon_briefing()` is a Claude forecast.
Same word, different features, different determinism. Rename one and disambiguate the UI labels.

**P1-13 · Duplicated jurisdiction picker.** `pages/Monitoring.tsx` re-implements the picker inline
instead of using the shared `JurisdictionPicker.tsx` that `Alerts.tsx` uses. Consume the shared
component.

**P1-14 · No automated tests exist.** Add a starter suite so future changes are safe:
chunker boundaries/overlap, the rule scorer math (P0-2/P0-3 are perfect first tests), ingest
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

1. **PR #1 (P0):** items 1–4. Small, high-value, low-risk. Add tests for #2 and #3 as you go.
2. **PR #2 (P1 trust):** items 5 (SDK bump — test country-scan), 6, 9, 11 (data/answer integrity)
   + starter tests (#14).
3. **PR #3 (P1 polish):** items 7, 8, 10, 12, 13.
4. **PR #4+ (P2):** only after confirming deployment context; security items (15) first if exposed.

For each PR: state what changed, why, how you verified it (commands + observed output), and anything
you deliberately left out. Flag anything that looked intentional so the owner can decide.

---

## Verification log (2026-07-17)

All 21 items were re-checked against the current tree (local-model first pass + adjudicated read).
Full detail in `VERIFICATION_REPORT.md`. Result: **18 confirmed as-written, 3 corrected, 0 removed.**

- **P0-1** — enriched: RAG Q&A is reachable via *both* the `/ask` page and RegChat-in-Corpus (only
  semantic search lacks a front door).
- **P1-7** — enriched: `invalidate_cache()` exists but is called nowhere (dead code).
- **P1-9** — **downgraded**: the normal paths already guard on `claude_enabled` (silent skip / clean 400),
  so the README is essentially accurate; only a *direct* call raises. Now a minor item, not a trust bug.
- **P1-10** — **rationale corrected**: the quoted `LIKE` prevents the substring-of-another case originally
  cited; the real fragility is `LIKE` wildcard metacharacters + serialization dependence. (Item still valid.)
- **P1-11** — **count corrected**: 8 HTML-type sources, not 6.

Everything else (P0-2, P0-3, P0-4, P1-5, P1-6, P1-8, P1-12, P1-13, P1-14, P2-15…P2-21) verified accurate
as written.
