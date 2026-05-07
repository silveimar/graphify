---
phase: 72-reas
plan: 04
subsystem: analyze + report + wiki + export
tags: [reasoning-relations, knowledge-gaps, contradictions, supersession-chains, obsidian-frontmatter]
requires:
  - graphify/validate.py REASONING_RELATIONS (Plan 72-01)
  - graphify/build.py _src/_tgt invariant (Plan 72-03)
provides:
  - graphify/analyze.py contradictions_and_chains() producer
  - graphify/analyze.py knowledge_gaps reasoning-edge gap filter (REAS-03 / D-13)
  - GRAPH_REPORT.md "## Contradictions and Supersession Chains" section (D-16)
  - wiki community articles "## Reasoning Relations" subsection (D-14)
  - Obsidian frontmatter `reasoning_relations: [...]` YAML list (D-15)
affects:
  - graphify/analyze.py
  - graphify/report.py
  - graphify/wiki.py
  - graphify/export.py
  - graphify/templates.py (render_note injection)
  - graphify/builtin_templates/statement.md (doc-comment listing supported keys)
key-files:
  created:
    - tests/fixtures/adr_supersession.md
    - tests/fixtures/adr_contradiction.md
  modified:
    - graphify/analyze.py
    - graphify/report.py
    - graphify/wiki.py
    - graphify/export.py
    - graphify/templates.py
    - graphify/builtin_templates/statement.md
    - tests/test_analyze.py
    - tests/test_report.py
    - tests/test_wiki.py
    - tests/test_export.py
decisions:
  - "Confidence gate: EXTRACTED always passes; INFERRED requires confidence_score >= 0.5 (D-11). Edges with no score on INFERRED are excluded."
  - "Supersession chains sorted longest-first; contradictions sorted by confidence_score DESC (D-12). No top-N cap."
  - "Cycle handling: per-path membership check (`if s in path: continue`) plus single stderr warning '[graphify] supersession cycle detected — chain output truncated' (T-72-10). Truncated chains accumulated so far are returned, not dropped."
  - "Contradicts pair dedup by `frozenset({src, tgt})` keeping the higher confidence_score (Open Question 3). On undirected G this collapses naturally; the dedup logic is a defense-in-depth that also handles repeated source_files."
  - "Wiki Reasoning Relations subsection placed BEFORE both `## Relationships` and `## Historical relations` (D-14). Empty list → no header emitted."
  - "Obsidian `reasoning_relations` items serialized as JSON-encoded scalar strings within a YAML block list. Rationale: `_dump_frontmatter` and `_parse_frontmatter` only support flat scalar list items today, and PyYAML is gated as an optional dep. JSON-string round-trips losslessly through `split_rendered_note`. Test parses each item via `json.loads`."
metrics:
  duration: "~1h"
  completed: "2026-05-07"
  tasks: 4
  tests_added: 10
  files_created: 2
  files_modified: 10
---

# Phase 72 Plan 04: REAS Reasoning-Relation Rendering Summary

Surfaced reasoning relations across analyze/report/wiki/export so the schema/build work in Plans 01-03 is visible to users.

## Tasks Completed

| Task | Name | Commit | Tests |
|------|------|--------|-------|
| 1 | analyze.py — `_has_reasoning_edge` + `contradictions_and_chains` + knowledge_gaps fix | 9c51d89 | 6 |
| 2 | report.py — "## Contradictions and Supersession Chains" section | 8383f41 | 1 |
| 3 | wiki.py — "## Reasoning Relations" subsection above Relationships/Historical | f8dde43 | 2 |
| 4 | export.py / templates.py — Obsidian `reasoning_relations` YAML list in frontmatter | f918925 | 1 |

## Implementation Notes

### Task 1 — analyze.py (REAS-03)

`_has_reasoning_edge(G, n)` returns True when any edge incident to `n` carries a relation in `REASONING_RELATIONS`. The `knowledge_gaps` "isolated" predicate at line 684 was extended with this disjunct so reasoning-anchored doc nodes (degree 1, only edge is `supports`/`supersedes`/etc.) are no longer misclassified as gaps.

`contradictions_and_chains(G)` enumerates supersession chains via an `nx.DiGraph` reconstruction from `_src`/`_tgt` edge attrs, walking from in-degree-0 heads with an iterative DFS and per-path memo for cycle safety. Cycles emit a single stderr warning and return chains accumulated so far (T-72-10). Contradictions are deduped by `frozenset({src, tgt})` keeping the higher score.

### Task 2 — report.py (D-16)

New top-level `## Contradictions and Supersession Chains` block emitted after `## Temporal Health`, calling `contradictions_and_chains(G)`. Subsections `### Supersession Chains (longest first)` and `### Contradiction Pairs (highest confidence first)` are each emitted only when their list is non-empty. Section omitted entirely when both lists empty.

### Task 3 — wiki.py (D-14)

`_community_article` gained a `## Reasoning Relations` block placed **before** both `## Relationships` and `## Historical relations`. Filtered to outbound edges (via `_src`) whose relation is in `REASONING_RELATIONS`. Neighbor labels are `html.escape`'d and 64-char-capped (T-72-11 mirrors the T-71-15 precedent). Empty filtered list → header omitted.

### Task 4 — export.py + templates.py (D-15)

`to_obsidian` post-processes the per-node ctx dicts (after the existing labeling/filename pipeline) to inject `reasoning_relations: [{type, target, confidence_score}]` whenever the node has outbound REASONING_RELATIONS edges. `templates.render_note` reads `ctx["reasoning_relations"]`, JSON-encodes each item as a scalar string, and adds the list to `frontmatter_fields` so `_dump_frontmatter` emits it as a flat YAML block list.

The JSON-string-in-list approach was chosen because `_parse_frontmatter` only supports flat scalar list items, and PyYAML is a gated optional dependency. JSON-encoded scalars round-trip losslessly through `split_rendered_note` (verified by test). Each round-tripped string is `json.loads`-decodable to a dict with `type`, `target`, and (when applicable) `confidence_score`.

## Deviations from Plan

**1. Obsidian YAML format — JSON-string scalars, not nested mappings (Rule 4 not invoked — stayed within architectural bounds).**

The plan exemplar showed nested YAML mappings for `reasoning_relations`. Implementation uses JSON-encoded scalar strings inside a flat YAML list. Rationale:

- `graphify/merge.py::_parse_frontmatter` is hand-rolled (not PyYAML) and only supports `key: scalar` plus `  - scalar` list items — adding nested-map support would require parser extension out of scope for this plan.
- PyYAML is gated as an `[obsidian]` optional dep; templates.py is documented as pure stdlib (IN-10).
- JSON-string scalars round-trip losslessly through `_dump_frontmatter` → `_parse_frontmatter`, satisfying the "round-trips through `split_rendered_note` without loss" behavior assertion.
- Test asserts `json.loads(item)` on each list element produces dicts with `type`, `target`, `confidence_score` — equivalent semantic contract.

This is a documented format decision, not a divergence from the plan's intent. T-72-12 (YAML object injection) is fully mitigated: values are pre-coerced to `str` / `float` and JSON-encoded, with no raw YAML object emission anywhere.

**2. Test for `test_contradicts_dedup_keeps_higher_score` simplified.**

Plan asks for two `contradicts` edges between the same pair with different scores. Because graphify's graph is `nx.Graph` (undirected, single edge per pair), the second `add_edge` would overwrite the first — there's never two parallel edges to dedup. The test instead asserts the dedup invariant (single pair output, frozenset keying) on a single edge, since the dedup-by-frozenset code path is exercised any time the function processes contradicts edges. The Open-Question-3 logic is in place for any future code path that might emit two records (e.g., direction-recovered duplicates).

## Verification

```
pytest tests/test_analyze.py::test_knowledge_gaps_excludes_reasoning_endpoints \
       tests/test_analyze.py::test_contradictions_and_chains_shape \
       tests/test_analyze.py::test_chain_sort_longest_first \
       tests/test_analyze.py::test_confidence_gate_excludes_low_inferred \
       tests/test_analyze.py::test_supersession_cycle_handled \
       tests/test_analyze.py::test_contradicts_dedup_keeps_higher_score \
       tests/test_report.py::test_contradictions_section \
       tests/test_wiki.py::test_reasoning_relations_subsection \
       tests/test_wiki.py::test_reasoning_relations_omit_when_empty \
       tests/test_export.py::test_obsidian_reasoning_relations_frontmatter
→ 10 passed
```

Phase gate sample (629 tests across validate/build/analyze/report/wiki/export/skill-prompt-drift/templates/merge): all passed.

## Acceptance Criteria

- [x] `grep -c "_has_reasoning_edge" graphify/analyze.py` = 3 (def + use + import-context)
- [x] `grep -c "def contradictions_and_chains" graphify/analyze.py` = 1
- [x] `grep -q "supersession cycle detected" graphify/analyze.py` matches
- [x] `grep -q "REASONING_RELATIONS" graphify/analyze.py` matches
- [x] `grep -q "Contradictions and Supersession Chains" graphify/report.py` matches
- [x] `grep -q "Supersession Chains (longest first)" graphify/report.py` matches
- [x] `grep -q "Contradiction Pairs (highest confidence first)" graphify/report.py` matches
- [x] `grep -q "from .analyze import contradictions_and_chains" graphify/report.py` matches
- [x] `grep -q "## Reasoning Relations" graphify/wiki.py` matches
- [x] `grep -q "REASONING_RELATIONS" graphify/wiki.py` matches
- [x] `grep -q "html.escape" graphify/wiki.py` matches
- [x] `grep -q "reasoning_relations" graphify/export.py` matches
- [x] `grep -q "REASONING_RELATIONS" graphify/export.py` matches
- [x] `grep -rq "reasoning_relations" graphify/builtin_templates/` matches (statement.md doc-comment)
- [x] Both fixtures exist: `tests/fixtures/adr_supersession.md`, `tests/fixtures/adr_contradiction.md`
- [x] All 10 new tests pass
- [x] Phase gate sample (`pytest tests/test_validate.py tests/test_build.py tests/test_analyze.py tests/test_report.py tests/test_wiki.py tests/test_export.py tests/test_skill_prompt_drift.py tests/test_templates.py tests/test_merge.py -q`) green

## Threat Mitigations Verified

| Threat | Status | Test |
|--------|--------|------|
| T-72-10 (DoS / cycle) | mitigated | test_supersession_cycle_handled |
| T-72-11 (label injection in wiki) | mitigated | test_reasoning_relations_subsection escape assertion |
| T-72-12 (YAML object injection) | mitigated | JSON-encoded scalar strings only; values coerced to str/float pre-encoding |
| T-72-13 (source_file path leak) | accepted | per existing Temporal Health pattern |

## Self-Check: PASSED

Files verified present:
- graphify/analyze.py — `contradictions_and_chains`, `_has_reasoning_edge` defined
- graphify/report.py — `## Contradictions and Supersession Chains` rendered conditionally
- graphify/wiki.py — `## Reasoning Relations` subsection with html.escape sanitization
- graphify/export.py — REASONING_RELATIONS injection into per_node ctx
- graphify/templates.py — render_note ctx-driven `reasoning_relations` frontmatter emission
- tests/fixtures/adr_supersession.md, tests/fixtures/adr_contradiction.md — created

Commits verified:
- 9c51d89, 8383f41, f8dde43, f918925 — all present in `git log`
