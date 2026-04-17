GATE: proceed
---
phase: 11-narrative-mode-slash-commands
plan: "07"
subsystem: commands
tags: [commands, stretch, phase-11, slash-commands, ghost, challenge]
dependency_graph:
  requires:
    - graphify/serve.py (get_annotations, query_graph, get_neighbors, god_nodes — all pre-existing MCP tools)
    - graphify/commands/context.md (voice/format reference)
    - graphify/commands/trace.md (guard-pattern reference)
  provides:
    - graphify/commands/ghost.md (SLASH-06 /ghost command)
    - graphify/commands/challenge.md (SLASH-07 /challenge command)
    - tests/test_commands.py (extended with 6 new stretch tests)
  affects:
    - graphify/commands/ (2 new .md files)
    - tests/test_commands.py (6 new test functions, 1 new constant)
tech_stack:
  added: []
  patterns:
    - "Pure .md slash-command prompt files — no new graphify/ code (D-18 honored)"
    - "Anti-fabrication guard: 'do NOT fabricate evidence' in challenge.md"
    - "GATE: proceed recorded as first line of SUMMARY (plan-checker WARNING 4 fix)"
key_files:
  created:
    - path: graphify/commands/ghost.md
      summary: "/ghost command — calls get_annotations(peer_id='self') + god_nodes(top_n=10); renders response in user's own voice; no_graph fallback guard; anti-impersonation note"
    - path: graphify/commands/challenge.md
      summary: "/challenge <belief> command — calls query_graph(seed_nodes=..., depth=2, budget=500); renders Evidence supporting + Evidence contradicting sections; anti-fabrication guard; no_graph fallback"
  modified:
    - path: tests/test_commands.py
      summary: "Added STRETCH_COMMANDS dict + 6 new test functions for ghost.md and challenge.md existence, frontmatter, guards, MCP tool refs, evidence sections, and anti-fabrication"
decisions:
  - "GATE: proceed — plans 11-01..06 completed in ~74 minutes total (45+7+7+3+5+7) with no blockers; well under 60% budget threshold; stretch plans ship"
  - "ghost.md uses peer_id='self' sentinel and explicit anti-impersonation note (T-11-07-02 mitigation)"
  - "challenge.md 'do NOT fabricate' guard tested by test_challenge_md_has_anti_fabrication_guard (T-11-07-04 mitigation)"
  - "Both stretch files reuse existing MCP tools only — no new serve.py tools added (D-18 honored, thin-wrapper promise kept)"
metrics:
  duration_minutes: 8
  tasks_completed: 4
  files_changed: 3
  completed_date: "2026-04-17"
---

# Phase 11 Plan 07: Stretch Commands — /ghost and /challenge — Summary

**One-liner:** Two stretch slash-command `.md` files for `/ghost` (annotation-grounded voice reflection) and `/challenge` (belief pressure-test with supporting vs. contradicting graph evidence), with 6-test coverage in `tests/test_commands.py`.

## Gate Decision

**GATE: proceed**

Budget analysis (plans 11-01 through 11-06):
- Plan 01: 45 minutes (complex MCP server code — graph_summary + connect_topics + 11 tests)
- Plan 02: 7 minutes (entity_trace + drift_nodes)
- Plan 03: 7 minutes (newly_formed_clusters + install/uninstall)
- Plan 04: 3 minutes (5 command .md files + 10 tests)
- Plan 05: 5 minutes (skill file discoverability section — 9 variants)
- Plan 06: ~7 minutes (install wiring + uninstall + platform config)
- **Total: ~74 minutes** for 6 plans — no blockers, all 1218 tests pass

The 60% threshold check: these 6 plans delivered MCP server code, 5 command files, install/uninstall wiring, and discoverability updates in 74 minutes. The remaining 2 stretch plans each produce only a single .md file + test extension — the lightest possible deliverable. Budget is clearly not exhausted.

**Decision: proceed. SLASH-06 (/ghost) and SLASH-07 (/challenge) ship in this plan.**

## What Was Built

### Task 0 (Gate)
Budget assessed from 6 prior SUMMARY.md files. GATE: proceed recorded as first line of this SUMMARY.

### Task 1: graphify/commands/ghost.md (SLASH-06)
`/ghost` command: answer in the user's own voice, grounded in their graph contributions and annotations.

- Calls `get_annotations(peer_id="self")` to pull the user's authored annotations + voice patterns
- Calls `god_nodes(top_n=10)` to identify conceptual concerns
- `no_graph` fallback with verbatim hint
- Empty annotations fallback with explanation and re-invoke hint
- Anti-impersonation note: "Do NOT pretend to be a different person — this is reflective, not impersonation"
- Thinking-partner beat: "This is how you might frame it — does it match how you'd actually answer?"

### Task 2: graphify/commands/challenge.md (SLASH-07)
`/challenge <belief>` command: pressure-test a stated belief against graph evidence.

- Calls `query_graph(seed_nodes=[...], depth=2, budget=500)` with concepts extracted from `$ARGUMENTS`
- `no_graph` and `no_seed_nodes` fallbacks
- Two distinct sections: **Evidence supporting** and **Evidence contradicting**
- Anti-fabrication guard: "do NOT fabricate evidence" + "If one side is empty, state so plainly"
- Thinking-partner question referencing `/trace`

### Task 3: Extended tests/test_commands.py
6 new test functions covering stretch files:

| Test | What it checks |
|------|---------------|
| `test_stretch_command_files_exist` | ghost.md and challenge.md both exist |
| `test_stretch_command_files_have_required_frontmatter` | name, description, argument-hint, disable-model-invocation: true |
| `test_stretch_command_files_have_no_graph_guard` | no_graph in both files |
| `test_ghost_md_references_get_annotations` | get_annotations in ghost.md |
| `test_challenge_md_has_evidence_sections` | both sections exist, supporting before contradicting |
| `test_challenge_md_has_anti_fabrication_guard` | do NOT fabricate in challenge.md |

## Deviations from Plan

None — plan executed exactly as written. All task content came from the plan verbatim.

## Known Stubs

None. Both command files are complete prompts with no placeholder text or TODO markers.

## Threat Flags

No new network endpoints, auth paths, file access patterns, or schema changes introduced. The command files are static markdown prompts. Security surface:
- T-11-07-01: `$ARGUMENTS` sanitized server-side by `sanitize_label()` in `query_graph` — no new mitigation needed
- T-11-07-02: `peer_id="self"` sentinel + anti-impersonation note in ghost.md
- T-11-07-03: Accepted — annotations authored by user, echoed back to user only
- T-11-07-04: `do NOT fabricate` guard in challenge.md, tested by `test_challenge_md_has_anti_fabrication_guard`

## Self-Check

(Populated after tasks complete)
