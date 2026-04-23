---
phase: 20-diagram-seed-engine
plan: 03
subsystem: mcp
tags: [mcp, registry, serve, d-02-envelope, d-16-alias, manifest-05, manifest-06]
requirements: [SEED-09, SEED-10, SEED-11]
dependency_graph:
  requires:
    - graphify/mcp_tool_registry.py::build_mcp_tools (registry convention)
    - graphify/serve.py::QUERY_GRAPH_META_SENTINEL (D-02)
    - graphify/serve.py::_run_get_focus_context_core (template)
    - graphify/serve.py::_run_query_graph (alias closure template)
    - graphify-out/seeds/seeds-manifest.json (D-03, Plan 20-02)
    - graphify-out/seeds/{seed_id}-seed.json (SEED-04, Plan 20-02)
  provides:
    - graphify.serve._run_list_diagram_seeds_core (SEED-09)
    - graphify.serve._run_get_diagram_seed_core (SEED-10)
    - MCP tools list_diagram_seeds + get_diagram_seed (MANIFEST-05 pair)
  affects:
    - Phase 22 Excalidraw skill (stable MCP consumer API)
tech_stack:
  added: []
  patterns:
    - D-02 envelope (text_body + SENTINEL + json meta)
    - D-16 alias threading via closure over alias_map parameter
    - D-11 binary-status invariant: ok vs non-ok with empty text_body
    - SP-8 never-raise: all IO exceptions -> status envelope
    - T-20-03-01 path traversal defense: regex + resolve + is_relative_to
    - T-20-03-02 DoS cap: budget*10 char cap -> status=truncated
    - MANIFEST-05 atomic-pair: registry + serve in one commit
    - MANIFEST-06: explicit capability_tool_meta.yaml entries
key_files:
  created: []
  modified:
    - graphify/mcp_tool_registry.py (lines 348-385: 2 new Tool declarations)
    - graphify/serve.py (4 new functions + 2 handler registrations)
    - graphify/capability_tool_meta.yaml (MANIFEST-06 entries)
    - server.json (manifest_content_hash + tool_count refresh)
    - tests/test_serve.py (12 new tests)
decisions:
  - Cores are module-level (not nested in serve()) to enable unit testing without booting the MCP server — mirrors the _run_get_focus_context_core / _run_query_graph pattern.
  - _SEED_ID_RE = ^[A-Za-z0-9_\-]+$ is the single-source gate for path traversal defense; belt-and-suspenders resolve()+is_relative_to() check runs after regex pass.
  - Cap guard uses budget*10 char ceiling on text_body (not a token estimator) — status becomes "truncated" so agents can detect and request a smaller slice.
  - Alias threading runs BOTH on the seed_id argument and on every node id inside the returned SeedDict body so a downstream agent never sees a non-canonical id in main_nodes/supporting_nodes/relations.
  - Corrupt manifest -> emit stderr warn + no_seeds envelope (not corrupt-at-list-level); individual corrupt seed files at get time -> "corrupt" envelope.
metrics:
  duration_seconds: ~600
  commits: 2
  tasks_completed: 2
  files_modified: 5
  tests_added: 12
  completed: 2026-04-23
---

# Phase 20 Plan 03: MCP Tools for Diagram Seeds — Summary

**One-liner:** Added `list_diagram_seeds` + `get_diagram_seed` as the MANIFEST-05 atomic pair — module-level never-raise cores, closure-local `_resolve_alias` per D-16, path-traversal defense via `_SEED_ID_RE`, budget-capped truncation, 12 unit tests, capability_tool_meta.yaml + server.json refreshed; full suite 1524 passed.

## Function Inventory (serve.py)

| Function | Scope | Line | Role |
|----------|-------|------|------|
| `_run_list_diagram_seeds_core` | module | 2562 | SEED-09 pure core; tab-separated rows + D-02 meta |
| `_run_get_diagram_seed_core`   | module | 2667 | SEED-10 pure core; full SeedDict JSON + D-02 meta |
| `_tool_list_diagram_seeds`     | `serve()` | 3316 | Thin wrapper; `_reload_if_stale()` + alias_map injection |
| `_tool_get_diagram_seed`       | `serve()` | 3323 | Thin wrapper; `_reload_if_stale()` + alias_map injection |

## Registry Entries (mcp_tool_registry.py)

| Tool | Line | Required args | Defaults |
|------|------|---------------|----------|
| `list_diagram_seeds` | 349 | — | `budget=500` |
| `get_diagram_seed`   | 364 | `seed_id` | `budget=2000` |

## Handlers Dict (_handlers in serve())

```python
"list_diagram_seeds": _tool_list_diagram_seeds,  # Phase 20 SEED-09
"get_diagram_seed":   _tool_get_diagram_seed,    # Phase 20 SEED-10
```

MANIFEST-05 startup invariant passes: `{t.name for t in build_mcp_tools()} == set(_handlers.keys())` (24 tools in registry, 24 handlers in serve).

## D-02 Envelope Meta Shapes

### list_diagram_seeds
| Status | Meta keys |
|--------|-----------|
| `ok` | `status, seed_count, budget_used [, resolved_from_alias]` |
| `no_seeds` | `status, seed_count=0, budget_used=0` |

Text body on `ok`: tab-separated rows `seed_id\tmain_node_label\tsuggested_layout_type\ttrigger\tnode_count` (one per non-dropped manifest entry). Empty on `no_seeds`.

### get_diagram_seed
| Status | Meta keys |
|--------|-----------|
| `ok` | `status, seed_id, node_count, budget_used [, resolved_from_alias]` |
| `not_found` | `status, seed_id, budget_used=0 [, resolved_from_alias]` |
| `corrupt` | `status, seed_id, budget_used=0` |
| `truncated` | `status, seed_id, node_count, budget_used [, resolved_from_alias]` |

Text body on `ok`/`truncated`: `json.dumps(seed_dict, indent=2, ensure_ascii=False)` (possibly trimmed to `budget*10` chars). Empty on `not_found`/`corrupt`.

## Test Coverage (12 new tests in tests/test_serve.py)

| Tool | Test | Coverage |
|------|------|----------|
| both | `test_list_diagram_seeds_tool_registered` | Registry membership + `seed_id` required arg (SEED-11) |
| list | `test_list_diagram_seeds_envelope_ok` | Happy path, 2 seeds, 5-field rows (SEED-09) |
| list | `test_list_diagram_seeds_envelope_no_seeds_missing_dir` | Missing seeds/ dir (SEED-09) |
| list | `test_list_diagram_seeds_envelope_no_seeds_empty_manifest` | Empty-list manifest (SEED-09) |
| list | `test_list_diagram_seeds_skips_dropped_by_cap_entries` | `dropped_due_to_cap=True` filtered (SEED-09) |
| list | `test_list_diagram_seeds_resolves_node_id_aliases_in_response` | D-16 seed_id canonicalization in rows |
| list | `test_list_diagram_seeds_corrupt_manifest_resilient` | SP-8 never-raise on corrupt manifest |
| get  | `test_get_diagram_seed_envelope_ok` | Full SeedDict round-trip (SEED-10) |
| get  | `test_get_diagram_seed_not_found` | Missing seed_id (SEED-10) |
| get  | `test_get_diagram_seed_corrupt_file` | Corrupt seed JSON (SP-8) |
| get  | `test_get_diagram_seed_resolves_seed_id_alias` | D-16 alias on seed_id argument |
| get  | `test_get_diagram_seed_rejects_path_traversal` | T-20-03-01 `../../secret` rejected |

`pytest tests/test_serve.py -q -k diagram_seed` -> 12 passed. `pytest tests/ -q` -> 1524 passed (no regressions).

## MANIFEST-05 Atomic-Pair Commit

Single commit `1a924cc` modifies both `graphify/mcp_tool_registry.py` and `graphify/serve.py` (plus `capability_tool_meta.yaml`, `server.json`, and `tests/test_serve.py`). Git log:

```
1a924cc feat(20-03): expose list_diagram_seeds + get_diagram_seed MCP tools (MANIFEST-05)
c2d5f42 test(20-03): add failing tests for list_diagram_seeds + get_diagram_seed MCP tools
```

## TDD Gate Compliance

- RED commit: `c2d5f42` — 12 new tests all failed on import of the undefined cores.
- GREEN commit: `1a924cc` — cores + wrappers + handlers added; all 12 pass; full suite green.
- REFACTOR: not needed.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] capability_tool_meta.yaml missing entries for new tools.**
- **Found during:** Task 1 verification (`pytest tests/test_capability.py::test_all_registered_tools_have_explicit_meta_yaml`).
- **Issue:** MANIFEST-06 enforcement rejected the registry-added tools because `capability_tool_meta.yaml` had no explicit entries (same class of drift the v1.4 audit flagged for `chat` / `get_focus_context`).
- **Fix:** Added explicit entries for both tools (cheap/deterministic/graph_mtime; `get_diagram_seed` declares `composable_from: [list_diagram_seeds]` since agents typically list before fetching).
- **Files modified:** `graphify/capability_tool_meta.yaml`
- **Commit:** `1a924cc` (folded into the MANIFEST-05 atomic pair since it's a mechanical follow-on from registry add).

**2. [Rule 3 - Blocking] server.json capability hash drift.**
- **Found during:** Task 1 verification (`pytest tests/test_capability.py::test_validate_cli_zero`).
- **Issue:** `_meta.manifest_content_hash` in `server.json` was stale after adding two tools (expected `c62f6c0e…`, committed `cd69cf63…`); `tool_count` 22 vs built 24.
- **Fix:** Updated `_meta.manifest_content_hash` to the new hash and `tool_count` from 22 to 24. (Prior regenerate commits `cdbee6e`, `10f671d`, `4da9efb` followed the same pattern.)
- **Files modified:** `server.json`
- **Commit:** `1a924cc`

**3. [Rule 1 - Bug] Test assertion false positive on substring match.**
- **Found during:** Task 1 initial GREEN run — `test_list_diagram_seeds_skips_dropped_by_cap_entries` failed because the assertion `"c" not in text_body.split("\n")[0]` matched the `c` in `architecture`, not the dropped seed id `c`.
- **Fix:** Split each row, extract first column (seed_id), and assert the exact set `{a, b}`.
- **Files modified:** `tests/test_serve.py`
- **Commit:** `1a924cc` (folded — test fix shipped with GREEN implementation).

No architectural deviations (Rule 4).

## Acceptance Criteria Verification

| Check | Result |
|-------|--------|
| `"list_diagram_seeds"` in `mcp_tool_registry.py` | 1 match |
| `"get_diagram_seed"` in `mcp_tool_registry.py` | 2 matches (name + description cross-reference) |
| `def _run_list_diagram_seeds_core\|def _run_get_diagram_seed_core\|def _tool_list_diagram_seeds\|def _tool_get_diagram_seed` | 4 defs |
| MANIFEST-05 startup invariant | Passes (24 registry tools == 24 handler keys) |
| Single commit modifies both registry + serve | `1a924cc` contains both |
| `grep -c "def test_.*diagram_seed" tests/test_serve.py` | 12 |
| `pytest tests/test_serve.py -q -k diagram_seed` | 12 passed |
| `pytest tests/ -q` | 1524 passed, 8 warnings |

## Handoff to Phase 22 (Excalidraw Skill)

The two tools are the stable MCP consumer API. Agents should:

1. Call `list_diagram_seeds` first (cheap, graph_mtime-cacheable) to discover what seeds exist.
2. Pick a seed by `seed_id` + `suggested_layout_type` and call `get_diagram_seed(seed_id)` to fetch the full SeedDict.
3. Render the SeedDict through the template file named in `seed.suggested_template` (e.g. `architecture.excalidraw.md`).
4. D-16 alias redirects are visible in `meta.resolved_from_alias` — canonical ids are used in the body.
5. Path traversal or unknown seed_id -> `status: "not_found"` (never raises, no filesystem leakage).

No further API-shape changes are expected; any Phase 22 extensions should land as **additions** (new tools, not new required args on these two) so the atomic-pair invariant stays clean.

## Self-Check: PASSED

- `graphify/mcp_tool_registry.py` lines 349 + 364 contain new Tool declarations (verified via `grep -n`)
- `graphify/serve.py` lines 2562 + 2667 + 3316 + 3323 contain the four new defs (verified via `grep -n`)
- Commit `c2d5f42` (RED) in git log
- Commit `1a924cc` (GREEN atomic pair) in git log; `git show --stat 1a924cc` lists both `graphify/mcp_tool_registry.py` and `graphify/serve.py`
- `.planning/phases/20-diagram-seed-engine/20-03-SUMMARY.md` written
- Full test suite: 1524 passed (41s)
