---
phase: 60-milestone-level-e2e-integration-tests
plan: "02"
subsystem: testing
tags:
  - testing
  - e2e
  - subprocess
  - elicit
  - sidecar-merge
  - vault-adapter
dependency_graph:
  requires:
    - "60-01"  # test_e2e_integration.py file created by Plan 01
  provides:
    - "E2E-02"  # elicit-sidecar → update-vault merge regression lock
  affects:
    - tests/test_e2e_integration.py
tech_stack:
  added: []
  patterns:
    - TDD RED/GREEN/REFACTOR with subprocess E2E tests
    - Module-level YAML/literal constants shared across test functions
    - elicit --demo → update-vault sidecar auto-discovery contract
key_files:
  modified:
    - tests/test_e2e_integration.py
decisions:
  - "Assertion targets corrected: rationale nodes appear as title-cased community MOC name/tag, NOT as verbatim labels in note bodies (_MEMBER_GROUP_ORDER excludes rationale)"
  - "_BASE_PROFILE_YAML extracted as shared module-level constant; _PROFILE_YAML_E2E_01 composed from base + extra blocks"
  - "_DEMO_ANSWER_LITERALS retained as module-level contract reference even though assertions use derived community name/tag forms"
  - "elicit call must pass --vault <vault> to align artifacts_dir with update-vault (RESEARCH Pitfall 3)"
metrics:
  duration: "~100 minutes"
  completed: "2026-05-04"
  tasks_completed: 3
  files_changed: 1
---

# Phase 60 Plan 02: E2E-02 Elicit Sidecar → Update-Vault Merge Summary

**One-liner:** E2E subprocess test locking Phase 57 elicit sidecar → Phase 56 update-vault merge handoff via community-MOC presence assertions.

## What Was Built

Appended `test_e2e_elicit_then_update_vault` to `tests/test_e2e_integration.py`, adding:

- `_BASE_PROFILE_YAML` — module-level constant holding the shared profile shell (extracted from Plan 01's inline string; `_PROFILE_YAML_E2E_01` now composes base + extension blocks)
- `_DEMO_ANSWER_LITERALS` — module-level tuple of locked demo answer strings from `__main__.py:2563-2570`
- `test_e2e_elicit_then_update_vault` — three-subprocess E2E test validating the Phase 57 + Phase 56 handoff:
  1. `graphify --vault <vault> elicit --demo` → sidecar at `<vault>.parent/graphify-out/elicitation.json`
  2. `graphify update-vault … (preview)` → migration plan JSON
  3. `graphify update-vault … --apply --plan-id` → notes materialised in vault

The test asserts sidecar structure (hub + ≥3 dimension nodes), community MOC presence (title-cased "Elicitation Session" in bodies), and community tag derivation (`community/elicitation-session` prefix in bodies).

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Wrong assertion target] Corrected elicitation visibility assertions**

- **Found during:** Task 2 (GREEN)
- **Issue:** RESEARCH section "Elicitation visibility assertion targets" claimed demo answer literals appear "via the members section / wikilinks". In practice, `rationale` file_type nodes are NOT included in `_MEMBER_GROUP_ORDER` (which only covers `thing`, `statement`, `person`, `source`), so individual elicitation dimension nodes do not appear in members sections, and their labels ("Daily standup, weekly retro" etc.) do not appear in any rendered note body. The hub label "Elicitation session" also doesn't appear verbatim — it appears title-cased as part of the community name "Elicitation Session Are c0b5".
- **Fix:** Changed assertions to check for:
  - `"Elicitation Session"` (title-cased form, present in community MOC heading and frontmatter)
  - `"community/elicitation-session"` (community tag prefix derived from hub label, proves merge occurred)
  - Retained all sidecar structure assertions unchanged (hub + dimensions are correctly present in JSON)
- **Evidence that merge works:** The elicitation hub node merges into the graph and forms a community; the MOC note for that community has a name and tag derived from the hub label. This is the correct observable evidence of the contract.
- **Files modified:** `tests/test_e2e_integration.py`
- **Commits:** b6378b9 (GREEN), a7d6617 (REFACTOR docstring)

## TDD Gate Compliance

- RED commit: 33bf1c7 — `test(60-02): RED — append test_e2e_elicit_then_update_vault`
- GREEN commit: b6378b9 — `feat(60-02): GREEN — test_e2e_elicit_then_update_vault passes`
- REFACTOR commit: a7d6617 — `refactor(60-02): update docstring to reflect actual rationale-node rendering contract`

All three gates present in correct order.

## Decisions Made

1. **Assertion target correction (Rule 1):** RESEARCH incorrectly predicted demo literals appear in note bodies; actual behavior is community MOC name/tag derivation. Test uses the correct observable form.

2. **_BASE_PROFILE_YAML extraction:** Shared profile base extracted to deduplicate between E2E-01 and E2E-02. Plan 01's `_PROFILE_YAML_E2E_01` refactored to `_BASE_PROFILE_YAML + extension_blocks`.

3. **_DEMO_ANSWER_LITERALS retained:** Module-level constant kept as a contract reference documenting the locked demo answer strings, even though the test assertions use derived community-name forms rather than literal string presence. Useful for future tests that may check individual node labels at a different layer (e.g. graph JSON, not rendered notes).

4. **Pitfall 3 compliance enforced:** `elicit` call passes `--vault <vault>` explicitly so `artifacts_dir` resolves to `<vault>.parent/graphify-out` — same path `update-vault` reads.

## Known Stubs

None.

## Threat Flags

None — test-infra-only changes; no new network endpoints, auth paths, file access patterns, or schema changes.

## Self-Check: PASSED

- `tests/test_e2e_integration.py` exists and parses as valid Python
- `test(60-02)` RED commit 33bf1c7: confirmed in git log
- `feat(60-02)` GREEN commit b6378b9: confirmed in git log
- `refactor(60-02)` REFACTOR commit a7d6617: confirmed in git log
- `pytest tests/test_e2e_integration.py -q` → 2 passed
- `pytest tests/ -q` → 2123 passed, 1 xfailed, 0 failures
