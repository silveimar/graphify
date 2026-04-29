---
phase: 36-migration-guide-skill-alignment-regression-sweep
plan: 03
subsystem: documentation
tags: [obsidian, migration, skill, pytest, contract-tests]

requires:
  - phase: 36-migration-guide-skill-alignment-regression-sweep
    provides: migration guide and CLI wording from Plan 36-02
provides:
  - exact v1.8 Obsidian phrase contract tests for packaged skill variants
  - shared v1.8 Obsidian behavior wording across all shipped graphify skill files
  - targeted stale `_COMMUNITY_*` generated-output claim guard
affects: [migration-guide, skill-alignment, release-packaging]

tech-stack:
  added: []
  patterns:
    - phrase-contract tests over packaged Markdown skill variants
    - shared skill wording block inserted near top-level usage guidance

key-files:
  created:
    - .planning/phases/36-migration-guide-skill-alignment-regression-sweep/36-03-SUMMARY.md
  modified:
    - tests/test_skill_files.py
    - graphify/skill.md
    - graphify/skill-codex.md
    - graphify/skill-opencode.md
    - graphify/skill-aider.md
    - graphify/skill-copilot.md
    - graphify/skill-claw.md
    - graphify/skill-windows.md
    - graphify/skill-droid.md
    - graphify/skill-trae.md

key-decisions:
  - "Skill contract drift is guarded with exact required phrases and targeted forbidden stale-claim phrases rather than full-file snapshots."
  - "The shared skill wording distinguishes lower-level `--obsidian` export from reviewed preview-first `update-vault` existing-vault migration/update."
  - "Legacy `_COMMUNITY_*` wording remains allowed only when describing reviewed legacy archive behavior, not generated v1.8 output."

patterns-established:
  - "Use `REQUIRED_V18_OBSIDIAN_PHRASES` and `FORBIDDEN_V18_OBSIDIAN_PHRASES` for future skill behavior drift tests."
  - "Place safety-critical Obsidian migration wording near each skill file's usage section so installed agents see it early."

requirements-completed: [VER-02]

duration: 6min
completed: 2026-04-29
---

# Phase 36 Plan 03: Platform Skill Variant Alignment Summary

**Packaged graphify skill variants now share one tested v1.8 Obsidian contract for MOC-only output, preview-first `update-vault`, backup-before-apply, archive evidence, and no destructive deletion.**

## Performance

- **Duration:** 6 min
- **Started:** 2026-04-29T07:48:31Z
- **Completed:** 2026-04-29T07:54:18Z
- **Tasks:** 2
- **Files modified:** 10

## Accomplishments

- Added skill drift tests requiring the exact v1.8 Obsidian phrases across `skill.md` and all platform variants enumerated by `PLATFORM_VARIANTS`.
- Added targeted forbidden-phrase coverage for stale `_COMMUNITY_*` generated-output claims while leaving legitimate legacy review/archive wording legal.
- Updated all nine packaged graphify skill variants with the same v1.8 behavior block, including `MOC-only community output`, `Graphify-owned v1.8 subtree`, `preview-first update-vault`, `Back up the target vault before apply`, `graphify-out/migrations/archive/`, and `no destructive deletion`.

## Task Commits

1. **Task 1 RED: Add required and forbidden skill phrase tests** - `5891a13` (test)
2. **Task 2 GREEN: Update all shipped graphify skill variants** - `82c948b` (feat)

## Files Created/Modified

- `tests/test_skill_files.py` - Added `REQUIRED_V18_OBSIDIAN_PHRASES`, `FORBIDDEN_V18_OBSIDIAN_PHRASES`, and all-variant contract tests.
- `graphify/skill.md` - Added shared v1.8 Obsidian behavior wording for the primary skill.
- `graphify/skill-codex.md` - Added shared v1.8 Obsidian behavior wording for Codex.
- `graphify/skill-opencode.md` - Added shared v1.8 Obsidian behavior wording for OpenCode.
- `graphify/skill-aider.md` - Added shared v1.8 Obsidian behavior wording for Aider.
- `graphify/skill-copilot.md` - Added shared v1.8 Obsidian behavior wording for Copilot.
- `graphify/skill-claw.md` - Added shared v1.8 Obsidian behavior wording for OpenClaw.
- `graphify/skill-windows.md` - Added shared v1.8 Obsidian behavior wording for Windows.
- `graphify/skill-droid.md` - Added shared v1.8 Obsidian behavior wording for Factory Droid.
- `graphify/skill-trae.md` - Added shared v1.8 Obsidian behavior wording for Trae.
- `.planning/phases/36-migration-guide-skill-alignment-regression-sweep/36-03-SUMMARY.md` - Captures execution outcome and verification evidence.

## Decisions Made

- Exact phrase constants are intentionally small and contract-focused; this avoids brittle snapshots of large platform skill files.
- Forbidden stale wording targets generated-output claims only, so skill text can still explain that legacy `_COMMUNITY_*` files are reviewed and archived after apply.
- The shared block uses the same canonical example as the migration guide: `graphify update-vault --input work-vault/raw --vault ls-vault`.

## Deviations from Plan

### Auto-fixed Issues

None - plan executed exactly as written.

**Total deviations:** 0 auto-fixed.
**Impact on plan:** Plan scope was preserved.

## TDD Gate Compliance

- Task 1 RED failed as expected because `skill.md` did not yet contain any required v1.8 Obsidian phrases.
- Task 2 GREEN passed after all shipped skill variants received the shared behavior block.

## Issues Encountered

- The git hook prints ImageMagick `import` help before graph rebuilds; commits still completed successfully with normal hooks.
- Tracked skill files under `graphify/` were staged with `git add -f` because the repository ignore rules otherwise make plain `git add graphify/...` unreliable.

## Known Stubs

None. Stub-pattern scan found only existing documentation references to template placeholders, not placeholder data or UI stubs introduced by this plan.

## Threat Flags

None. This plan changed Markdown skill guidance and tests only; it introduced no new endpoint, auth path, schema, network, or filesystem trust boundary beyond the skill-text behavior covered by the plan threat model.

## Verification

- `pytest tests/test_skill_files.py -q` after RED - 1 failed, 4 passed as expected.
- `pytest tests/test_skill_files.py -q` after Task 2 - 5 passed.
- Exact phrase checks for `preview-first update-vault`, `graphify-out/migrations/archive/`, `REQUIRED_V18_OBSIDIAN_PHRASES`, and `FORBIDDEN_V18_OBSIDIAN_PHRASES` passed with `rg`.
- `pytest tests/test_skill_files.py -q && pytest tests/ -q` - 5 passed, then 1883 passed, 1 xfailed, 8 warnings.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

Ready for Plan 36-04 to add sanitizer coverage matrix/security evidence and close the final Phase 36 regression gate.

## Self-Check: PASSED

- Summary file exists at `.planning/phases/36-migration-guide-skill-alignment-regression-sweep/36-03-SUMMARY.md`.
- Task commits exist in `git log --oneline --all`: `5891a13`, `82c948b`.
- Focused and full verification commands passed.

---
*Phase: 36-migration-guide-skill-alignment-regression-sweep*
*Completed: 2026-04-29*
