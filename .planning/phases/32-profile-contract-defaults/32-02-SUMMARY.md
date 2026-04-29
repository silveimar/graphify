---
phase: 32-profile-contract-defaults
plan: 02
subsystem: profile-validation
tags: [v1.8, taxonomy, profile-contract, obsidian, validation]

# Dependency graph
requires:
  - phase: 32-profile-contract-defaults
    provides: corrected v1.8 planning contract wording from Plan 01
provides:
  - v1.8 taxonomy defaults rooted at Atlas/Sources/Graphify
  - Canonical mapping.min_community_size validation
  - Hard validation error for mapping.moc_threshold
  - Shared preflight warnings for deprecated community overview templates
affects: [graphify-profile, validate-profile-cli, obsidian-export-defaults, phase-33, phase-34, phase-35]

# Tech tracking
tech-stack:
  added: []
  patterns: [profile-contract-atomicity, taxonomy-derived-folder-mapping, shared-preflight-warnings]

key-files:
  created:
    - .planning/phases/32-profile-contract-defaults/32-02-SUMMARY.md
  modified:
    - graphify/profile.py
    - tests/test_profile.py

key-decisions:
  - "Resolved taxonomy into folder_mapping inside the profile layer so downstream mapping/export code can keep consuming the existing folder_mapping surface."
  - "Kept validate_profile() usable for partial schema unit checks, while validate_profile_preflight() and load_profile() enforce required v1.8 user-profile keys."
  - "Treated community overview templates as warning-level deprecated usage, not fatal validation errors."

patterns-established:
  - "Taxonomy path validation reuses the profile validator accumulator style and rejects absolute, home-relative, traversal, and non-string values."
  - "User-authored v1.8 profile required-key checks live beside preflight/load profile-file handling instead of turning every partial validate_profile() unit test into a full-profile fixture."

requirements-completed: [TAX-01, TAX-02, TAX-03, TAX-04, COMM-03, CLUST-01, CLUST-04]

# Metrics
duration: 5min
completed: 2026-04-29
---

# Phase 32 Plan 02: Profile Contract & Defaults Summary

**v1.8 profile defaults now resolve Obsidian note folders under `Atlas/Sources/Graphify/`, validate taxonomy and `mapping.min_community_size`, and warn on deprecated community overview output.**

## Performance

- **Duration:** 5 min
- **Started:** 2026-04-29T00:11:50Z
- **Completed:** 2026-04-29T00:17:05Z
- **Tasks:** 2
- **Files modified:** 3

## Accomplishments

- Added RED coverage for the v1.8 profile contract: taxonomy defaults, taxonomy atomicity, unsafe taxonomy folders, required user-profile keys, legacy `mapping.moc_threshold`, and community template deprecation warnings.
- Updated `graphify/profile.py` so `_DEFAULT_PROFILE`, `_VALID_TOP_LEVEL_KEYS`, `load_profile()`, `validate_profile()`, and `validate_profile_preflight()` share the v1.8 contract.
- Preserved the existing downstream `folder_mapping` integration surface by deriving folder mappings from `taxonomy.root` plus `taxonomy.folders.*`.

## Task Commits

Each task was committed atomically:

1. **Task 1: Add failing tests for v1.8 profile defaults and validation** - `e76bf1c` (test)
2. **Task 2: Implement the profile contract and shared preflight warnings** - `3c6d9fd` (feat)

## Files Created/Modified

- `graphify/profile.py` - Adds v1.8 taxonomy defaults, derived Graphify-owned folder mappings, required user-profile key checks, `mapping.min_community_size` validation, `mapping.moc_threshold` invalidation, and community overview deprecation warnings.
- `tests/test_profile.py` - Adds and updates unit/CLI coverage for the v1.8 profile contract.
- `.planning/phases/32-profile-contract-defaults/32-02-SUMMARY.md` - Records execution outcome and verification evidence.

## Decisions Made

- Resolved taxonomy into `folder_mapping` during profile loading/preflight so downstream code can adopt the new default paths without immediate mapping/export changes.
- Enforced required v1.8 keys for user-authored profile files through `load_profile()` and `validate_profile_preflight()`, while leaving `validate_profile()` useful for focused partial schema validation.
- Emitted warning-level findings for `community.md` and `community_templates` usage so renderer support remains intact while users get migration guidance toward MOC-only output.

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

- The first RED test run and one commit attempt hit transient shell fork/resource errors. Retrying the same scoped commands succeeded.
- The implementation commit initially stopped after staging because `git add` reported an ignore-rule warning for `graphify/profile.py`; the intended files were staged, verified with `git diff --cached --stat`, and committed successfully.
- The repo post-commit hook rebuilt the graph after commits and printed ImageMagick `import` help before completing; no generated files were left untracked.

## User Setup Required

None - no external service configuration required.

## Known Stubs

None. Stub scan found only existing empty-list/dict initializers and one pre-existing xfail placeholder comment in tests; no runtime UI/data stubs were introduced.

## Verification

- RED gate: `pytest tests/test_profile.py -q` failed before implementation with missing taxonomy, `min_community_size`, and deprecation-warning behavior.
- GREEN verification: `pytest tests/test_profile.py -q` passed with `180 passed, 1 xfailed`.
- CLI verification: `python -m graphify --validate-profile /tmp/nonexistent-vault` exited non-zero with `vault_dir does not exist`.
- Editor diagnostics: no linter errors for `graphify/profile.py` or `tests/test_profile.py`.

## TDD Gate Compliance

- RED commit present: `e76bf1c`
- GREEN commit present after RED: `3c6d9fd`
- Refactor commit: not needed

## Self-Check: PASSED

- Found `graphify/profile.py`.
- Found `tests/test_profile.py`.
- Found `.planning/phases/32-profile-contract-defaults/32-02-SUMMARY.md`.
- Found task commit `e76bf1c`.
- Found task commit `3c6d9fd`.

## Next Phase Readiness

Plan 03 can consume the shared preflight/profile contract and focus on doctor or downstream warning surfaces without redefining taxonomy defaults. Later mapping/export work should read `mapping.min_community_size` as canonical and treat `mapping.moc_threshold` as invalid.

---
*Phase: 32-profile-contract-defaults*
*Completed: 2026-04-29*
