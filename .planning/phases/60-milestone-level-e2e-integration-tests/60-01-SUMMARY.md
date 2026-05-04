---
phase: 60-milestone-level-e2e-integration-tests
plan: "01"
subsystem: testing
tags:
  - e2e
  - subprocess
  - tdd
  - vault-adapter
  - profile-composition
  - override-ladder

dependency_graph:
  requires:
    - Phase 55 (note_type_templates block expansion)
    - Phase 56 (mapping_rule_templates override ladder)
    - Phase 60.1 (update-vault apply determinism fix — Leiden random_seed=42)
  provides:
    - E2E-01 subprocess regression test for Phase 55+56 composition contract
    - _graphify, _write_vault, _write_corpus, _read_frontmatter, _run_update_vault_preview_then_apply helpers for Plan 02 reuse
  affects:
    - tests/test_e2e_integration.py

tech_stack:
  added: []
  patterns:
    - subprocess E2E test via python -m graphify
    - two-step preview->apply CLI contract
    - inline YAML vault fixture with tmp_path
    - YAML frontmatter parse assertion + targeted body substring assertions

key_files:
  created:
    - tests/test_e2e_integration.py
  modified: []

decisions:
  - _graphify helper defined locally in test file (not promoted to conftest.py — deferred per CONTEXT.md)
  - Inline YAML profile per-test, not shared fixture, to keep tests self-contained
  - Module-level constants _OUTPUT_PATH and _OVERRIDE_SENTINEL for strings used 3+ times
  - No community_templates in inline profile (Pitfall 4 avoidance — keeps test isolated to mrt->ntt->base path)

metrics:
  duration: "~9 hours total (test written at commit 333d2da; Phase 60.1 determinism fix was prerequisite)"
  completed: 2026-05-04
  tasks_completed: 3
  files_changed: 1
---

# Phase 60 Plan 01: E2E-01 Subprocess Test for Compose+Override Ladder Summary

One-liner: E2E subprocess test locking down Phase 55+56 composition (note_type_templates block expansion + mapping_rule_templates override ladder) through the real graphify update-vault CLI pipeline.

## What Was Built

`tests/test_e2e_integration.py` — 264 lines, one test function plus five local helpers.

**Test:** `test_e2e_compose_override_ladder` exercises the two-step preview->apply CLI contract end-to-end via subprocess.run calls against a tmp_path vault with an inline profile that exercises BOTH `note_type_templates` (pattern: thing) AND `mapping_rule_templates` (pattern: e2e-test-rule, intentionally non-matching) to prove the ladder falls through to ntt when mrt does not match.

**Helpers (all local, all reusable by Plan 02):**
- `_graphify(args, cwd, env=None)` — subprocess invoke with PYTHONPATH injection and GRAPHIFY_ELICIT_LLM pop
- `_read_frontmatter(p)` — YAML frontmatter parser for assertion on type/tags/community/cohesion
- `_write_vault(tmp_path, profile_yaml, *, templates=None)` — creates .obsidian/, .graphify/profile.yaml, optional template files
- `_write_corpus(tmp_path)` — writes a fixed 2-class Python corpus (TransformerLayer + AttentionHead)
- `_run_update_vault_preview_then_apply(corpus, vault)` — orchestrates preview, plan_id harvest, then apply; returns output_root Path

**D-16 ordering invariant locked:** The ntt-thing.md override template contains both `{{#connections}}...{{/connections}}` (block) AND `${label}` (substitution) plus the sentinel `OVERRIDE_NTT_THING_MARKER`. Assertions verify sentinel present + block expanded + placeholders fully substituted, proving block expansion runs BEFORE `${}` substitution.

## TDD Gate Compliance

- RED gate: commit 333d2da — `test(60-01): add failing E2E-01 subprocess test for compose+override ladder` — test was failing at commit time due to real upstream determinism bug (plan_id non-determinism between consecutive preview runs, escalated per CONTEXT scope boundary)
- GREEN gate: Phase 60.1 (commits e110ead through 6eddd83) fixed the Leiden random_seed determinism issue; test became GREEN without changes to the test file
- REFACTOR gate: file was already in clean state; all assertion sites use `assert result.returncode == 0, f"stderr={result.stderr!r}"` pattern; textwrap.dedent used consistently for all multiline literals; module-level constants for strings used 3+ times

## Deviations from Plan

### Auto-fixed Issues

None — plan executed exactly as written.

### Context Note: Phase 60.1 Prerequisite

The RED gate (Task 1) was completed in a prior execution attempt (commit 333d2da). The test was intentionally failing because the underlying prod-code had a non-determinism bug (Leiden clustering used no fixed seed, so plan_ids differed between the preview call and the apply call). Rather than self-healing by fixing prod code (which CONTEXT.md explicitly prohibits for this phase), the prior executor correctly escalated as a checkpoint. Phase 60.1 was inserted to fix the issue; after those commits, the test became GREEN without any changes to the test file.

This execution (Phase 60 Plan 01 re-execution) confirmed:
- Task 1 (RED) commit exists at 333d2da
- Task 2 (GREEN) is satisfied: `pytest tests/test_e2e_integration.py::test_e2e_compose_override_ladder -q` exits 0 (1 passed in ~14.6s)
- Task 3 (REFACTOR) confirmed file is already clean
- Full regression suite: 2122 passed, 1 xfailed, 0 failures

## Known Stubs

None.

## Threat Flags

None — test-only file, no new network endpoints or auth paths introduced.

## Self-Check: PASSED

- `tests/test_e2e_integration.py` exists: FOUND
- Commit 333d2da exists: FOUND
- `pytest tests/test_e2e_integration.py::test_e2e_compose_override_ladder -q` exits 0: VERIFIED
- All Task 1 grep gates: VERIFIED
- Full suite 2122 passed: VERIFIED
