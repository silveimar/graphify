---
phase: 56
plan: 03
subsystem: profile-validation
tags: [CFG-01, D-56.03, D-56.04, schema, validator, slug]
requires:
  - phase-56-plan-01 (provenance shape dict[str, list[Path]])
  - phase-56-plan-02 (_VALID_TOP_LEVEL_KEYS extension; per-list dupe detectors)
provides:
  - mapping_rule_templates_validator
  - note_type_templates_validator
  - mapping_rules_id_field_validation
  - rule_id_uniqueness_pass
affects:
  - graphify/profile.py (validate_profile)
  - graphify/mapping.py (validate_rules)
tech-stack:
  added: []
  patterns:
    - "byte-for-byte port from community_templates: validator (substring-style path-confinement)"
    - "optional-field guard pattern (mirror then.folder analog)"
key-files:
  created: []
  modified:
    - graphify/profile.py
    - graphify/mapping.py
    - tests/test_profile.py
    - tests/test_mapping.py
decisions:
  - "Duplicated slug regex locally (_MAPPING_RULE_TEMPLATE_PATTERN_RE in profile.py) to avoid mapping.py↔profile.py import cycle, mirroring _KNOWN_NOTE_TYPES placement convention"
  - "Substring-style path-confinement ('..' in template) ported verbatim — NOT Path.parts — per D-56.03"
metrics:
  duration: "~6 min"
  tasks_completed: 3
  tests_added: 18
  files_modified: 4
  completed_date: "2026-05-02"
---

# Phase 56 Plan 03: CFG-01 Schema Validators Summary

Schema-only contributions for CFG-01 (scoped template overrides): two new top-level validators (`mapping_rule_templates:`, `note_type_templates:`) ported byte-for-byte from `community_templates:` validator, plus optional `mapping_rules[].id:` slug field validated in `validate_rules` with type/length/pattern/uniqueness guards. Render-time wiring deferred to Plan 05.

## Task → Commit Map

| Task | Description | Commit |
| ---- | ----------- | ------ |
| 1 | RED — 18 failing tests across test_profile.py + test_mapping.py | `f23dc5d` |
| 2 | GREEN — port community_templates: → mapping_rule_templates: + note_type_templates: validators in profile.py | `a13dbac` |
| 3 | GREEN — mapping_rules.id: optional slug field + uniqueness pass in mapping.py | `ae40676` |

## What Shipped

### graphify/profile.py
- **Lines added:** 115 (two new validator blocks immediately after community_templates: validator at line 735)
- **`mapping_rule_templates:` validator** (`mrt = profile.get(...)`):
  - `match` allowlist: `{"rule_id"}` only (single value in v1.11)
  - `pattern` slug regex: `^[a-z][a-z0-9_-]*$` (locally-duplicated `_MAPPING_RULE_TEMPLATE_PATTERN_RE` to avoid cross-module import cycle)
  - Path-confinement: `'..' in template`, `Path(template).is_absolute()`, `template.startswith('~')` — substring style verbatim from analog
  - Unknown-keys check: `set(rule) - {"match", "pattern", "template"}`
- **`note_type_templates:` validator** (`ntt = profile.get(...)`):
  - `match` allowlist: `{"note_type"}` only
  - `pattern` constrained to `_KNOWN_NOTE_TYPES` (frozenset of 7 types)
  - Same path-confinement + unknown-keys block
- `_VALID_TOP_LEVEL_KEYS` already extended in Plan 02 (no change here — verified via regression tests)

### graphify/mapping.py
- **Constants added** (after `_MAX_PATTERN_LEN`):
  - `_RULE_ID_PATTERN = re.compile(r"^[a-z][a-z0-9_-]*$")`
  - `_RULE_ID_MAX_LEN = 80`
- **Per-rule id: validation** inserted in `validate_rules` per-rule loop after the `not isinstance(rule, dict)` guard, before `when`/`then` extraction:
  - Type check (str)
  - Length cap (≤ 80)
  - Slug pattern fullmatch
  - All checks gated by `rule_id is not None` (optional field; backward compat)
- **Uniqueness pass** added before `_detect_dead_rules` call: tracks `seen_ids: dict[str, int]`, emits error citing both rule indices on collision

### tests/test_profile.py (+13 tests)
- 6 mapping_rule_templates tests: positive, non-list, bad match kind, non-slug pattern, path escapes, unknown keys
- 5 note_type_templates tests: positive, non-list, unknown note_type, path escapes, unknown keys
- 2 regression guards: `_VALID_TOP_LEVEL_KEYS` membership for both keys

### tests/test_mapping.py (+5 tests)
- `test_validate_rules_id_field_accepted_when_valid_slug` — positive + backward compat (no id: field)
- `test_validate_rules_id_field_rejects_non_string` — int, list rejected
- `test_validate_rules_id_field_rejects_too_long` — 81-char id rejected
- `test_validate_rules_id_field_rejects_bad_pattern` — leading digit, uppercase, dots, slash all rejected
- `test_validate_rules_id_field_rejects_duplicate_across_rules` — error cites both colliding indices

## Swap-from-Community-Templates Audit

| Field | community_templates (analog) | mapping_rule_templates (new) | note_type_templates (new) |
|-------|------------------------------|------------------------------|---------------------------|
| Variable | `ct` | `mrt` | `ntt` |
| Top-level key | `community_templates` | `mapping_rule_templates` | `note_type_templates` |
| Prefix template | `community_templates[{idx}]` | `mapping_rule_templates[{idx}]` | `note_type_templates[{idx}]` |
| `match` allowlist | `{"label", "id"}` | `{"rule_id"}` | `{"note_type"}` |
| `pattern` constraint | str if label, int (non-bool) if id | str matching `^[a-z][a-z0-9_-]*$` | str ∈ `_KNOWN_NOTE_TYPES` |
| Path-confinement | `'..' in`, is_absolute, `~` (substring) | identical | identical |
| Unknown-keys check | `set(rule) - {match, pattern, template}` | identical | identical |

## Verification

- `pytest tests/test_profile.py tests/test_mapping.py -q`: 267 passed, 1 xfailed
- `pytest tests/ -q`: **2062 passed, 1 xfailed, 8 warnings** (no regression)
- `grep '".." in template' graphify/profile.py`: 3 occurrences (community_templates + 2 new validators — substring style preserved)

## Deviations from Plan

None — plan executed exactly as written.

## Backward Compatibility

- Profiles without `mapping_rule_templates:` / `note_type_templates:` continue to validate cleanly (absent keys → no validator triggered)
- `mapping_rules` entries without `id:` field validate cleanly (optional field guard `if rule_id is not None`)
- `community_templates:` validator untouched per D-56.03 (locked decision)

## Out-of-Scope (Locked)

- Render-time consumption of `mapping_rule_templates:` / `note_type_templates:` (Plan 05)
- Glob/regex pattern overlap detection (Plan 02 deferred — non-goal)
- Any change to `community_templates:` validator (D-56.03 locked)

## Self-Check: PASSED

- graphify/profile.py: validators present at expected locations (`grep -n 'mrt = profile.get' graphify/profile.py` returns 1; `grep -n 'ntt = profile.get'` returns 1)
- graphify/mapping.py: constants + id-validation + uniqueness pass present (`grep -c '_RULE_ID_PATTERN'` returns 2 — definition + use; `grep -c 'duplicate id'` returns 1)
- All commits exist in git log: f23dc5d, a13dbac, ae40676
- Full pytest suite green (2062 passed)
