---
phase: 11-narrative-mode-slash-commands
plan: 04
subsystem: commands
tags: [commands, slash-commands, prompt, mcp, phase-11]
dependency_graph:
  requires: [11-01, 11-02, 11-03]
  provides: [context.md, trace.md, connect.md, drift.md, emerge.md, tests/test_commands.py]
  affects: [graphify/commands/, tests/test_commands.py]
tech_stack:
  added: []
  patterns: [disable-model-invocation-frontmatter, ARGUMENTS-placeholder, hybrid-envelope-parse, pitfall-4-distinct-sections, drift-detector-regex-test]
key_files:
  created:
    - graphify/commands/context.md
    - graphify/commands/trace.md
    - graphify/commands/connect.md
    - graphify/commands/drift.md
    - graphify/commands/emerge.md
    - tests/test_commands.py
  modified: []
decisions:
  - "Five command files ship as data (prompts) in graphify/commands/ — no code changes to serve.py or __main__.py in this plan"
  - "connect.md explicitly guards Pitfall-4 with 'Do NOT merge' wording and section ordering enforced by test"
  - "Drift detector test uses regex over serve.py source (types.Tool name= extraction) — avoids MCP runtime dependency in tests"
metrics:
  duration_minutes: 3
  tasks_completed: 3
  files_modified: 6
  completed_date: "2026-04-17"
requirements: [SLASH-01, SLASH-02, SLASH-03, SLASH-04, SLASH-05]
---

# Phase 11 Plan 04: Slash-Command Prompt Files Summary

**One-liner:** Five Claude Code slash-command `.md` files for `/context`, `/trace`, `/connect`, `/drift`, `/emerge` — each with YAML frontmatter, correct MCP tool name, status-coded fallback guards, and a 10-test drift-detector test suite enforcing serve.py cross-reference.

## What Was Built

### graphify/commands/ (new directory)

Five prompt files created, each with:
- YAML frontmatter: `name`, `description`, `argument-hint`, `disable-model-invocation: true`
- Body instructing Claude to call the matching MCP tool from plans 11-01..11-03
- `no_graph` status guard with verbatim fallback message (all 5)
- Snapshot-history guard (`insufficient_history`) where applicable (trace, drift, emerge)
- Thinking-partner prose output instructions (not raw JSON, not bullet-point status reports)

**context.md** — calls `graph_summary(top_n=10, budget=500)`. Renders a one-line graph frame, top 3 god nodes, top 3 communities, delta summary, and a single follow-up question pointing to `/emerge`, `/trace`, or `/drift`.

**trace.md** — calls `entity_trace(entity=$ARGUMENTS, budget=500)`. Handles `no_graph`, `insufficient_history`, `ambiguous_entity` (candidates list + re-invoke hint), `entity_not_found`. On `ok`: renders first-seen, community journey, degree trend, current status, alias redirect if present. Ends with one follow-up question.

**connect.md** — calls `connect_topics(topic_a, topic_b, budget=500)` with args parsed from `$ARGUMENTS`. Handles `no_graph`, `ambiguous_entity`, `entity_not_found`, `no_path`. On `ok`: renders TWO DISTINCT SECTIONS ("Shortest path" then "Surprising bridges in the graph") — Pitfall-4 anti-conflation guard is explicit in the file body and enforced by test.

**drift.md** — calls `drift_nodes(top_n=10, max_snapshots=10, budget=500)`. Handles `no_graph`, `insufficient_history`. On `ok`: prose narrative naming top 3 drifters, community changes, directionality, one pressing question.

**emerge.md** — calls `newly_formed_clusters(budget=500)`. Handles `no_graph`, `insufficient_history`, `no_change`. On `ok`: narrative naming each emerged community with 2-3 representative members and a follow-up `/trace` suggestion.

### tests/test_commands.py (new file)

10 tests covering:

| Test | What it enforces |
|------|-----------------|
| `test_command_files_exist_in_package` | all 5 .md files present under graphify/commands/ |
| `test_command_files_have_required_frontmatter` | name, description, argument-hint, disable-model-invocation: true |
| `test_command_files_reference_correct_mcp_tool` | each file contains its designated tool name |
| `test_command_files_have_no_graph_guard` | no_graph in every file |
| `test_snapshot_commands_have_insufficient_history_guard` | trace/drift/emerge have insufficient_history |
| `test_trace_md_has_ambiguous_and_not_found_guards` | ambiguous_entity + entity_not_found in trace.md |
| `test_connect_md_has_distinct_sections` | "Shortest path" and "Surprising bridges" both present |
| `test_connect_md_does_not_conflate_sections` | Shortest path section appears before Surprising bridges (order check) |
| `test_parameterized_commands_reference_arguments` | $ARGUMENTS in trace.md and connect.md |
| `test_command_files_reference_registered_tools` | every tool name in CORE_COMMANDS is registered as types.Tool(name=...) in serve.py (drift detector — plan-checker WARNING 3 fix) |

## Deviations from Plan

None — plan executed exactly as written. The plan specified the exact file content for all 5 command files and the test file; all were created verbatim. The TDD task (Task 3) had the command files already present from Tasks 1 and 2, so tests went straight to GREEN (10/10 passing) — this is expected behavior per the plan's task ordering.

## Known Stubs

None. All 5 command files are complete prompts with no placeholder text, hardcoded empties, or TODO markers. The `graphify/commands/` directory is not yet wired to `graphify install` (that is plan 11-06's responsibility, as documented in the plan objective).

## Threat Flags

No new network endpoints, auth paths, file access patterns, or schema changes introduced. The command files are static markdown prompts. The `$ARGUMENTS` echo path is sanitized server-side via `sanitize_label()` in serve.py (T-11-04-01 per plan threat model — accepted, mitigation already present).

## Self-Check: PASSED
