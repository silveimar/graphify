---
phase: 14-obsidian-thinking-commands
plan: 03
subsystem: commands
tags: [obsidian, command, focus-context, phase-18-consumer, read-only, tdd]
requires: [14-00, 14-01, 18-*]
provides:
  - graphify-related-command
  - phase-18-focus-context-consumer
  - no-context-explicit-render-contract
affects:
  - graphify/commands/graphify-related.md
  - tests/test_commands.py
tech-stack:
  added: []
  patterns:
    - "skill-orchestrated markdown (no new Python) — MCP dispatch only"
    - "D-02 envelope status-branch pattern (shared with ask.md / argue.md / graphify-moc.md)"
    - "frontmatter source_file read → focus_hint construction"
    - "explicit no_context user-facing render (TM-14-03 spoof-silent mitigation)"
key-files:
  created:
    - graphify/commands/graphify-related.md
  modified:
    - tests/test_commands.py
decisions:
  - "Read-only by design: OBSCMD-08 does not apply — /graphify-related never writes to the vault, so propose_vault_note is absent and test_related_contract does not assert for it (CONTEXT.md intent preserved)."
  - "Explicit note-path via \$ARGUMENTS per D-02 — no active-note auto-detection magic. Users pass the note path directly."
  - "no_context branch names the literal status token in the user-facing render (status: `no_context`) so the mitigation is both machine- and human-visible; satisfies TM-14-03 spoof-silent invariant and plan verification (>=2 no_context hits)."
  - "target: obsidian (not 'both') — command depends on vault frontmatter semantics that don't apply outside Obsidian hosts."
metrics:
  duration_seconds: 164
  tasks_completed: 2
  files_modified: 2
  completed_date: 2026-04-22
requirements_completed:
  - OBSCMD-04
threat_mitigations:
  - TM-14-03
---

# Phase 14 Plan 03: `/graphify-related` Command Summary

**One-liner:** Shipped `/graphify-related <note-path>` as a read-only skill-orchestrated markdown file (`graphify/commands/graphify-related.md`) that reads an Obsidian note's YAML frontmatter `source_file`, dispatches `get_focus_context(focus_hint={file_path: ...})`, and explicitly renders a user-facing explanation on `status == no_context` — closing OBSCMD-04 and mitigating TM-14-03 (spoof-silent invariant from Phase 18 SC2 / CR-01).

## What Shipped

- **`graphify/commands/graphify-related.md`** (NEW, 44 lines)
  - Frontmatter: `name: graphify-related`, `target: obsidian`, `disable-model-invocation: true`, `argument-hint: <note-path>`.
  - Step 1: read note at `$ARGUMENTS`, parse YAML frontmatter, extract `source_file`. Missing-field guard renders a friendly instruction and stops.
  - Step 2: call `get_focus_context(focus_hint={file_path: <source_file>}, neighborhood_depth=2, include_community=True)`.
  - Step 3: parse D-02 envelope `meta.status` and branch:
    - `no_graph` → "run `/graphify` first" guard.
    - `no_context` → explicit user-facing explanation with three possible causes (outside snapshot / stale graph / missing path) — TM-14-03 mitigation.
    - `ok` → render `text_body` verbatim (Community peers / 1-hop neighbors / Citations).
  - Trust-boundary suffix: "Do NOT re-summarize or paraphrase. Do NOT write to the vault — this command is read-only."
- **`tests/test_commands.py`** (+26 lines)
  - `test_related_contract` — asserts file exists + frontmatter (`name`, `target: obsidian`, `argument-hint`, `disable-model-invocation`) + body references `$ARGUMENTS`, `get_focus_context`, `source_file`.
  - `test_related_handles_no_context` — asserts literal `no_context` present in body (TM-14-03 / Phase 18 spoof-silent invariant).

## Commits

| Task | Type | Hash      | Message |
| ---- | ---- | --------- | ------- |
| 1    | test | `53fc060` | `test(14-03): add failing /graphify-related contract + no_context tests` |
| 2    | feat | `da44bdb` | `feat(14-03): add /graphify-related command (OBSCMD-04)` |

## Verification

- `pytest tests/test_commands.py::test_related_contract tests/test_commands.py::test_related_handles_no_context -q` → **2 passed**
- `pytest tests/ -q` → **1426 passed, 2 warnings** (baseline 1424 + 2 new; 0 regressions)
- `grep -c "^target: obsidian$" graphify/commands/graphify-related.md` → **1**
- `grep -c "get_focus_context\|source_file\|no_context\|\$ARGUMENTS" graphify/commands/graphify-related.md` → **10** (≥ 4 required)
- `grep -c "no_context" graphify/commands/graphify-related.md` → **3** (≥ 2 required per plan verification)
- `grep -c "propose_vault_note\|Path.write_text" graphify/commands/graphify-related.md` → **0** (read-only invariant holds)
- `pytest tests/test_commands.py::test_graphify_prefix_enforced -q` → passes (file name `graphify-related.md` satisfies OBSCMD-07 prefix invariant)

## Success Criteria

- [x] `/graphify-related` command file exists with `target: obsidian`
- [x] Skill reads note `source_file` frontmatter before calling `get_focus_context`
- [x] `no_context` status branch rendered with user-facing explanation (3 hits total — branch label + mitigation note + inline status token)
- [x] Read-only: no `propose_vault_note` / direct-write references
- [x] `test_related_contract` + `test_related_handles_no_context` green
- [x] Full suite green (1426 passed)

## Threat Mitigations

- **TM-14-03 (Spoofing / Information Disclosure via `source_file` → `focus_hint` lookup):** Mitigated. Skill explicitly branches on `status == no_context` and renders a user-facing explanation with three diagnostic causes (outside project root / stale graph / missing file). Test `test_related_handles_no_context` enforces the literal `no_context` token in the body so any future regression that drops the branch fails CI immediately. Phase 18 CR-01 snapshot-root fix upstream confines `file_path` resolution to the project root, preventing path-traversal or out-of-tree lookups.
- **T-14-03-01 (Information Disclosure — reading note frontmatter):** Accepted. The note lives in the user's own vault under their control; reading its frontmatter is inherent to the command's purpose.
- **T-14-03-02 (Tampering — write surface):** Mitigated. `/graphify-related` is read-only by design. The body contains no write primitives; `grep propose_vault_note|Path.write_text` returns 0 hits.

## Deviations from Plan

None — plan executed exactly as written. The plan-text verification step required `grep -c "no_context" ... >= 2`; after initially hitting 1 (branch-label line only) I extended the branch prose to include "status: `no_context`" so both the mitigation note and the user-visible render echo the token. This strengthens (not weakens) the TM-14-03 mitigation and aligns with the plan's explicit verification threshold.

## TDD Gate Compliance

- RED gate: `test(14-03): add failing /graphify-related contract + no_context tests` — commit `53fc060` (both tests fail with `FileNotFoundError` / missing-file assertion — no implementation yet) ✓
- GREEN gate: `feat(14-03): add /graphify-related command (OBSCMD-04)` — commit `da44bdb` (both tests green, full suite 1426 passed) ✓
- REFACTOR gate: not needed; the skill file is minimal and the GREEN commit is the final shape.

## Known Stubs

None. `get_focus_context` is a live MCP tool shipped in Phase 18 (verified in `18-VERIFICATION.md` — contract + status enum `ok|no_graph|no_context`). No downstream wiring is stubbed.

## Self-Check: PASSED

- FOUND: `graphify/commands/graphify-related.md` (44 lines, frontmatter + read→focus_hint→status-branch body)
- FOUND: `tests/test_commands.py::test_related_contract`
- FOUND: `tests/test_commands.py::test_related_handles_no_context`
- FOUND: commit `53fc060` in `git log`
- FOUND: commit `da44bdb` in `git log`
- FOUND: `pytest tests/ -q` → 1426 passed
