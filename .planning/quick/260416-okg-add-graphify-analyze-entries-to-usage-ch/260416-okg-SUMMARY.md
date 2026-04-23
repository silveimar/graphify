---
quick_task: 260416-okg
title: add /graphify analyze to skill Usage cheat-sheet
subsystem: skill-docs
tags: [skill, docs, usage-cheatsheet, analyze]
key-files:
  modified:
    - graphify/skill.md
    - graphify/skill-codex.md
    - graphify/skill-opencode.md
    - graphify/skill-claw.md
    - graphify/skill-droid.md
    - graphify/skill-trae.md
    - graphify/skill-aider.md
    - graphify/skill-copilot.md
    - graphify/skill-windows.md
metrics:
  files_edited: 9
  files_skipped: 0
  lines_inserted: 27
  lines_deleted: 0
  commit: 058152b
completed: 2026-04-16
---

# Quick Task 260416-okg: add /graphify analyze to skill Usage cheat-sheet Summary

Inserted the 3-line `/graphify analyze` block (full tournament, subset-lens, single-lens) into the top-of-file `## Usage` code-block of all 9 graphify skill variants in `graphify/`, immediately after the `/graphify explain "SwinTransformer"` anchor line. All 9 target files had the anchor; none were skipped.

## Per-file status

| File | had_anchor | edited | new `/graphify analyze` count |
| --- | --- | --- | --- |
| graphify/skill.md | yes | yes | 6 (3 pre-existing orchestration refs + 3 new Usage lines) |
| graphify/skill-codex.md | yes | yes | 3 |
| graphify/skill-opencode.md | yes | yes | 3 |
| graphify/skill-claw.md | yes | yes | 3 |
| graphify/skill-droid.md | yes | yes | 3 |
| graphify/skill-trae.md | yes | yes | 3 |
| graphify/skill-aider.md | yes | yes | 3 |
| graphify/skill-copilot.md | yes | yes | 3 |
| graphify/skill-windows.md | yes | yes | 3 |

Expected per-file delta was exactly +3 new `/graphify analyze` occurrences; all 9 files met that delta (`skill.md` went 3 -> 6, all others 0 -> 3). Total: 30 occurrences across 9 files, up from 3 before the commit.

## Commit

- Hash: `058152b` (`058152b78fc92cfd6b92466d3a7b394b11a9abce`)
- Message: `docs(260416-okg): add /graphify analyze to skill Usage cheat-sheet`
- Diff: 9 files changed, 27 insertions (+), 0 deletions (-)

## Deviations from Plan

None - plan executed exactly as written. All 9 files had the anchor, no SKIP branch was triggered, no deviation rules fired.

## Constraint compliance

- Did NOT touch `graphify/__main__.py`, `graphify/analyze.py`, or the `## For /graphify analyze` orchestration section further down in `skill.md`.
- Did NOT run `graphify claude install` or any install command.
- Did NOT modify anything under `~/.claude/skills/graphify/`.
- Did NOT stage `.planning/config.json`, `.cursor/`, or `.planning/quick/` (unrelated / orchestrator-owned).
- Did NOT stage PLAN.md / SUMMARY.md / STATE.md / ROADMAP.md in this commit; orchestrator handles planning artifacts.
- Trailing newline behavior preserved on all 9 files (insertion occurred strictly between the existing anchor line and the closing ``` fence, no blank lines added/removed).

## Next step reminder for the user

Run `graphify claude install` (and equivalent for other platforms you use) to propagate the updated skill to `~/.claude/skills/graphify/SKILL.md` etc.

## Self-Check: PASSED

- All 9 modified files exist: confirmed via `git log -1 --stat` (each shown with `3 +++`).
- Commit `058152b` exists: confirmed via `git log -1`.
- Per-file `/graphify analyze` counts match expectations (see per-file table above).
- No unintentional deletions: `git log -1 --stat` reports 0 deletions.
- Excluded files untouched: `.planning/config.json`, `.cursor/`, `.planning/quick/` remain in working-tree/untracked state unchanged.
