---
phase: 03-mapping-engine
plan: 03
subsystem: mapping-engine
tags: [validation, profile, security, dead-rule-detection, path-traversal]
requirements: [MAP-04, MAP-05]
dependency-graph:
  requires:
    - 03-01 (compile_rules + _kind_of in mapping.py)
    - 03-02 (classify() reads profile["mapping"]["moc_threshold"] + profile["topology"]["god_node"]["top_n"])
    - Phase 1 profile.py (validate_profile error-list pattern, path-rejection style)
  provides:
    - graphify.mapping.validate_rules — single source of truth for mapping_rules grammar
    - graphify.mapping._detect_dead_rules — conservative structural dead-rule warnings
    - graphify.profile._DEFAULT_PROFILE["topology"]["god_node"]["top_n"] = 10
    - graphify.profile._DEFAULT_PROFILE["mapping"]["moc_threshold"] = 3
    - graphify.profile.validate_profile delegation to validate_rules
  affects:
    - Phase 3 Plan 04 (consumes validate_profile output at load_profile time)
    - Phase 5 export writers (two-layer defense — validate_vault_path at write time)
tech-stack:
  added: []
  patterns:
    - function-local import to break circular dependency (mapping -> templates -> profile -> mapping)
    - bool-before-int guard (isinstance bool check precedes isinstance int check)
    - error-list validator returning list[str], never raising
key-files:
  created: []
  modified:
    - graphify/mapping.py (validate_rules + _detect_dead_rules + 5 helpers, 336 lines)
    - graphify/profile.py (_DEFAULT_PROFILE extensions + validate_profile topology/mapping/delegation, 60 lines)
    - tests/test_mapping.py (10 new validator tests, 118 lines)
    - tests/test_profile.py (8 new extension tests, 69 lines)
decisions:
  - Delegation via function-local import (T-3-11 mitigation) — top-level import would cycle through templates.py
  - Dead-rule detector stays conservative — attr:contains, attr:regex, source_file_matches skipped entirely (undecidable without semantic equivalence, false-negative acceptable, zero false positives guaranteed)
  - Shape errors suppress dead-rule warnings (nonsense rules would be misread by the pairwise heuristic)
metrics:
  duration: ~18 minutes
  completed: 2026-04-11
  tasks: 2
  commits: 4
  files_modified: 4
  tests_added: 18
  tests_passing: 129/129 (tests/test_mapping.py + tests/test_profile.py)
---

# Phase 3 Plan 03: Validator + Profile Extension Summary

One-liner: `validate_rules` closes the mapping_rules grammar gap (regex-cap ReDoS guard, path-traversal rejection, conservative dead-rule warnings) and `validate_profile` now delegates to it via a function-local import that breaks the mapping <- templates <- profile <- mapping cycle.

## What shipped

### Task 1 — `graphify/mapping.py`: `validate_rules` + `_detect_dead_rules`

Replaced the `NotImplementedError` stub with a full error-list validator covering the D-43 rule grammar:

- **Rule shape:** `rule` must be a dict; `when` and `then` must both be dicts. Non-dict rules, missing keys, and wrong-type keys are surfaced with `mapping_rules[{idx}].{path}:` prefixes (mirrors `validate.py` convention).
- **Matcher kinds (exactly one):** `attr`, `topology`, `source_file_ext`, `source_file_matches`. Multi-matcher rules are rejected with a pointed `multiple matcher kinds` error (T-3-08 mitigation — prevents accidental AND-style rules deferred to v2).
- **attr operators (exactly one):** `equals`, `in`, `contains`, `regex`. `in` must be a list/tuple; `regex` compiles at validation time so malformed patterns fail fast.
- **Regex safety (T-3-01):** pattern length cap `_MAX_PATTERN_LEN=512` enforced BEFORE `re.compile`; `re.error` caught and converted to an error string, never raised.
- **topology.value bool-before-int guard (T-3-03):** `community_size_gte`, `community_size_lt` require `int and not bool`; `cohesion_gte` requires `(int|float) and not bool` in `[0.0, 1.0]`.
- **source_file_ext:** must be a string or list of strings that each start with `.`.
- **then.note_type (required):** whitelisted against `_NOTE_TYPES` from `templates.py` (`moc`, `community`, `thing`, `statement`, `person`, `source`). T-3-10 mitigation.
- **then.folder (optional, path-safety — T-3-02):** rejects `..`, absolute paths, and leading `~`. Mirrors `profile.py:178-195` conventions exactly.
- **Unknown `then:` keys (D-46 / W-1 fix):** any key not in `{"note_type", "folder"}` produces a pointed error `unknown keys ['tags'] — only 'note_type' and 'folder' are supported (D-46)`. This is the critical WARNING 1 fix — without it, users would silently lose `tags`, `up`, etc.
- **Dead-rule warnings (D-45):** appended only when no per-rule shape errors exist. `_detect_dead_rules` runs a conservative pairwise superset heuristic — see "Dead-rule heuristic bounds" below.

Added five private helpers (`_validate_when_kind`, `_validate_attr_when`, `_validate_topology_when`, `_validate_source_file_ext_when`, `_validate_source_file_matches_when`, `_validate_folder`) plus `_is_shadowed` for the dead-rule pass.

### Task 2 — `graphify/profile.py`: `_DEFAULT_PROFILE` extensions + delegation

- `_DEFAULT_PROFILE` gains `"topology": {"god_node": {"top_n": 10}}` (D-48) and `"mapping": {"moc_threshold": 3}` (D-52).
- `_VALID_TOP_LEVEL_KEYS` extended with `"topology"` and `"mapping"`.
- `validate_profile` adds three new sections:
  1. `topology.god_node.top_n` — bool-before-int guard, `≥ 0`.
  2. `mapping.moc_threshold` — bool-before-int guard, `≥ 1`.
  3. `mapping_rules` — delegates to `graphify.mapping.validate_rules` via a **function-local** `from graphify.mapping import validate_rules` at the exact call site (the only location that needs it).

## Why the function-local import (T-3-11)

A top-level `from graphify.mapping import validate_rules` in `profile.py` would create a circular import chain:

```
graphify.mapping
  -> imports from graphify.templates  (ClassificationContext, _NOTE_TYPES)
  -> graphify.templates
       -> imports from graphify.profile (safe_frontmatter_value, safe_tag)
       -> graphify.profile
            -> would import from graphify.mapping  ← cycle
```

Python's import system catches the cycle and either raises `ImportError` or hands back a half-initialized module depending on evaluation order. A function-local import inside `validate_profile` defers the resolution until after all module bodies have executed, so by the time `validate_profile` is actually called, `graphify.mapping` is fully loaded. An inline comment at the call site documents this (future maintainers may otherwise try to "clean it up").

## Dead-rule heuristic bounds (D-45)

The detector is intentionally conservative — **zero false positives, false negatives acceptable**:

| Matcher kind | Supported? | Rule |
|---|---|---|
| `attr:equals` | Yes | same attr AND same equals value |
| `attr:in` | Yes | same attr AND broader `in` list issuperset of narrower |
| `attr:contains` | No | semantic substring equivalence undecidable |
| `attr:regex` | No | regex equivalence undecidable |
| `topology:god_node` | Yes | identical (parameterless) — earlier wins |
| `topology:is_source_file` | Yes | identical (parameterless) — earlier wins |
| `topology:community_size_gte` | Yes | `broad.value <= narrow.value` |
| `topology:community_size_lt` | Yes | `broad.value >= narrow.value` |
| `topology:cohesion_gte` | Yes | `broad.value <= narrow.value` |
| `source_file_ext` | Yes | broad ext set issuperset of narrow ext set |
| `source_file_matches` | No | regex equivalence undecidable |

Cross-kind pairs never warn — `topology: god_node` followed by `attr: label equals X` is NOT flagged, even though the first rule might match everything the second rule matches at runtime. This is by contract (3-03-05 test pins this).

Same `then.note_type` is required — shadowing across note_types is a user intent signal (e.g. "first match person, later fall through to thing") and should not warn.

## Tests added (18 total)

**tests/test_mapping.py (10 validator tests):**

| Test | VALIDATION row | Covers |
|---|---|---|
| `test_validate_rules_regex_too_long_rejected` | 3-03-01 | ReDoS cap BEFORE compile |
| `test_validate_rules_rejects_malformed_regex_with_pointed_error` | — | `re.error` surfaced with rule index |
| `test_validate_rules_rejects_unknown_note_type` | — | whitelist enforcement |
| `test_validate_rules_rejects_path_traversal_in_folder` | 3-03-06 | `..`, absolute, `~` all caught |
| `test_validate_rules_rejects_bool_topology_value` | — | T-3-03 bool-before-int |
| `test_validate_rules_rejects_multiple_matcher_kinds` | — | T-3-08 |
| `test_validate_rules_dead_rule_warning_identical` | 3-03-04 | duplicate rules warned |
| `test_validate_rules_no_dead_rule_warning_across_kinds` | 3-03-05 | cross-kind never warns |
| `test_validate_rules_accepts_valid_example_from_context` | — | D-43 example passes clean |
| `test_validate_rules_rejects_unknown_then_keys` | 3-03-08 | **W-1 fix — unknown keys surfaced** |

**tests/test_profile.py (8 extension tests):**

| Test | VALIDATION row | Covers |
|---|---|---|
| `test_default_profile_includes_topology_and_mapping_keys` | — | both new sections present |
| `test_default_profile_top_n_and_threshold_are_not_bool` | — | defaults are `int`, not `bool` |
| `test_deep_merge_respects_topology_section` | 3-04-04 | `_deep_merge` recurses into topology |
| `test_default_profile_rejects_bool_as_int_threshold` | 3-03-07 | `{"moc_threshold": True}` rejected |
| `test_validate_profile_rejects_bool_top_n` | — | `{"top_n": False}` rejected |
| `test_validate_profile_rejects_negative_top_n` | — | `top_n < 0` rejected |
| `test_validate_profile_surfaces_mapping_rules_errors` | 3-04-03 | delegation works; errors surface |
| `test_validate_profile_accepts_default_profile_unchanged` | — | regression check: default is always valid |

## Verification results

```
$ pytest tests/test_mapping.py tests/test_profile.py -q
129 passed in 0.20s
```

Full suite:

```
$ pytest tests/ -q
2 failed, 704 passed
```

The 2 failures (`test_detect_skips_dotfiles`, `test_collect_files_from_dir`) are the pre-existing worktree-path failures already captured in `deferred-items.md` from Plan 03-01 — both stem from the worktree checkout being inside a `.claude/` directory, which the detect/extract modules filter as dot-directories. Unrelated to Plan 03-03.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Robustness] `_is_shadowed` bool/int guards on topology value comparisons**
- **Found during:** Task 1 implementation review
- **Issue:** The plan's sketch for `_is_shadowed` used `broad_when.get("value") or 0` which would treat `False` as 0 and potentially emit false-positive shadowing warnings. bool is a subclass of int in Python, so `True` would also leak through numeric comparison.
- **Fix:** Added explicit `isinstance(x, int)` + `isinstance(x, bool)` rejection checks at the top of each topology-value shadowing branch. If either rule carries a non-int or bool value, `_is_shadowed` returns `False` — which is consistent with the "no false positives" contract (shape errors would have been caught by `validate_rules` before `_detect_dead_rules` ran, but defensive guards cost nothing and match the codebase's general bool-before-int style).
- **Files modified:** `graphify/mapping.py::_is_shadowed`
- **Commit:** `84e45b7`

**2. [Rule 1 - Robustness] `_detect_dead_rules` defensive dict check**
- **Found during:** Task 1 implementation review
- **Issue:** Plan sketch read `rule.get("when") or {}` without verifying `when`/`then` were actually dicts. A user rule like `{"when": "broken", "then": "broken"}` would crash later when `_kind_of` calls `when.__contains__`.
- **Fix:** Added `isinstance(wj/wi/ti/tj, dict)` checks inside the pairwise loop. If either side is malformed, skip the pair (shape errors would already be in the error list; warnings are gated on `not errors` so this is belt-and-suspenders).
- **Files modified:** `graphify/mapping.py::_detect_dead_rules`
- **Commit:** `84e45b7`

**3. [Rule 2 - Critical] Per-rule matcher-keys validator continues rather than skipping**
- **Found during:** Task 1 implementation review
- **Issue:** Plan sketch used `continue` after `len(matcher_keys) > 1` error, which would skip validating `then.note_type`, `then.folder`, and unknown-then-keys for the same rule. Users submitting malformed rules would see errors discovered incrementally instead of all at once.
- **Fix:** Changed to `else:` branch (validate `when_kind` only when exactly one matcher), and let the rest of the per-rule loop run so all `then` problems surface on the first pass.
- **Files modified:** `graphify/mapping.py::validate_rules`
- **Commit:** `84e45b7`

No architectural changes (Rule 4) were required.

## Known Stubs

None. Both `validate_rules` and `_detect_dead_rules` are fully implemented; the prior `NotImplementedError` stub has been removed. `graphify/profile.py` carries no stubs.

## Commits

| # | Hash | Type | Message |
|---|---|---|---|
| 1 | `0a9a951` | test | add failing validate_rules + dead-rule tests |
| 2 | `84e45b7` | feat | implement validate_rules + _detect_dead_rules |
| 3 | `61567f3` | test | add failing profile extension tests for topology/mapping sections |
| 4 | `2a8645a` | feat | extend _DEFAULT_PROFILE with topology+mapping, delegate to validate_rules |

## Self-Check: PASSED

- `graphify/mapping.py` FOUND, contains `def validate_rules` at line 707
- `graphify/mapping.py` FOUND, contains `def _detect_dead_rules` at line 936
- `graphify/mapping.py` FOUND, contains `def _is_shadowed` at line 980
- `graphify/profile.py` FOUND, contains `"topology":` at line 38 and `"mapping":` at line 39
- `graphify/profile.py` FOUND, contains `from graphify.mapping import validate_rules` at line 255
- `tests/test_mapping.py` FOUND, 10 new `test_validate_rules_*` tests green
- `tests/test_profile.py` FOUND, 8 new profile extension tests green
- Commit `0a9a951` FOUND in log
- Commit `84e45b7` FOUND in log
- Commit `61567f3` FOUND in log
- Commit `2a8645a` FOUND in log
- `pytest tests/test_mapping.py tests/test_profile.py -q` → 129 passed
- Full suite: 704 passed, 2 pre-existing worktree-path failures (documented in deferred-items.md)
