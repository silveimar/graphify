---
phase: 17
plan: 03
subsystem: mcp-server
tags: [chat, alias, slash-command, zero-llm, stage-3, finalize]
requires:
  - serve.py::_run_chat_core (Plans 17-01 / 17-02)
  - serve.py::_run_connect_topics (alias closure pattern source)
  - graphify/commands/connect.md (frontmatter convention)
provides:
  - serve.py::_run_chat_core::_resolve_alias (closure)
  - serve.py::_run_chat_core::_resolved_aliases (state dict)
  - meta.resolved_from_alias field in chat envelope
  - graphify/commands/ask.md (/graphify-ask slash command)
  - tests/test_serve.py::test_chat_alias_redirect_canonical
  - tests/test_serve.py::test_chat_no_alias_empty_redirect_map
  - tests/test_serve.py::test_serve_makes_zero_llm_calls
  - tests/test_commands.py::test_ask_md_frontmatter
  - tests/test_commands.py::_parse_frontmatter
affects:
  - graphify/serve.py
  - graphify/commands/ask.md
  - tests/test_serve.py
  - tests/test_commands.py
tech_stack:
  added: []  # no new dependencies — stdlib `re` reused for frontmatter parsing
  patterns:
    - Verbatim closure copy (alias resolver from _run_connect_topics:1245)
    - Structural test as architectural invariant enforcement (zero-LLM via grep-on-source)
    - Shared frontmatter parser helper in test_commands.py
key_files:
  created:
    - graphify/commands/ask.md
  modified:
    - graphify/serve.py
    - tests/test_serve.py
    - tests/test_commands.py
decisions:
  - "Reused `resolved_from_alias` key name (6+ existing hits in serve.py) — never `alias_redirects` (CONTEXT.md D-08 Clarification)"
  - "No `target:` field in ask.md frontmatter (CONTEXT.md Clarification — matches connect.md/trace.md convention)"
  - "Zero-LLM enforcement via static grep on serve.py source — catches future regressions before runtime"
  - "Alias resolver applied BEFORE citation dict construction (Pitfall 3 — timing matters)"
metrics:
  duration: "~12 min"
  completed: 2026-04-22
  tasks: 2
  tests_added: 4
  tests_total_after: 1384
requirements: [CHAT-03, CHAT-06, CHAT-07]
---

# Phase 17 Plan 03: Command + Alias Integration Summary

Delivered CHAT-07 alias threading (canonical node_ids in chat citations via `_resolve_alias` closure), CHAT-06 `/graphify-ask` slash command, and CHAT-03 zero-LLM structural invariant test — closing all remaining Phase 17 threads.

## What Shipped

### Task 1 — Alias threading in `_run_chat_core` (CHAT-07 / T-17-05)

- Inserted the verbatim `_resolve_alias` closure from `_run_connect_topics:1245` into `_run_chat_core`, including the `_resolved_aliases: dict[str, list[str]]` accumulator and `_effective_alias_map` normalization of the nullable `alias_map` parameter.
- Applied `_resolve_alias(nid)` at two points:
  1. **seed_ids construction** — right after `_score_nodes`, so intent classification and downstream traversal only ever work on canonical IDs.
  2. **citation dict construction** — each citation's `node_id` passes through the resolver before entering `meta.citations`. Label/source_file lookups guard against the (now canonical) `nid` no longer being present in `G` with a `nid in G.nodes` check (since the alias was never a graph node in the first place).
- Replaced the Plan 17-01 placeholder `"resolved_from_alias": {}` with `"resolved_from_alias": _resolved_aliases` in the `meta` dict so the accumulator's final state (populated during citation resolution) is emitted.

**Commit:** `01eed87 feat(17-03): thread _resolve_alias through _run_chat_core citations`

Tests added (in `tests/test_serve.py`):
- `test_chat_alias_redirect_canonical` — monkeypatches `_score_nodes` to prepend a synthetic alias tuple, asserts the alias never appears in `meta.citations[*].node_id` and that `meta.resolved_from_alias[canonical_id]` lists the alias.
- `test_chat_no_alias_empty_redirect_map` — with `alias_map={}`, `meta.resolved_from_alias == {}`.

### Task 2 — `/graphify-ask` slash command (CHAT-06) + zero-LLM test (CHAT-03)

- Created `graphify/commands/ask.md` following the `connect.md` frontmatter convention (`name`, `description`, `argument-hint`, `disable-model-invocation: true`) — no `target:` field per CONTEXT.md Clarification.
- Body delegates to the `chat` MCP tool with `query: "$ARGUMENTS"` and defines the renderer behavior for all four envelope statuses (`no_graph`, `no_results`, `ok`, and `resolved_from_alias` note when non-empty).
- Added `_parse_frontmatter` helper + `test_ask_md_frontmatter` to `tests/test_commands.py`.
- Added `test_serve_makes_zero_llm_calls` to `tests/test_serve.py` (landed alongside Task 1 tests in commit `01eed87`) asserting `serve.py` source contains none of the forbidden import needles: `import anthropic`, `from anthropic`, `import openai`, `from openai`, `from graphify.llm`, `import graphify.llm`, `import langchain`, `from langchain`.

**Commit:** `23aed05 feat(17-03): ship /graphify-ask slash command + zero-LLM architectural test`

## Verification

| Check | Result |
|---|---|
| `pytest tests/test_serve.py -q -k chat` | 12 passed |
| `pytest tests/test_commands.py::test_ask_md_frontmatter` | passed |
| `pytest tests/test_serve.py::test_serve_makes_zero_llm_calls` | passed |
| `pytest tests/ -q` full baseline | **1384 passed**, 2 unrelated deprecation warnings |
| `grep -c "alias_redirects" graphify/serve.py` | 0 (correct — wrong key name absent) |
| `grep -n "resolved_from_alias" graphify/serve.py` | 15 hits (new hit inside `_run_chat_core`, rest pre-existing) |
| `grep -c "def _resolve_alias(" graphify/serve.py` | 4 (chat + connect + query + focus cores) |
| `test -f graphify/commands/ask.md` | exists |

## Deviations from Plan

None. The plan was executed exactly as written. The only micro-deviation: `test_serve_makes_zero_llm_calls` was bundled into the Task 1 commit (`01eed87`) rather than the Task 2 commit, because tests/test_serve.py was only staged once in that atomic edit. The test content, placement (chat test cluster), and behavior are identical to the plan's spec; only the commit boundary differs. Documented in the Task 2 commit message.

## Threat Model Compliance

- **T-17-05 (alias leak)** — MITIGATED. `_resolve_alias` is applied to every `node_id` BEFORE it enters `meta.citations`; test_chat_alias_redirect_canonical asserts the invariant. `meta.resolved_from_alias` is forward-only (lists canonical → [aliases redirected], does NOT enumerate aliases that weren't redirected).
- **T-17-02 (no_graph echo)** — MITIGATED. `ask.md` renders only envelope fields; `no_results` branch sources suggestions exclusively from `meta.suggestions` (graph-labels only per Plan 17-02 `_fuzzy_suggest`); never interpolates user query tokens into output.

## Key Decisions (for STATE.md)

- Chat citations are canonical-post-dedup via `_resolve_alias` threading (CHAT-07).
- `/graphify-ask` follows connect.md frontmatter convention — no `target:` field (CONTEXT.md Clarification).
- Zero-LLM invariant enforced structurally via grep-on-source (CHAT-03 SC4).

## Phase 17 Status

All three plans shipped: 17-01 (core dispatch + sessions), 17-02 (validator + composer + cap), 17-03 (command + alias + zero-LLM). All 12 P1 CHAT REQs (CHAT-01..09) covered by at least one passing test. Phase 17 is ready for `/gsd-verify-work`.

## Self-Check: PASSED

- graphify/commands/ask.md — FOUND
- tests/test_commands.py::test_ask_md_frontmatter — FOUND
- tests/test_serve.py::test_chat_alias_redirect_canonical — FOUND
- tests/test_serve.py::test_chat_no_alias_empty_redirect_map — FOUND
- tests/test_serve.py::test_serve_makes_zero_llm_calls — FOUND
- Commit 01eed87 — FOUND (feat(17-03): thread _resolve_alias through _run_chat_core citations)
- Commit 23aed05 — FOUND (feat(17-03): ship /graphify-ask slash command + zero-LLM architectural test)
