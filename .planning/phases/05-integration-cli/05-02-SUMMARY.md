---
phase: 05-integration-cli
plan: 02
subsystem: profile
tags: [preflight, validation, named-tuple, d-77, prof-05]
dependency_graph:
  requires: [01-foundation/01-01, 02-template-engine, 03-mapping-engine]
  provides: [PreflightResult, validate_profile_preflight]
  affects: [graphify/profile.py, tests/test_profile.py]
tech_stack:
  added: [typing.NamedTuple]
  patterns: [four-layer composite validator, function-local imports to avoid circular deps, TDD RED-GREEN]
key_files:
  modified:
    - graphify/profile.py
    - tests/test_profile.py
decisions:
  - "Early return when .graphify dir absent: all counts zero — N/M suffix reflects user-authored overrides only (D-77a)"
  - "Function-local imports for templates.validate_template and mapping._detect_dead_rules to avoid circular import cycles"
  - "No .graphify dir check added before loading profile YAML — prevents default-profile path-safety warnings on fresh vaults"
metrics:
  duration: 3m 29s
  completed: 2026-04-11T20:45:21Z
  tasks_completed: 2
  files_modified: 2
---

# Phase 05 Plan 02: Preflight Validator (PreflightResult + validate_profile_preflight) Summary

**One-liner:** Four-layer composite preflight validator returning `PreflightResult(errors, warnings, rule_count, template_count)` NamedTuple with D-77 schema/template/dead-rule/path-safety checks and D-77a N/M suffix support.

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 (RED) | Add failing preflight tests to tests/test_profile.py | 3622afc | tests/test_profile.py |
| 1 (GREEN) | Add PreflightResult NamedTuple + validate_profile_preflight | b5fa932 | graphify/profile.py |
| 2 | Tests verified passing (all 116 tests green, 11 new preflight tests) | b5fa932 | tests/test_profile.py |

## What Was Built

`PreflightResult` is a `typing.NamedTuple` with four fields:
- `errors: list[str]` — layer 1 (schema) + layer 2 (template) errors; non-empty → skill exits 1
- `warnings: list[str]` — layer 3 (dead rules) + layer 4 (path safety) warnings; never block exit 0
- `rule_count: int` — `len(merged_profile["mapping_rules"])` for D-77a N/M suffix
- `template_count: int` — count of `.graphify/templates/<type>.md` files that passed layer 2

`validate_profile_preflight(vault_dir)` runs four independent passes:
1. **Schema (errors):** calls existing `validate_profile(user_data)` on the raw user dict
2. **Templates (errors):** for every `.graphify/templates/<type>.md` present, calls `validate_template(text, required)` from `templates.py`; failed templates do NOT increment `template_count`
3. **Dead rules (warnings):** calls `_detect_dead_rules(rules)` from `mapping.py`
4. **Path safety (warnings):** checks folder segment count > 4 and simulated full-path length > 240 chars (Windows MAX_PATH headroom)

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] No-.graphify-dir early return missing in plan spec**
- **Found during:** GREEN phase - test `test_validate_profile_preflight_no_graphify_dir` failed
- **Issue:** When no `.graphify/` directory exists, the function still merged with `_DEFAULT_PROFILE` and ran layer 4 path-safety checks against the default `Atlas/Maps/`, `Atlas/Dots/Things/` etc. folders. The tmp_path prefix was long enough to trigger "worst-case path length exceeds 240-char budget" warnings, contradicting the spec: "no .graphify dir → PreflightResult(errors=[], warnings=[], rule_count=0, template_count=0)"
- **Fix:** Added early return immediately after checking `graphify_dir.exists()` — returns zero-everything before any layers run. This is correct per D-77a semantics: "N/M suffix reflects user-authored overrides only"
- **Files modified:** graphify/profile.py
- **Commit:** b5fa932

## Known Stubs

None — all preflight logic fully implemented and exercised.

## Threat Surface Scan

No new network endpoints, auth paths, or file write paths introduced. `validate_profile_preflight` is strictly read-only. T-05-04 (template path confinement) mitigated via `validate_vault_path()` call before each template read, as specified in threat register.

## Self-Check: PASSED

- [x] `graphify/profile.py` exists and contains `class PreflightResult(NamedTuple):`
- [x] `graphify/profile.py` contains `def validate_profile_preflight(`
- [x] `graphify/profile.py` contains `_PATH_SAFETY_MAX_LEN = 240`
- [x] `graphify/profile.py` contains `_PATH_SAFETY_MAX_SEGMENTS = 4`
- [x] `grep -n "from graphify.templates import" graphify/profile.py` shows indented (line 540)
- [x] Commits 3622afc and b5fa932 exist
- [x] `pytest tests/test_profile.py -q` → 116 passed
