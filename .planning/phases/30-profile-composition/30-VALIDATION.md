---
phase: 30
slug: profile-composition
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-04-28
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
| **Estimated runtime** | ~3 seconds (composition tests); ~90 seconds (full) |

---

## Sampling Rate

- **After every task commit:** Run `pytest tests/test_profile_composition.py tests/test_profile.py -q`
- **After every plan wave:** Run `pytest tests/ -q`
- **Before `/gsd-verify-work`:** Full suite must be green
- **Max feedback latency:** 5 seconds (composition + profile tests)

---

## Per-Task Verification Map

> Filled by gsd-planner during planning. Each task gets a row mapping it to the test it produces or extends. Status starts ⬜ pending and is updated by gsd-executor as tasks complete.

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| TBD by planner | — | — | CFG-02 / CFG-03 | — | — | unit | — | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/test_profile_composition.py` — new test file, stubs for all CFG-02 / CFG-03 cases
- [ ] `tests/fixtures/profiles/` — fixture vaults for extends chains, includes lists, cycle scenarios, depth-cap, partial fragments, path-escape attempts, community-template patterns, missing template files
- [ ] `tests/conftest.py` — verify existing `tmp_path`-based isolation patterns suffice (no new shared fixture expected per CONTEXT.md D-08)

*Existing pytest infrastructure covers everything else — framework already installed, runner already configured.*

---

## Test Cases (from RESEARCH.md Validation Architecture)

> Per-success-criterion mapping. Final per-task assignment is filled by gsd-planner.

### Success Criterion 1 — extends/includes resolves with deterministic merge order; cycles detected
- `test_extends_single_parent_merges` — string `extends:` chain merges parent under child
- `test_includes_ordered_merges_in_declared_order` — list `includes:` last wins
- `test_extends_then_includes_then_own_fields_order` — full D-02 ordering
- `test_extends_chain_post_order_root_first` — A → B → C: C's fields foundation, A wins on conflict
- `test_includes_only_no_extends` — `extends:` absent works
- `test_extends_only_no_includes` — `includes:` absent works
- `test_neither_extends_nor_includes_unchanged_behavior` — back-compat: profile without composition keys parses identically to today
- `test_cycle_self_reference_detected` — `a.yaml extends: a.yaml`
- `test_cycle_two_node_a_extends_b_extends_a` — direct cycle
- `test_cycle_three_node_chain_detected` — A → B → C → A
- `test_cycle_via_includes_detected` — cycle through `includes:` not just `extends:`
- `test_cycle_diamond_legitimate_not_flagged` — A extends B; A includes C; C extends B (diamond is OK, not a cycle)
- `test_depth_cap_8_enforced` — chain depth 9 rejected with clear error
- `test_depth_cap_8_allowed` — chain depth 8 succeeds
- `test_extends_must_be_string_not_list` — D-03 list rejected with validation error
- `test_includes_must_be_list_not_string` — schema-tightening symmetry

### Success Criterion 2 — community_templates first-match-wins
- `test_community_templates_label_glob_match` — `transformer*` hits "transformer-encoder"
- `test_community_templates_id_exact_match` — `match: id, pattern: 0` hits community 0
- `test_community_templates_first_match_wins` — multiple matches, top rule wins
- `test_community_templates_no_match_falls_back_to_default` — default community template path used when no rule matches
- `test_community_templates_invalid_match_field_rejected` — `match: foo` validation error
- `test_community_templates_missing_template_file_warns` — referenced template path doesn't exist on disk → clear error or warning during preflight
- `test_community_templates_moc_only_scope` — D-12: member nodes (Things, Statements) keep type-based templates even when override matches
- `test_community_templates_fnmatch_case_sensitive` — `transformer*` does NOT match "Transformer-X" (fnmatchcase semantics)

### Success Criterion 3 — --validate-profile reports merge chain and resolved community templates
- `test_validate_profile_prints_merge_chain` — output contains `Merge chain:` with arrow-joined paths in resolution order
- `test_validate_profile_prints_field_provenance` — output contains `Field provenance:` with dotted-keys → source-file mapping
- `test_validate_profile_prints_resolved_community_templates` — output contains `Resolved community templates:` with rules-as-written + "no graph available" note
- `test_validate_profile_exits_zero_on_valid_composed` — exit code 0 with all 3 sections present
- `test_validate_profile_exits_nonzero_on_cycle` — D-04: --validate-profile returns non-zero exit and prints chain
- `test_validate_profile_exits_nonzero_on_path_escape` — fragment escapes `.graphify/` → non-zero exit

### Success Criterion 4 — removing extends: shows lost fields
- `test_removing_extends_shrinks_provenance_table` — provenance table loses entries previously sourced from removed parent
- `test_removing_extends_drops_fields_visible_in_diff` — D-15: leaf keys traced to removed file disappear from `Field provenance:` output

### Path Resolution & Security (D-06, D-07)
- `test_relative_path_resolves_from_referencing_file` — sibling-relative resolution
- `test_absolute_path_rejected` — D-07: absolute path rejected with clear error
- `test_path_traversal_rejected` — `../../../etc/passwd` and `../sibling-vault/profile.yaml` rejected
- `test_symlink_pointing_outside_dotgraphify_rejected` — confinement honored
- `test_partial_fragment_validates_when_composed` — D-08: fragment missing required fields composes cleanly into a valid profile
- `test_partial_fragment_alone_is_not_validated` — `validate_profile()` not run on individual fragments

### load_profile() Graceful Fallback (D-04)
- `test_load_profile_cycle_returns_default` — `load_profile()` prints error to stderr but returns `_DEFAULT_PROFILE` (graphify-never-crashes contract)
- `test_load_profile_path_escape_returns_default` — same contract for path-escape errors
- `test_load_profile_missing_fragment_returns_default` — same contract for missing referenced fragment

**Total: ~33 test cases across CFG-02 / CFG-03.** Mapping back to roadmap success criteria: 16 cover SC#1, 8 cover SC#2, 6 cover SC#3, 2 cover SC#4 (others are cross-cutting).

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Real-vault smoke test on Ideaverse profile.yaml without composition | CFG-02 | Validates v1.0 profiles unchanged in real Obsidian vault | Run `graphify --validate-profile <ideaverse-vault>` against an existing v1.0 vault — output should add new sections but show single-element merge chain and no community_templates rules |
| Real-vault smoke test of fragmented profile | CFG-02 + CFG-03 | End-to-end vault export with composed profile | Build a vault with `extends: bases/fusion.yaml`, `includes: [mixins/team-tags.yaml]`, and `community_templates`, run `graphify --obsidian` against a small repo, inspect generated MOC notes for correct template selection |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references (test file + fixtures directory)
- [ ] No watch-mode flags
- [ ] Feedback latency < 5s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
