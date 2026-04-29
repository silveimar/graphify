---
phase: 33-naming-repo-identity-helpers
plan: 03
subsystem: naming
tags: [concept-naming, cache, provenance, pytest, obsidian]

requires:
  - phase: 33-02
    provides: repo identity resolver and naming.concept_names profile controls
provides:
  - Stable ConceptName resolution for concept MOC titles
  - Community signatures based on sorted member IDs, labels, and source files
  - Deterministic fallback names with stable filename stems
  - concept-names.json sidecar cache/provenance IO with dry-run suppression
  - Unsafe LLM title rejection before names reach downstream sinks
affects: [phase-33, phase-34, phase-35, naming, export, templates]

tech-stack:
  added: []
  patterns:
    - Stdlib JSON sidecar with tmp + os.replace atomic persistence
    - Injectable llm_namer callable with deterministic offline fallback
    - NamedTuple provenance records for naming decisions

key-files:
  created: []
  modified:
    - graphify/naming.py

key-decisions:
  - "Concept naming cache/provenance is sidecar-only under the supplied artifacts directory."
  - "Fallback names use top graph terms plus a community/hash suffix to satisfy Wave 0 filename stability expectations."
  - "LLM candidates are treated as untrusted and rejected before cache persistence when they are generic, duplicate, path-like, template-breaking, wikilink-breaking, control-character-bearing, empty, or too long."

patterns-established:
  - "resolve_concept_names() always returns ConceptName records, even when naming is disabled, budget-blocked, rejected, or unavailable."
  - "Tolerant cache reuse requires strong top-term overlap and records previous/current signatures in the reason."

requirements-completed:
  - NAME-01
  - NAME-02
  - NAME-03
  - NAME-04
  - NAME-05

duration: 5min
completed: 2026-04-29
---

# Phase 33 Plan 03: Concept Naming Helper Summary

**Cache-backed concept MOC names with deterministic fallbacks, provenance sidecar records, and unsafe LLM title rejection**

## Performance

- **Duration:** 5 min
- **Started:** 2026-04-29T02:17:33Z
- **Completed:** 2026-04-29T02:22:20Z
- **Tasks:** 3
- **Files modified:** 1

## Accomplishments

- Replaced the reserved `resolve_concept_names()` placeholder with stable `ConceptName` resolution driven by community signatures and top graph terms.
- Added generated-artifact sidecar handling at `concept-names.json`, including tolerant corrupt-cache fallback, stable JSON writes, provenance records, and dry-run no-write behavior.
- Added LLM candidate validation for unsafe, generic, duplicate, path-like, template-breaking, wikilink-breaking, control-character-bearing, empty, and too-long names.

## Task Commits

Each implementation task was committed atomically:

1. **Task 1: Add community signatures and deterministic fallback names** - `fc43fc3` (feat)
2. **Task 2: Add cache/provenance IO and LLM candidate validation** - `1b37d3f` (feat)
3. **Task 3: Verify complete concept naming helper slice** - no code changes; verification-only task

## Files Created/Modified

- `graphify/naming.py` - Adds concept naming signatures, fallback titles, cache/provenance sidecar IO, tolerant cache matching, LLM candidate validation, and dry-run write suppression.

## Decisions Made

- Kept concept naming fully optional at runtime: when disabled, budget-blocked, unavailable, or rejected, the helper returns deterministic fallback names instead of failing.
- Stored cache entries by current community signature while preserving read compatibility with the existing Wave 0 legacy sidecar shape used by tests.
- Kept filename stem sanitation local to `graphify/naming.py` to avoid a circular import with `graphify.profile`, which already imports repo identity normalization from `graphify.naming`.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Avoided profile/naming circular import**
- **Found during:** Task 1 (Add community signatures and deterministic fallback names)
- **Issue:** Importing `safe_filename` from `graphify.profile` caused `profile.py` to import `normalize_repo_identity` from a partially initialized `graphify.naming` module.
- **Fix:** Added a local `_filename_stem()` helper that mirrors the existing filename safety rules needed for cached provenance while keeping final sink-specific sanitation in templates/profile.
- **Files modified:** `graphify/naming.py`
- **Verification:** `python3 -m pytest tests/test_naming.py::test_fallback_name_uses_terms_and_suffix tests/test_naming.py::test_same_signature_reuses_filename -q`
- **Committed in:** `fc43fc3`

**2. [Rule 1 - Bug] Matched fallback suffix to Wave 0 stability contract**
- **Found during:** Task 1 (Add community signatures and deterministic fallback names)
- **Issue:** A pure signature-prefix suffix produced stable names, but the existing Wave 0 test expected the community/hash suffix shape to include the community id for the fixture.
- **Fix:** Used `c{community_id}{signature[:2]}` for fallback suffixes, preserving deterministic signature influence while satisfying the locked test contract.
- **Files modified:** `graphify/naming.py`
- **Verification:** `python3 -m pytest tests/test_naming.py::test_fallback_name_uses_terms_and_suffix tests/test_naming.py::test_same_signature_reuses_filename -q`
- **Committed in:** `fc43fc3`

---

**Total deviations:** 2 auto-fixed (1 blocking, 1 bug)
**Impact on plan:** Both fixes were required for import correctness and existing contract compatibility; no new runtime surface or dependency was added.

## Verification

- Task 1 RED gate: focused fallback/signature tests failed on the reserved `NotImplementedError` placeholder.
- Task 1 focused gate: `python3 -m pytest tests/test_naming.py::test_fallback_name_uses_terms_and_suffix tests/test_naming.py::test_same_signature_reuses_filename -q` -> 2 passed.
- Task 2 RED gate: cache/provenance tests failed because cached names were ignored and rejected LLM candidates did not update provenance.
- Task 2 focused gate: `python3 -m pytest tests/test_naming.py::test_concept_name_uses_cached_llm_title tests/test_naming.py::test_concept_name_provenance_records_source tests/test_naming.py::test_unsafe_llm_title_rejected -q` -> 3 passed.
- Task 3 focused gate: `python3 -m pytest tests/test_naming.py -q` -> 8 passed.
- Wave gate: `python3 -m pytest tests/test_naming.py tests/test_profile.py -q` -> 192 passed, 1 xfailed.
- `ReadLints` on `graphify/naming.py` and `tests/test_naming.py` -> no linter errors reported.

## Known Stubs

None. The previous reserved `resolve_concept_names()` placeholder was replaced with working helper behavior.

## Threat Flags

None. This plan touches generated sidecar file IO under caller-supplied artifacts directories and untrusted LLM title validation already described by the plan threat model; it adds no network endpoints, auth paths, schema migrations, or vault-owned configuration writes.

## Issues Encountered

- The repository's git hook rebuilt `graphify-out` after each implementation commit and emitted an ImageMagick `import` usage banner before completing successfully.
- `graphify/*.py` is ignored by the user's global ignore rules, so `graphify/naming.py` had to be staged with `git add -f`.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

Plan 04 can consume `resolve_concept_names()` from export/CLI wiring to feed MOC labels, generated paths, dry-run previews, and later migration reporting without adding a network dependency.

## Self-Check: PASSED

- Found summary file at `.planning/phases/33-naming-repo-identity-helpers/33-03-SUMMARY.md`.
- Found modified helper file at `graphify/naming.py`.
- Verified task commits exist with `git cat-file`: `fc43fc3`, `1b37d3f`.

---
*Phase: 33-naming-repo-identity-helpers*
*Completed: 2026-04-29*
