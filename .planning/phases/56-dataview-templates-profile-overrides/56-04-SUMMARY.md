---
phase: 56
plan: 04
subsystem: profile-validation
tags: [TMPL-03, D-56.02, dataview_queries, dead-rules, preflight]
requires: [56-01, 56-02, 56-03]
provides:
  - "_DATAVIEW_QUERY_VARS allowlist constant (graphify/profile.py:196)"
  - "_reachable_note_types(profile) helper (graphify/profile.py:199-217)"
  - "TMPL-03 §1 unknown ${var} dead-rule (graphify/profile.py:918-926)"
  - "TMPL-03 §2 unreachable note_type dead-rule (graphify/profile.py:928-935)"
  - "TMPL-03 §3 empty-after-substitution dead-rule (graphify/profile.py:937-949)"
  - "TMPL-03 §4 cross-chain duplicate (delegates to Plan 02 _detect_dataview_collisions; graphify/profile.py:951-953 documents the contract)"
affects:
  - "graphify/profile.py — dataview_queries: validator hardened with three new dead-rule classes"
  - "tests/test_profile.py — nine new tests + one existing Phase 31 test updated for stricter §2 reachability"
tech-stack:
  added: []
  patterns:
    - "string.Template.pattern.finditer for ${var} extraction without rendering"
    - "string.Template.safe_substitute(community_tag='', folder='').strip() for the §3 emptiness probe"
    - "Conservative reachability: topology-fallback set ∪ mapping_rules.then.note_type"
    - "Single source of truth for §4: validator delegates rather than duplicates Plan 02 detector"
key-files:
  created: []
  modified:
    - "graphify/profile.py (+44 lines: import string, _DATAVIEW_QUERY_VARS, _reachable_note_types, three new validator blocks, §4 delegation comment)"
    - "tests/test_profile.py (+179 lines: nine new tests; +6/-3 lines: existing test_dataview_queries_validates_against_known_types updated to satisfy §2 reachability)"
decisions:
  - "Allowlist locked to {community_tag, folder} per RESEARCH §1 exhaustive _build_dataview_block callsite walk (templates.py:1290-1293, 1439-1444, 1707-1710). NOT note_type, NOT vault_root."
  - "§2 algorithm conservative: only emit unreachable error when conservatively provable; only person/source ever flaggable in v1.11."
  - "§4 not re-implemented: Plan 02's _detect_dataview_collisions wired in validate_profile_preflight is single source of truth. Validator carries a one-line delegating comment so future readers do not duplicate."
  - "string.Template (not Jinja2) — matches the existing template surface and keeps zero-new-deps constraint from CLAUDE.md."
metrics:
  duration: "~25min"
  completed: "2026-05-02"
  commits: 2
  tests_added: 9
  suite_total: 2071
---

# Phase 56 Plan 04: TMPL-03 Dead-Rule Preflight Checks for `dataview_queries:` Summary

Hardens the existing Phase 31 `dataview_queries:` validator at `graphify/profile.py` with the four dead-rule classes mandated by D-56.02 (TMPL-03), turning silently-broken profiles into preflight errors before render.

## What Shipped

### `graphify/profile.py`

1. **Import added** (line 9): `import string` — `string.Template` powers both the `${var}` discovery (§1) and the empty-substitution probe (§3).

2. **`_DATAVIEW_QUERY_VARS` constant** (lines 190-196):
   ```python
   _DATAVIEW_QUERY_VARS: frozenset[str] = frozenset({"community_tag", "folder"})
   ```
   The comment block above it cites the exact provenance — "exhaustive enumeration of `_build_dataview_block` callsites at templates.py:1290-1293, 1439-1444, 1707-1710". Documented to prevent future drift expansion (no `note_type`, no `vault_root`).

3. **`_reachable_note_types(profile: dict) -> set[str]` helper** (lines 199-217):
   - Seeds with the topology fallback set `{moc, community, thing, statement, code}` from `mapping.py:397-406`.
   - Adds `then.note_type` from every `mapping_rule` entry.
   - Conservative bias: only `person` / `source` are ever potentially unreachable in v1.11 — anything else is guaranteed reachable.

4. **Three new dead-rule blocks** inside the existing `dataview_queries:` validator (lines ~915-953):
   - **§1 unknown `${var}`** (918-926): Iterates `string.Template.pattern.finditer(value)`, surfaces unknown names with the canonical allowlist suggestion.
   - **§2 unreachable note_type** (928-935): One-shot `_reachable_note_types(profile)` check per key.
   - **§3 empty after substitution** (937-949): Probes `safe_substitute(community_tag="", folder="").strip()`; empty result → error.
   - **§4 delegating comment** (951-953): One-line note that `_detect_dataview_collisions` (Plan 02, wired in `validate_profile_preflight`) owns cross-chain detection — no duplicate logic.

### `tests/test_profile.py`

Nine new tests adjacent to existing Phase 31 dvq tests (lines 1887-2065):

| Test | Class | Sense |
|------|-------|-------|
| `test_dataview_queries_unknown_var_rejected` | §1 | positive |
| `test_dataview_queries_known_vars_accepted` | §1 | negative |
| `test_dataview_queries_unreachable_note_type_rejected` | §2 | positive |
| `test_dataview_queries_reachable_note_type_accepted` | §2 | negative |
| `test_dataview_queries_unreachable_note_type_becomes_reachable_via_mapping_rule` | §2 | augmentation negative |
| `test_dataview_queries_empty_after_substitution_rejected` | §3 | positive |
| `test_dataview_queries_non_empty_after_substitution_accepted` | §3 | negative |
| `test_dataview_queries_cross_chain_collision_via_tmpl03` | §4 | positive (wiring) |
| `test_dataview_queries_single_source_no_cross_chain_error` | §4 | negative (wiring) |

The §4 tests verify that Plan 02's detector is reachable through the user-facing `validate_profile_preflight` channel — i.e. they assert the **wiring** rather than re-implementing the detection logic.

## Verification

- `pytest tests/test_profile.py -k dataview_queries -q` → 19 passed (10 pre-existing Phase 31 + 9 new).
- `pytest tests/ -q` → **2071 passed, 1 xfailed** (baseline 2062 + 9 new = exactly the expected delta).
- All <success_criteria> from the plan satisfied:
  1. Unknown `${var}` rejected against locked allowlist ✓
  2. Unreachable `dataview_queries.<note_type>` rejected conservatively ✓
  3. Empty-after-substitution rejected ✓
  4. §4 delegates to single source of truth (Plan 02) ✓
  5. Backward compat preserved (existing Phase 31 dvq tests still GREEN after one targeted update for §2 reachability) ✓

## Deviations from Plan

### Rule 1 (auto-fix) — Existing Phase 31 test broken by §2

`test_dataview_queries_validates_against_known_types` (line 1642) iterated over every member of `_KNOWN_NOTE_TYPES` (which includes `person` and `source`) and asserted `validate_profile(profile) == []`. Once §2 landed, that assertion failed for `person`/`source` because no `mapping_rules` route to them.

**Fix:** Added a two-rule `mapping_rules` block to the test profile that routes to `person` and `source` via `{"attr": "kind", "equals": ...}` shape. The test still proves its original intent — every `_KNOWN_NOTE_TYPES` key is schema-acceptable — but now under the stricter §2 reachability contract. This is the documented bridge between Phase 31's "shape-only" semantics and Phase 56's "shape + reachability" semantics. Plan explicitly anticipated it: "Existing Phase 31 dataview_queries: tests stay GREEN (additive, not replacement)."

**Files modified:** `tests/test_profile.py` (single test body).
**Commit:** `d68e064` (folded into the GREEN commit).

### Mapping-rule shape for §2 augmentation test

Initial draft used `{"label_re": ".*"}` for the `when` clause, which `validate_profile` rejects (must be one of `attr` / `topology` / `source_file_ext` / `source_file_matches`). Corrected to `{"attr": "kind", "equals": "person"}` in both the new §2 augmentation test and the updated existing test. No behavioral impact — both forms exercise the `then.note_type` branch of `_reachable_note_types`.

### No other deviations

§4 was not re-implemented (per plan). No new dependencies. No changes outside the targeted region of `profile.py:737-763` (now `:911-953` post-insertion).

## Provenance Decisions Locked In

- **`_DATAVIEW_QUERY_VARS = frozenset({"community_tag", "folder"})`** — the comment block above the constant documents the exhaustive callsite walk so future readers cannot expand the set without re-running the enumeration. RESEARCH §1 is the canonical citation.
- **`_reachable_note_types` topology fallback set** = `{moc, community, thing, statement, code}` — sourced from `mapping.py:397-406`. The helper docstring spells out that only `person` and `source` can ever trigger §2 in v1.11.
- **§4 delegation contract** — the validator carries a comment block at lines 951-953 stating that cross-chain detection lives in `_detect_dataview_collisions` (Plan 02). Single source of truth.

## Commits

| Hash | Message |
|------|---------|
| `293abf9` | `test(56-04): RED — TMPL-03 dead-rule classes for dataview_queries:` |
| `d68e064` | `feat(56-04): GREEN — TMPL-03 §1-3 dead-rule classes (§4 reuses Plan 02 detector)` |

## Self-Check: PASSED

- `graphify/profile.py:196` (_DATAVIEW_QUERY_VARS) — FOUND
- `graphify/profile.py:199` (_reachable_note_types) — FOUND
- `graphify/profile.py:918-953` (three new validator blocks + §4 comment) — FOUND
- `tests/test_profile.py:1887-2065` (nine new tests) — FOUND
- Commit `293abf9` (RED) — present in `git log`
- Commit `d68e064` (GREEN) — present in `git log`
- `pytest tests/ -q` exit 0; 2071 passed
