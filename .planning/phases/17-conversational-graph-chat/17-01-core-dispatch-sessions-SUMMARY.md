---
phase: 17
plan: 01
subsystem: mcp-server
tags: [chat, mcp-tool, sessions, intent-dispatch, stage-1-shell]
requires: [serve.py::_score_nodes, serve.py::_bfs, serve.py::_bidirectional_bfs, serve.py::QUERY_GRAPH_META_SENTINEL]
provides: [_run_chat_core, _tool_chat, _CHAT_SESSIONS, _classify_intent, _extract_entity_terms, _augment_terms_from_history, _chat_evict_stale, chat MCP tool]
affects: [graphify/serve.py, graphify/mcp_tool_registry.py, tests/test_serve.py, server.json]
tech_stack:
  added:
    - collections.deque (stdlib) — session FIFO ring
    - re (stdlib) — intent + token patterns
  patterns:
    - Closure-local _tool_* wrapper inside serve() (mirrors _tool_connect_topics)
    - Module-level _run_*_core pure-dispatch for unit testability (mirrors _run_connect_topics)
    - D-02 sentinel envelope on every return path
    - Lazy TTL eviction on each call (no background thread)
key_files:
  created: []
  modified:
    - graphify/serve.py
    - graphify/mcp_tool_registry.py
    - tests/test_serve.py
    - server.json
decisions:
  - "Registry exposes build_mcp_tools() function (not TOOLS constant) — test accommodates via getattr+fallback"
  - "Stage 2 narrative body left empty ('') — Plan 17-02 will wire composer/validator/cap"
  - "session_id silently coerced to None when malformed or over 128 chars (T-17-03)"
  - "Connect intent requires 2+ scored seeds before dispatching _bidirectional_bfs; otherwise falls through to explore"
metrics:
  duration_minutes: ~15
  tasks_completed: 2
  files_modified: 4
  tests_added: 5
  tests_total: 1375
  completed_date: "2026-04-22"
---

# Phase 17 Plan 01: Core Dispatch & Sessions Summary

Ship the Stage-1 shell of the `chat` MCP tool: deterministic intent classifier, entity-term extractor, primitive dispatcher (explore/connect/summarize), per-session conversation history with lazy TTL eviction, and D-02 envelope skeleton. Narrative composition is stubbed; Plan 17-02 fills `text_body`.

## What Shipped

- **`_run_chat_core(G, communities, alias_map, arguments) -> str`** — pure-dispatch core, 4-arg signature matching `_run_connect_topics`. Returns full D-02 envelope on every path.
- **`_tool_chat(arguments)`** — MCP wrapper inside `serve()` closure. Calls `_reload_if_stale()`, returns `no_graph` envelope if graph.json absent, else delegates to `_run_chat_core`.
- **Intent classifier** — `_classify_intent()` resolves summarize triggers (`what's in`, `overview of`, `summarize`) before connect verbs (`connect|relate|between|path|from…to`); default is `explore`.
- **Entity-term extractor** — `_extract_entity_terms()` lowercases + ASCII-tokenizes + drops stopwords + drops tokens ≤2 chars.
- **Follow-up augmentation** — `_augment_terms_from_history()` prepends prior turn's cited `node_id`s when query starts with `and/but/what about/tell me more/more/why/how come/it/that`.
- **Session store** — module-level `_CHAT_SESSIONS: dict[str, deque]` with `maxlen=10`, `TTL=1800s`, lazy eviction via `_chat_evict_stale(now)` called on every invocation.
- **Registry entry** — `types.Tool(name="chat", inputSchema={properties: {query, session_id}, required: [query]})`.
- **Dispatch table** — `"chat": _tool_chat` added between `graph_summary` and `connect_topics`.
- **Tests (5)** — `test_chat_tool_registered`, `test_chat_envelope_ok`, `test_chat_intent_connect_calls_bi_bfs`, `test_chat_session_isolation`, `test_chat_ttl_eviction`.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 2 — Missing Critical Functionality] Refresh `server.json` capability manifest hash**
- **Found during:** Task 2 verification (`pytest tests/`)
- **Issue:** `test_capability.py::test_validate_cli_zero` failed with `manifest content hash mismatch (committed vs generated)`. Adding a new MCP tool silently broke the manifest drift gate.
- **Fix:** Recomputed `canonical_manifest_hash(build_manifest_dict())` = `ce1d730e…`, updated `server.json._meta.manifest_content_hash` and `_meta.tool_count` (20 → 21).
- **Files modified:** `server.json`
- **Commit:** 10f671d

### Test-file registry-symbol fallback

Plan's Task 2 test skeleton used `getattr(mcp_tool_registry, "TOOLS", None) or getattr(..., "tools", None)`. The registry module exposes neither — it provides `build_mcp_tools()` (function). Per plan's own guard note ("Do NOT change the registry module itself to satisfy the test") I extended the fallback chain: `TOOLS → tools → build_mcp_tools()`. No registry change.

## Authentication Gates

None.

## Threat Flags

None. Surface matches plan's threat model:
- T-17-03 (Spoofing/DoS on `_CHAT_SESSIONS`) mitigated via `_CHAT_SESSION_ID_MAX_LEN=128` cap + silent-ignore on non-str or over-cap `session_id`. No stderr logging of session_id values.

## Known Stubs

**`_run_chat_core.text_body = ""`** — Stage 2 narrative composition stubbed by design. Plan 17-02 wires:
- Real narrative composer (template-based, zero LLM)
- Citation validator (every narrative claim must reference a real visited node_id)
- Budget cap

Stubbed intentionally per plan objective ("Narrative composition and citation validation are stubbed in this plan") and flagged in inline comments (`# Plan 17-02 populates`).

## Verification

| Check | Result |
|-------|--------|
| `pytest tests/test_serve.py -q -k chat` | 5/5 passed |
| `pytest tests/test_serve.py -q` | 180/180 passed |
| `pytest tests/ -q` | 1375/1375 passed |
| `grep -n "def _run_chat_core(" graphify/serve.py` | 1 hit (L989) |
| `grep -n '"chat":' graphify/serve.py` | 1 hit (L2712, dispatch table) |
| `grep -n 'name="chat"' graphify/mcp_tool_registry.py` | 1 hit (L214) |
| `grep -c "alias_redirects" graphify/serve.py` | 0 (uses `resolved_from_alias`) |
| `grep -cE "^(import\|from)[[:space:]]+(anthropic\|openai)" graphify/serve.py` | 0 (no LLM client) |
| `python -c "from graphify.serve import _run_chat_core, _CHAT_SESSIONS, _classify_intent, _extract_entity_terms, _chat_evict_stale"` | OK |

## TDD Gate Compliance

This plan used a test-after pattern rather than strict test-first: Task 1 added the implementation in commit `3f01f63` (`feat(17-01)`) and Task 2 added the tests in commit `10f671d` (`test(17-01)`). Plan frontmatter declares `type: execute` (not `type: tdd`), so strict RED→GREEN gate ordering is not mandatory. All 5 tests pass GREEN and full suite is green.

## Commits

| Hash | Type | Subject |
|------|------|---------|
| 3f01f63 | feat | add chat tool shell with intent dispatch and session store |
| 10f671d | test | add chat tool tests and refresh capability manifest hash |

## Self-Check: PASSED

- FOUND: graphify/serve.py (`_run_chat_core` at L989)
- FOUND: graphify/mcp_tool_registry.py (`name="chat"` at L214)
- FOUND: tests/test_serve.py (5 `test_chat_*` cases appended)
- FOUND: server.json (updated `_meta.manifest_content_hash`)
- FOUND: commit 3f01f63
- FOUND: commit 10f671d
