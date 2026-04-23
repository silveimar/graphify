---
phase: 10-cross-file-semantic-extraction
plan: "09"
subsystem: cli-ux / mcp-serve
tags: [gap-closure, error-handling, alias-resolution, tdd]
dependency_graph:
  requires: []
  provides:
    - clean-dedup-cli-errors
    - no-seed-nodes-alias-visibility
  affects:
    - graphify/__main__.py
    - graphify/serve.py
tech_stack:
  added: []
  patterns:
    - stat().st_size == 0 check before json.loads (zero-byte short-circuit)
    - try/except (RuntimeError, ValueError) at CLI boundary for clean error UX
    - resolved_from_alias guard mirrored from happy-path to no_seed_nodes path
key_files:
  created: []
  modified:
    - graphify/__main__.py
    - graphify/serve.py
    - tests/test_main_cli.py
    - tests/test_serve.py
decisions:
  - Zero-byte graph file → empty extraction short-circuit (not a JSONDecodeError)
  - RuntimeError + ValueError both caught at the --dedup CLI boundary (single except clause)
  - resolved_from_alias guard copied verbatim from happy-path line ~928 to no_seed_nodes early-return
  - "Consider whether node_id should be a scoring seed in _score_nodes" left deferred (design question, not gap closure)
metrics:
  duration_minutes: 9
  completed_date: "2026-04-17"
  tasks_completed: 2
  files_modified: 4
---

# Phase 10 Plan 09: UAT Gap Closure (tests 2, 3, 8) Summary

One-liner: Clean error surfacing for dedup CLI edge-cases (zero-byte file, missing extra, path escape) and MCP alias-resolution visibility on the no_seed_nodes short-circuit path.

## What Was Built

Three UX polish fixes across two files, validated by four TDD regression tests (RED before GREEN).

### Fix 1 — Zero-byte graph file treated as empty extraction (UAT gap test 2)

**`graphify/__main__.py`** — `--dedup` handler, before `json.loads()`:

```python
if source_path.exists() and source_path.stat().st_size == 0:
    extraction = {"nodes": [], "edges": []}
else:
    extraction = json.loads(source_path.read_text(encoding="utf-8"))
```

A zero-byte `--graph` file now exits 0 with a 0-merge empty report instead of surfacing `JSONDecodeError: Expecting value: line 1 column 1 (char 0)`.

### Fix 2 — Clean error messages at CLI boundary (UAT gaps test 2b + test 3)

**`graphify/__main__.py`** — wraps `_dedup()` + `write_dedup_reports()`:

```python
try:
    new_extraction, report = _dedup(extraction, ...)
    write_dedup_reports(report, out_dir)
except (RuntimeError, ValueError) as e:
    print(f"error: {e}", file=sys.stderr)
    sys.exit(1)
```

- `RuntimeError` from `_get_model()` (missing `[dedup]` extra) → `error: sentence-transformers not installed; install graphify[dedup]`
- `ValueError` from `write_dedup_reports()` (path confinement, T-10-01) → `error: out_dir must be within cwd`

Both produce a single-line error message and exit 1 with no Python traceback.

### Fix 3 — resolved_from_alias visible on no_seed_nodes path (UAT gap test 8)

**`graphify/serve.py`** — `_run_query_graph()` no_seed_nodes early-return:

```python
if not start_nodes:
    meta = { ..., "status": "no_seed_nodes", ... }
    if _resolved_aliases:
        meta["resolved_from_alias"] = _resolved_aliases   # ← NEW
    return "" + QUERY_GRAPH_META_SENTINEL + json.dumps(meta, ...)
```

When `node_id='auth'` redirects via alias_map but the canonical has no scoreable neighbors (so `start_nodes` is empty), agents now receive `resolved_from_alias: {"authentication_service": ["auth"]}` in the `no_seed_nodes` meta — consistent with the happy-path behavior already working.

## Test Count

| State | Tests passing |
|-------|---------------|
| Before plan | 1174 |
| After RED (4 new tests, all failing) | 1174 passing, 4 failing |
| After GREEN | **1178 passing** |

4 new regression tests added:
- `tests/test_main_cli.py::test_dedup_zero_byte_graph_exits_clean`
- `tests/test_main_cli.py::test_dedup_path_escape_clean_error`
- `tests/test_main_cli.py::test_dedup_missing_extra_clean_error`
- `tests/test_serve.py::test_no_seed_nodes_surfaces_resolved_from_alias`

## Commits

| Task | SHA | Message |
|------|-----|---------|
| Task 1 (RED) | 57b5468 | `test(10-09): add RED regression tests for dedup CLI UX + MCP no_seed_nodes alias visibility` |
| Task 2 (GREEN) | be7a391 | `fix(10-09): wrap dedup CLI errors, handle zero-byte graph, surface alias redirect on no_seed_nodes (closes UAT gaps tests 2, 3, 8)` |

## UAT Gaps Closed

| Gap ID | Description | Status |
|--------|-------------|--------|
| test 2 | Zero-byte graph exits 0 with empty report, no JSONDecodeError | CLOSED |
| test 2b | Missing [dedup] extra → clean `error: ...` exit 1, no traceback | CLOSED |
| test 3 | Path escape `--out-dir /tmp/...` → clean `error: ...` exit 1, no traceback | CLOSED |
| test 8 | MCP `no_seed_nodes` meta includes `resolved_from_alias` when alias was resolved | CLOSED |

## Deferred Items

| Item | Reason |
|------|--------|
| "Consider whether `arguments['node_id']` should be a seed source in `_score_nodes`" (UAT test 8 sub-item) | Design decision beyond gap closure scope. Currently `_score_nodes` uses question terms only; making node_id a direct seed source would change the scoring contract for all callers. Deferred to a future plan. |

## Deviations from Plan

None — plan executed exactly as written. The `test_dedup_path_escape_clean_error` test was adjusted to pass `--graph` explicitly (so the CLI reaches `write_dedup_reports()` and triggers the path-confinement check rather than failing earlier on missing source file) — this is a test correctness fix, not a plan deviation.

## Threat Flags

None. All code paths touched are already within audited trust boundaries:
- T-10-01 path confinement: now surfaced cleanly rather than as a traceback
- T-10-09-02 information disclosure: traceback suppression reduces leakage of sys.path info
- T-10-09-03 alias metadata: resolved_from_alias is graph-internal data, not sensitive

## TDD Gate Compliance

- RED gate commit: 57b5468 (`test(10-09): ...`) — 4 tests, all failing
- GREEN gate commit: be7a391 (`fix(10-09): ...`) — 4 tests, all passing
- Both gates present in git log. Compliant.

## Self-Check: PASSED

- [x] `tests/test_main_cli.py::test_dedup_zero_byte_graph_exits_clean` PASSED
- [x] `tests/test_main_cli.py::test_dedup_path_escape_clean_error` PASSED
- [x] `tests/test_main_cli.py::test_dedup_missing_extra_clean_error` PASSED
- [x] `tests/test_serve.py::test_no_seed_nodes_surfaces_resolved_from_alias` PASSED
- [x] Full suite: 1178 passing (0 regressions introduced)
- [x] RED commit 57b5468 exists in git log
- [x] GREEN commit be7a391 exists in git log
