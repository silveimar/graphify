---
phase: 30
slug: profile-composition
status: complete
nyquist_compliant: true
wave_0_complete: true
created: 2026-04-28
audited: 2026-04-28
---

# Phase 30 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 7.x (Python 3.10+) |
| **Config file** | `pyproject.toml` (existing pytest config under `[tool.pytest.ini_options]`) |
| **Quick run command** | `pytest tests/test_profile_composition.py -q` |
| **Full suite command** | `pytest tests/ -q` |
| **Estimated runtime** | ~1 second (composition tests, measured 0.99s); ~90 seconds (full) |

---

## Sampling Rate

- **After every task commit:** Run `pytest tests/test_profile_composition.py tests/test_profile.py -q`
- **After every plan wave:** Run `pytest tests/ -q`
- **Before `/gsd-verify-work`:** Full suite must be green
- **Max feedback latency:** 5 seconds (composition + profile tests)

---

## Per-Task Verification Map

> Each row maps a plan task to the test(s) that pin its behavior. Status set by audit on 2026-04-28 (post-execution).

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 30-01-T1 | 30-01 | 0 | CFG-02 | T-30-01 / T-30-02 | Path confinement, depth cap, cycle detect (RED scaffolding) | unit + fixtures | `pytest tests/test_profile_composition.py -q` | ✅ | ✅ green |
| 30-01-T2 | 30-01 | 1 | CFG-02 | T-30-01 / T-30-02 / T-30-03 | `_resolve_profile_chain`, `_deep_merge_with_provenance`, `is_relative_to` confinement, `yaml.safe_load` only | unit | `pytest tests/test_profile_composition.py -q -k "extends or includes or cycle or depth or partial or path or symlink or absolute or load_profile or resolved or deep_merge or provenance"` | ✅ | ✅ green |
| 30-02-T1 | 30-02 | 0 | CFG-03 | — | RED tests for community_templates dispatch + fixture vault | unit + fixtures | `pytest tests/test_profile_composition.py -q -k "community_templates or override"` | ✅ | ✅ green |
| 30-02-T2 | 30-02 | 1 | CFG-03 | T-30-04 | `_pick_community_template` (first-match-wins, fnmatchcase, MOC-only), `_load_override_template` graceful fallback | unit | `pytest tests/test_profile_composition.py -q -k "community_templates or override"` | ✅ | ✅ green |
| 30-03-T1 | 30-03 | 0 | CFG-02 + CFG-03 | — | RED tests for --validate-profile output: merge chain, provenance, community-templates rules, lost-fields flow | unit + fixtures + subprocess | `pytest tests/test_profile_composition.py -q -k "validate_profile"` | ✅ | ✅ green |
| 30-03-T2 | 30-03 | 1 | CFG-02 + CFG-03 | — | Always-print informational sections (D-14), graph-blind disclaimer (D-17), exit-code contract preserved | unit + subprocess | `pytest tests/test_profile_composition.py -q -k "validate_profile"` | ✅ | ✅ green |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [x] `tests/test_profile_composition.py` — 48 `def test_*` cases covering CFG-02 + CFG-03 (`grep -c '^def test_'` = 48)
- [x] `tests/fixtures/profiles/` — 13 fixture vaults present: `single_file`, `linear_chain`, `linear_chain_valid`, `includes_only`, `extends_and_includes`, `cycle_self`, `cycle_indirect`, `cycle_via_profile_yaml`, `diamond`, `partial_fragment`, `community_templates`, `path_escape`, `lost_fields_demo`
- [x] `tests/conftest.py` — existing `tmp_path`-based isolation patterns sufficed (D-08); no shared fixture added

*Existing pytest infrastructure covered everything else — framework already installed, runner already configured.*

---

## Test Cases — Implemented Coverage

> Per-success-criterion mapping with actual test names from `tests/test_profile_composition.py` (audited 2026-04-28). Implemented suite expanded planned ~33 cases to 48; all extras tighten edge-case behavior.

### Success Criterion 1 — extends/includes resolves with deterministic merge order; cycles detected (CFG-02)

- ✅ `test_extends_single_parent_merges`
- ✅ `test_includes_ordered_last_wins`
- ✅ `test_extends_then_includes_then_own_fields_order`
- ✅ `test_neither_extends_nor_includes_unchanged_behavior`
- ✅ `test_extends_must_be_string_not_list`
- ✅ `test_includes_must_be_list_not_string`
- ✅ `test_cycle_self_reference_detected`
- ✅ `test_cycle_indirect_chain_detected`
- ✅ `test_cycle_via_includes_detected`
- ✅ `test_diamond_inheritance_not_cycle`
- ✅ `test_depth_cap_8_allowed`
- ✅ `test_depth_cap_9_rejected`
- ✅ `test_partial_fragment_validates_when_composed`
- ✅ `test_partial_fragment_alone_is_not_validated`
- ✅ `test_resolved_profile_namedtuple_shape`
- ✅ `test_deep_merge_with_provenance_does_not_mutate_base`
- ✅ `test_provenance_records_dotted_keys`
- ✅ `test_provenance_list_typed_leaves_record_at_list_level` *(extra: pins list-leaf provenance semantics)*

### Success Criterion 2 — community_templates first-match-wins (CFG-03)

- ✅ `test_community_templates_label_glob_match`
- ✅ `test_community_templates_id_exact_match`
- ✅ `test_community_templates_first_match_wins`
- ✅ `test_community_templates_no_match_falls_back_to_default`
- ✅ `test_community_templates_fnmatch_case_sensitive`
- ✅ `test_community_templates_question_mark_glob` *(extra: `?` glob semantics)*
- ✅ `test_community_templates_id_pattern_bool_rejected` *(extra: bool-vs-int discriminator)*
- ✅ `test_community_templates_label_pattern_int_rejected` *(extra: type discrimination)*
- ✅ `test_community_templates_unknown_keys_rejected` *(extra: schema strictness)*
- ✅ `test_override_template_path_escape_falls_back`
- ✅ `test_override_template_missing_file_falls_back`
- ✅ `test_override_template_invalid_placeholder_falls_back` *(extra: malformed override template safety)*
- ✅ `test_override_scope_moc_only` (D-12)

### Success Criterion 3 — --validate-profile reports merge chain and resolved community templates

- ✅ `test_validate_profile_prints_merge_chain`
- ✅ `test_validate_profile_prints_field_provenance`
- ✅ `test_validate_profile_prints_resolved_community_templates`
- ✅ `test_validate_profile_single_file_shows_no_rules` *(extra: empty-rules edge case)*
- ✅ `test_validate_profile_exits_zero_on_valid_composed`
- ✅ `test_validate_profile_exits_nonzero_on_cycle` (D-04)
- ✅ `test_validate_profile_exits_nonzero_on_path_escape`
- ✅ `test_validate_profile_graph_blind_note` *(extra: D-17 disclaimer presence)*

### Success Criterion 4 — removing extends: shows lost fields

- ✅ `test_validate_profile_lost_fields_after_extends_removal` (D-15)

### Path Resolution & Security (D-06, D-07)

- ✅ `test_absolute_extends_path_rejected`
- ✅ `test_extends_traversal_rejected`
- ✅ `test_extends_symlink_escape_rejected`
- ✅ `test_sibling_relative_path_resolution`
- ✅ `test_malformed_yaml_in_fragment` *(extra: YAML parser failure path)*

### load_profile() Graceful Fallback (D-04)

- ✅ `test_load_profile_cycle_returns_default`
- ✅ `test_load_profile_path_escape_returns_default`
- ✅ `test_load_profile_missing_fragment_returns_default`

**Total: 48 implemented tests across CFG-02 / CFG-03.** All green in 0.99s. SC#1: 18 · SC#2: 13 · SC#3: 8 · SC#4: 1 · cross-cutting: 8.

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Real-vault smoke test on Ideaverse profile.yaml without composition | CFG-02 | Validates v1.0 profiles unchanged in real Obsidian vault | Run `graphify --validate-profile <ideaverse-vault>` against an existing v1.0 vault — output should add new sections but show single-element merge chain and no community_templates rules |
| Real-vault smoke test of fragmented profile | CFG-02 + CFG-03 | End-to-end vault export with composed profile | Build a vault with `extends: bases/fusion.yaml`, `includes: [mixins/team-tags.yaml]`, and `community_templates`, run `graphify --obsidian` against a small repo, inspect generated MOC notes for correct template selection |

---

## Validation Sign-Off

- [x] All tasks have automated verification (pytest commands above)
- [x] Sampling continuity: every task wave is automated; no 3 consecutive tasks without automated verify
- [x] Wave 0 covers all MISSING references (test file + 13 fixture vaults)
- [x] No watch-mode flags
- [x] Feedback latency < 5s (measured: 0.99s)
- [x] `nyquist_compliant: true` set in frontmatter

**Approval:** approved 2026-04-28 (gsd-validate-phase audit)

---

## Validation Audit 2026-04-28

| Metric | Count |
|--------|-------|
| Gaps found | 0 |
| Resolved | 0 |
| Escalated | 0 |
| Tests already implemented (COVERED) | 48 |
| Tests added by this audit | 0 |
| Manual-only carried forward | 2 |

**Method:** State A audit — VALIDATION.md pre-existed in draft form (planning template, no per-task rows filled). Cross-referenced against `tests/test_profile_composition.py` (48 `def test_*`), 13 fixture vaults under `tests/fixtures/profiles/`, three SUMMARY.md files, and 30-VERIFICATION.md (4/4 success criteria PASSED). All requirements have automated subprocess + pytest coverage; no test generation needed. Updated frontmatter (`status: complete`, `nyquist_compliant: true`, `wave_0_complete: true`), filled Per-Task Map with concrete task IDs, replaced planned test list with implemented test names, checked off Wave 0 + Sign-Off boxes.

**Outcome:** Phase 30 is Nyquist-compliant. No auditor spawn required.
