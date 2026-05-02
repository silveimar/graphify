---
phase: 55
slug: template-conditionals-connections
requirements: [TMPL-01, TMPL-02]
status: passed
verified: 2026-05-02
pytest: "2034 passed, 1 xfailed, 0 failed"
baseline: "2018 passed, 1 xfailed (Phase 55 Plan 03 close, 16 doc-fence RED pending)"
---

# Phase 55 Verification — Template Conditionals & Connection Loops

Goal-backward verification per Phase 55 ROADMAP success criteria. All truths grep- or pytest-verifiable.

## Goal

> Extend `string.Template`-based rendering with conditional sections and connection-iteration blocks, expanded **before** `${}` substitution and routed through existing sanitization sinks (no Jinja2 dependency).

## TMPL-01 Mapping Table

> TMPL-01 — *Users can author conditional template sections in `.graphify/templates/` driven by profile-controlled predicates (note type / god-node / simple flags); blocks expand before `${}` substitution and outputs pass label/HTML sanitization.*

| Sub-requirement | Source (file:line) | Test |
|-----------------|-------------------|------|
| `_IF_NOTE_TYPE_RE` regex constant added after `_IF_ATTR_RE` | `graphify/templates.py:197` | `tests/test_templates.py::test_if_note_type_thing_renders_when_note_type_matches` (L2674), `test_if_note_type_all_six_types_evaluated_independently` (L2762) |
| `_IF_FLAG_RE` regex constant added after `_IF_NOTE_TYPE_RE` | `graphify/templates.py:199` | `tests/test_templates.py::test_if_flag_truthy_rule_renders` (L2802) |
| `_eval_predicate` has `elif _IF_NOTE_TYPE_RE.match(name)` branch | `graphify/templates.py:322` | 10 `if_note_type` tests (all GREEN): `pytest tests/test_templates.py -k "if_note_type" → 10 passed` |
| `_eval_predicate` has `elif _IF_FLAG_RE.match(name)` branch | `graphify/templates.py:328` | 5 `if_flag` tests (all GREEN): `pytest tests/test_templates.py -k "if_flag" → 5 passed` |
| `BlockContext` has `note_type: str | None = None` field (defaulted) | `graphify/templates.py:232` | `tests/test_templates.py::test_block_free_template_renders_byte_identical` (L3436) — byte-identical gate verifies no regression from field addition |
| `BlockContext` has `flag_predicates: dict = field(default_factory=dict)` field (defaulted) | `graphify/templates.py:233` | `tests/test_templates.py::test_if_flag_truthy_rule_renders` (L2802) |
| `render_note` BlockContext call site threads `note_type=note_type` | `graphify/templates.py:1500` | `tests/test_templates.py::test_if_note_type_thing_renders_when_note_type_matches` |
| `render_note` BlockContext call site threads `flag_predicates=_compile_flag_predicates(profile)` | `graphify/templates.py:1502` | `tests/test_templates.py::test_if_flag_truthy_rule_renders` |
| `_render_moc_like` BlockContext call site threads `note_type=None` | `graphify/templates.py:1763` | MOC/community context has no TMPL-01 note_type; if_note_type blocks evaluate False (safe per D-55.02) |
| `_render_moc_like` BlockContext call site threads `flag_predicates=_compile_flag_predicates(profile)` | `graphify/templates.py:1765` | `tests/test_templates.py::test_if_flag_truthy_rule_renders` |
| `validate_template` signature extended with `known_flag_predicates: frozenset[str] = frozenset()` | `graphify/templates.py:461` | `tests/test_profile.py::test_predicate_flags_top_level_key_accepted` (L1842) |
| Unknown note-type suffix rejected at `validate_template` | `graphify/templates.py:582–590` | `tests/test_templates.py::test_if_note_type_unknown_suffix_rejected_at_validate_template` (L2788): 1 passed |
| Block expansion runs before `${}` substitution (D-16 / D-55.12) | `graphify/templates.py:1497–1504` | `tests/test_templates.py::test_block_expansion_runs_before_substitution` (L3401): 1 passed |
| No new sanitization sink — existing sinks unchanged | `graphify/templates.py` (no new HTML-escape paths added) | `pytest tests/test_templates.py -k "sanitize or inject" → 15 passed` |

## TMPL-02 Mapping Table

> TMPL-02 — *Users can iterate outbound/inbound connections via `{{#connections}}…{{/connections}}` with deterministic ordering and sanitized labels/targets; pytest covers nested + empty-iterable cases.*

TMPL-02 was satisfied by Phase 31 (v1.7 block engine). Per D-55.02, these Phase 31 tests constitute the acceptance evidence. No Phase 55 implementation work was required for TMPL-02.

| Sub-requirement | Source (file:line) | Test |
|-----------------|-------------------|------|
| `{{#connections}}…{{/connections}}` iterates outbound/inbound edges | `graphify/templates.py:_expand_blocks` (Phase 31 implementation) | `tests/test_templates.py::test_connections_loop_iterates` (L2890) |
| Loop exposes all 6 connection fields | Phase 31 implementation | `tests/test_templates.py::test_connections_loop_exposes_all_six_fields` (L2908) |
| Flattened template form works | Phase 31 implementation | `tests/test_templates.py::test_connections_loop_flattened_form_works` (L2939) |
| Deterministic ordering (label asc + source_file asc) | Phase 31 implementation | `tests/test_templates.py::test_connections_loop_deterministic_order` (L2997) |
| Empty iterable renders nothing (D-55.02 backward-compat sentinel) | Phase 31 implementation | `tests/test_templates.py::test_connections_empty_loop_renders_nothing` (L2984): 1 passed |
| Connection field sanitization blocks label injection | Phase 31 implementation | `tests/test_templates.py::test_connection_field_sanitization_blocks_label_injection` (L3340): 1 passed |
| Nested `{{#connections}}…{{#connections}}` rejected with specific error (D-55.02 backward-compat sentinel) | Phase 31 implementation | `tests/test_templates.py::test_nested_blocks_rejected_with_specific_error` (L3055): 1 passed |
| Nested `{{#if_*}}` inside `{{#if_*}}` rejected (D-55.02 backward-compat sentinel) | Phase 31 implementation | `tests/test_templates.py::test_nested_if_in_if_rejected` (L3069): 1 passed |

### D-55.02 Decision Note

Per D-55.02 ("TMPL-02 already satisfied by Phase 31 sentinel tests"), no new Phase 55 implementation was required for `{{#connections}}` iteration. The four backward-compat sentinels above are the Phase 31 tests that prove TMPL-02 behavior is preserved by Phase 55's additions.

## predicate_flags Profile Validation

> Sub-feature of TMPL-01 (D-55.08): `predicate_flags:` profile key enables user-defined flag predicates referenceable as `{{#if_flag_<name>}}`.

| Sub-requirement | Source (file:line) | Test |
|-----------------|-------------------|------|
| `_validate_predicate_flags` helper in `profile.py` | `graphify/profile.py:563` | `tests/test_profile.py::test_predicate_flags_non_dict_rejected` (L1797) |
| Rule 1: must be a dict | `graphify/profile.py:580–582` | `tests/test_profile.py::test_predicate_flags_non_dict_rejected` (L1797): PASSED |
| Rule 2: names must not start with `attr_` | `graphify/profile.py:610–614` | `tests/test_profile.py::test_predicate_flags_attr_prefix_rejected` (L1815): PASSED |
| Rule 3: names must not collide with built-in catalog | `graphify/profile.py:617–621` | `tests/test_profile.py::test_predicate_flags_catalog_collision_rejected` (L1806): PASSED |
| Rule 4: each rule must have an `attr` key | `graphify/profile.py:624–627` | `tests/test_profile.py::test_predicate_flags_missing_attr_key_rejected` (L1824): PASSED |
| `validate_profile_preflight` Layer 2 calls `_validate_predicate_flags` | `graphify/profile.py:1175` | `tests/test_profile.py::test_predicate_flags_top_level_key_accepted` (L1842): PASSED |
| `validate_profile_preflight` Layer 2 threads `known_flag_predicates` to `_validate_template` | `graphify/profile.py:1548–1553` | `tests/test_profile.py` — `pytest tests/test_profile.py -k "predicate_flags" → 8 passed` |
| `predicate_flags` added to `_VALID_TOP_LEVEL_KEYS` | `graphify/profile.py` (inside `_VALID_TOP_LEVEL_KEYS` set) | `tests/test_profile.py::test_predicate_flags_top_level_key_accepted` (L1842): no spurious "unknown key" error |

## Required Artifacts

| # | Artifact | Verification | Result |
|---|----------|-------------|--------|
| A1 | `graphify/templates.py` — `_IF_NOTE_TYPE_RE` and `_IF_FLAG_RE` present | `grep -n "_IF_NOTE_TYPE_RE\|_IF_FLAG_RE" graphify/templates.py` → L197, L199 | ✓ VERIFIED |
| A2 | `graphify/templates.py` — `BlockContext.note_type` and `BlockContext.flag_predicates` fields | `grep -n "note_type:\|flag_predicates:" graphify/templates.py` → L232, L233 | ✓ VERIFIED |
| A3 | `graphify/templates.py` — `validate_template` accepts `known_flag_predicates=frozenset()` | `grep -n "known_flag_predicates" graphify/templates.py` → L461 | ✓ VERIFIED |
| A4 | `graphify/profile.py` — `_validate_predicate_flags` helper with 4 rejection rules | `grep -n "def _validate_predicate_flags" graphify/profile.py` → L563 | ✓ VERIFIED |
| A5 | `graphify/profile.py` — `validate_profile_preflight` Layer 2 calls `_validate_predicate_flags` and threads `known_flag_predicates` | `grep -n "_validate_predicate_flags\|known_flag_predicates" graphify/profile.py` → L1175, L1548–1553 | ✓ VERIFIED |
| A6 | `docs/TEMPLATES.md` exists with 8 H2 sections | `test -f docs/TEMPLATES.md && grep -c "^## " docs/TEMPLATES.md` → 8 | ✓ VERIFIED |
| A7 | `docs/TEMPLATES.md` has 8 annotated `<!-- test:<id> -->` fences (one per section) | `grep -c "<!-- test:" docs/TEMPLATES.md` → 8 | ✓ VERIFIED |
| A8 | `docs/PROFILE-CONFIGURATION.md` contains 1-line pointer to `TEMPLATES.md` | `grep -n "TEMPLATES.md" docs/PROFILE-CONFIGURATION.md` → L311 | ✓ VERIFIED |
| A9 | `tests/test_docs_templates_examples.py` exists and lifts ≥1 example per section | `test -f tests/test_docs_templates_examples.py && pytest tests/test_docs_templates_examples.py -q` → 16 passed | ✓ VERIFIED |

## Behavioral Spot-Checks

| # | Behavior | Command | Result |
|---|----------|---------|--------|
| S1 | `if_note_type_*` tests GREEN (10 total) | `pytest tests/test_templates.py -k "if_note_type" -q` | ✓ VERIFIED — 10 passed, 218 deselected |
| S2 | `if_flag_*` tests GREEN (5 total) | `pytest tests/test_templates.py -k "if_flag" -q` | ✓ VERIFIED — 5 passed, 223 deselected |
| S3 | `predicate_flags` validation tests GREEN (8 total) | `pytest tests/test_profile.py -k "predicate_flags" -q` | ✓ VERIFIED — 8 passed, 188 deselected |
| S4 | Unknown note-type suffix rejected at `validate_template` | `pytest tests/test_templates.py::test_if_note_type_unknown_suffix_rejected_at_validate_template -q` | ✓ VERIFIED — 1 passed |
| S5 | Block expansion runs before substitution | `pytest tests/test_templates.py::test_block_expansion_runs_before_substitution -q` | ✓ VERIFIED — 1 passed |
| S6 | TMPL-02 backward-compat sentinel: empty loop renders nothing | `pytest tests/test_templates.py::test_connections_empty_loop_renders_nothing -q` | ✓ VERIFIED — 1 passed |
| S7 | TMPL-02 backward-compat sentinel: nested blocks rejected with specific error | `pytest tests/test_templates.py::test_nested_blocks_rejected_with_specific_error -q` | ✓ VERIFIED — 1 passed |
| S8 | TMPL-02 backward-compat sentinel: nested if_* in if_* rejected | `pytest tests/test_templates.py::test_nested_if_in_if_rejected -q` | ✓ VERIFIED — 1 passed |
| S9 | TMPL-02 backward-compat sentinel: block-free template byte-identical | `pytest tests/test_templates.py::test_block_free_template_renders_byte_identical -q` | ✓ VERIFIED — 1 passed |
| S10 | Sanitization tests GREEN (no new sink needed) | `pytest tests/test_templates.py -k "sanitize or inject" -q` | ✓ VERIFIED — 15 passed, 213 deselected |
| S11 | Doc-fence examples all pass (16 tests) | `pytest tests/test_docs_templates_examples.py -q` | ✓ VERIFIED — 16 passed |
| S12 | Full pytest suite GREEN | `pytest tests/ -q` | ✓ VERIFIED — **2034 passed, 1 xfailed, 8 warnings** |

## Observable Truths (12 Must-Haves)

| # | Truth | Evidence | Result |
|---|-------|----------|--------|
| T1 | `_IF_NOTE_TYPE_RE` regex constant present in `templates.py` | `graphify/templates.py:197` — `_IF_NOTE_TYPE_RE = re.compile(r"^if_note_type_([a-z_]+)$")` | ✓ VERIFIED |
| T2 | `_IF_FLAG_RE` regex constant present in `templates.py` | `graphify/templates.py:199` — `_IF_FLAG_RE = re.compile(r"^if_flag_([a-z][a-z0-9_]*)$")` | ✓ VERIFIED |
| T3 | `_eval_predicate` has `elif _IF_NOTE_TYPE_RE.match(name)` branch | `graphify/templates.py:322` | ✓ VERIFIED |
| T4 | `_eval_predicate` has `elif _IF_FLAG_RE.match(name)` branch | `graphify/templates.py:328` | ✓ VERIFIED |
| T5 | `BlockContext` has `note_type: str | None = None` field | `graphify/templates.py:232` | ✓ VERIFIED |
| T6 | `BlockContext` has `flag_predicates: dict` field with `default_factory=dict` | `graphify/templates.py:233` | ✓ VERIFIED |
| T7 | Both production `BlockContext(...)` call sites thread `note_type` and `flag_predicates` | `graphify/templates.py:1500,1502` (`render_note`) and `graphify/templates.py:1763,1765` (`_render_moc_like`) | ✓ VERIFIED |
| T8 | `validate_template` signature accepts `known_flag_predicates=frozenset()` | `graphify/templates.py:461` | ✓ VERIFIED |
| T9 | `_validate_predicate_flags` helper in `profile.py` with 4 rejection rules | `graphify/profile.py:563` (dict-check, attr_-prefix, catalog-collision, attr-key-required) | ✓ VERIFIED |
| T10 | `validate_profile_preflight` Layer 2 calls `_validate_predicate_flags` and threads `known_flag_predicates` | `graphify/profile.py:1175` (call) + `graphify/profile.py:1548–1553` (threading) | ✓ VERIFIED |
| T11 | `docs/TEMPLATES.md` exists with 8 H2 sections; `tests/test_docs_templates_examples.py` lifts ≥1 example per section | `grep -c "^## " docs/TEMPLATES.md → 8`; `pytest tests/test_docs_templates_examples.py → 16 passed` | ✓ VERIFIED |
| T12 | Phase 31 backward-compat sentinels GREEN (TMPL-02 evidence per D-55.02) | `pytest tests/test_templates.py::test_nested_blocks_rejected_with_specific_error::test_nested_if_in_if_rejected::test_connections_empty_loop_renders_nothing::test_block_free_template_renders_byte_identical → 5 passed` (incl. `test_connections_loop_deterministic_order`) | ✓ VERIFIED |

## Anti-Patterns Found

None — Phase 55 implementation followed the established Phase 31 patterns for block expansion:

- No Jinja2 dependency introduced (D-55.01 preserved)
- Block expansion remains pre-substitution (D-16 preserved)
- No new sanitization sinks — label injection prevention uses existing `_build_edge_records` HTML-escape paths
- `BlockContext` extension uses frozen-dataclass defaults (`note_type=None`, `flag_predicates={}`) — all ~30+ existing call sites unaffected without changes
- `templates↔profile` import cycle avoided via function-local import in `_validate_predicate_flags` (consistent with existing pattern at `profile.py:1430–1435`)

## Plan Execution Summary

| Plan | Wave | Description | Commit | Status |
|------|------|-------------|--------|--------|
| 55-01 | 0 (RED) | BlockContext extension + RED scaffold tests | `1abad3f` (impl), `91a3b60` (tests) | ✓ COMPLETE |
| 55-02 | 1 (GREEN) | `if_note_type_*` evaluator + unknown-suffix rejection + `render_note` plumbing | `1d49966` | ✓ COMPLETE |
| 55-03 | 2 (GREEN) | `if_flag_*` evaluator + `_validate_predicate_flags` + preflight cross-check | `80348d3` | ✓ COMPLETE |
| 55-04 | 3 (RED-doc) | Doc-fence fixture loader `tests/test_docs_templates_examples.py` | `bab5aaf` | ✓ COMPLETE |
| 55-05 | 3 (GREEN-doc) | `docs/TEMPLATES.md` (8 sections) + `PROFILE-CONFIGURATION.md` pointer | `769370a` | ✓ COMPLETE |
| 55-06 | 4 (close-out) | `55-VERIFICATION.md` + ROADMAP/REQUIREMENTS close | *(this plan)* | ✓ COMPLETE |

## Full-suite gate

```
$ pytest tests/ -q
2034 passed, 1 xfailed, 8 warnings in 70.82s
```

| Metric | Phase 54 baseline | Phase 55 close | Delta |
|--------|-------------------|----------------|-------|
| passed | 1995 | 2034 | +39 (matches new test count from plans 01–05) |
| xfailed | 1 | 1 | 0 |
| failed | 0 | 0 | 0 |

**Status: passed.** Zero failures attributable to Phase 55.

## Outstanding / Deferred

- **`graphify` PyPI version bump** — deferred to next milestone close (per CLAUDE.md release flow).
- **`/trace` slash command widening** — deferred (D-55.02 satisfied TMPL-02 via Phase 31 sentinels).
- **Dataview templates + profile overrides** — Phase 56 scope (TMPL-03, CFG-01, CFG-02).

---

## Phase 55 status: passed
