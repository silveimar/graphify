---
phase: 33-naming-repo-identity-helpers
plan: 01
subsystem: testing
tags: [pytest, naming, repo-identity, obsidian, cli]

requires:
  - phase: 32-output-taxonomy-cluster-quality
    provides: v1.8 output taxonomy and profile preflight contracts
provides:
  - Wave 0 pytest contract coverage for concept naming helpers
  - Wave 0 pytest contract coverage for repo identity precedence
  - Integration coverage for Obsidian MOC naming, template sanitization, and CLI flag parsing
affects: [phase-33, naming, profile, export, templates, cli]

tech-stack:
  added: []
  patterns:
    - Pure pytest fixtures using tmp_path, capsys, and monkeypatch
    - Red Wave 0 tests for future helper implementation

key-files:
  created:
    - tests/test_naming.py
  modified:
    - tests/test_profile.py
    - tests/test_export.py
    - tests/test_templates.py
    - tests/test_main_flags.py

key-decisions:
  - "Phase 33 Wave 0 intentionally commits red tests that define the helper contracts before graphify.naming exists."
  - "Repo identity tests lock CLI > profile > git remote > directory fallback precedence and stderr source reporting."
  - "Concept naming tests lock cached/fallback naming, provenance, dry-run sidecar safety, and unsafe generated-title rejection."

patterns-established:
  - "Naming helper tests import planned symbols lazily so pytest can collect all target test names before implementation exists."
  - "Integration tests assert downstream sinks rather than only helper return values."

requirements-completed:
  - NAME-01
  - NAME-02
  - NAME-03
  - NAME-04
  - NAME-05
  - REPO-01
  - REPO-02
  - REPO-03

duration: 6min
completed: 2026-04-29
---

# Phase 33 Plan 01: Wave 0 Naming Test Scaffold Summary

**Red pytest contract suite for cached concept names, deterministic fallbacks, repo identity precedence, MOC naming sinks, and CLI `--repo-identity` parsing**

## Performance

- **Duration:** 6 min
- **Started:** 2026-04-29T01:59:03Z
- **Completed:** 2026-04-29T02:05:19Z
- **Tasks:** 3
- **Files modified:** 5

## Accomplishments

- Added `tests/test_naming.py` with eight Phase 33 helper contract tests covering NAME-01..05 and REPO-01..03.
- Extended `tests/test_profile.py` with schema expectations for top-level `repo.identity` and `naming.concept_names`.
- Added downstream coverage in export, template, and CLI tests for MOC naming paths, dry-run sidecar safety, generated title sanitization, and repo identity flag precedence.

## Task Commits

Each task was committed atomically:

1. **Task 1: Add repo identity and concept naming unit tests** - `165c63e` (test)
2. **Task 2: Add profile schema tests for repo and naming controls** - `028cfdd` (test)
3. **Task 3: Add export, template, and CLI integration tests** - `11e6819` (test)

## Files Created/Modified

- `tests/test_naming.py` - New Wave 0 helper contract tests for concept naming and repo identity resolution.
- `tests/test_profile.py` - Added profile schema tests for `repo.identity` and `naming.concept_names`.
- `tests/test_export.py` - Added dry-run Obsidian export tests for resolved MOC names and naming sidecar absence.
- `tests/test_templates.py` - Added generated MOC title sanitization coverage across filename, tag, frontmatter, and injection sinks.
- `tests/test_main_flags.py` - Added CLI parsing expectations for `--repo-identity` on `run` and `--obsidian`.

## Decisions Made

- Phase 33 Plan 01 remains a validation scaffold only. No production helpers were added in this plan.
- The red state is intentional: missing `graphify.naming`, profile schema gaps, export naming integration, template sanitization, and CLI parsing are implementation targets for later Phase 33 plans.

## Deviations from Plan

None - plan executed exactly as written.

## Verification

- `python3 -m pytest tests/test_naming.py -q` -> expected red: 8 failures due to missing `graphify.naming`.
- Focused profile tests -> expected red: 3 failures, 1 pass until `repo` and `naming.concept_names` validation is implemented.
- Focused export/template/CLI tests -> expected red: 4 failures, 1 pass until naming integration, generated-title sanitization, and `--repo-identity` parsing are implemented.
- Combined focused Wave 0 command -> expected red: 15 failed, 2 passed.
- `ReadLints` on edited test files -> no linter errors reported.

## Known Stubs

None. Tests intentionally reference future production contracts, but no placeholder production code or UI-facing stub was added.

## Threat Flags

None. This plan only adds synthetic pytest fixtures under `tmp_path` and does not introduce new runtime endpoints, file-access paths, or trust-boundary behavior.

## Issues Encountered

- The repository's git hook rebuilt `graphify-out` after each commit and emitted an ImageMagick `import` usage banner before completing successfully. No tracked generated output remained after the hook.
- `tests/test_naming.py` is ignored by the user's global `*.py` ignore rule, so it was staged with `git add -f`.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

Plan 02 can implement `graphify.naming` and profile schema support against the red tests from this plan. Plan 03/04 can then wire concept naming into export/template/CLI surfaces until the integration tests turn green.

## Self-Check: PASSED

- Found summary file at `.planning/phases/33-naming-repo-identity-helpers/33-01-SUMMARY.md`.
- Found created test file at `tests/test_naming.py`.
- Verified task commits exist with `git cat-file`: `165c63e`, `028cfdd`, `11e6819`.

---
*Phase: 33-naming-repo-identity-helpers*
*Completed: 2026-04-29*
