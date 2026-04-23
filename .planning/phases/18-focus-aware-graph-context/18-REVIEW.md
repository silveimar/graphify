---
phase: 18-focus-aware-graph-context
reviewed: 2026-04-20T20:48:00Z
depth: standard
files_reviewed: 8
files_reviewed_list:
  - graphify/mcp_tool_registry.py
  - graphify/serve.py
  - graphify/snapshot.py
  - server.json
  - tests/conftest.py
  - tests/test_delta.py
  - tests/test_serve.py
  - tests/test_snapshot.py
findings:
  critical: 0
  warning: 0
  info: 3
  total: 3
status: issues_found
---

# Phase 18: Code Review Report (Post-Gap-Closure)

**Reviewed:** 2026-04-20T20:48:00Z
**Depth:** standard
**Files Reviewed:** 8
**Status:** issues_found (all Info / non-blocking)

## Summary

This is a post-gap-closure re-review of Phase 18 (Focus-Aware Graph Context) after Plan 18-04 wired the `CR-01` sentinel guard into four snapshot helpers, removed the dead `alias_map` parameter from `_run_get_focus_context_core`, and strengthened two tests (`test_focus_debounce_suppresses_duplicate` and `test_budget_drop_outer_hop_first`).

**All prior findings (WR-01/02/03/04 from the pre-gap-closure review) are correctly addressed:**

- **WR-01 (SC4 structural sentinel wiring):** The `CR-01`/Pitfall-20 guard is now replicated as an inline `raise ValueError` at the top of `snapshots_dir()`, `list_snapshots()`, `save_snapshot()`, and `auto_snapshot_and_delta()` in `graphify/snapshot.py` (lines 36, 50, 75, 137). Four new regression tests in `tests/test_snapshot.py:2383-2419` pin each production callsite.
- **WR-02 (dead `alias_map` parameter):** Fully removed from `_run_get_focus_context_core` (`graphify/serve.py:1731-1751`). The function now takes `(G, communities, project_root, arguments)` — no `alias_map`. The only callsite `_tool_get_focus_context` (`serve.py:2285`) mirrors the new signature. Zero lingering `alias` references exist in the 120-line function body.
- **WR-03 (`test_focus_debounce_suppresses_duplicate` strengthening):** The test now monkeypatches `serve_mod._run_get_focus_context_core` with a counting wrapper and asserts `call_counter["n"] == 1` both after the first call and after the cache-get, proving the core is not re-invoked on cache hit. This correctly exercises the dispatcher path (`tests/test_serve.py:2504-2545`).
- **WR-04 (`test_budget_drop_outer_hop_first` rewrite):** The test now asserts D-08 strict-depth invariants — `small.node_count < large.node_count`, `small.depth_used < large.depth_used`, and (when `depth_used >= 1`) `small.node_count >= 4` (seed + 3 inner neighbors). Uses a purpose-built 10-node two-hop fixture (`_make_large_focus_graph`). The earlier inner-hop logic error (observation 1640) is resolved by tuning the fixture and pinning invariants instead of magic numbers (`tests/test_serve.py:2446-2485`).

**Source-file review:**

- `graphify/snapshot.py` — 4 new guards land cleanly; no regressions to the `ProjectRoot` dataclass. Minor message-format inconsistency noted (IN-01).
- `graphify/serve.py` — `_run_get_focus_context_core` signature is tight, the `_tool_get_focus_context` callsite is clean, and the debounce + freshness helpers are correctly placed. One minor DoS-cap eviction nit noted (IN-02).
- `tests/test_snapshot.py` — Four new callsite-guard tests (one per helper) follow the existing pattern (`tmp_path / "graphify-out"` + `pytest.raises(ValueError, match="graphify-out")`). Solid.
- `tests/test_serve.py` — WR-03 and WR-04 rewrites are well-commented and exercise the intended invariants. One small style nit noted (IN-03).
- `graphify/mcp_tool_registry.py`, `server.json`, `tests/conftest.py`, `tests/test_delta.py` — No phase-18 changes or issues detected.

**No Critical or Warning findings.** The three Info items below are cosmetic / defense-in-depth observations that do not block phase sign-off.

## Info

### IN-01: `ProjectRoot.__post_init__` error message omits "CR-01 Pitfall 20" tag

**File:** `graphify/snapshot.py:26-32`
**Issue:** The four function-level guards (`snapshots_dir`, `list_snapshots`, `save_snapshot`, `auto_snapshot_and_delta`) each end their `ValueError` message with the canonical suffix `"(Codifies v1.3 CR-01 Pitfall 20.)"` (lines 41, 55, 80, 142). The `ProjectRoot.__post_init__` guard (lines 26-32) does not — its message ends at the `Try: ProjectRoot(...)` suggestion. This is the *earliest* sentinel in the stack and the most likely one an agent will hit first; the missing tag makes it slightly harder to grep-find the originating issue.

**Fix:**
```python
def __post_init__(self) -> None:
    if self.path.name == "graphify-out":
        raise ValueError(
            f"ProjectRoot received {self.path!r} which has name 'graphify-out'. "
            f"Pass the directory CONTAINING graphify-out/, not graphify-out/ itself. "
            f"Try: ProjectRoot({self.path.parent!r}). "
            f"(Codifies v1.3 CR-01 Pitfall 20.)"
        )
```

The class-level docstring (lines 17-22) already mentions "v1.3 CR-01 (Pitfall 20)", so the tag is consistent with existing prose — it just belongs in the raised message too for grep parity with the other four guards.

### IN-02: `_focus_debounce_put` eviction uses Python `sorted()` on every overflow

**File:** `graphify/serve.py:1875-1881`
**Issue:** When the debounce cache exceeds 256 entries the code calls `sorted(_FOCUS_DEBOUNCE_CACHE.items(), key=lambda kv: kv[1][0])[:64]` to pick the 64 oldest. This sorts all ~257 entries (O(N log N)) just to get the 64 smallest — `heapq.nsmallest(64, ...)` would be ~O(N log 64) and cleaner intent. Correctness is unaffected; the cap is tiny (256) so the performance delta is negligible. Flagged as Info rather than Warning because: (a) v1 review scope excludes performance, (b) the cap ceiling keeps the worst case bounded.

**Fix (optional):**
```python
import heapq
if len(_FOCUS_DEBOUNCE_CACHE) > 256:
    oldest = heapq.nsmallest(64, _FOCUS_DEBOUNCE_CACHE.items(), key=lambda kv: kv[1][0])
    for k, _ in oldest:
        _FOCUS_DEBOUNCE_CACHE.pop(k, None)
```

### IN-03: `test_focus_debounce_expires` uses list-of-one indirection for `fake_now`

**File:** `tests/test_serve.py:2553-2559`
**Issue:** The test defines `fake_now = [time_mod.monotonic()]` and then uses `fake_now[0] - 1.0` as the cached timestamp. The list-of-one indirection has no purpose (nothing else references `fake_now` later). Collapsing to a scalar keeps the test's intent obvious.

**Fix (optional):**
```python
past_ts = time_mod.monotonic() - 1.0
_FOCUS_DEBOUNCE_CACHE[key] = (past_ts, "CACHED_VALUE")
```

This is purely cosmetic — the test correctly verifies the 500ms window expiration.

## Observations (Positive — not findings)

These are intentionally highlighted because they represent good engineering hygiene that should be preserved:

1. **Layered `CR-01` defense:** `auto_snapshot_and_delta` guards at entry (line 137) *and* then calls `list_snapshots` (line 145) and `save_snapshot` (line 148), both of which re-guard. This defense-in-depth is correct — each public helper is independently robust even if a future refactor bypasses the top-level guard.

2. **`_run_get_focus_context_core` never raises (D-03 / D-11 invariant):** All failure paths collapse to `_no_context()` which returns a clean 4-key meta envelope. The try/except at line 1785 catches *both* `ValueError` and `FileNotFoundError` per Pitfall 4 — a bare `except ValueError` would leak tracebacks on `T-18-B`.

3. **Debounce uses `time.monotonic()` not `time.time()`:** Correct per Pitfall 6 — immune to NTP adjustments / system suspend-resume. Comment on lines 1846-1847 documents the choice.

4. **`_check_focus_freshness` Py 3.10 Z-suffix shim:** `reported_at.replace("Z", "+00:00")` before `fromisoformat` is the correct compat pattern; Python 3.11 would handle `Z` natively but the project targets 3.10+.

5. **`test_binary_status_invariant` pins the D-11 binary-status contract:** Three failure modes (spoofed, unindexed, missing) all asserted to produce identical 4-key meta. This is exactly the kind of cross-cutting invariant test that prevents the no_graph/no_context status drift noted in the `_tool_get_focus_context` docstring (lines 2258-2262).

6. **`test_no_context_does_not_echo_focus_hint` pins T-18-D:** Explicit `assert "/etc/passwd" not in response` + `assert "SECRET_FN" not in response` + `assert "424242" not in response` ensures no focus_hint values leak — crucial for the spoof-indistinguishable-from-unindexed security posture.

---

_Reviewed: 2026-04-20T20:48:00Z_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
