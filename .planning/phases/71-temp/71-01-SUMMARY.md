---
phase: 71-temp
plan: 01
subsystem: temporal
tags: [temporal, schema, validate, wave-0, foundation]
requires: []
provides:
  - graphify.temporal.run_now_iso
  - graphify.temporal.load_decay_config
  - graphify.temporal.compute_decay_weight
  - graphify.temporal.stamp_supersessions
  - SCHEMA_VERSION="2.0"
  - tests/fixtures/graph_legacy_v113.json
  - tests/fixtures/graph_temporal_v20.json
  - pinned_run_ts conftest fixture
affects: [graphify/validate.py, graphify/build.py, pyproject.toml]
tech_stack:
  added: [PyYAML (lazy import; already optional via [obsidian]/[mcp]/[routing])]
  patterns: [stdlib-only-import-with-lazy-yaml, in-code-default-fallback, INFERRED-only-supersession]
key_files:
  created:
    - graphify/temporal.py
    - graphify/temporal_config.yaml
    - tests/test_temporal.py
    - tests/fixtures/graph_legacy_v113.json
    - tests/fixtures/graph_temporal_v20.json
  modified:
    - graphify/build.py (SCHEMA_VERSION 1.13 → 2.0)
    - graphify/validate.py (validate_extraction_for_write extended)
    - tests/conftest.py (pinned_run_ts fixture)
    - tests/test_validate.py (Phase 71 test block + legacy test updated)
    - tests/test_build.py (constant assertion bumped to 2.0)
    - tests/test_export.py (schema_version assertion bumped to 2.0)
    - pyproject.toml (package-data adds temporal_config.yaml)
decisions:
  - "D-1 honored: GRAPHIFY_RUN_TS overrides wall clock; UTC ISO default."
  - "D-2 honored: compute_decay_weight fails open at 1.0 on unknown function or unparseable timestamps."
  - "D-3 honored: load_decay_config falls back to in-code defaults on PyYAML missing / file missing / YAMLError."
  - "D-4 honored: stamp_supersessions stamps INFERRED only — EXTRACTED prior edges never stamped."
  - "D-5 honored: supersession match is the GLOBAL (source,target,relation) tuple across the whole new run, regardless of source_file."
  - "D-6 honored: superseded edges are retained with valid_until=run_now (history not deleted)."
  - "D-8 honored: SCHEMA_VERSION = '2.0' single-source-of-truth, read/write split kept."
  - "T-71-01 mitigated: yaml.safe_load only; ImportError, FileNotFoundError, OSError, YAMLError caught → defaults."
  - "T-71-05 mitigated: valid_from / decay_weight NOT added to REQUIRED_EDGE_FIELDS — read-mode legacy compat preserved."
  - "T-71-13 mitigated: malformed prior graph.json (invalid JSON, non-dict, networkx parse failure) → returns new_edges unchanged."
metrics:
  tasks_completed: 2
  commits: 4
  tests_added: 26 (19 in test_temporal.py + 7 in test_validate.py Phase 71 block)
  fixtures_added: 2
---

# Phase 71-01: Temporal Foundation Summary

Wave 0 foundation for Phase 71 temporal-edge-validity: a new `graphify.temporal` helper module
(with the FULL `stamp_supersessions` algorithm implemented and unit-tested), schema bump
1.13 → 2.0, write-mode validator extension for per-edge temporal fields, and the test fixtures
plus `pinned_run_ts` conftest fixture every later plan in this phase depends on.

## What Shipped

### `graphify/temporal.py` (full surface, no stubs)

| Function | Behavior |
| --- | --- |
| `run_now_iso() -> str` | UTC ISO-8601 timestamp; pinned by `GRAPHIFY_RUN_TS` env var (D-1). |
| `load_decay_config(path=None) -> dict` | YAML loader with lazy PyYAML import; falls back to `_IN_CODE_DEFAULTS` on ImportError / FileNotFoundError / OSError / YAMLError. Always merges a valid `default` key (D-3, T-71-01). |
| `compute_decay_weight(*, relation, valid_from, run_now, config) -> float` | Per-relation lookup; exponential `max(floor, 0.5 ** (age_days / half_life))`. Fail-open returns 1.0 on unknown function or unparseable timestamps (D-2). |
| `stamp_supersessions(*, new_edges, prior_graph_path, run_now) -> list[dict]` | INFERRED-only history stamper. Builds the new-run global match set on `(source, target, relation)`. Prior INFERRED edges absent from the set are appended with `valid_until=run_now`. EXTRACTED prior edges and reproduced tuples are skipped. Malformed/missing prior graph → returns `new_edges` unchanged (D-4 / D-5 / D-6 / T-71-13). |

### `graphify/temporal_config.yaml`

Default exponential decay (`half_life_days=30`, `floor=0.1`) plus a faster decay for
`semantically_similar_to` (`half_life_days=14`). Shipped via `[tool.setuptools.package-data]`.

### Validators

`graphify/validate.py::validate_extraction_for_write` now appends per-edge errors:

- `"Edge {i} missing required field 'valid_from' (write-mode)"`
- `"Edge {i} 'decay_weight' must be float in [0.0, 1.0] (write-mode)"`

`valid_until` may be `None` (still valid), an ISO string, or absent. The base
`validate_extraction` is untouched: legacy v1.13 graphs still validate with zero errors,
and `validate_extraction_for_read` continues to delegate straight through.

### Schema bump

`graphify/build.py:37` — `SCHEMA_VERSION = "2.0"`. Already stamped in-memory by the
existing Phase 70.2 stamping inside `build_from_json` and `build()` (lines 314 and 351).
Updated existing assertions in `tests/test_build.py` and `tests/test_export.py` to
match the new constant.

### Wave 0 fixtures

- `tests/fixtures/graph_legacy_v113.json` — pre-temporal graph (schema_version=1.13, no
  valid_from/valid_until/decay_weight). Used to gate read-mode backward compat.
- `tests/fixtures/graph_temporal_v20.json` — temporal graph (schema_version=2.0, mixed
  valid_until including null and ISO strings, decay_weight values across the range).

`tests/conftest.py` exposes `pinned_run_ts` which monkeypatches
`GRAPHIFY_RUN_TS=2026-05-07T12:00:00+00:00` for deterministic temporal tests.

## Test Coverage

`pytest tests/test_temporal.py tests/test_validate.py tests/test_build.py tests/test_export.py -q`
→ **83 passed** (post-merge of all four commits).

| File | New tests |
| --- | --- |
| tests/test_temporal.py | 19 (run_now_iso × 3, load_decay_config × 4, compute_decay_weight × 5, stamp_supersessions × 7) |
| tests/test_validate.py | 7 (Phase 71 block: legacy fixture read, v2.0 fixture read, valid_from required, decay_weight bounds × 4 cases, null valid_until, base validator additive, SCHEMA_VERSION constant) |

Supersession algorithm coverage gates D-4 (INFERRED-only), D-5 (global tuple match),
D-6 (history retention), no-prior-graph case, malformed-JSON, and non-dict-root.

## Deviations from Plan

### Auto-fixed Issues

1. **[Rule 1 — Bug] Updated two pre-existing assertions pinned to '1.13'.**
   - **Found during:** Task 2 GREEN verification.
   - **Issue:** `tests/test_build.py::test_schema_version_constant_value` and
     `tests/test_export.py::test_to_json_emits_schema_version` asserted the old value.
   - **Fix:** Bumped both assertions to `"2.0"`; updated docstring of the build test to
     reference Phase 71 / D-8.
   - **Files modified:** `tests/test_build.py`, `tests/test_export.py`.
   - **Commit:** 12c20b7.

2. **[Rule 1 — Bug] Updated `test_write_accepts_with_schema_version` for schema 2.0 contract.**
   - **Found during:** Task 2 GREEN verification.
   - **Issue:** The Phase 65 test stamped only `schema_version="1.13"`; under the new
     Phase 71 write contract every edge needs `valid_from` and `decay_weight`.
   - **Fix:** Updated the test to stamp `schema_version="2.0"` and the three temporal fields
     on every edge (using node_link "links" key as fallback to "edges"), preserving the
     original intent (write-mode accepts a properly-stamped legacy graph).
   - **Files modified:** `tests/test_validate.py`.
   - **Commit:** 12c20b7.

No deviations on Rules 2/3/4. No auth gates encountered.

## Pre-Existing Failures (Out of Scope)

`pytest tests/ --tb=no` reports 47 failures, of which **all 47 are pre-existing** and
unrelated to this plan (vault_parity, vault_cli, vault_cwd, audit_b_closure, capability,
delta, enrich, explain_paths, federate, harness_import, harness_interchange, migration).
Confirmed via `git stash && pytest && git stash pop` — same failure set on the
pre-change tree. Logged here per scope-boundary rule, not fixed.

## Self-Check: PASSED

- graphify/temporal.py — FOUND
- graphify/temporal_config.yaml — FOUND
- tests/test_temporal.py — FOUND
- tests/fixtures/graph_legacy_v113.json — FOUND
- tests/fixtures/graph_temporal_v20.json — FOUND
- Commits 6f34348, 08e71b1, 876d959, 12c20b7 — ALL PRESENT in git log

`python -c "from graphify.temporal import run_now_iso, load_decay_config, compute_decay_weight, stamp_supersessions"` imports clean.
`grep -n '^SCHEMA_VERSION' graphify/build.py` → `37:SCHEMA_VERSION = "2.0"`.
