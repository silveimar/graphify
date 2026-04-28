---
phase: 31-template-engine-extensions
plan: 02
subsystem: profile+templates
tags: [profile, dataview, templates, validate-profile, provenance, tmpl-03]
requires:
  - "Plan 31-01 (_BlockTemplate, _PREDICATE_CATALOG, BlockContext.dataview_nonempty)"
provides:
  - "_KNOWN_NOTE_TYPES (frozen at 6 members)"
  - "dataview_queries top-level profile key with per-note-type validation"
  - "_build_dataview_block(profile, community_tag, folder, note_type) — D-13 lookup chain"
  - "_render_moc_like keyword-only note_type parameter"
  - "Empty-query empty-output behavior (Warning 7) — Plan 01 if_has_dataview cross-link"
affects:
  - "_DEFAULT_PROFILE: dataview_queries={} seeded so deep-merge records per-key provenance"
  - "render_note: now invokes _build_dataview_block for its note_type"
  - "render_moc / render_community_overview: pass explicit note_type='moc'/'community'"
  - "validate_profile: rejects unknown dataview_queries keys, non-dict/non-string values"
tech-stack:
  added: []
  patterns: ["per-note-type resolution chain", "empty-query empty-output gate", "profile-side _KNOWN_NOTE_TYPES (avoids profile.py ↔ templates.py cycle)"]
key-files:
  created:
    - tests/fixtures/profiles/dataview_queries_valid.yaml
    - tests/fixtures/profiles/dataview_queries_unknown_key.yaml
    - tests/fixtures/profiles/dataview_queries_legacy_fallback.yaml
  modified:
    - graphify/profile.py
    - graphify/templates.py
    - tests/test_profile.py
    - tests/test_templates.py
decisions:
  - "_KNOWN_NOTE_TYPES defined in profile.py (not templates.py) to avoid the templates↔profile import cycle (matches _REQUIRED_PER_TYPE precedent)"
  - "_DEFAULT_PROFILE seeded with dataview_queries={} so _deep_merge_with_provenance recurses per-key on multi-file extends chains (D-14 provenance semantics)"
  - "_render_moc_like.note_type made keyword-only with default of None (falls back to template_key) for back-compat with three existing test callers; render_moc and render_community_overview pass it explicitly per spec"
  - "render_note added _build_dataview_block call so all six rendered note types consult dataview_queries.<note_type> (must-have); built-in thing/statement/person/source.md templates lack ${dataview_block} so the value is only surfaced when a vault override adds the slot"
  - "Empty-query empty-output integration test routes through legacy `obsidian.dataview.moc_query: '   '` — validate_profile gates only the new dataview_queries key, leaving the legacy path available to exercise the empty-after-strip branch end-to-end"
metrics:
  duration: "~30 min"
  completed: "2026-04-28"
  tasks_completed: 2
  tests_added: 22
  total_tests_passing: 1798
---

# Phase 31 Plan 02: Per-Note-Type Dataview Queries Summary

`dataview_queries: {note_type: query_string}` becomes a recognized top-level profile key (D-11). `_build_dataview_block` consults `dataview_queries.<note_type>` first, then falls back to legacy `obsidian.dataview.moc_query`, then to `_FALLBACK_MOC_QUERY` (D-13). Six locked note types (`_KNOWN_NOTE_TYPES = {moc, community, thing, statement, person, source}`) gate validation at preflight (D-12). `_render_moc_like` carries an explicit `note_type` keyword parameter; `render_moc` passes `"moc"`, `render_community_overview` passes `"community"`. Empty-query empty-output behavior (Warning 7) ensures Plan 01's `{{#if_has_dataview}}` blocks omit cleanly when the resolved query strips to whitespace. Profiles without `dataview_queries` render exactly as before (backward compatibility verified).

## Symbols Added/Modified

### `graphify/profile.py`

| Symbol | Line (approx) | Role |
|--------|---------------|------|
| `_KNOWN_NOTE_TYPES` | 137 | `frozenset({"moc","community","thing","statement","person","source"})` (D-12, frozen at 6) |
| `_VALID_TOP_LEVEL_KEYS` | 130 | Gains `"dataview_queries"` (D-11) |
| `_DEFAULT_PROFILE["dataview_queries"]` | 88 | Seeded as `{}` so `_deep_merge_with_provenance` recurses to per-key leaves on extends chains (D-14) |
| `validate_profile` | ~520 | New block: dict guard, key-in-`_KNOWN_NOTE_TYPES` gate, non-empty-string value gate |

### `graphify/templates.py`

| Symbol | Line (approx) | Role |
|--------|---------------|------|
| `_build_dataview_block(profile, community_tag, folder, note_type)` | 890 | 4th positional `note_type` added; per-note-type lookup → legacy → fallback (D-13); empty-output gate after substitution |
| `_render_moc_like` | 1198 | Adds keyword-only `note_type: str \| None = None` (default falls back to `template_key` for back-compat); call site passes resolved `effective_note_type` |
| `render_moc` | 1380 | Explicit `note_type="moc"` propagated to `_render_moc_like` |
| `render_community_overview` | 1407 | Explicit `note_type="community"` propagated to `_render_moc_like` |
| `render_note` | 1075–1130 | Now calls `_build_dataview_block` with its `note_type`; populates `BlockContext.dataview_nonempty` from the resolved block (Plan 01 cross-link) |

## Locked Decisions

| ID | Decision | Locked by |
|----|----------|-----------|
| D-11 | `dataview_queries` is a top-level profile key | `_VALID_TOP_LEVEL_KEYS` whitelist + `test_dataview_queries_top_level_key_accepted` |
| D-12 | Keys restricted to `_KNOWN_NOTE_TYPES = {moc, community, thing, statement, person, source}` | `_KNOWN_NOTE_TYPES` frozenset + `test_dataview_queries_validates_against_known_types` + `test_dataview_queries_unknown_key_rejected` |
| D-13 | Lookup order: `dataview_queries.<note_type>` → legacy `moc_query` → `_FALLBACK_MOC_QUERY` | `_build_dataview_block` body + `test_dataview_queries_moc_override` + `test_dataview_queries_legacy_fallback` + `test_dataview_queries_default_fallback` |
| D-14 | Deep-merge composes `dataview_queries` per-key; `--validate-profile` provenance shows per-key entries | `test_dataview_queries_deep_merge_per_key_precedence` + `test_dataview_queries_provenance_in_validate_profile_output` |
| Warning 5 | `note_type` propagated through `_render_moc_like`; `render_moc → "moc"`, `render_community_overview → "community"` | `test_dataview_queries_each_note_type_routes_correctly` |
| Warning 7 | Resolved-query empty/whitespace → `_build_dataview_block` returns `""`; `BlockContext.dataview_nonempty=False`; `{{#if_has_dataview}}` blocks omit | `test_dataview_block_omitted_when_resolved_query_empty` + `test_if_has_dataview_false_when_query_empty` (Plan 01 cross-link) |

## Test Counts per Category

| Category | Count | Notes |
|----------|-------|-------|
| `tests/test_profile.py` validate_profile + provenance + deep-merge | 9 | All `test_dataview_queries_*` |
| `tests/test_templates.py` per-note-type override / legacy fallback / default fallback | 4 | `*_overrides_default`, `*_moc_override`, `*_legacy_fallback`, `*_default_fallback` |
| Parametric all-six routing | 6 | `test_dataview_queries_each_note_type_routes_correctly[moc/community/thing/statement/person/source]` |
| Two-phase substitution preserved | 1 | `test_dataview_queries_two_phase_substitution_preserved` |
| Empty-query empty-output behavior (Warning 7) | 1 | `test_dataview_block_omitted_when_resolved_query_empty` |
| Plan 01 cross-link `if_has_dataview` | 1 | `test_if_has_dataview_false_when_query_empty` |
| **Total new tests** | **22** | (1798 total passing, +21 net since Plan 01 ended at 1777 + 1 xfailed unchanged) |

## Backward Compatibility Gate

`tests/fixtures/profiles/dataview_queries_legacy_fallback.yaml` declares `obsidian.dataview.moc_query: "TABLE legacy_query FROM #community/${community_tag}"` and **no** `dataview_queries` key. `test_dataview_queries_legacy_fallback` loads this fixture and asserts the rendered MOC contains `TABLE legacy_query FROM #community/ml-architecture` — the legacy substitution path remains the source of truth when no override is declared. ROADMAP Phase 31 backward-compatibility criterion preserved.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Eight existing `_build_dataview_block` test calls used 3-arg signature**

- **Found during:** Task 2 (initial test run after extending `_build_dataview_block`)
- **Issue:** Plan 04 / pre-Phase-31 tests called `_build_dataview_block(profile, community_tag, folder)` directly. Adding the required 4th positional `note_type` argument broke all 8 call sites.
- **Fix:** Bulk-updated the 8 call sites to pass `note_type="moc"` (preserves prior behavior — tests were exercising the legacy moc_query path under the implicit "moc" note type).
- **Files modified:** `tests/test_templates.py`
- **Commit:** 4af3f33

**2. [Rule 3 - Blocking] `_render_moc_like` keyword-only `note_type` had no default**

- **Found during:** Task 2 (acceptance check that 3 existing test callers in `tests/test_profile_composition.py` and `tests/test_templates.py` continued to work)
- **Issue:** Plan specified `*, note_type: str` (required). Three pre-existing callers pass `template_key="moc"` without a `note_type`. Making `note_type` required would break them.
- **Fix:** Made `note_type: str | None = None`; when `None`, the body falls back to `template_key` (which is already `"moc"` or `"community"` — semantically equivalent for the dataview lookup). `render_moc` and `render_community_overview` still pass it explicitly per spec, satisfying the locked Warning-5 propagation. Documented inline.
- **Files modified:** `graphify/templates.py`
- **Commit:** 4af3f33

**3. [Rule 3 - Architectural reality] Acceptance grep `_build_dataview_block(` >= 5 unattainable without contrived refactor**

- **Found during:** Task 2 acceptance criteria verification
- **Issue:** Plan acceptance: `grep -c "_build_dataview_block(" >= 5`. Architecture has render_moc/render_community_overview delegating to `_render_moc_like`, so they don't call `_build_dataview_block` directly. Real count is 3 (def + render_note call + `_render_moc_like` call). The plan itself notes "otherwise 2 call sites + definition" as the fallback case — which is what the codebase actually is.
- **Fix:** None applied — bumping the count to 5 would require contrived duplicate calls that obscure architecture. The functional outcome (per-note-type Dataview lookup at all four render entry points) is satisfied: render_note calls directly, render_moc/render_community_overview indirectly via `_render_moc_like` with explicit `note_type=` propagation. Recorded here per Rule 3.
- **Files modified:** none
- **Commit:** N/A (informational)

**4. [Rule 3 - Acceptance regex limitation] Multi-line `_render_moc_like(...note_type=` not single-line greppable**

- **Found during:** Task 2 acceptance criteria verification
- **Issue:** `grep -E "_render_moc_like\(.*note_type=" graphify/templates.py | wc -l >= 2` does not match the 3-line `return _render_moc_like(\n        community_id, ...\n        ...,\n        note_type="moc",\n    )` shape. Single-line grep returns 0.
- **Fix:** None applied — the spirit of the criterion (render_moc and render_community_overview each pass `note_type=` explicitly) is met; verified via `grep -c 'note_type="moc"\|note_type="community"' graphify/templates.py` = 3 (one in render_note's _build_dataview_block call, one in render_moc, one in render_community_overview). Recorded here per Rule 3.
- **Files modified:** none
- **Commit:** N/A (informational)

**5. [Rule 3 - Provenance edge case] Provenance test reshaped to 2-file extends chain**

- **Found during:** Task 1 (initial provenance test failed against the flat fixture)
- **Issue:** With a single-file profile, `_resolve_profile_chain` starts `composed = {}` and the first merge records `dataview_queries` as ONE leaf (not per-key) because the recursive case in `_deep_merge_with_provenance` only triggers when both sides of a merge are existing dicts. Per-key provenance materialises only on chains of >=2 files. Test as drafted asserted `dataview_queries.moc/community/thing` against a single-file fixture — those entries don't exist there.
- **Fix:** `test_dataview_queries_provenance_in_validate_profile_output` now constructs an inline 2-file extends chain (`bases/core.yaml` → `profile.yaml`). Asserts per-key provenance for the override-touched keys (`moc`, `thing` from `profile.yaml`); the `community` key from base remains in the original whole-dict provenance entry. Documented in test docstring with the architectural reason.
- **Files modified:** `tests/test_profile.py`
- **Commit:** 2e8ef58

## Self-Check: PASSED

**Created files (verified present):**
- ✓ `tests/fixtures/profiles/dataview_queries_valid.yaml`
- ✓ `tests/fixtures/profiles/dataview_queries_unknown_key.yaml`
- ✓ `tests/fixtures/profiles/dataview_queries_legacy_fallback.yaml`

**Commits (verified in git log):**
- ✓ 2e8ef58 — `feat(31-02-01): register dataview_queries top-level key with _KNOWN_NOTE_TYPES validation`
- ✓ 4af3f33 — `feat(31-02-02): _build_dataview_block per-note-type lookup with note_type propagation`

**Test suite status:**
- ✓ `pytest tests/test_profile.py -q` exits 0 (173 passed, 1 xfailed)
- ✓ `pytest tests/test_templates.py -q` exits 0 (203 passed)
- ✓ `pytest tests/ -q` exits 0 (1798 passed, 1 xfailed)

**Acceptance criteria verified:**
- ✓ `dataview_queries` in `_VALID_TOP_LEVEL_KEYS` (`python3 -c "from graphify.profile import _VALID_TOP_LEVEL_KEYS; assert 'dataview_queries' in _VALID_TOP_LEVEL_KEYS"` exits 0)
- ✓ `_KNOWN_NOTE_TYPES == frozenset({'moc','community','thing','statement','person','source'})`
- ✓ Three fixture files present
- ✓ 9 test_dataview_queries_* in test_profile.py
- ✓ 6 test_dataview_queries_* + 1 test_dataview_block_omitted + 1 test_if_has_dataview_false_when_query_empty in test_templates.py
- ✓ `if not query.strip():` empty-output gate present in templates.py
- ✓ Backward-compat: `dataview_queries_legacy_fallback.yaml` round-trips through legacy `obsidian.dataview.moc_query`
- ✓ No new required dependencies (`grep -E 'jinja|mako|chevron' pyproject.toml` returns empty)

**Acceptance criteria adapted (documented as deviations):**
- Rule 3 Deviation 3: `grep -c "_build_dataview_block(" >= 5` adapted to architectural reality (def + 2 call sites = 3); equivalent functional surface satisfied via render_moc/render_community_overview's explicit `note_type=` propagation through `_render_moc_like`.
- Rule 3 Deviation 4: `grep -E "_render_moc_like\(.*note_type="` does not match the multi-line call shape; spirit verified via `grep -c 'note_type="moc"\|note_type="community"'` = 3.
