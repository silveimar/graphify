---
phase: 66-cfed-cross-repo-concept-federation-federate-py
plan: 04
subsystem: report
tags: [federation, report, graph-report-md, omit-on-zero, tdd, cfed]
requires:
  - graphify/federate.py::write_manifest (D-66.5 schema)
  - graphify/report.py::generate
provides:
  - graphify/report.py::generate (federation_manifest=...) renders `## Federation`
affects:
  - graphify/report.py
tech_stack:
  added: []
  patterns: [omit-on-zero, optional-kwarg-rendering, table-from-json-schema]
key_files:
  created: []
  modified:
    - graphify/report.py
    - tests/test_federate.py
decisions: [D-66.5, D-66.6]
metrics:
  duration: ~6m
  tasks: 2
  tests_added: 3
  date: 2026-05-06
requirements: [CFED-05]
---

# Phase 66 Plan 04: GRAPH_REPORT.md Federation section — Summary

Renders the Federation section in `GRAPH_REPORT.md` from
`federation-manifest.json` (D-66.5 schema), positioned immediately after the
Communities block per D-66.6, with strict omit-on-zero behavior.

## Tasks Completed

| Task | Name                                                | Commit  |
| ---- | --------------------------------------------------- | ------- |
| 1    | RED — Federation section render tests (3 new)       | 4a799a2 |
| 2    | GREEN — wire `federation_manifest` kwarg + renderer | 09c13f9 |

## Behaviors Locked by Tests

- **`test_report_renders_section`** — passing a 2-entry manifest produces:
  - `## Federation` heading present and positioned after `## Communities`.
  - Table header line exactly matches D-66.6:
    `| Merged Concept | Repos | Jaccard | Shared Basenames | Tiebreaker |`.
  - Jaccard rendered with two-decimal formatting (`0.67`).
  - Tiebreaker rendered with two-decimal formatting (`0.82`) when present;
    cell is empty (`""` after strip) when `tiebreaker_score` absent.
- **`test_report_omits_on_zero`** — empty manifest (`[]`) → output contains
  no `## Federation` substring (omit-on-zero per D-66.6, mirrors Phase 67
  CDRIFT "absent ⇒ omit" convention noted in the ROADMAP).
- **`test_report_section_placement`** — strict order in rendered markdown:
  `Calibration < Communities < Federation`. Calibration position unchanged.

## Public API

```python
from graphify.report import generate

# Default (federation off — backward compatible, no `## Federation` emitted)
md = generate(G, communities, cohesion, labels, gods, surprises,
              detection, tokens, root)

# Federation rendering (Plan 04)
md = generate(G, communities, cohesion, labels, gods, surprises,
              detection, tokens, root,
              federation_manifest=entries)  # list[dict] per D-66.5 schema
```

The new kwarg is keyword-only by virtue of position after the existing
`dedup_report` and `usage_data` kwargs. All existing callers continue to
work unchanged — confirmed by the full-suite green (only the documented
pre-existing migration failure remains).

## Implementation (graphify/report.py)

```python
# --- Phase 66 (CFED-05) Federation section ---
# Placement per D-66.6: immediately AFTER the Communities block.
# Omit-on-zero policy: when manifest is empty/None, no `## Federation`
# heading is emitted.
if federation_manifest:
    lines += ["", "## Federation"]
    lines.append("| Merged Concept | Repos | Jaccard | Shared Basenames | Tiebreaker |")
    lines.append("|---|---|---|---|---|")
    for entry in federation_manifest:
        repos = ", ".join(c.get("repo", "") for c in entry.get("contributing", []))
        sigs = entry.get("signals", {}) or {}
        jacc = f"{float(sigs.get('neighborhood_jaccard', 0.0)):.2f}"
        basenames = ", ".join(sigs.get("shared_basenames", []) or [])
        tb = (
            f"{float(entry['tiebreaker_score']):.2f}"
            if "tiebreaker_score" in entry else ""
        )
        lines.append(
            f"| {entry.get('merged_id', '')} | {repos} | {jacc} | {basenames} | {tb} |"
        )
```

Inserted between the Communities `for cid, nodes in communities.items():`
loop and the `ambiguous = ...` block — preserves Calibration (above
Communities) and downstream sections (Knowledge Gaps, Suggested Questions,
Usage Patterns, Entity Dedup) unchanged.

## Verification

- `pytest tests/test_federate.py -x -k report` → **3 passed**
- `pytest tests/test_federate.py tests/test_report_calibration.py -q` → **27 passed**
- `pytest tests/ -q` → **2342 passed**, 1 xfailed, 1 pre-existing failure
  (`tests/test_migration.py::test_preview_expands_risky_action_rows` —
  documented out of scope per Plan 02 SUMMARY).
- `grep -n "## Federation" graphify/report.py` → matches at L275 ✓
- `awk '/## Communities/{c=NR} /## Federation/{f=NR} END{exit !(c<f)}' graphify/report.py` → exit 0 ✓
- `grep -c "Merged Concept | Repos | Jaccard | Shared Basenames | Tiebreaker" graphify/report.py` → 1 ✓

## Deviations from Plan

**[Rule 1 — Test fixture bug]** The plan-supplied `_report_aux()` originally
returned `{0: ["a", "b"]}` for communities, but the existing Communities
rendering loop (`graphify/report.py` L253-266) calls `G.nodes[n]` for every
node listed. The test graph built by `_build_graph_with_inferred_scores_local`
has node ids `code_0..code_9` and `concept_0..concept_9` — never `"a"` or
`"b"` — so the loop raised `KeyError: 'a'` before reaching the new
Federation block. Fixed by changing the helper to return
`{0: ["code_0", "concept_0"]}`. This is a test-fixture-only correction; no
production code or behavior was altered to satisfy a test.

No other deviations. CONTEXT D-66.6 placement (after Communities, Calibration
unchanged) was honored exactly — line-order grep proves it in the source.

## Cross-Plan Handoff

Plan 04 closes the CFED phase rendering surface:
- `report.generate(..., federation_manifest=entries)` is the integration
  hook. The caller responsible for sourcing `entries` from
  `default_graphify_artifacts_dir(...)/federation-manifest.json` (written by
  Plan 02's `write_manifest`) must thread the list through. Skill / build
  orchestration plumbing for that read-back is intentionally out of scope
  for Plan 04 — it is a one-line `json.load` at the call site, and the
  manifest path is already stable from Plan 02.

## Self-Check: PASSED

- `graphify/report.py` (modified — Federation block at L269-289) — FOUND
- `tests/test_federate.py` (3 new tests appended) — FOUND
- Commit 4a799a2 (RED) — FOUND
- Commit 09c13f9 (GREEN) — FOUND

## TDD Gate Compliance

- **RED gate:** `test(66-04): add failing tests for GRAPH_REPORT Federation section` (4a799a2) — confirmed RED via `TypeError: generate() got an unexpected keyword argument 'federation_manifest'` before implementation.
- **GREEN gate:** `feat(66-04): render Federation section in GRAPH_REPORT.md after Communities` (09c13f9) — all 3 new tests pass; full federate + calibration scope (27/27) green; full suite 2342 passed.
- **REFACTOR gate:** not needed; renderer landed clean; only a test-fixture bug surfaced and was fixed under Rule 1.
