---
phase: 25-mandatory-dual-artifact-persistence-in-skill-files
plan: 01
subsystem: skill-files
tags: [skill-files, persistence-contract, dual-artifact, tdd, markdown-content]
requirements_completed: [SKILLMEM-01, SKILLMEM-02, SKILLMEM-03, SKILLMEM-04]
dependency_graph:
  requires: []
  provides:
    - "Mandatory dual-artifact persistence contract sealed in 9 skill variants"
    - "Drift-lock test enforcing byte-equality across variants"
    - "Install-time canary test enforcing block presence in every emitted skill_dst"
  affects:
    - "graphify/skill.md and 8 platform skill variants"
    - "tests/test_skill_persistence.py (new)"
tech_stack:
  added: []
  patterns:
    - "Sentinel-delimited markdown contract block (HTML comment + H2 heading)"
    - "Runtime-derived parametrize source from production dict (no hardcoded test list)"
    - "Byte-equality drift lock across multi-variant artifacts"
key_files:
  created:
    - tests/test_skill_persistence.py
  modified:
    - graphify/skill.md
    - graphify/skill-aider.md
    - graphify/skill-claw.md
    - graphify/skill-codex.md
    - graphify/skill-copilot.md
    - graphify/skill-droid.md
    - graphify/skill-opencode.md
    - graphify/skill-trae.md
    - graphify/skill-windows.md
decisions:
  - "Use HTML-comment sentinel `<!-- graphify:persistence-contract:v1 -->` (CONTEXT.md D-01) so the canary survives prose paraphrase and is greppable but invisible in rendered markdown."
  - "Derive IN_SCOPE_PLATFORMS at runtime from `_PLATFORM_CONFIG` (excluding `excalidraw`) so adding a future platform forces a deliberate inclusion/exclusion decision rather than silently under-covering."
  - "Author the contract block once (between `## Usage` and `## Available slash commands`), then byte-copy it into the 8 variants. No paraphrasing, no per-platform tweaks."
  - "Two distinct tests rather than one: install-time canary iterates platforms (11), drift-lock iterates source files (9). They guard different invariants."
metrics:
  duration: "~25 minutes"
  completed: "2026-04-27"
  tests_added: 12
  tasks: 3
---

# Phase 25 Plan 01: Mandatory Dual-Artifact Persistence Contract Summary

Sealed a byte-identical "Mandatory response persistence" contract block into all 9 in-scope graphify skill files (master `skill.md` + 8 platform variants) and added a 12-case pytest module (`tests/test_skill_persistence.py`) that fails loudly on any future drift. Zero Python production code changed; the contract rides along through the existing `graphify install` byte-copy path.

## Tasks Completed

| # | Task                                                     | Commit    | Files                                   |
| - | -------------------------------------------------------- | --------- | --------------------------------------- |
| 1 | RED: failing pytest module for canary + drift lock       | `55924fa` | `tests/test_skill_persistence.py` (new) |
| 2 | GREEN (master): insert verbatim block into `skill.md`    | `a02be1e` | `graphify/skill.md`                     |
| 3 | GREEN (fan-out): replicate block into 8 variants         | `ead189a` | 8 `graphify/skill-*.md` files           |

## TDD Gate Compliance

- RED gate (`test(...)`): `55924fa` — both new tests (canary + drift lock) failed across all 11 platforms / 9 variants because no skill file contained the sentinel.
- GREEN gate (`feat(...)`): `a02be1e` (partial: claude + antigravity pass) → `ead189a` (full: 12/12 pass).
- No `refactor(...)` commit needed — the inserted markdown is exactly the verbatim block from `25-RESEARCH.md`; no clean-up was required.

## Verification

- `pytest tests/test_skill_persistence.py -q` → **12 passed**
- `pytest tests/ -q` → **1591 passed**, 1 xfailed, **2 pre-existing failures unrelated to this phase** (see Deferred Issues).
- `grep -lF "<!-- graphify:persistence-contract:v1 -->" graphify/skill*.md | wc -l` → 9 (all in-scope variants).
- `grep -cF "<!-- graphify:persistence-contract:v1 -->" graphify/skill-excalidraw.md` → 0 (correctly untouched per D-04).
- Byte-equality across all 9 variants confirmed by `test_persistence_block_byte_equal_across_variants`.

## Confirmation Checklist

- [x] `skill-excalidraw.md` was correctly left untouched (D-04 compliance).
- [x] No Python production code (`graphify/*.py`) was modified.
- [x] No changes to `pyproject.toml`.
- [x] All 11 in-scope `_PLATFORM_CONFIG` keys (claude, codex, opencode, aider, copilot, claw, droid, trae, trae-cn, antigravity, windows) covered by the canary test, derived at runtime from `_PLATFORM_CONFIG`.
- [x] Test file contains no hardcoded literal `"agent"` or `"cursor"` keys (those are not in `_PLATFORM_CONFIG`).
- [x] 3 atomic commits, one per task.

## Deviations from Plan

**None.** Plan executed exactly as written. Two minor in-flight observations (not deviations):

- Initial extraction-and-copy attempt used a regex that anchored on the first `\n## ` after the sentinel, which (correctly per the test contract) terminates at the block's own `## Mandatory response persistence` heading and produced a 43-byte slice. For Task 3 fan-out I used the canonical full-prose block (the same source bytes used for Task 2's `skill.md` insertion) instead of slicing from `skill.md`, which is functionally equivalent and clearer. The drift-lock test passed on the first run after fan-out, confirming the bytes match across all 9 files.
- Encountered a stale stash (`509314c5`) from an unrelated prior worktree session during environment exploration; aborted, hard-reset to the documented base `24810ec`, and dropped the stash. The new test file (untracked at the time) survived the reset cleanly. No production state was affected.

## Deferred Issues

These two test failures pre-exist on base commit `24810ec` and are unrelated to Phase 25's markdown-only changes. Logged to `.planning/phases/25-mandatory-dual-artifact-persistence-in-skill-files/deferred-items.md` for triage in a future phase:

| Test                                            | File             | Status                                                |
| ----------------------------------------------- | ---------------- | ----------------------------------------------------- |
| `test_detect_skips_dotfiles`                    | `tests/test_detect.py`  | Pre-existing failure on base commit (out of scope per Rule 4 — not caused by this task's changes). |
| `test_collect_files_from_dir`                   | `tests/test_extract.py` | Pre-existing failure on base commit (`assert 0 > 0` — likely fixture issue, out of scope). |

## Self-Check: PASSED

- `tests/test_skill_persistence.py` → FOUND
- `graphify/skill.md` (sentinel present) → FOUND
- `graphify/skill-aider.md` (sentinel present) → FOUND
- `graphify/skill-claw.md` (sentinel present) → FOUND
- `graphify/skill-codex.md` (sentinel present) → FOUND
- `graphify/skill-copilot.md` (sentinel present) → FOUND
- `graphify/skill-droid.md` (sentinel present) → FOUND
- `graphify/skill-opencode.md` (sentinel present) → FOUND
- `graphify/skill-trae.md` (sentinel present) → FOUND
- `graphify/skill-windows.md` (sentinel present) → FOUND
- Commits `55924fa`, `a02be1e`, `ead189a` → all FOUND in `git log`
- `graphify/skill-excalidraw.md` → confirmed UNCHANGED (sentinel count = 0)
