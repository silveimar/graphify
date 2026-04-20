---
phase: 18
plan: 03
subsystem: serve (dispatch-layer guards)
tags: [mcp, focus-context, debounce, freshness, py310-compat, d-14-monotonic, d-15-freshness-window, time-monotonic, datetime-fromisoformat, p2-guards, phase-18-final-wave]
requirements_closed: [FOCUS-08, FOCUS-09]
dependency_graph:
  requires:
    - graphify/serve.py::_run_get_focus_context_core (Plan 18-02)
    - graphify/serve.py::_tool_get_focus_context (Plan 18-02)
    - graphify/serve.py::QUERY_GRAPH_META_SENTINEL
    - stdlib: time.monotonic (module-level import added)
    - stdlib: datetime.fromisoformat (already imported for snapshot lifecycle)
  provides:
    - graphify/serve.py::_FOCUS_DEBOUNCE_CACHE
    - graphify/serve.py::_FOCUS_DEBOUNCE_WINDOW
    - graphify/serve.py::_focus_debounce_key
    - graphify/serve.py::_focus_debounce_get
    - graphify/serve.py::_focus_debounce_put
    - graphify/serve.py::_check_focus_freshness
  affects:
    - graphify/serve.py::_tool_get_focus_context (wrapper body now: freshness → debounce-get → core → debounce-put)
tech_stack:
  added: []
  patterns:
    - "D-14: monotonic-clock debounce — `time.monotonic()` immune to NTP skew / suspend-resume (not `time.time()`)"
    - "D-14: bounded LRU — evict oldest 64 when cache >256 (RESEARCH Pitfall 6 DoS cap)"
    - "D-15: `reported_at` ≤ 300s freshness window; absent = backward compatible True"
    - "Py 3.10 compat shim: `reported_at.replace(\"Z\", \"+00:00\")` BEFORE `datetime.fromisoformat` (Pitfall 2)"
    - "Pitfall 7: cache pre-manifest-merge core output (byte-identical replay across `_merge_manifest_meta`)"
    - "D-11 binary invariant preserved: freshness fail + debounce hit + stale parse all collapse to the 4-key no_context envelope"
key_files:
  created:
    - .planning/phases/18-focus-aware-graph-context/18-03-SUMMARY.md
  modified:
    - graphify/serve.py
    - tests/test_serve.py
decisions:
  - "Cache is `dict[tuple, tuple[float, str]]` — simpler than `OrderedDict` LRU; sort-and-drop-oldest-64-on-overflow is O(n log n) only when >256, negligible overhead at steady state."
  - "Cache size cap 256 + eviction batch 64 taken verbatim from RESEARCH.md Code Example — not re-tuned. Rationale: 256 × ~2KB envelope ≈ 512KB worst-case working set; trivially safe."
  - "Debounce key is a tuple of 5 fields (file_path, function_name, line, neighborhood_depth, include_community). `reported_at` is DELIBERATELY excluded from the key — two calls within 500ms reporting different `reported_at` values are still duplicates for debounce purposes. The freshness gate runs BEFORE debounce, so stale reported_at never even reaches the cache lookup."
  - "`_no_context_envelope()` duplicated as a closure in `_tool_get_focus_context` (vs. importing the core's version) — keeps both sites byte-identical and covered by `test_binary_status_invariant` from Plan 18-02. Extracting a shared helper was a 1-test-coverage-loss tradeoff not worth taking in a P2 plan."
  - "Freshness check runs BEFORE debounce (not after). If a stale reported_at is received, we never populate the cache with a no_context envelope keyed on a stale focus — keeps cache semantically clean (entries are always post-freshness-passed)."
  - "Py 3.10 vs 3.11+ Z-suffix behavior: Py 3.11 datetime.fromisoformat accepts 'Z'; Py 3.10 raises. Using `.replace(\"Z\", \"+00:00\")` unconditionally is safe on both versions and avoids version-gated code — simpler than conditional `sys.version_info` branching."
metrics:
  duration_seconds: 510
  completed: "2026-04-20T19:52:41Z"
  tasks_completed: 3
  files_modified: 2
  tests_added: 5
  tests_total_after: 1325
---

# Phase 18 Plan 03: Focus Debounce + Reported-At Freshness Summary

Ships the two P2 guards for `get_focus_context`: a 500ms module-level LRU debounce keyed on the focus-hint tuple (FOCUS-08 / D-14) and a `reported_at` freshness check with Py 3.10 Z-suffix compatibility (FOCUS-09 / D-15). Both guards are dispatch-layer adapters wrapping `_run_get_focus_context_core` (the Plan 18-02 pure dispatch core) — no changes to core envelope semantics, no new modules, no new runtime dependencies.

With Plan 18-03 landed, **Phase 18 is complete**: all 9 FOCUS REQ-IDs (FOCUS-01..09) are closed and the 500ms debounce + 300s freshness gates are in place before Phase 14 (Obsidian Commands) starts hammering the tool on every keystroke.

## What Shipped

### Symbols Added (graphify/serve.py)

- **`_FOCUS_DEBOUNCE_CACHE: dict[tuple, tuple[float, str]]`** (line 1850) — Module-level cache. Value is `(monotonic_timestamp, envelope_string)`. Empty-dict initial state.
- **`_FOCUS_DEBOUNCE_WINDOW = 0.5`** (line 1851) — Debounce window in seconds. Per D-14 verbatim.
- **`_focus_debounce_key(focus_hint: dict) -> tuple`** (line 1854) — 5-tuple: `(file_path, function_name, line, neighborhood_depth, include_community)`. Sentinel `-1` for missing line; `""` for missing function_name.
- **`_focus_debounce_get(key: tuple) -> str | None`** (line 1865) — Returns cached envelope if `time.monotonic() - ts < 0.5`; None otherwise.
- **`_focus_debounce_put(key: tuple, envelope: str) -> None`** (line 1876) — Evicts oldest 64 entries when cache size >256 (DoS mitigation per RESEARCH Pitfall 6).
- **`_check_focus_freshness(reported_at: str | None, now: datetime | None = None) -> bool`** (line 1886) — Absent reported_at returns True (backward compat D-15). Parse failure or `now - reported_at > 300s` returns False. Py 3.10 `.replace("Z", "+00:00")` compat shim applied BEFORE `datetime.fromisoformat` (line 1901).

### Wrapper Rewired (graphify/serve.py)

`_tool_get_focus_context` (line 2256 onward) now routes every call:

```text
_reload_if_stale
  → graph.json exists? → (no) → no_context
  → focus_hint extracted
  → _check_focus_freshness(reported_at) → (stale/malformed) → no_context
  → _focus_debounce_get(key)           → (cache hit) → return cached envelope
  → _run_get_focus_context_core(...)
  → _focus_debounce_put(key, envelope)
  → return envelope
```

Both guard rejections emit the same 4-key no_context envelope as any other failure (`meta = {status, node_count, edge_count, budget_used}` all zeros except status), preserving the D-03/D-11 binary-status invariant tested by `test_binary_status_invariant` from Plan 18-02.

### Tests Added (tests/test_serve.py)

All five names locked verbatim per 18-VALIDATION.md rows 18-03-01..05 — do NOT rename:

1. `test_focus_debounce_suppresses_duplicate` — FOCUS-08 / D-14. Cache hit within window returns byte-identical envelope; monkeypatched core raises if invoked (proves no core re-dispatch occurred).
2. `test_focus_debounce_expires` — FOCUS-08 / D-14. Entry with timestamp 1s in the past is rejected by `_focus_debounce_get` (window is 0.5s).
3. `test_focus_stale_reported_at_rejected` — FOCUS-09 / D-15. `reported_at` 10 minutes ago returns False.
4. `test_focus_reported_at_z_suffix_parses` — FOCUS-09 Py 3.10 compat. `"2026-MM-DDTHH:MM:SSZ"` parses via the shim (True on fresh).
5. `test_focus_malformed_reported_at` — FOCUS-09 / D-11. `"not-an-iso-date"` and `"2026-99-99T99:99:99Z"` return False; `""` and `None` return True (absent = backward compatible).

## Commits

| # | Gate | Hash | Message |
|---|------|------|---------|
| 1 | RED (18-03-01) | `2309a57` | `test(18-03): add failing tests for focus debounce + reported_at freshness` |
| 2 | GREEN (18-03-02 + 03) | `0f06629` | `feat(18-03): add focus debounce cache + reported_at freshness with Py3.10 Z-shim` |

## Verification Results

```text
$ grep -Fn "_FOCUS_DEBOUNCE_CACHE" graphify/serve.py | head -1
1850:_FOCUS_DEBOUNCE_CACHE: "dict[tuple, tuple[float, str]]" = {}

$ grep -Fn "_FOCUS_DEBOUNCE_WINDOW = 0.5" graphify/serve.py
1851:_FOCUS_DEBOUNCE_WINDOW = 0.5  # seconds; D-14

$ grep -n "^def _focus_debounce_key\|^def _focus_debounce_get\|^def _focus_debounce_put\|^def _check_focus_freshness" graphify/serve.py
1854:def _focus_debounce_key(focus_hint: dict) -> tuple:
1865:def _focus_debounce_get(key: tuple) -> "str | None":
1876:def _focus_debounce_put(key: tuple, envelope: str) -> None:
1886:def _check_focus_freshness(

$ grep -Fn '.replace("Z", "+00:00")' graphify/serve.py
1894:    compat shim `.replace("Z", "+00:00")` (RESEARCH Pitfall 2). Parse failure
1901:        ts = datetime.fromisoformat(reported_at.replace("Z", "+00:00"))

$ grep -Fn 'time.monotonic()' graphify/serve.py
1848:# time.monotonic() is used (not time.time()) because it is guaranteed non-decreasing
1871:    if time.monotonic() - ts < _FOCUS_DEBOUNCE_WINDOW:
1882:    _FOCUS_DEBOUNCE_CACHE[key] = (time.monotonic(), envelope)

$ grep -Fn '_focus_debounce_get(key)' graphify/serve.py
2279:        cached = _focus_debounce_get(key)

$ grep -Fn '_focus_debounce_put(key, envelope)' graphify/serve.py
2287:        _focus_debounce_put(key, envelope)

$ grep -Fn '_check_focus_freshness(focus_hint.get("reported_at"))' graphify/serve.py
2271:        if not _check_focus_freshness(focus_hint.get("reported_at")):

$ grep -n "time.time()" graphify/serve.py | grep -i focus   # anti-pattern — expect zero
(zero — all focus-path timing uses time.monotonic as required by D-14)

$ grep -n "dateutil" graphify/serve.py                      # anti-pattern — expect zero
(zero — no new runtime dependency)

$ pytest tests/ -q
1325 passed, 2 warnings in 35.28s
```

All success-criteria items from the plan are satisfied:

- [x] Module-level `_FOCUS_DEBOUNCE_CACHE` + `_FOCUS_DEBOUNCE_WINDOW = 0.5` exist in graphify/serve.py.
- [x] `_focus_debounce_get(key)` returns cached envelope when `time.monotonic() - last_ts < 0.5s`; None otherwise.
- [x] `_focus_debounce_put(key, envelope)` evicts oldest 64 when cache size >256.
- [x] `_check_focus_freshness(reported_at, now=None)` returns False on stale (>300s) or malformed; True when reported_at is absent (D-15 backward compat).
- [x] Freshness uses `.replace("Z", "+00:00")` shim BEFORE `datetime.fromisoformat` (RESEARCH Pitfall 2).
- [x] `_tool_get_focus_context` checks freshness BEFORE debounce, and debounce BEFORE core.
- [x] Debounce caches the core output (pre-`_merge_manifest_meta`) per RESEARCH Pitfall 7.
- [x] Stale/malformed freshness AND cache-hit both produce identical no_context envelope shape as unindexed/spoofed path → D-03/D-11 binary invariant preserved.
- [x] No `time.time()` usage in the debounce path.
- [x] No new runtime dependencies.
- [x] Py 3.10 + 3.12 compatibility preserved (Z-suffix shim verified by `test_focus_reported_at_z_suffix_parses` on Py 3.10.19 CI matrix).
- [x] Full suite green: 1325 passed (1320 baseline + 5 new, zero regressions).

## Deviations from Plan

None — plan executed exactly as written. No Rule 1/2/3 auto-fixes needed; no auth gates; no architectural surprises. The Plan 18-02 SUMMARY's "Expected Interface for Plan 18-03 Consumer" section precisely matched the implementation seams, so wrap-don't-rewrite composition landed cleanly on first attempt.

## Consumer Note for Phase 14 (Obsidian Thinking Commands)

Phase 14 commands (`/graphify-moc`, `/graphify-related`, `/graphify-wayfind`) that consume `get_focus_context` on keystroke events should:

1. **Optionally include `reported_at` in the focus_hint** as ISO 8601 UTC (either `"+00:00"` or `"Z"` suffix — both work). Absence is backward compatible. Presence enables the 300s staleness check; stale focus returns the same silent no_context envelope as spoofed paths.
2. **Expect duplicate-suppression at 500ms**. Calls within that window return the previous envelope byte-identically (including same citations, same community summary, same budget_used). Treat the cache as transparent — there is no cache-hit marker in the envelope (by design, per D-12 no-observability-leak).
3. **Budget for ~512KB steady-state memory** for the debounce cache under adversarial load (256 entries × ~2KB envelope) — trivial in server context.

## Phase 18 Retrospective Triggers

What would we catch next time with a broader fixture pattern (captured for future phases)?

1. **Nested-dir fixture proved its worth.** Plan 18-02's `nested_project_root` fixture caught the CR-01 double-nesting regression class that hit v1.3 in production. Phases 15/17 (which read from `_out_dir.parent` in their own wrappers) should reuse the same fixture — done by the fixture living in `conftest.py` at test-level scope.
2. **Binary-status invariant is the phase's strongest property test.** `test_binary_status_invariant` was originally Plan 18-02 scope, but Plan 18-03's two new rejection paths (stale/malformed freshness, debounce hit) implicitly strengthen its coverage. Recommendation for Phases 15/17: design a similar n-cases-→-same-shape property test alongside the first no-context handler, to future-proof the envelope against silent leak.
3. **Py 3.10 datetime gotcha was pre-flagged by RESEARCH.md Pitfall 2** — resolution landed exactly as documented. The CI matrix (3.10 + 3.12) is critical for catching version-gated datetime/pathlib behavior; do NOT drop Py 3.10 support without an explicit ADR, because downstream phases (15 enrichment, 17 chat) will inherit the same Z-suffix handling.
4. **`time.monotonic()` vs `time.time()` decision is easy to get wrong under pressure.** Every future phase using wall-clock debounce should default to `time.monotonic()` unless the timestamp needs to be serialized (it doesn't here — cache is in-process ephemeral).

## `time.monotonic()` Edge Cases Observed

None in testing. Py 3.10.19 on Darwin ARM64 produced a stable monotonic clock with sub-microsecond resolution — all 5 tests passed deterministically in 0.15s combined. The `time.monotonic() - ts < 0.5` check is structurally robust against:

- **NTP skew** — monotonic does not step; wall clock can.
- **System suspend-resume** — monotonic stops during suspend on macOS (per POSIX) but resumes correctly on wake; no spurious "0.5s elapsed" false positives from long-sleep laptops.
- **Multi-process confusion** — module-level cache is per-process; no cross-process contention (the MCP stdio server is single-process by design).

## Self-Check: PASSED

- graphify/serve.py::_FOCUS_DEBOUNCE_CACHE — FOUND (line 1850)
- graphify/serve.py::_FOCUS_DEBOUNCE_WINDOW = 0.5 — FOUND (line 1851)
- graphify/serve.py::_focus_debounce_key — FOUND (line 1854)
- graphify/serve.py::_focus_debounce_get — FOUND (line 1865)
- graphify/serve.py::_focus_debounce_put — FOUND (line 1876)
- graphify/serve.py::_check_focus_freshness — FOUND (line 1886)
- graphify/serve.py::`.replace("Z", "+00:00")` — FOUND (line 1901)
- graphify/serve.py::time.monotonic() in helpers — FOUND (lines 1871, 1882)
- graphify/serve.py::wrapper freshness gate — FOUND (line 2271)
- graphify/serve.py::wrapper debounce get — FOUND (line 2279)
- graphify/serve.py::wrapper debounce put — FOUND (line 2287)
- tests/test_serve.py::test_focus_debounce_suppresses_duplicate — FOUND (line 2459)
- tests/test_serve.py::test_focus_debounce_expires — FOUND (line 2490)
- tests/test_serve.py::test_focus_stale_reported_at_rejected — FOUND (line 2506)
- tests/test_serve.py::test_focus_reported_at_z_suffix_parses — FOUND (line 2514)
- tests/test_serve.py::test_focus_malformed_reported_at — FOUND (line 2524)
- commit 2309a57 (test RED) — FOUND in git log
- commit 0f06629 (feat GREEN) — FOUND in git log
- anti-pattern `time.time()` in focus path — ABSENT (as required by D-14)
- anti-pattern `dateutil` — ABSENT (no new runtime dep)
- full suite: 1325 passed (1320 baseline + 5 new, zero regressions) — GREEN
