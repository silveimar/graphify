---
phase: 57-elicitation-harness-increment
plan: 01
subsystem: elicitation
tags: [tests, regression-lock, elicitation, sidecar, ELIC-01]
requires: []
provides:
  - "ELIC-01 regression-lock: 6 sidecar-collision tests covering D-02 (happy-path) and D-03 (failure modes)"
affects:
  - tests/test_elicit.py
tech-stack:
  added: []
  patterns:
    - "Regression-lock tests author the sidecar via save_elicitation_sidecar (force=True) per Pitfall 3 — never write raw {nodes, edges} to elicitation.json directly. Exception: dangling-edge test bypasses the save validator and writes the canonical {version, extraction, meta} payload to disk to simulate an externally-produced sidecar (the property under test is build()'s tolerance, not save's strictness)."
key-files:
  created: []
  modified:
    - tests/test_elicit.py
decisions:
  - "[D-02 lock] Elicitation node attrs win on id collision; conflicting edge relation last-wins on (source, target) in undirected graph; confidence preserved across merge."
  - "[D-03 lock] Malformed JSON: load_elicitation_sidecar returns None and emits stderr warning. Missing required node field: save_elicitation_sidecar raises ValueError. Dangling edge endpoint: build() does NOT raise — endpoints absent from node_set are silently filtered."
metrics:
  duration: "12 minutes"
  tasks_completed: 2
  files_modified: 1
  tests_added: 6
  completed: "2026-05-03"
---

# Phase 57 Plan 01: Elicitation sidecar collision regression lock — Summary

Lock down the elicitation sidecar collision merge contract (D-01..D-04) with six new regression tests in `tests/test_elicit.py`. These tests assert behavior that already holds in `graphify/build.py:281-307` and `graphify/elicit.py` today; they prevent regression. **No production code changes** — pure test additions.

## Tests Added

All six functions live in `tests/test_elicit.py` and use only the imports already present at the file head (no new top-level imports). Every test runs against `tmp_path` only — pure unit tests, no network, no fs side effects outside `tmp_path`.

### Happy-path collision tests (Task 1, commit `33981a0`)

| Test | D-row | Asserts |
|------|-------|---------|
| `test_sidecar_node_id_collision_elicitation_wins` | D-02 | Same `id="shared"` in base (`file_type=code`) and elicitation (`file_type=rationale`) → graph node has elicitation attrs (`label="from elicit"`, `file_type="rationale"`) |
| `test_sidecar_edge_conflicting_relation_last_wins` | D-02 | Same `(a, b)` edge in base (`relation="calls"`, `EXTRACTED`) and elicitation (`relation="depends_on"`, `INFERRED`) → undirected graph edge has `relation="depends_on"` and `confidence="INFERRED"` (not "both edges preserved" per RESEARCH Pitfall 1) |
| `test_sidecar_preserves_confidence_across_merge` | D-02 | Self-loop `x→x` with `confidence="AMBIGUOUS"` survives the sidecar round-trip into `G.edges["x","x"]["confidence"]` |

### Failure-mode tests (Task 2, commit `c52ffd3`)

| Test | D-row | Asserts |
|------|-------|---------|
| `test_malformed_sidecar_loader_returns_none` | D-03 | Garbled JSON file → `load_elicitation_sidecar() is None` AND stderr contains `"[graphify] elicitation sidecar invalid JSON"` (locks T-57-02 mitigation) |
| `test_sidecar_missing_required_fields_rejected` | D-03 | Node missing `file_type` → `save_elicitation_sidecar(...)` raises `ValueError` (locks T-57-03 schema-enforcement layer) |
| `test_sidecar_edge_referencing_absent_node` | D-03 | Sidecar with edge `x→ghost` (ghost not declared) authored directly on disk → `build()` does NOT raise; explicit node `x` is preserved; `ghost` is silently filtered (build_from_json drops edges where either endpoint is absent from node_set) |

## Surface Tested

- `graphify/build.py:281-307` — `build()` iteration order and add_node/add_edge attr-overwrite semantics.
- `graphify/build.py:259-261` — dangling-edge filter ("expected, not an error").
- `graphify/elicit.py:182-313` — `save_elicitation_sidecar`, `load_elicitation_sidecar`, `merge_elicitation_into_build_inputs`, `_merge_extractions_by_node_id`.
- `graphify/validate.py` — `validate_extraction` enforcing `REQUIRED_NODE_FIELDS = {"id", "label", "file_type", "source_file"}` invoked from `save_elicitation_sidecar`.

## Threat Register Coverage

All four STRIDE entries from the plan's `<threat_model>` are covered:

| Threat ID | Mitigation Test | Status |
|-----------|-----------------|--------|
| T-57-01 (Tampering) | `test_sidecar_node_id_collision_elicitation_wins` | locked |
| T-57-02 (DoS via malformed JSON) | `test_malformed_sidecar_loader_returns_none` | locked |
| T-57-03 (Input validation) | `test_sidecar_missing_required_fields_rejected` | locked |
| T-57-04 (Dangling-edge tolerance, accept) | `test_sidecar_edge_referencing_absent_node` | documented (no auto-create) |

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Plan must_have for dangling-endpoint behavior was incorrect**

- **Found during:** Task 2, third test (`test_sidecar_edge_referencing_absent_node`)
- **Issue:** Plan asserted "build()'s resulting graph still contains the dangling endpoint as a bare node (no exception)" — this would be true for raw `nx.Graph.add_edge`, but `graphify/build.py:259-261` explicitly filters edges where either endpoint is absent from `node_set` ("skip edges to external/stdlib nodes — expected, not an error"). The "ghost" endpoint is therefore NOT auto-created.
- **Fix:** Test now locks the actual behavior: `build()` raises no exception, the declared node `x` is preserved, and the absent endpoint `ghost` is silently filtered (asserted absent from `G.nodes` and `G.edges`). Threat T-57-04 disposition (`accept`) is unchanged — the property of interest was always "no exception", which is preserved.
- **Files modified:** `tests/test_elicit.py` (single test body + docstring + commit message)
- **Commit:** `c52ffd3`

**2. [Rule 1 - Bug] Plan instructed `save_elicitation_sidecar` for the dangling-edge sidecar; validator rejects it**

- **Found during:** Task 2, third test, first execution
- **Issue:** The plan's action body said "Save via `save_elicitation_sidecar`", but that helper invokes `validate_extraction`, which rejects edges with endpoints not present in the node list (`Edge 0 target 'ghost' does not match any node id`). The test cannot use the save helper to produce the very condition under test.
- **Fix:** Author the sidecar payload directly with the canonical `{version, extraction, meta}` shape (matching `save_elicitation_sidecar`'s output) using `Path.write_text(json.dumps(...))`. This simulates a sidecar produced by an externally relaxed validator or future tooling — exactly the scenario the regression lock is meant to detect.
- **Files modified:** same as above.
- **Commit:** `c52ffd3`

No other deviations. No authentication gates encountered.

## Verification

```bash
$ pytest tests/test_elicit.py -q
................                                                         [100%]
16 passed in 0.20s
```

10 pre-existing tests + 6 new tests = 16 passing.

## Acceptance Criteria

- [x] All six new test functions exist in `tests/test_elicit.py` (verifiable via grep).
- [x] `pytest tests/test_elicit.py -q` is green.
- [x] No new imports beyond what was already in the file head (json, pathlib, pytest, etc.).
- [x] ELIC-01 requirement is testably closed.

## Self-Check: PASSED

- `tests/test_elicit.py`: FOUND (file modified, 16 tests passing)
- Commit `33981a0`: FOUND in `git log`
- Commit `c52ffd3`: FOUND in `git log`
- Six new test functions: all present (verified via `grep -c`)
