---
phase: 34-mapping-cluster-quality-note-classes
plan: 3
subsystem: obsidian-export
tags: [naming, export, code-notes, moc-only, tdd]

# Dependency graph
requires:
  - phase: 34-mapping-cluster-quality-note-classes
    provides: First-class `code` note type, CODE mapping context, and routing metadata from Plans 34-01 and 34-02.
provides:
  - Deterministic repo-prefixed CODE filename stems.
  - Export-time CODE filename injection before rendering and merge planning.
  - MOC-only per-community export dispatch for legacy `community` requests.
affects: [phase-34, phase-35, obsidian-export, naming, templates]

# Tech tracking
tech-stack:
  added: []
  patterns: [TDD red-green commits, pure naming helpers, export-time context injection]

key-files:
  created:
    - .planning/phases/34-mapping-cluster-quality-note-classes/34-03-SUMMARY.md
  modified:
    - graphify/naming.py
    - graphify/export.py
    - graphify/templates.py
    - tests/test_naming.py
    - tests/test_export.py
    - tests/test_templates.py

key-decisions:
  - "CODE filename identity is generated in graphify.naming and injected once in to_obsidian after repo identity resolution."
  - "Colliding CODE stems suffix every colliding member with an 8-character SHA-256 hash derived from node id and source file."
  - "Normal Obsidian export coerces legacy community note requests to MOC rendering instead of calling the community overview renderer."

patterns-established:
  - "CODE filename stem context uses filename_stem, filename_collision, and filename_collision_hash fields consumed by render_note()."
  - "Export tests should set mapping.min_community_size explicitly when asserting standalone concept MOC paths."

requirements-completed: [COMM-01, GOD-01, GOD-04]

# Metrics
duration: 6min
completed: 2026-04-29
---

# Phase 34 Plan 3: Deterministic CODE Filename Identity Summary

**Repo-aware CODE note filenames with deterministic collision provenance and MOC-only community export dispatch**

## Performance

- **Duration:** 6 min
- **Started:** 2026-04-29T03:55:38Z
- **Completed:** 2026-04-29T04:02:01Z
- **Tasks:** 2
- **Files modified:** 6

## Accomplishments

- Added `build_code_filename_stems()` in `graphify/naming.py`, producing `CODE_<repo>_<node>` stems and suffixing every colliding member with a stable SHA-256-derived hash.
- Wired `to_obsidian()` to collect classified CODE contexts, inject filename/provenance fields before rendering, and avoid recomputing repo identity in render loops.
- Updated `render_note()` to consume `filename_stem`, allowing dry-run merge plans to produce CODE paths before vault writes.
- Replaced normal per-community overview fallback with warning-level MOC coercion for legacy `note_type: community`.

## Task Commits

Each task was committed atomically:

1. **Task 1: Add deterministic CODE filename helper tests** - `5a95c48` (test)
2. **Task 2: Add CODE export/render RED tests** - `98e767b` (test)
3. **Task 2: Implement CODE filename helper and export injection** - `22828b4` (feat)

**Plan metadata:** pending final docs commit

_Note: Both implementation tasks used TDD RED/GREEN commits._

## Files Created/Modified

- `graphify/naming.py` - Adds the pure CODE filename helper with repo normalization, safe node stems, collision grouping, and hash provenance.
- `graphify/export.py` - Injects CODE filename fields after mapping classification and coerces legacy community contexts to MOC rendering.
- `graphify/templates.py` - Extends `ClassificationContext` with filename metadata and uses `filename_stem` for rendered note filenames.
- `tests/test_naming.py` - Locks unique and colliding CODE stem behavior, including order independence.
- `tests/test_export.py` - Covers dry-run CODE paths, collision-stable path sets, no `_COMMUNITY_*` generated paths, and explicit floor setup for concept MOC path assertions.
- `tests/test_templates.py` - Proves `render_note()` returns CODE filenames from injected `filename_stem`.

## Decisions Made

- CODE filename generation lives in `graphify.naming` so repo normalization and deterministic hashing remain centralized with Phase 33 naming logic.
- Export injects filename metadata into `ClassificationContext` rather than adding a parallel CODE exporter, preserving merge-plan and template behavior.
- The renderer sanitizes an injected `filename_stem` before appending `.md` as a belt-and-suspenders guard, while the naming helper remains the trusted source of safe stems.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Made an older export test explicit about cluster floor**
- **Found during:** Task 2 RED verification
- **Issue:** `test_to_obsidian_resolves_concept_names_for_moc_paths` assumed the default community-size floor allowed a 3-node standalone MOC. Plan 34-01 changed the default floor to 6, so the broader Task 2 test command failed outside the new CODE assertions.
- **Fix:** Set `profile["mapping"]["min_community_size"] = 1` inside that test to preserve its original concept-name path intent.
- **Files modified:** `tests/test_export.py`
- **Verification:** Re-running the RED command left only the intended missing-helper/export/render failures.
- **Committed in:** `98e767b`

**2. [Rule 3 - Blocking] Used tracked-file staging because global ignore hides graphify paths**
- **Found during:** Task 2 GREEN commit
- **Issue:** A global ignore rule prevented `git add graphify/...` from staging tracked production files.
- **Fix:** Used targeted `git add -u graphify/naming.py graphify/export.py graphify/templates.py` for tracked files only.
- **Files modified:** none beyond planned production files
- **Verification:** Commit `22828b4` includes the intended three production files and no unexpected deletions.
- **Committed in:** `22828b4`

---

**Total deviations:** 2 auto-fixed (2 blocking)
**Impact on plan:** Both fixes were limited to verification/staging correctness. No product scope changed beyond the planned CODE filename and MOC-only export behavior.

## Issues Encountered

- The git post-commit graphify hook printed ImageMagick `import` help before rebuilding `graphify-out`; this is pre-existing hook noise and did not affect commits or tests.
- Plan verification emitted third-party deprecation warnings from `hyppo`/`numba`; tests still passed.
- The first self-check shell loop used `path` as a zsh variable and temporarily clobbered `PATH`; the shell environment was restored and the self-check was rerun with `file_path`.

## Known Stubs

None. Stub scan matches were existing placeholder/test strings, type defaults, empty list initializers, and intentional UI placeholder text in HTML export.

## Threat Flags

None. The plan touched filename generation and vault merge-plan paths already covered by the plan threat model; no new unplanned endpoint, auth path, schema, or file-access surface was introduced.

## TDD Gate Compliance

- RED commits present: `5a95c48`, `98e767b`
- GREEN commit present after RED commits: `22828b4`
- No refactor commit was needed.

## Verification

- Task 1 RED: `pytest tests/test_naming.py -q` failed with 3 expected missing `build_code_filename_stems` import failures.
- Task 2 RED: `pytest tests/test_naming.py tests/test_export.py tests/test_templates.py -q` failed with expected missing helper, missing CODE dry-run paths, and missing `filename_stem` rendering failures.
- Task 2 GREEN: `pytest tests/test_naming.py tests/test_export.py tests/test_templates.py -q` passed: 242 passed, 2 warnings.
- Final plan verification after commits passed: `pytest tests/test_naming.py tests/test_export.py tests/test_templates.py -q` -> 242 passed, 2 warnings.
- Acceptance searches passed:
  - `rg 'CODE_|build_code_filename|collision_hash|\\0' tests/test_naming.py`
  - `rg 'build_code_filename|CODE_|filename_collision' graphify/naming.py graphify/export.py graphify/templates.py`
  - `rg 'filename_stem.*CODE_|CODE_graphify_Auth_Service' tests/test_templates.py`
  - `! rg 'render_community_overview' graphify/export.py`
  - `rg '_COMMUNITY_' tests/test_export.py`

## Self-Check: PASSED

- Confirmed all created/modified plan files exist.
- Confirmed task commits exist: `5a95c48`, `98e767b`, `22828b4`.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

Ready for Plan 34-04 to wire richer CODE/concept bidirectional rendering and run the focused Phase 34 gate across mapping, templates, export, profile, and naming. Phase 35 still owns migration visibility for legacy `_COMMUNITY_*` vault files and repo identity recording polish.

---
*Phase: 34-mapping-cluster-quality-note-classes*
*Completed: 2026-04-29*
