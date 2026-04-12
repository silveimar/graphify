---
phase: 03-mapping-engine
verified: 2026-04-11T11:15:00Z
status: passed
score: 5/5 must-haves verified
overrides_applied: 0
---

# Phase 3: Mapping Engine Verification Report

**Phase Goal:** Every graph node is classified into exactly one note type and assigned a folder location, driven by topology and attribute rules from the profile.
**Verified:** 2026-04-11T11:15:00Z
**Status:** PASSED
**Re-verification:** No — initial verification

## Executive Summary

Phase 3 ships a pure-function classification engine (`graphify/mapping.py`, 1049 lines) that turns `(NetworkX graph, community partition, profile dict)` into a `MappingResult` TypedDict with per-node and per-community `ClassificationContext` entries. Every must-have is pinned to at least one binary-success test; all 17 verification tests pass. Requirements MAP-01..MAP-06 are covered across plans 01..04. Full test suite runs 663/663 green (excluding two pre-existing, worktree-path-dependent failures in `test_detect.py` / `test_extract.py` tracked in `deferred-items.md` — unrelated to Phase 3).

## Goal Achievement

### Must-Haves (Goal-Backward)

| # | Must-Have | Pinned Test(s) | Status | Evidence |
|---|-----------|----------------|--------|----------|
| 1 | God nodes land in `Atlas/Dots/Things/` by default AND in a custom folder when a rule overrides it | `test_classify_topology_fallback_god_node_becomes_thing`, `test_classify_rule_folder_override` | ✓ VERIFIED | Both tests PASS. n_transformer (top god node, top_n=1) falls through topology to `thing` + `Atlas/Dots/Things/`. Rule `{when: {attr: label, equals: Softmax}, then: {note_type: statement, folder: Atlas/Dots/Custom/}}` reroutes to custom folder. D-47 precedence pipeline confirmed. |
| 2 | Communities with ≥3 members produce MOC notes; below-threshold communities appear in the host MOC's `sub_communities` list | `test_community_above_threshold_becomes_moc`, `test_community_below_threshold_collapses_to_host`, `test_bucket_moc_absorbs_hostless_below_threshold` | ✓ VERIFIED | All three PASS. Fixture: cid 0 (6 members, threshold=3) → `per_community[0]["note_type"] == "moc"`. cid 1 (2 members) collapses into cid 0 via nearest-host (single inter-community edge `n_transformer — n_auth`). Bucket MOC absorbs host-less below-threshold communities (D-56). |
| 3 | A node with `file_type: person` under an attribute rule becomes a Person note even when it's also a god node | `test_classify_attribute_rule_beats_topology` | ✓ VERIFIED | PASS. n_auth has `file_type=person` AND is the top god node in cid 1. Explicit `{when: {attr: file_type, equals: person}, then: {note_type: person}}` rule wins over topology fallback. Assert `per_node[n_auth]["note_type"] == "person"`, `folder == "Atlas/Dots/People/"`. D-47 Step 1 beats Step 2. |
| 4 | A `source_file_ext` rule routes `.py` files to a custom folder (MAP-06 example) | `test_classify_source_file_ext_routes_to_custom_folder` | ✓ VERIFIED | PASS. Rule `{source_file_ext: .py, then: {note_type: source, folder: Atlas/Sources/Code/}}` routes n_softmax (source_file ends `.py`) to the custom folder. `_norm_ext_from_path` + `_norm_ext` normalize leading dot and case. |
| 5 | Precedence observable: attribute rule > topology rule > default, first-match-wins, verified by a test with competing rules on one node | `test_classify_first_match_wins_rule_order`, `test_classify_first_rule_locks_outcome` | ✓ VERIFIED | Both PASS. Rules `[{attr:file_type=person→person}, {topology:god_node→thing}]` applied to n_auth: first rule wins, `rule_traces[node_id=n_auth].rule_index == 0`. Second test confirms a later duplicate rule on the same predicate never fires (first locks). D-47 short-circuit semantics verified. |

**Score:** 5/5 must-haves verified.

### Additional Contract & Lock-in Tests

| # | Contract | Test | Status |
|---|----------|------|--------|
| C1 | classify() output round-trips through Phase 2 `render_note()` without raising | `test_classify_output_round_trips_through_render_note` | ✓ PASS |
| C2 | classify() output round-trips through Phase 2 `render_moc()` without raising; cohesion is a plain `float` | `test_classify_output_round_trips_through_render_moc` | ✓ PASS |
| C3 | Every member of cid 0 surfaces in rendered MOC text (members_by_type population) | `test_classify_output_round_trips_members_by_type_into_moc` | ✓ PASS |
| D60-1 | Non-god nodes receive `sibling_labels = []` (D-60 BLOCKER 1 fidelity fix) | `test_sibling_labels_empty_for_non_god_node` | ✓ PASS |
| D60-2 | `sibling_labels` capped at 5 | `test_sibling_labels_cap_at_5` | ✓ PASS |
| D60-3 | `sibling_labels` excludes current node label | `test_sibling_labels_exclude_current_node` | ✓ PASS |
| LZ-1 | `graphify.classify`, `graphify.validate_rules`, `graphify.MappingResult` callable via lazy map | `test_graphify_package_lazy_exports_classify` | ✓ PASS |
| LZ-2 | `graphify.classify is graphify.mapping.classify` (typo guard) | `test_graphify_classify_is_graphify_mapping_classify` | ✓ PASS |

All 17 pinned tests PASS (9 must-have tests + 8 contract/lock-in tests).

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `graphify/mapping.py` | Exports `classify`, `MappingResult`, `RuleTrace`, `compile_rules`, `_match_when`, `validate_rules`, `_MatchCtx`; imports `ClassificationContext` from `graphify.templates` | ✓ VERIFIED | 1049 lines. `from graphify.mapping import classify, MappingResult, validate_rules, compile_rules, ClassificationContext` succeeds. All 11 matcher kinds dispatched in `_match_when`. D-47 precedence pipeline implemented in `classify()`. `_assemble_communities` handles community-level enrichment. Length caps `_MAX_PATTERN_LEN=512`, `_MAX_CANDIDATE_LEN=2048` declared at module level. |
| `graphify/profile.py` | `_DEFAULT_PROFILE["topology"]["god_node"]["top_n"] == 10`, `_DEFAULT_PROFILE["mapping"]["moc_threshold"] == 3`, `validate_profile` delegates to `validate_rules` via function-local import | ✓ VERIFIED | Line 38: `"topology": {"god_node": {"top_n": 10}}`. Line 39: `"mapping": {"moc_threshold": 3}`. Line 255: `from graphify.mapping import validate_rules` (function-local, breaks `mapping → templates → profile` cycle, T-3-11 mitigation). `_VALID_TOP_LEVEL_KEYS` extended with `topology`, `mapping`. Bool-before-int guards for `top_n` and `moc_threshold`. |
| `graphify/__init__.py` | Lazy-import map contains `classify`, `MappingResult`, `validate_rules` entries pointing to `graphify.mapping` | ✓ VERIFIED | Lines 30-32: three new entries appended after Phase 2's template entries. No top-level `from graphify.mapping import ...` (lazy pattern preserved). Runtime smoke: `python -c "from graphify import classify, validate_rules, MappingResult; print(classify)"` succeeds. |
| `tests/test_mapping.py` | ≥30 tests covering MAP-01..MAP-06, D-44..D-60, contract round-trip | ✓ VERIFIED | 45 tests, all passing in 0.13s. Covers: 11 matcher kinds, precedence pipeline, synthetic-node filter, community assembly (above/below/bucket), D-60 sibling labels, validator (10 tests), contract round-trip (3 tests), lazy exports (2 tests). |
| `tests/test_profile.py` | 89 tests (81 Phase 1 baseline + 8 new Phase 3 extension tests) | ✓ VERIFIED | 89 tests, all passing. New Phase 3 tests: `test_default_profile_includes_topology_and_mapping_keys`, `test_default_profile_top_n_and_threshold_are_not_bool`, `test_deep_merge_respects_topology_section`, `test_default_profile_rejects_bool_as_int_threshold`, `test_validate_profile_rejects_bool_top_n`, `test_validate_profile_rejects_negative_top_n`, `test_validate_profile_surfaces_mapping_rules_errors`, `test_validate_profile_accepts_default_profile_unchanged`. Note: the verification checklist said "90+"; actual is 89 (baseline 81 + 8 new). |
| `tests/fixtures/template_context.py` | `make_classification_fixture()` helper producing 3-community + 1-isolate graph with synthetic nodes | ✓ VERIFIED | Extended in Plan 01. Reused across all mapping tests and by the Phase 2/3 round-trip contract tests. |

### Key Link Verification

| From | To | Via | Status | Details |
|------|-----|-----|--------|---------|
| `graphify/mapping.py::classify` | `graphify.analyze.god_nodes / _is_file_node / _is_concept_node / _node_community_map` | direct import | ✓ WIRED | `from graphify.analyze import ...` at mapping.py line 10-15. Confirmed by `test_concept_and_file_hubs_are_skipped`. |
| `graphify/mapping.py::classify` | `graphify/mapping.py::_assemble_communities` | second-pass after per-node | ✓ WIRED | classify() return block calls `_assemble_communities(...)` (line count: `grep '^def _assemble_communities' → 1 match`). Verified by `test_community_above_threshold_becomes_moc`. |
| `graphify/mapping.py::_resolve_folder` | `profile['folder_mapping']` | dict lookup with `then.folder` override | ✓ WIRED | `test_classify_rule_folder_override` and `test_classify_default_statement_uses_folder_mapping_default` both pass. |
| `graphify/profile.py::validate_profile` | `graphify/mapping.py::validate_rules` | function-local import at call site | ✓ WIRED | Line 255. Verified by `test_validate_profile_surfaces_mapping_rules_errors`: profile with malformed mapping_rules produces pointed `mapping_rules[0].then.note_type` errors. |
| `graphify/__init__.py::__getattr__` | `graphify.mapping` | lazy import map | ✓ WIRED | Three new entries verified by `test_graphify_classify_is_graphify_mapping_classify` (identity check: `graphify.classify is graphify.mapping.classify`). |
| `tests/test_mapping.py round-trip tests` | `graphify.templates.render_note / render_moc` | per_node / per_community contexts fed into rendering functions | ✓ WIRED | Three contract tests confirm every key consumed by Phase 2 is populated by Phase 3 with matching names: `community_name`, `community_tag`, `parent_moc_label`, `sibling_labels`, `members_by_type`, `sub_communities`, `cohesion` (plain float per WR-06). |

### Data-Flow Trace (Level 4)

| Artifact | Data Variable | Source | Produces Real Data | Status |
|----------|---------------|--------|--------------------|--------|
| `classify()` | `per_node` dict | Per-node loop over `G.nodes` with D-47 precedence pipeline + synthetic filter | Yes — live graph attrs + rule evaluation | ✓ FLOWING |
| `classify()` | `per_community` dict | `_assemble_communities(communities, per_node, god_node_ids, profile, cohesion)` second pass | Yes — iterates real communities, resolves hosts via edge walk | ✓ FLOWING |
| `_assemble_communities` | `cohesion` float per MOC | `score_all(G, communities)` called from classify(); wrapped with `float()` at every write site (WR-06) | Yes — plain Python float, not numpy.float64 (asserted by `test_classify_output_round_trips_through_render_moc`) | ✓ FLOWING |
| `_build_sibling_labels` | `sibling_labels` list | Top-5 god_node labels in same community by `G.degree()`, excluding self | Yes — real degree ranking; non-god nodes get `[]` (D-60 BLOCKER 1 fix) | ✓ FLOWING |
| `_nearest_host` | host cid | Single-pass `G.edges()` walk filtered through `node_to_community` (D-53 arg-max by edge count) | Yes — real edges, deterministic tie-break (count desc → size desc → cid asc) | ✓ FLOWING |

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
|----------|---------|--------|--------|
| Full mapping suite | `pytest tests/test_mapping.py -q` | `45 passed in 0.13s` | ✓ PASS |
| Full profile suite | `pytest tests/test_profile.py -q` | `89 passed in 0.15s` | ✓ PASS |
| Full templates suite (Phase 2 regression) | `pytest tests/test_templates.py -q` | `143 passed in 0.15s` | ✓ PASS |
| Full project suite (excluding pre-existing worktree-path failures) | `pytest tests/ -q --ignore=tests/test_detect.py --ignore=tests/test_extract.py` | `663 passed in 1.44s` | ✓ PASS |
| Lazy exports smoke | `python -c "import graphify; print(graphify.classify, graphify.validate_rules, graphify.MappingResult)"` | All three imports succeed | ✓ PASS |
| Default profile sanity | `grep -n '"top_n":\|"moc_threshold":' graphify/profile.py` | `top_n: 10`, `moc_threshold: 3` | ✓ PASS |

### Requirements Coverage

| Requirement | Description | Source Plans | Mapped Tests | Status |
|-------------|-------------|--------------|--------------|--------|
| MAP-01 | Notes placed in folders defined by `folder_mapping` | 03-01, 03-04 | `test_classify_default_statement_uses_folder_mapping_default`, `test_classify_topology_fallback_god_node_becomes_thing`, `test_classify_rule_folder_override` | ✓ SATISFIED |
| MAP-02 | Topology-based classification (god nodes → Things, communities → MOCs, source files → Sources) | 03-01, 03-02, 03-04 | `test_classify_topology_fallback_god_node_becomes_thing`, `test_community_above_threshold_becomes_moc`, `test_classify_zero_god_nodes_no_crash` | ✓ SATISFIED |
| MAP-03 | Attribute-based classification overrides topology | 03-01, 03-04 | `test_classify_attribute_rule_beats_topology`, `test_classify_rule_folder_override` | ✓ SATISFIED |
| MAP-04 | Dual evaluation: attribute > topology > default, first-match-wins | 03-01, 03-03, 03-04 | `test_classify_first_match_wins_rule_order`, `test_classify_first_rule_locks_outcome`, `test_classify_default_statement_when_no_match` | ✓ SATISFIED |
| MAP-05 | Community-to-MOC threshold configurable (default 3); below-threshold collapses | 03-02, 03-03, 03-04 | `test_community_above_threshold_becomes_moc`, `test_community_below_threshold_collapses_to_host`, `test_bucket_moc_absorbs_hostless_below_threshold`, `test_default_profile_rejects_bool_as_int_threshold` | ✓ SATISFIED |
| MAP-06 | Source files route to sub-folders by file type | 03-01, 03-04 | `test_classify_source_file_ext_routes_to_custom_folder`, `test_classify_file_hub_opted_in_by_rule` | ✓ SATISFIED |

**Orphaned requirements check:** `.planning/REQUIREMENTS.md` maps MAP-01..MAP-06 to Phase 3. All six appear in at least one plan's `requirements:` frontmatter field. Zero orphans.

**Traceability update note:** REQUIREMENTS.md still lists MAP-01..MAP-06 as "Pending". These should flip to "Complete" in the milestone audit — the orchestrator owns that update, not this verifier.

### Test Results

| Suite | Passing | Failing | Notes |
|-------|---------|---------|-------|
| `tests/test_mapping.py` | 45 | 0 | Target: 45 (plan 03-04 SUMMARY). Match. |
| `tests/test_profile.py` | 89 | 0 | Plan 03-03 SUMMARY claimed "129 passing across mapping+profile" (40 mapping + 89 profile = 129); this lines up. The prompt said "90+" but actual baseline was 81 and 8 new Phase 3 tests were added = 89. |
| `tests/test_templates.py` | 143 | 0 | No Phase 2 regressions. |
| `tests/ -q` (excluding pre-existing worktree-path failures) | 663 | 0 | `test_detect.py::test_detect_skips_dotfiles` and `test_extract.py::test_collect_files_from_dir` fail on worktree checkouts under `.claude/`; pre-date this phase and tracked in `deferred-items.md`. Not Phase 3 regressions. |

### Anti-Patterns Found

Phase 3 code was reviewed in `03-REVIEW.md` (0 critical, 3 warnings, 5 info). Review findings summary:

| File | Pattern | Severity | Impact |
|------|---------|----------|--------|
| `graphify/mapping.py::compile_rules` (WR-01) | Two independent `if` branches can both write to `_COMPILED_KEY` when both `attr+regex` and `source_file_matches` are present | Warning | Defense-in-depth; `validate_rules` rejects multi-matcher rules so `classify` is not reachable with this input via `load_profile`. Recommended: change second branch to `elif`. Non-blocking. |
| `graphify/mapping.py::_match_when` (WR-02) | `in` matcher accepts `set` (validate_rules restricts to list/tuple). Unhashable attr values with a set `choices` could raise `TypeError` | Warning | Same defense-in-depth: reachable only if a test bypasses validation. Recommended: narrow isinstance to `(list, tuple)` and wrap `in` check in try/except TypeError. Non-blocking. |
| `graphify/mapping.py::_is_shadowed` (WR-03) | `attr:?` short-kind documented only in a comment | Warning | Cosmetic. `validate_rules` rejects attr-without-op before `_detect_dead_rules` runs. Non-blocking. |
| `graphify/analyze.py::god_nodes` (IN-01) | `god_nodes(top_n=0)` returns 1 result instead of 0 (upstream bug: `len(result) >= top_n` check fires after append) | Info | Deferred — `analyze.py` is read-only per 03-CONTEXT. `validate_profile` accepts `top_n >= 0`; `test_classify_zero_god_nodes_no_crash` works around via fixture. Optional fix: reject `top_n < 1` in validate_profile. Non-blocking. |
| IN-02..IN-05 | Minor perf / refactor opportunities (recomputed community maps, list vs set for `above_cids` membership checks, etc.) | Info | None block goal achievement. |

**Per prompt instructions, review findings are non-blocking for verification.** They are tracked for optional cleanup in a later pass and do NOT constitute gaps.

### Human Verification Required

None. Phase 3 is a pure-function library with fully automated binary-success coverage. Every must-have has at least one pinned test; the Phase 2 ↔ Phase 3 contract boundary has three round-trip tests; the mapping rule grammar has a full validator test suite. No visual, real-time, or external-service behavior exists in Phase 3 to warrant human UAT.

---

## Gaps Summary

No gaps. All 5 must-haves verified by automated tests, all 6 requirements (MAP-01..MAP-06) satisfied, Phase 2 round-trip contract holds, and the full test suite is green. The phase is ready for Phase 5 wiring (`to_obsidian()` rewrite), which can now compose:

```python
from graphify import classify, render_note, render_moc
from graphify.cluster import score_all

cohesion = score_all(G, communities)
result = classify(G, communities, profile, cohesion=cohesion)
for node_id, ctx in result["per_node"].items():
    if ctx["note_type"] != "moc":
        filename, text = render_note(node_id, G, profile, ctx["note_type"], ctx, vault_dir=vault_dir)
for cid, moc_ctx in result["per_community"].items():
    if moc_ctx["note_type"] == "moc":
        filename, text = render_moc(cid, G, communities, profile, moc_ctx, vault_dir=vault_dir)
```

---

_Verified: 2026-04-11T11:15:00Z_
_Verifier: Claude (gsd-verifier)_
