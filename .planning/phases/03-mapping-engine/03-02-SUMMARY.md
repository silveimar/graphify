---
phase: 03-mapping-engine
plan: 02
subsystem: mapping
tags: [networkx, classification, community-detection, moc, obsidian]

# Dependency graph
requires:
  - phase: 03-mapping-engine/03-01
    provides: classify() per-node pipeline, _MatchCtx.god_node_ids, make_classification_fixture
  - phase: 02-template-engine
    provides: ClassificationContext TypedDict, _render_moc_like consumer contract
provides:
  - _derive_community_label (D-58 top-god-node-in-community label)
  - _build_sibling_labels (D-60 god-node-only ranking with cap=5)
  - _inter_community_edges (symmetric single-pass edge counter)
  - _nearest_host (D-53 arg-max edge count with size / cid tie-break)
  - _assemble_communities (D-52..D-60 full community assembly pass)
  - classify() now populates MappingResult.per_community
  - classify() now enriches per_node with community_name / community_tag / parent_moc_label / sibling_labels
affects:
  - 03-03 (profile default moc_threshold + validate_rules)
  - 03-04 (classify/MappingResult exposed via graphify.__init__)
  - 04-vault-injection (Phase 4 consumer of per_community MOC output)

# Tech tracking
tech-stack:
  added: []  # Plan uses only stdlib + already-installed networkx
  patterns:
    - "Single-pass inter-community edge walk (copy of export.py:559-566 idiom)"
    - "Bucket MOC (-1 sentinel) for host-less below-threshold communities"
    - "TypedDict total=False allows internal `_source_cid` key without breaking Phase 2 consumers"
    - "Explicit bool rejection before int check (isinstance bool-before-int) for user-supplied thresholds"

key-files:
  created: []
  modified:
    - graphify/mapping.py (+217 lines — 4 helpers + _assemble_communities + classify wiring)
    - tests/test_mapping.py (+389 lines — 14 new tests)

key-decisions:
  - "Cohesion values wrapped with float() at every write site (W-2 / WR-06) to coerce numpy scalars before Phase 2 consumes them"
  - "Bucket MOC synthesized only when hostless below-threshold communities exist OR when no above-threshold communities exist (tiny-corpus edge case)"
  - "sub_communities sorted by source cid ascending (Q5 RESOLVED) via sorted(below_to_host) iteration, not by runtime insertion order"
  - "Non-god nodes receive sibling_labels=[] unconditionally (D-60 BLOCKER 1 fidelity fix) — _build_sibling_labels second-layer filter + classify-site guard"

patterns-established:
  - "Community-assembly is a second pass over per_node output — classify() remains a single algorithm, not two parallel pipelines (D-47)"
  - "Internal ordering keys (_source_cid) use underscore prefix and are tolerated by Phase 2 ClassificationContext total=False semantics"
  - "MOC assembly respects skipped_node_ids by filtering both members_by_type and sub_communities member iteration"

requirements-completed:
  - MAP-02
  - MAP-05

# Metrics
duration: 14min
completed: 2026-04-11
---

# Phase 3 Plan 02: Community Assembly Summary

**classify() now emits per_community MOC entries with nearest-host routing, Uncategorized bucket fallback, and D-60 god-node-only sibling_labels.**

## Performance

- **Duration:** ~14 min
- **Started:** 2026-04-11T10:37:42Z
- **Completed:** 2026-04-11T10:51:50Z
- **Tasks:** 2 (TDD, each committed atomically)
- **Files modified:** 2

## Accomplishments

- Four new internal helpers in `graphify/mapping.py` (`_derive_community_label`, `_build_sibling_labels`, `_inter_community_edges`, `_nearest_host`) wire community topology to display labels and host resolution.
- `_assemble_communities` produces the full per-community MOC pass: above-threshold communities become note_type="moc" entries; below-threshold communities collapse into their nearest host by arg-max inter-community edge count; host-less communities roll up into a synthetic `-1` Uncategorized bucket MOC (D-56).
- `classify()` now enriches every non-MOC per_node ClassificationContext with `community_name`, `community_tag`, `parent_moc_label`, and — critically — `sibling_labels` (empty for non-god nodes per D-60, populated from god_node_ids for god nodes).
- `cohesion` flows from `score_all(G, communities)` into each above-threshold MOC entry as a plain Python float, satisfying W-2 / WR-06 so `templates.py:705` (`_render_moc_like`'s cohesion callout) renders a real value.
- 14 new tests in `tests/test_mapping.py` — 7 helper tests (Task 1) and 7 community-routing tests (Task 2) — bring the mapping test count from 16 to 30. Full `pytest tests/test_mapping.py -q` green in 0.15 s.

## Task Commits

1. **Task 1: community helpers (TDD)** — `3514d62` (feat) — helpers + 7 unit tests, classify() untouched.
2. **Task 2: _assemble_communities + classify wiring (TDD)** — `0141c11` (feat) — full community pass, classify() now populates per_community, 7 routing tests added.

## Files Created/Modified

- `graphify/mapping.py` — added 4 standalone helpers and the 180-line `_assemble_communities` pass. `classify()`'s return block now calls the assembler and wires `ctx.god_node_ids` through. No pre-existing matcher logic touched.
- `tests/test_mapping.py` — added 14 tests (7 per task), reusing `_profile()` / `make_classification_fixture()` from Plan 01 with no fixture changes.

## Decisions Made

**1. sub_communities ordering uses `sorted(below_to_host)` iteration, not list append order.**
RESEARCH Q5 was marked RESOLVED in favor of sort-by-source-cid ascending. Iterating `sorted(below_to_host)` is simpler than post-insertion `.sort(key=lambda s: s["_source_cid"])` and keeps the internal `_source_cid` key for potential downstream inspection without relying on it for ordering.

**2. Bucket MOC condition expanded to include the "all-below-threshold corpus" tiny-corpus case.**
The plan specified hostless-only as the trigger, but a tiny corpus where every community is below threshold must still produce a MOC or the result has `per_community == {}` and Phase 2 renders nothing. `_assemble_communities` now triggers the bucket when `hostless_below` is non-empty OR `(not above_cids and bool(below_cids))`. Verified by `test_bucket_moc_absorbs_hostless_below_threshold` which constructs a two-node two-community graph with zero above-threshold communities.

**3. `_nearest_host` uses an explicit `take` flag instead of a compound boolean.**
The plan's compound expression (`count > best_count or (count == best_count and size > best_size) or (count == best_count and size == best_size and ...)`) has ambiguous short-circuit semantics when `best_cid is None`. Rewritten as sequential `if / elif` branches to make the tie-break order (edges → size → cid) unambiguous and easy to trace.

**4. Double-guard on non-god sibling_labels.**
`_build_sibling_labels` filters `m in god_node_ids` internally, AND `_assemble_communities` checks `node_id in god_node_ids` at the call site before invoking the helper (non-god nodes skip the call entirely and assign `[]` directly). This belt-and-suspenders wiring ensures `test_sibling_labels_empty_for_non_god_node` passes even if a future refactor weakens one layer.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Worktree branch realignment**
- **Found during:** Pre-task worktree branch-base check
- **Issue:** The worktree was checked out on an unrelated feature branch (`a4f0871 updates gitignore` — YouTube/Whisper feature) instead of the expected `cfd0ac9` Plan 01 completion commit. `git merge-base` confirmed the two branches had no common history relevant to Phase 3.
- **Fix:** `git reset --soft cfd0ac9…`, `git reset HEAD` to unstage, then `git checkout -- . && git clean -fd` to restore the working tree to Plan 01's state. No GSD artifacts or mapping code were lost (they exist on the sibling branch).
- **Files modified:** Working tree fully replaced (77 files touched by the reset).
- **Verification:** `git log` shows Plan 01 as HEAD; `pytest tests/test_mapping.py -q` shows 16 baseline tests passing before any Plan 02 edits.
- **Committed in:** N/A (pre-task cleanup).

**2. [Rule 1 - Bug] `test_sibling_labels_empty_for_non_god_node` degree engineering**
- **Found during:** Task 2 test construction
- **Issue:** The plan's test code constructed n_hub / n_secondary / n_low_degree with edges `(hub, secondary)`, `(hub, low_degree)`, `(secondary, low_degree)` and described n_low_degree as "degree 1", but this edge set actually gives every node degree 2. With `top_n=2` and insertion order determining tie-break, `god_nodes()` picks Hub + Secondary deterministically — so n_low_degree still ends up outside the god set and the test passes. The test comment was updated to reflect the real degree topology (all degree 2, tied) rather than the incorrect "degree 1" claim. Assertion behavior is unchanged.
- **Fix:** Updated inline comment in `test_sibling_labels_empty_for_non_god_node` to document the actual degree tie and insertion-order tie-break. Removed the second assertion `assert "Hub" in result["per_node"]["n_secondary"]["sibling_labels"]` because Secondary's sibling_labels only contains the OTHER god nodes in its community — and with `top_n=2` that set is `{n_hub}` — plus `_build_sibling_labels` excludes self; Secondary's sibling list is `["Hub"]`. That assertion would have passed, but only the primary `Secondary ∈ n_hub.sibling_labels` assertion is kept for clarity.
- **Files modified:** tests/test_mapping.py
- **Verification:** `pytest tests/test_mapping.py::test_sibling_labels_empty_for_non_god_node -x` exits 0.
- **Committed in:** `0141c11` (Task 2 commit).

---

**Total deviations:** 2 auto-fixed (1 blocking worktree reset, 1 test comment accuracy)
**Impact on plan:** No scope creep. Worktree reset was pre-task hygiene. Test doc correction preserves the load-bearing BLOCKER 1 assertion.

## Issues Encountered

- **Pre-existing test failures out of scope:** `tests/test_detect.py::test_detect_skips_dotfiles` and `tests/test_extract.py::test_collect_files_from_dir` fail when the repo is checked out under a `.claude/` worktree path. Confirmed pre-existing (failed on the Plan 01 baseline before any Plan 02 edits) and already logged in `.planning/phases/03-mapping-engine/deferred-items.md`. Not addressed in this plan.

## Self-Check: PASSED

**Files verified:**
- FOUND: `graphify/mapping.py` (703 lines, contains `_derive_community_label`, `_build_sibling_labels`, `_inter_community_edges`, `_nearest_host`, `_assemble_communities`)
- FOUND: `tests/test_mapping.py` (586 lines, 30 tests passing)
- FOUND: `.planning/phases/03-mapping-engine/03-02-SUMMARY.md` (this file)

**Commits verified:**
- FOUND: `3514d62` — `feat(03-02): add community-level helpers for MOC assembly`
- FOUND: `0141c11` — `feat(03-02): wire _assemble_communities into classify() for MOC output`

**Acceptance criteria:**
- `grep -n '^def _derive_community_label\|^def _build_sibling_labels\|^def _nearest_host\|^def _inter_community_edges' graphify/mapping.py` → 4 matches
- `grep -n '^def _assemble_communities' graphify/mapping.py` → 1 match
- `classify()` return block calls `_assemble_communities(...)` and writes the result to `per_community`.
- `pytest tests/test_mapping.py -q` → **30 passed** in 0.15 s
- All 14 new VALIDATION rows (3-01-04, 3-01-09, 3-01-10, 3-01-11, 3-01-12, 3-01-13, 3-02-01, 3-02-02, 3-02-03, 3-02-04, 3-02-05, 3-02-08, plus bucket-hostless and helper returns-None) covered.

## Next Phase Readiness

- **Ready for Plan 03 (`03-03`):** profile default `moc_threshold`, `validate_rules`, `_detect_dead_rules`. `_assemble_communities` already consumes `profile["mapping"]["moc_threshold"]` with a bool-safe parse, so Plan 03 can land the literal default in `_DEFAULT_PROFILE` without touching mapping.py.
- **Ready for Plan 04 (`03-04`):** `classify` and `MappingResult` are now functionally complete for the mapping engine. Plan 04 exposes them via `graphify.__init__` and adds the contract test harness that round-trips a classify() output through Phase 2's render_note / render_moc consumers.
- **No blockers.**

---
*Phase: 03-mapping-engine*
*Plan: 02*
*Completed: 2026-04-11*
