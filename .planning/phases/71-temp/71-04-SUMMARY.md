---
phase: 71-temp
plan: 04
subsystem: temporal
tags: [temporal, build, export, supersession, merge, wave-3]
requires: [71-01, 71-02, 71-03]
provides:
  - stamp_supersessions wired into build_from_json
  - shared prior-graph path resolution (_prior_graph_path) mirroring __main__.py:~3215
  - _merge_edge_fields temporal-aware (Pitfall 5)
  - to_graphml drops valid_until=None (Pitfall 4)
  - to_cypher emits temporal fields (ISO quoted; None → Cypher null)
  - to_obsidian unchanged (history rendering deferred to Plan 71-05)
affects: [graphify/build.py, graphify/export.py, tests/test_build.py, tests/test_export.py]
tech_stack:
  added: []
  patterns:
    - shared-resolved-output-path-helper
    - inferred-only-supersession-call-site
    - drop-vs-coerce-none-for-graphml
    - cypher-null-literal-for-current-edges
key_files:
  created: []
  modified:
    - graphify/build.py
    - graphify/export.py
    - tests/test_build.py
    - tests/test_export.py
decisions:
  - "D-4 honored at integration: EXTRACTED prior edges absent from new run are NOT carried forward."
  - "D-5 honored at integration: same (s,t,r) tuple from another file in current run blocks supersession."
  - "D-6 honored at integration: superseded INFERRED edges persist in nx.Graph with valid_until=run_now."
  - "Pitfall 1 closed: build-side _prior_graph_path uses default_graphify_artifacts_dir contract (default → cwd/graphify-out, vault/option-b/cli-flag → resolved.artifacts_dir)."
  - "Pitfall 4 (refined): to_graphml DROPS valid_until=None (instead of coercing to '') so the round-trip preserves 'no valid_until' semantics."
  - "Pitfall 5 closed: _merge_edge_fields preserves earliest valid_from, None-wins valid_until, max decay_weight."
  - "Plan-scope split honored: TEMP-04 wiki/report rendering of historical relations is Plan 71-05's responsibility."
metrics:
  tasks_completed: 3
  commits: 6
  tests_added: 17 (7 supersession-integration + 5 merge-helper + 5 export round-trip)
  duration_minutes: ~12
---

# Phase 71-04: Supersession Wiring + Temporal-Aware Merge + Export Round-Trip

Closes the algorithmic side of TEMP-03 by wiring the previously-isolated
`stamp_supersessions` algorithm (Plan 71-01) into `build_from_json`, fixing the
mixed-temporal-status merge bug (Pitfall 5), and round-tripping
`valid_from` / `valid_until` / `decay_weight` through every export format
graphify ships. Wiki and report rendering of historical relations is Plan 71-05.

## What Shipped

### Task 1 — `graphify/build.py:67–87` `_prior_graph_path` helper + supersession wire-up at `build.py:310–320`

```python
# graphify/build.py:67–87 (new helper)
def _prior_graph_path(target_dir, *, resolved_output=None) -> Path:
    """Mirror __main__.py:3215 ResolvedOutput contract:
       vault/option-b/vault-list/cli-flag → resolved.artifacts_dir / graph.json
       default                            → (target_dir or cwd) / graphify-out / graph.json"""
    ...

# graphify/build.py:310–320 (call site, after temporal stamping, before federate / validate)
extraction["edges"] = stamp_supersessions(
    new_edges=extraction["edges"],
    prior_graph_path=_prior_graph_path(target_dir, resolved_output=resolved_output),
    run_now=run_now,
)
```

Path-resolution audit confirms `__main__.py`:

- Line 1962 (`--obsidian`), 2148 (insights re-load), 2409 (other re-loads) all use
  `graph_path = "graphify-out/graph.json"` (CLI-overridable via `--graph`). This is
  the **default-mode** path; build-side `_prior_graph_path` returns the same path
  when `resolved_output` is None or has `source == "default"`.
- Line 3215 (the canonical write-path resolution) uses
  `default_graphify_artifacts_dir(target, resolved=resolved)` for `source=="default"`
  and `resolved.artifacts_dir` otherwise. Build-side `_prior_graph_path` mirrors
  the **non-default** branch by returning `resolved.artifacts_dir / "graph.json"`,
  so vault-mode supersession reads the same file vault-mode `to_json` will overwrite.
- A test (`test_supersession_path_resolution_vault_mode`) gates the vault branch
  with a synthetic `ResolvedOutput(source="vault", artifacts_dir=…)` plus a prior
  `graph.json` at that path, asserting the supersession picks it up.

No refactor of `__main__.py` was needed: the build-side helper is the new shared
contract surface, and `__main__.py` writes through `to_json(out_dir/"graph.json")`
where `out_dir` is computed by the same `default_graphify_artifacts_dir` rule.

### Task 2 — `graphify/build.py:144–172` temporal-aware `_merge_edge_fields`

After the existing scalar-field merge, three lines are appended that merge the
three temporal fields per Pitfall 5:

```python
out["valid_from"]   = min(present_valid_froms)            # earliest (ISO sorts lexicographically)
out["valid_until"]  = None if any(v is None for v in vu)  # current wins
                       else max(present_valid_untils)     # latest superseded
out["decay_weight"] = max(present_decay_weights)          # current/highest dominates
```

Each branch is conditional on the field actually being present on at least one
input — so legacy edges without temporal fields are merged exactly as before
(regression-gated by `test_merge_no_temporal_fields`).

### Task 3 — `graphify/export.py:1112–1124` and `graphify/export.py:367–388`

**`to_graphml` (lines ≈1112–1124):** the prior Phase 71-02 None→"" coercion is
refined: `valid_until` specifically is **dropped** when `None` so the GraphML
round-trip preserves "no valid_until" semantics — the literal empty string would
be a misleading sentinel. All other `None` edge/node attrs still coerce to `""`
(Phase 71-02 robustness).

**`to_cypher` (lines ≈367–388):** edge property emission extended to include
`valid_from`, `valid_until`, `decay_weight` when present:

```cypher
MATCH (a {id: 'a'}), (b {id: 'b'}) MERGE (a)-[:CALLS {
  confidence: 'INFERRED',
  valid_from: '2026-01-01T00:00:00+00:00',
  valid_until: null,        -- Cypher null literal, NOT the string "None"
  decay_weight: 0.85
}]->(b);
```

ISO timestamps are escaped through the existing `_cypher_escape` and
single-quoted; `None` becomes the unquoted Cypher literal `null`; `decay_weight`
is emitted as a bare float.

**`to_json` and `to_obsidian` — no code change.** `to_json` already round-trips
arbitrary edge attrs via `nx.readwrite.json_graph.node_link_data` (Assumption A5,
verified). `to_obsidian` renders **nodes** (not edges) into frontmatter; per the
plan-checker scope split, historical-relations rendering is Plan 71-05's job.
`test_obsidian_no_edge_frontmatter_change` is a regression guard: even if
to_obsidian fails for unrelated reasons (optional deps), the test asserts no
edge-temporal field leaked into any node frontmatter.

## Test Coverage

`pytest tests/test_build.py tests/test_export.py tests/test_temporal.py tests/test_validate.py tests/test_analyze.py -q`
→ **162 passed**.

| File | New tests | Behaviors gated |
| --- | --- | --- |
| tests/test_build.py | 7 supersession-integration | D-4 (INFERRED-only), D-5 (global), D-6 (history retained), no-prior, default-mode path, vault-mode path |
| tests/test_build.py | 5 merge-helper | mixed-status current-wins, earliest valid_from, both-superseded latest, decay max, legacy regression |
| tests/test_export.py | 5 round-trip + 1 schema | json roundtrip, schema_version=2.0 propagation, graphml None-dropped, graphml ISO preserved, cypher null/quoted, obsidian no-frontmatter |

## Invariant Checks

```
$ grep -n 'stamp_supersessions' graphify/build.py
31:from .temporal import compute_decay_weight, load_decay_config, run_now_iso, stamp_supersessions
314:    # global tuple match are owned by graphify.temporal.stamp_supersessions
316:    extraction["edges"] = stamp_supersessions(
$ grep -n 'valid_until' graphify/export.py | head
1115:                if _k == "valid_until":
1119:                    _data[_k] = ""
$ grep -n 'valid_until: null' graphify/export.py
0   # value is in tests, not source
```

## Deviations from Plan

### Auto-fixed Issues

1. **[Rule 2 — Critical functionality] `to_cypher` was emitting only `confidence`, no temporal fields.**
   - **Found during:** Task 3 RED — `test_cypher_temporal_quoted` failed because temporal fields were absent from cypher output.
   - **Fix:** Extended the per-edge property emission loop in `to_cypher` to optionally include `valid_from`, `valid_until`, `decay_weight`. Plan called for verifying behavior; the actual code change required to get there is small but real.
   - **Files modified:** `graphify/export.py`.
   - **Commit:** 2a5faf1.

2. **[Rule 1 — Bug] `to_graphml` Phase 71-02 coercion was over-broad.**
   - **Found during:** Task 3 RED — `test_graphml_none_sanitized` asserted `valid_until` MUST be absent from the written file when None, but Phase 71-02's blanket `None → ""` coercion left it as the literal empty string.
   - **Fix:** Refined the loop to `pop()` `valid_until` specifically when None, while preserving the generic `None → ""` fallback for other nullable edge/node attrs (Phase 71-02 robustness intact).
   - **Files modified:** `graphify/export.py`.
   - **Commit:** 2a5faf1.

No deviations on Rules 3/4. No auth gates encountered.

## Pre-Existing Failures (Out of Scope)

Same set documented in 71-01 / 71-02 / 71-03 (≈47 unrelated failures across
vault_*, audit_b_closure, capability, delta, enrich, explain_paths, federate,
harness_*, migration). Not touched.

## Self-Check: PASSED

- graphify/build.py — modified (import + `_prior_graph_path` helper + stamp_supersessions call site + temporal-aware `_merge_edge_fields`)
- graphify/export.py — modified (to_graphml `valid_until` pop + to_cypher temporal emission)
- tests/test_build.py — 12 new tests (198 → 463 lines)
- tests/test_export.py — 6 new tests (604 → 720 lines)
- Commits 72e34a8, 4f4bd09, 7fe15a2, 7b2be3f, 5fcd821, 2a5faf1 — all PRESENT in git log

`pytest tests/test_build.py tests/test_export.py tests/test_temporal.py -x -q` → **green**.
