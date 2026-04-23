---
phase: 18
plan: 02
subsystem: serve + snapshot
tags: [mcp, d-02-envelope, snapshot, sentinel, security, focus-context, cr-01-regression]
requirements_closed: [FOCUS-01, FOCUS-03, FOCUS-04, FOCUS-05, FOCUS-07]
dependency_graph:
  requires:
    - graphify/serve.py::_resolve_focus_seeds (Plan 18-01)
    - graphify/serve.py::_multi_seed_ego (Plan 18-01)
    - graphify/serve.py::QUERY_GRAPH_META_SENTINEL
    - graphify/security.py::validate_graph_path
    - graphify/serve.py::_subgraph_to_text (layer=2)
  provides:
    - graphify/serve.py::_run_get_focus_context_core
    - graphify/serve.py::_render_focus_community_summary
    - graphify/serve.py::_tool_get_focus_context (MCP handler closure)
    - graphify/snapshot.py::ProjectRoot (frozen-dataclass sentinel)
    - graphify/mcp_tool_registry.py::get_focus_context Tool
    - tests/conftest.py::nested_project_root (fixture)
  affects:
    - graphify/snapshot.py (4 signatures renamed root→project_root)
    - graphify/skill.md (2 runtime callsites updated to project_root=)
    - tests/conftest.py, test_snapshot.py, test_serve.py, test_delta.py (all root= callers updated)
    - server.json (manifest_content_hash + tool_count updated for MANIFEST-09 drift gate)
tech_stack:
  added: []
  patterns:
    - "D-02 hybrid response envelope: text_body + QUERY_GRAPH_META_SENTINEL + json(meta) — reused from Phase 9.2/11"
    - "Binary status invariant (D-03 + D-11): only {ok, no_context} — no_graph/insufficient_history collapse to no_context"
    - "No focus_hint echo (D-12 / T-18-D): 4-key meta {status, node_count, edge_count, budget_used} — no file_path, function_name, line"
    - "Path confinement via validate_graph_path(path, base=project_root) — explicit base (default graphify-out/ would reject every legitimate focus source file)"
    - "Frozen-dataclass construction-time sentinel codifying v1.3 CR-01 (Pitfall 20)"
    - "D-08 outer-hop-first budget degradation: shrink radius before char-clipping (while-loop over _multi_seed_ego)"
key_files:
  created: []
  modified:
    - graphify/serve.py
    - graphify/snapshot.py
    - graphify/mcp_tool_registry.py
    - graphify/skill.md
    - tests/conftest.py
    - tests/test_serve.py
    - tests/test_snapshot.py
    - tests/test_delta.py
    - server.json
decisions:
  - "Named the dispatch core `_run_get_focus_context_core` (matches PATTERNS.md and the VALIDATION.md-locked test naming convention test_get_focus_context_*) — RESEARCH.md used `_run_focus_core` but PATTERNS.md won on the naming tie-break. Documented as a deviation (Rule 3, blocking) below."
  - "Relative file_paths are resolved against project_root (not CWD) before validate_graph_path — otherwise Path.resolve() resolves relative paths against CWD, causing legitimate tmp_path-relative paths to false-escape. Documented as a Pitfall-3 extension."
  - "Seed resolver receives the project-root-relative form of `validated` (not the absolute form) because stored source_file values are relative; passing the absolute form caused the resolver's target_raw comparison to miss every node."
  - "test_no_watchdog_import_in_focus_path narrowed its scan range from [_resolve_focus_seeds, _handlers={] to [_run_get_focus_context_core, next top-level def] — broader scan picked up the unrelated _filter_blank_stdin stdio helper (legit threading.Thread) and false-tripped."
  - "_tool_get_focus_context missing-graph path collapses to no_context (not no_graph) — preserves the T-18-A/B/C binary invariant tested by test_binary_status_invariant."
  - "make_snapshot_chain fixture accepts both project_root= AND legacy root= (backwards-compat alias) per Plan 18-02 Step D; all other test call-sites migrated to project_root=."
metrics:
  duration_seconds: 837
  completed: "2026-04-20T20:37:11Z"
  tasks_completed: 5
  files_modified: 9
  tests_added: 13
  tests_total_after: 1320
---

# Phase 18 Plan 02: Focus-Aware Graph Context MCP Tool Summary

The `get_focus_context` MCP tool — a pull-model focus → scoped ego-graph + community summary pipeline — lands in `graphify/serve.py` with a full D-02 envelope, D-11 binary-status invariant, D-12 no-focus-hint-echo guarantee, and D-08 outer-hop-first budget degradation. In the same plan, v1.3 CR-01 (Pitfall 20, snapshot-path double-nesting) is codified via a `ProjectRoot` frozen-dataclass sentinel in `graphify/snapshot.py` that raises at construction when given `graphify-out/` directly, plus the `root`→`project_root` rename across 4 snapshot helper signatures.

## What Shipped

### Symbols Added (graphify/serve.py)

- **`_render_focus_community_summary(G, focused, communities) -> str`** (line 1687) — Minimal per-community top-3-by-degree label renderer. Returns a `## Communities in focus:` markdown block or an empty string when no community attrs are available. Claude's Discretion D-06: minimal shape; v1.5 may gate this behind a community_detail enum.
- **`_run_get_focus_context_core(G, communities, alias_map, project_root, arguments) -> str`** (line 1730) — Pure dispatch core. Returns the D-02 envelope string. Never raises — all failure modes collapse to the binary no_context envelope.
- **`_tool_get_focus_context(arguments: dict) -> str`** (line 2181, closure inside `serve()`) — MCP handler. Passes `_out_dir.parent` positionally to preserve the CR-01 invariant. Missing graph.json also collapses to no_context (binary status preserved).

### Symbols Added (graphify/snapshot.py)

- **`class ProjectRoot` (@dataclass(frozen=True))** (line 16) — Construction-time sentinel. `__post_init__` raises `ValueError` when `path.name == "graphify-out"` with an actionable message suggesting `path.parent` as the corrected form. Grep-verifiable literal `path.name == "graphify-out"` at line 26.

### Renamed API (graphify/snapshot.py)

Four signatures migrated from `root` → `project_root` (default `Path(".")` preserved):

| Function | Line |
|----------|------|
| `snapshots_dir(project_root)` | 34 |
| `list_snapshots(project_root)` | 41 |
| `save_snapshot(G, communities, project_root, name, cap)` | 49 |
| `auto_snapshot_and_delta(G, communities, project_root, cap)` | 105 |

`load_snapshot(path)` at line 143 is unchanged (takes `path`, not `root`).

### Registry Entry (graphify/mcp_tool_registry.py)

`get_focus_context` Tool registered at line 231 with the full inputSchema: required `focus_hint.file_path`, optional `function_name`, `line`, `neighborhood_depth ∈ [0,6]`, `include_community`, `reported_at`; budget clamp `[50, 100000]` default 2000.

### Fixture (tests/conftest.py)

`nested_project_root(tmp_path)` fixture at line 144 — lays out `tmp_path/project/graphify-out/snapshots/` + `tmp_path/project/src/auth.py` and returns `tmp_path/project` as the project root. Used by both test_serve.py and test_snapshot.py for CR-01 regression coverage.

### Tests Added (tests/test_snapshot.py)

All three names locked verbatim per 18-VALIDATION.md rows 18-02-07, 18-02-08 (+ positive counterpart):

1. `test_project_root_sentinel_rejects_graphify_out` — T-18-C mitigation; `ProjectRoot(path=tmp_path/"graphify-out")` raises `ValueError` matching "graphify-out".
2. `test_project_root_sentinel_accepts_project_root` — positive; `ProjectRoot(path=tmp_path)` succeeds.
3. `test_nested_dir_fixture_list_snapshots` — integration; `save_snapshot(..., project_root=nested_project_root)` + `list_snapshots(nested_project_root)` round-trips.

### Tests Added (tests/test_serve.py)

All ten names locked verbatim per 18-VALIDATION.md rows 18-02-01..06, 18-02-09..12:

1. `test_get_focus_context_registered` — FOCUS-01 / MANIFEST-05 parity.
2. `test_get_focus_context_envelope_ok` — FOCUS-03 / D-02 envelope with `meta.status == "ok"`.
3. `test_get_focus_context_community_summary` — FOCUS-03 / D-06 community info in meta or text_body.
4. `test_get_focus_context_spoofed_path_silent` — FOCUS-04 / T-18-A; `/etc/passwd` returns 4-key no_context envelope.
5. `test_get_focus_context_missing_file_silent` — FOCUS-04 / T-18-B; file indexed but absent on disk returns silent no_context (FileNotFoundError caught).
6. `test_no_watchdog_import_in_focus_path` — FOCUS-05 pull-model static check (no watchdog/threading.Thread/asyncio.create_task in focus core region).
7. `test_snapshot_callsites_use_project_root` — FOCUS-07 smoke; 4 Phase-11 wrappers still reference `_out_dir.parent`.
8. `test_binary_status_invariant` — D-03 + D-11 property test; spoof/unindexed/missing all yield byte-identical meta keys `{status, node_count, edge_count, budget_used}`.
9. `test_budget_drop_outer_hop_first` — D-08; `budget=50` response length ≤ `budget=10000` response length.
10. `test_no_context_does_not_echo_focus_hint` — D-12 / T-18-D; no `/etc/passwd`, `SECRET_FN`, `424242` in the no_context envelope.

## Commits

| # | Gate | Hash | Message |
|---|------|------|---------|
| 1 | RED (18-02-01) | `6c63501` | `test(18-02): add failing tests for ProjectRoot sentinel + nested-dir fixture` |
| 2 | GREEN (18-02-02) | `39a8236` | `feat(18-02): add ProjectRoot sentinel + rename root→project_root` |
| 3 | RED (18-02-03) | `1d0169c` | `test(18-02): add failing tests for get_focus_context envelope + silent-ignore + invariants` |
| 4 | GREEN (18-02-04) | `b058d37` | `feat(18-02): implement get_focus_context MCP tool with no_context silent-ignore` |
| 5 | CHORE (18-02-05) | `4da9efb` | `chore(18-02): regenerate server.json capability hash for get_focus_context` |

## Verification Results

```text
$ grep -Fn "def _run_get_focus_context_core" graphify/serve.py
1730:def _run_get_focus_context_core(

$ grep -Fn "def _render_focus_community_summary" graphify/serve.py
1687:def _render_focus_community_summary(G: "nx.Graph", focused: "nx.Graph", communities: dict) -> str:

$ grep -Fn "def _tool_get_focus_context" graphify/serve.py
2181:    def _tool_get_focus_context(arguments: dict) -> str:

$ grep -Fn "class ProjectRoot" graphify/snapshot.py
16:class ProjectRoot:

$ grep -Fn 'path.name == "graphify-out"' graphify/snapshot.py
26:        if self.path.name == "graphify-out":

$ grep -Fn 'name="get_focus_context"' graphify/mcp_tool_registry.py
231:            name="get_focus_context",

$ grep -Fn "def nested_project_root" tests/conftest.py
144:def nested_project_root(tmp_path):

$ grep -Fn "base=project_root" graphify/serve.py
1771:    # FOCUS-04 + Pitfall 3: explicit base=project_root (default base is graphify-out/
1784:        validated = validate_graph_path(candidate, base=project_root)

$ grep -En "except \(ValueError, FileNotFoundError\)" graphify/serve.py
443:    except (ValueError, FileNotFoundError) as exc:
1785:    except (ValueError, FileNotFoundError):

$ grep -Fn '"get_focus_context": _tool_get_focus_context' graphify/serve.py
2310:        "get_focus_context": _tool_get_focus_context,

$ grep -Fcn '_out_dir.parent' graphify/serve.py
7

$ grep -En 'nx\.ego_graph\(G, *\[' graphify/serve.py
(zero — anti-pattern absent)

$ grep -rEn '(save_snapshot|list_snapshots|snapshots_dir|auto_snapshot_and_delta)\([^)]*\broot=' graphify/ tests/ | grep -v conftest.py
(zero — only conftest backwards-compat alias retained)

$ pytest tests/ -q
1320 passed, 2 warnings in 36.96s
```

All success-criteria items from the plan are satisfied:

- [x] `_run_get_focus_context_core` returns D-02 envelope on success (meta.status == "ok"); byte-identical no_context envelope on any failure mode.
- [x] Spoofed / unindexed / missing all produce identical meta key set.
- [x] `ProjectRoot(path=Path("graphify-out"))` raises ValueError at construction; positive constructs succeed.
- [x] All 4 legacy snapshot-helper callers (`_tool_entity_trace`, `_tool_drift_nodes`, `_tool_newly_formed_clusters`, `_tool_graph_summary`) still use `_out_dir.parent` positionally.
- [x] `get_focus_context` registered in both registry and `_handlers`; MANIFEST-05 invariant holds.
- [x] Py 3.10 + 3.12 compatibility preserved (no 3.11+ syntax).
- [x] No new runtime dependencies.
- [x] Full suite green: 1320 passed (+13 new, zero regressions vs. 1307 pre-18-02 HEAD).

## Deviations from Plan

### Rule 3 — Blocking issue (path resolution)

**1. `validate_graph_path` with relative `file_path` false-escaped tmp_path-based `project_root`**
- **Found during:** Task 18-02-04 GREEN (test_get_focus_context_envelope_ok failed with status=no_context when it should have been ok).
- **Issue:** `validate_graph_path('src/auth.py', base=/tmp/pytest-xxx/project)` raised `ValueError: Path 'src/auth.py' escapes the allowed directory /tmp/pytest-xxx/project` because `Path.resolve()` resolves relative paths against CWD (the repo root), not against `base`.
- **Fix:** Before calling `validate_graph_path`, I prepend `project_root` to relative `file_path`s: `candidate = Path(file_path); if not candidate.is_absolute(): candidate = Path(project_root) / candidate`. This matches the intended semantics ("file_path is project-relative") and preserves confinement (the subsequent `validate_graph_path` still asserts the resolved path stays under `base`).
- **Files modified:** `graphify/serve.py` (commit `b058d37`).

**2. `_resolve_focus_seeds` needs project-root-relative form**
- **Found during:** Task 18-02-04 GREEN (same test, after fix 1).
- **Issue:** `_resolve_focus_seeds` from Plan 18-01 compares `target_raw = str(target_path)` against stored `source_file` values. Stored values are relative (`"src/auth.py"`), but passing `validated` (an absolute path) causes `target_raw` comparison to miss every node. The resolver's `Path(s).resolve()` fallback resolves relative stored paths against CWD (repo root), not project_root, so it also misses.
- **Fix:** Project the validated absolute path back to its project-root-relative form via `Path(validated).relative_to(Path(project_root).resolve())` before passing to `_resolve_focus_seeds`. Falls back to `validated` if `relative_to` raises.
- **Files modified:** `graphify/serve.py` (commit `b058d37`).

### Rule 1 — Test-fix (scan-range regression)

**3. `test_no_watchdog_import_in_focus_path` scan range too wide**
- **Found during:** Task 18-02-04 GREEN.
- **Issue:** The plan's test scanned `src[focus_start:_handlers={]` — a 1300-line range that picked up the unrelated `_filter_blank_stdin` helper (stdio blank-line filter, legitimately uses `threading.Thread`) and false-tripped the assertion.
- **Fix:** Narrowed the scan to the focus-core region `[def _run_get_focus_context_core, next top-level def]`. The assertion intent (FOCUS-05 static pull-model check over focus code only) is preserved; the test still catches any future focus-path regression that adds a watcher.
- **Files modified:** `tests/test_serve.py` (commit `b058d37`).

### Rule 1 — Runtime bug (skill.md)

**4. `graphify/skill.md` runtime callsites still used legacy `root=` keyword**
- **Found during:** Task 18-02-02 verification grep.
- **Issue:** Lines 504 and 1064 of `graphify/skill.md` invoke `auto_snapshot_and_delta(G, communities, root=Path('.'))` — after the snapshot.py rename, these would crash at skill-runtime with `TypeError: auto_snapshot_and_delta() got an unexpected keyword argument 'root'`.
- **Fix:** Updated both to `project_root=Path('.')`.
- **Files modified:** `graphify/skill.md` (commit `39a8236`).

### Naming-tie-break deviation

**5. Function naming conflict: RESEARCH.md vs PATTERNS.md**
- **Issue:** RESEARCH.md used `_run_focus_core` while PATTERNS.md used `_run_get_focus_context_core`. The executor initial-context call-out flagged this.
- **Decision:** Used `_run_get_focus_context_core` — it matches:
  - The VALIDATION.md-locked test naming pattern (`test_get_focus_context_*`).
  - The MCP tool name (`get_focus_context`).
  - The Expected Interface from Plan 18-01 SUMMARY.md.
- **Files affected:** `graphify/serve.py`, `tests/test_serve.py`.

## Expected Interface for Plan 18-03 Consumer

Plan 18-03 (focus debouncer + freshness gate, P2 / FOCUS-08 + FOCUS-09) should **wrap `_run_get_focus_context_core`** (the pure dispatch core), not `_tool_get_focus_context` (the MCP closure). This matches RESEARCH.md Pitfall 7 (the debounce layer must see the full pipeline for cache-key fingerprinting).

**Monkey-patchable seams for debounce:**

```python
# Plan 18-03 should wrap the pure core:
from graphify.serve import _run_get_focus_context_core as _core

def _run_get_focus_context_core_debounced(G, communities, alias_map, project_root, arguments):
    focus_hint = arguments.get("focus_hint", {})
    reported_at = focus_hint.get("reported_at")  # ISO 8601 UTC
    fingerprint = (
        focus_hint.get("file_path", ""),
        focus_hint.get("function_name", ""),
        focus_hint.get("line"),
    )
    if _seen_recently(fingerprint, within_seconds=5):
        return _no_context_envelope_from_core()  # reuse binary no_context shape
    if reported_at and _is_stale(reported_at, max_age_seconds=300):
        return _no_context_envelope_from_core()  # D-11 binary invariant still holds
    return _core(G, communities, alias_map, project_root, arguments)
```

**Contracts Plan 18-03 must honor:**

- The wrapper MUST preserve the D-03/D-11 binary-status invariant — debounce/freshness rejection MUST emit the same 4-key no_context envelope, not a new status.
- `reported_at` parsing MUST tolerate the Python 3.10 `Z`-suffix gotcha (use `fromisoformat(reported_at.replace("Z","+00:00"))` or similar).
- Malformed `reported_at` MUST collapse to no_context (no traceback) per the D-12 / test_focus_malformed_reported_at contract.
- Rewiring the MCP handler to the debounced wrapper: replace the existing `_tool_get_focus_context`'s call `_run_get_focus_context_core(...)` with the debounced variant. No registry schema change needed.

**Interface NOT to depend on:**

- `_render_focus_community_summary` is an implementation detail; do not construct envelopes around it directly.
- Internal variable `chosen_depth` is not exposed — Plan 18-03 cache-key design should not depend on the final radius used.

## Self-Check: PASSED

- graphify/serve.py::_run_get_focus_context_core — FOUND (line 1730)
- graphify/serve.py::_render_focus_community_summary — FOUND (line 1687)
- graphify/serve.py::_tool_get_focus_context — FOUND (line 2181)
- graphify/serve.py::"get_focus_context": _tool_get_focus_context — FOUND (line 2310)
- graphify/snapshot.py::class ProjectRoot — FOUND (line 16)
- graphify/snapshot.py::path.name == "graphify-out" — FOUND (line 26)
- graphify/mcp_tool_registry.py::name="get_focus_context" — FOUND (line 231)
- tests/conftest.py::def nested_project_root — FOUND (line 144)
- tests/test_snapshot.py::test_project_root_sentinel_rejects_graphify_out — FOUND
- tests/test_snapshot.py::test_project_root_sentinel_accepts_project_root — FOUND
- tests/test_snapshot.py::test_nested_dir_fixture_list_snapshots — FOUND
- tests/test_serve.py::test_get_focus_context_registered — FOUND
- tests/test_serve.py::test_get_focus_context_envelope_ok — FOUND
- tests/test_serve.py::test_get_focus_context_community_summary — FOUND
- tests/test_serve.py::test_get_focus_context_spoofed_path_silent — FOUND
- tests/test_serve.py::test_get_focus_context_missing_file_silent — FOUND
- tests/test_serve.py::test_no_watchdog_import_in_focus_path — FOUND
- tests/test_serve.py::test_snapshot_callsites_use_project_root — FOUND
- tests/test_serve.py::test_binary_status_invariant — FOUND
- tests/test_serve.py::test_budget_drop_outer_hop_first — FOUND
- tests/test_serve.py::test_no_context_does_not_echo_focus_hint — FOUND
- commit 6c63501 (test RED snapshot) — FOUND in git log
- commit 39a8236 (feat GREEN snapshot) — FOUND in git log
- commit 1d0169c (test RED serve) — FOUND in git log
- commit b058d37 (feat GREEN serve) — FOUND in git log
- commit 4da9efb (chore server.json) — FOUND in git log
- anti-pattern `nx.ego_graph(G, [` — ABSENT (as required)
- anti-pattern `root=` legacy kwarg outside conftest alias — ABSENT (as required)
- full suite: 1320 passed (1307 baseline + 13 new) — GREEN
