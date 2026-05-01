# Phase 54: MCP, trace & Obsidian parity - Context

**Gathered:** 2026-04-30
**Status:** Ready for planning

<domain>
## Phase Boundary

Surface the typed concept↔code edges shipped in Phase 53 through:

1. **MCP traversal** — extend `concept_code_hops` (Phase 47) to walk all 5 concept↔code relations via a backward-compat filter param
2. **MCP `entity_trace`** — extend to follow concept↔code hops in at least one golden-path scenario
3. **Obsidian vault output** — `to_obsidian()` emits per-relation sections in CODE notes and concept MOC notes, sourcing wikilinks from graph edges
4. **Parity tests** — bidirectional + per-relation count assertion proving graph and vault don't diverge

In scope: `graphify/serve.py` (MCP `concept_code_hops` + `entity_trace`), `graphify/export.py` (`to_obsidian` per-relation sections), tests in `tests/test_serve.py` / `tests/test_concept_code_mcp.py` / `tests/test_export_obsidian.py` (or equivalent), agent capability manifest updates if `concept_code_hops` signature changes, MCP `server.json` regeneration.

Out of scope (deferred):
- `/trace` slash workflow remains a temporal-tracing surface, not concept↔code (defer to a future phase if users ask)
- Obsidian Dataview query blocks (deferred — per-relation sections cover the requirement; Dataview is a future flexibility option)
- Profile-driven `concept_code_layout` switch (deferred to v1.11 CFG-01 phase if needed)
- Template work for new sections (Phase 55-56 will address template conditionals/loops)

</domain>

<decisions>
## Implementation Decisions

### MCP tool surface (CGRAPH-03)
- **D-54.01:** Keep tool name `concept_code_hops`. Add a `relations: list[str]` parameter, default `["implements"]`. Backward-compat for Phase 47 callers.
- **D-54.02:** Allowed `relations` values are exactly the 5 from Phase 53 (`implements`, `documents`, `tests`, `realizes`, `instantiates`). Unknown value → MCP tool error with actionable message. Empty list → error (use Phase 47 default semantics if user wants `implements`-only).
- **D-54.03:** `_implements_hop_kind` and `_implements_hop_allowed` helpers (Phase 47, lines 2137-2160 in serve.py) are renamed to `_concept_code_hop_kind` and `_concept_code_hop_allowed` and generalized over the relations filter. The `implements` traversal-step counter in the tool's response payload (`implements_traversal_steps`) is renamed to `traversal_steps` with a per-relation breakdown (`steps_by_relation: {relation: count}`). Backward-compat shim retains the old `implements_traversal_steps` key when `relations == ["implements"]` to avoid breaking existing capability manifest consumers.
- **D-54.04:** `entity_trace` MCP tool is extended to optionally follow concept↔code hops (param: `include_concept_code: bool = False`). When true, results merge concept↔code traversal alongside temporal hops. Backward-compat default = false.

### `/trace` vs `entity_trace` (CGRAPH-03)
- **D-54.05:** `/trace` slash workflow remains scoped to temporal tracing (Phase 11) — NOT updated in Phase 54. CGRAPH-03's "/trace OR entity_trace" requirement is satisfied via `entity_trace` MCP tool extension (D-54.04) and `concept_code_hops` widening (D-54.01).
- **D-54.06:** Documented mapping table (CGRAPH-03 success criterion) lives in `54-VERIFICATION.md`: a table mapping each CGRAPH-03 sub-requirement to the MCP tool/parameter/test that satisfies it.

### Obsidian export structure (CGRAPH-04)
- **D-54.07:** Each CODE note (graph node with `file_type='code'` exported by `to_obsidian()`) gets per-relation sections in the note body:
  ```
  ## Implements
  - [[ConceptA]]
  - [[ConceptB]]

  ## Documents
  - [[ConceptC]]
  ```
  Sections present only if non-empty. Section ordering: `Implements`, `Documents`, `Tests`, `Realizes`, `Instantiates` (canonical order).
- **D-54.08:** Each concept MOC note gets the **inverse** per-relation sections — listing CODE/test/doc artifacts that point at this concept:
  ```
  ## Implemented by
  - [[CodeFileA]]
  - [[CodeFileB]]

  ## Documented by
  - [[DocC]]
  ```
  Section ordering: `Implemented by`, `Documented by`, `Tested by`, `Realized by`, `Instantiated by`. Same empty-suppression rule.
- **D-54.09:** Wikilinks use the same `_make_id()` slugification + label resolution path as Phase 33 concept-naming. No new label-resolution code path. Sanitization through `security.py` (existing pattern).
- **D-54.10:** Per-relation sections are emitted by extending the existing template path in `to_obsidian` — no new templates, no profile changes (CFG-01 will add profile knobs in a later phase if needed).
- **D-54.11:** Existing CODE-note and concept-MOC bodies are NOT replaced — per-relation sections are appended at a deterministic position (after the existing summary block, before any user-preserved frontmatter trailer). Round-trip tests confirm this doesn't break v1.7 round-trip preservation.

### Parity assertion bar (CGRAPH-04)
- **D-54.12:** Golden-path parity test asserts THREE things on a fixture corpus:
  1. **Forward parity** — every concept↔code edge in graph appears as a wikilink in the right per-relation section of the right note
  2. **Backward parity** — every concept↔code wikilink in CODE/MOC notes maps to a graph edge with the matching relation type
  3. **Per-relation count parity** — for each of the 5 relations, count(graph edges) == count(vault wikilinks)
- **D-54.13:** Test corpus reuses (or extends) the Phase 53 round-trip fixture (`tests/fixtures/concept_code/round_trip.json`) plus a small synthetic vault output target. New fixture file path: `tests/fixtures/concept_code/vault_parity/` containing expected note bodies. Test compares actual export output to expected per-section content.
- **D-54.14:** Snapshot tests on full vault bytes are NOT used — too brittle, high false-positive rate. Per-section assertions are stricter where it matters and looser where it doesn't.

### Claude's Discretion
- Where exactly in `to_obsidian()` the per-relation sections get rendered (before/after `dataview_dynamic` block, around frontmatter preservation marks) — planner decides based on existing template structure.
- Whether `traversal_steps` payload key in `concept_code_hops` is a new top-level field or replaces `implements_traversal_steps` outright (D-54.03 specifies a backward-compat shim; planner determines exact JSON shape).
- Whether `entity_trace`'s `include_concept_code` integration uses BFS depth-limit shared with `concept_code_hops` or a separate `concept_code_max_hops` param — researcher to evaluate against existing `entity_trace` API.
- Test file organization (extend existing `test_concept_code_mcp.py` and `test_export_obsidian.py` vs new files) — planner decides based on file size.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Requirements & roadmap
- `.planning/REQUIREMENTS.md` §"Concept ↔ code graph semantics (CGRAPH)" — CGRAPH-03 + CGRAPH-04 wording (canonical)
- `.planning/ROADMAP.md` §"Phase 54" — Goal, Depends on, Success Criteria
- `.planning/research/SUMMARY.md` — v1.11 sequencing rationale
- `.planning/research/ARCHITECTURE.md`, `.planning/research/PITFALLS.md` — vault-export pitfalls

### Phase 53 (just shipped — locked, do not regress)
- `.planning/phases/53-concept-code-schema-build-merge/53-CONTEXT.md` — D-53.01..13 (vocabulary, orientation, evidence rules, canonical sort)
- `.planning/phases/53-concept-code-schema-build-merge/53-VERIFICATION.md` — Phase 53 must-haves
- `graphify/validate.py` — `KNOWN_EDGE_RELATIONS`, `KNOWN_EVIDENCE_VALUES`, `NEW_CONCEPT_CODE_RELATIONS`
- `graphify/build.py` — `_normalize_concept_code_edges`, `_merge_edge_fields`, canonical sort
- `tests/fixtures/concept_code/round_trip.json` — reusable corpus

### Prior milestone artifacts (locked, must not break)
- `.planning/milestones/v1.10-REQUIREMENTS.md` §"CCODE-03/04" — Phase 47 contract (`concept_code_hops` original signature, `entity_trace` Phase 11 origin)
- `graphify/serve.py` — `_run_concept_code_hops` (line 2161), `_implements_hop_kind` (line 2137), `_implements_hop_allowed` (line 2152), `_run_entity_trace` (line 1952)
- `graphify/export.py` — `to_obsidian()` (line 547), MOC rendering (line 784+), concept-naming via Phase 33 `resolve_concept_names` (line 619+)
- MCP capability manifest / `server.json` — must reflect any signature changes

### Code paths likely affected
- `graphify/serve.py` — `concept_code_hops`, `entity_trace`, helper renames, payload shape
- `graphify/export.py` — `to_obsidian` per-relation section rendering for CODE notes and concept MOCs
- `tests/test_concept_code_mcp.py` — new tests for `relations` param + new relations traversal
- `tests/test_serve.py` — `entity_trace` `include_concept_code` integration
- `tests/test_export_obsidian.py` (or new file) — bidirectional + per-relation count parity
- `tests/fixtures/concept_code/vault_parity/` — new fixture vault snippets
- `docs/RELATIONS.md` — append §"MCP traversal" with the `relations` param doc
- `scripts/sync_mcp_server_json.py` — re-run after signature changes; manifest hash invalidates if `graphify_version` bump warranted (researcher decides if v1.11 has shipped enough to warrant pre-milestone bump)

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `_run_concept_code_hops` (serve.py:2161) — already structured around an edge-walking BFS. Widening means parameterizing the predicate (currently `_implements_hop_allowed`) over a configurable `relations` set.
- `_implements_hop_kind` / `_implements_hop_allowed` (serve.py:2137, 2152) — single point to generalize. Rename + accept a `relations` arg.
- `to_obsidian()` (export.py:547) — entry point for CODE notes and concept MOCs. Existing template path is the natural insertion point for per-relation sections.
- `resolve_concept_names` (export.py:619) — Phase 33 concept-naming pipeline. Use to resolve concept node IDs to display labels for wikilinks. Don't reinvent.
- `_make_id` — existing slugifier used everywhere. Use for wikilink targets.
- `tests/fixtures/concept_code/round_trip.json` — Phase 53 fixture has 8 edges across all 5 relations. Reuse as the parity-test corpus base.

### Established Patterns
- **MCP tool error semantics:** raise with `[graphify]` prefix on stderr + return structured `{"error": "..."}`; existing pattern in serve.py.
- **MCP capability manifest:** `server.json` regenerated by `scripts/sync_mcp_server_json.py`; manifest hash includes `graphify_version`. If signature changes, regenerate.
- **Backward-compat for MCP:** Phase 47 already established the pattern of widening a tool via a default-=-old-behavior parameter (see `_concept_code_hops` original signature). Follow it.
- **Obsidian frontmatter preservation:** Phase 4 / Phase 8 round-trip safety. New sections must NOT touch frontmatter or user-preserved fields. Append per-relation sections inside the body block, between summary and trailer.
- **Concept↔code edge access:** edges are stored on the `nx.Graph` with `relation`, `_src`, `_tgt` (after `build_from_json` orientation). Use these directly; don't re-orient.

### Integration Points
- **Phase 53 → 54:** Phase 53 ships the validated typed edges. Phase 54 reads them. No mutation of build/validate.
- **Phase 47 → 54:** Phase 47's `concept_code_hops` is widened, not replaced. The `implements_traversal_steps` payload key is preserved as a backward-compat shim when `relations == ["implements"]`.
- **Phase 33 → 54:** Concept naming pipeline (`resolve_concept_names`) is reused for wikilink labels. No duplication.
- **Phase 8 / Phase 4 → 54:** Round-trip preservation guarantees. New per-relation sections must survive vault re-runs without clobbering user edits.
- **Phase 55-56 (later v1.11):** Template conditionals/loops + profile overrides may eventually replace the hard-coded section template with a profile-driven one. D-54.10 leaves room for that future move.

</code_context>

<specifics>
## Specific Ideas

- **Section ordering is canonical** (Implements → Documents → Tests → Realizes → Instantiates) — same on CODE notes and inverted on concept MOCs (Implemented by → Documented by → ...). Don't sort alphabetically; the canonical order matches reading flow ("what does this code DO" / "what describes it" / "what tests it" / etc.).
- **Empty-section suppression** is non-negotiable — vaults shouldn't have `## Tests` followed by a blank line. Only emit a section if at least one wikilink would land in it.
- **The parity test catches BOTH directions** — forward (graph → vault) and backward (vault → graph). Backward catches the bug class where someone manually edits a vault note adding a stale wikilink that no longer corresponds to a graph edge. Without backward parity, that drift is invisible.
- **Backward compat for `concept_code_hops` is structural, not just behavioral** — the tool's payload shape stays compatible when called with the default `relations=["implements"]`. The `implements_traversal_steps` key is preserved (D-54.03 shim).

</specifics>

<deferred>
## Deferred Ideas

- **`/trace` slash workflow concept↔code surfacing** — currently temporal-only. If users want conversational concept↔code tracing, add a future phase. Not blocking CGRAPH-03.
- **Profile-driven `concept_code_layout`** (per_relation / merged / dataview switch) — defer to CFG-01 (Phase 56) or a follow-up; per-relation default is fine for v1.11 ship.
- **Dataview query blocks for concept↔code** — covered by Phase 56 (TMPL-03 Dataview templates) if desired.
- **Per-relation hop limits** in `concept_code_hops` — single shared `max_hops` is sufficient for v1.11; per-relation tuning is YAGNI until users ask.
- **`graphify_version` PyPI bump for MCP signature change** — research evaluates whether v1.11 warrants a pre-milestone bump, or whether server.json regeneration alone is enough.

</deferred>

---

*Phase: 54-mcp-trace-obsidian-parity*
*Context gathered: 2026-04-30*
