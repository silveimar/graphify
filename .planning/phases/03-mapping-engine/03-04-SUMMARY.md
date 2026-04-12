---
phase: 03-mapping-engine
plan: 04
subsystem: mapping-engine
tags: [package-surface, lazy-import, contract-test, phase-boundary]
requirements: [MAP-01, MAP-02, MAP-03, MAP-04, MAP-05, MAP-06]
dependency-graph:
  requires:
    - 03-01 (classify, MappingResult, compile_rules, _match_when)
    - 03-02 (community-level enrichment — community_name, cohesion, sub_communities)
    - 03-03 (validate_rules as final public API surface)
    - Phase 2 render_note / render_moc / _render_moc_like (D-41 signatures; WR-06 float cast; ctx.get('cohesion') consumption)
  provides:
    - graphify.classify as a top-level lazy export (was only accessible via graphify.mapping)
    - graphify.MappingResult and graphify.validate_rules as top-level lazy exports
    - Phase 3 ↔ Phase 2 contract tests — guardrails against ClassificationContext key drift
  affects:
    - Phase 5 to_obsidian() can now import classify directly from graphify
    - Any future edit to ClassificationContext keys on either side of the boundary
tech-stack:
  added: []
  patterns:
    - lazy-import map entry (three new tuples in graphify/__init__.py::__getattr__)
    - pure-function contract test over make_classification_fixture — no tmp_path, no I/O
key-files:
  created:
    - .planning/phases/03-mapping-engine/03-04-SUMMARY.md
  modified:
    - graphify/__init__.py (3 new lazy-map entries: classify, MappingResult, validate_rules)
    - tests/test_mapping.py (5 new tests: 2 lazy-export sanity + 3 round-trip contract)
decisions:
  - Lazy imports preserved — no top-level `from graphify.mapping import ...` added; the lazy pattern is load-bearing for `graphify install` before heavy deps (networkx, PyYAML) are available
  - Contract tests assert both "does not raise" AND content invariants (label, community_tag, sub_community collapse, cohesion plain-float) — a key-name rename on either side of the boundary fails loudly
  - cohesion float type is explicitly asserted via `isinstance(cohesion, float)` per WR-06 — prevents numpy.float64 regression
metrics:
  duration: ~7 minutes
  completed: 2026-04-11
  tasks: 2
  commits: 2
  files_modified: 2
  tests_added: 5
  tests_passing: 45/45 (tests/test_mapping.py) · 711/711 (full suite)
---

# Phase 3 Plan 04: Package Surface + Phase 2/3 Contract Summary

One-liner: Registered `classify`, `MappingResult`, and `validate_rules` as top-level lazy exports on `graphify/__init__.py` and closed the Phase 3 ↔ Phase 2 boundary with three round-trip contract tests that feed real `classify()` output through `render_note()` / `render_moc()` and assert label, community tag, sub-community collapse, and cohesion-float end-to-end.

## What shipped

### Task 1 — Lazy-export registration (`graphify/__init__.py`)

Added three entries to the `_map` dict inside `__getattr__` after the existing `render_community_overview` line:

```python
"classify": ("graphify.mapping", "classify"),
"MappingResult": ("graphify.mapping", "MappingResult"),
"validate_rules": ("graphify.mapping", "validate_rules"),
```

No top-level imports added — the lazy pattern is untouched, so `graphify install` still works before PyYAML / networkx are present. Verified by grep: `^from graphify.mapping` returns zero lines.

Sanity tests in `tests/test_mapping.py`:

- `test_graphify_package_lazy_exports_classify` (VALIDATION row 3-04-05 — W-4 fix): asserts `graphify.classify` and `graphify.validate_rules` are callable and `graphify.MappingResult` is accessible.
- `test_graphify_classify_is_graphify_mapping_classify` (T-3-13 mitigation): asserts `graphify.classify is graphify.mapping.classify` — a typo in the lazy-map tuple would produce an ImportError at first access.

Runtime smoke verified:
```
$ python -c "from graphify import classify, validate_rules, MappingResult; print(classify)"
<function classify at 0x108c1add0>
```

### Task 2 — Phase 3 ↔ Phase 2 round-trip contract tests (`tests/test_mapping.py`)

Three new tests that feed real `classify()` output through Phase 2's render functions using the `make_classification_fixture()` helper (pure function — no tmp_path, no network):

**`test_classify_output_round_trips_through_render_note`** (VALIDATION 3-04-01)

- Fixture: cid 0 (4 real + 2 synthetic, above threshold), cid 1 (2 real, below), cid 2 (1 isolate).
- `_profile()` uses `top_n=1` so `n_transformer` is the unique top god node → classified as `thing` via topology fallback.
- Pre-render assertions:
  - `result["per_node"]["n_transformer"]["note_type"] == "thing"`
  - `ctx["community_name"] == "Transformer"` (Plan 02 enrichment)
  - `ctx["parent_moc_label"] == "Transformer"`
  - `ctx["community_tag"] == safe_tag("Transformer")`
- `render_note()` call with `created=datetime.date(2024, 1, 1)` for determinism.
- Post-render assertions:
  - `filename.endswith(".md")`
  - rendered text contains the `"Transformer"` heading
  - rendered text contains `community/{safe_tag("Transformer")}` (templates.py:598 tag emission)

**`test_classify_output_round_trips_through_render_moc`** (VALIDATION 3-04-02 + 3-04-06)

- Same fixture; picks cid 0 (the only above-threshold community).
- Pre-render assertions:
  - `moc_ctx["note_type"] == "moc"`
  - `moc_ctx["community_name"] == "Transformer"`
- `render_moc()` with determinism date.
- Post-render assertions:
  - filename ends in `.md`, non-empty text
  - text contains community name `"Transformer"` and dataview fence `"```dataview"`
  - text contains `"AuthService"` — the top god node of cid 1, which collapses into cid 0's `sub_communities` via `_assemble_communities` nearest-host resolution
- **W-2 fix verification (VALIDATION row 3-04-06):**
  - Pick first real (non-bucket) MOC cid: `next(cid for cid, cctx in per_community if note_type == "moc" and cid >= 0)`
  - Assert `cohesion is not None` (must be populated so templates.py:705-706 renders a real value)
  - Assert `isinstance(cohesion, float)` (WR-06: plain Python float, not numpy.float64)

**`test_classify_output_round_trips_members_by_type_into_moc`**

- Tightens 3-04-02 beyond "doesn't raise" to "every member surfaces".
- Builds `expected_labels` = labels of every non-skipped member in `communities[0]`.
- Asserts each label appears in the rendered MOC text — catches any regression where `members_by_type` is silently under-populated.

## Test Coverage

```
$ pytest tests/test_mapping.py -q
.............................................                            [100%]
45 passed in 0.09s

$ pytest tests/ -q
...............................................................          [100%]
711 passed in 1.54s
```

Net new tests: 5 (2 Task 1 + 3 Task 2). test_mapping.py went from 40 → 45.

Full-suite verdict: 711/711 green. No Phase 1 or Phase 2 regressions. The two detect/extract worktree-path failures that were previously tracked in `deferred-items.md` are absent from this run — they resolve correctly on this worktree branch.

## VALIDATION.md rows closed by this plan

| Row | Test | Status |
|-----|------|--------|
| 3-04-01 | `test_classify_output_round_trips_through_render_note` | ✅ |
| 3-04-02 | `test_classify_output_round_trips_through_render_moc` | ✅ |
| 3-04-05 | `test_graphify_package_lazy_exports_classify` (W-4 fix) | ✅ |
| 3-04-06 | `test_classify_output_round_trips_through_render_moc` (cohesion float) | ✅ |

Rows 3-04-03 (`test_validate_profile_surfaces_mapping_rules_errors`) and 3-04-04 (`test_deep_merge_respects_topology_section`) were landed by Plan 03 under `tests/test_profile.py`. VALIDATION sign-off / frontmatter flip is the responsibility of `/gsd-verify-work` at the phase gate, not this executor.

## Deviations from Plan

None — plan executed exactly as written. No Rule 1/2/3 auto-fixes required; existing Plans 01–03 already populated every key the contract tests assert against (community_name, cohesion as plain float, sub_communities collapse, safe_tag emission). This plan was pure verification of the already-built surface, exactly as the planner intended ("the hardest verification of the Phase 2 ↔ Phase 3 boundary").

## Phase 5 handoff note

With Phase 3 done, Phase 5's `to_obsidian()` rewrite can be expressed as:

```python
from graphify import classify, render_note, render_moc
from graphify.cluster import score_all

def to_obsidian(G, communities, profile, vault_dir, **kwargs):
    cohesion = score_all(G, communities)
    result = classify(G, communities, profile, cohesion=cohesion)

    # Emit per-node notes (Thing/Statement/Person/Source)
    for node_id, ctx in result["per_node"].items():
        if ctx["note_type"] == "moc":
            continue
        filename, text = render_note(
            node_id, G, profile, ctx["note_type"], ctx, vault_dir=vault_dir
        )
        # write text to vault_dir / ctx["folder"] / filename

    # Emit per-community MOC notes
    for cid, moc_ctx in result["per_community"].items():
        if moc_ctx["note_type"] != "moc":
            continue
        filename, text = render_moc(
            cid, G, communities, profile, moc_ctx, vault_dir=vault_dir
        )
        # write text to vault_dir / moc_ctx["folder"] / filename
```

The contract tests added in this plan guarantee every `ctx` in `result["per_node"]` / `result["per_community"]` feeds the respective renderer without a key-name mismatch. Phase 5's work narrows to path resolution, merge-mode handling (MRG-01..MRG-05), and file I/O.

## Self-Check: PASSED

Files verified to exist on disk:
- `graphify/__init__.py` — modified (contains three new lazy-map entries)
- `tests/test_mapping.py` — modified (contains 5 new test functions)
- `.planning/phases/03-mapping-engine/03-04-SUMMARY.md` — created (this file)

Commits verified in git log:
- `a04fa5b` feat(03-04): register Phase 3 API in graphify lazy import map
- `0acdeb7` test(03-04): add Phase 3 <-> Phase 2 round-trip contract tests

Runtime verifications:
- `pytest tests/test_mapping.py -q` → 45 passed
- `pytest tests/ -q` → 711 passed
- `python -c "from graphify import classify, validate_rules, MappingResult"` → succeeds
