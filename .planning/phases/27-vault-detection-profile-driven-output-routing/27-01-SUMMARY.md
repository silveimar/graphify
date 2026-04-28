---
phase: 27-vault-detection-profile-driven-output-routing
plan: 01
subsystem: profile-schema
tags: [profile-schema, validation, sibling-of-vault, vault-adapter, vault-10]
requires: [VAULT-10]
provides:
  - "_VALID_OUTPUT_MODES constant"
  - "output: schema branch in validate_profile()"
  - "validate_sibling_path() helper"
affects:
  - graphify/profile.py
  - tests/test_profile.py
tech-stack:
  added: []
  patterns:
    - "schema validator branch (mirrors profile_sync, folder_mapping patterns)"
    - "use-time path resolver (mirrors validate_vault_path)"
key-files:
  created: []
  modified:
    - graphify/profile.py
    - tests/test_profile.py
decisions:
  - "D-01 (schema): output: { mode, path } with three modes"
  - "D-02 (no default output): _DEFAULT_PROFILE deliberately omits 'output' so D-05 missing-key signal can fire in Plan 27-02"
  - "D-03 (sibling deferred): sibling-of-vault path validation lives in validate_sibling_path() called at use-time, not at static schema validation"
metrics:
  duration: ~10m
  tasks_completed: 2
  files_modified: 2
  tests_added: 20
  tests_passing: 158
  completed: 2026-04-27
---

# Phase 27 Plan 01: Profile Schema — output: Block + Sibling-of-Vault Validator Summary

Extended `graphify/profile.py` with the new `output: { mode, path }` profile block schema (3 modes — vault-relative / absolute / sibling-of-vault) and the `validate_sibling_path()` helper that authorizes the deliberate one-parent escape for `mode: sibling-of-vault` while rejecting all 5 traversal classes plus the filesystem-root corner case.

## What Was Built

### `graphify/profile.py`

1. **`_VALID_OUTPUT_MODES`** — new module-level set `{"vault-relative", "absolute", "sibling-of-vault"}` placed after `_VALID_NAMING_CONVENTIONS`.
2. **`_VALID_TOP_LEVEL_KEYS`** — `"output"` added to the existing 10-key allow-list (so unknown-key guard still fires for typos like `"foo"`).
3. **`validate_profile()` output branch** — appended after the `profile_sync` branch. Validates:
   - `output` is a dict
   - `mode` and `path` keys both present
   - `mode` is one of the 3 valid values
   - `path` is a non-empty string
   - For `mode: vault-relative` → rejects absolute paths, `~`-prefix, and `..` segments at schema time
   - For `mode: absolute` → requires absolute filesystem path at schema time
   - For `mode: sibling-of-vault` → schema only validates shape; path-level checks deferred to `validate_sibling_path()` (vault_dir unknown at static-validation time)
4. **`validate_sibling_path(candidate, vault_dir) -> Path`** — new public function placed immediately after `validate_vault_path()`. Raises `ValueError` for:
   - empty/whitespace-only candidate (or non-`str`)
   - candidate starting with `~`
   - absolute candidate
   - candidate containing `..` segments
   - `vault_base.parent == vault_base` (filesystem-root corner)
   - resolved path that escapes `<vault>.parent` (defense-in-depth `relative_to` check)
   Returns `(parent / candidate).resolve()` for valid input.
5. **`_DEFAULT_PROFILE`** — left untouched (Pitfall 1 / D-02 invariant: no default `output` so Plan 27-02's "refuse loudly when vault detected without explicit destination" path can fire).

### `tests/test_profile.py`

20 new tests appended (target was ≥13):
- 11 schema tests covering valid 3 modes, missing/empty/invalid keys, vault-relative rejections (absolute, ~, ..), absolute mode requires absolute path
- 1 invariant test (`_DEFAULT_PROFILE.get("output") is None`)
- 1 regression test (unknown-key guard still catches `"foo"` after `"output"` added)
- 6 `validate_sibling_path` edge-case tests (empty, ~, absolute, .. — two variants, filesystem-root, happy path)

## Verification

- `pytest tests/test_profile.py -q` → **158 passed, 1 xfailed** (was 138 passed, 1 xfailed pre-change → +20 new tests, no regressions)
- All acceptance criteria from plan met (constants present, function exists with docstring, default profile has no `output` key, all named tests pass)

## Threats Mitigated

| Threat ID | Mitigation |
|-----------|------------|
| T-27-01 (Tampering — vault-relative path) | Schema rejects absolute / `~` / `..` at validation time |
| T-27-02 (Tampering — sibling path traversal) | `validate_sibling_path()` rejects all 5 traversal classes; defense-in-depth `relative_to(parent)` check |
| T-27-03 (Information Disclosure — silent default `output`) | `_DEFAULT_PROFILE` deliberately omits `output`; asserted by `test_default_profile_has_no_output_key` |
| T-27-04 (DoS — filesystem-root corner) | `validate_sibling_path()` raises actionable `ValueError` instead of silently producing `/<candidate>` |

## Decisions Implemented

- **D-01** — `_VALID_TOP_LEVEL_KEYS` includes `"output"`; `_VALID_OUTPUT_MODES` defined with exactly 3 modes.
- **D-02** — `_DEFAULT_PROFILE.get("output") is None` (verified by test).
- **D-03** — `validate_sibling_path()` covers all 5 rejection branches + happy path; schema does NOT call it (deferred to use-time when `vault_dir` is known in Plan 27-02).

## Requirement Addressed

- **VAULT-10 (schema half)** — Profile YAML now accepts `output: { mode, path }` with three valid modes; invalid configurations rejected by `validate_profile()` with actionable error messages. The use-time half (resolution + write-time confinement) is owned by Plan 27-02.

## Deviations from Plan

None — plan executed exactly as written. Inline Task 1 verify (Python one-liner) and Task 2 pytest verify both pass cleanly.

## Files Modified

| File | Change |
|------|--------|
| `graphify/profile.py` | +71 lines: `_VALID_OUTPUT_MODES` constant, `"output"` in allow-list, output branch in `validate_profile()`, `validate_sibling_path()` function |
| `tests/test_profile.py` | +112 lines: 20 new tests (header comments + 2 sub-sections) |

## Commits

- `06c678b` feat(27-01): add output: schema validation to profile.py
- `2d2d58d` feat(27-01): add validate_sibling_path() + output-block tests

## Self-Check: PASSED

- FOUND: `graphify/profile.py` (modified) — `_VALID_OUTPUT_MODES`, `validate_sibling_path` both present
- FOUND: `tests/test_profile.py` (modified) — 20 new tests, all green
- FOUND: commit `06c678b` in `git log`
- FOUND: commit `2d2d58d` in `git log`
- VERIFIED: `pytest tests/test_profile.py -q` → 158 passed, 1 xfailed (no regressions vs. baseline 138 passed)
