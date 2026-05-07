---
phase: 71-temp
plan: 05
subsystem: temporal
tags: [temporal, report, wiki, rendering, wave-3]
requires: [71-01, 71-02, 71-04]
provides:
  - "## Temporal Health" subsection in GRAPH_REPORT.md (D-10 minimal counts-only)
  - "## Historical relations" subsection in wiki community articles (D-11 omit-when-empty)
  - html.escape + 64-char cap on valid_until before rendering (T-71-15, T-71-19)
affects: [graphify/report.py, graphify/wiki.py, tests/test_report.py, tests/test_wiki.py]
tech_stack:
  added: []
  patterns:
    - end-of-report-counts-only-renderer
    - second-filtered-pass-omit-when-empty
    - html-escape-plus-length-cap-defense-in-depth
key_files:
  created: []
  modified:
    - graphify/report.py
    - graphify/wiki.py
    - tests/test_report.py
    - tests/test_wiki.py
decisions:
  - "D-10 honored: Temporal Health renders three lines (currently-valid count, superseded count, percent share). No histogram, no per-relation breakdown."
  - "D-11 honored: Historical relations heading is omitted entirely when no superseded edges incident to the community."
  - "T-71-15 mitigated: valid_until is html.escape'd before rendering — defense in depth even though build-time stamper controls the value."
  - "T-71-19 mitigated: valid_until is truncated to 64 chars after escaping — O(1) per-entry rendering cost regardless of input."
  - "T-71-20 mitigated: Temporal Health pct calculation guards `if total else 0.0` so empty graphs render cleanly."
metrics:
  tasks_completed: 2
  commits: 4
  tests_added: 10 (4 in test_report.py + 6 in test_wiki.py)
  duration_minutes: ~6
---

# Phase 71-05: Temporal Rendering — Report + Wiki Summary

Closes the rendering side of TEMP-04 by surfacing the temporal data that
Plans 71-01/71-02/71-04 stamped into the graph: a counts-only Temporal
Health subsection in GRAPH_REPORT.md (D-10) and a per-community
Historical relations list in wiki articles (D-11). Combined with Plan
71-04, Phase 71 is complete: TEMP-01..04 all delivered.

## What Shipped

### Task 1 — `graphify/report.py` Temporal Health subsection (lines 449–467)

End-of-`generate()` append, immediately before `return "\n".join(lines)`.
Three counts only per D-10:

```python
_temp_total = G.number_of_edges()
_temp_superseded = sum(
    1 for _, _, _d in G.edges(data=True) if _d.get("valid_until") is not None
)
_temp_current = _temp_total - _temp_superseded
_temp_pct = (_temp_superseded / _temp_total * 100.0) if _temp_total else 0.0
lines += [
    "",
    "## Temporal Health",
    "",
    f"- Currently valid edges: {_temp_current}",
    f"- Superseded edges: {_temp_superseded}",
    f"- Superseded share: {_temp_pct:.1f}%",
]
```

Empty-graph guard (`if _temp_total else 0.0`) closes T-71-20.

### Task 2 — `graphify/wiki.py` Historical relations (`_community_article`, lines ≈90–112)

Inserted just before the article footer. The existing current-edge rendering
pass (Relationships, Source Files, Audit Trail) is **unchanged** — Historical
relations is a strictly additive second pass over edges incident to the
community. Per-edge dedup via a `(min, max)` key prevents listing the same
edge twice when both endpoints are in the same community:

```python
import html  # added at module top

historical: list[tuple[str, str]] = []
seen: set[tuple[str, str]] = set()
for nid in nodes:
    for neighbor in G.neighbors(nid):
        ed = G.edges[nid, neighbor]
        vu = ed.get("valid_until")
        if vu is None:
            continue
        key = tuple(sorted((nid, neighbor)))
        if key in seen:
            continue
        seen.add(key)
        neighbor_label = G.nodes[neighbor].get("label", neighbor)
        historical.append((neighbor_label, str(vu)))
if historical:
    lines += ["## Historical relations", ""]
    for neighbor_label, vu in historical:
        vu_safe = html.escape(vu)[:64]
        lines.append(f"- [[{neighbor_label}]] (until {vu_safe})")
    lines.append("")
```

Heading omitted entirely when `historical` is empty per D-11.
`html.escape` + 64-char cap close T-71-15 / T-71-19 as defense in depth.

## Test Coverage

`pytest tests/test_report.py tests/test_wiki.py -x -q` → **75 passed**.

| File | New tests | Behaviors gated |
| --- | --- | --- |
| tests/test_report.py | 4 | D-10 render with mixed edges, zero-superseded, zero-total no-divide (T-71-20), placement after Summary |
| tests/test_wiki.py | 6 | D-11 present-when-nonempty, D-11 omit-when-empty, format `[[neighbor]] (until <vu>)`, T-71-15 html.escape, T-71-19 64-char cap, current-pass regression guard |

## Invariant Checks

```
$ grep -n 'Temporal Health' graphify/report.py | wc -l
2  (1 comment + 1 emitted heading)
$ grep -n 'Historical relations' graphify/wiki.py | wc -l
2  (1 comment + 1 emitted heading)
$ python -m pytest tests/test_report.py tests/test_wiki.py -x -q
75 passed
```

## TDD Gate Compliance

| Task | RED commit (test) | GREEN commit (feat) |
| --- | --- | --- |
| Task 1 | f735565 test(71-05): add failing tests for Temporal Health subsection in report | f65444d feat(71-05): render Temporal Health subsection in GRAPH_REPORT.md |
| Task 2 | e0990eb test(71-05): add failing tests for Historical relations in wiki community articles | 5248862 feat(71-05): render Historical relations in wiki community articles |

Both gates verified in git log; RED preceded GREEN; both RED commits failed
their target asserts before GREEN was implemented.

## Deviations from Plan

None — plan executed exactly as written. No Rule 1/2/3 fixes required.
No Rule 4 architectural decisions required. No auth gates encountered.

## Pre-Existing Failures (Out of Scope)

Same set documented in 71-01..71-04 (≈47 unrelated failures across
vault_*, audit_b_closure, capability, delta, enrich, explain_paths,
federate, harness_*, migration). Not touched.

## Phase 71 Status

TEMP-01..04 all delivered:

- TEMP-01 (foundation: temporal helpers, schema bump, validators) — Plan 71-01 ✅
- TEMP-02 (build-time stamping: valid_from + decay_weight on every new edge) — Plan 71-02 ✅
- TEMP-03 (supersession wiring + temporal-aware merge + export round-trip) — Plan 71-04 ✅
- TEMP-04 (rendering: Temporal Health + Historical relations) — Plan 71-05 ✅

## Self-Check: PASSED

- graphify/report.py — modified (Temporal Health renderer at end of `generate()`)
- graphify/wiki.py — modified (`html` import + Historical relations second pass in `_community_article`)
- tests/test_report.py — 4 new tests
- tests/test_wiki.py — 6 new tests
- Commits f735565, f65444d, e0990eb, 5248862 — ALL PRESENT in git log

`pytest tests/test_report.py tests/test_wiki.py -x -q` → **75 passed**.
