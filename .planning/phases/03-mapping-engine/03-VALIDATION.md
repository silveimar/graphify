---
phase: 3
slug: 03-mapping-engine
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-04-11
---

# Phase 3 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest (latest, no version pin — verified pyproject.toml + .planning/codebase/TESTING.md) |
| **Config file** | none — no pytest.ini / [tool.pytest] section |
| **Quick run command** | `pytest tests/test_mapping.py -q` |
| **Full suite command** | `pytest tests/ -q` |
| **Estimated runtime** | <1s quick / ~5s full (pure-dict/graph unit tests, no tmp_path, no network) |

---

## Sampling Rate

- **After every task commit:** Run `pytest tests/test_mapping.py -q`
- **After every plan wave:** Run `pytest tests/test_mapping.py tests/test_profile.py tests/test_templates.py -q`
- **Before `/gsd-verify-work`:** Full suite must be green (`pytest tests/ -q`)
- **Max feedback latency:** <5 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 3-01-01 | 01 | 1 | MAP-01 | — | Default folder from folder_mapping when rule omits `then.folder` | unit | `pytest tests/test_mapping.py::test_classify_default_statement_uses_folder_mapping_default -x` | ❌ W0 | ⬜ pending |
| 3-01-02 | 01 | 1 | MAP-01 | T-3-02 path-traversal | Per-rule `then.folder` override applied and re-validated | unit | `pytest tests/test_mapping.py::test_classify_rule_folder_override -x` | ❌ W0 | ⬜ pending |
| 3-01-03 | 01 | 1 | MAP-02 | — | God-node list classified as Thing in topology fallback | unit | `pytest tests/test_mapping.py::test_classify_topology_fallback_god_node_becomes_thing -x` | ❌ W0 | ⬜ pending |
| 3-01-04 | 01 | 1 | MAP-02 | — | Above-threshold community emitted as MOC | unit | `pytest tests/test_mapping.py::test_community_above_threshold_becomes_moc -x` | ❌ W0 | ⬜ pending |
| 3-01-05 | 01 | 1 | MAP-02 | — | Unmatched real node routes to default statement | unit | `pytest tests/test_mapping.py::test_classify_default_statement_when_no_match -x` | ❌ W0 | ⬜ pending |
| 3-01-06 | 01 | 1 | MAP-03 | — | Attribute rule `file_type: person` beats topology | unit | `pytest tests/test_mapping.py::test_classify_attribute_rule_beats_topology -x` | ❌ W0 | ⬜ pending |
| 3-01-07 | 01 | 1 | MAP-04 | — | Precedence order: attribute > topology > default observable | unit | `pytest tests/test_mapping.py::test_classify_first_match_wins_rule_order -x` | ❌ W0 | ⬜ pending |
| 3-01-08 | 01 | 1 | MAP-04 | — | First-match-wins within the rule list | unit | `pytest tests/test_mapping.py::test_classify_first_rule_locks_outcome -x` | ❌ W0 | ⬜ pending |
| 3-01-09 | 01 | 1 | MAP-05 | — | `_DEFAULT_PROFILE.mapping.moc_threshold == 3` | unit | `pytest tests/test_mapping.py::test_default_profile_moc_threshold_is_3 -x` | ❌ W0 | ⬜ pending |
| 3-01-10 | 01 | 1 | MAP-05 | — | Below-threshold community collapses into host MOC | unit | `pytest tests/test_mapping.py::test_community_below_threshold_collapses_to_host -x` | ❌ W0 | ⬜ pending |
| 3-01-11 | 01 | 1 | MAP-05 | — | Nearest-host resolution picks `arg max` by inter-community edge count | unit | `pytest tests/test_mapping.py::test_nearest_host_arg_max_by_edge_count -x` | ❌ W0 | ⬜ pending |
| 3-01-12 | 01 | 1 | MAP-05 | — | Tie-break: largest host then lowest cid | unit | `pytest tests/test_mapping.py::test_nearest_host_tiebreak_largest_then_lowest_cid -x` | ❌ W0 | ⬜ pending |
| 3-01-13 | 01 | 1 | MAP-05 | — | Host-less below-threshold falls into synthetic `Uncategorized` bucket MOC | unit | `pytest tests/test_mapping.py::test_bucket_moc_absorbs_hostless_below_threshold -x` | ❌ W0 | ⬜ pending |
| 3-01-14 | 01 | 1 | MAP-06 | — | `source_file_ext` matcher routes `.py` to sub-folder | unit | `pytest tests/test_mapping.py::test_classify_source_file_ext_routes_to_custom_folder -x` | ❌ W0 | ⬜ pending |
| 3-01-15 | 01 | 1 | MAP-06 | — | `{topology: is_source_file}` explicit rule opts file hubs back in | unit | `pytest tests/test_mapping.py::test_classify_file_hub_opted_in_by_rule -x` | ❌ W0 | ⬜ pending |
| 3-02-01 | 02 | 2 | D-58 | — | Community label = top god node inside community | unit | `pytest tests/test_mapping.py::test_community_label_top_god_node_in_community -x` | ❌ W0 | ⬜ pending |
| 3-02-02 | 02 | 2 | D-58 | — | All-synthetic community falls back to `"Community N"` | unit | `pytest tests/test_mapping.py::test_community_label_fallback_to_community_n -x` | ❌ W0 | ⬜ pending |
| 3-02-03 | 02 | 2 | D-59 | — | `community_tag == safe_tag(community_name)` | unit | `pytest tests/test_mapping.py::test_community_tag_is_safe_tag_of_name -x` | ❌ W0 | ⬜ pending |
| 3-02-04 | 02 | 2 | D-60 | — | `sibling_labels` capped at 5 | unit | `pytest tests/test_mapping.py::test_sibling_labels_cap_at_5 -x` | ❌ W0 | ⬜ pending |
| 3-02-05 | 02 | 2 | D-60 | — | `sibling_labels` excludes current node label | unit | `pytest tests/test_mapping.py::test_sibling_labels_exclude_current_node -x` | ❌ W0 | ⬜ pending |
| 3-02-06 | 02 | 2 | D-50 | — | Concept + file hubs appear in `skipped_node_ids`, not `per_node` | unit | `pytest tests/test_mapping.py::test_concept_and_file_hubs_are_skipped -x` | ❌ W0 | ⬜ pending |
| 3-02-07 | 02 | 2 | D-49 | — | Zero god nodes is valid state (no crash, no fallback promotion) | unit | `pytest tests/test_mapping.py::test_classify_zero_god_nodes_no_crash -x` | ❌ W0 | ⬜ pending |
| 3-03-01 | 03 | 1 | D-44 | T-3-01 ReDoS | Regex pattern length >512 chars rejected at validation time | unit | `pytest tests/test_mapping.py::test_validate_rules_regex_too_long_rejected -x` | ❌ W0 | ⬜ pending |
| 3-03-02 | 03 | 1 | D-44 | T-3-01 ReDoS | Candidate string length >2048 chars → matcher returns False | unit | `pytest tests/test_mapping.py::test_match_when_attr_regex_candidate_too_long_returns_false -x` | ❌ W0 | ⬜ pending |
| 3-03-03 | 03 | 1 | D-44 | T-3-04 non-string attr | Non-string attribute fed to `contains`/`regex` → matcher returns False (no crash) | unit | `pytest tests/test_mapping.py::test_match_when_non_string_attr_contains_returns_false -x` | ❌ W0 | ⬜ pending |
| 3-03-04 | 03 | 1 | D-45 | — | Dead-rule warning emitted for strict structural shadow | unit | `pytest tests/test_mapping.py::test_validate_rules_dead_rule_warning_identical -x` | ❌ W0 | ⬜ pending |
| 3-03-05 | 03 | 1 | D-45 | — | No cross-kind dead-rule false positives | unit | `pytest tests/test_mapping.py::test_validate_rules_no_dead_rule_warning_across_kinds -x` | ❌ W0 | ⬜ pending |
| 3-03-06 | 03 | 1 | D-47 | T-3-02 path-traversal | `then.folder` with `..` / absolute / `~` rejected at validation | unit | `pytest tests/test_mapping.py::test_validate_rules_rejects_path_traversal_in_folder -x` | ❌ W0 | ⬜ pending |
| 3-03-07 | 03 | 1 | D-47 | T-3-03 bool-as-int | `moc_threshold: true` rejected by validator | unit | `pytest tests/test_profile.py::test_default_profile_rejects_bool_as_int_threshold -x` | ❌ W0 | ⬜ pending |
| 3-04-01 | 04 | 3 | Contract | — | `classify()` output round-trips through `render_note()` without raising | integration (no IO) | `pytest tests/test_mapping.py::test_classify_output_round_trips_through_render_note -x` | ❌ W0 | ⬜ pending |
| 3-04-02 | 04 | 3 | Contract | — | `classify()` output round-trips through `render_moc()` without raising | integration (no IO) | `pytest tests/test_mapping.py::test_classify_output_round_trips_through_render_moc -x` | ❌ W0 | ⬜ pending |
| 3-04-03 | 04 | 3 | Profile | — | `validate_profile` surfaces `mapping_rules` errors in aggregate list | unit | `pytest tests/test_profile.py::test_validate_profile_surfaces_mapping_rules_errors -x` | ❌ W0 | ⬜ pending |
| 3-04-04 | 04 | 3 | Profile | — | `_deep_merge` respects new `topology` + `mapping` sections | unit | `pytest tests/test_profile.py::test_deep_merge_respects_topology_section -x` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/test_mapping.py` — new file; covers MAP-01..MAP-06 plus D-44..D-60 implementation verification
- [ ] `tests/fixtures/template_context.py` — extend with `make_classification_fixture()` helper for multi-community graphs with opt-in file-hub / concept nodes
- [ ] `tests/test_profile.py` — extend with `test_validate_profile_surfaces_mapping_rules_errors`, `test_default_profile_includes_topology_and_mapping_keys`, `test_deep_merge_respects_topology_section`, `test_default_profile_rejects_bool_as_int_threshold`
- [ ] No new framework install needed — pytest already the runner
- [ ] No new `conftest.py` — shared fixtures continue living in `tests/fixtures/template_context.py`

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| (none) | — | All phase behaviors have deterministic automated verification over pure functions of (graph, communities, profile) | — |

*All phase behaviors have automated verification.*

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 5s
- [ ] `nyquist_compliant: true` set in frontmatter (set by planner/executor when table is fully green)

**Approval:** pending
