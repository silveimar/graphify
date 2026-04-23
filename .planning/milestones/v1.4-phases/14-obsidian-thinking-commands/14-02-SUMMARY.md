---
phase: 14-obsidian-thinking-commands
plan: 02
subsystem: commands
tags: [obsidian, command, moc, trust-boundary, tdd]
requires: [14-00, 14-01]
provides:
  - graphify-moc-command
  - moc-trust-boundary-contract
  - profile-driven-moc-render
affects:
  - graphify/commands/graphify-moc.md
  - tests/test_commands.py
tech-stack:
  added: []
  patterns:
    - "skill-orchestrated markdown (no new Python) — MCP dispatch only"
    - "D-02 envelope status-branch pattern (shared with argue.md / ask.md)"
    - "trust-boundary grep-assertion test (forbidden-pattern denylist)"
key-files:
  created:
    - graphify/commands/graphify-moc.md
  modified:
    - tests/test_commands.py
decisions:
  - "Skill file is pure orchestration markdown — no Python module needed because all behavior composes existing MCP tools (get_community, load_profile, propose_vault_note)."
  - "Trust boundary is enforced at test time via grep denylist (Path.write_text, write_note_directly, open('w')) rather than runtime — consistent with Plan 01 prefix-enforcement pattern; fails loudly in CI if a future edit regresses TM-14-01."
  - "target: obsidian (not 'both') — MOC rendering is vault-specific; claude and windows are the only platforms with obsidian in supports, so the command lands only where it can actually execute against a vault."
metrics:
  duration_seconds: 187
  tasks_completed: 2
  files_modified: 2
  completed_date: 2026-04-22
requirements_completed:
  - OBSCMD-03
  - OBSCMD-08
threat_mitigations:
  - TM-14-01
---

# Phase 14 Plan 02: `/graphify-moc` Command Summary

**One-liner:** Shipped `/graphify-moc <community_id>` as a pure skill-orchestrated markdown file (`graphify/commands/graphify-moc.md`) that composes `get_community` → `load_profile` → `propose_vault_note`, enforcing the TM-14-01 trust boundary (no direct vault writes) via a test-time denylist of write patterns.

## What Shipped

- **`graphify/commands/graphify-moc.md`** (NEW, 56 lines)
  - Frontmatter: `name: graphify-moc`, `target: obsidian`, `disable-model-invocation: true`, `argument-hint: <community_id>`.
  - Arg parse: `$ARGUMENTS` validated as non-negative int before any MCP call.
  - MCP dispatch sequence: `get_community(community_id)` → D-02 envelope status branch → `load_profile(vault_path)` → render MOC body → `propose_vault_note(...)`.
  - Status branches for `no_graph`, `community_not_found`, `ok` — consistent with `ask.md` / `argue.md` pattern.
  - Profile fields consumed: `obsidian.frontmatter_template`, `folder_mapping.moc`, `obsidian.dataview.moc_query`.
  - Body sections: frontmatter (type: moc, community_id), title (top_labels[0] or fallback), Members (wikilinks capped at 25), Cohesion, Dataview, Related Communities.
  - Trust-boundary suffix: "Tell the user the proposal ID … do NOT write to the vault yourself."
- **`tests/test_commands.py`** (+32 lines)
  - `test_graphify_moc_frontmatter` — asserts file exists + frontmatter fields including `target: obsidian`.
  - `test_moc_trust_boundary_and_contract` — asserts body contains `get_community`, `load_profile`, `propose_vault_note`, `$ARGUMENTS`, AND grep-denylists `Path.write_text`, `write_note_directly`, `open('w')`.

## Commits

| Task | Type | Hash      | Message |
| ---- | ---- | --------- | ------- |
| 1    | test | `92c9d8f` | `test(14-02): add failing /graphify-moc frontmatter + trust-boundary tests` |
| 2    | feat | `b5589f5` | `feat(14-02): add /graphify-moc command (OBSCMD-03, OBSCMD-08)` |

## Verification

- `pytest tests/test_commands.py::test_graphify_moc_frontmatter tests/test_commands.py::test_moc_trust_boundary_and_contract -q` → **2 passed**
- `pytest tests/ -q` → **1424 passed, 2 warnings** (baseline 1422 + 2 new; 0 regressions)
- `grep -c "^target: obsidian$" graphify/commands/graphify-moc.md` → **1**
- `grep -c "get_community\|load_profile\|propose_vault_note\|\$ARGUMENTS" graphify/commands/graphify-moc.md` → **4** (≥ required 4)
- `grep -cE "Path\\.write_text|write_note_directly|open\\(.*['\"]w['\"]" graphify/commands/graphify-moc.md` → **0**
- `pytest tests/test_commands.py::test_graphify_prefix_enforced -q` → **1 passed** (file name `graphify-moc.md` satisfies OBSCMD-07 prefix invariant from Plan 01)

## Success Criteria

- [x] `/graphify-moc` command file exists with `target: obsidian`
- [x] Skill invokes `get_community`, `load_profile`, `propose_vault_note` (all three literal names present)
- [x] No direct-write helpers referenced (`Path.write_text`, `write_note_directly`, `open('w')` all absent)
- [x] `test_graphify_moc_frontmatter` + `test_moc_trust_boundary_and_contract` green
- [x] Full suite `pytest tests/ -q` green (1424 passed)

## Threat Mitigations

- **TM-14-01 (Vault auto-write bypass):** Mitigated. Skill body ends with explicit "do NOT write to the vault yourself" directive and routes 100% of vault writes through `propose_vault_note` + user `graphify approve`. `test_moc_trust_boundary_and_contract` grep-denylists direct-write patterns (`Path.write_text`, `write_note_directly`, `open('w')`), so any future regression that adds a direct-write helper fails CI immediately.
- **T-14-02-01 (Spoofing via `$ARGUMENTS`):** Mitigated. Skill validates `$ARGUMENTS` as non-negative integer before any MCP call; non-integer input short-circuits with a friendly error and no `get_community` dispatch.
- **T-14-02-02 (Information disclosure — community member rendering):** Accepted. Labels are already in the user's local graph; the 25-member cap prevents pathological expansion.

## Deviations from Plan

None — plan executed exactly as written.

## TDD Gate Compliance

- RED gate: `test(14-02): add failing /graphify-moc frontmatter + trust-boundary tests` — commit `92c9d8f` (both tests fail with `FileNotFoundError` — no implementation yet) ✓
- GREEN gate: `feat(14-02): add /graphify-moc command (OBSCMD-03, OBSCMD-08)` — commit `b5589f5` (both tests green, full suite 1424 passed) ✓
- REFACTOR gate: not needed; the skill file is minimal and the GREEN commit is the final shape.

## Known Stubs

None. Every field consumed from the profile (`obsidian.frontmatter_template`, `folder_mapping.moc`, `obsidian.dataview.moc_query`) exists in `_DEFAULT_PROFILE` (verified in `graphify/profile.py` during 14-00), so the command produces a fully-realized MOC even with no user `.graphify/profile.yaml` present. The MCP tools `get_community`, `load_profile`, `propose_vault_note` are all pre-existing (shipped earlier in v1.3 / v1.4).

## Self-Check: PASSED

- FOUND: `graphify/commands/graphify-moc.md` (56 lines, frontmatter + body)
- FOUND: `tests/test_commands.py` with `test_graphify_moc_frontmatter` and `test_moc_trust_boundary_and_contract`
- FOUND: commit `92c9d8f` in `git log`
- FOUND: commit `b5589f5` in `git log`
- FOUND: `pytest tests/ -q` → 1424 passed
