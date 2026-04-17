---
phase: 11-narrative-mode-slash-commands
plan: 05
subsystem: skill-files
tags: [skill, discoverability, phase-11]
dependency_graph:
  requires: [11-03]
  provides: [skill.md discoverability section, 8 platform variant discoverability sections, tests/test_skill_files.py]
  affects: [graphify/skill.md, graphify/skill-codex.md, graphify/skill-opencode.md, graphify/skill-aider.md, graphify/skill-copilot.md, graphify/skill-claw.md, graphify/skill-droid.md, graphify/skill-trae.md, graphify/skill-windows.md, tests/test_skill_files.py]
tech_stack:
  added: []
  patterns: [skill-file-injection, self-contained-test, parallel-wave-independence]
key_files:
  created:
    - tests/test_skill_files.py
  modified:
    - graphify/skill.md
    - graphify/skill-codex.md
    - graphify/skill-opencode.md
    - graphify/skill-aider.md
    - graphify/skill-copilot.md
    - graphify/skill-claw.md
    - graphify/skill-droid.md
    - graphify/skill-trae.md
    - graphify/skill-windows.md
decisions:
  - "Section injected immediately after Usage code block (before ## What graphify is for) — consistent injection point across all 9 files"
  - "test_skill_files.py is self-contained — no import of tests/test_commands.py to avoid parallel-wave race (WARNING 1 fix)"
  - "Identical block across all 9 variants — test_skill_files_discoverability_section_is_consistent enforces no drift (T-11-05-02 mitigation)"
metrics:
  duration_minutes: 5
  tasks_completed: 3
  files_modified: 10
  completed_date: "2026-04-17"
requirements: [SLASH-01, SLASH-02, SLASH-03, SLASH-04, SLASH-05]
---

# Phase 11 Plan 05: Skill File Discoverability Section Summary

**One-liner:** "Available slash commands" section injected into all 9 skill file variants (Claude Code + 8 platforms) listing /context, /trace, /connect, /drift, /emerge — enforced by 3-test suite in tests/test_skill_files.py.

## What Was Built

### graphify/skill.md + 8 platform variants (modified)

A single new section added immediately after the `## Usage` code block in each skill file:

```markdown
## Available slash commands

After `graphify install`, these commands are available in Claude Code:
- `/context` — full graph-backed summary (god nodes, top communities, recent deltas)
- `/trace <entity>` — evolution of a named entity across snapshots
- `/connect <topic-a> <topic-b>` — shortest path + surprising bridges
- `/drift` — nodes trending across recent snapshots
- `/emerge` — new clusters formed since the last snapshot
```

The section is identical across all 9 files. Injection point: right after the closing ` ``` ` of the Usage block and before `## What graphify is for`. Each file received +9 lines (heading, blank line, 5 command bullets, 2 surrounding blank lines).

**Files modified:** skill.md, skill-codex.md, skill-opencode.md, skill-aider.md, skill-copilot.md, skill-claw.md, skill-droid.md, skill-trae.md, skill-windows.md

### tests/test_skill_files.py (new file)

Three tests:

| Test | What it enforces |
|------|-----------------|
| `test_primary_skill_file_lists_available_commands` | skill.md contains heading + all 5 command references |
| `test_platform_variant_skill_files_list_available_commands` | All 8 variants contain heading + all 5 command references |
| `test_skill_files_discoverability_section_is_consistent` | Heading text is identical across all 9 files — drift guard |

All 3 tests pass. File is fully self-contained (imports only `pathlib` and `graphify`) — no dependency on `tests/test_commands.py` (plan-checker WARNING 1 fix preserved).

## Deviations from Plan

None — plan executed exactly as written. All 9 files received the identical block at the correct injection point. The TDD task went straight to GREEN because Tasks 1 and 2 had already implemented the sections before Task 3 ran — expected behavior per plan's task ordering note.

## Known Stubs

None. All 5 command references are real commands shipped in plan 11-04 (graphify/commands/). The discoverability section contains no placeholder text or TODO markers.

## Threat Flags

No new network endpoints, auth paths, file access patterns, or schema changes introduced. Static documentation content only. T-11-05-02 (skill file drift) is mitigated by `test_skill_files_discoverability_section_is_consistent`.

## Self-Check: PASSED

Files exist:
- graphify/skill.md — FOUND, contains `## Available slash commands`
- graphify/skill-codex.md — FOUND, contains `## Available slash commands`
- graphify/skill-opencode.md — FOUND, contains `## Available slash commands`
- graphify/skill-aider.md — FOUND, contains `## Available slash commands`
- graphify/skill-copilot.md — FOUND, contains `## Available slash commands`
- graphify/skill-claw.md — FOUND, contains `## Available slash commands`
- graphify/skill-droid.md — FOUND, contains `## Available slash commands`
- graphify/skill-trae.md — FOUND, contains `## Available slash commands`
- graphify/skill-windows.md — FOUND, contains `## Available slash commands`
- tests/test_skill_files.py — FOUND

Commits verified:
- b9cb6af — feat(11-05): inject Available slash commands section into skill.md
- ede460f — feat(11-05): inject Available slash commands section into 8 platform variant skill files
- f328a56 — test(11-05): add test_skill_files.py asserting discoverability section across all 9 skill variants

pytest tests/test_skill_files.py -q: 3 passed
