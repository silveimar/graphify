# Phase 53: Concept↔code schema & build merge - Context

**Gathered:** 2026-04-30
**Status:** Ready for planning

<domain>
## Phase Boundary

Promote concept↔implementation relationships to first-class, validated graph edges. Extend the v1.10 Phase 46 foundation (`implements` + `_normalize_concept_code_edges`) by:

1. Adding four new typed concept↔code relations to the validated vocabulary in `validate.py`
2. Hardening the build/merge path so concept↔code edges are deterministic and round-trip stable

In scope: schema (`validate.py`), merge logic (`build.py::_normalize_concept_code_edges` + `_merge_edge_fields`), `docs/RELATIONS.md`, fixture-backed tests proving stability.

Out of scope (deferred to later v1.11 phases): MCP traversal of new relations (Phase 54), `/trace` plumbing (Phase 54), Obsidian export parity for new relations (Phase 54), template changes (Phase 55), profile overrides (Phase 56).

</domain>

<decisions>
## Implementation Decisions

### New relation vocabulary (CGRAPH-01)
- **D-53.01:** Add four new concept↔code relations to `validate.py`'s `KNOWN_RELATIONS`:
  - `documents` — code/doc artifact (docstring, comment, README) cites a concept. Direction: doc → concept.
  - `tests` — test artifact asserts behavior of a concept. Direction: test → concept.
  - `realizes` — interface/abstract type realizes a concept. Direction: code → concept.
  - `instantiates` — concrete subtype instantiates a concept. Direction: code → concept.
- **D-53.02:** Existing `implements` is hardened (not replaced). All five concept↔code relations are oriented code → concept canonically.
- **D-53.03:** `docs/RELATIONS.md` is updated with the four new entries; `warn_unknown_relations` will not warn for these once added to `KNOWN_RELATIONS`.

### Stable ID strategy (CGRAPH-02)
- **D-53.04:** Edge dedupe key remains `(source, target, relation)` — no content-hash field added to the edge schema. (Avoids invasive change to MCP/export/telemetry.)
- **D-53.05:** On merge in `_merge_edge_fields`, **canonicalize**:
  - `source_files`: lexicographically sorted, deduplicated
  - `confidence_score`: take `max()` (highest signal wins)
  - `source_location`: take lexicographically lowest (deterministic, stable across re-runs)
  - `confidence`: keep highest tier (EXTRACTED > INFERRED > AMBIGUOUS)
- **D-53.06:** After all dedupe passes (directed merge + opposite-direction `implements` collapse), apply a **canonical sort** to the final edge list: `(source, target, relation)` tuple ascending. Applies to all relations (concept↔code AND structural), not just the new four.

### Confidence rules for new relations (CGRAPH-01)
- **D-53.07:** New relations default to `INFERRED` and require a `confidence_score ∈ [0.0, 1.0]` field. `validate.py` rejects new-relation edges with `EXTRACTED` confidence unless they carry an explicit evidence field (see D-53.08).
- **D-53.08:** Promotion to `EXTRACTED` requires an explicit `evidence` field on the edge — e.g., `evidence: "annotation"` (for `# graphify: implements MyConcept` style markers), `evidence: "jsdoc"`, `evidence: "test_docstring"`. Schema documents the allowed evidence values; unknown evidence value → validation error.
- **D-53.09:** `AMBIGUOUS` is permitted for any of the four new relations without evidence (existing semantic).
- **D-53.10:** `implements` confidence rules are unchanged from Phase 46 (backward compat).

### Stability acceptance bar (CGRAPH-02)
- **D-53.11:** Tests prove **identical edges in identical order** across re-runs:
  - Test runs `build()` twice on the same fixture
  - Asserts `list(graph.edges(data=True)) == list(graph.edges(data=True))`
  - Asserts `_normalize_concept_code_edges(...)` output list equality (not just set)
- **D-53.12:** A round-trip fixture is added under `tests/fixtures/concept_code/` containing nodes/edges across all five relations (`implements` + 4 new) including duplicate-direction edge pairs and mergeable duplicates.
- **D-53.13:** `graph.json` byte-for-byte stability is **not** required (deferred — would catch export-layer non-determinism unrelated to Phase 53 scope).

### Claude's Discretion
- Test file layout (one new test module vs additions to existing `test_validate.py` / `test_build.py`) — planner decides.
- Whether new relations get tree-sitter AST signals in this phase or stay LLM-only — researcher to evaluate; default is LLM-only (no extractor changes in Phase 53 unless trivial).
- Specific docstring format for `evidence` annotation parsing — researcher to investigate cross-language conventions.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Requirements & roadmap
- `.planning/REQUIREMENTS.md` §"Concept ↔ code graph semantics (CGRAPH)" — CGRAPH-01 + CGRAPH-02 wording (canonical)
- `.planning/ROADMAP.md` §"Phase 53" — Goal, Depends on, Success Criteria
- `.planning/research/SUMMARY.md` — v1.11 sequencing rationale (graph schema first)
- `.planning/research/ARCHITECTURE.md` — pipeline boundaries to honor
- `.planning/research/PITFALLS.md` — concept↔code edge pitfalls

### Prior milestone artifacts (locked, must not break)
- `.planning/milestones/v1.10-REQUIREMENTS.md` §"CCODE-01..05" — Phase 46 contract
- `graphify/validate.py` (esp. `KNOWN_RELATIONS`, `REQUIRED_EDGE_FIELDS`, `warn_unknown_relations`) — schema entry point
- `graphify/build.py` (esp. `_merge_edge_fields`, `_normalize_concept_code_edges`) — merge entry point
- `graphify/security.py` — sanitization boundary (CCODE-05 still applies; new labels/paths must pass through)
- `docs/RELATIONS.md` — relation vocabulary docs (must be updated)

### Code paths likely affected
- `graphify/validate.py` — add four relations to `KNOWN_RELATIONS`; add `evidence` field validation; add INFERRED-default + EXTRACTED-evidence rule
- `graphify/build.py` — extend `_normalize_concept_code_edges` to cover new relations; canonicalize merge fields per D-53.05; add canonical sort per D-53.06
- `tests/test_validate.py`, `tests/test_build.py` — extend with new-relation cases
- `tests/fixtures/concept_code/` — new fixture corpus

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `_normalize_concept_code_edges` (build.py:71) — already orients code→concept, merges duplicates by `(src, tgt, rel)`, collapses opposite-direction `implements` pairs. Phase 53 extends, doesn't rewrite.
- `_merge_edge_fields` (build.py:47) — single point for field-level merge. Add canonical sort + max() rules here.
- `KNOWN_RELATIONS` (validate.py:12) — already includes `implements`, `conceptually_related_to`. Add four new entries.
- `warn_unknown_relations` (validate.py:49) — non-blocking warning path. Adding to `KNOWN_RELATIONS` silences it.
- `REQUIRED_EDGE_FIELDS` (validate.py:10) — `{source, target, relation, confidence, source_file}`. `evidence` is added as conditional-required (only when confidence=EXTRACTED on new relations).

### Established Patterns
- **Confidence enum:** EXTRACTED / INFERRED / AMBIGUOUS — locked, don't extend.
- **Direction normalization:** code → concept (per Phase 46). All five relations follow this.
- **No new required deps:** Use stdlib only for any new validation/merge logic. (Project constraint, see CLAUDE.md.)
- **Fail-loudly validation:** `validate_extraction` returns list of error strings; build proceeds only if list is empty.
- **`from __future__ import annotations`:** First line of every module.

### Integration Points
- Phase 54 (MCP/trace) will read these new relations from the built graph — schema must be stable before 54 starts.
- Phase 58 (vault CLI parity) and the existing Obsidian exporter (`export.py::to_obsidian`) consume relations via `graph.json`; canonical sort (D-53.06) protects them from re-run flicker.
- Existing telemetry (Phase 9.1 query telemetry / usage-weighted edges) keys by `(src, tgt, rel)` — unchanged by Phase 53 (no new ID field).

</code_context>

<specifics>
## Specific Ideas

- The `evidence` field for EXTRACTED promotion is the user's structural defense against over-confident LLM tags. Treat it as a contract, not a suggestion — validation must reject EXTRACTED-without-evidence.
- "Identical edges in identical order" is the bar — not "edges as sets". The canonical sort step (D-53.06) is what makes this achievable; don't skip it as an optimization.
- Test the round-trip with **mergeable duplicates** in the fixture, not just unique edges. The dedupe path is the part that historically drifts.

</specifics>

<deferred>
## Deferred Ideas

- **`graph.json` byte-for-byte equality** — would protect export-layer determinism but adds blast radius beyond Phase 53. Future hygiene phase if export flicker becomes an issue.
- **Content-hash edge IDs** — if/when MCP needs label-rename resilience, revisit. Out of scope for v1.11.
- **AST-based extractors for `realizes` / `instantiates`** — tree-sitter signal extraction (e.g., Java `implements`, Python ABC subclass). Default in Phase 53 is LLM-only; revisit when extractor coverage matters.
- **Per-language `evidence` annotation parsing** (e.g., `# graphify:` for Python, `// @graphify` for JS) — Phase 53 defines the schema field; concrete annotation parsers can land in a follow-up extractor phase.

</deferred>

---

*Phase: 53-concept-code-schema-build-merge*
*Context gathered: 2026-04-30*
