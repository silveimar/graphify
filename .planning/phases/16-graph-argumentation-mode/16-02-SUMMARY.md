---
phase: 16
plan: 02
subsystem: mcp-tool-dispatch
tags: [argue, mcp-tool, envelope, manifest, composable-from, recursion-guard, pitfall-4, pitfall-18]
dependency_graph:
  requires: [16-01]
  provides: [argue_topic MCP tool, _run_argue_topic_core, _tool_argue_topic, capability manifest argue_topic entry]
  affects: [graphify/serve.py, graphify/mcp_tool_registry.py, graphify/capability_tool_meta.yaml, tests/test_serve.py, tests/test_capability.py]
tech_stack:
  added: []
  patterns: [D-02 envelope, MANIFEST-05 handler parity, composable_from recursion guard, alias threading, sanitize_label]
key_files:
  created: []
  modified:
    - graphify/serve.py
    - graphify/mcp_tool_registry.py
    - graphify/capability_tool_meta.yaml
    - tests/test_serve.py
    - tests/test_capability.py
decisions:
  - "D-14: _run_argue_topic_core returns meta with exact 7 keys: status, verdict, rounds_run, argument_package, citations, resolved_from_alias, output_path"
  - "D-15: composable_from: [] declared in capability_tool_meta.yaml — ARGUE-07 recursion guard (chat→argue forbidden)"
  - "D-16: alias threading via _resolve_alias closure copied from _run_chat_core pattern; resolved_from_alias (never alias_redirects)"
  - "Rule 1: test_argue_does_not_invoke_chat used naive top-level \\ndef  boundary — fails for nested closures; fixed to indent-aware boundary extraction"
metrics:
  duration: "~7 minutes"
  completed: "2026-04-23T00:34:58Z"
  tasks_completed: 2
  tasks_total: 2
  files_modified: 5
---

# Phase 16 Plan 02: argue_topic MCP Tool Registration + Dispatch Summary

**One-liner:** argue_topic MCP tool registered with D-02 envelope, composable_from:[] recursion guard, and 5 regression tests enforcing ARGUE-04/07/09 and Pitfalls 4+18.

## What Was Built

### Task 1 — Registry + Manifest + Recursion Guard (ARGUE-07)

- `graphify/mcp_tool_registry.py`: Added `argue_topic` Tool entry to `build_mcp_tools()` with `required: ["topic"]`, `scope` enum `["topic","subgraph","community"]`, `budget` integer, `node_ids` array, `community_id` integer.
- `graphify/capability_tool_meta.yaml`: Added top-level `argue_topic:` block with `composable_from: []` — hard constraint preventing Phase 17 chat recursion (D-15, Pitfall 18).
- `tests/test_capability.py`: Added `test_argue_topic_not_composable` — asserts `build_manifest_dict()` reports `argue_topic.composable_from == []`.

### Task 2 — Core Function + Tool Wrapper + Handler Registration (ARGUE-04, ARGUE-09)

- `graphify/serve.py`:
  - `_run_argue_topic_core(G, communities, alias_map, arguments) -> str`: Top-level function immediately after `_run_chat_core`. Calls `graphify.argue.populate()`, threads every evidence citation through `_resolve_alias` closure, returns D-02 envelope. Never calls `_run_chat_core` (Pitfall 18). `output_path` hardcoded to `"graphify-out/GRAPH_ARGUMENT.md"` on every code path (ARGUE-09, T-16-05).
  - `_tool_argue_topic(arguments) -> str`: Closure inside `serve()` — mirrors `_tool_chat` pattern: reload-if-stale, no_graph early return, delegates to `_run_argue_topic_core`.
  - `_handlers["argue_topic"] = _tool_argue_topic`: MANIFEST-05 parity restored (22 tools total).
- `tests/test_serve.py`: Added 5 tests:
  - `test_argue_topic_tool_registered` — registry surface (ARGUE-04)
  - `test_argue_topic_envelope_ok` — D-14 meta keys, Pitfall 4 guard
  - `test_argue_topic_output_path` — ARGUE-09 both code paths
  - `test_argue_topic_alias_redirect` — D-16 alias threading
  - `test_argue_does_not_invoke_chat` — ARGUE-03/07 Pitfall 18 source-grep

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] test_argue_does_not_invoke_chat used incorrect function-body boundary**
- **Found during:** Task 2, Step E
- **Issue:** The plan's test used `src.find("\ndef ", ...)` (top-level `def` boundary) to extract `_tool_argue_topic`'s body. Since `_tool_argue_topic` is a closure nested inside `serve()`, `"\ndef "` never matches — `tool_end == -1` — so `tool_body = src[tool_start:]` includes the entire rest of the file (including the `_handlers` dict which contains `_tool_chat`), causing a false positive failure.
- **Fix:** Replaced naive `\ndef ` search with an indent-aware `_extract_func_body()` helper that detects the function's indentation level and searches for `"\n" + " " * indent + "def "` as the boundary.
- **Files modified:** `tests/test_serve.py`
- **Commit:** `7d8e57f`

**2. [Rule 1 - Bug] Docstring/comment contained literal `_run_chat_core` substring**
- **Found during:** Task 2, first test run
- **Issue:** `_run_argue_topic_core`'s docstring said "Never calls _run_chat_core" — the grep-based test found the substring in the function body and incorrectly flagged it as a violation.
- **Fix:** Rewrote docstring phrase to "Cross-phase chat invocation forbidden"; updated inline comment "copy verbatim from _run_chat_core" to reference "same transitive-cycle-guard pattern as chat core".
- **Files modified:** `graphify/serve.py`
- **Commit:** `7d8e57f`

### Pre-existing Failure (Out of Scope — Logged to deferred-items.md)

- `tests/test_capability.py::test_validate_cli_zero`: Fails with `assert 1 == 0` before Phase 16 changes (confirmed via `git stash`). Root cause: `server.json` manifest hash drift from Phase 17 adding `chat`/`get_focus_context` tools without regenerating the manifest. Requires Phase 13 Wave B manifest regen. Not caused by this plan.

## Verification Results

```
pytest tests/test_serve.py -q -k argue        → 5 passed
pytest tests/test_capability.py -q             → 20 passed, 1 pre-existing fail (test_validate_cli_zero)
pytest tests/ -q                               → 1409 passed, 1 pre-existing fail, 2 warnings
```

## Threat Surface Scan

No new network endpoints, auth paths, file access patterns, or schema changes at trust boundaries introduced. `output_path` is hardcoded (T-16-05 mitigated). `topic` sanitized via `sanitize_label(topic)[:120]` before embedding in `text_body` (T-16-01 mitigated).

## Known Stubs

- `meta["verdict"] = None` and `meta["rounds_run"] = 0`: Intentional — debate rounds run in `skill.md` SPAR-Kit orchestration (Plan 03). The substrate correctly returns 0/None; skill.md updates these after completing debate rounds.
- `meta["argument_package"]` contains node/edge counts but no debate transcript: Intentional — transcript is built by skill.md and written to `graphify-out/GRAPH_ARGUMENT.md`.

## Self-Check: PASSED

| Check | Result |
|-------|--------|
| graphify/serve.py exists | FOUND |
| graphify/mcp_tool_registry.py exists | FOUND |
| graphify/capability_tool_meta.yaml exists | FOUND |
| tests/test_serve.py exists | FOUND |
| tests/test_capability.py exists | FOUND |
| Task 1 commit f99e0e5 | FOUND |
| Task 2 commit 7d8e57f | FOUND |
| _run_argue_topic_core defined | FOUND |
| _tool_argue_topic defined | FOUND |
| argue_topic in registry | FOUND |
| argue_topic in capability_tool_meta.yaml | FOUND |
