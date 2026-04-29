---
phase: 34-mapping-cluster-quality-note-classes
plan: 1
subsystem: obsidian-export
tags: [profile, templates, code-notes, moc-only, tdd]

# Dependency graph
requires:
  - phase: 33-naming-repo-identity-helpers
    provides: Repo identity and concept naming helpers that later CODE export paths will consume.
provides:
  - First-class `code` note type in profile and template validation.
  - Built-in `code.md` template for CODE notes.
  - Default v1.8 `mapping.min_community_size` floor of 6.
affects: [phase-34, phase-35, obsidian-export, mapping, templates]

# Tech tracking
tech-stack:
  added: []
  patterns: [TDD red-green commits, shared profile/template note-type allowlists]

key-files:
  created:
    - graphify/builtin_templates/code.md
  modified:
    - graphify/profile.py
    - graphify/templates.py
    - tests/test_profile.py
    - tests/test_templates.py

key-decisions:
  - "CODE notes are now a first-class template/profile note type while legacy community remains accepted for compatibility warnings."
  - "The built-in v1.8 profile now uses mapping.min_community_size = 6; user profile overrides remain literal."

patterns-established:
  - "Profile and template note-type allowlists must be updated together for new note classes."
  - "New built-in note types need a matching builtin_templates/<type>.md file and validation coverage."

requirements-completed: [COMM-01, GOD-01]

# Metrics
duration: 6min
completed: 2026-04-29
---

# Phase 34 Plan 1: Profile/Template Note-Class Contract Summary

**CODE note contracts with default cluster floor 6 and built-in safe template rendering**

## Performance

- **Duration:** 6 min
- **Started:** 2026-04-29T03:34:32Z
- **Completed:** 2026-04-29T03:40:35Z
- **Tasks:** 2
- **Files modified:** 5

## Accomplishments

- Locked the profile contract with tests for default `mapping.min_community_size == 6`, `code` in `_KNOWN_NOTE_TYPES`, and `dataview_queries.code` validation.
- Added `code` to the template note-type contract: `_NOTE_TYPES`, `_REQUIRED_PER_TYPE`, built-in template loading, and `render_note()` non-MOC rendering.
- Added `graphify/builtin_templates/code.md`, matching the safe thing-like template shape required for later CODE export work.

## Task Commits

Each task was committed atomically:

1. **Task 1: Lock profile note-type and floor tests** - `a56f2d3` (test)
2. **Task 1: Implement profile contract** - `46bb91b` (feat)
3. **Task 2: Lock template CODE contract tests** - `d03fcbf` (test)
4. **Task 2: Implement template CODE contract** - `0e33da1` (feat)

**Plan metadata:** pending final docs commit

_Note: Both tasks used TDD RED/GREEN commits._

## Files Created/Modified

- `graphify/profile.py` - Defaults cluster floor to 6 and accepts `code` as a profile Dataview note type.
- `graphify/templates.py` - Recognizes `code` as a renderable non-MOC note type and validates its built-in template.
- `graphify/builtin_templates/code.md` - Provides default CODE note rendering with frontmatter, wayfinder, body, connections, and metadata slots.
- `tests/test_profile.py` - Covers the floor and profile note-type contract.
- `tests/test_templates.py` - Covers code template loading, rendering, and per-note-type Dataview routing.

## Decisions Made

- CODE uses the existing non-MOC render path for this plan, preserving `_build_frontmatter_fields()`, `_dump_frontmatter()`, `_emit_wikilink()`, and existing block-template sanitization.
- No distinct default `code` folder was added in this plan; code notes can use the existing downstream folder routing until Phase 35 template/export polish.
- Legacy `community` remains in allowlists for compatibility and warning-level MOC-only guidance; this plan did not revive normal `_COMMUNITY_*` overview output.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Force-staged required CODE template despite global ignore**
- **Found during:** Task 2 (Implement profile and template note-class contract)
- **Issue:** A global ignore rule (`graphify*`) hid the new required `graphify/builtin_templates/code.md` file from normal staging.
- **Fix:** Used targeted `git add -f -- graphify/builtin_templates/code.md` for that single plan-required source file, while staging tracked `graphify/templates.py` normally.
- **Files modified:** `graphify/builtin_templates/code.md`
- **Verification:** Commit `0e33da1` includes `create mode 100644 graphify/builtin_templates/code.md`; focused tests pass.
- **Committed in:** `0e33da1`

---

**Total deviations:** 1 auto-fixed (1 blocking)
**Impact on plan:** The fix was limited to staging a required source artifact already specified by the plan; no behavior scope changed.

## Issues Encountered

- The git post-commit graphify hook ran after each commit and rebuilt `graphify-out`; those generated outputs are ignored and were not committed.
- The stub scan found only existing template-placeholder language and intentional test fixtures; no new runtime stubs were introduced.

## Known Stubs

None.

## Threat Flags

None.

## TDD Gate Compliance

- RED commits present: `a56f2d3`, `d03fcbf`
- GREEN commits present after RED commits: `46bb91b`, `0e33da1`
- No refactor commit was needed.

## Verification

- `pytest tests/test_profile.py -q` during Task 1 RED failed with the expected floor and `code` note-type failures.
- `pytest tests/test_templates.py -q` during Task 2 RED failed with the expected missing `code` template/rendering failures.
- `pytest tests/test_profile.py tests/test_templates.py -q` passed: 393 passed, 1 xfailed.
- Acceptance checks passed:
  - `test -f graphify/builtin_templates/code.md`
  - `rg '"code"' graphify/profile.py graphify/templates.py tests/test_templates.py`
  - `rg 'min_community_size": 6|min_community_size.*6' graphify/profile.py`

## Self-Check: PASSED

- Confirmed all created/modified plan files exist.
- Confirmed task commits exist: `a56f2d3`, `46bb91b`, `d03fcbf`, `0e33da1`.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

Ready for Plan 34-02 to consume the note-class contract from mapping classification and routing metadata. Plan 34-03 still owns deterministic CODE filename identity and collision handling; Phase 35 still owns migration visibility for legacy `_COMMUNITY_*` vault files.

---
*Phase: 34-mapping-cluster-quality-note-classes*
*Completed: 2026-04-29*
