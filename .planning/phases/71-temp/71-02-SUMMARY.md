---
phase: 71-temp
plan: 02
subsystem: temporal
tags: [temporal, build, stamping, wave-2]
requires: [71-01]
provides:
  - build_from_json edge stamping (valid_from / valid_until / decay_weight)
  - run_now single-source-of-truth invariant
affects: [graphify/build.py, graphify/export.py, tests/test_build.py]
tech_stack:
  added: []
  patterns: [setdefault-preserves-prior-stamp, single-clock-per-build, fail-open-decay]
key_files:
  created: []
  modified:
    - graphify/build.py
    - graphify/export.py
    - tests/test_build.py
decisions:
  - "D-1 honored: run_now_iso() called exactly once per build_from_json (top of function, never inside loop)."
  - "D-2 honored: compute_decay_weight + load_decay_config wired with relation key for per-relation half-life."
  - "Pitfall 3 honored: SCHEMA_VERSION='2.0' stamped via existing in-memory line untouched."
  - "Pitfall 6 honored: AMBIGUOUS edges decay alongside INFERRED — only EXTRACTED is fixed at 1.0."
  - "T-71-08 mitigated: e.setdefault(...) preserves pre-stamped valid_from/valid_until/decay_weight."
metrics:
  tasks_completed: 1
  commits: 2
  tests_added: 8
  duration_minutes: ~10
---

# Phase 71-02: Build-Time Temporal Stamping Summary

Wires temporal stamping into `build_from_json` so every edge produced by the build
pipeline carries `valid_from`, `valid_until`, and `decay_weight`. The downstream
analyze filter (71-03) and export round-trip (71-04) can rely on these fields
being universally present.

## What Shipped

### `graphify/build.py`

New module-level import:
```python
from .temporal import compute_decay_weight, load_decay_config, run_now_iso
```

New stamping block inserted **after** `_normalize_concept_code_edges` (line ~217)
and **before** the optional federation hook + `validate_extraction` call. Run-clock
is computed once and decay config is loaded once; both feed a single linear pass
over `extraction["edges"]`:

```python
run_now = run_now_iso()
decay_cfg = load_decay_config()
for e in extraction["edges"]:
    e.setdefault("valid_from", run_now)
    e.setdefault("valid_until", None)
    if "decay_weight" not in e:
        if e.get("confidence") == "EXTRACTED":
            e["decay_weight"] = 1.0
        else:
            e["decay_weight"] = compute_decay_weight(
                relation=e.get("relation", ""),
                valid_from=e["valid_from"],
                run_now=run_now,
                config=decay_cfg,
            )
```

`setdefault` (not `=`) preserves any pre-stamped fields on incoming edges (T-71-08:
supersession test fixtures, upstream-stamped edges). The `if "decay_weight" not in e`
guard does the same for `decay_weight`.

`G.graph["schema_version"] = SCHEMA_VERSION` line in both `build_from_json` and `build`
remains untouched (Phase 70.2 precedent — Pitfall 3).

### `tests/test_build.py`

Added 8 tests under the Phase 71-02 block:

| Test | Truth gated |
| --- | --- |
| `test_build_stamps_valid_from` | Every edge has `valid_from == run_now` |
| `test_build_valid_until_none_default` | `valid_until=None` for fresh edges |
| `test_build_extracted_decay_one` | EXTRACTED → `decay_weight==1.0` |
| `test_build_inferred_decays` | INFERRED far in past → `decay_weight < 1.0` |
| `test_build_ambiguous_decays_like_inferred` | AMBIGUOUS decays (Pitfall 6 / A4) |
| `test_schema_version_2_0_in_memory` | `G.graph['schema_version']=='2.0'` via build_from_json AND build |
| `test_run_now_computed_once` | `run_now_iso` called exactly once per build (counter monkeypatch over 3-edge fixture) |
| `test_existing_temporal_fields_preserved` | Pre-stamped `valid_from` not overwritten (setdefault) |

All 8 use `pinned_run_ts` from the Plan 71-01 conftest fixture. The "computed once"
test monkeypatches `graphify.build.run_now_iso` to a counting wrapper and asserts
the counter is exactly 1 after a multi-edge `build_from_json` call — proving the
clock is not pulled inside the per-edge loop.

## Test Coverage

`pytest tests/test_build.py tests/test_temporal.py tests/test_validate.py -x -q`
→ **64 passed**.

`pytest tests/test_build.py tests/test_temporal.py tests/test_validate.py tests/test_export.py tests/test_extract.py -q`
→ **112 passed** (full graphify-cone regression).

## Invariant Checks

```
$ grep -c 'run_now_iso()' graphify/build.py
1
$ grep -n 'setdefault.*valid_from' graphify/build.py
244:        e.setdefault("valid_from", run_now)
```

`run_now_iso()` is called at exactly one site (top of `build_from_json`), satisfying
the per-build single-clock invariant.

## Deviations from Plan

### Auto-fixed Issues

1. **[Rule 1 — Bug] `to_graphml` rejected None edge/node attributes.**
   - **Found during:** Task 1 GREEN regression run (`pytest tests/test_export.py`).
   - **Issue:** Stamping `valid_until=None` on every edge tripped
     `nx.write_graphml`, which raises `TypeError: GraphML does not support type
     <class 'NoneType'> as data values.` Three pre-existing tests
     (`test_to_graphml_creates_file`, `test_to_graphml_valid_xml`,
     `test_to_graphml_has_community_attribute`) flipped from green to red.
   - **Confirmed cause:** `git stash && pytest …graphml… && git stash pop` showed
     the same three tests pass on the pre-change tree.
   - **Fix:** In `to_graphml`, coerce `None` edge and node attribute values to
     empty string `""` on the working `H = G.copy()` before calling
     `nx.write_graphml`. Per-attribute pass; non-None values untouched.
   - **Files modified:** `graphify/export.py`.
   - **Commit:** 6475855 (squashed with the GREEN feat commit).

No deviations on Rules 2/3/4. No auth gates encountered.

## Pre-Existing Failures (Out of Scope)

Same set documented in 71-01 SUMMARY (47 unrelated failures across vault_*,
audit_b_closure, capability, delta, enrich, explain_paths, federate,
harness_*, migration). Not touched.

## Self-Check: PASSED

- graphify/build.py — modified (import + stamping block at line ~239–252)
- graphify/export.py — modified (None-coercion in to_graphml)
- tests/test_build.py — 8 new tests added
- Commits 4440f5d (RED test) and 6475855 (GREEN feat + Rule-1 fix) — both PRESENT in git log

`grep -c 'run_now_iso()' graphify/build.py` → 1 (single call site invariant).
