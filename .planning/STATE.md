---
gsd_state_version: 1.0
milestone: v1.8
milestone_name: Output Taxonomy & Cluster Quality
status: executing
stopped_at: Completed 36-01-PLAN.md
last_updated: "2026-04-29T07:45:03.456Z"
last_activity: 2026-04-29
progress:
  total_phases: 5
  completed_phases: 4
  total_plans: 20
  completed_plans: 18
  percent: 90
---

# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-04-28 for v1.8)

**Core value:** Graphify can inject knowledge into any Obsidian vault framework driven entirely by a declarative vault-side profile.
**Current focus:** Phase 36 — Migration Guide, Skill Alignment & Regression Sweep

## Current Position

Phase: 36 (Migration Guide, Skill Alignment & Regression Sweep) — EXECUTING
Plan: 4 of 4
Status: Ready to execute
Last activity: 2026-04-29

Progress: [█████████░] 88%

## Performance Metrics

**Recent milestone baselines:**

| Milestone | Phases | Plans | Result |
|-----------|--------|-------|--------|
| v1.5 | 19-22 | 11 | 34/34 requirements, shipped 2026-04-27 |
| v1.6 | 23-26 | 5 | 15/15 requirements, shipped 2026-04-27 |
| v1.7 | 27-31 | 14 | 13/13 requirements, shipped 2026-04-28 |
| v1.8 | 32-36 | TBD | 33/33 requirements mapped, not started |
| Phase 32 P01 | 4min | 2 tasks | 3 files |
| Phase 32 P02 | 5min | 2 tasks | 3 files |
| Phase 32 P03 | 5min | 2 tasks | 4 files |
| Phase 32 P04 | 6min | 2 tasks | 3 files |
| Phase 33 P01 | 6min | 3 tasks | 5 files |
| Phase 33 P02 | 6min | 3 tasks | 2 files |
| Phase 33 P03 | 5min | 3 tasks | 1 file |
| Phase 33 P04 | 12min | 3 tasks | 5 files |
| Phase 34 P1 | 6min | 2 tasks | 5 files |
| Phase 34 P2 | 8min | 2 tasks | 2 files |
| Phase 34 P03 | 6min | 2 tasks | 6 files |
| Phase 34 P4 | 7min | 3 tasks | 4 files |
| Phase 34 P5 | 4min | 2 tasks | 2 files |
| Phase 35 P01 | 6min | 3 tasks | 2 files |
| Phase 35 P02 | 6min | 3 tasks | 5 files |
| Phase 35 P03 | 9min | 3 tasks | 5 files |
| Phase 36 P01 | 13min | 3 tasks | 4 files |
| Phase 36 P02 | 7min | 2 tasks | 5 files |
| Phase 36 P02 | 6min | 2 tasks | 5 files |

## Accumulated Context

### Decisions

Locked v1.8 choices:

- MOCs live under `Atlas/Sources/Graphify/MOCs/` by default.
- `_COMMUNITY_*` default output is hard-deprecated; community output is MOC-only by default.
- Cached LLM concept naming is required, with deterministic fallback.
- Migration support includes an automated migration command plus a Markdown guide.
- v1.8 derives phases from current milestone requirements only and continues numbering at Phase 32.
- [Phase 32]: Phase 32 planning contract uses mapping.min_community_size as the canonical cluster floor key.
- [Phase 32]: mapping.moc_threshold is documented as invalid immediately for v1.8 profiles.
- [Phase 32]: v1.8 taxonomy is resolved into folder_mapping at profile load/preflight time. — Keeps downstream mapping/export consumers on the existing folder_mapping contract while centralizing taxonomy truth in profile.py.
- [Phase 32]: mapping.min_community_size is canonical; mapping.moc_threshold is a hard validation error. — Matches the locked v1.8 contract and prevents silent legacy precedence behavior.
- [Phase 32]: Deprecated community overview templates remain renderable but produce MOC-only output migration warnings. — Phase 32 is the contract layer, so warnings guide migration without removing renderer support.
- [Phase 32]: Mapping resolves taxonomy folders into ClassificationContext.folder before Obsidian export rendering.
- [Phase 32]: mapping.min_community_size is the only runtime standalone MOC floor key in mapping.py.
- [Phase 32]: Hostless tiny communities route to the _Unclassified MOC bucket.
- [Phase 32]: Doctor profile diagnostics now use validate_profile_preflight() as the shared source for errors and warnings.
- [Phase 32]: Warning-only doctor profile findings guide migration without making is_misconfigured() true.
- [Phase 32]: Doctor skips output resolution when fatal preflight errors exist to avoid duplicate invalid-profile diagnostics.
- [Phase 33 Plan 01]: Wave 0 tests intentionally define red naming and repo identity contracts before production helpers are implemented.
- [Phase 33 Plan 02]: Repo identity resolution is centralized in graphify.naming with explicit CLI > profile > git remote > directory precedence.
- [Phase 33 Plan 02]: repo.identity is the only profile location for repo identity; naming.repo is rejected with guidance.
- [Phase 33 Plan 02]: naming.concept_names exposes enabled, budget, and style controls only; prompt templates remain out of schema.
- [Phase 33 Plan 03]: Concept naming cache/provenance is sidecar-only under the supplied artifacts directory.
- [Phase 33 Plan 03]: LLM concept title candidates are rejected before persistence when unsafe, generic, duplicate, path-like, template-breaking, wikilink-breaking, control-character-bearing, empty, or too long.
- [Phase 33]: [Phase 33 Plan 04]: Repo identity remains centralized in graphify.naming; CLI parsing only extracts and forwards the optional flag value.
- [Phase 33]: [Phase 33 Plan 04]: to_obsidian() records repo identity as graphify-out/repo-identity.json only on non-dry-run exports.
- [Phase 33]: [Phase 33 Plan 04]: Explicit community_labels remain the highest-precedence override over auto-resolved concept names.
- [Phase 33]: [Phase 33 Plan 04]: Unsafe generated MOC titles are normalized inside templates.py before filename/frontmatter/template sinks consume them.
- [Phase 34]: [Phase 34 Plan 01]: CODE notes are a first-class profile/template note type while legacy community remains a compatibility token. — Phase 34 Plan 01 established the shared profile/template contract needed before mapping and export consume CODE notes.
- [Phase 34]: [Phase 34 Plan 01]: Default mapping.min_community_size is now 6 for built-in v1.8 profiles. — D-08 selected 6 as the default cluster-quality floor while preserving literal user overrides.
- [Phase 34 Plan 02]: Mapping now emits standalone, hosted, and bucketed routing metadata as the source of truth for downstream export/template behavior.
- [Phase 34 Plan 02]: CODE note eligibility is limited to code-backed god nodes with non-empty string source_file values and synthetic-node exclusions.
- [Phase 34 Plan 02]: Concept MOC CODE member context is sorted by degree descending, then label and node id, and capped at 10.
- [Phase 34]: [Phase 34 Plan 03]: CODE filename identity is generated in graphify.naming and injected once in to_obsidian after repo identity resolution. — Keeps repo normalization and filename identity centralized while preserving the existing export/render pipeline.
- [Phase 34]: [Phase 34 Plan 03]: Colliding CODE stems suffix every colliding member with an 8-character SHA-256 hash derived from node id and source file. — Makes collision handling deterministic and independent of graph insertion order.
- [Phase 34]: [Phase 34 Plan 03]: Normal Obsidian export coerces legacy community note requests to MOC rendering instead of calling the community overview renderer. — Satisfies MOC-only community output while retaining migration diagnostics for later phases.
- [Phase 34]: [Phase 34 Plan 04]: Export propagates final concept labels into CODE parent links before rendering. — Keeps CODE up links aligned with explicit community labels and concept naming overrides.
- [Phase 34]: [Phase 34 Plan 04]: Concept MOC CODE links render from ClassificationContext code_members/code_member_labels via _emit_wikilink(). — Preserves context-owned rendering and established wikilink sanitization.
- [Phase 34]: [Phase 34 Plan 04]: CODE collision provenance is emitted only for colliding filename stems through the frontmatter dumper. — Avoids extra metadata for normal CODE notes while keeping collision evidence sanitized.
- [Phase 34 Plan 05]: Structured CODE member links preserve export-provided filename_stem as the wikilink target after safe_filename only. — Closes the verifier gap by preventing title-case target drift while keeping aliases sanitized.
- [Phase 35 Plan 01]: Migration preview plan IDs are SHA-256 digests over normalized non-volatile preview payloads.
- [Phase 35 Plan 01]: Legacy _COMMUNITY_* files are surfaced as review-only ORPHAN rows and never promoted into apply writes.
- [Phase 35 Plan 01]: Migration artifact writes are confined to graphify-out/migrations with tmp+fsync+os.replace.
- [Phase 35]: [Phase 35 Plan 02]: Repo identity for CODE notes is sourced from resolved_repo_identity.identity and propagated through CODE render contexts. — Keeps repo normalization centralized while allowing templates and manifests to expose the same resolved identity.
- [Phase 35]: [Phase 35 Plan 02]: Repo frontmatter is graphify-owned replace metadata while unknown user-added keys remain preserved. — Ensures generated repo metadata updates safely without clobbering arbitrary user-authored frontmatter.
- [Phase 35]: [Phase 35 Plan 02]: Vault manifest run metadata uses reserved __graphify_run__ so path-entry readers can skip it safely. — Separates run-level audit metadata from per-note path entries and preserves old manifest compatibility.
- [Phase 36 Plan 01]: Archive movement stays migration-specific in graphify/migration.py; the generic merge engine continues to skip ORPHAN rows.
- [Phase 36 Plan 01]: Reviewed apply archives legacy notes only after apply_merge_plan reports zero failures.
- [Phase 36 Plan 01]: Rollback evidence is exposed through archived_legacy_notes metadata and CLI wording under graphify-out/migrations/archive/.
- [Phase 36]: ---

phase: 36-migration-guide-skill-alignment-regression-sweep
plan: 02
subsystem: documentation
tags: [obsidian, migration, cli, docs, pytest]

requires:

  - phase: 35-templates-export-plumbing-dry-run-migration-visibility
    provides: preview-first update-vault flow, reviewed apply, and archive evidence

  - phase: 36-migration-guide-skill-alignment-regression-sweep
    provides: archive-by-default apply wording from Plan 36-01
provides:

  - generic-first v1.8 Obsidian migration guide
  - README guidance distinguishing direct export from reviewed update-vault migration
  - CLI help contract for backup-before-apply and archive location

affects: [migration-guide, skill-alignment, release-docs]

tech-stack:
  added: []
  patterns:

    - docs contract tests reading repo-root Markdown directly
    - argparse RawDescriptionHelpFormatter epilog for multi-line safety guidance

key-files:
  created:

    - MIGRATION_V1_8.md
    - tests/test_docs.py
    - .planning/phases/36-migration-guide-skill-alignment-regression-sweep/36-02-SUMMARY.md
  modified:

    - README.md
    - graphify/__main__.py
    - tests/test_main_flags.py

key-decisions:

  - "The v1.8 guide is generic-first: --input is any raw corpus and --vault is the target Obsidian vault, with work-vault/raw -> ls-vault as the canonical example."
  - "README presents --obsidian as lower-level direct export and update-vault as the reviewed existing-vault migration/update workflow."
  - "CLI help repeats backup-before-apply, reviewed --apply --plan-id, archive path, and non-destructive legacy-note wording."

patterns-established:

  - "Docs drift tests assert exact safety phrases and section ordering rather than snapshotting full Markdown files."
  - "User-facing migration docs put backup before any apply command and rollback immediately after apply/archive."

requirements-completed: [MIG-05, VER-02]

duration: 7min
completed: 2026-04-29
---

# Phase 36 Plan 02: Migration Guide and Command Docs Summary

**Generic-first v1.8 migration guide with README and CLI help aligned around preview-first `update-vault`, reviewed apply, archive evidence, and rollback.**

- [Phase 36]: The migration guide is generic-first: --input is any raw corpus and --vault is the target Obsidian vault, with work-vault/raw -> ls-vault kept as the canonical example. — Keeps docs reusable while preserving the canonical example from the plan.
- [Phase 36]: Backup-before-apply, reviewed --apply --plan-id, archive path, rollback, and rerun wording are enforced by docs and CLI help tests. — Prevents documentation drift around write safety.
- [Phase 36]: Localized READMEs remain outside this English docs contract per D-08. — Matches the phase scope and avoids unreviewed translation edits.

## Performance

- **Duration:** 7 min
- **Started:** 2026-04-29T07:36:05Z
- **Completed:** 2026-04-29T07:43:41Z
- **Tasks:** 2
- **Files modified:** 5

## Accomplishments

- Added `MIGRATION_V1_8.md`, covering raw-corpus-to-target-vault semantics, validation, dry-run preview, plan review, backup as a hard prerequisite, reviewed apply/archive, immediate rollback, rerun, and cleanup review.
- Added `tests/test_docs.py` to enforce required migration guide phrases, backup/apply/rollback ordering, README guide linkage, and the English-only docs contract for this plan.
- Updated `README.md` and `graphify update-vault --help` so both distinguish lower-level `--obsidian` export from reviewed `update-vault` migration and mention `graphify-out/migrations/archive/`.

## Task Commits

1. **Task 1 RED: Add migration guide docs contract** - `90ecce3` (test)
2. **Task 1 GREEN: Add v1.8 migration guide** - `afc8ac1` (feat)
3. **Task 1 refinement: Tighten migration guide wording/order** - `2992437` (feat)
4. **Task 2 RED: Add README and CLI help docs contracts** - `dfd0ef5` (test)
5. **Task 2 GREEN: Align README and CLI help** - `ca24880` (feat)

## Files Created/Modified

- `MIGRATION_V1_8.md` - Generic-first v1.8 migration guide with canonical `work-vault/raw` to `ls-vault` example.
- `README.md` - English Obsidian adapter docs now describe direct export and reviewed existing-vault update/migration as separate surfaces.
- `graphify/__main__.py` - Top-level and `update-vault --help` text now include reviewed apply, backup, and archive wording.
- `tests/test_docs.py` - Docs contract tests for guide phrases, ordering, README linkage, and localized README scope.
- `tests/test_main_flags.py` - CLI help contract now checks backup, `--apply --plan-id`, and archive path wording.

## Decisions Made

- Keep the migration guide in the repository root as `MIGRATION_V1_8.md` so README can link to it directly and users can find it beside other top-level guides.
- Keep localized READMEs unchanged per D-08; the tests explicitly scope this contract to English docs.
- Use exact phrase tests for safety-critical wording, including `Back up the target vault before apply`, `Review the migration plan before apply`, and `Rollback immediately after apply/archive if needed`.

## Deviations from Plan

### Auto-fixed Issues

None - plan executed exactly as written.

**Total deviations:** 0 auto-fixed.
**Impact on plan:** Plan scope was preserved.

## TDD Gate Compliance

- Task 1 RED failed as expected because `MIGRATION_V1_8.md` did not exist yet; GREEN passed after adding the guide.
- Task 2 RED failed as expected because README and CLI help lacked the required v1.8 wording; GREEN passed after updating both surfaces.
- An additional guide refinement commit (`2992437`) was created after the initial guide commit to tighten section wording and ordering while preserving the Task 1 behavior.

## Issues Encountered

- The git hook prints ImageMagick `import` help before graph rebuilds; commits still completed successfully with normal hooks.
- `git add graphify/...` reports the ignored `graphify` path, so tracked changes under `graphify/` were staged explicitly with `git add -f graphify/__main__.py`.
- A transient `.git/index.lock` appeared after the first commit retry. No active Git process was found, and the lock cleared before the retry; no manual lock deletion was needed.

## Known Stubs

None. Stub-pattern scan found no TODO/FIXME/placeholder or UI-empty-data patterns in the files created or modified by this plan.

## Threat Flags

None. This plan changed documentation and CLI help only; no new endpoint, auth path, schema, network, or filesystem trust boundary was introduced beyond the documented migration behavior covered by the plan threat model.

## Verification

- `pytest tests/test_docs.py -q` - 3 passed after Task 1 GREEN
- `pytest tests/test_docs.py tests/test_main_flags.py::test_update_vault_help_lists_command_shape -q` - 5 passed
- `pytest tests/ -q` - 1881 passed, 1 xfailed, 8 warnings

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

Ready for Plan 36-03 to align packaged platform skill variants with the same v1.8 wording and drift tests.

## Self-Check: PASSED

- Summary file exists at `.planning/phases/36-migration-guide-skill-alignment-regression-sweep/36-02-SUMMARY.md`.
- Created/modified files exist: `MIGRATION_V1_8.md`, `tests/test_docs.py`, `README.md`, `graphify/__main__.py`, and `tests/test_main_flags.py`.
- Task commits exist in `git log --oneline --all`: `90ecce3`, `afc8ac1`, `2992437`, `dfd0ef5`, `ca24880`.
- Focused and full verification commands passed.

---
*Phase: 36-migration-guide-skill-alignment-regression-sweep*
*Completed: 2026-04-29*
---
phase: 36-migration-guide-skill-alignment-regression-sweep
plan: 02
subsystem: docs
tags: [obsidian, migration, update-vault, cli, pytest]

requires:

  - phase: 35-templates-export-plumbing-dry-run-migration-visibility
    provides: preview-first update-vault flow with reviewed apply and migration artifacts

  - phase: 36-migration-guide-skill-alignment-regression-sweep
    provides: archive-by-default apply metadata from Plan 36-01
provides:

  - generic-first v1.8 Obsidian migration guide
  - README guidance for lower-level export versus reviewed update-vault migration
  - CLI help wording for backup-before-apply and archive location

affects: [migration-guide, skill-alignment, docs-contracts]

tech-stack:
  added: []
  patterns:

    - exact-phrase docs contract tests for migration safety wording
    - preview-first CLI docs mirrored across README and help text

key-files:
  created:

    - MIGRATION_V1_8.md
    - .planning/phases/36-migration-guide-skill-alignment-regression-sweep/36-02-SUMMARY.md
  modified:

    - README.md
    - graphify/__main__.py
    - tests/test_docs.py
    - tests/test_main_flags.py

key-decisions:

  - "The migration guide is generic-first: --input is any raw corpus and --vault is the target Obsidian vault, with work-vault/raw -> ls-vault kept as the canonical example."
  - "Backup-before-apply, reviewed --apply --plan-id, archive path, rollback, and rerun wording are enforced by docs and CLI help tests."
  - "Localized READMEs remain outside this English docs contract per D-08."

patterns-established:

  - "Docs safety contract: required user-facing phrases are asserted directly from Markdown and CLI help output."
  - "Migration docs distinguish low-level --obsidian export from reviewed existing-vault update-vault migration."

requirements-completed: [MIG-05, VER-02]

duration: 6min
completed: 2026-04-29
---

# Phase 36 Plan 02: Migration Guide and Docs Alignment Summary

**Generic-first v1.8 Obsidian migration guidance now documents preview, backup, reviewed apply/archive, rollback, and rerun across the guide, README, CLI help, and docs contract tests.**

## Performance

- **Duration:** 6 min
- **Started:** 2026-04-29T07:37:37Z
- **Completed:** 2026-04-29T07:43:03Z
- **Tasks:** 2
- **Files modified:** 5

## Accomplishments

- Added `MIGRATION_V1_8.md` with the canonical `graphify update-vault --input work-vault/raw --vault ls-vault` example while explaining that the command works for any raw corpus and target Obsidian vault.
- Documented backup as a hard prerequisite before `--apply --plan-id <id>`, with rollback instructions immediately after the apply/archive step and rerun guidance after archive review.
- Updated README and `graphify update-vault --help` to describe the same preview-first reviewed apply flow, archive location, and non-destructive legacy-note handling.
- Added docs and CLI help contract tests that protect required v1.8 wording without requiring localized README updates.

## Task Commits

1. **Task 1 RED: Add migration guide docs contract** - `90ecce3` (test)
2. **Task 1 GREEN: Add v1.8 migration guide** - `afc8ac1` (feat)
3. **Task 1 GREEN refinement: Normalize guide content** - `2992437` (feat)
4. **Task 2 RED: Add README and CLI docs contracts** - `dfd0ef5` (test)
5. **Task 2 GREEN: Align README and update-vault help** - `ca24880` (feat)

## Files Created/Modified

- `MIGRATION_V1_8.md` - Generic-first v1.8 migration guide with backup, preview, review, apply/archive, rollback, rerun, and cleanup guidance.
- `README.md` - Obsidian section now distinguishes `--obsidian` direct export from reviewed `update-vault` migration and links to the guide.
- `graphify/__main__.py` - Top-level and `update-vault --help` text now include backup-before-apply, reviewed apply, lower-level export, and archive wording.
- `tests/test_docs.py` - Direct Markdown contract tests for guide and README required phrases.
- `tests/test_main_flags.py` - CLI help phrase assertions for the `update-vault` command.
- `.planning/phases/36-migration-guide-skill-alignment-regression-sweep/36-02-SUMMARY.md` - Execution summary and verification record.

## Decisions Made

- The guide keeps `work-vault/raw` -> `ls-vault` as the example but frames it as a replaceable raw-corpus-to-target-vault pattern.
- README uses the generic command shape `graphify update-vault --input <raw-corpus> --vault <target-vault>` while CLI help keeps the concrete canonical example for discoverability.
- Localized READMEs are intentionally untouched and excluded from this docs contract.

## Deviations from Plan

None - plan executed exactly as written.

**Total deviations:** 0 auto-fixed.
**Impact on plan:** Plan scope was preserved.

## Issues Encountered

- The Task 1 and Task 2 RED commits already existed in the working history when execution began; focused tests confirmed both RED states before GREEN changes were applied.
- The git hook prints ImageMagick `import` help before graph rebuilds; commits still completed successfully with normal hooks.
- `git add graphify/...` is blocked by the ignored `graphify` path unless staged with `git add -f`; the intended tracked file was staged explicitly.

## Known Stubs

None. Stub-pattern scan found no TODO, FIXME, placeholder, empty UI-data defaults, or hardcoded empty values in the files created or modified by this plan.

## Threat Flags

None. The changes are documentation, CLI help, and tests only; no new endpoint, auth path, file-access implementation, or schema trust boundary was introduced.

## TDD Gate Compliance

- Task 1 RED failed as expected on the missing migration guide, then GREEN passed after guide content was present.
- Task 2 RED failed as expected on missing README and CLI help phrases, then GREEN passed after README and help wording were aligned.

## Verification

- `pytest tests/test_docs.py -q` - 3 passed
- `pytest tests/test_docs.py tests/test_main_flags.py::test_update_vault_help_lists_command_shape -q` - 5 passed
- Acceptance greps passed for canonical command, backup prerequisite, rollback wording, README guide link, README update-vault guidance, and `graphify-out/migrations/archive/` wording in README and CLI help.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

Ready for Plan 36-03 to align shipped platform skill variants against the same v1.8 preview/apply/archive wording.

## Self-Check: PASSED

- Summary and all key files exist on disk.
- Task commits exist: `90ecce3`, `afc8ac1`, `2992437`, `dfd0ef5`, `ca24880`.
- Focused verification and acceptance checks passed.

---
*Phase: 36-migration-guide-skill-alignment-regression-sweep*
*Completed: 2026-04-29*

### Pending Todos

None.

### Blockers/Concerns

None. Research flags for planning:

- Phase 35 should research existing merge manifest/orphan mechanics before designing migration reporting.
- Phase 36 should audit platform skill variants for Obsidian export behavior drift.
- Any LLM naming plan must preserve offline behavior, budget gates, cache stability, and sanitization.

## Deferred Items

Items carried forward outside v1.8 scope:

| Category | Item | Status |
|----------|------|--------|
| seed | SEED-001 tacit-to-explicit elicitation | Dormant; revisit when onboarding/discovery is milestone theme |
| seed | SEED-002 multi-harness/inverse import | Deferred pending prompt-injection defenses |
| vault-selection | Explicit `--vault` flag and multi-vault selector | Future milestone |
| baseline-test | `test_detect_skips_dotfiles`, `test_collect_files_from_dir` | Separate `/gsd-debug` session |

## Session Continuity

Last session: 2026-04-29T07:44:36.284Z
Stopped at: Completed 36-01-PLAN.md
Next action: `/gsd-discuss-phase 36`
