# Phase 12: Heterogeneous Extraction Routing - Context

**Gathered:** 2026-04-17
**Status:** Ready for planning

<domain>
## Phase Boundary

Deliver **per-file complexity-based model routing** for extraction: AST-derived metrics classify files into tiers; each tier maps to a model endpoint via declarative config; parallel extraction respects global concurrency and 429 backoff; **cache keys include `model_id`** so different models never share cache entries; **`graphify-out/routing.json`** records an auditable per-file decision trail; **full ROUTE-01–10 scope** ships in this phase (including P2 canary, cost ceiling, and image/vision slot per user choice).

**Composes with:** v1.3 Phase 10 batch extraction — clustering remains; routing must not silently downgrade quality for bundled files.

</domain>

<decisions>
## Implementation Decisions

### Router ↔ Phase 10 batch extraction (Claude's discretion)

- **D-01:** For **import-cluster batch LLM calls** (Phase 10), the **single** model used for that call is the **maximum tier** required by any file in the cluster (by tier ordering: trivial < simple < complex, plus vision slot when applicable). **One LLM call per cluster** is preserved.
- **D-02:** **`routing.json` records per-file** entries: each file’s **complexity class**, **selected model id**, and metrics used, even when the batch call uses the max tier — so the audit trail reflects classification + which call actually ran.
- **D-03:** Do **not** split clusters solely for tier mismatch by default (avoids API multiplication); if future work needs split clusters, treat as a separate opt-in.

### Activation & CLI

- **D-04:** Routing is **opt-in only** via **`graphify run --router`** (and skill-equivalent wiring). **No** `GRAPHIFY_USE_ROUTER` default-on and **no** implicit activation from YAML presence alone — keeps existing runs byte-for-byte predictable unless the flag is passed.

### Classification config

- **D-05:** **Trivial / simple / complex** thresholds and per-language metric weights live in **YAML** (paired with or nested under `graphify/routing_models.yaml` per ROUTE-02 pattern) so users can tune without code changes. Code supplies **safe defaults** only when keys are omitted.

### P1 / P2 scope for this phase

- **D-06:** **Ship ROUTE-01 through ROUTE-10 in Phase 12** — including **canary probes (ROUTE-08)**, **`GRAPHIFY_COST_CEILING` pre-flight (ROUTE-09)**, and **image → vision-capable slot with skip fallback (ROUTE-10)**. Planner breaks into plans/waves; no separate “Phase 12.1” for these unless execution discovers a hard dependency.

### Audit trail (Claude's discretion — align with dedup)

- **D-07:** **`routing.json`** follows **Phase 10 dedup sidecar conventions**: top-level **`version`**, **atomic write** via `.tmp` + `os.replace` under `graphify-out/`; paths and labels respect **`security.py`** (`validate_graph_path`, `sanitize_label` where surfaced in summaries).
- **D-08:** Add a **human-readable** companion where useful — either a **`routing_report.md`** sibling (like `dedup_report.md`) **or** a dedicated **"Routing"** section in **`GRAPH_REPORT.md`** — planner chooses the least redundant option vs existing report length.

### Claude's Discretion (remaining)

- Exact **JSON schema version** for `routing.json` and field names — design during planning for stability across minor versions.
- **Tier ordering** implementation detail (enum vs numeric rank) as long as max-tier aggregation for clusters is deterministic.
- Whether **canary failures** surface as **stderr warning** vs **non-zero exit** — default to **warning** unless REQ text mandates exit code.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Milestone & requirements

- `.planning/ROADMAP.md` — § "Phase 12: Heterogeneous Extraction Routing" (goal, depends, success criteria, plans note)
- `.planning/REQUIREMENTS.md` — ROUTE-01 through ROUTE-10 (full text + P2 markers)
- `.planning/PROJECT.md` — v1.4 milestone context and Phase 12 one-liner

### v1.4 cross-cutting invariants (from ROADMAP)

- D-02 MCP envelope, D-16 alias redirect (for any MCP-facing summaries), **`graph.json` read-only**, `security.py` gates, **`peer_id="anonymous"` default**

### Prior phase integration

- `.planning/milestones/v1.3-phases/10-cross-file-semantic-extraction/10-CONTEXT.md` — batch clustering (`batch.py`), dedup pipeline order, explicit **out-of-scope** pointer to Phase 12 routing

### Code touchpoints (read before changing)

- `graphify/cache.py` — `file_hash()`, `load_cached`, `save_cached` (ROUTE-04 extends keys)
- `graphify/extract.py` — extraction dispatch, LLM calls (router injection point per ROUTE-03)
- `graphify/dedup.py` — `write_dedup_reports` atomic pattern for sidecar JSON/md

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets

- **`cache.py`**: Central place to add **`model_id`** to hash inputs and cache filenames per ROUTE-04; maintain backward compatibility for callers omitting `model_id`.
- **`dedup.py`**: Template for **atomic JSON + optional markdown** sidecars in `graphify-out/`.
- **`batch.py`** (Phase 10): Cluster lists — use for **max-tier** aggregation over member files when batch LLM path runs.

### Established Patterns

- Pipeline stages communicate via **plain dicts**; new **`Router`** type passed as optional kwarg into **`extract()`** per ROUTE-03.
- **Stdlib + optional deps**: `radon` for Python complexity only if bundled as optional extra or documented install — align with `pyproject.toml` extras pattern.

### Integration Points

- **`graphify/__main__.py`**: Add **`--router`** to `run` (and document skill flag parity).
- **`graphify/skill.md`** (and platform variants): Wire user-facing **`/graphify`** or run config to pass **`--router`** when user enables routing in skill flow (planner to list exact touchpoints).

</code_context>

<specifics>
## Specific Ideas

- User selected **full ROUTE-01–10** in one phase, **`--router` only** activation, **YAML-first** tunability, and delegated **batch vs router** + **audit format** to builder discretion as specified above.

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within Phase 12 scope.

</deferred>

---

*Phase: 12-heterogeneous-extraction-routing*
*Context gathered: 2026-04-17*
