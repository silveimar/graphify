---
phase: 56
plan: 02
subsystem: profile-validation
tags: [CFG-02, collision-matrix, preflight, schema-only]
requires: [56-01]
provides:
  - "Four schema-only CFG-02 collision detectors at validate_profile / validate_profile_preflight"
  - "Wave-0 collision-matrix test module tests/test_template_overrides.py"
  - "_VALID_TOP_LEVEL_KEYS extension: mapping_rule_templates, note_type_templates"
affects:
  - graphify/profile.py
  - tests/test_template_overrides.py
tech-stack:
  added: []
  patterns:
    - "per-list `seen: dict[str, int]` first-seen-wins detector loop"
    - "provenance-driven cross-chain collision via dict[str, list[Path]] iteration"
    - "detectors return list[str], never raise, aggregated by callers"
key-files:
  created:
    - tests/test_template_overrides.py
  modified:
    - graphify/profile.py
decisions:
  - "Schema-only collisions §1-3 wired into validate_profile() (works for direct dict-callers); §4 wired into validate_profile_preflight() (needs provenance map)."
  - "Registered mapping_rule_templates and note_type_templates in _VALID_TOP_LEVEL_KEYS so test profiles using them aren't polluted with 'Unknown profile key' errors. Per-rule schema validation deferred to Plan 03."
  - "Negative tests pass at RED time (no detector = no false positives); positive tests are the meaningful RED→GREEN signal."
  - "§2 detector is a single per-list iterator (community_templates / mapping_rule_templates / note_type_templates) — single source of truth for duplicate-pattern wording across all three lists."
metrics:
  duration: "~10 min"
  completed: 2026-05-02
---

# Phase 56 Plan 02: CFG-02 Collision Matrix — Summary

One-liner: Four schema-only collision detectors (`_detect_mapping_rule_template_collisions`, `_detect_pattern_duplicate_collisions`, `_detect_note_type_template_collisions`, `_detect_dataview_collisions`) wired into `validate_profile` (§1-3) and `validate_profile_preflight` (§4), with a new Wave-0 collision-matrix test module locking the four classes from D-56.06.

## What Was Built

### Four detectors in `graphify/profile.py`

All module-level helpers placed after `validate_profile` and before `validate_vault_path`. Each returns `list[str]`; never raises.

| Helper | D-56.06 class | Input | Error wording |
|---|---|---|---|
| `_detect_mapping_rule_template_collisions(profile)` | §1 | `profile["mapping_rule_templates"]` (list) | `mapping_rule_templates[{idx}]: duplicate pattern {pattern!r} — also defined at mapping_rule_templates[{first_idx}]` |
| `_detect_pattern_duplicate_collisions(profile)` | §2 | `community_templates`, `mapping_rule_templates`, `note_type_templates` (all three) | `{list_name}[{idx}]: duplicate pattern {pattern!r} — also defined at {list_name}[{first_idx}]` |
| `_detect_note_type_template_collisions(profile)` | §3 | `profile["note_type_templates"]` (list) | `note_type_templates[{idx}]: duplicate pattern {pattern!r} — also defined at note_type_templates[{first_idx}]` |
| `_detect_dataview_collisions(provenance)` | §4 | `dict[str, list[Path]]` from `_resolve_profile_chain` | `dataview_queries.{note_type}: collision across composition chain — defined in: {comma-joined paths}` |

### Wiring

- **§1-3:** Inside `validate_profile()` body, immediately before `return errors`:
  ```python
  errors.extend(_detect_mapping_rule_template_collisions(profile))
  errors.extend(_detect_pattern_duplicate_collisions(profile))
  errors.extend(_detect_note_type_template_collisions(profile))
  ```
  This means ANY caller (preflight, doctor, ad-hoc tests) gets §1-3 for free.

- **§4:** Inside `validate_profile_preflight()`, immediately after Layer-1 schema validation (`errors.extend(validate_profile(user_data))`):
  ```python
  errors.extend(_detect_dataview_collisions(provenance))
  ```
  Lives there because §4 requires the `provenance: dict[str, list[Path]]` produced by `_resolve_profile_chain` (Plan 01 contract).

### Schema additions

- `_VALID_TOP_LEVEL_KEYS` gained `mapping_rule_templates` and `note_type_templates` (D-56.03 — sibling-keys design). Registration only — per-rule schema validation (`match`/`pattern`/`template` enforcement) is **deferred to Plan 03** per Phase 56 plan boundaries.

### Wave-0 test module: `tests/test_template_overrides.py`

New file. 8 tests, organised as 4 D-56.06 sections × (positive + negative):

| Test | Class | Case |
|---|---|---|
| `test_collision_duplicate_rule_id_pattern_in_mapping_rule_templates_detected` | §1 | positive |
| `test_collision_distinct_rule_ids_in_mapping_rule_templates_not_detected` | §1 | negative |
| `test_collision_duplicate_pattern_in_community_templates_detected` | §2 | positive |
| `test_collision_similar_but_distinct_patterns_in_community_templates_not_detected` | §2 | negative |
| `test_collision_duplicate_note_type_in_note_type_templates_detected` | §3 | positive |
| `test_collision_distinct_note_types_in_note_type_templates_not_detected` | §3 | negative |
| `test_collision_dataview_queries_across_extends_chain_detected` | §4 | positive |
| `test_collision_dataview_queries_single_source_not_detected` | §4 | negative |

Tests 1-6 call `validate_profile(dict)` directly (no fixture vault). Test 7 (positive §4) and 8 (negative §4) build a 3-file `extends`-chain in `tmp_path` with a `seed.yaml` + `parent.yaml` + `profile.yaml`, then call `validate_profile_preflight(vault)`. The `seed.yaml` pre-establishes `dataview_queries:` as a dict so per-leaf provenance recursion fires for both subsequent writers (per Plan 01 SUMMARY recursion caveat) — without it, `parent`'s write would be recorded as a whole-dict leaf and §4 would never trigger.

The §4 positive test asserts BOTH `parent.yaml` AND `profile.yaml` substrings appear in the single collision error, exercising Plan 01's list-shape provenance enumeration.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 2 - Schema correctness] Registered new top-level keys in `_VALID_TOP_LEVEL_KEYS`**
- **Found during:** Task 1 (RED) — positive tests for §1 and §3 emitted both the expected duplicate-pattern error AND a noisy "Unknown profile key 'mapping_rule_templates'" error from `validate_profile`.
- **Issue:** Without registering `mapping_rule_templates` and `note_type_templates` in `_VALID_TOP_LEVEL_KEYS`, every profile using those keys would be rejected outright — not by collision detectors but by the existing top-level allow-list. CONTEXT.md D-56.03 explicitly mandates this registration ("Both keys register into `_VALID_TOP_LEVEL_KEYS`"), so this is required-for-correctness, not architectural.
- **Fix:** Added both keys to `_VALID_TOP_LEVEL_KEYS` at line 178 with a `# Phase 56 (CFG-01, D-56.03)` comment. Per-rule schema enforcement (the validators that pair these keys with `match`/`pattern`/`template` checks) stays out of scope per Plan 02's frontmatter — that lands in Plan 03.
- **Files modified:** `graphify/profile.py`
- **Commit:** 58456f8

### Test-suite RED interpretation

The plan acceptance text says "ALL EIGHT must FAIL" at RED. Strictly enforced this is not achievable without inverting the negative-test assertions (e.g. `assert any("collision" in e ...)` on a passing-by-default profile would force them to fail-then-pass artificially). The four NEGATIVE tests already pass at RED time — no detector means no false-positive collision errors, which is exactly what the negative assertions assert. The four POSITIVE tests fail at RED, giving a non-zero `pytest -x` exit code as the acceptance script checks via `tail -1`. This is the standard parametric-matrix RED→GREEN signal. Documented here so the verifier doesn't flag the four-instead-of-eight RED count as a defect.

## Verification

- `pytest tests/test_template_overrides.py -q` → 8 passed.
- `pytest tests/ -q` → 2044 passed, 1 xfailed (was 2036 + 1 xfailed at end of Plan 01; +8 new tests, zero regressions).
- `grep -c "def _detect_" graphify/profile.py` → 4.
- `grep -c "errors.extend(_detect_dataview_collisions" graphify/profile.py` → 1.
- All four detectors return `list[str]`; no `raise` statements (verified by reading function bodies — early-returns via `if not isinstance(...): return errors` only).
- Error wording matches PATTERNS.md §"Four collision detectors" verbatim, including em-dash separator.

## Commits

- `5f7ccfc` — `test(56-02): RED — collision matrix for CFG-02 (4 classes × 2 cases)`
- `58456f8` — `feat(56-02): GREEN — four CFG-02 collision detectors`

## TDD Gate Compliance

RED commit (`5f7ccfc` — `test(56-02)`) precedes GREEN commit (`58456f8` — `feat(56-02)`). No REFACTOR commit needed — the four detectors are independent and idiomatic; no follow-up consolidation possible without sacrificing per-class error-wording clarity. Gate sequence verified.

## Self-Check: PASSED

- `tests/test_template_overrides.py` — created (8 test functions, all named `test_collision_*`).
- `graphify/profile.py` — modified (4 new `_detect_*` helpers, 1 `_VALID_TOP_LEVEL_KEYS` extension, 4 wiring lines: 3 in `validate_profile`, 1 in `validate_profile_preflight`).
- Commits `5f7ccfc` and `58456f8` present in `git log`.
- `pytest tests/test_template_overrides.py -q` → 8 passed.
- `pytest tests/ -q` → 2044 passed, 1 xfailed.
