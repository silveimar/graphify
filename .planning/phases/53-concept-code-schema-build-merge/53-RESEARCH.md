# Phase 53: Concept↔code schema & build merge - Research

**Researched:** 2026-04-30
**Domain:** Graph schema vocabulary + deterministic edge merge (concept↔code semantics)
**Confidence:** HIGH (in-tree code inspection of `validate.py`, `build.py`, `serve.py`, existing tests; no external library guesswork required)

## Summary

Phase 53 extends an existing, well-bounded contract that landed in v1.10 Phase 46:

1. `validate.py::KNOWN_EDGE_RELATIONS` already contains `implements` + `implemented_by` — Phase 53 adds 4 more typed concept↔code relations to that frozenset.
2. `build.py::_normalize_concept_code_edges` already orients code→concept and merges `(src, tgt, rel)` duplicates plus opposite-direction `implements` collapses — Phase 53 hardens the field-level merge inside `_merge_edge_fields` and adds a final canonical sort.

The phase is scoped tightly: schema entries, merge canonicalization rules, an `evidence` field validator gate, a fixture-backed round-trip test, and `docs/RELATIONS.md` updates. **No new dependencies, no new modules, no new public API.**

**Primary recommendation:** Treat Phase 53 as four discrete waves — (1) Wave 0 fixture + failing tests, (2) `validate.py` schema additions including `evidence` rule, (3) `build.py` canonical merge + sort, (4) docs/RELATIONS.md. Keep `implements` semantics byte-identical to Phase 46 — every change must be additive.

## Project Constraints (from CLAUDE.md)

- Python 3.10+ (CI: 3.10 and 3.12)
- **No new required dependencies** — stdlib only for any logic added in this phase
- `from __future__ import annotations` first import in every module
- All file paths confined to `graphify-out/` per `security.py` patterns; label sanitization at security boundary
- Pure unit tests, no network, no FS side effects outside `tmp_path`
- Type hints with PEP 604 union syntax (`str | None`), built-in collection types (`list[str]` not `List[str]`)
- Fail-loudly: `validate_extraction` returns list of error strings; build proceeds only if list is empty
- One test file per module; PyPI package name `graphifyy`, internal name `graphify`

## User Constraints (from CONTEXT.md)

### Locked Decisions

- **D-53.01:** Add `documents`, `tests`, `realizes`, `instantiates` to `KNOWN_EDGE_RELATIONS` in `validate.py`. Per-relation directions:
  - `documents` — doc → concept
  - `tests` — test → concept
  - `realizes` — code → concept (interface/abstract)
  - `instantiates` — code → concept (concrete subtype)
- **D-53.02:** Existing `implements` is hardened, not replaced. All five concept↔code relations canonically oriented code → concept.
- **D-53.03:** `docs/RELATIONS.md` is updated; `warn_unknown_relations` will not warn for these once added.
- **D-53.04:** Edge dedupe key remains `(source, target, relation)` — no `edge_id` / content-hash field added.
- **D-53.05:** On merge, canonicalize: `source_files` lex-sorted+deduped, `confidence_score` = max(), `source_location` = lex-lowest, `confidence` = highest tier.
- **D-53.06:** After all dedupe passes, apply final canonical sort by `(source, target, relation)` ascending across **all** edges (concept↔code AND structural).
- **D-53.07:** New relations default to `INFERRED` and require `confidence_score ∈ [0.0, 1.0]`. EXTRACTED on a new relation requires explicit `evidence` field.
- **D-53.08:** Promotion to EXTRACTED requires explicit `evidence` field; unknown evidence value → validation error.
- **D-53.09:** AMBIGUOUS permitted for any new relation without evidence.
- **D-53.10:** `implements` confidence rules unchanged from Phase 46 (backward compat).
- **D-53.11:** Tests prove identical edges in identical order across re-runs (list equality, not set).
- **D-53.12:** Round-trip fixture under `tests/fixtures/concept_code/`.
- **D-53.13:** `graph.json` byte-for-byte equality is **not** required (deferred).

### Claude's Discretion

- Test file layout (one new module vs additions to existing `test_validate.py`/`test_build.py`).
- Whether new relations get tree-sitter AST signals in this phase or stay LLM-only.
- Concrete docstring/annotation format for `evidence` parsing.

### Deferred Ideas (OUT OF SCOPE)

- `graph.json` byte-for-byte equality (export-layer hygiene).
- Content-hash edge IDs (revisit if MCP needs label-rename resilience).
- AST-based extractors for `realizes` / `instantiates` (tree-sitter ABC / `implements`).
- Per-language `evidence` annotation parsing (`# graphify:`, `// @graphify`).

## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| CGRAPH-01 | `validate_extraction` accepts new relation values for concept↔implementation edges with required fields and confidence rules aligned to existing schema | §"Codebase deep-dive: validate.py" + §"Implementation guidance: schema" below pinpoint `KNOWN_EDGE_RELATIONS` (line 14), `REQUIRED_EDGE_FIELDS` (line 10), and the conditional-`evidence` rule shape |
| CGRAPH-02 | `build` / merge preserves concept↔code edges with deterministic dedupe and stable IDs | §"Codebase deep-dive: build.py" + §"Implementation guidance: merge/sort" below specify exact insertion points in `_merge_edge_fields` (line 47) and `_normalize_concept_code_edges` (line 71) |

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Relation vocabulary registry | Schema (`validate.py`) | Docs (`RELATIONS.md`) | Single source of truth for known relations is `KNOWN_EDGE_RELATIONS`; docs mirror it |
| Per-edge schema validation (`evidence` rule) | Schema (`validate.py`) | — | All extractor input flows through `validate_extraction` before graph assembly |
| Direction normalization (code→concept) | Build (`build.py::_normalize_concept_code_edges`) | — | Already owns orient/swap logic for `implements`/`implemented_by` |
| Field-level merge (max score, lex sort) | Build (`build.py::_merge_edge_fields`) | — | Single function called once per `(src,tgt,rel)` collision |
| Final canonical edge ordering | Build (`build.py::_normalize_concept_code_edges` epilogue) | — | Must run after all dedupe passes; before NetworkX `add_edge` loop |
| Round-trip stability assertions | Tests (`tests/test_*.py`) | Fixtures (`tests/fixtures/concept_code/`) | Existing pattern: pure unit tests, list-equality assertions |

## Codebase Deep-Dive

### `graphify/validate.py` (174 lines, current state)

| Symbol | Line | What it does | Phase 53 change |
|--------|------|--------------|-----------------|
| `VALID_FILE_TYPES` | 7 | `{code, document, paper, image, rationale}` | unchanged |
| `VALID_CONFIDENCES` | 8 | `{EXTRACTED, INFERRED, AMBIGUOUS}` | unchanged |
| `REQUIRED_NODE_FIELDS` | 9 | `{id, label, file_type, source_file}` | unchanged |
| `REQUIRED_EDGE_FIELDS` | 10 | `{source, target, relation, confidence, source_file}` | unchanged (do NOT add `evidence` here — it's conditional) |
| `KNOWN_EDGE_RELATIONS` | 14 | frozenset, currently 24 entries including `implements`, `implemented_by`, `conceptually_related_to` | **Add 4: `documents`, `tests`, `realizes`, `instantiates`** |
| `KNOWN_HYPEREDGE_RELATIONS` | 42 | `{participate_in, implement, implements, form}` | unchanged |
| `warn_unknown_relations` | 49 | One stderr line per distinct unknown relation; non-blocking | Will silently accept the 4 new relations once added to set |
| `validate_extraction` | 88 | Returns `list[str]` of errors. Iterates edges checking required fields + confidence enum + node-id existence | **Insert per-edge `evidence` rule for new relations** (see §Implementation guidance) |
| `assert_valid` | 169 | Raises `ValueError` if errors non-empty | unchanged |

Note that `validate_extraction` accepts both `"edges"` and `"links"` keys (NetworkX <= 3.1 compat). New evidence rule must respect that fallback.

### `graphify/build.py` (222 lines, current state)

| Symbol | Line | What it does | Phase 53 change |
|--------|------|--------------|-----------------|
| `_CONF_RANK` | 30 | `{EXTRACTED:3, INFERRED:2, AMBIGUOUS:1}` | unchanged |
| `_edge_priority` | 33 | Returns `(rank, score)` tuple for ladder comparison | unchanged |
| `_merge_edge_fields` | 47 | Picks higher-priority as base; concatenates differing `source_file` and `source_location` with `"; "`; sums weights | **REWRITE field-level rules per D-53.05**: lex-sorted dedupe of source_files, max() of confidence_score, lex-lowest source_location, highest confidence tier |
| `_normalize_concept_code_edges` | 71 | (1) `implemented_by` → swap+rename to `implements`. (2) Orient code→concept for `implements`. (3) `(src,tgt,rel)` dict-merge across **all** edges. (4) Opposite-direction `implements` collapse via `frozenset` bucket. Mutates `edges` list in place. | **Extend orientation step to all 5 concept↔code relations**; **append final canonical sort** by `(source, target, relation)` ascending |
| `build_from_json` | 137 | Calls `_normalize_concept_code_edges`, then `validate_extraction`, then assembles `nx.Graph` / `nx.DiGraph` | unchanged (canonical sort lives inside `_normalize_concept_code_edges` epilogue so it applies before NetworkX iteration order matters) |
| `build` | 191 | Concatenates extractions and elicitation, calls `build_from_json` | unchanged |

**Critical insight on existing merge**: today `_merge_edge_fields` concatenates `source_file` strings as `"k.py; other.py"` order-dependent. **This is the historical drift source.** Switching to `sorted(set(...))` and serializing as a stable form (e.g., `"; ".join(sorted(unique))`) is the actual change that makes round-trip stable.

### Existing test patterns

`tests/test_concept_code_edges.py` (~120 lines) is the established host module for Phase 46 work. It demonstrates the exact pattern Phase 53 should follow:

```python
def test_implemented_by_normalizes_to_implements_orient_code_to_concept():
    extraction = {"nodes": [...], "edges": [...]}
    G = build_from_json(extraction)
    assert G.number_of_edges() == 1
    _, _, data = next(iter(G.edges(data=True)))
    assert data.get("relation") == "implements"
    assert data["_src"] == "k_code"
    assert data["_tgt"] == "c_doc"
```

Patterns in use:
- In-process JSON dicts as fixtures (no file I/O for happy path)
- `tempfile.TemporaryDirectory()` only for round-trip-through-`graph.json` tests
- Direct edge-data inspection via `G.edges(data=True)` iteration
- `_src`/`_tgt` attributes to verify direction survived undirected NetworkX storage

`tests/fixtures/extraction.json` is the canonical small fixture (4 nodes, 4 edges, demonstrates `implements` from a code node to a document node). Phase 53 fixture should mirror this shape but expand to all 5 concept↔code relations.

### Downstream consumers of `implements` (must not regress)

| File | Usage | Phase 53 impact |
|------|-------|-----------------|
| `graphify/serve.py:2137-3367` | `_implements_hop_kind`, `_implements_hop_allowed`, `_run_concept_code_hops`, MCP tool `concept_code_hops` (Phase 47) — BFS over `implements` edges only | **No change required.** Phase 53 doesn't extend MCP traversal to new relations (that's Phase 54). |
| `graphify/analyze.py` | God-node detection by degree — relation-agnostic | unaffected by canonical sort |
| `graphify/export.py` | `to_obsidian`, `to_neo4j`, HTML viz — iterates `G.edges(data=True)` | **Beneficiary of canonical sort** — non-deterministic edge ordering is the latent bug Phase 53 closes |
| `graphify/seed.py` | Reads alias maps; relation-agnostic | unaffected |
| `tests/test_concept_code_edges.py` | Existing Phase 46 tests | must continue passing |
| `tests/test_concept_code_mcp.py` | Phase 47 MCP golden-path | must continue passing |
| `tests/test_excalidraw_layout.py`, `tests/test_confidence.py` | Use `implements` in fixtures | must continue passing |

**Risk audit:** No file *requires* a particular edge ordering today. The canonical sort is purely additive — it constrains an order that was previously implementation-defined.

## Implementation Guidance

### 1. New relations in `KNOWN_EDGE_RELATIONS` (D-53.01)

Insertion point: `validate.py` line ~37, immediately after `"implemented_by"` for grouping clarity:

```python
KNOWN_EDGE_RELATIONS: frozenset[str] = frozenset({
    "implements",
    "implemented_by",
    "documents",      # NEW: doc artifact → concept
    "tests",          # NEW: test artifact → concept
    "realizes",       # NEW: interface/abstract → concept
    "instantiates",   # NEW: concrete subtype → concept
    "calls",
    ...
})
```

No per-relation schema validation needed beyond what `evidence` rule covers. Direction is **canonicalized at build time**, not validated at schema time (mirrors Phase 46 treatment of `implemented_by` — accepted, then normalized).

### 2. `evidence` field rule (D-53.07, D-53.08, D-53.09)

**Allowed evidence values** (researcher recommendation, planner to confirm with user if scope expands):

| Value | Meaning | Source |
|-------|---------|--------|
| `annotation` | Explicit code marker (e.g., `# graphify: implements MyConcept`) | Per-language extractor |
| `jsdoc` | JSDoc-style structured comment tag | TS/JS extractors |
| `docstring` | Python/Ruby/Java structured docstring tag | Code extractors |
| `test_docstring` | Test docstring naming asserted concept | Test-file extractor |
| `inheritance` | AST-derived `class X(Concept)` / `implements I` / Python ABC | Tree-sitter (deferred per CONTEXT) |

Recommend the planner ship a `KNOWN_EVIDENCE_VALUES` frozenset alongside `KNOWN_EDGE_RELATIONS` so it's discoverable in one place. Treat as additive: validation rejects only fully-unrecognized values.

**Validation rule shape** (insert in `validate_extraction` edge loop, right after the `confidence` enum check):

```python
NEW_CONCEPT_CODE_RELATIONS = frozenset({"documents", "tests", "realizes", "instantiates"})
KNOWN_EVIDENCE_VALUES = frozenset({"annotation", "jsdoc", "docstring", "test_docstring", "inheritance"})

rel = edge.get("relation")
conf = edge.get("confidence")
if rel in NEW_CONCEPT_CODE_RELATIONS:
    if conf == "EXTRACTED":
        ev = edge.get("evidence")
        if not isinstance(ev, str) or not ev:
            errors.append(f"Edge {i} relation={rel!r} confidence=EXTRACTED requires 'evidence' field")
        elif ev not in KNOWN_EVIDENCE_VALUES:
            errors.append(
                f"Edge {i} relation={rel!r} has unknown evidence {ev!r} - "
                f"must be one of {sorted(KNOWN_EVIDENCE_VALUES)}"
            )
    elif conf == "INFERRED":
        score = edge.get("confidence_score")
        try:
            s = float(score) if score is not None else None
        except (TypeError, ValueError):
            s = None
        if s is None or not (0.0 <= s <= 1.0):
            errors.append(
                f"Edge {i} relation={rel!r} confidence=INFERRED requires "
                f"'confidence_score' in [0.0, 1.0]"
            )
    # AMBIGUOUS: permitted without evidence/score (D-53.09)
```

**Backward-compat guard**: this rule applies **only to the four new relations**. `implements` is explicitly excluded (D-53.10) so existing fixtures with `EXTRACTED` `implements` edges and no `evidence` field continue to validate.

### 3. Canonical merge in `_merge_edge_fields` (D-53.05)

Replace current concatenation logic with deterministic transforms. Sketch (preserving signature):

```python
def _merge_edge_fields(primary: dict[str, Any], secondary: dict[str, Any]) -> dict[str, Any]:
    """Merge two edges with same (source, target, relation); deterministic across re-runs."""
    # Pick higher-priority as base for non-merged fields like 'evidence', 'relation'
    if _edge_priority(secondary) > _edge_priority(primary):
        base, other = secondary, primary
    else:
        base, other = primary, secondary
    out = dict(base)

    # source_file: union, lex-sorted, joined with "; "
    def _split_sf(v: Any) -> list[str]:
        if isinstance(v, list):
            return [s for s in v if isinstance(s, str)]
        if isinstance(v, str) and v:
            return [s.strip() for s in v.split(";") if s.strip()]
        return []
    sf_set = sorted(set(_split_sf(base.get("source_file")) + _split_sf(other.get("source_file"))))
    if sf_set:
        out["source_file"] = "; ".join(sf_set)

    # source_location: lex-lowest non-empty
    locs = [v for v in (base.get("source_location"), other.get("source_location"))
            if isinstance(v, str) and v]
    if locs:
        out["source_location"] = min(locs)

    # confidence: highest tier (already implicit in base selection above; explicit for clarity)
    if _CONF_RANK.get(str(other.get("confidence", "")), 0) > _CONF_RANK.get(str(base.get("confidence", "")), 0):
        out["confidence"] = other["confidence"]

    # confidence_score: max()
    scores = []
    for v in (base.get("confidence_score"), other.get("confidence_score")):
        try:
            if v is not None:
                scores.append(float(v))
        except (TypeError, ValueError):
            pass
    if scores:
        out["confidence_score"] = max(scores)

    # weight: still additive (preserves Phase 46 semantic)
    try:
        out["weight"] = float(base.get("weight", 1.0)) + float(other.get("weight", 1.0))
    except (TypeError, ValueError):
        out["weight"] = base.get("weight", 1.0)

    # evidence: prefer the EXTRACTED side's evidence if present (already inherited from base)
    return out
```

**Compatibility note**: existing Phase 46 test `test_duplicate_implements_merges_source_files` asserts `"k.py" in sf and "other.py" in sf`. Both substrings remain present under sorted-join; that test continues to pass. If the planner finds any test asserting **exact** `"a.py; b.py"` ordering, that test must be updated to assert sorted ordering (this is the intended behavioral change for CGRAPH-02).

### 4. Canonical sort in `_normalize_concept_code_edges` (D-53.06)

Insert at the very end of `_normalize_concept_code_edges`, after the existing `edges[:] = rest + impl_out` line:

```python
    # Final canonical sort across ALL relations (D-53.06)
    edges.sort(key=lambda e: (
        str(e.get("source", "")),
        str(e.get("target", "")),
        str(e.get("relation", "")),
    ))
```

Why inside this function and not in `build_from_json`: the function is the existing single hop where edge mutation happens, and it runs **before** `validate_extraction` and the NetworkX assembly loop, so canonical order propagates to NetworkX's edge insertion order. NetworkX preserves insertion order in modern (>=2.0) versions for both `Graph` and `DiGraph`, so this is sufficient for `G.edges(data=True)` iteration order.

### 5. Extend orientation to all 5 relations (D-53.02)

Inside `_normalize_concept_code_edges`, the existing block:

```python
    if rel == "implements":
        s, t = orient(str(e["source"]), str(e["target"]))
        e["source"], e["target"] = s, t
```

becomes:

```python
    CONCEPT_CODE_RELATIONS = ("implements", "documents", "tests", "realizes", "instantiates")
    if rel in CONCEPT_CODE_RELATIONS:
        s, t = orient(str(e["source"]), str(e["target"]))
        e["source"], e["target"] = s, t
```

**Important**: `documents` direction is doc → concept. The `orient()` helper currently flips when `target.file_type == "code"` and `source.file_type != "code"` — so a doc-source / concept-target edge is left alone (neither end is `code`). For the four new relations, **the existing `orient()` helper is correct only for `realizes`/`instantiates`/`tests`** when the source endpoint is `file_type == "code"`. For `documents`, neither endpoint is `code` (doc → document/rationale concept), so `orient()` returns unchanged — good.

The opposite-direction collapse (`impl_buckets` block) currently runs **only on `implements`**. Per D-53.02, the four new relations do not have an `implemented_by`-style synonym today, so do **not** add them to the opposite-direction collapse — that would silently merge user-distinct edges. Leave that block scoped to `implements`.

### 6. Documentation updates (D-53.03)

`docs/RELATIONS.md` — extend "Concept ↔ code (Phase 46)" section with a Phase 53 sub-table:

```markdown
### Phase 53 additions (v1.11)

| Relation | Direction | Confidence rules | Notes |
|----------|-----------|------------------|-------|
| `documents` | doc → concept | INFERRED+score default; EXTRACTED requires `evidence` | Docstring/comment/README references |
| `tests` | test → concept | INFERRED+score default; EXTRACTED requires `evidence=test_docstring` typically | Test file asserts behavior of concept |
| `realizes` | code → concept | INFERRED+score default; EXTRACTED requires `evidence=inheritance` typically | Interface/abstract type realization |
| `instantiates` | code → concept | INFERRED+score default; EXTRACTED requires `evidence=inheritance` typically | Concrete subtype |

`evidence` allowed values: `annotation`, `jsdoc`, `docstring`, `test_docstring`, `inheritance`.
```

If the project also has `docs/EXTRACTION-SCHEMA.md` (referenced in CONTEXT but not confirmed in this research session — planner should `ls docs/` to verify), mirror the `evidence`-field semantics there.

## Risks & Landmines (open questions resolved)

### Q1: What `evidence` values should be allowed?

**Recommendation:** Start with `{annotation, jsdoc, docstring, test_docstring, inheritance}` — covers Python (`# graphify:` annotation, docstring), JS/TS (jsdoc), test files (test_docstring), and AST-derived inheritance signals. **Confidence: MEDIUM** (no language survey performed; values selected by mapping CONTEXT.md examples to plausible cross-language sources). Mark as additive — easy to grow later. Validate with the user during planning if uncertain.

### Q2: Tree-sitter AST signals for `realizes`/`instantiates`?

**Available cheap signals in current extractors:**
- Python: `ast.ClassDef.bases` already extracted by `_import_python` family — could yield `realizes` when base name resolves to a known concept node, but **concept nodes are emitted by semantic extraction, not AST**, so the base-name-to-concept join has to wait for semantic merge.
- TypeScript: `class X implements I` and `interface I extends J` — `tree-sitter-typescript` exposes these as discrete node kinds.
- Java: `class X implements I` — first-class in `tree-sitter-java`.

**Recommendation: defer to a post-Phase-53 extractor phase.** AST-tagging requires the semantic-merge join to know *which* base class names are concept nodes; that join is non-trivial and out of scope for the Phase 53 schema/build hardening. CONTEXT.md D-53 explicitly leaves this as Claude's discretion with default = LLM-only; this research confirms LLM-only is the correct default for Phase 53.

### Q3: Edge cases that break `(source, target, relation)` dedupe today?

Three identified:

1. **`source_files` differ** — current code concatenates `"a.py; b.py"` order-dependent on iteration order. Fix: sorted-set join (D-53.05).
2. **`confidence_score` conflicts when both edges are INFERRED with same tier** — current code keeps `base` priority's score and drops the other. Fix: `max()` (D-53.05).
3. **`source_location` non-determinism when both have values** — current code concatenates `"L42; L7"` order-dependent. Fix: lex-min (D-53.05).

A fourth latent bug: NetworkX undirected `Graph` storage means that `add_edge(a, b)` and `add_edge(b, a)` produce one edge with implementation-defined `_src`/`_tgt`. Phase 46 already mitigates this with `_src`/`_tgt` attributes carried through. **Phase 53 does not need to revisit this** as long as direction normalization runs before NetworkX assembly (it does).

### Q4: Downstream consumers of edge ordering in `graph.json`?

Audit results:
- `serve.py::_run_concept_code_hops` — BFS visits neighbors in NetworkX adjacency order. Adjacency order is insertion-order. Canonical sort makes this deterministic across re-runs (improvement, not regression).
- `export.py::to_neo4j` (line 1031), `to_obsidian` HTML viz — iterate edges and emit Cypher / HTML. Output ordering becomes deterministic post-Phase-53 (silent improvement).
- MCP `query_graph`, `shortest_path` — algorithmic; output not order-dependent.
- Telemetry (Phase 9.1) — keys by `(src, tgt, rel)` triples; order-agnostic.

**Net: canonical sort is purely additive across all consumers.** No file in the repo asserts a specific non-canonical edge order today.

### Q5: Round-trip fixture structure?

**Recommendation: in-process JSON dict** (mirrors `tests/test_concept_code_edges.py` happy-path pattern). The directory `tests/fixtures/concept_code/` (D-53.12) should hold a small **JSON file** (`round_trip.json`) loadable via `json.loads(Path(...).read_text())` — **not a corpus directory**. Reasons:

1. Existing pattern in `tests/fixtures/extraction.json` is a single JSON dict with `nodes`/`edges`/token counts.
2. Phase 53 is testing `validate.py` + `build.py`, not detect/extract — no need for source files.
3. Easier to assert list equality on a deterministic input.

Layout proposal:

```
tests/fixtures/concept_code/
└── round_trip.json    # 5 concept↔code relations + structural edges + duplicates
```

Wave-3 test loads it once, calls `build_from_json` twice, asserts list equality of `G.edges(data=True)`.

### Q6: Where to document new relations?

`docs/RELATIONS.md` is the single authoritative registry per the file's own header. Update it. If `docs/EXTRACTION-SCHEMA.md` exists, mirror the `evidence` field there (`ls docs/` during planning to verify).

### Q7: Existing AMBIGUOUS handling for new-relation types?

Phase 46 has no special AMBIGUOUS handling — `validate_extraction` accepts AMBIGUOUS for any relation including `implements`. D-53.09 explicitly preserves this for the four new relations: AMBIGUOUS without `evidence` is permitted. **No code change needed for the AMBIGUOUS path** — the proposed `evidence` rule only fires on `confidence == "EXTRACTED"`.

## Suggested Wave Structure

The planner is free to combine waves; below is a tested-first decomposition that keeps each PR small and reviewable.

### Wave 0 — Test scaffolding & fixture (CGRAPH-01, CGRAPH-02 traceability)

**Scope:**
- Create `tests/fixtures/concept_code/round_trip.json` with the corpus shape in §"Test Corpus Suggestion" below.
- Write failing tests (red phase) in `tests/test_concept_code_edges.py` covering:
  - All 4 new relations validate-clean when INFERRED+score
  - EXTRACTED + new relation without `evidence` → validation error
  - EXTRACTED + new relation + unknown `evidence` value → validation error
  - EXTRACTED + new relation + valid `evidence` → validates clean
  - AMBIGUOUS + new relation without evidence → validates clean (D-53.09)
  - Round-trip: `build_from_json(fixture)` twice, list equality of `G.edges(data=True)`
  - Mergeable duplicates: same `(s,t,r)` from two source files merge with sorted `source_file` and `max(confidence_score)`
  - Direction normalization: `realizes`/`instantiates`/`tests` reversed input → canonicalized output
- Confirm tests fail with current code.

**Files:** `tests/test_concept_code_edges.py` (additions), `tests/fixtures/concept_code/round_trip.json` (new).

### Wave 1 — Schema (CGRAPH-01)

**Scope:**
- Add 4 relations to `KNOWN_EDGE_RELATIONS`.
- Add `KNOWN_EVIDENCE_VALUES` frozenset.
- Add `evidence` validation rule in `validate_extraction` (per §3 above).
- Confirm Wave-0 schema tests turn green; build/merge tests still red.

**Files:** `graphify/validate.py`.

### Wave 2 — Build merge & canonical sort (CGRAPH-02)

**Scope:**
- Rewrite `_merge_edge_fields` per §3 of guidance (sorted source_files, max score, lex-min location, highest tier).
- Extend orientation in `_normalize_concept_code_edges` to all 5 concept↔code relations.
- Append final canonical sort by `(source, target, relation)` ascending.
- Confirm all Wave-0 tests turn green.
- Run full test suite to confirm no Phase 46 / Phase 47 regression (`tests/test_concept_code_edges.py`, `tests/test_concept_code_mcp.py`, `tests/test_excalidraw_layout.py`).

**Files:** `graphify/build.py`.

### Wave 3 — Documentation (CGRAPH-01)

**Scope:**
- Update `docs/RELATIONS.md` Phase 53 sub-table.
- If `docs/EXTRACTION-SCHEMA.md` exists, mirror `evidence` semantics.
- Update v1.11 traceability table in `.planning/REQUIREMENTS.md` (mark CGRAPH-01, CGRAPH-02 status pointer if convention requires).

**Files:** `docs/RELATIONS.md`, optionally `docs/EXTRACTION-SCHEMA.md`, `.planning/REQUIREMENTS.md`.

### Wave 4 (optional — only if Wave 0-3 fit budget) — Edge-case hardening

**Scope:**
- Property-style test: shuffle input edge order across 5 random seeds; assert canonical output identical.
- Validation rejects `confidence_score` outside [0.0, 1.0] for new relations even when INFERRED.
- `evidence` rule does not fire on `implements` (backward-compat regression test).

## Test Corpus Suggestion

`tests/fixtures/concept_code/round_trip.json`:

```json
{
  "nodes": [
    {"id": "k_klass",     "label": "Klass",       "file_type": "code",     "source_file": "k.py",     "source_location": "L10"},
    {"id": "k_subklass",  "label": "SubKlass",    "file_type": "code",     "source_file": "sub.py",   "source_location": "L5"},
    {"id": "t_test_klass","label": "test_klass",  "file_type": "code",     "source_file": "tests/test_k.py", "source_location": "L1"},
    {"id": "d_readme",    "label": "README",      "file_type": "document", "source_file": "README.md","source_location": "§2"},
    {"id": "c_concept",   "label": "AuthService", "file_type": "rationale","source_file": "design.md"},
    {"id": "c_concept2",  "label": "TokenStore",  "file_type": "rationale","source_file": "design.md"}
  ],
  "edges": [
    {"source": "k_klass",     "target": "c_concept",  "relation": "implements",   "confidence": "EXTRACTED", "source_file": "k.py"},
    {"source": "k_klass",     "target": "c_concept",  "relation": "implements",   "confidence": "INFERRED",  "confidence_score": 0.6, "source_file": "other.py"},
    {"source": "k_subklass",  "target": "c_concept",  "relation": "instantiates", "confidence": "EXTRACTED", "evidence": "inheritance", "source_file": "sub.py"},
    {"source": "k_klass",     "target": "c_concept2", "relation": "realizes",     "confidence": "INFERRED",  "confidence_score": 0.8, "source_file": "k.py"},
    {"source": "t_test_klass","target": "c_concept",  "relation": "tests",        "confidence": "EXTRACTED", "evidence": "test_docstring", "source_file": "tests/test_k.py"},
    {"source": "d_readme",    "target": "c_concept",  "relation": "documents",    "confidence": "INFERRED",  "confidence_score": 0.5, "source_file": "README.md"},
    {"source": "c_concept",   "target": "k_klass",    "relation": "implements",   "confidence": "AMBIGUOUS", "source_file": "design.md"},
    {"source": "k_klass",     "target": "k_subklass", "relation": "contains",     "confidence": "EXTRACTED", "source_file": "k.py"}
  ]
}
```

What this fixture covers:

| Concern | Edge(s) | Expected outcome |
|---------|---------|------------------|
| All 5 concept↔code relations represented | edges 1, 3, 4, 5, 6 | All survive build |
| Mergeable duplicate (same s,t,r) with different source_files & confidence tiers | edges 1+2 | Single edge: confidence=EXTRACTED, source_file="k.py; other.py" (sorted), confidence_score=0.6 (only one had a score) |
| Opposite-direction `implements` collapse with AMBIGUOUS reverse | edges 1+2+7 | Single `implements` edge oriented k_klass→c_concept (code → rationale); AMBIGUOUS dropped per highest-tier rule |
| EXTRACTED + new relation requires evidence | edges 3, 5 | Both have `evidence` and validate clean |
| INFERRED + new relation requires score | edges 4, 6 | Both have score |
| Direction normalization reverses input | (add an extra: `c_concept → k_klass realizes` to invert) | After normalize: `k_klass → c_concept realizes` |
| Structural edges unaffected by canonical sort | edge 8 | Survives, sorted by `(source, target, relation)` alongside concept↔code edges |
| Round-trip stability | full fixture × 2 builds | `list(G.edges(data=True))` equal across runs |

Recommend the planner add a 9th edge: `{"source": "c_concept", "target": "k_klass", "relation": "realizes", ...}` to exercise direction-flip on a new relation explicitly.

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | `KNOWN_EVIDENCE_VALUES = {annotation, jsdoc, docstring, test_docstring, inheritance}` is a sensible starting set | §"evidence rule" | LOW — set is additive; planner / user can amend during discuss-phase |
| A2 | NetworkX preserves edge insertion order on iteration in versions used by graphify | §"canonical sort" | LOW — verified true since NetworkX 2.0 (Python dict order); graphify pins networkx but no version pin observed in pyproject |
| A3 | No downstream code asserts a specific pre-Phase-53 edge order | §"Q4" | LOW — grep audit covered serve.py / analyze.py / export.py / tests; canonical sort is additive |
| A4 | `tests/fixtures/concept_code/` should hold JSON file(s), not a corpus directory | §"Q5" | LOW — pattern matches `tests/fixtures/extraction.json` precedent; user accepts via D-53.12 wording "fixture under tests/fixtures/concept_code/" |
| A5 | `docs/EXTRACTION-SCHEMA.md` may or may not exist | §"docs" | LOW — planner verifies via `ls docs/` |

## Environment Availability

Phase 53 is purely code/config/docs work — no new external dependencies, no runtime tools beyond pytest. Skipped per rule.

## Validation Architecture

### Test Framework

| Property | Value |
|----------|-------|
| Framework | pytest (as configured in `pyproject.toml`; `[all]` extras include test deps) |
| Config file | `pyproject.toml` (no separate pytest.ini) |
| Quick run command | `pytest tests/test_concept_code_edges.py tests/test_validate.py tests/test_build.py -q` |
| Full suite command | `pytest tests/ -q` |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|--------------|
| CGRAPH-01 | New relations accepted by validate_extraction | unit | `pytest tests/test_concept_code_edges.py -k new_relation -x` | Wave 0 (additions to existing file) |
| CGRAPH-01 | EXTRACTED on new relation requires `evidence` | unit | `pytest tests/test_concept_code_edges.py -k evidence -x` | Wave 0 |
| CGRAPH-01 | INFERRED on new relation requires `confidence_score ∈ [0,1]` | unit | `pytest tests/test_concept_code_edges.py -k inferred_score -x` | Wave 0 |
| CGRAPH-01 | AMBIGUOUS on new relation does not require evidence | unit | `pytest tests/test_concept_code_edges.py -k ambiguous -x` | Wave 0 |
| CGRAPH-02 | `(s,t,r)` dedupe with canonical merge | unit | `pytest tests/test_concept_code_edges.py -k merge -x` | Wave 0 |
| CGRAPH-02 | Identical edges in identical order across re-runs | unit | `pytest tests/test_concept_code_edges.py -k round_trip -x` | Wave 0 |
| CGRAPH-02 | Direction normalization for all 5 concept↔code relations | unit | `pytest tests/test_concept_code_edges.py -k orient -x` | Wave 0 |
| Backward compat | Phase 46 `implements` semantics unchanged | unit | `pytest tests/test_concept_code_edges.py -k implements -x` | ✅ existing |
| Backward compat | Phase 47 MCP `concept_code_hops` unchanged | unit | `pytest tests/test_concept_code_mcp.py -x` | ✅ existing |

### Sampling Rate

- **Per task commit:** `pytest tests/test_concept_code_edges.py tests/test_validate.py tests/test_build.py -q`
- **Per wave merge:** `pytest tests/ -q -x`
- **Phase gate:** Full suite green on Python 3.10 and 3.12 (CI matrix).

### Wave 0 Gaps

- [ ] `tests/fixtures/concept_code/round_trip.json` — round-trip fixture corpus (D-53.12)
- [ ] Test additions in `tests/test_concept_code_edges.py` covering 8 scenarios above (planner may split into a new module if file grows >300 lines)
- [ ] No `tests/conftest.py` change needed — existing fixtures sufficient
- [ ] No framework install needed — pytest already present

## Sources

### Primary (HIGH confidence)
- `/Users/silveimar/Documents/silogia-repos/graphify/graphify/validate.py` (174 lines, full read)
- `/Users/silveimar/Documents/silogia-repos/graphify/graphify/build.py` (222 lines, full read)
- `/Users/silveimar/Documents/silogia-repos/graphify/tests/test_concept_code_edges.py` (~120 lines, full read)
- `/Users/silveimar/Documents/silogia-repos/graphify/docs/RELATIONS.md` (full read)
- `/Users/silveimar/Documents/silogia-repos/graphify/.planning/phases/53-concept-code-schema-build-merge/53-CONTEXT.md` (canonical decisions D-53.01..13)
- `/Users/silveimar/Documents/silogia-repos/graphify/.planning/REQUIREMENTS.md` (CGRAPH-01, CGRAPH-02 wording)
- `/Users/silveimar/Documents/silogia-repos/graphify/.planning/ROADMAP.md` (Phase 53 success criteria)
- `/Users/silveimar/Documents/silogia-repos/graphify/.planning/milestones/v1.10-REQUIREMENTS.md` (CCODE-01..05 prior contract)
- `/Users/silveimar/Documents/silogia-repos/graphify/.planning/research/SUMMARY.md`, `PITFALLS.md` (v1.11 cross-cutting risks)

### Secondary (MEDIUM confidence)
- Grep audit of `implements` consumers across `graphify/` and `tests/` — verified no edge-order assertions
- `tests/fixtures/extraction.json` precedent for fixture shape

### Tertiary (LOW confidence)
- None — every claim in this document derives from in-tree code or locked CONTEXT.md decisions

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — no new deps, all changes against in-tree files
- Schema additions: HIGH — exact insertion points identified
- Build merge logic: HIGH — `_merge_edge_fields` and `_normalize_concept_code_edges` fully read; rewrite scope bounded
- `evidence` value set: MEDIUM — no language-survey performed; recommended set is conservative and additive
- Tree-sitter AST extension feasibility: MEDIUM — deferred per CONTEXT, but signal locations identified for future phase
- Round-trip stability: HIGH — canonical sort + canonical merge fully eliminate identified non-determinism sources
- Backward compat: HIGH — `implements` exclusion from `evidence` rule (D-53.10) and opposite-direction collapse scoping protect Phase 46 surface

**Research date:** 2026-04-30
**Valid until:** 2026-05-30 (in-tree code; will only invalidate if `validate.py` or `build.py` are touched outside Phase 53)

## RESEARCH COMPLETE
