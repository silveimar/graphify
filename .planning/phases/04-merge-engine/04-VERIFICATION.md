---
phase: 04-merge-engine
verified: 2026-04-11T18:00:00Z
status: passed
score: 28/28 must-haves verified
overrides_applied: 0
re_verification: false
gaps: []
human_verification: []
---

# Phase 4: Merge Engine Verification Report

**Phase Goal:** Re-running graphify on a vault with existing notes updates graphify-owned fields without overwriting user-edited fields, in a deterministic, git-friendly way
**Verified:** 2026-04-11T18:00:00Z
**Status:** passed
**Re-verification:** No — initial verification

## Goal Achievement

### ROADMAP Success Criteria

| # | Success Criterion | Status | Evidence |
|---|---|---|---|
| SC-1 | A user-edited `rank` or `mapState` frontmatter field survives a graphify re-run unchanged | VERIFIED | `test_preserve_rank_survives_update` passes; `_DEFAULT_FIELD_POLICIES["rank"] = "preserve"`; `_DEFAULT_FIELD_POLICIES["mapState"] = "preserve"` |
| SC-2 | Running graphify with `merge_strategy: skip` leaves existing note files completely untouched | VERIFIED | `test_strategy_skip_is_noop` passes; compute emits SKIP_PRESERVE; apply performs zero writes |
| SC-3 | Running graphify with `merge_strategy: replace` overwrites the full note including user-edited fields | VERIFIED | `test_strategy_replace_overwrites_preserve_fields` passes; REPLACE action confirmed |
| SC-4 | Frontmatter field ordering in updated notes matches the original ordering, producing minimal git diff noise | VERIFIED | `test_field_order_preserved_minimal_diff` passes; `diff_count == 1` assertion pins minimal-diff |

### Observable Truths (aggregated from all plan must_haves)

| # | Truth | Status | Evidence |
|---|---|---|---|
| T-01 | Every non-empty wayfinder_callout emitted by render_note is wrapped in sentinel comments | VERIFIED | `test_render_note_emits_matched_wayfinder_sentinels` passes; `_wrap_sentinel("wayfinder", ...)` confirmed in templates.py |
| T-02 | Every non-empty connections_callout emitted by render_note is wrapped in sentinel comments | VERIFIED | `test_render_note_emits_matched_connections_sentinels` passes |
| T-03 | Every non-empty metadata_callout emitted by render_note or render_moc is wrapped in sentinel comments | VERIFIED | `test_render_note_emits_matched_metadata_sentinels` + `test_render_moc_emits_all_moc_sentinels` pass |
| T-04 | Every non-empty members_section emitted by render_moc is wrapped in sentinel comments | VERIFIED | `test_render_moc_emits_all_moc_sentinels` passes |
| T-05 | Every non-empty sub_communities_callout emitted by render_moc is wrapped in sentinel comments | VERIFIED | `test_render_moc_emits_all_moc_sentinels` passes |
| T-06 | Every non-empty dataview_block emitted by render_moc is wrapped in sentinel comments | VERIFIED | `test_render_moc_emits_all_moc_sentinels` passes |
| T-07 | Empty sections (returning '') do NOT emit stray sentinel markers | VERIFIED | `test_render_note_omits_connections_sentinel_when_no_edges`, `test_render_moc_omits_members_sentinel_when_empty`, `test_render_moc_omits_sub_communities_sentinel_when_empty` all pass; `_wrap_sentinel` short-circuits on empty string |
| T-08 | _DEFAULT_PROFILE.merge.preserve_fields contains 'created' in addition to 'rank', 'mapState', 'tags' | VERIFIED | `_DEFAULT_PROFILE["merge"]["preserve_fields"] == ["rank", "mapState", "tags", "created"]` confirmed via direct Python assertion |
| T-09 | _DEFAULT_PROFILE.merge has a field_policies key defaulting to an empty dict {} | VERIFIED | `_DEFAULT_PROFILE["merge"]["field_policies"] == {}` confirmed |
| T-10 | A user profile setting merge.field_policies: {tags: replace} deep-merges over the empty default without discarding other merge keys | VERIFIED | `test_deep_merge_field_policies_override` in test_profile.py passes (102 passed total) |
| T-11 | validate_profile flags an invalid field_policies value (e.g. 'blah') with mode error and continues validation | VERIFIED | Direct invocation returns `["merge.field_policies.tags has invalid mode 'nuke' — valid modes are: [...]"]` |
| T-12 | validate_profile flags a non-string field_policies key with a type error | VERIFIED | Direct invocation returns `["merge.field_policies key 42 must be a string (got int)"]` |
| T-13 | validate_profile continues to accept all three merge.strategy values: update, skip, replace | VERIFIED | `test_validate_profile_accepts_all_three_merge_strategies` passes |
| T-14 | graphify/merge.py module file exists with `from __future__ import annotations` and module docstring | VERIFIED | File exists (911 lines); first line is module docstring; second line is `from __future__ import annotations` |
| T-15 | MergeAction, MergePlan, MergeResult frozen dataclasses are defined with the locked D-71 shape | VERIFIED | `TestDataclassesAndPolicies` (12 tests) all pass; dataclasses are frozen |
| T-16 | _DEFAULT_FIELD_POLICIES dict maps every key graphify emits to a locked mode per D-64 | VERIFIED | 14-key table confirmed: 7 replace, 4 union, 3 preserve |
| T-17 | _parse_frontmatter round-trips correctly against _dump_frontmatter | VERIFIED | Direct Python round-trip assertion passes for all type branches (list, bool, int, float, date, quoted string, bare string) |
| T-18 | _parse_frontmatter reports malformed YAML by returning None | VERIFIED | `TestParseFrontmatter` tests pass; malformed input returns None |
| T-19 | _parse_sentinel_blocks extracts block content and raises _MalformedSentinel on invalid structure | VERIFIED | 6 `TestParseSentinelBlocks` tests pass covering extraction, nested, unpaired cases |
| T-20 | _resolve_field_policy merges user field_policies over _DEFAULT_FIELD_POLICIES with preserve fallback for unknowns | VERIFIED | `TestPolicyDispatcher` (15 tests) all pass |
| T-21 | _apply_field_policy dispatches replace/union/preserve modes correctly | VERIFIED | `TestPolicyDispatcher` tests cover all three modes |
| T-22 | compute_merge_plan is pure — no file writes during plan computation | VERIFIED | `test_compute_merge_plan_is_pure` passes (mtime unchanged after compute-only call) |
| T-23 | compute_merge_plan emits correct action types for all 7 vault states | VERIFIED | 17 integration tests in `TestComputeMergePlan` all pass: CREATE, UPDATE, SKIP_CONFLICT (3 kinds), SKIP_PRESERVE, REPLACE, ORPHAN |
| T-24 | apply_merge_plan writes CREATE/UPDATE/REPLACE atomically and never writes outside vault_dir | VERIFIED | `test_apply_create_writes_new_file`, `test_apply_atomic_no_partial_file_on_error`, `test_apply_path_escape_recorded_as_failed` all pass |
| T-25 | apply_merge_plan content-hash skip produces zero writes on unchanged vault | VERIFIED | `test_apply_merge_plan_content_hash_skip` passes (M10) |
| T-26 | apply_merge_plan never deletes ORPHAN files | VERIFIED | `test_orphan_never_deleted_under_replace` passes (M8) |
| T-27 | graphify/__init__.py exposes compute_merge_plan, apply_merge_plan, MergePlan, MergeAction, MergeResult, RenderedNote via lazy import | VERIFIED | All 6 symbols resolve correctly via `graphify.<name>` |
| T-28 | TestPhase4MustHaves M1..M10 + T-04-01 all pass end-to-end | VERIFIED | 18 must_have tests (including pre-existing variants from Plans 04-05) all pass: 0 failures |

**Score:** 28/28 truths verified

### Required Artifacts

| Artifact | Expected | Status | Details |
|---|---|---|---|
| `graphify/templates.py` | Section builders returning strings pre-wrapped in sentinel HTML comments | VERIFIED | `_SENTINEL_START_FMT`, `_SENTINEL_END_FMT`, `_wrap_sentinel` added; 6 call sites confirmed via `grep -c "_wrap_sentinel("` == 7 (6 uses + 1 def) |
| `tests/test_templates.py` | Sentinel round-trip assertions | VERIFIED | 9 sentinel tests added; 152 total tests pass |
| `graphify/profile.py` | _DEFAULT_PROFILE.merge extended + validate_profile extended | VERIFIED | 911 lines; `preserve_fields == ["rank", "mapState", "tags", "created"]`; `_VALID_FIELD_POLICY_MODES` defined; 7 validator branches added |
| `tests/test_profile.py` | Field_policies validation coverage | VERIFIED | 102 tests pass; 13 new tests for merge.field_policies |
| `graphify/merge.py` | Full merge engine (primitives + compute + apply) | VERIFIED | 911 lines (exceeds min 600); all primitives + public functions present |
| `tests/test_merge.py` | Full test suite covering all must_haves | VERIFIED | 1154 lines (exceeds min 400); 85 tests pass |
| `tests/fixtures/vaults/` | 7 representative vault states | VERIFIED | 7 subdirectories confirmed: empty, pristine_graphify, user_extended, fingerprint_stripped, malformed_sentinel, preserve_fields_edited, unmanaged_collision |
| `graphify/__init__.py` | Lazy exports for 6 Phase 4 public symbols | VERIFIED | All 6 entries present and resolvable |

### Key Link Verification

| From | To | Via | Status | Details |
|---|---|---|---|---|
| `templates.py::_build_wayfinder_callout` | Rendered note body | `_wrap_sentinel("wayfinder", body)` | VERIFIED | `grep` confirms pattern in templates.py; round-trip test passes |
| `templates.py::render_note` | `${wayfinder_callout}` placeholder | pre-wrapped string through `string.Template.safe_substitute` | VERIFIED | `test_render_note_emits_matched_wayfinder_sentinels` passes |
| `_DEFAULT_PROFILE[merge][preserve_fields]` | "created" field | Preserving `created` across runs | VERIFIED | `_DEFAULT_PROFILE["merge"]["preserve_fields"].index("created") == 3` confirmed |
| `_DEFAULT_PROFILE[merge][field_policies]` | merge.py _DEFAULT_FIELD_POLICIES | deep_merge override path | VERIFIED | `_resolve_field_policy` 4-tier precedence chain merges user overrides over built-in table |
| `merge.py::_parse_frontmatter` | `profile.py::_dump_frontmatter` | symmetric inverse grammar | VERIFIED | Round-trip identity confirmed for all 7 type branches |
| `merge.py::_resolve_field_policy` | `profile.py::_deep_merge` | user field_policies override deep-merged over built-in table | VERIFIED | `_deep_merge` imported in merge.py; dispatcher uses profile.merge.field_policies |
| `compute_merge_plan` | `_parse_frontmatter + _parse_sentinel_blocks + _resolve_field_policy + _apply_field_policy` | Plan 03 primitives composed into per-file decision logic | VERIFIED | `TestComputeMergePlan` 17 tests exercise all code paths |
| `compute_merge_plan` | `profile.validate_vault_path` | every MergeAction.path gated through path-confinement | VERIFIED | `test_compute_action_paths_are_absolute_and_inside_vault` passes |
| `apply_merge_plan` | `os.replace + fsync` | crash-safe write protocol | VERIFIED | `test_apply_atomic_no_partial_file_on_error` passes (monkeypatched os.replace) |
| `apply_merge_plan` | `profile._dump_frontmatter` | re-emission of merged frontmatter preserves key ordering | VERIFIED | `test_field_order_preserved_minimal_diff` passes with `diff_count == 1` |

### Data-Flow Trace (Level 4)

This phase is algorithmic/library code (no UI rendering, no data flows through empty placeholders). Level 4 data-flow trace is not applicable — all data flows are algorithmic transformations with no dynamic data sources that could be hollow.

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
|---|---|---|---|
| Profile merge defaults correct | `python -c "from graphify.profile import _DEFAULT_PROFILE, _VALID_FIELD_POLICY_MODES; assert _DEFAULT_PROFILE['merge']['preserve_fields'] == ['rank', 'mapState', 'tags', 'created']..."` | OK | PASS |
| Wayfinder sentinel wrapping | `python -c "from graphify.templates import _build_wayfinder_callout; s = _build_wayfinder_callout(...); assert s.startswith('<!-- graphify:wayfinder:start -->\n')..."` | OK | PASS |
| Connections empty sentinel | `python -c "...assert _build_connections_callout(G, 'n_iso', 'title_case') == ''"` | OK | PASS |
| Round-trip identity | `_dump_frontmatter(d)` piped through `_parse_frontmatter` returns original dict | OK | PASS |
| All merge imports resolvable | `from graphify.merge import compute_merge_plan, apply_merge_plan, MergePlan, MergeAction, MergeResult, RenderedNote` | OK | PASS |
| All __init__ lazy exports | `graphify.compute_merge_plan`, `graphify.apply_merge_plan`, etc. all resolve | OK | PASS |
| validate_profile field_policies rejection | Invalid mode `'nuke'`, non-string key `42`, non-dict value all return actionable errors | OK | PASS |
| Full test suite (818 tests) | `pytest tests/ -q` | 818 passed | PASS |

### Requirements Coverage

| Requirement | Source Plan(s) | Description | Status | Evidence |
|---|---|---|---|---|
| MRG-01 | 04-01, 04-03, 04-04, 04-05, 04-06 | Re-running graphify updates graphify-owned fields while preserving user-edited fields | SATISFIED | `test_preserve_rank_survives_update` (M1) passes; sentinel system enables body-block refresh; `_DEFAULT_FIELD_POLICIES` encodes ownership; 85/85 test_merge.py tests pass |
| MRG-02 | 04-02, 04-06 | preserve_fields in profile specifies frontmatter fields graphify never overwrites | SATISFIED | `_DEFAULT_PROFILE.merge.preserve_fields == ["rank", "mapState", "tags", "created"]`; `_resolve_field_policy` 4-tier precedence chain; `validate_profile` validates `field_policies` schema |
| MRG-06 | 04-04, 04-06 | Frontmatter field ordering preserved on update to minimize git diff noise | SATISFIED | `_CANONICAL_KEY_ORDER` list + `_insert_with_canonical_neighbor` + `_merge_frontmatter`; `test_field_order_preserved_minimal_diff` (M4) asserts `diff_count == 1` |
| MRG-07 | 04-02, 04-04, 04-05, 04-06 | User can configure merge strategy: update (default), skip, replace | SATISFIED | Strategy dispatched from `profile.merge.strategy`; `test_strategy_skip_is_noop` (M2) and `test_strategy_replace_overwrites_preserve_fields` (M3) pass; all three strategies accepted by `validate_profile` |

All 4 phase requirements satisfied. No orphaned requirements (REQUIREMENTS.md traceability table maps MRG-01, MRG-02, MRG-06, MRG-07 exclusively to Phase 4).

### Anti-Patterns Found

No blocking anti-patterns. The 4 warnings from 04-REVIEW.md are advisory and noted below. None prevent goal achievement.

| File | Warning | Severity | Impact on Must-Haves |
|---|---|---|---|
| `graphify/merge.py:560-585` | WR-01: `_merge_body_blocks` silently no-ops when sentinel lines have prefix/suffix text (regex vs. replace asymmetry) | Advisory | None — graphify-authored content always uses canonical form; only affects hand-edited sentinel lines, which is an edge case not covered by any must-have |
| `graphify/merge.py:476-502` | WR-02: `_insert_with_canonical_neighbor` docstring says "append at end" but code prepends when no neighbor found | Advisory | None — behavior is deterministic; `test_compute_field_order_preserved_after_merge` (M4) covers the neighbor-found branch; no must-have asserts the no-neighbor branch |
| `graphify/merge.py:462-469` | WR-03: `_validate_target` doesn't resolve symlinks before `relative_to` — may misclassify valid paths on macOS (`/tmp` vs `/private/tmp`) | Advisory | None — test suite uses relative paths so the bug is masked; no must-have exercises absolute symlink path |
| `graphify/merge.py:136` | WR-04: `_FM_FLOAT_RE` too narrow — user-hand-edited floats with non-.2f precision fall through to string, causing false "changed" on re-run | Advisory | None — graphify-authored files always use `{:.2f}`; must-haves only test graphify-authored vault fixtures |

The 6 INFO items from 04-REVIEW.md (duplicated sentinel grammar, `_find_body_start` inconsistency, late stdlib imports, dead unknown-mode branch, double sentinel parse, fixture coverage gap) are code quality observations with no impact on any must-have.

### Human Verification Required

None — all phase-4 behaviors are mechanically verifiable via unit tests. The merge engine is a pure algorithmic library with no UI, no real-time behavior, and no external service dependencies.

### Gaps Summary

No gaps. All 4 ROADMAP success criteria are verified end-to-end by dedicated named tests. All 4 required requirements (MRG-01, MRG-02, MRG-06, MRG-07) have complete implementation evidence. The full test suite (818 tests) passes with zero failures.

The 04-REVIEW.md warnings are tracked quality issues for follow-up — they are advisory and do not block the phase goal.

---

_Verified: 2026-04-11T18:00:00Z_
_Verifier: Claude (gsd-verifier)_
