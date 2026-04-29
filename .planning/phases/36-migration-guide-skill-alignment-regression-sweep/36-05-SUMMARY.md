---
phase: 36-migration-guide-skill-alignment-regression-sweep
plan: 05
subsystem: testing
tags: [skill-guidance, obsidian, v1.8, regression-tests]

requires:
  - phase: 36-03
    provides: Platform skill variant v1.8 wording and drift tests
  - phase: 36-04
    provides: Phase verification evidence identifying install-time guidance drift
provides:
  - Install-time Claude and AGENTS guidance aligned to the v1.8 MOC/wiki/GRAPH_REPORT contract
  - Regression coverage for embedded install guidance drift in `graphify/__main__.py`
affects: [phase-36-verification, v1.8-release-readiness, install-guidance]

tech-stack:
  added: []
  patterns: [embedded guidance constants covered by pure unit drift tests]

key-files:
  created:
    - .planning/phases/36-migration-guide-skill-alignment-regression-sweep/36-05-SUMMARY.md
  modified:
    - graphify/__main__.py
    - tests/test_skill_files.py

key-decisions:
  - "Install-time Claude and AGENTS sections now direct agents through GRAPH_REPORT.md, Obsidian MOC notes with [[wikilinks]], and wiki/index.md fallback instead of legacy `_COMMUNITY_*` overview notes."
  - "Install guidance drift tests use install-specific required phrases and reuse the shared stale `_COMMUNITY_*` guards."

patterns-established:
  - "Embedded install guidance constants are regression-tested alongside packaged skill files."
  - "Forbidden stale-claim test strings are constructed without matching the source-level stale-claim scan."

requirements-completed: [VER-02]

duration: 6min
completed: 2026-04-29
---

# Phase 36 Plan 05: Install Guidance Drift Closure Summary

**Install-time Claude/AGENTS guidance now matches the v1.8 Obsidian navigation contract and is covered by regression tests.**

## Performance

- **Duration:** 6 min
- **Started:** 2026-04-29T08:33:21Z
- **Completed:** 2026-04-29T08:39:18Z
- **Tasks:** 2
- **Files modified:** 3

## Accomplishments

- Replaced stale `_COMMUNITY_*.md overview notes` wording in `_CLAUDE_MD_SECTION` and `_AGENTS_MD_SECTION`.
- Added install-time guidance tests that import `graphify.__main__` and cover both embedded install sections.
- Verified focused tests and stale-claim scans for the gap closure gate.

## Task Commits

Each task was committed atomically:

1. **Task 1: Align embedded Claude and AGENTS guidance** - `d2025bc` (fix)
2. **Task 2: Add install-time guidance drift tests** - `129d572` (test)

**Plan metadata:** pending final metadata commit.

## Files Created/Modified

- `graphify/__main__.py` - Aligns installed Claude/AGENTS guidance with `GRAPH_REPORT.md`, Obsidian MOC notes, `[[wikilinks]]`, and `wiki/index.md` fallback.
- `tests/test_skill_files.py` - Adds `INSTALL_GUIDANCE_SECTIONS`, required install navigation phrases, and stale-claim regression coverage for embedded install sections.
- `.planning/phases/36-migration-guide-skill-alignment-regression-sweep/36-05-SUMMARY.md` - Records execution evidence and completion state.

## Decisions Made

- Installed agents should navigate the Graphify-owned v1.8 Obsidian MOC output when `graphify-out/obsidian/` exists, not legacy community overview files.
- The install guidance has its own required phrase set because the embedded sections are concise project rules, not full packaged skill documentation.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Avoided stale-claim scan hits in regression constants**
- **Found during:** Task 2 (Add install-time guidance drift tests)
- **Issue:** The required negative scan matched forbidden `_COMMUNITY_* overview notes` literals inside `tests/test_skill_files.py` itself.
- **Fix:** Kept the same forbidden phrase coverage but split those string literals so the source-level scan only catches real stale guidance text.
- **Files modified:** `tests/test_skill_files.py`
- **Verification:** `pytest tests/test_skill_files.py tests/test_main_flags.py -q` and the stale-claim `rg` gate passed.
- **Committed in:** `129d572`

---

**Total deviations:** 1 auto-fixed (1 blocking issue)
**Impact on plan:** The fix preserved test behavior and made the plan's source-level drift gate executable. No scope expansion.

## TDD Gate Compliance

Task 2 was marked `tdd="true"`, but the production guidance alignment was completed and committed in Task 1 before the install-section regression tests were added. The added tests passed immediately as regression coverage for already-aligned behavior; no separate GREEN implementation commit was needed.

## Issues Encountered

- The normal `git add graphify/__main__.py` path was blocked by an ignore rule; the tracked file was staged with `git add -u graphify/__main__.py`.
- Commit hooks rebuilt `graphify-out` after each code/test commit; no tracked generated changes remained afterward.

## Known Stubs

None.

## User Setup Required

None - no external service configuration required.

## Verification

- `pytest tests/test_main_flags.py -q` -> 23 passed
- `pytest tests/test_skill_files.py tests/test_main_flags.py -q` -> 30 passed
- `rg` stale generated-output scan over `graphify/__main__.py` and `tests/test_skill_files.py` -> no matches
- `rg -n "INSTALL_GUIDANCE_SECTIONS" tests/test_skill_files.py` -> present
- `rg -n "GRAPH_REPORT.md" graphify/__main__.py` and `rg -n "wiki/index.md" graphify/__main__.py` -> present

## Next Phase Readiness

VER-02's install-time guidance gap is closed. Phase 36 is ready for re-verification.

## Self-Check: PASSED

- Summary file exists at `.planning/phases/36-migration-guide-skill-alignment-regression-sweep/36-05-SUMMARY.md`.
- Task commit `d2025bc` exists.
- Task commit `129d572` exists.

---
*Phase: 36-migration-guide-skill-alignment-regression-sweep*
*Completed: 2026-04-29*
