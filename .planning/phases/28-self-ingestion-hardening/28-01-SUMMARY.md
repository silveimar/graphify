---
phase: 28-self-ingestion-hardening
plan: "01"
subsystem: output-schema
tags: [vault-adapter, schema, tdd, namedtuple, validation]
dependency_graph:
  requires:
    - phases/27-vault-detection-profile-driven-output-routing/27-02-SUMMARY.md
  provides:
    - ResolvedOutput.exclude_globs field (6th field, tuple[str, ...])
    - validate_profile() output.exclude validation (D-17)
  affects:
    - graphify/output.py
    - graphify/profile.py
    - tests/test_output.py
    - tests/test_profile.py
tech_stack:
  added: []
  patterns:
    - NamedTuple trailing default field (Python 3.6.1+ / 3.10+ CI)
    - validate_profile errors-accumulator pattern (list[str], no raising)
    - Path(item.lstrip("/")).parts traversal check (consistent with vault-relative path validation)
key_files:
  created: []
  modified:
    - graphify/output.py
    - graphify/profile.py
    - tests/test_output.py
    - tests/test_profile.py
decisions:
  - "D-14: exclude_globs as 6th trailing-default field on ResolvedOutput; tuple for immutability"
  - "D-15: exclude globs always apply when profile loaded; --output flag governs destination only"
  - "D-17: validate_profile() loud-fails on 5 malformed shapes (non-list, non-string, empty, absolute, traversal)"
metrics:
  duration_minutes: 3
  completed_date: "2026-04-28"
  tasks_completed: 3
  tasks_total: 3
  files_modified: 4
requirements: [VAULT-11]
---

# Phase 28 Plan 01: VAULT-11 Schema Foundation Summary

ResolvedOutput gains a 6th field `exclude_globs: tuple[str, ...] = ()` populated from `profile.output.exclude`; `validate_profile()` rejects five malformed exclude shapes at load time.

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 | RED tests for exclude_globs field and output.exclude validation | 99b2af6 | tests/test_output.py, tests/test_profile.py |
| 2 | Extend ResolvedOutput with exclude_globs and populate in resolve_output() | 094b90d | graphify/output.py |
| 3 | Extend validate_profile() with output.exclude validation | 11979a7 | graphify/profile.py |

## What Was Built

**graphify/output.py** — `ResolvedOutput` NamedTuple extended with a 6th field `exclude_globs: tuple[str, ...] = ()`. The vault+profile branch of `resolve_output()` now reads `profile["output"]["exclude"]` and tuple-casts it; malformed values (non-list) degrade gracefully to `()`. The cli-flag and default branches inherit the empty-tuple default transparently.

**graphify/profile.py** — `validate_profile()` output: branch extended with D-17 validation block appended after the existing mode/path checks. Rejects: non-list `exclude`, per-item non-string, empty/whitespace-only, absolute path, and `..` traversal. Valid glob lists (e.g., `["**/cache/**", "*.tmp"]`) accumulate zero errors.

**tests/test_output.py** — Two existing tests updated to expect 6 fields. Four new tests added: default empty tuple, populated from profile YAML, empty on cli-flag branch, empty on default branch.

**tests/test_profile.py** — Six new `test_validate_profile_output_exclude_*` tests added covering all five rejection shapes plus one valid-list acceptance.

## TDD Gate Compliance

| Gate | Commit | Status |
|------|--------|--------|
| RED (test) | 99b2af6 | 11 tests failing as expected |
| GREEN (feat x2) | 094b90d, 11979a7 | All 12 target tests pass |
| REFACTOR | n/a | No refactor needed |

## Verification

- `pytest tests/test_output.py tests/test_profile.py -q` — 189 passed, 1 xfailed
- `pytest tests/ -q` — 1657 passed, 1 xfailed, 8 warnings (no regressions; +10 tests vs baseline 1647)
- `python -c "from graphify.output import ResolvedOutput; print(ResolvedOutput._fields)"` confirms 6-field tuple ending with `exclude_globs`

## Deviations from Plan

None — plan executed exactly as written.

## Known Stubs

None — `exclude_globs` is fully populated from the profile and consumed by downstream plans (28-02).

## Threat Flags

No new network endpoints, auth paths, or file access patterns introduced. The traversal and absolute-path rejections in `validate_profile()` directly mitigate T-28-01 through T-28-04 as specified in the plan threat model.

## Self-Check: PASSED

- `graphify/output.py` exists and contains `exclude_globs: tuple[str, ...] = ()` — FOUND
- `graphify/profile.py` exists and contains `output.exclude must be a list` — FOUND
- `tests/test_output.py` exists and contains 12 references to `exclude_globs` — FOUND
- `tests/test_profile.py` exists and contains 6 `test_validate_profile_output_exclude_*` tests — FOUND
- Commits 99b2af6, 094b90d, 11979a7 — FOUND
