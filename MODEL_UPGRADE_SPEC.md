# Spec — Upgrading the Claude Model in AFFAIRS

**Status:** proposal · **Date:** 2026-07-17 · **Scope:** the model behind every Claude call in the
backend. Corresponds to brief item **P1-5**. Doc-only; no code changed on this branch.

**Verification basis:** the compatibility facts below were checked against the current Anthropic model
catalog + SDK reference on 2026-07-17 (same pass that produced `VERIFICATION_REPORT.md`).

---

## 1. Where the model is used today

One knob drives everything:

```python
# backend/regintel/config.py:30
self.model = os.getenv("REGINTEL_MODEL", "claude-opus-4-6").strip()
```

`settings.model` is read by **five** call sites, all via the Anthropic Python SDK:

| Call site | File | Shape | Notes |
|---|---|---|---|
| Document interpretation | `nlp/interpret.py` | forced `tool_use` (`record_interpretation`) | structured JSON, `max_tokens=4096` |
| Alert scoring | `alerts/score.py` | forced `tool_use` (`record_alert_score`) | high volume — one call per monitored update |
| Impact assessment | `impact.py` | forced `tool_use` (`record_impact`) | per update × portfolio |
| RAG answer | `api/rag.py` | plain text completion | high volume — interactive Q&A |
| Country web-scan | `country_scan.py` | server tool `web_search_20260209` | reads `block.citations` |

SDK pin: **`anthropic==0.42.0`** (`backend/requirements.txt:19`).

**Key finding that de-risks the whole change:** none of these calls set `thinking`, `budget_tokens`,
`temperature`, `top_p`, or an assistant prefill. That means **none of the Opus 4.7/4.8 breaking changes
apply** — the upgrade is a model-string swap, not a code migration.

---

## 2. Target & recommendation

`claude-opus-4-6` is a real, currently-active model, so the code runs as-is today. It is simply one
generation behind.

**Recommended: move to `claude-opus-4-8` (current top Opus, 1M context, $5 / $25 per MTok), and make the
model per-task so the high-volume paths can run cheaper.**

Two shippable stages:

- **Stage 1 (drop-in, ~30 min):** flip the single default `REGINTEL_MODEL` → `claude-opus-4-8`. Pure
  string swap. Immediate quality lift, zero code change beyond the default.
- **Stage 2 (per-task tiering, optional):** split the one knob into per-task settings so the cheap,
  high-frequency paths (alert scoring, RAG synthesis) can use a lower tier while the deep-reasoning paths
  (interpretation, impact, horizon) stay on Opus.

Suggested tiering:

| Task | Model | Why |
|---|---|---|
| Interpretation | `claude-opus-4-8` | deepest reasoning; runs once per doc, not hot |
| Impact assessment | `claude-opus-4-8` | portfolio reasoning; correctness matters |
| Horizon briefing | `claude-opus-4-8` | forecast quality |
| Alert scoring | `claude-sonnet-5` or `claude-haiku-4-5` | one call per update — highest volume; a triage score, not deep reasoning |
| RAG answer | `claude-sonnet-5` | interactive; latency + cost sensitive; grounded by retrieved context |
| Country web-scan | `claude-opus-4-8` | must drive `web_search` well and cite; keep strong |

Cost framing: the two hot paths (scoring, RAG) dominate call volume; moving them to Sonnet 5 (~$3 / $15,
intro $2 / $10 through 2026-08-31) or Haiku 4.5 (~$1 / $5) is where the savings are. Interpretation/impact/
horizon are low-frequency, so keeping them on Opus costs little.

---

## 3. Verified compatibility facts (2026-07-17)

- **`claude-opus-4-8` is the current top Opus** (1M ctx). `claude-opus-4-6` is still active. Both are
  valid model strings — use exactly, no date suffix.
- **The swap needs no code change.** No `thinking`/`budget_tokens` (would be rejected on 4.7/4.8 if set —
  they aren't), no `temperature`/`top_p`, no prefill. Forced `tool_use` and plain completions behave the
  same across the Opus family.
- **`web_search_20260209` is valid** on Opus 4.6 / 4.7 / 4.8 and Sonnet 5 / 4.6. The tool *string* in
  `country_scan.py` is fine across the upgrade. (Not available on Vertex — only basic `web_search_20250305`
  there — irrelevant unless this deploys on Vertex.)
- **Cheaper tiers are drop-in too:** `claude-sonnet-5`, `claude-haiku-4-5` take the same `messages.create`
  + `tool_use` shape. Haiku is 200K context (vs 1M) — fine for scoring/RAG payloads here, which are small.

---

## 4. The SDK bump (do this alongside)

`anthropic==0.42.0` is old and should move to a current release **in the same branch**, because:

- `country_scan.py` reads `block.citations` off `web_search_tool_result` blocks. Server tools serialize as
  plain dicts regardless of SDK version, but the **response deserialization** of citation blocks is exactly
  the kind of thing that firmed up after 0.42.0. Bumping de-risks the country-scan path.
- SDK response models change across majors, so after bumping you **must re-verify that the four other paths
  still parse** (`tool_use` block access in interpret/score/impact, `.text` access in rag).

This is the one place the change is more than a string swap — treat the country-scan path as the
highest-risk item and test it end-to-end.

---

## 5. Design (Stage 2 — per-task config)

Extend `config.py` without breaking the single-knob contract:

```python
# base default becomes 4-8; REGINTEL_MODEL still works as an override for all tasks
_BASE = os.getenv("REGINTEL_MODEL", "claude-opus-4-8").strip()
self.model = _BASE                                            # back-compat: existing code keeps working
self.model_interpret     = os.getenv("REGINTEL_MODEL_INTERPRET", _BASE).strip()
self.model_score         = os.getenv("REGINTEL_MODEL_SCORE",  "claude-sonnet-5").strip()
self.model_rag           = os.getenv("REGINTEL_MODEL_RAG",    "claude-sonnet-5").strip()
self.model_impact        = os.getenv("REGINTEL_MODEL_IMPACT",  _BASE).strip()
self.model_horizon       = os.getenv("REGINTEL_MODEL_HORIZON", _BASE).strip()
self.model_country_scan  = os.getenv("REGINTEL_MODEL_COUNTRY", _BASE).strip()
```

Then each call site reads its task-specific setting instead of `settings.model`. `/api/health` (which
already returns `model`) can return the resolved per-task map for observability.

Everything defaults to Opus 4.8, so **Stage 2 is safe even if you never set the cheaper env vars** — it's
identical to Stage 1 until someone opts a path down a tier.

---

## 6. Implementation steps (branch workflow)

1. **Branch** off `main` (this branch is the spec; implementation gets its own).
2. **Bump SDK** — `anthropic` → current release in `requirements.txt`; `pip install -r requirements.txt`.
3. **Flip default** — `REGINTEL_MODEL` default → `claude-opus-4-8` (Stage 1).
4. **Smoke every path with a key** (there are no tests yet — see brief P1-14):
   - interpret one document → `record_interpretation` tool call returns and `_store()` persists.
   - score one update → `record_alert_score` returns.
   - impact for one update × a product → `record_impact` returns.
   - `POST /api/ask` → non-empty grounded answer, `.text` parses.
   - `POST` a country scan → `country.summary` populated **and** `sources` parsed from citations.
5. **(Optional) Add per-task config** (Stage 2) + point each call site at its setting.
6. **Add a minimal smoke script** (`scripts/smoke_claude.py`) that runs the five checks behind a key, so
   this is repeatable — doubles as the seed for the P1-14 test suite.
7. **Update `.env.example` + README** with the new default and the per-task overrides.

---

## 7. Testing & rollback

- **Testing:** manual/scripted smoke (step 4/6) — the repo has no automated tests. Prioritize the
  country-scan path (SDK-sensitive) and confirm `sources` still populate.
- **Rollback:** Stage 1 is env-only — set `REGINTEL_MODEL=claude-opus-4-6` to revert instantly, no code
  change. The SDK bump is the only code-level rollback (revert the `requirements.txt` line + reinstall).

---

## 8. Decisions to confirm

1. **Drop-in only, or tiered?** Recommend shipping Stage 1 first, then Stage 2 if cost matters.
2. **Which tier for the hot paths?** Sonnet 5 (quality) vs Haiku 4.5 (cheapest). Recommend Sonnet 5 for RAG
   (answer quality is user-facing) and either for scoring (it's triage).
3. **SDK target version** — pin to the latest stable after the smoke passes; re-pin only once all five
   paths are confirmed parsing.

**Effort:** Stage 1 = S (≈30 min + smoke). SDK bump = S but test-heavy on country-scan. Stage 2 = S–M.
