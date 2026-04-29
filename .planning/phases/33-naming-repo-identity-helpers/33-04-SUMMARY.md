---
phase: 33-naming-repo-identity-helpers
plan: 04
subsystem: export
tags: [cli, obsidian, repo-identity, concept-naming, templates, pytest]

requires:
  - phase: 33-03
    provides: cache-backed ConceptName resolution and repo identity helper contracts
provides:
  - CLI parsing for --repo-identity on graphify run and graphify --obsidian
  - Obsidian export repo identity resolution with repo-identity.json generated artifact
  - Concept-name-driven MOC filename/content rendering through to_obsidian()
  - Generated MOC title sink sanitization across filename, tag, frontmatter, and template output
affects: [phase-33, phase-34, phase-35, cli, export, templates]

tech-stack:
  added: []
  patterns:
    - Function-local naming imports inside export/CLI paths to preserve lazy CLI loading
    - Generated sidecar writes via tmp file, fsync, and os.replace
    - Explicit label precedence: caller community_labels > resolved concept names > mapping labels

key-files:
  created: []
  modified:
    - graphify/__main__.py
    - graphify/export.py
    - graphify/templates.py
    - tests/test_export.py
    - tests/test_main_flags.py

key-decisions:
  - "Repo identity remains centralized in graphify.naming; CLI parsing only extracts and forwards the optional flag value."
  - "to_obsidian() records repo identity as graphify-out/repo-identity.json only on non-dry-run exports."
  - "Explicit community_labels remain the highest-precedence override over auto-resolved concept names."
  - "Unsafe generated MOC titles are normalized inside templates.py before filename/frontmatter/template sinks consume them."

patterns-established:
  - "Use repo-identity.json as the Phase 33 durable generated artifact for resolved repo identity provenance."
  - "Use concept_namer as an injectable test seam for resolve_concept_names() without adding Phase 33 cache-refresh UI."

requirements-completed:
  - NAME-01
  - NAME-02
  - NAME-03
  - NAME-04
  - NAME-05
  - REPO-01
  - REPO-02
  - REPO-03

duration: 12min
completed: 2026-04-29
---

# Phase 33 Plan 04: CLI and Obsidian Naming Integration Summary

**Repo identity and concept naming now flow through CLI and Obsidian export, with durable sidecar provenance and sanitized generated MOC titles**

## Performance

- **Duration:** 12 min
- **Started:** 2026-04-29T02:25:08Z
- **Completed:** 2026-04-29T02:36:57Z
- **Tasks:** 3
- **Files modified:** 5

## Accomplishments

- Added `--repo-identity` parsing for both `graphify run` and `graphify --obsidian`, including `--flag=value` support and exit-2 missing-value handling.
- Extended `to_obsidian()` with repo identity resolution, non-dry-run `repo-identity.json` sidecar persistence, concept naming resolution, and correct label precedence.
- Hardened generated MOC title rendering so unsafe names are normalized before filenames, tags, wikilinks, Dataview/frontmatter-adjacent content, and template output.

## Task Commits

Each task was committed atomically:

1. **Task 1 RED: Parse --repo-identity in CLI entry points** - `0a26d8a` (test)
2. **Task 1 GREEN: Parse --repo-identity in CLI entry points** - `18455ef` (feat)
3. **Task 2 RED: Resolve repo identity and concept names inside to_obsidian** - `77f1da9` (test)
4. **Task 2 GREEN: Resolve repo identity and concept names inside to_obsidian** - `443114e` (feat)
5. **Task 3: Verify generated title sink safety and phase slice** - `c95eefc` (fix)

## Files Created/Modified

- `graphify/__main__.py` - Parses `--repo-identity` before positional target selection and forwards the value to run/export wiring.
- `graphify/export.py` - Resolves repo identity, writes `repo-identity.json`, resolves concept names, and injects MOC labels with explicit precedence.
- `graphify/templates.py` - Normalizes unsafe generated MOC titles before final sink rendering.
- `tests/test_export.py` - Covers concept-namer MOC paths, dry-run sidecar suppression, and repo identity sidecar persistence.
- `tests/test_main_flags.py` - Covers CLI repo identity precedence and missing-value errors.

## Decisions Made

- Kept CLI handling narrow: parse and forward the repo identity flag, while `graphify.naming.resolve_repo_identity()` remains the sole precedence/reporting authority.
- Wrote repo identity provenance to `repo-identity.json` during real exports only; dry-run computes naming provenance without durable sidecar writes.
- Preserved `community_labels` as an explicit caller override over concept names to avoid breaking existing API behavior.

## Deviations from Plan

None - plan executed exactly as written.

## Verification

- Task 1 RED: focused CLI repo identity tests failed before parsing/export wiring existed.
- Task 1 GREEN: `python3 -m pytest tests/test_main_flags.py::test_run_repo_identity_flag_overrides_profile tests/test_main_flags.py::test_run_profile_repo_identity_used_without_flag tests/test_main_flags.py::test_obsidian_repo_identity_flag_overrides_profile tests/test_main_flags.py::test_run_repo_identity_missing_value_exits_two tests/test_main_flags.py::test_obsidian_repo_identity_missing_value_exits_two -q` -> 5 passed.
- Task 2 RED: focused Obsidian naming tests failed before `concept_namer` and sidecar persistence existed.
- Task 2 GREEN: `python3 -m pytest tests/test_export.py::test_to_obsidian_resolves_concept_names_for_moc_paths tests/test_export.py::test_to_obsidian_dry_run_does_not_write_naming_sidecar tests/test_export.py::test_to_obsidian_profile_repo_identity_records_sidecar tests/test_export.py::test_to_obsidian_fallback_repo_identity_records_sidecar -q` -> 4 passed.
- Task 3 sink safety: `python3 -m pytest tests/test_templates.py::test_generated_moc_title_is_sanitized_across_sinks -q` -> 1 passed.
- Focused Phase 33 gate: `python3 -m pytest tests/test_naming.py tests/test_profile.py tests/test_templates.py tests/test_mapping.py tests/test_export.py tests/test_output.py tests/test_main_flags.py -q` -> 508 passed, 1 xfailed, 2 warnings.
- Full suite: `python3 -m pytest tests/ -q` -> 1836 passed, 1 xfailed, 8 warnings.
- Acceptance scope checks: no `.graphify` concept-names writes and no Phase 34 `CODE_` behavior added in `graphify/export.py` or `graphify/templates.py`.
- `ReadLints` on edited Python files -> no linter errors reported.

## Known Stubs

None. Stub-pattern scan only found existing explanatory uses of "placeholder" and intentional empty values in template rendering calls; no new UI-facing or behavior-blocking stubs were introduced.

## Threat Flags

None. The new CLI argument, generated sidecar write, dry-run filesystem boundary, and generated-title template sinks were all covered by the plan threat model.

## Issues Encountered

- The repository's git hook rebuilt `graphify-out` after each task commit and emitted an ImageMagick `import` usage banner before completing successfully.
- The initial Plan 04 test slice lacked sidecar and missing-value coverage, so those RED tests were added before implementation.
- Concept-namer tests needed an explicit nonzero concept naming budget because the built-in default profile keeps LLM naming offline by default.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

Phase 33 is complete and ready for verification. Phase 34 can consume repo identity and concept MOC names without adding CODE-note behavior retroactively to this plan.

## Self-Check: PASSED

- Found summary file at `.planning/phases/33-naming-repo-identity-helpers/33-04-SUMMARY.md`.
- Verified task commits exist with `git log`: `0a26d8a`, `18455ef`, `77f1da9`, `443114e`, `c95eefc`.
- Verified focused and full pytest gates passed after all task commits.

---
*Phase: 33-naming-repo-identity-helpers*
*Completed: 2026-04-29*
