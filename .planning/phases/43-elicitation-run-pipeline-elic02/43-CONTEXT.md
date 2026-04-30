# Phase 43: Elicitation ↔ run pipeline (ELIC-02) — Context

**Gathered:** 2026-04-30  
**Status:** Ready for planning

<domain>

## Phase Boundary

Close the **ELIC-02** gap from `.planning/v1.9-MILESTONE-AUDIT.md`: elicitation sidecar data (`elicitation.json` under `artifacts_dir`) must be merged into extraction-shaped inputs **before** graph assembly so `validate_extraction` runs on the combined payload with the same dangling-edge warning policy as other merges. Deliver **code** (merge wiring at every corpus→`build` path that has an `artifacts_dir`), **tests** proving fixture sessions validate and merge order, and **docs** updates so the contract is discoverable (ties to ELIC-07).

**In scope:** Merge helper usage, ordering/dedup alignment with `build()`, migration/watch fixes, tests, doc touchpoints.  
**Out of scope:** ELIC-04 idempotent re-run semantics (separate requirement), new harness targets (PORT-*), changing elicitation interview content (ELIC-01).

Depends on Phase 39 baseline (sidecar layout, `save_elicitation_sidecar` / `load_elicitation_sidecar`).

</domain>

<decisions>

## Implementation Decisions

### Merge semantics and ordering

- **D-01:** Before any `build(extractions: list[dict], ...)` call where extractions come from corpus extraction and an `artifacts_dir` is known, replace the raw list with `merge_elicitation_into_build_inputs(extractions, artifacts_dir)`. If `artifacts_dir` is `None`, skip merge (preserve current behavior).
- **D-02:** Ordering is **corpus extraction(s) first, elicitation sidecar last** — matches `build(..., elicitation=...)` documentation (elicitation wins on duplicate node IDs). The helper appends the sidecar extraction only when `elicitation.json` exists and parses; oversized or invalid JSON is skipped with stderr warnings (existing `load_elicitation_sidecar` behavior).
- **D-03:** Validation path is unchanged: merged combined dict flows through `build()` → `build_from_json()` → `validate_extraction()` with the same “real errors vs dangling edge” filtering already in `build_from_json`.

### Call sites (inventory locked for implementation)

- **D-04:** **`graphify/migration.py`** — preview workflow calls `run_corpus(..., out_dir=resolved.artifacts_dir, ...)` then **`build([extraction])` without merge**. This path **must** use `merge_elicitation_into_build_inputs([extraction], resolved.artifacts_dir)` before `build()` so vault migration previews include elicitation when present.
- **D-05:** **`graphify/watch.py`** — `_rebuild_graph` uses `build_from_json(result)` only. When `graphify-out/elicitation.json` exists, rebuild must incorporate it using the same ordering as D-01/D-02 (e.g. `build(merge_elicitation_into_build_inputs([result], out)), ...)` or equivalent single combined dict before `build_from_json`, without double-counting nodes).
- **D-06:** **`graphify/pipeline.run_corpus`** returns a single extraction dict only — no change required here; merge responsibility sits **at every `build` / full-graph caller** that knows `artifacts_dir`.
- **D-07:** **`graphify run` (`__main__.py`)** — currently invokes only `run_corpus` (detect → extract) and does **not** call `build` or write `graph.json`. For ELIC-02 product closure: **either** (recommended) extend `run` so that when output is vault-/resolved-artifacts–backed, the command also merges sidecar and persists a graph bundle consistent with other CLI outputs (planner to confirm minimal surface: `graph.json` only vs full cluster/report); **or** document explicitly that `run` is extract-only and ELIC-02 is satisfied via paths that already call `build` + `artifacts_dir`, once migration/watch are fixed. **Preference captured:** prefer wiring merge everywhere `build` is used first; then decide `run` extension based on backward-compat review (tests must spell out chosen contract).

### Documentation and tests

- **D-08:** Update or add references so ELIC-07’s “how elicitation joins the graph” matches implementation: at minimum `docs/ELICITATION.md`, CLI `--help` cross-links where the project already does so for elicit/run.
- **D-09:** Tests: extend `tests/test_elicit.py` or add focused tests that (1) fixture elicitation dict passes `validate_extraction`, (2) merged list fed to `build()` includes sidecar nodes when file present, (3) migration/watch code paths are covered with `tmp_path` fixtures where practical without network.

### Claude’s discretion

- Exact **`run`** UX (always write `graph.json` vs new flag vs docs-only exemption) after D-04/D-05 land — choose the smallest change that keeps ELIC-02 acceptance criteria verifiable in CI.

</decisions>

<canonical_refs>

## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Requirements and audit

- `.planning/REQUIREMENTS.md` — § ELIC-02 (validated extraction-shaped graph input); § ELIC-07 (discovery docs / sidecar merge explanation).
- `.planning/v1.9-MILESTONE-AUDIT.md` — ELIC-02 gap notes (if present in repo snapshot).

### Library contracts

- `graphify/elicit.py` — `ELICITATION_SIDECAR_FILENAME`, `load_elicitation_sidecar`, `merge_elicitation_into_build_inputs`, `save_elicitation_sidecar`.
- `graphify/build.py` — `build()`, `build_from_json()`, merge ordering and validation comments.
- `graphify/validate.py` — `validate_extraction`.

### Pipeline entrypoints

- `graphify/pipeline.py` — `run_corpus` (extract-only; no merge).
- `graphify/__main__.py` — `run` command branch (~`cmd == "run"`).
- `graphify/migration.py` — vault migration preview: `run_corpus` → `build`.
- `graphify/watch.py` — incremental rebuild → `build_from_json`.

### Documentation

- `docs/ELICITATION.md` — user-facing elicitation overview and join semantics.

</canonical_refs>

<code_context>

## Existing Code Insights

### Reusable assets

- **`merge_elicitation_into_build_inputs`** (`graphify/elicit.py`) — appends sidecar extraction when `elicitation.json` exists under `artifacts_dir`; already unit-tested in `tests/test_elicit.py` for append/no-op cases.

### Established patterns

- **`build()`** merges multiple extractions then validates; optional `elicitation=` kwarg duplicates “append last” semantics — callers using the merge helper should pass **either** a merged list **or** the `elicitation=` kwarg, not both, to avoid double-merge.

### Integration points

- **Migration preview** is a high-value fix: it already has `resolved.artifacts_dir` but omits sidecar merge before `build`.
- **Watch** rebuild reads/writes `graphify-out/graph.json` but ignores `elicitation.json` unless merged into `result` before `build_from_json`.
- **`graphify run`** stops after `run_corpus`; no graph write today — ELIC-02 “reaches build” is currently unsatisfied for users who only use `run` unless another stage invokes `build` with merge.

</code_context>

<specifics>

## Specific Ideas

No additional user specifics beyond milestone audit + ELIC-02/07 requirements.

</specifics>

<deferred>

## Deferred Ideas

- Full **`run`** → cluster → export parity with skill-driven pipelines (if only `graph.json` + merge is in scope for 43, richer outputs stay deferred).
- **ELIC-04** preview/merge UX for repeated elicitation runs.

**Reviewed Todos (not folded)**  
None — stub context only.

</deferred>

---

*Phase: 43-elicitation-run-pipeline-elic02*  
*Context gathered: 2026-04-30*
