# Phase 67: CDRIFT + CQUERY — Edge-Level Drift (`drift.py`) & Parameterized Concept Queries - Context

**Gathered:** 2026-05-06
**Status:** Ready for planning

<domain>
## Phase Boundary

Deliver two backward-compatible features that consume Phase 65 per-edge confidence and Phase 66 federated baselines:

1. **CDRIFT** — A new `graphify/drift.py` module that compares the current graph against a persisted snapshot via community-membership Jaccard similarity (never community names/IDs) and classifies each `implements` / `documents` / `tests` edge as `stable`, `community-renamed`, `community-resharded`, or `orphaned`. Snapshots persist under `graphify-out/cache/snapshots/`. A new Drift section is rendered in `GRAPH_REPORT.md` after the Federation section when a prior snapshot exists.
2. **CQUERY** — Extend the MCP `concept_code_hops` tool with three new optional parameters (`min_confidence`, `relations`, `confidence_band`) that filter BFS traversal results, while preserving byte-identical behavior on a frozen v1.12 fixture when callers omit the new parameters.

Out of scope: new edge classes for drift; surfacing drift via MCP/CLI query tools; concept coverage queries (D-3 deferred); UI/HTML viz of drift.

</domain>

<decisions>
## Implementation Decisions

### Snapshot lifecycle (CDRIFT-04)
- **D-01:** Auto-snapshot on every successful `graphify run` — write the snapshot to `graphify-out/cache/snapshots/` at end of pipeline. Zero-friction drift accumulation; no opt-in flag required.
- **D-02:** FIFO retention — keep the last 10 snapshots by mtime. Older snapshots are removed by `drift.py` after writing the new one. No age-based policy.
- **D-03:** Snapshot writes use the same atomic `fsync + os.replace` pattern as Phase 66 `federate.write_manifest` — no partial files on crash.

### Community matching (CDRIFT-01, CDRIFT-02)
- **D-04:** Cross-snapshot community matching uses **set Jaccard** on community membership (node-id sets). Threshold is **0.7 hardcoded** — communities matching ≥ 0.7 are treated as `community-renamed`; below threshold they are `community-resharded`. Edges whose endpoints disappear entirely are `orphaned`. Edges whose endpoints stay in matched communities are `stable`.
- **D-05:** Threshold is a single hardcoded module-level constant in `drift.py` (no env var, no CLI flag). Extract to config later only if a real use case requires it.

### Drift rendering (CDRIFT-03)
- **D-06:** Drift section sits **after the Federation section** in `GRAPH_REPORT.md` (Communities → Federation → Drift). Mirrors the Phase 66 placement decision.
- **D-07:** Section content = a 4-row summary table (`stable` / `community-renamed` / `community-resharded` / `orphaned` with edge counts) + per-class top-N (N=10) listing of source→target + relation for the three non-`stable` classes. Audit-friendly without being unbounded.
- **D-08:** When a snapshot exists but the current graph has zero `implements`/`documents`/`tests` edges, the Drift section still renders with a `0/0/0/0` table and a brief "no drift edges to classify" note. Predictable section presence aids automation.
- **D-09:** When **no prior snapshot exists** (per CDRIFT-03), the Drift section is omitted entirely from `GRAPH_REPORT.md` — no header, no table.

### CQUERY parameters (CQUERY-01)
- **D-10:** `confidence_band` is an **enum** with values `"high"` / `"medium"` / `"low"`. Cutpoints: `high` ≥ 0.8, `medium` 0.5 ≤ x < 0.8, `low` < 0.5. Discoverable via MCP schema. (Final cutpoints to be confirmed against Phase 65 confidence distribution during research; values above are the planning-time default.)
- **D-11:** When both `min_confidence` and `confidence_band` are supplied, both must pass — **AND semantics**. Either may be `None`/omitted independently.
- **D-12:** `relations` is a **whitelist** of relation strings. Default `None` = no filter (all relations traverse). Empty list `[]` = explicit "no relations match" → zero results. Strict semantics: empty-list does not silently mean "all".
- **D-13:** All three parameters are optional and default to `None`; the BFS code path when all three are `None` MUST be byte-identical to v1.12 (CQUERY-02). Validation reuses the existing `concept_code_hops` validator pattern at `graphify/serve.py:2246`.

### Backward-compatibility regression test (CQUERY-02)
- **D-14:** Add a frozen-fixture test under `tests/` that loads a v1.12-shaped graph and asserts the JSON result of `concept_code_hops` with no new params is equal (deep-equal, not just key subset) to a checked-in golden output. The fixture and golden output are committed to the repo.

### Claude's Discretion
- Internal data structures inside `drift.py` (snapshot file format, in-memory dataclasses) — researcher/planner choose, subject to atomic-write + JSON-serializable constraints.
- Exact location of the Drift renderer (`report.py` vs a small `drift_report.py` helper called from `report.py`) — planner decides based on `report.py` size after Phase 66 (currently fine to extend in place per the Federation section pattern).
- Top-N value for per-class drift listings is fixed at 10 in **D-07**; planner may add a small constant in code rather than a config knob.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Phase scope and requirements
- `.planning/ROADMAP.md` §"Phase 67" — phase goal, dependencies, and the four success-criteria assertions that VERIFICATION must close.
- `.planning/REQUIREMENTS.md` lines 26–34 — CDRIFT-01..04 + CQUERY-01..02 requirement IDs and exact wording.
- `.planning/REQUIREMENTS.md` line 64 (D-3) — coverage-lens query is explicitly **deferred** and not part of CQUERY.

### Upstream phases this depends on
- `.planning/phases/65-cconf-per-edge-confidence-cache-split-schema-version/` — per-edge `confidence_score` contract and cache/schema version split that snapshots must respect.
- `.planning/phases/66-cfed-cross-repo-concept-federation-federate-py/` — federation manifest writer (`graphify/federate.py::write_manifest`) is the reference pattern for atomic snapshot writes; Federation section in `report.py` is the reference pattern for the Drift section.

### Code touch points (read before planning)
- `graphify/serve.py:2246` — `_validate_relations_argument` (or equivalent) — pattern to follow when validating new CQUERY params.
- `graphify/serve.py:2290–2566` — `_run_concept_code_hops` and helpers; the BFS loop is where filters apply.
- `graphify/serve.py:3553` — `_tool_concept_code_hops` MCP entry; advertises the JSON schema that gets the three new optional fields.
- `graphify/report.py` — Federation section (Phase 66) is the template for the new Drift section; same kwarg-on-`generate()` pattern.
- `graphify/cluster.py` — community membership is the input to Jaccard matching; ensure stable node-id semantics.
- `graphify/cache.py` — confirm conventions for files under `graphify-out/cache/`.

### Codebase maps
- `.planning/codebase/ARCHITECTURE.md`, `STRUCTURE.md`, `CONVENTIONS.md` — referenced for naming, error-stderr format (Phase 64 stderr contract), and security/path-confinement rules.

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `graphify/federate.py::write_manifest` (Phase 66) — atomic `fsync + os.replace` pattern to copy verbatim for `drift.py` snapshot writes.
- `graphify/report.py` `generate()` — Federation section (Phase 66) provides the exact template for adding a new optional kwarg + section renderer.
- `graphify/serve.py` — `_run_concept_code_hops` (line 2345) is already factored as a pure helper; new filter args should be added as named kwargs with `None` defaults to keep the v1.12 path untouched.
- `graphify/cluster.py` — Leiden produces deterministic communities (seed=42), so membership sets are stable for Jaccard computation.

### Established Patterns
- All external input passes through `graphify/security.py` (path confinement to `graphify-out/`); `cache/snapshots/` paths must use the same helpers.
- Stderr contract from Phase 64 AUDIT-A — any user-visible drift/snapshot error must use `[graphify] error:` + `  hint:` two-line format.
- Test convention: one `tests/test_<module>.py` per module → expect `tests/test_drift.py` and additions to `tests/test_serve.py` (or `tests/test_concept_code_hops.py` if it exists) and `tests/test_report*.py` for the new section.
- Pure unit tests, no network, no filesystem outside `tmp_path`.

### Integration Points
- `graphify/__main__.py::run` (CLI pipeline) — call `drift.write_snapshot(...)` after `report.generate(...)` so the new snapshot does not influence the report it accompanies.
- `graphify/report.py::generate` — accept a new optional `drift_summary` (or similar) kwarg, populated by `__main__.py` after computing drift against the previous snapshot in `cache/snapshots/`.
- `graphify/serve.py::_run_concept_code_hops` — three new optional kwargs threaded into BFS traversal; MCP tool schema in `_tool_concept_code_hops` updated to advertise them.

</code_context>

<specifics>
## Specific Ideas

- The Phase 66 Federation section in `report.py` is the explicit template — same kwarg-on-`generate()` shape, same omit-on-zero policy adapted as omit-on-no-snapshot for Drift.
- Confidence cutpoints for `confidence_band` (high ≥ 0.8 / medium 0.5–0.8 / low < 0.5) are the planning-time default; researcher should sanity-check against the actual Phase 65 confidence distribution before locking in `drift.py`.
- Snapshot file naming should encode either timestamp or manifest hash so FIFO mtime-based eviction is unambiguous — researcher decides the exact filename shape.

</specifics>

<deferred>
## Deferred Ideas

- **Coverage-lens query (D-3 in REQUIREMENTS.md line 64)** — surface % of concepts with `implements` edges above a confidence threshold. Explicitly deferred; depends on CQUERY shipping and being exercised first.
- **Drift exposure via MCP/CLI** — a `drift_query` tool or `graphify drift` subcommand. Not in Phase 67 scope; revisit once GRAPH_REPORT.md drift section sees real usage.
- **Age-based snapshot retention** — only revisit if real users hit the count=10 cap on long-running projects.
- **User-tunable Jaccard threshold (env var or CLI flag)** — extract from D-05 hardcoded constant only if a concrete use case appears.
- **HTML viz of drift** — visual diff in the vis.js export. Out of scope for v1.13.

</deferred>

---

*Phase: 67-CDRIFT + CQUERY — Edge-Level Drift (`drift.py`) & Parameterized Concept Queries*
*Context gathered: 2026-05-06*
