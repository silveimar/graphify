# Graphify relation vocabulary

Authoritative registry for **`edge.relation`** strings (extract JSON) and **`hyperedges[].relation`** (group edges). **`validate.py`** warns once per unknown value on stderr; update this doc when adding emitters.

## Concept ↔ code (Phase 46)

| Relation | Direction | Notes |
|----------|-----------|--------|
| `implements` | **code → concept** | Canonical after `build()` normalization. |
| `implemented_by` | concept → code | Accepted from extractors; normalized to `implements` with endpoints swapped before graph assembly. |

Non-code endpoints (both ends non-`code` `file_type`): orientation is left as emitted after `implemented_by` removal.

### Phase 53 additions (v1.11)

The four relations below extend the concept↔code vocabulary established by Phase 46's `implements` / `implemented_by`. All five concept↔code relations are canonically oriented **code → concept** at build time (`graphify/build.py::_normalize_concept_code_edges`).

| Relation | Direction | Default confidence | Notes |
|----------|-----------|--------------------|-------|
| `documents` | doc → concept | INFERRED + `confidence_score` | Docstring / comment / README references a concept |
| `tests` | test → concept | INFERRED + `confidence_score` | Test artifact asserts behavior of a concept |
| `realizes` | code → concept | INFERRED + `confidence_score` | Interface / abstract type realization |
| `instantiates` | code → concept | INFERRED + `confidence_score` | Concrete subtype instantiation |

#### Confidence rules (D-53.07-09)

For the four new relations only (`implements` retains Phase 46 semantics — D-53.10):

- `INFERRED` — requires `confidence_score ∈ [0.0, 1.0]`.
- `EXTRACTED` — requires an `evidence` field whose value is one of:
  - `annotation` — explicit code marker (e.g. `# graphify: implements MyConcept`)
  - `jsdoc` — JSDoc-style structured comment tag
  - `docstring` — Python / Ruby / Java structured docstring tag
  - `test_docstring` — test docstring naming the asserted concept
  - `inheritance` — AST-derived inheritance (`class X(Concept)` / `implements I` / Python ABC)
- `AMBIGUOUS` — permitted without `evidence` or `confidence_score`.

Unknown `evidence` values are rejected by `validate_extraction`. The allowed set is additive — extend `KNOWN_EVIDENCE_VALUES` in `graphify/validate.py` when extractors emit new evidence kinds.

#### Merge & ordering invariants (D-53.05, D-53.06)

When two edges share `(source, target, relation)`, `graphify/build.py::_merge_edge_fields` canonicalizes the merged edge:

- `source_file` — union of inputs, lex-sorted, deduplicated, joined with `"; "`.
- `source_location` — lex-minimum of non-empty values.
- `confidence` — highest tier (EXTRACTED > INFERRED > AMBIGUOUS).
- `confidence_score` — `max()` across present numeric values.
- `weight` — sum (preserves Phase 46 semantic).
- `evidence` — **base-wins**. The merge inherits all non-canonicalized fields (including `evidence`) from the higher-priority edge via `out = dict(base)`. When two edges carry conflicting `evidence` values, the lower-priority edge's `evidence` is silently dropped. This is by design: `evidence` is only meaningful on `EXTRACTED` edges, and `_edge_priority` always promotes `EXTRACTED > INFERRED > AMBIGUOUS`, so the surviving `evidence` is always the one attached to the strongest tier.

After all merge passes, `_normalize_concept_code_edges` applies a final canonical sort by `(source, target, relation)` ascending across **all** edges (concept↔code AND structural). This guarantees `list(G.edges(data=True))` is identical across re-runs of `build_from_json` on the same input.

### MCP surfaces (Phase 47)

| MCP tool | Uses `implements` / concept↔code |
|----------|-----------------------------------|
| `concept_code_hops` | Traverses **only** `implements` edges on the live graph (bounded hops); implementation in `graphify/serve.py` (`_run_concept_code_hops`). |
| `query_graph`, `shortest_path`, … | May include `implements` among other relations depending on query — not relation-filtered to `implements` alone. |

## Structural / extractor edges

Includes **imports**, **imports_from**, **contains**, **method**, **inherits**, **defines**, **case_of** (Swift enums), **calls**, **includes**, **uses_component**, **binds_method**, **uses**, **rationale_for**.

## Semantic / narrative edges

Includes **references**, **cites**, **conceptually_related_to**, **shares_data_with**, **semantically_similar_to**, **related**, **related_to**.

## Tooling / harness

**derived_shortcut** — MCP-derived shortcut edges.

## Hyperedges

| Relation | Purpose |
|----------|---------|
| `participate_in` | Multi-node participation |
| `implement` | Legacy singular verb (skills); prefer aligning new payloads with `implements` where practical |
| `implements` | Allowed synonym on hyperedges |
| `form` | Group formation |

---

Implementation: `KNOWN_EDGE_RELATIONS` / `KNOWN_HYPEREDGE_RELATIONS` in `graphify/validate.py`.
