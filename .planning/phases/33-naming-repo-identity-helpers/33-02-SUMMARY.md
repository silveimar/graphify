---
phase: 33-naming-repo-identity-helpers
plan: 02
subsystem: profile
tags: [repo-identity, profile-schema, naming, pytest, obsidian]

requires:
  - phase: 33-01
    provides: Wave 0 red tests for repo identity precedence and profile naming controls
provides:
  - Repo identity resolver with CLI, profile, git remote, and directory fallback sources
  - Profile defaults and validation for top-level repo.identity
  - Profile defaults and validation for naming.concept_names controls
affects: [phase-33, phase-34, phase-35, naming, profile, export]

tech-stack:
  added: []
  patterns:
    - Stdlib-only helper module using NamedTuple contracts and configparser git config parsing
    - Profile validation accumulator with dotted-path error strings

key-files:
  created:
    - graphify/naming.py
  modified:
    - graphify/profile.py

key-decisions:
  - "Repo identity resolution is centralized in graphify.naming with explicit source reporting before downstream CODE note rendering consumes it."
  - "Profile repo identity lives only under top-level repo.identity; naming.repo is rejected with guidance to avoid split configuration surfaces."
  - "Concept naming profile controls are limited to enabled, budget, and style; prompt templates remain out of the profile schema."

patterns-established:
  - "Explicit repo identities are validated as path-safe slugs and fall through with warnings when rejected."
  - "Git fallback reads .git/config with configparser instead of invoking git."

requirements-completed:
  - NAME-01
  - NAME-02
  - REPO-01
  - REPO-02
  - REPO-03

duration: 6min
completed: 2026-04-29
---

# Phase 33 Plan 02: Repo Identity Resolver and Profile Controls Summary

**Stdlib repo identity resolver plus vault profile schema for repo.identity and bounded concept naming controls**

## Performance

- **Duration:** 6 min
- **Started:** 2026-04-29T02:08:26Z
- **Completed:** 2026-04-29T02:13:57Z
- **Tasks:** 3
- **Files modified:** 2

## Accomplishments

- Added `graphify/naming.py` with `ResolvedRepoIdentity`, `normalize_repo_identity()`, and `resolve_repo_identity()` implementing CLI > profile > git remote > directory precedence.
- Extended `_DEFAULT_PROFILE` and `_VALID_TOP_LEVEL_KEYS` with `repo`, and added default `naming.concept_names` controls.
- Added collect-all validation for `repo.identity` and `naming.concept_names` without exposing prompt-template fields.

## Task Commits

Each implementation task was committed atomically:

1. **Task 1: Create repo identity resolver** - `300ef06` (feat)
2. **Task 2: Extend profile defaults and validation** - `9f370c1` (feat)
3. **Task 3: Verify helper and schema slice together** - no code changes; verification-only task

## Files Created/Modified

- `graphify/naming.py` - New repo identity helper module with source-reporting resolver and path-safe normalization.
- `graphify/profile.py` - Profile defaults and validation for `repo.identity` and `naming.concept_names`.

## Decisions Made

- Used `configparser` to parse `.git/config` directly and avoid shelling out to `git`.
- Rejected nested `naming.repo` with a targeted repo identity error instead of silently accepting a second schema location.
- Kept concept naming prompt templates out of the profile surface; only enablement, budget, and style hints are accepted.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Added import-compatible concept naming contracts**
- **Found during:** Task 1 (Create repo identity resolver)
- **Issue:** The existing Wave 0 `_naming_api()` helper imports `ConceptName` and `resolve_concept_names` before selecting repo identity symbols, so the focused repo identity tests could not import the new module unless those names existed.
- **Fix:** Added `ConceptName` and a reserved `resolve_concept_names()` entry point in `graphify/naming.py` so repo identity tests can import cleanly while Plan 03 owns concept naming behavior.
- **Files modified:** `graphify/naming.py`
- **Verification:** `python3 -m pytest tests/test_naming.py::test_repo_identity_cli_wins tests/test_naming.py::test_repo_identity_profile_wins tests/test_naming.py::test_repo_identity_fallback_git_remote_then_cwd -q`
- **Committed in:** `300ef06`

---

**Total deviations:** 1 auto-fixed (1 blocking)
**Impact on plan:** The added names unblock existing tests without wiring concept naming behavior ahead of Plan 03.

## Verification

- Initial RED gate for Task 1: focused repo identity tests failed with `ModuleNotFoundError: No module named 'graphify.naming'`.
- Initial RED gate for Task 2: focused profile tests failed on missing `repo` allowlist/default validation and missing `naming.concept_names` validation.
- Task 1 focused gate: `python3 -m pytest tests/test_naming.py::test_repo_identity_cli_wins tests/test_naming.py::test_repo_identity_profile_wins tests/test_naming.py::test_repo_identity_fallback_git_remote_then_cwd -q` -> 3 passed.
- Task 2 focused gate: `python3 -m pytest tests/test_profile.py::test_validate_profile_accepts_repo_identity tests/test_profile.py::test_validate_profile_rejects_invalid_repo_identity tests/test_profile.py::test_validate_profile_accepts_concept_naming_controls tests/test_profile.py::test_validate_profile_rejects_invalid_concept_naming_controls -q` -> 4 passed.
- Combined Plan 02 gate: `python3 -m pytest tests/test_naming.py::test_repo_identity_cli_wins tests/test_naming.py::test_repo_identity_profile_wins tests/test_naming.py::test_repo_identity_fallback_git_remote_then_cwd tests/test_profile.py::test_validate_profile_accepts_repo_identity tests/test_profile.py::test_validate_profile_rejects_invalid_repo_identity tests/test_profile.py::test_validate_profile_accepts_concept_naming_controls tests/test_profile.py::test_validate_profile_rejects_invalid_concept_naming_controls -q` -> 7 passed.
- Forward-import and forbidden-helper check scoped to new helper/test slice: `rg "from __future__ import annotations" graphify/naming.py graphify/profile.py && ! rg "subprocess|GitPython|dulwich|requests|urllib.request" graphify/naming.py tests/test_naming.py` -> passed.
- `ReadLints` on `graphify/naming.py` and `graphify/profile.py` -> no linter errors reported.

## Known Stubs

- `graphify/naming.py` contains a reserved `resolve_concept_names()` entry point that raises `NotImplementedError`. It exists only so the Wave 0 `_naming_api()` import helper can load repo identity symbols; Plan 03 implements concept naming behavior.

## Threat Flags

None. This plan handles user-controlled profile/CLI/git config identity strings with path-segment rejection, deterministic length caps, and source reporting. It does not introduce network endpoints, auth paths, schema migrations, or vault write sinks.

## Issues Encountered

- The repository's git hook rebuilt `graphify-out` after each commit and emitted an ImageMagick `import` usage banner before completing successfully.
- `graphify/*.py` is ignored by the user's global ignore rules, so new/modified Python files had to be staged individually with `git add -f`.
- The exact Task 3 forbidden-pattern command includes `tests/test_profile.py`, which already contains a pre-existing subprocess-based CLI helper unrelated to this plan. The implementation slice itself (`graphify/naming.py`, `tests/test_naming.py`) has no subprocess/network matches.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

Plan 03 can replace the reserved concept naming entry point with cache-backed LLM naming, deterministic fallback titles, provenance, and unsafe-title rejection. Plan 04 can then thread repo identity and concept names into CLI/export surfaces.

## Self-Check: PASSED

- Found summary file at `.planning/phases/33-naming-repo-identity-helpers/33-02-SUMMARY.md`.
- Found created helper file at `graphify/naming.py`.
- Verified task commits exist with `git cat-file`: `300ef06`, `9f370c1`.

---
*Phase: 33-naming-repo-identity-helpers*
*Completed: 2026-04-29*
