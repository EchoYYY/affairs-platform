# Spec — Merging AFFAIRS into ReviewPort

**Status:** proposal · **Date:** 2026-07-17 · **Scope:** fold the AFFAIRS regulatory-intelligence
platform into ReviewPort as a native capability layer ("Regulatory Intelligence"), serving two uses:
**(a) inline regulatory context during MLR review** and **(b) regulatory-change alerts that flag affected
review content**. Doc-only; no code changed on this branch.

> **This is a merge, not an integration seam.** AFFAIRS's five pillars become ReviewPort features running
> on ReviewPort's own stack — not a separate service RP calls. Because the two apps are built on different
> platforms, the merge is a **re-platform**, described below.

---

## 0. Gating precondition — code ownership

AFFAIRS lives in **`EchoYYY/affairs-platform`** (a standalone repo, not part of the MicroPort Star fleet).
ReviewPort is MicroPort's. Lifting AFFAIRS's source into ReviewPort is a code/IP move that needs the
**owner's explicit consent + a clear license** before any code is copied. This spec assumes that's settled;
if it isn't, that is the first blocker. (The port is a re-implementation, not a verbatim copy, but the
design and prompts still originate there.)

---

## 1. The two platforms

| | AFFAIRS (source) | ReviewPort (target) |
|---|---|---|
| Backend | Python 3.9 + FastAPI | **Node 18 + Express (JavaScript)** |
| Data | SQLite (single file, raw sqlite3) | **PostgreSQL + Prisma 7.8** (`@prisma/adapter-pg`) |
| Embeddings | `fastembed` `bge-small-en-v1.5` (ONNX, local) | **none today** |
| Vector search | NumPy brute-force cosine | **none today** |
| LLM | Anthropic **Python** SDK, forced tool-use | **none today** (content pre-check is rule-based: `lib/contentScan.js`) |
| Frontend | React + Vite + Recharts | **Next.js** (`web/`, app router, next-intl tri-locale, microport-ui) |
| Doc storage | filesystem corpus walk | **S3 + `pdf-parse`** (assets already ingested) |

**Consequence:** every pillar is re-implemented in JS/Prisma. The merge also introduces ReviewPort's
**first** Anthropic SDK dependency and its **first** embedding/vector workload — a real infra + cost step,
not just new routes.

---

## 2. The synergy that makes this worth doing

ReviewPort already owns most of what AFFAIRS had to build from scratch. The merge is mostly *mapping*, not
*porting*:

| AFFAIRS concept | ReviewPort home | Note |
|---|---|---|
| Document corpus (folder of PDFs) | existing **`assets` / `library`** (S3 + `pdf-parse`) | RP already ingests & stores the regulatory documents — reuse them as the corpus; no separate folder |
| `interpretations` / `requirements` / `obligations` | **new Prisma models** linked to `Asset` | Claude-interpret approved assets |
| Semantic search / chunks | **new `RegIntelChunk`** + pgvector | search over asset chunks |
| `watch_profile` | existing **`products`** + **`regulatory`** (RA country×product approval matrix) | RP's RA team already maintains the profile-equivalent |
| Monitoring sources / `updates` | **new monitoring module** | RSS / openFDA / HTML fetch adapters ported |
| `alerts` (scoring vs profile) | existing **`notifications`** + **`reviewTasks`** | an alert → in-app notice **and** a re-review flag on affected assets |
| `impact_assessments` | existing **`products`** / **`claims`** / **`risk`** | per-product impact maps onto RP's product + risk models |
| `insights` / horizon | **new dashboard widget** in `web/` | trend + forecast |
| "Ask the corpus" (RAG) | **inline panel in the review-task screen** | cited answers `[n]` beside the content under review |

The payoff for use-case (b): AFFAIRS scoring already knows "this regulatory update is relevant to product X";
in RP that becomes **"flag every approved asset for product X for re-review"** — a first-class RP action.

⚠️ **Naming clash:** RP's existing `regulatory.js` is the RA **approval matrix** (country × product), not a
document corpus. Namespace all new surfaces **`RegIntel*`** (models, routes `/api/regintel/*`, nav
"Regulatory Intelligence") to avoid colliding with it.

---

## 3. Architecture decisions (the hard parts)

**3.1 Embeddings in Node.** Preserve AFFAIRS's "local, offline, no second API key" intent.
- **Recommended:** `@xenova/transformers` (transformers.js) running the *same* `bge-small-en-v1.5` ONNX
  model on CPU. Same vectors, no API, no key. Node-native.
- Rejected: a hosted embedding API (adds a key + cost + contradicts the design intent); a Python sidecar
  (defeats the merge).

**3.2 Vector search → pgvector.** RP is already Postgres. Add the **`pgvector`** extension and store chunk
embeddings in a `vector(384)` column; query with cosine `<=>`. This **fixes AFFAIRS's P2-17 (brute-force
won't scale) at the source** rather than porting the limitation. Prisma reaches pgvector via an
`Unsupported("vector(384)")` column + raw SQL for the similarity query. (Fallback: brute-force cosine in
Node at small corpus size — but pgvector is the right call given RP already runs Postgres.)

**3.3 Claude interpretation.** Add `@anthropic-ai/sdk`. Port the forced-tool-use JSON schemas verbatim
(`record_interpretation`, `record_alert_score`, `record_impact`, `record_horizon`) — they're plain dicts,
language-agnostic. Use **`claude-opus-4-8`** (see the companion `MODEL_UPGRADE_SPEC.md`; don't port the
one-generation-behind default). Must **degrade gracefully without a key** — fixing AFFAIRS's P1-9 in the
port (no hard raise on the hot paths).

**3.4 Corpus = RP's approved assets.** Instead of a filesystem walk, ingestion hooks into RP's existing
asset lifecycle: on asset approval, chunk + embed + interpret. This ties regulatory intelligence directly
to the documents RP already governs, and keeps a single source of truth.

**3.5 New Prisma models** (all `RegIntel*`-prefixed, FK'd to `Asset`/`Product` where they map):
`RegIntelInterpretation`, `RegIntelChunk` (+ `vector(384)`), `RegIntelRequirement`, `RegIntelObligation`,
`RegIntelSource`, `RegIntelUpdate`, `RegIntelAlert`, `RegIntelImpact`, `RegIntelWatchProfile` (or reuse
`products`+`regulatory` for the profile). Follow the Prisma 7 migration footguns already documented for the
fleet (non-transactional migrations, enum rebuild pattern, CA-bundle adapter setup).

**3.6 Frontend = RP Next.js conventions.** Reimplement AFFAIRS's screens as RP `web/app/(app)/regintel/*`
pages honoring the fleet standards: **next-intl tri-locale (en/zh/fr)**, **microport-ui** components + theme
tokens (no hardcoded colors), **testId** naming convention, **HelpButton** coverage per screen, TopBar/page-h1
standard, and the modal/popover standards. Recharts → whatever RP's `web/` already charts with. The RAG
"Ask the corpus" panel embeds into the existing review-task screen, not a standalone page.

---

## 4. Fleet seams the merge must honor

- **Auth/roles:** RegIntel screens gated by RP's `requireRole` (RP verifies SalesPort's JWT — no new IdP).
  Reviewers get read + ask; RA role gets monitoring/profile management.
- **Notifications:** change-alerts route through RP's existing `notifications` (in-app) and optionally SES
  email — reuse, don't rebuild.
- **Re-review trigger:** the intelligence-hub payoff — a `RegIntelAlert` on a product creates/flags a RP
  `reviewTask` on affected approved assets.
- **Audit log:** RegIntel mutations logged through RP's `auditLog`.
- **Webhook (optional, later):** RP already emits `rp→sp` (`asset.approved`, `capa.created`,
  `complaint.created`). A `regulation.changed` / `regintel.alert` event could be added if SalesPort or other
  Ports need it — not required for the two core use-cases.

---

## 5. Carry the fixes, not the bugs

The merge is the moment to land AFFAIRS "built better." Apply the verified brief items during the port
(see `CLAUDE_IMPROVEMENT_BRIEF.md` + `VERIFICATION_REPORT.md`):

- **P0-2** region match becomes profile-driven (RP's products/regulatory), not the hardcoded 4-region pass.
- **P0-3** relevance floor actually applied (or the notion dropped) — no unfiltered alert spam into RP notifications.
- **P0-4** horizon/insights wrapped in the graceful-fallback pattern.
- **P1-6** RAG citations validated before display — critical when a reviewer may cite them in an MLR record.
- **P1-7** cache staleness — **moot** under pgvector (no in-process matrix cache).
- **P1-9** graceful degradation without a key — required for a shared RP deployment.

---

## 6. Phased plan (each phase a shippable RP slice)

| Phase | Delivers | Pillars |
|---|---|---|
| **0 — Foundations** | pgvector + `RegIntel*` Prisma models + `@anthropic-ai/sdk` + transformers.js embeddings; ingest+embed RP's approved assets | corpus + search backend |
| **1 — Interpret + Search UI** | Claude interpretation of assets; semantic-search screen; "Ask the corpus" panel inline in the review task (cited answers) | 1, 2, RAG |
| **2 — Monitoring + Alerts** | source registry + RSS/openFDA/HTML fetch adapters (scheduled job); scoring vs profile; alerts → notifications + **re-review flags** | 3 + change-alerts (use-case b) |
| **3 — Impact + Insights** | per-product impact vs RP products/risk; horizon dashboard widget | 4, 5 |

Each phase follows RP's **Mig → Lang → Ship → Hunt → Watch** deploy workflow (migration safety, tri-locale
pass, ship, error hunt, log watch).

---

## 7. Risks & open decisions

- **Ownership/consent (blocker)** — §0. Resolve before any code moves.
- **Embeddings-in-Node maturity** — validate transformers.js produces vectors equivalent to fastembed's
  bge-small (same model, but confirm parity) and its cold-start/latency on RP's containers.
- **pgvector + Prisma 7** — `Unsupported` column + raw-SQL similarity is a known-but-fiddly pattern; prove
  it in Phase 0.
- **Schema reconciliation** — how much to reuse RP's `products`/`regulatory` as the watch profile vs a new
  `RegIntelWatchProfile`. Recommend: reuse where it maps, add only what's missing.
- **First AI workload in RP** — cost (Claude + embedding CPU) and infra (ONNX model in the container image).
  Ties to `MODEL_UPGRADE_SPEC.md` for the model/tiering choices.
- **Corpus scope** — only approved assets, or a broader regulatory library? Affects ingestion volume + cost.
- **Monitoring sources** — keep AFFAIRS's source list, or align to RP/fleet's existing feeds?

**Where this builds:** the actual implementation lands in the **`reviewport`** repo (this spec lives with
AFFAIRS as the origin design record). Each phase = its own PR in ReviewPort.

**Effort:** Large — a multi-phase build, not a single PR. Phase 0+1 deliver the highest-value slice (inline
cited regulatory context in review) and are the recommended first milestone.
