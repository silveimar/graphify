---
phase: 36-migration-guide-skill-alignment-regression-sweep
fixed_at: 2026-04-29T08:18:00Z
review_path: .planning/phases/36-migration-guide-skill-alignment-regression-sweep/36-REVIEW.md
iteration: 1
findings_in_scope: 4
fixed: 4
skipped: 0
status: all_fixed
---

# Phase 36: Code Review Fix Report

**Fixed at:** 2026-04-29T08:18:00Z
**Source review:** `.planning/phases/36-migration-guide-skill-alignment-regression-sweep/36-REVIEW.md`
**Iteration:** 1

**Summary:**
- Findings in scope: 4
- Fixed: 4
- Skipped: 0

## Fixed Issues

### BL-01: Reviewed plan id does not bind legacy note contents before archive

**Files modified:** `graphify/migration.py`, `tests/test_migration.py`
**Commit:** 2f4b5ab
**Applied fix:** Legacy scan and preview rows now include stable content hashes, legacy mappings carry the reviewed old-note hash, plan digests include both hash sources, and archive apply revalidates the current legacy note hash before moving.

### BL-02: Archive move can overwrite existing rollback evidence

**Files modified:** `graphify/migration.py`, `tests/test_migration.py`
**Commit:** 2f4b5ab
**Applied fix:** Archive preflight now rejects existing archive destinations before any legacy note is moved, with regression coverage proving earlier sources stay in place when a later destination collides.

### HI-01: Skill variants still advertise generated `_COMMUNITY_*` overview notes

**Files modified:** `graphify/skill.md`, `graphify/skill-codex.md`, `graphify/skill-opencode.md`, `graphify/skill-aider.md`, `graphify/skill-copilot.md`, `graphify/skill-claw.md`, `graphify/skill-windows.md`, `graphify/skill-droid.md`, `graphify/skill-trae.md`
**Commit:** 6ab2fed
**Applied fix:** Replaced the stale `_COMMUNITY_*` generated overview print line in every packaged skill variant with v1.8 MOC community-note wording.

### MD-01: Skill regression test misses the stale `_COMMUNITY_*` claim it was meant to prevent

**Files modified:** `tests/test_skill_files.py`
**Commit:** aab25a8
**Applied fix:** The stale-claim test now rejects semantic regex patterns for `_COMMUNITY_*` overview/dataview/print claims while preserving allowed legacy archive wording.

## Skipped Issues

None.

## Verification

- `python -c "import ast, pathlib; [ast.parse(pathlib.Path(p).read_text(encoding='utf-8')) for p in ['graphify/migration.py', 'tests/test_migration.py', 'tests/test_skill_files.py']]"`
- `pytest tests/test_migration.py tests/test_main_flags.py tests/test_skill_files.py -q`
- Result: 44 passed, 2 warnings.

---

_Fixed: 2026-04-29T08:18:00Z_
_Fixer: Claude (gsd-code-fixer)_
_Iteration: 1_
