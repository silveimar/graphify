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

## MCP traversal (Phase 54)

Phase 54 widens the existing MCP traversal surface so all five Phase 53 concept↔code relations are reachable through `concept_code_hops` and (optionally) merged into `entity_trace`. No new tools were added; existing schemas grew two new properties. Phase 47 callers continue to work unchanged.

### `concept_code_hops`

BFS-walk concept↔code edges from a starting node, bounded by hops and a global edge budget.

| Parameter | Type | Default | Notes |
|-----------|------|---------|-------|
| `entity` | string | required | Node label (preferred) or node id |
| `max_hops` | integer | `3` | Range `1..6` |
| `direction` | enum | `"both"` | `"code_to_concept"` / `"concept_to_code"` / `"both"` |
| `relations` | `list[string]` | `["implements"]` | Subset of the five concept↔code relations: `implements`, `documents`, `tests`, `realizes`, `instantiates` |

**Validation (`graphify/serve.py:_validate_relations_arg`):**

- Empty list → MCP `status=error` envelope (`"relations must not be empty"`).
- Unknown value → MCP `status=error` envelope listing the five allowed values.

**Payload (meta keys):**

| Key | Shape | Notes |
|-----|-------|-------|
| `relations` | `list[string]` | Sorted echo of the validated input |
| `traversal_steps` | integer | Total edges walked across all relations |
| `steps_by_relation` | `dict[string, int]` | Per-relation traversal count; keys are a subset of the 5 relations |
| `reachable_node_ids` | `list[string]` | Deterministic BFS output |
| `depth_by_id` | `dict[string, int]` | Hop distance from `entity` |
| `truncated` | boolean | True iff the global edge budget was hit |
| `implements_traversal_steps` | integer | **Backward-compat shim** — emitted **only** when `set(relations) == {"implements"}` (D-54.03 / Phase 47 compatibility) |

**Edge budget:** `_IMPL_EDGE_BUDGET = 500` (constant in `graphify/serve.py`). The same global cap applies regardless of how many relations are requested. When the cap is reached BFS halts and the payload sets `truncated=true`. The cap is not user-tunable on this tool (D-54.10 — no new params).

### `entity_trace`

Existing Phase 11 temporal-trace surface. Phase 54 adds an optional concept↔code merge.

| Parameter | Type | Default | Notes |
|-----------|------|---------|-------|
| `entity` | string | required | |
| `budget` | integer | `500` | Existing cap |
| `include_concept_code` | boolean | `false` | When `true`, merge concept↔code reachability into the meta envelope (D-54.04) |

When `include_concept_code=true`, the meta envelope gains:

- `concept_code_reachable: list[string]` — node ids reachable via the typed edges
- `concept_code_steps_by_relation: dict[string, int]` — per-relation step count

The merge uses fixed `max_hops=2` and **all five** concept↔code relations (no per-call tunable). When `include_concept_code` is omitted or `false` the response is byte-identical to Phase 11.

### Backward compatibility

| Caller | Behaviour |
|--------|-----------|
| Phase 47 client omitting `relations` on `concept_code_hops` | Defaults to `["implements"]`; `implements_traversal_steps` shim is present in the payload (set-equality, not None-vs-list — explicit `relations=["implements"]` also activates the shim per D-54.03). |
| Phase 11 client omitting `include_concept_code` on `entity_trace` | No change; trace envelope identical to Phase 11. |
| Manifest-pinned client | `server.json::_meta.manifest_content_hash` rotates when the tool schemas change. Re-run `python scripts/sync_mcp_server_json.py` after every schema edit. |

### Examples

Default-args call (Phase 47-compatible):

```json
{"tool": "concept_code_hops", "arguments": {"entity": "AuthService", "max_hops": 2}}
```

Returns meta:

```json
{
  "relations": ["implements"],
  "traversal_steps": 7,
  "steps_by_relation": {"implements": 7},
  "implements_traversal_steps": 7,
  "truncated": false
}
```

Widened-relations call:

```json
{"tool": "concept_code_hops", "arguments": {"entity": "AuthService", "relations": ["documents", "tests"]}}
```

Returns meta (note: shim absent — non-implements-only set):

```json
{
  "relations": ["documents", "tests"],
  "traversal_steps": 4,
  "steps_by_relation": {"documents": 3, "tests": 1},
  "truncated": false
}
```

`entity_trace` with concept↔code merge:

```json
{"tool": "entity_trace", "arguments": {"entity": "AuthService", "include_concept_code": true}}
```

Adds to the trace meta:

```json
{
  "concept_code_reachable": ["TokenStore", "AuthService_test"],
  "concept_code_steps_by_relation": {"implements": 2, "tests": 1}
}
```

### Implementation references

- Tool registration: `graphify/mcp_tool_registry.py` (input schemas).
- Validation: `graphify/serve.py:_validate_relations_arg`.
- Hop helpers: `graphify/serve.py:_concept_code_hop_kind`, `_concept_code_hop_allowed` (renamed from `_implements_hop_*` per D-54.03).
- BFS factor-out: `graphify/serve.py:_bfs_concept_code_from`.
- Tool body: `graphify/serve.py:_run_concept_code_hops`.
- `entity_trace` extension: `graphify/serve.py:_run_entity_trace`.



## Reasoning relations (Phase 72)

Reasoning relations encode claims about ideas/documents (not code). Both endpoints must be document- or concept-typed; code-typed endpoints are rejected by `validate.py`.

| Relation | Definition | Direction | Confidence |
|----------|-----------|-----------|------------|
| `supports` | Source asserts evidence in favor of target. | `supporter -> claim` | EXTRACTED, INFERRED (with `confidence_score` in [0.0, 1.0]), or AMBIGUOUS |
| `contradicts` | Source asserts target is false or incompatible. | symmetric semantically; emitted with stable `(source, target)` ordering by extractor | EXTRACTED, INFERRED (with `confidence_score` in [0.0, 1.0]), or AMBIGUOUS |
| `supersedes` | Source replaces target as canonical. **Orientation: newer -> older. The TARGET is the superseded (deprecated) node.** | `replacement -> deprecated` | EXTRACTED, INFERRED (with `confidence_score` in [0.0, 1.0]), or AMBIGUOUS |
| `evolved_into` | Source is an earlier version that became target. (Note: opposite orientation from `supersedes`.) | `older -> newer` | EXTRACTED, INFERRED (with `confidence_score` in [0.0, 1.0]), or AMBIGUOUS |
| `depends_on` | Source's claim relies on target's claim. | `dependent -> prerequisite` | EXTRACTED, INFERRED (with `confidence_score` in [0.0, 1.0]), or AMBIGUOUS |

All five relations may be emitted with confidence `EXTRACTED`, `INFERRED` (with `confidence_score` in [0.0, 1.0] per CCONF v1.13), or `AMBIGUOUS`.

### Auto-stamping interaction with Phase 71 temporal layer

When `A supersedes B` lands, `build.py` stamps `valid_until = run_now` on every other outbound edge of B. The behavior is idempotent (skipped when `valid_until` is already set). Rationale: once B is superseded, all its outbound claims become historical and surface in the wiki's `## Historical relations` subsection.

#### Worked example (ADR supersession)

`ADR-0042 supersedes ADR-0028` -> auto-stamps outbound edges of `adr_0028` with `valid_until = run_now`. Subsequent runs leave already-stamped edges unchanged.
