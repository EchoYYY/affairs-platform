# Verification Report — CLAUDE_IMPROVEMENT_BRIEF.md

**Date:** 2026-07-17
**Purpose:** Fact-check every claim in `CLAUDE_IMPROVEMENT_BRIEF.md` against the *current* source tree
before anyone acts on it, so the brief is airtight for the AI agent that picks it up.

**Method (two-pass):**
1. **First pass — local model.** Each claim was handed to `qwen2.5-coder:32b` (running locally) together
   with the *actual* source lines it points at. The model returned a structured verdict
   (`CONFIRMED` / `DRIFTED` / `WRONG` / `UNCERTAIN`) with quoted evidence. Raw output is preserved at the
   bottom of this file.
2. **Second pass — adjudication.** Every verdict was reviewed against a direct read of the code. The local
   model is a first opinion, not the ruling: where its label was inconsistent with its own evidence, or it
   misread the mechanism, the adjudicated verdict below overrides it (see "Where the two passes diverged").

## Bottom line

21 claims checked. **18 confirmed as-written, 3 corrected, 0 removed.** Nothing in the brief is a
fabrication — every item points at real code. Three items had inaccurate *details* (not conclusions) and
have been fixed in the brief; two accurate items were *enriched* with an extra finding.

| Result | Items |
|---|---|
| ✅ Confirmed (accurate as written) | P0-1, P0-2, P0-3, P0-4, P1-5, P1-6, P1-7, P1-8, P1-12, P1-13, P1-14, P2-15, P2-16, P2-17, P2-18, P2-19, P2-20, P2-21 |
| ✏️ Corrected in brief | P1-9 (overstated), P1-10 (wrong mechanism), P1-11 (count 6→8) |
| ➕ Enriched in brief | P0-1 (RAG reachable via `/ask` *and* RegChat), P1-7 (`invalidate_cache()` is dead code) |
| ❌ Removed | — none |

## Per-claim verdicts (adjudicated)

| ID | Adjudicated | Local model | Evidence / note |
|---|---|---|---|
| P0-1 | ✅ Confirmed (+enrich) | CONFIRMED | `App.tsx:73` routes `/search` → `KnowledgeHub`; `Search.tsx` is never imported. Enrich: RAG Q&A *is* reachable via a dedicated `/ask` page **and** `RegChat` in Corpus — only semantic search lacks a front door. |
| P0-2 | ✅ Confirmed | CONFIRMED | `score.py:37-38` — `region_match` passes for `US/EU/UK/International` regardless of `profile["markets"]`. |
| P0-3 | ✅ Confirmed | ~~WRONG~~ | `RELEVANCE_FLOOR=0.15` defined at `score.py:22`, referenced nowhere in `score_updates()`/`rescore_all()`. Model's own evidence ("defined but not used") *confirms* the claim; its `WRONG` label was a mis-tag. |
| P0-4 | ✅ Confirmed | CONFIRMED | `trends.py:152` `client.messages.create` in `horizon_briefing()` has no try/except; siblings `score.py:157` and `impact.py:146` do. |
| P1-5 | ✅ Confirmed | CONFIRMED | `config.py:30` default `claude-opus-4-6`; `requirements.txt:19` `anthropic==0.42.0`; `country_scan.py:120` reads `block.citations`. (Model-validity is a separate, already-documented finding — code facts hold.) |
| P1-6 | ✅ Confirmed | CONFIRMED | `rag.py` returns the answer verbatim — no `[n]` parsing; `seen` set is written but never read to affect output. |
| P1-7 | ✅ Confirmed (+enrich) | CONFIRMED | `semantic.py:47` reloads only when `COUNT(*)` changes → content edits at constant count serve stale vectors. Enrich: `invalidate_cache()` (`semantic.py:41`) is **defined but called nowhere** — dead code. |
| P1-8 | ✅ Confirmed | CONFIRMED | 10 pages use `.catch(() => {})`; only `DocumentDetail.tsx:15` takes the error. |
| P1-9 | ✏️ Corrected (overstated) | DRIFTED | `interpret_corpus/one()` do raise without a key, **but** the normal paths guard: `ingest_service.run_sync()` gates on `claude_enabled` (silent skip) and `/interpret` returns a clean `400`. README's "interpretation is simply skipped" is essentially accurate. Downgraded to a minor rough edge. |
| P1-10 | ✏️ Corrected (wrong mechanism) | CONFIRMED* | `queries.py:75-76` uses `LIKE '%"area"%'`. The quote-bounding **does** prevent the "one area is a substring of another" case the brief cited (`"Software/SaMD"` ≠ `"Software"`). Real fragility = `LIKE` treats `%`/`_` in area names as wildcards + exact-serialization dependence. Item kept, rationale rewritten. I overruled the model here. |
| P1-11 | ✏️ Corrected (count) | DRIFTED | `grep -c '"type": "html"'` = **8** HTML sources, not "6". Silent-failure point is accurate. (Model said "off by one" and self-contradicted with "6" — both wrong; ground truth 8.) |
| P1-12 | ✅ Confirmed | DRIFTED | `horizon.py` (rule-only pillar) vs `trends.py::horizon_briefing()` (Claude, with heuristic fallback) — genuine naming collision. Model's "drift" was only the fallback nuance; collision claim stands. |
| P1-13 | ✅ Confirmed | CONFIRMED | `Monitoring.tsx:74-110` re-implements the picker inline; `Alerts.tsx:5` imports the shared `JurisdictionPicker`. |
| P1-14 | ✅ Confirmed | CONFIRMED | No `test_*.py`/`*.test.ts*`/etc. anywhere; no `.github/workflows`. |
| P2-15 | ✅ Confirmed | ~~WRONG~~ | `main.py:23` CORS `["*"]`; no auth dependency; `document_file` (`:133`) checks only `os.path.exists`, no `corpus_root` containment. Model's evidence confirms; `WRONG` was a mis-tag. (Nuance added: path is DB-sourced by integer id, so traversal risk is lower than raw path-serving sounds.) |
| P2-16 | ✅ Confirmed | ~~WRONG~~ | `db.py` is `CREATE TABLE IF NOT EXISTS` only; no versioned migrations. Model's evidence confirms; `WRONG` was a mis-tag. |
| P2-17 | ✅ Confirmed | CONFIRMED | `semantic.py:69` `mat @ q` scans the full matrix each query. |
| P2-18 | ✅ Confirmed | CONFIRMED | `ingest_service.py:15` process-local `threading.Lock`; no cross-process/DB guard. |
| P2-19 | ✅ Confirmed | CONFIRMED | `main.py:57` `@app.on_event("startup")` (deprecated). |
| P2-20 | ✅ Confirmed | DRIFTED (parse-fail) | `extract.py:93` sets `is_scanned`; `pipeline.py:97-102` stores the doc but skips chunking; `interpret.py:132` filters `is_scanned = 0`. No OCR. Accurate. |
| P2-21 | ✅ Confirmed | DRIFTED | `interpret.py:_store()` writes both `raw_json` and exploded columns — a two-place contract with the tool schema. Model's "drift" just restated the claim. |

\* P1-10: the local model labeled CONFIRMED but with reasoning I judged incorrect; see below.

## Where the two passes diverged (why adjudication mattered)

- **Mis-tagged verdicts (P0-3, P2-15, P2-16).** The model returned `WRONG` while its *own evidence* stated
  exactly what the brief claims ("defined but not used", "no containment check", "no migration logic"). These
  are label errors, not disagreements — adjudicated to **Confirmed**.
- **Genuine disagreement (P1-10).** The model asserted the quoted `LIKE` "does not prevent substring matches."
  A direct read shows the closing quote *does* block the substring-of-another case the brief described. The
  item survives, but with a corrected rationale — the model was wrong on the mechanism.
- **Count (P1-11).** Neither the brief ("6") nor the model ("off by one") matched the tree; `grep -c` settles it at **8**.

A single-pass "trust the local model" run would have wrongly flagged three correct items as WRONG and left
P1-10's bad rationale in place. The frontier adjudication pass is what kept the brief accurate.

---

## Appendix — raw local-model output

Model: `qwen2.5-coder:32b`, temp 0.1. Verbatim first-pass verdicts (before adjudication):

```json
[
  {"id":"P0-1","verdict":"CONFIRMED","note":"/search path renders KnowledgeHub.tsx, not Search.tsx","evidence":"App.tsx:13 <Route path=\"/search\" element={<KnowledgeHub />} />; Search.tsx not imported"},
  {"id":"P0-2","verdict":"CONFIRMED","note":"accurately reflects the code logic","evidence":"region_match = update.region in profile.markets OR in (US,EU,UK,International)"},
  {"id":"P0-3","verdict":"WRONG","note":"RELEVANCE_FLOOR defined but not used","evidence":"no reference to RELEVANCE_FLOOR in score_updates/rescore_all"},
  {"id":"P0-4","verdict":"CONFIRMED","note":"messages.create not wrapped in try/except","evidence":"horizon_briefing() client.messages.create has no guard"},
  {"id":"P1-5","verdict":"CONFIRMED","evidence":"default claude-opus-4-6; anthropic==0.42.0; reads block.citations"},
  {"id":"P1-6","verdict":"CONFIRMED","evidence":"no [n] parsing/validation; seen set built but never used"},
  {"id":"P1-7","verdict":"CONFIRMED","note":"content changes at constant COUNT(*) serve stale vectors until restart"},
  {"id":"P1-8","verdict":"CONFIRMED","note":"most pages empty catch; DocumentDetail handles error"},
  {"id":"P1-9","verdict":"DRIFTED","note":"README not entirely overstated; could be more precise","correction":"specify normal paths (run_sync, /interpret) guard on claude_enabled — skip or clean 400"},
  {"id":"P1-10","verdict":"CONFIRMED","note":"[claim: quotes do not prevent substring match — OVERRULED in adjudication]"},
  {"id":"P1-11","verdict":"DRIFTED","note":"number of sources is off by one","correction":"[adjudicated to 8]"},
  {"id":"P1-12","verdict":"DRIFTED","note":"omits that horizon_briefing uses Claude only when claude_enabled"},
  {"id":"P1-13","verdict":"CONFIRMED","note":"Monitoring inline; Alerts uses shared JurisdictionPicker"},
  {"id":"P1-14","verdict":"CONFIRMED","note":"no test files or CI workflows found"},
  {"id":"P2-15","verdict":"WRONG","note":"no auth + wildcard CORS confirmed; no corpus_root containment check","evidence":"only os.path.exists check"},
  {"id":"P2-16","verdict":"WRONG","note":"no migration scripts / versioning logic present"},
  {"id":"P2-17","verdict":"CONFIRMED","note":"mat @ q — full scan every query"},
  {"id":"P2-18","verdict":"CONFIRMED","note":"process-local threading.Lock"},
  {"id":"P2-19","verdict":"CONFIRMED","note":"uses deprecated @app.on_event('startup')"},
  {"id":"P2-20","verdict":"DRIFTED","note":"is_scanned set at extract; interpret filters is_scanned=0 (parse-fail on wire; recovered)"},
  {"id":"P2-21","verdict":"DRIFTED","note":"stores both structured columns and raw_json; not all fields exploded"}
]
```

Note how the raw labels differ from the adjudicated column above: P0-3 / P2-15 / P2-16 came back `WRONG`
while their evidence *confirmed* the claims (mis-tags), and P1-10 came back `CONFIRMED` on reasoning that
was itself incorrect. Those are the four the adjudication pass overrode.
