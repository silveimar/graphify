---
phase: 18-focus-aware-graph-context
reviewed: 2026-04-20T19:58:00Z
depth: standard
files_reviewed: 9
files_reviewed_list:
  - graphify/mcp_tool_registry.py
  - graphify/serve.py
  - graphify/skill.md
  - graphify/snapshot.py
  - server.json
  - tests/conftest.py
  - tests/test_delta.py
  - tests/test_serve.py
  - tests/test_snapshot.py
findings:
  critical: 0
  warning: 4
  info: 5
  total: 9
status: issues_found
---

# Phase 18: Code Review Report

**Reviewed:** 2026-04-20T19:58:00Z
**Depth:** standard
**Files Reviewed:** 9
**Status:** issues_found

## Summary

Phase 18 "Focus-Aware Graph Context" ships the `get_focus_context` MCP tool, the `ProjectRoot` snapshot sentinel, and the P2 debounce + freshness guards across three plans. Full test suite (213 tests) passes cleanly.

The seven invariants flagged in the phase context all check out:

1. Binary status invariant (D-03/D-11) — `_run_get_focus_context_core` and `_tool_get_focus_context` both emit the 4-key `{status, node_count, edge_count, budget_used}` shape on every no-context path, with empty `text_body`. No `focus_hint` values echo in error responses (confirmed by `test_no_context_does_not_echo_focus_hint`).
2. Path-confinement — `validate_graph_path(candidate, base=project_root)` is called with the explicit `base=` override, and both `ValueError` and `FileNotFoundError` are caught.
3. NetworkX 3.x — `_multi_seed_ego` correctly uses `nx.compose_all([ego_graph(G, s, r) for s in seeds])`. No `nx.ego_graph(G, [...])` multi-seed pattern exists.
4. Py 3.10 compat — `datetime.fromisoformat(reported_at.replace("Z", "+00:00"))` shim is present and tested.
5. Debounce cache — uses `time.monotonic()`, has bounded growth (evicts oldest 64 when size exceeds 256).
6. Snapshot sentinel — `ProjectRoot.__post_init__` raises on `path.name == "graphify-out"` as designed.
7. Envelope parity under debounce — the cached envelope is byte-identical to the core's output (no "cached: true" marker).

Four Warning-level issues surface around test-assertion tightness, a dead parameter, the ProjectRoot sentinel not being wired into the production call sites it was meant to guard, and test-quality gaps in the debounce assertions. Five Info items cover stylistic and minor hygiene observations. No Critical issues.

## Warnings

### WR-01: `ProjectRoot` sentinel defined but not wired into protected call sites

**File:** `graphify/snapshot.py:15-31`
**Issue:** `ProjectRoot` is a frozen dataclass that raises on `path.name == "graphify-out"` — this is the codified guard against v1.3 CR-01 (Pitfall 20). However, it is never actually used to protect `snapshots_dir`, `save_snapshot`, `list_snapshots`, or `auto_snapshot_and_delta`. Those functions all take `project_root: Path` (not `project_root: ProjectRoot`). In-tree production callers (`serve.py` passes `_out_dir.parent`, `skill.md` passes `Path('.')`) bypass the sentinel entirely; only the two unit tests construct `ProjectRoot(...)`. The regression the sentinel was designed to prevent remains reachable if a future maintainer passes `_out_dir` directly to `save_snapshot`. The sentinel currently documents intent but does not enforce it.
**Fix:** Either (a) add a runtime guard inside `snapshots_dir` / `save_snapshot` / `list_snapshots` that rejects `Path` arguments whose `.name == "graphify-out"`, or (b) change the parameter type to accept either `Path | ProjectRoot`, unwrap `ProjectRoot.path` internally, and reject raw `Path(...) / "graphify-out"` at the boundary. Option (a) is smaller:
```python
def snapshots_dir(project_root: Path = Path(".")) -> Path:
    p = Path(project_root)
    if p.name == "graphify-out":
        raise ValueError(
            f"snapshots_dir received {p!r}; pass the directory CONTAINING "
            f"graphify-out/, not graphify-out/ itself. Try: {p.parent!r}"
        )
    d = p / "graphify-out" / "snapshots"
    d.mkdir(parents=True, exist_ok=True)
    return d
```

### WR-02: Unused `alias_map` parameter in `_run_get_focus_context_core`

**File:** `graphify/serve.py:1731-1735`
**Issue:** `_run_get_focus_context_core(G, communities, alias_map, project_root, arguments)` declares `alias_map: dict` but the function body never references it (confirmed via grep: 0 occurrences inside the function body). The caller `_tool_get_focus_context` still passes `_alias_map` positionally. This is dead API surface that invites future misuse — a reader will reasonably assume alias resolution is happening.
**Fix:** Either remove the parameter (and update the caller):
```python
def _run_get_focus_context_core(
    G: "nx.Graph",
    communities: dict,
    project_root: "Path",
    arguments: dict,
) -> str:
    ...
```
…or wire alias resolution into `_resolve_focus_seeds` (so `function_name` and `file_path` can be alias-translated the same way `_run_entity_trace` uses `_alias_map`). Given the phase scope is "pull-model per-call focus," removing the parameter is the simpler path; add an alias-map TODO if future resolution is desired.

### WR-03: `test_focus_debounce_suppresses_duplicate` does not exercise the production dispatcher

**File:** `tests/test_serve.py:2459-2488`
**Issue:** The test name claims it verifies that "second call within 500ms returns the cached envelope," but the test body seeds `_FOCUS_DEBOUNCE_CACHE` manually via `_FOCUS_DEBOUNCE_CACHE[key] = (time_mod.monotonic(), first)` and then merely reads it back with `_FOCUS_DEBOUNCE_CACHE.get(key)` — it does NOT invoke `_tool_get_focus_context` at all. The `monkeypatch.setattr(serve_mod, "_run_get_focus_context_core", _blow_up)` setup is unreachable — the test never calls any function that could route through the mock. The claim `"core should not be called when cache hit within window"` is not actually verified: you could delete the entire `_tool_get_focus_context` body and this test would still pass. The assertion `envelope == first` only verifies dict lookup round-trips, not the debounce wrapper's behavior.
**Fix:** Exercise the actual dispatcher path. Since `_tool_get_focus_context` is a closure inside `serve()`, extract the debounce logic to a module-level helper or refactor the test to stand up the full `serve()` closure. A focused alternative:
```python
def test_focus_debounce_suppresses_duplicate(tmp_path, monkeypatch):
    _FOCUS_DEBOUNCE_CACHE.clear()
    key = _focus_debounce_key({"file_path": "src/auth.py"})
    # Seed cache + assert the get-path returns within the window
    _FOCUS_DEBOUNCE_CACHE[key] = (time.monotonic(), "CACHED_ENV")
    assert _focus_debounce_get(key) == "CACHED_ENV"
    # Simulate window expiry by rewriting the stored monotonic timestamp
    _FOCUS_DEBOUNCE_CACHE[key] = (time.monotonic() - 1.0, "CACHED_ENV")
    assert _focus_debounce_get(key) is None
    _FOCUS_DEBOUNCE_CACHE.clear()
```
…and ADD a separate integration test that stands up `serve()` and calls `_tool_get_focus_context` twice in quick succession to verify the wrapper path. The current test overlaps `test_focus_debounce_expires` (both verify the get helper) and leaves the wrapper logic uncovered.

### WR-04: `test_budget_drop_outer_hop_first` assertions are too weak to validate D-08

**File:** `tests/test_serve.py:2391-2405`
**Issue:** The test docstring claims it verifies "D-08: when ego-graph + community summary > budget*3 chars, drop outer hop first." But the actual assertions are:
1. `len(small_parts[0]) <= len(large_parts[0])` — only proves text is shorter with smaller budget, not that the outer hop was dropped first.
2. `small_meta["status"] in ("ok", "no_context")` — tautological; those are the only two possible statuses.

There is no assertion that `small_meta["depth_used"] < large_meta["depth_used"]` (the actual D-08 signature). A char-clip-only truncation (no hop reduction) would pass this test. The 4-node synthetic graph `_make_focus_graph()` may not even be large enough to force hop reduction at the radius=2 default, so `depth_used` might equal `2` for both the small-budget and large-budget cases — making a stronger assertion non-trivial without a bigger fixture.
**Fix:** Either strengthen the assertion with a larger graph:
```python
# Build a wider graph so radius=2 ego-graph overflows a tiny budget
G = _make_wide_focus_graph(n_nodes=50)  # new fixture with many hop-2 reachable nodes
...
small_meta = json.loads(small.split(QUERY_GRAPH_META_SENTINEL)[1])
large_meta = json.loads(large.split(QUERY_GRAPH_META_SENTINEL)[1])
if small_meta["status"] == "ok":
    assert small_meta["depth_used"] <= large_meta["depth_used"], \
        f"D-08 expected depth reduction: small={small_meta!r} large={large_meta!r}"
```
…or rename/re-scope the test to `test_budget_reduces_text_body_size` and accept it as a weaker regression net, with a separate D-08-specific test covering the hop-reduction path on a purpose-built fixture.

## Info

### IN-01: `function_name` narrowing uses substring match (`in`) without word-boundary

**File:** `graphify/serve.py:815-816`
**Issue:** `if function_name and function_name not in label: continue` — `function_name="a"` matches every label containing letter "a". Per D-02 this is accepted (narrowing is a courtesy, not strict filter), and the phase docstring describes this as "narrows the union," so behavior is intentional. But it may surprise callers who pass short function names.
**Fix:** Consider documenting the substring-match behavior in the tool's `inputSchema` description, or use `==` for exact match when `function_name` is short (<4 chars). Minor — current behavior matches D-02 spec.

### IN-02: Private helper `_iter_sources` imported across modules

**File:** `graphify/serve.py:17`
**Issue:** `from graphify.analyze import _iter_sources` — the leading underscore marks it as module-private per Python convention. Cross-module consumption of a `_private` helper couples `serve.py` to `analyze.py`'s internals and signals the symbol should be lifted to a shared non-private location. Phase 10 noted the same pattern elsewhere.
**Fix:** Promote `_iter_sources` to `graphify/validate.py` or a new `graphify/node_helpers.py` as a non-underscore public helper (`iter_sources`), and update the three current call sites (`analyze.py`, `dedup.py`, `serve.py`). Low-risk rename; defer to v1.5 if phase budget is tight.

### IN-03: Commented-out-looking trailing `f""` truncation marker

**File:** `graphify/serve.py:1823`
**Issue:** `text_body = text_body[:char_budget] + f"\n... (truncated to ~{budget} token budget)"` — the marker hints text was clipped but is emitted as part of the `text_body` the agent reads, not as meta. An LLM agent may interpret the literal "truncated to ~N token budget" as a fact about its own context window. Minor but noteworthy.
**Fix:** Move truncation signaling into `meta`:
```python
was_truncated = len(text_body) > char_budget
if was_truncated:
    text_body = text_body[:char_budget]
...
if was_truncated:
    meta["truncated"] = True
```
…and drop the inline marker. Consistent with the D-02 "structured meta" philosophy.

### IN-04: `datetime.now(timezone.utc)` called twice in `save_snapshot`

**File:** `graphify/snapshot.py:62,81`
**Issue:** `save_snapshot` calls `datetime.now(timezone.utc)` once to build the filename stem (line 62) and again to populate `metadata.timestamp` (line 81). The two timestamps can differ by milliseconds to seconds (especially on slow systems). Callers who try to correlate filename to payload.metadata.timestamp may be surprised. Pre-existing behavior; not introduced in Phase 18, but Phase 18 touched this file.
**Fix:** Capture once:
```python
now = datetime.now(timezone.utc)
ts = now.strftime("%Y-%m-%dT%H-%M-%S")
...
"metadata": {
    "timestamp": now.isoformat(),
    ...
}
```
Low priority (pre-existing); note for future snapshot hardening.

### IN-05: `tests/conftest.py` `make_snapshot_chain` backward-compat kwarg pattern

**File:** `tests/conftest.py:106-110`
**Issue:** The fixture accepts both `project_root=` (new) and `root=` (legacy) kwargs and coalesces them:
```python
def _make(n: int = 3, project_root: "Path | None" = None, root: "Path | None" = None) -> "list[Path]":
    effective = project_root if project_root is not None else root
    base = Path(effective) if effective is not None else tmp_path
```
This is a reasonable transition pattern, but it hides the kwarg rename from future readers. A grep for `root=` in tests now yields both legitimate callers (that should migrate) and the shim arm of this fixture. Recommend adding a deprecation docstring or migrating all `root=` callers (visible by grep) and removing the shim after the phase closes.
**Fix:** Either add an explicit `DeprecationWarning` when `root=` is passed, or grep for remaining `root=` callers in the test suite and migrate them:
```bash
grep -rn 'make_snapshot_chain.*root=' tests/
```
Then drop the backward-compat arm. Defer to the Phase 18 cleanup commit or follow-up housekeeping.

---

_Reviewed: 2026-04-20T19:58:00Z_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
