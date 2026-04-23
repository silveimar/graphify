---
phase: 14-obsidian-thinking-commands
plan: 05
subsystem: commands
tags: [obsidian, command, wayfind, connect-topics, trust-boundary, tdd]
requires: [14-00, 14-01, 14-02]
provides:
  - graphify-wayfind-command
  - wayfind-moc-root-heuristic
  - cross-command-trust-boundary-invariant
affects:
  - graphify/commands/graphify-wayfind.md
  - tests/test_commands.py
tech-stack:
  added: []
  patterns:
    - "skill-orchestrated markdown (no new Python) — MCP dispatch only"
    - "D-02 envelope status-branch pattern (shared with ask/argue/connect/moc)"
    - "D-05 MOC-root heuristic: get_community(0) — Leiden re-indexes largest to id 0"
    - "cross-command grep-assertion invariant test (forbidden-pattern denylist across all P1 write commands)"
key-files:
  created:
    - graphify/commands/graphify-wayfind.md
    - .planning/phases/14-obsidian-thinking-commands/14-05-SUMMARY.md
  modified:
    - tests/test_commands.py
decisions:
  - "MOC-root heuristic resolves via get_community(0) directly — graphify/cluster.py re-indexes Leiden output so community 0 is always the largest, making the tie-break degenerate (deterministic by construction, no need for a second get_community call)."
  - "Cross-command trust-boundary invariant codified at test level, not runtime — test_trust_boundary_invariant_all_p1 iterates {graphify-moc, graphify-wayfind} and grep-denies direct-write primitives. Any future P1 write command must be added to the allow-list AND pass the denylist; read-only commands (/graphify-related, /graphify-orphan) are intentionally excluded."
  - "Wayfind note uses folder_mapping.wayfind with fallback to `wayfind/` — stays profile-driven but degrades gracefully when the active vault profile lacks a wayfind slot (consistent with Plan 02 moc fallback pattern)."
metrics:
  duration_seconds: 180
  tasks_completed: 2
  files_modified: 2
  files_created: 1
  completed_date: 2026-04-22
requirements_completed:
  - OBSCMD-06
  - OBSCMD-08
threat_mitigations:
  - TM-14-01
---

# Phase 14 Plan 05: `/graphify-wayfind` Command Summary

**One-liner:** Shipped `/graphify-wayfind <topic>` as a pure skill-orchestrated markdown file (`graphify/commands/graphify-wayfind.md`) that composes `get_community(0)` (D-05 largest-community MOC-root heuristic) → `connect_topics` (shortest path) → `propose_vault_note` (staged breadcrumb), and codifies the Phase 14 cross-command trust-boundary invariant (`test_trust_boundary_invariant_all_p1`) that grep-denies direct-write primitives across every P1 write command.

## What Shipped

- **`graphify/commands/graphify-wayfind.md`** (NEW, 76 lines)
  - Frontmatter: `name: graphify-wayfind`, `target: obsidian`, `disable-model-invocation: true`, `argument-hint: <topic>`.
  - Single-`$ARGUMENTS` shape — target topic as free-text label or node id.
  - Step 1: `get_community(community_id=0)` resolves MOC root via `meta.top_labels[0]`.
  - Step 2: `connect_topics(topic_a=moc_root_label, topic_b=$ARGUMENTS, budget=500)` computes shortest path.
  - Step 3: renders breadcrumb (wikilink chain + full chain list) and stages via `propose_vault_note` with `note_type: "wayfind"` and `suggested_folder: profile.folder_mapping.wayfind` (falls back to `wayfind/`).
  - Status branches for `no_graph`, `community_not_found`, `entity_not_found`, `no_path`, `ok`.
  - Trust-boundary suffix: "do NOT write to the vault yourself."
- **`tests/test_commands.py`** (+39 lines)
  - `test_wayfind_contract` — asserts file exists, frontmatter fields, body references `connect_topics`, `get_community`, `$ARGUMENTS`.
  - `test_trust_boundary_invariant_all_p1` — iterates `{graphify-moc, graphify-wayfind}`, asserts each contains `propose_vault_note` AND grep-denies `Path.write_text`, `write_note_directly`, `open('w')`. Read-only commands (`/graphify-related`, `/graphify-orphan`) intentionally excluded from the allow-list.

## Commits

| Task | Type | Hash      | Message |
| ---- | ---- | --------- | ------- |
| 1    | test | `9e9f140` | `test(14-05): add failing /graphify-wayfind contract + trust-boundary invariant tests` |
| 2    | feat | `87158a4` | `feat(14-05): add /graphify-wayfind command (OBSCMD-06, OBSCMD-08)` |

## Verification

- `pytest tests/test_commands.py::test_wayfind_contract tests/test_commands.py::test_trust_boundary_invariant_all_p1 -q` → **2 passed**
- `pytest tests/ -q` → **1430 passed, 2 warnings** (baseline 1428 + 2 new; 0 regressions)
- `grep -c "^target: obsidian$" graphify/commands/graphify-wayfind.md` → **1**
- `grep -c "connect_topics\|get_community\|propose_vault_note\|\$ARGUMENTS" graphify/commands/graphify-wayfind.md` → **7** (≥ required 4)
- `grep -cE "Path\\.write_text|write_note_directly|open\\(.*['\"]w['\"]" graphify/commands/graphify-wayfind.md` → **0**
- `pytest tests/test_commands.py::test_graphify_prefix_enforced -q` → **1 passed** (file name `graphify-wayfind.md` satisfies OBSCMD-07 prefix invariant from Plan 01)
- Cross-command confirmation: `test_trust_boundary_invariant_all_p1` passes for BOTH `graphify-moc.md` (shipped in Plan 02) and `graphify-wayfind.md` (this plan).

## Success Criteria

- [x] `/graphify-wayfind` command file exists with `target: obsidian`
- [x] MOC-root resolved via `get_community(0)` (largest-community heuristic per D-05)
- [x] `connect_topics` used for shortest path
- [x] `propose_vault_note` used as sole write surface
- [x] `test_wayfind_contract` + `test_trust_boundary_invariant_all_p1` green
- [x] Full `pytest tests/ -q` green (1430 passed; entire Phase 14 Wave 2 regression-clean)

## Threat Mitigations

- **TM-14-01 (Vault auto-write bypass):** Mitigated. Skill body ends with explicit "do NOT write to the vault yourself" directive and routes 100% of vault writes through `propose_vault_note` + user `graphify approve`. `test_trust_boundary_invariant_all_p1` grep-denies direct-write primitives (`Path.write_text`, `write_note_directly`, `open('w')`) across every P1 write command in the allow-list — any future regression that adds a direct-write helper to `graphify-moc.md` or `graphify-wayfind.md` fails CI immediately.
- **T-14-05-01 (DoS via degenerate single-community graphs):** Mitigated. Skill branches on `status == community_not_found` and emits a graceful stop message.
- **T-14-05-02 (Spoofing via `$ARGUMENTS` as target topic):** Mitigated. `connect_topics` returns `entity_not_found` when the topic doesn't match any graph node — skill renders a friendly message; no `propose_vault_note` call fires on unresolved topics.

## Deviations from Plan

None — plan executed exactly as written.

## TDD Gate Compliance

- RED gate: `test(14-05): add failing /graphify-wayfind contract + trust-boundary invariant tests` — commit `9e9f140` (both tests fail: `AssertionError: graphify-wayfind.md missing`) ✓
- GREEN gate: `feat(14-05): add /graphify-wayfind command (OBSCMD-06, OBSCMD-08)` — commit `87158a4` (both tests green, full suite 1430 passed) ✓
- REFACTOR gate: not needed; the skill file is minimal and the GREEN commit is the final shape.

## Known Stubs

None. `connect_topics`, `get_community`, and `propose_vault_note` are all pre-existing MCP tools; `folder_mapping.wayfind` falls back to `wayfind/` when absent from the active profile, so the command produces a fully-realized breadcrumb proposal with or without user profile configuration.

## Self-Check: PASSED

- FOUND: `graphify/commands/graphify-wayfind.md` (76 lines, frontmatter + body)
- FOUND: `tests/test_commands.py::test_wayfind_contract`
- FOUND: `tests/test_commands.py::test_trust_boundary_invariant_all_p1`
- FOUND: commit `9e9f140` in `git log`
- FOUND: commit `87158a4` in `git log`
- FOUND: `pytest tests/ -q` → 1430 passed
