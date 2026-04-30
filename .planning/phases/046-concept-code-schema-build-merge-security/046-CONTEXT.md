# Phase 46: Concept↔Code Schema, Build Merge & Security - Context

**Gathered:** 2026-04-30
**Status:** Ready for planning

<domain>
## Phase Boundary

**Roadmap baseline:** First-class concept↔code relation type(s) in **`validate.py`** and **`build`/graph merge**, persisted through **`graph.json`** round-trip assumptions, with **`security.py`** sanitization everywhere new surface appears (**CCODE-01**, **CCODE-02**, **CCODE-05**).

**Explicitly later phases:** MCP listing/traversal (**CCODE-03**), **`/trace`** / **`entity_trace`** (**CCODE-04**) — Phase 47.

</domain>

<decisions>
## Implementation Decisions

### Relation taxonomy

- **D-46.01:** Use an explicit **directional pair** of relation strings (inverse of each other), not a single symmetric label. Canonical spellings: **planner chooses** stable `snake_case` aligned with existing vocabulary; default recommendation **`implements`** (code → concept) and **`implemented_by`** (concept → code), consistent with skill JSON examples that already mention `implements`.
- **D-46.02:** When extractors emit **redundant inverses** for the **same unordered pair** of nodes (same two endpoints, both directions), **`build()` canonicalizes to one directed edge** via a deterministic rule (planner specifies, e.g. always retain code→concept `implements`). This **supersedes** the earlier discuss option “preserve both directions” where it would duplicate semantics.
- **D-46.03:** **Unify hyperedge vocabulary with edge relations in Phase 46:** extend validation and documentation so hyperedge `relation` values are aligned with the same verb family as graph edges (not left as an unrelated `"implement"` string without reconciliation).

### Confidence semantics

- **D-46.04:** **`EXTRACTED`** for concept↔code edges when a **deterministic parser** finds the linkage (including **comments/docstrings**), not only AST structure.
- **D-46.05:** **`INFERRED`** when **LLM / semantic extraction** proposes the link without that deterministic anchor.
- **D-46.06:** **`AMBIGUOUS`** only for **conflicting sources**, weak/contested evidence, or equivalent ambiguity — not as the default for all LLM links.
- **D-46.07:** **`confidence_score`** on **INFERRED** edges: **planner aligns with current schema posture** for other INFERRED edges (today optional in validation; do not invent new hard requirement unless tightening is explicitly scoped).

### Merge & graph shape

- **D-46.08:** **Duplicate edges** with the same `(source, target, relation)` across extractions: **merge attributes** into one edge (planner defines merge keys — e.g. combine `source_file`, preserve richest metadata).
- **D-46.09:** Same triple but **differing confidence**: prefer **`confidence_score`** when comparing INFERRED edges; **break ties with confidence ladder** **`EXTRACTED` > `INFERRED` > `AMBIGUOUS`** when scores absent or equal.
- **D-46.10:** Remain on **`nx.Graph` / `nx.DiGraph`** — **no MultiGraph** in Phase 46; parallel evidences collapse via merged attributes.

### Validation & documentation

- **D-46.11:** **`validate.py`:** introduce relation validation that **`warn`s on stderr for unknown edge `relation` strings** but **does not fail** by default (backward compatible). **Hyperedges** use a **separate allowed vocabulary** (superset/subset as needed) with the same warn-unknown posture.
- **D-46.12:** Tests should **capture/assert stderr** where unknown-relation warnings are part of the contract (regression harness).
- **D-46.13:** Canonical relation registry for authors lives in **`docs/RELATIONS.md`** (new file), linked from **`.planning/codebase/ARCHITECTURE.md`** (or equivalent pipeline doc) and **`validate.py`** pointers.

### Claude's Discretion

- Exact canonical spellings if `implements`/`implemented_by` collide with overloaded meanings elsewhere.
- Deterministic canonical direction rule when collapsing inverse duplicates.
- Field-by-field merge matrix for duplicate edges and hyperedge allowed-list contents.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Planning & requirements

- `.planning/ROADMAP.md` — Phase 46 goal, success criteria, Depends on Phase 45.
- `.planning/REQUIREMENTS.md` — **CCODE-01**, **CCODE-02**, **CCODE-05** (Phase 46); **CCODE-03**, **CCODE-04** deferred to Phase 47.
- `.planning/phases/45-baselines-detect-self-ingestion/45-CONTEXT.md` — prior milestone hygiene decisions (**D-45.xx**) — avoid contradictory corpus/graph contracts.

### Code (implementation anchors)

- `graphify/validate.py` — extraction schema; extend for relation warnings + hyperedge alignment.
- `graphify/build.py` — merge order, edge dedupe/canonicalization, attribute merge.
- `graphify/security.py` — sanitization for any new rendered fields/paths (**CCODE-05**).
- `graphify/skill.md` (and platform variants) — JSON examples already listing `implements` among edge relations.

### Documentation (to create/update in Phase 46)

- `docs/RELATIONS.md` — canonical registry for edge + hyperedge relations (per **D-46.13**).

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets

- **`validate.py`** — validates required edge fields and **`VALID_CONFIDENCES`**; does **not** currently whitelist `relation` strings — Phase 46 adds warn-unknown behavior without breaking legacy extractions.
- **`build.build()`** — concatenates all edges then **`build_from_json`**; **`nx.Graph.add_edge`** overwrites same undirected pair — attribute-merge policy must run **before** or **during** graph construction to meet **D-46.08**.
- **Skill templates** — edge `relation` examples include `implements`, useful for naming alignment.

### Established Patterns

- Node merge: later extraction overwrites same `id` (documented in **`build.py`**).
- Edge direction: **`_src` / `_tgt`** preserved on undirected graphs for display.

### Integration Points

- **`graph.json`** export/import path used in tests — new merge rules must preserve **CCODE-02** fixture parity.
- Phase **47** will traverse these relations in MCP/trace — keep relation names stable and documented.

</code_context>

<specifics>
## Specific Ideas

- Discussion assumed **SEED-bidirectional-concept-code-links** naming alignment; no separate external SEED doc path was cited in-repo.

</specifics>

<deferred>
## Deferred Ideas

- **Phase 47:** MCP tools / structured query for typed concept↔implementation links (**CCODE-03**); **`/trace`** or **`entity_trace`** golden paths (**CCODE-04**).

</deferred>

---

*Phase: 46-Concept↔Code Schema, Build Merge & Security*
*Context gathered: 2026-04-30*
