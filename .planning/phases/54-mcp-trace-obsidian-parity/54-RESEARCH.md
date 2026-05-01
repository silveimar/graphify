# Phase 54: MCP, trace & Obsidian parity - Research

**Researched:** 2026-04-30
**Domain:** MCP tool surface widening + Obsidian export parity
**Confidence:** HIGH (verified against committed code; Phase 53 just shipped, all line numbers fresh)

## Summary

Phase 54 surfaces the four new typed concept↔code relations shipped in Phase 53 (`documents`, `tests`, `realizes`, `instantiates`) plus the original `implements` through three surfaces: (1) widening `concept_code_hops` MCP tool to filter on a configurable `relations` list, (2) extending `entity_trace` to optionally merge concept↔code traversal alongside its temporal walk, and (3) emitting per-relation sections in CODE notes and concept MOCs from `to_obsidian()`. A bidirectional + per-relation parity test seals graph↔vault drift.

The codebase is in excellent shape for this work: Phase 53 already canonicalized concept↔code relations into a single tuple (`build.py:CONCEPT_CODE_RELATIONS`), validated evidence/score rules (`validate.py:NEW_CONCEPT_CODE_RELATIONS`, `KNOWN_EVIDENCE_VALUES`), and produces deterministic edge order. Phase 47's `_run_concept_code_hops` is structured around two narrow predicates (`_implements_hop_kind`, `_implements_hop_allowed`) that need only generalization — no rewrite. The Obsidian export pipeline (`templates.py:render_note`, `templates.py:render_moc`) has a clean `body` substitution slot already wired into both `code.md` and `moc.md` builtin templates that's currently empty (`"body": ""`) — this is the natural insertion point for per-relation sections, with zero template-file changes required.

**Primary recommendation:** Execute as a 4-wave TDD plan: (W1) failing parity + MCP `relations` tests using the existing Phase 53 fixture; (W2) widen `concept_code_hops` (rename helpers, validate `relations`, payload shim); (W3) populate `body` in `render_note`/`render_moc` for code+MOC types with per-relation sections; (W4) docs + capability manifest + `entity_trace` `include_concept_code` integration + manifest hash regen.

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| MCP tool widening (`concept_code_hops` relations filter) | `graphify/serve.py` (MCP layer) | `graphify/mcp_tool_registry.py` (schema) | Tool helpers (`_run_*`) are MCP layer; tool schema declarations live in registry; manifest hash recomputed by capability layer. |
| `entity_trace` concept↔code integration | `graphify/serve.py` | — | Helper `_run_entity_trace` is already MCP-only; `include_concept_code` merges concept↔code edge walking into its existing per-snapshot loop. |
| Capability manifest schema | `graphify/mcp_tool_registry.py` + `graphify/capability_tool_meta.yaml` | `scripts/sync_mcp_server_json.py` | Tool input schema lives in `mcp_tool_registry.build_mcp_tools()`; cost class/cacheability in YAML; manifest_content_hash derived. |
| Per-relation sections in CODE notes | `graphify/templates.py:render_note` | `graphify/export.py:to_obsidian` (call site) | The `body` substitution slot in `code.md` is empty by default and is the canonical place to append per-relation sections; `to_obsidian` already calls `render_note(... node_id, G, profile, "code", ctx)` with G in scope. |
| Per-relation inverse sections in concept MOCs | `graphify/templates.py:render_moc` (via `_render_moc_like`) | `graphify/export.py:to_obsidian` (call site) | The `body` slot in `moc.md` is also empty and reserved for this use. Concept MOCs are detected via `note_type == "moc"` + community-membership composition in `to_obsidian`. |
| Wikilink target slugification | `graphify/extract.py:_make_id` (already used everywhere) + `graphify/templates.py:_emit_wikilink` (renders `[[filename\|alias]]`) | `graphify/security.py:sanitize_label` | Reuse — D-54.09 says no new label-resolution path. |
| Concept display label resolution | `graphify/naming.py:resolve_concept_names` (Phase 33) | — | Already called by `to_obsidian` (`export.py:629`), produces `dict[community_id → ConceptName]`. Reuse for inverse-section labels on concept MOCs. |
| Concept↔code edge access | `nx.Graph` edge attrs `_src`/`_tgt` (Phase 53 canonicalized) | — | Graph is already source-of-truth; reading edges in `templates.py` body builders is the parity-by-construction strategy. |
| Parity test corpus | `tests/fixtures/concept_code/round_trip.json` (reuse) + new `tests/fixtures/concept_code/vault_parity/` | — | Phase 53's 8-edge / 5-relation fixture is exactly the right shape; only need expected vault note bodies as a new sub-fixture. |

## Standard Stack

### Core (already in repo, no additions)
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| networkx | unpinned | Graph traversal for BFS in `_run_concept_code_hops` | Project's primary abstraction (CLAUDE.md). |
| stdlib `string.Template` (`_BlockTemplate` extension) | 3.10+ | Templates expansion | CLAUDE.md "no new required deps"; Jinja2 explicitly out of scope per `REQUIREMENTS.md`. |
| pytest | 7.x (CI) | Tests | Existing test convention. |

### Supporting (already used)
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| `mcp` | optional (`[mcp]` extra) | MCP stdio server | Already wired; serve.py line 3354 dispatches `_tool_concept_code_hops`. |

**No new packages required.** D-54.10 explicitly forbids new templates/profile knobs.

**Version verification skipped:** No new packages. Existing extras unchanged.

## Architecture Patterns

### System Architecture Diagram

```
┌─ Phase 53 graph (typed concept↔code edges) ─────────┐
│   nx.Graph with edges{_src,_tgt,relation,confidence}│
│   relations ∈ {implements, documents, tests,        │
│                realizes, instantiates}              │
└──────────────────┬──────────────────┬───────────────┘
                   │                  │
        Phase 54 reader paths        │
                   │                  │
   ┌───────────────▼──────┐  ┌────────▼────────────┐
   │ MCP layer (serve.py) │  │ Export layer        │
   │                      │  │ (export.py +        │
   │ concept_code_hops    │  │  templates.py)      │
   │ (widened):           │  │                     │
   │ - relations filter   │  │ render_note(code):  │
   │ - per-relation count │  │  body = per-rel     │
   │ - shim impl_steps    │  │   sections          │
   │                      │  │  (Implements/       │
   │ entity_trace         │  │   Documents/Tests/  │
   │ (extended):          │  │   Realizes/         │
   │ - include_concept_\  │  │   Instantiates)     │
   │   code: bool         │  │                     │
   │ - merges concept↔    │  │ render_moc          │
   │   code hops into     │  │  (concept MOC):     │
   │   timeline meta      │  │  body = inverse     │
   └──────────┬───────────┘  │   sections          │
              │              │  (Implemented by/   │
              │              │   Documented by/    │
              │              │   Tested by/        │
              │              │   Realized by/      │
              │              │   Instantiated by)  │
              │              └─────────┬───────────┘
              │                        │
              ▼                        ▼
   ┌────────────────────┐  ┌─────────────────────┐
   │ MCP tool registry  │  │ Vault MD files      │
   │ (mcp_tool_registry │  │ (Atlas/Sources/.../ │
   │ .py, capability_   │  │  Atlas/Maps/...)    │
   │ tool_meta.yaml)    │  │                     │
   │                    │  │ Round-trip safe via │
   │ → server.json hash │  │ frontmatter / sentinel
   │ regenerated by     │  │ markers (Phase 4/8) │
   │ scripts/sync_mcp_  │  └─────────────────────┘
   │ server_json.py     │
   └────────────────────┘
              │
              ▼
   ┌────────────────────────────┐
   │ Parity test (W1 RED → W3   │
   │ GREEN)                     │
   │ - forward: edges → wikilinks│
   │ - backward: wikilinks → edges│
   │ - per-relation count match │
   └────────────────────────────┘
```

### Recommended File Layout
```
graphify/
├── serve.py             # widen concept_code_hops, extend entity_trace
├── mcp_tool_registry.py # update tool inputSchema for `relations`, `include_concept_code`
├── templates.py         # populate `body` slot in render_note (code) + render_moc
├── export.py            # (likely no changes — body fills in via templates.py)
docs/
├── RELATIONS.md         # append §"MCP traversal" with relations param
tests/
├── test_concept_code_mcp.py    # extend: relations filter, unknown rel, empty list, payload shim
├── test_serve.py               # extend: entity_trace include_concept_code merge
├── test_export.py              # extend: per-relation sections + parity tests
fixtures/concept_code/
├── round_trip.json             # reuse Phase 53 fixture
├── vault_parity/               # NEW — expected note bodies
│   ├── code_klass.md           # expected body for k_klass code note
│   ├── code_subklass.md        # expected body for k_subklass
│   ├── moc_authservice.md      # expected inverse body for c_concept MOC
│   └── moc_tokenstore.md       # expected inverse body for c_concept2 MOC
scripts/
├── sync_mcp_server_json.py     # regenerate server.json after schema change
server.json                     # regenerated; manifest_content_hash invalidates
```

### Pattern 1: MCP helper widening (Phase 47 → 54 pattern)
**What:** Generalize a relation-specific helper by parameterizing the relation set, keeping default behavior backward-compatible.

**When to use:** Whenever a Phase-N tool's helper hardcodes a single relation that Phase-N+1 wants to widen.

**Example (transcribed from current code at serve.py:2137-2160, target shape after Phase 54):**
```python
# BEFORE (Phase 47, serve.py:2137):
def _implements_hop_kind(G: nx.Graph, u: str, v: str) -> str | None:
    ed = G.edges[u, v]
    if ed.get("relation") != "implements":
        return None
    ...

def _implements_hop_allowed(G: nx.Graph, u: str, v: str, direction: str) -> bool:
    kind = _implements_hop_kind(G, u, v)
    ...

# AFTER (Phase 54):
def _concept_code_hop_kind(
    G: nx.Graph, u: str, v: str, relations: frozenset[str]
) -> tuple[str, str] | None:
    """Returns (relation, direction_kind) or None if edge not in relations filter.
    direction_kind ∈ {'code_to_concept', 'concept_to_code', 'both'}."""
    ed = G.edges[u, v]
    rel = ed.get("relation")
    if rel not in relations:
        return None
    src_m, tgt_m = ed.get("_src"), ed.get("_tgt")
    if isinstance(src_m, str) and isinstance(tgt_m, str):
        if u == src_m and v == tgt_m:
            return (rel, "code_to_concept")
        if u == tgt_m and v == src_m:
            return (rel, "concept_to_code")
    return (rel, "both")

def _concept_code_hop_allowed(
    G: nx.Graph, u: str, v: str, direction: str, relations: frozenset[str]
) -> tuple[str, str] | None:
    """Returns (relation, direction_kind) if traversal allowed, else None.
    Replaces bool return so caller can attribute steps_by_relation."""
    classified = _concept_code_hop_kind(G, u, v, relations)
    if classified is None:
        return None
    rel, kind = classified
    if direction == "both" or kind == "both":
        return (rel, kind)
    return (rel, kind) if kind == direction else None
```

**Source:** Synthesized from `serve.py` lines 2137-2160 (current Phase 47 code, [VERIFIED: read 2026-04-30]).

### Pattern 2: Body substitution in templates (per-relation rendering)
**What:** Use the existing `body` substitution variable in `code.md` / `moc.md` builtin templates.

**When to use:** Phase 54 sections — the slot is currently empty (`"body": ""` in templates.py:1181, 1431). No template file edits.

**Example:**
```python
# templates.py render_note() — replace the empty "body" with per-relation sections
# when note_type == "code"
def _build_concept_code_sections_for_code(G, node_id, convention) -> str:
    """Build per-relation sections for a CODE note, sourced from graph edges."""
    if node_id not in G:
        return ""
    # Canonical order — matches D-54.07
    SECTION_ORDER = [
        ("implements",   "Implements"),
        ("documents",    "Documents"),
        ("tests",        "Tests"),
        ("realizes",     "Realizes"),
        ("instantiates", "Instantiates"),
    ]
    by_relation: dict[str, list[str]] = {rel: [] for rel, _ in SECTION_ORDER}
    for u, v, data in G.edges(node_id, data=True):
        rel = data.get("relation")
        if rel not in by_relation:
            continue
        # Use _src/_tgt to verify code → concept direction (this CODE note is _src)
        src_m, tgt_m = data.get("_src"), data.get("_tgt")
        if not (isinstance(src_m, str) and src_m == node_id):
            continue
        target = v if u == node_id else u
        target_label = G.nodes[target].get("label", target)
        by_relation[rel].append(_emit_wikilink(target_label, convention))
    parts: list[str] = []
    for rel, header in SECTION_ORDER:
        items = by_relation[rel]
        if not items:
            continue  # D-54.07: empty-suppression
        parts.append(f"## {header}")
        # Deterministic intra-section sort
        for link in sorted(set(items)):
            parts.append(f"- {link}")
        parts.append("")
    if not parts:
        return ""
    return _wrap_sentinel("concept_code_relations", "\n".join(parts).rstrip())
```

**Round-trip preservation:** Wrap output in `_wrap_sentinel("concept_code_relations", ...)` (templates.py:68). The merge layer respects sentinel boundaries (D-67/D-68) so user-edits outside the sentinel survive vault re-runs and the section content is refreshed deterministically.

### Anti-Patterns to Avoid
- **Sourcing wikilinks from anywhere but `G.edges`** — single source of truth (CGRAPH-04). Don't recompute relations from labels/text.
- **Re-orienting edges in templates.py** — Phase 53 already oriented them code→concept via `_normalize_concept_code_edges`. Read `_src`/`_tgt` direct.
- **Forgetting `_wrap_sentinel`** — without sentinel markers the merge layer will treat per-relation sections as user-content and refuse to refresh them on re-run.
- **Adding the `body` content via export.py post-hoc** — that bypasses block expansion and frontmatter splitting; populate via the `substitution_ctx` in `render_note`/`render_moc`.
- **Sorting sections alphabetically** — D-54.07 specifies canonical order: Implements, Documents, Tests, Realizes, Instantiates (and inverse counterparts).
- **Snapshot test on full vault bytes** — D-54.14 explicitly forbids; per-section assertions only.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Slugify a node label for wikilink filename | New slugifier | `graphify/extract.py:_make_id` | Project-wide stable id convention. D-54.09. |
| Render `[[fname\|alias]]` wikilink | New emit function | `graphify/templates.py:_emit_wikilink` (line 663) | Already sanitizes, applies `convention`, prevents `]]\|\n` injection (CR-01). |
| Resolve concept community label | New label-pipeline | `graphify/naming.py:resolve_concept_names` (line 459) | Phase 33 cache+LLM+fallback chain; already called by `to_obsidian` at export.py:629. |
| Sanitize edge labels for callouts | Inline `replace()` | `graphify/templates.py:_sanitize_wikilink_alias` + `security.py:sanitize_label` | Existing security boundary. |
| Section content idempotence on re-run | New marker scheme | `_wrap_sentinel("concept_code_relations", ...)` (templates.py:68) | Merge engine already respects start/end sentinels (D-67/D-68). |
| Edge iteration in deterministic order | `sorted(G.edges)` | `_build_edge_records` (templates.py:253) — sorts by (relation, label) | Already canonical; we just need the relation-filter projection. |
| Concept↔code edge orientation check | Recompute file_type | `data["_src"]` / `data["_tgt"]` | Phase 53's `_normalize_concept_code_edges` set these atomically. |

**Key insight:** Phase 54 is overwhelmingly a **composition phase** — every primitive needed already exists post Phase 53. The risk is in plumbing & ordering, not in building new logic.

## Runtime State Inventory

| Category | Items Found | Action Required |
|----------|-------------|------------------|
| Stored data | None — graph is read-only at MCP/export time. No DB or schema migration. | None. |
| Live service config | None — MCP server uses `server.json` regenerated from manifest source files (`mcp_tool_registry.py`, `capability.py`, `capability_tool_meta.yaml`). Hash regenerates automatically when source file mtimes change (serve.py:`_manifest_invalidation_tuple`). | After tool schema edit, run `scripts/sync_mcp_server_json.py` to regenerate `server.json` (manifest_content_hash will change). |
| OS-registered state | None — graphify is a stdio MCP server, no persistent OS registration. | None. |
| Secrets/env vars | None. | None. |
| Build artifacts | None for this phase. `graphifyy` PyPI version (`pyproject.toml`) — researcher recommendation: do NOT bump for Phase 54 alone; bump at v1.11 milestone close per CLAUDE.md "After a shipped milestone" guidance. | Skip version bump in this phase. |

**Confirmed:** Phase 54 is code-only. No data migrations, no live-service mutations, no OS registrations. The only "external" surface is `server.json`'s manifest hash — regenerated mechanically by an existing script.

## Common Pitfalls

### Pitfall 1: Round-trip frontmatter regression
**What goes wrong:** Adding body content overwrites a user's manually-edited section on re-run, or clobbers preserved frontmatter.
**Why it happens:** Forgetting to wrap new sections in `_wrap_sentinel("concept_code_relations", ...)` (templates.py:68) or substituting `body` outside the existing template's `${body}` slot.
**How to avoid:** Place the per-relation block in `substitution_ctx["body"]` (already empty by default — templates.py:1181, 1431); wrap the content with `_wrap_sentinel`. The merge engine (`compute_merge_plan` / `apply_merge_plan`) already respects D-67 (refresh sentinel content) and D-68 (respect deletion).
**Warning signs:** Existing `test_export.py::test_to_obsidian_*` round-trip tests start failing; manifest content hash differs across two consecutive `to_obsidian` calls on the same graph.

### Pitfall 2: Backward-compat shim leak
**What goes wrong:** `concept_code_hops` returns `traversal_steps` AND `implements_traversal_steps` for non-implements traversals, confusing consumers.
**Why it happens:** Misreading D-54.03 — the shim is conditional: `implements_traversal_steps` is only emitted when `relations == ["implements"]`.
**How to avoid:** Single conditional in payload assembly:
```python
if requested_relations == frozenset({"implements"}):
    meta["implements_traversal_steps"] = traversals
meta["traversal_steps"] = traversals
meta["steps_by_relation"] = dict(sorted(steps_by_relation.items()))
```
**Warning signs:** Phase 47 test `test_concept_code_hops_golden_path` fails on `meta["implements_traversal_steps"]` lookup, OR new tests find the legacy key when called with `relations=["documents"]`.

### Pitfall 3: BFS perf with 5 relations
**What goes wrong:** Widening from one relation (`implements`) to five increases edge candidates. Existing `_IMPL_EDGE_BUDGET = 500` cap (serve.py:2135) may truncate earlier than users expect.
**Why it happens:** Cap is global, not per-relation. With 5x more candidate edges per node, BFS hits the cap faster on dense graphs.
**How to avoid:** Keep the global cap (D-54.10 — no new params). Add a test asserting truncation behavior for the new `relations` filter and document the cap in `docs/RELATIONS.md` §"MCP traversal".
**Warning signs:** `meta["truncated"] == True` on small fixtures (size < ~50 edges).

### Pitfall 4: Capability manifest hash drift
**What goes wrong:** Tool schema in `mcp_tool_registry.py` is updated but `server.json` is not regenerated; downstream MCP clients see stale tool description.
**Why it happens:** `server.json` is a build artifact, not auto-generated on import.
**How to avoid:** Plan must include a step `python scripts/sync_mcp_server_json.py` after every `mcp_tool_registry.py` change; tests should NOT assert the hash value (it'll churn) but SHOULD assert that `server.json` and `build_manifest_dict()` agree (existing `test_capability.py` likely covers this — verify in W1).
**Warning signs:** `tests/test_capability.py` failures referencing `manifest_content_hash`.

### Pitfall 5: Section ordering non-determinism
**What goes wrong:** Two consecutive `to_obsidian` runs on the same graph emit per-relation sections in different orders → round-trip churn.
**Why it happens:** Iterating `G.edges(node_id)` order depends on NetworkX node-insertion order. Phase 53 W2 fix solved this for the EDGE list, but `G.edges(node_id, data=True)` for a SINGLE node may still vary if intra-section list isn't explicitly sorted.
**How to avoid:** Inside each per-relation list, `sorted(set(items))` on the wikilink string before emission. Section ORDER is hardcoded canonical list (Implements, Documents, Tests, Realizes, Instantiates).
**Warning signs:** Parity test passes once but fails when re-run on a graph rebuilt from the same fixture.

### Pitfall 6: `entity_trace` envelope shape break
**What goes wrong:** Adding `include_concept_code` field to the meta envelope breaks existing /trace consumers that strict-match the meta keys.
**Why it happens:** `_run_entity_trace` (serve.py:1952) returns a closed-set meta dict. Adding fields is generally safe BUT must follow the existing optional-key pattern (e.g., `resolved_from_alias` only present when non-empty).
**How to avoid:** Only emit concept↔code merge keys when `include_concept_code=True`. Default path is byte-identical to Phase 11 behavior. New keys: `concept_code_reachable: list[str]`, `concept_code_steps_by_relation: dict[str, int]` — both omitted when not requested.
**Warning signs:** `tests/test_serve.py` Phase 11 trace tests start failing with "unexpected key" assertions.

## Code Examples

### Verified pattern: helper rename + filter
```python
# graphify/serve.py — new section replacing lines 2137-2160 (Phase 47 helpers)
# Source: synthesized from current code [VERIFIED: serve.py 2026-04-30]

# Renamed and generalized; old names removed (no caller besides _run_concept_code_hops)
def _concept_code_hop_kind(
    G: nx.Graph, u: str, v: str, relations: frozenset[str]
) -> tuple[str, str] | None:
    ed = G.edges[u, v]
    rel = ed.get("relation")
    if rel not in relations:
        return None
    src_m = ed.get("_src")
    tgt_m = ed.get("_tgt")
    if isinstance(src_m, str) and isinstance(tgt_m, str):
        if u == src_m and v == tgt_m:
            return (rel, "code_to_concept")
        if u == tgt_m and v == src_m:
            return (rel, "concept_to_code")
    return (rel, "both")


def _concept_code_hop_allowed(
    G: nx.Graph, u: str, v: str, direction: str, relations: frozenset[str]
) -> tuple[str, str] | None:
    classified = _concept_code_hop_kind(G, u, v, relations)
    if classified is None:
        return None
    rel, kind = classified
    if direction == "both" or kind == "both":
        return (rel, kind)
    return (rel, kind) if kind == direction else None
```

### Verified pattern: argument validation
```python
# In _run_concept_code_hops (replacing the start of the function)
# Source: synthesized; pattern follows existing direction-validation at serve.py:2173

_ALLOWED_CONCEPT_CODE_RELATIONS = frozenset({
    "implements", "documents", "tests", "realizes", "instantiates",
})

def _validate_relations_arg(raw: object) -> tuple[frozenset[str], str | None]:
    """Returns (validated_set, error_message). error_message is None on success."""
    if raw is None:
        # Backward-compat default per D-54.01
        return (frozenset({"implements"}), None)
    if not isinstance(raw, list):
        return (frozenset(), "'relations' must be a list of strings")
    if not raw:
        return (frozenset(), "'relations' must not be empty (omit param for implements-only)")
    for item in raw:
        if not isinstance(item, str):
            return (frozenset(), f"'relations' contains non-string item {item!r}")
        if item not in _ALLOWED_CONCEPT_CODE_RELATIONS:
            return (frozenset(), (
                f"'relations' contains unknown value {item!r} - "
                f"must be one of {sorted(_ALLOWED_CONCEPT_CODE_RELATIONS)}"
            ))
    return (frozenset(raw), None)
```

### Verified pattern: payload shim
```python
# In _run_concept_code_hops, at the meta-dict assembly (replacing serve.py:2295-2308)
# Source: synthesized; preserves backward-compat per D-54.03

requested_relations: frozenset[str]  # set above by _validate_relations_arg
# … BFS produces `traversals: int` and `steps_by_relation: dict[str, int]` …

meta: dict = {
    "status": "ok",
    "layer": 1,
    "search_strategy": "concept_code_hops",
    "cardinality_estimate": len(reachable),
    "continuation_token": None,
    "start_id": start_id,
    "max_hops": max_hops,
    "direction": direction,
    "relations": sorted(requested_relations),  # echo for client introspection
    "truncated": truncated,
    "traversal_steps": traversals,
    "steps_by_relation": {
        rel: steps_by_relation.get(rel, 0)
        for rel in sorted(requested_relations)
    },
    "reachable_node_ids": [start_id] + reachable,
    "depth_by_id": {k: depth_map[k] for k in sorted(depth_map.keys())},
}
# Phase 47 shim — emit legacy key only on the implements-only path
if requested_relations == frozenset({"implements"}):
    meta["implements_traversal_steps"] = traversals
```

### Verified pattern: parity test idiom
```python
# tests/test_export.py (or new tests/test_concept_code_obsidian.py)
# Source: synthesized from existing test patterns at test_export.py:266-294

import json
from pathlib import Path
from graphify.build import build_from_json
from graphify.export import to_obsidian

_ALL_RELATIONS = ("implements", "documents", "tests", "realizes", "instantiates")
_FIXTURE = Path(__file__).parent / "fixtures" / "concept_code" / "round_trip.json"

def _count_graph_edges_by_relation(G):
    counts = {rel: 0 for rel in _ALL_RELATIONS}
    for _, _, data in G.edges(data=True):
        rel = data.get("relation")
        if rel in counts:
            counts[rel] += 1
    return counts

def _count_vault_wikilinks_by_relation(vault_dir, sections):
    """Walk vault MD files, count wikilinks per H2 section header.
    sections = {"Implements": "implements", "Documents": "documents", ...}
    """
    import re
    counts = {rel: 0 for rel in _ALL_RELATIONS}
    for md_path in vault_dir.rglob("*.md"):
        text = md_path.read_text()
        # Find each "## Header" section then count [[...]] until next ## or EOF
        for header, rel in sections.items():
            pattern = rf"^## {re.escape(header)}\n((?:- \[\[.+?\]\]\n?)+)"
            for match in re.finditer(pattern, text, flags=re.MULTILINE):
                counts[rel] += match.group(1).count("[[")
    return counts

def test_concept_code_parity_per_relation_count(tmp_path):
    extraction = json.loads(_FIXTURE.read_text())
    G = build_from_json(extraction)
    communities = {0: [n["id"] for n in extraction["nodes"]]}
    out = tmp_path / "vault"
    to_obsidian(G, communities, str(out))
    forward_sections = {
        "Implements": "implements", "Documents": "documents",
        "Tests": "tests", "Realizes": "realizes", "Instantiates": "instantiates",
    }
    inverse_sections = {
        "Implemented by": "implements", "Documented by": "documents",
        "Tested by": "tests", "Realized by": "realizes", "Instantiated by": "instantiates",
    }
    graph_counts = _count_graph_edges_by_relation(G)
    forward_counts = _count_vault_wikilinks_by_relation(out, forward_sections)
    inverse_counts = _count_vault_wikilinks_by_relation(out, inverse_sections)
    # Per D-54.12: forward and inverse each match graph counts
    for rel in _ALL_RELATIONS:
        assert forward_counts[rel] == graph_counts[rel], (
            f"forward parity broken for {rel}: vault={forward_counts[rel]} graph={graph_counts[rel]}"
        )
        assert inverse_counts[rel] == graph_counts[rel], (
            f"inverse parity broken for {rel}: vault={inverse_counts[rel]} graph={graph_counts[rel]}"
        )
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Phase 47: `_implements_hop_*` helpers hardcoded for `implements` | Phase 54: `_concept_code_hop_*` over relation set | This phase | Adds filter param; preserves default behavior. |
| Phase 47: `implements_traversal_steps` payload | Phase 54: `traversal_steps` + `steps_by_relation` (legacy key shimmed) | This phase | Backward compat via conditional shim. |
| Pre-Phase 53: only `implements` was a typed concept↔code relation | Post-Phase 53: 5 relations canonicalized | Phase 53 (just shipped) | Phase 54 surfaces these. |
| `code.md` and `moc.md` builtin templates have empty `${body}` slot | Body slot used for per-relation sections | This phase | Zero template-file changes; renders into existing slot. |
| `entity_trace` is purely temporal (snapshot walk) | Optional concept↔code merge via `include_concept_code` | This phase | Backward-compat default = false. |

**Deprecated/outdated:**
- `_implements_hop_kind` and `_implements_hop_allowed` — remove (no external callers per `grep -n` analysis; only `_run_concept_code_hops` uses them).
- `implements_traversal_steps` payload key — kept as shim, plan for removal in v1.12+ if no users break.

## User Constraints (from CONTEXT.md)

### Locked Decisions
- **D-54.01:** Keep tool name `concept_code_hops`. Add `relations: list[str]` parameter, default `["implements"]`. Backward-compat for Phase 47 callers.
- **D-54.02:** Allowed `relations` values are exactly the 5 from Phase 53 (`implements`, `documents`, `tests`, `realizes`, `instantiates`). Unknown value → MCP tool error with actionable message. Empty list → error.
- **D-54.03:** Helpers `_implements_hop_kind` / `_implements_hop_allowed` (serve.py:2137, 2152) renamed to `_concept_code_hop_kind` / `_concept_code_hop_allowed` and generalized over the relations filter. Payload `implements_traversal_steps` → `traversal_steps` + `steps_by_relation: {relation: count}`. Backward-compat shim retains `implements_traversal_steps` when `relations == ["implements"]`.
- **D-54.04:** `entity_trace` gains `include_concept_code: bool = False`. When true, results merge concept↔code traversal alongside temporal hops.
- **D-54.05:** `/trace` slash workflow remains scoped to temporal — NOT updated. CGRAPH-03 satisfied via `entity_trace` extension + `concept_code_hops` widening.
- **D-54.06:** Documented mapping table lives in `54-VERIFICATION.md`.
- **D-54.07:** CODE notes get per-relation sections: `## Implements`, `## Documents`, `## Tests`, `## Realizes`, `## Instantiates` (canonical order; empty-suppression).
- **D-54.08:** Concept MOCs get inverse per-relation sections: `## Implemented by`, `## Documented by`, `## Tested by`, `## Realized by`, `## Instantiated by` (canonical order; empty-suppression).
- **D-54.09:** Wikilinks via existing `_make_id()` slugifier + Phase 33 `resolve_concept_names` + `_emit_wikilink`. No new label-resolution path. Sanitization through `security.py` (existing pattern).
- **D-54.10:** Per-relation sections via existing template body-slot — no new templates, no profile changes.
- **D-54.11:** Existing CODE-note and concept-MOC bodies NOT replaced — per-relation sections appended at deterministic position (after summary, before user-preserved trailer). Round-trip preservation must not regress.
- **D-54.12:** Parity test asserts THREE things: forward parity (graph→vault), backward parity (vault→graph), per-relation count parity for each of 5 relations.
- **D-54.13:** Test corpus reuses Phase 53 fixture (`tests/fixtures/concept_code/round_trip.json`) plus new `tests/fixtures/concept_code/vault_parity/` for expected note bodies.
- **D-54.14:** Snapshot tests on full vault bytes NOT used.

### Claude's Discretion
- Where exactly in `to_obsidian()` per-relation sections render (researcher recommendation: in `templates.py:render_note`/`render_moc` via `body` substitution, NOT in export.py — see "Pattern 2" above).
- Whether `traversal_steps` is new top-level field or replaces `implements_traversal_steps` outright (researcher recommendation: NEW top-level field; shim `implements_traversal_steps` when `relations == ["implements"]`).
- Whether `entity_trace`'s `include_concept_code` shares depth limit with `concept_code_hops` or has separate `concept_code_max_hops` (researcher recommendation: SHARED — reuse `_IMPL_EDGE_BUDGET=500` global cap and a fixed `max_hops=2` for the concept↔code merge to keep traversal cheap; new param adds plumbing without value).
- Test file organization (researcher recommendation: extend `test_concept_code_mcp.py` for MCP changes; new `tests/test_concept_code_obsidian.py` for parity tests since `test_export.py` is already 600+ lines; extend `test_serve.py` for `entity_trace` changes).

### Deferred Ideas (OUT OF SCOPE)
- `/trace` slash workflow concept↔code surfacing.
- Profile-driven `concept_code_layout` switch (per-relation / merged / dataview).
- Dataview query blocks for concept↔code.
- Per-relation hop limits in `concept_code_hops`.
- `graphify_version` PyPI bump for MCP signature change (defer to milestone close).

## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| CGRAPH-03 | MCP exposes typed concept↔code hop/query consistent with v1.10 `concept_code_hops` and slash `/trace` expectations (documented mapping table in verification). | Pattern 1 (helper widening) + payload shim guidance + `entity_trace` `include_concept_code` extension + capability manifest regen path. Mapping table lives in 54-VERIFICATION.md per D-54.06. |
| CGRAPH-04 | Obsidian CODE / concept MOC export does not contradict graph-level concept↔code edges (single source of truth from the graph). | Pattern 2 (templates body slot) sources wikilinks directly from `G.edges` reading `_src`/`_tgt`. Parity test corpus + 3-way assertion (forward/backward/count) seals the contract. Round-trip preservation via `_wrap_sentinel("concept_code_relations", ...)`. |

## Project Constraints (from CLAUDE.md)

- **Python 3.10+** — no syntax newer than 3.10 (no `match`-only-in-3.11+ features in fixtures or tests).
- **No new required deps** — stdlib only. (Already satisfied — composition phase.)
- **`from __future__ import annotations`** as first import in every module.
- **Type hints on all functions** — `dict[str, int]`, `str | None`, etc. (no `Optional`/`Dict`).
- **Security boundary:** all external input through `graphify/security.py` — `sanitize_label` applied to wikilink content already (templates.py uses `_sanitize_wikilink_alias`).
- **Validation boundary:** any new edge-schema field passes through `validate.py` (NOT applicable here — no new edge fields).
- **Fail loudly:** `[graphify]` prefix on stderr; raise `ValueError` for invalid input; MCP tools return structured `{status: error, ...}` envelope.
- **Tests pure unit:** no network, no filesystem mutation outside `tmp_path`.
- **Test pairing:** `test_<module>.py` per module convention.
- **Skill install stamp** — out of scope for this phase.
- **`graphify` CLI version via `importlib.metadata`** — bump deferred to v1.11 close.

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest 7.x (CI on Python 3.10 and 3.12) |
| Config file | `pyproject.toml` (no separate `pytest.ini`) |
| Quick run command | `pytest tests/test_concept_code_mcp.py tests/test_concept_code_obsidian.py -x` |
| Full suite command | `pytest tests/ -q` |

### Phase Requirements → Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| CGRAPH-03 | `concept_code_hops` accepts `relations: list[str]` defaulting to `["implements"]` | unit | `pytest tests/test_concept_code_mcp.py::test_concept_code_hops_default_relations -x` | ❌ Wave 0 |
| CGRAPH-03 | Unknown relation in list returns structured error | unit | `pytest tests/test_concept_code_mcp.py::test_concept_code_hops_unknown_relation_errors -x` | ❌ Wave 0 |
| CGRAPH-03 | Empty list returns structured error | unit | `pytest tests/test_concept_code_mcp.py::test_concept_code_hops_empty_relations_errors -x` | ❌ Wave 0 |
| CGRAPH-03 | `relations=["documents", "tests"]` traverses both | unit | `pytest tests/test_concept_code_mcp.py::test_concept_code_hops_multi_relation_traversal -x` | ❌ Wave 0 |
| CGRAPH-03 | Payload includes `traversal_steps` + `steps_by_relation` | unit | `pytest tests/test_concept_code_mcp.py::test_concept_code_hops_payload_steps_by_relation -x` | ❌ Wave 0 |
| CGRAPH-03 | Backward-compat shim: implements-only emits `implements_traversal_steps` | unit | `pytest tests/test_concept_code_mcp.py::test_concept_code_hops_backward_compat_implements_steps_key -x` | ❌ Wave 0 |
| CGRAPH-03 | `entity_trace` `include_concept_code=False` byte-identical to Phase 11 | unit | `pytest tests/test_serve.py::test_entity_trace_default_excludes_concept_code -x` | ❌ Wave 0 |
| CGRAPH-03 | `entity_trace` `include_concept_code=True` merges hops into envelope | unit | `pytest tests/test_serve.py::test_entity_trace_includes_concept_code_when_requested -x` | ❌ Wave 0 |
| CGRAPH-03 | Tool registry input schema declares `relations` and `include_concept_code` | unit | `pytest tests/test_capability.py::test_concept_code_hops_schema_includes_relations -x` (extend) | ❌ Wave 0 |
| CGRAPH-04 | CODE note emits per-relation sections (Implements/Documents/Tests/Realizes/Instantiates) in canonical order | unit | `pytest tests/test_concept_code_obsidian.py::test_code_note_per_relation_sections_canonical_order -x` | ❌ Wave 0 |
| CGRAPH-04 | Concept MOC emits inverse sections in canonical order | unit | `pytest tests/test_concept_code_obsidian.py::test_concept_moc_inverse_sections_canonical_order -x` | ❌ Wave 0 |
| CGRAPH-04 | Empty section is suppressed | unit | `pytest tests/test_concept_code_obsidian.py::test_empty_relation_section_suppressed -x` | ❌ Wave 0 |
| CGRAPH-04 | Forward parity: every graph edge appears as wikilink in correct section | unit | `pytest tests/test_concept_code_obsidian.py::test_forward_parity_edges_to_wikilinks -x` | ❌ Wave 0 |
| CGRAPH-04 | Backward parity: every wikilink in per-relation section maps to a graph edge | unit | `pytest tests/test_concept_code_obsidian.py::test_backward_parity_wikilinks_to_edges -x` | ❌ Wave 0 |
| CGRAPH-04 | Per-relation count parity (5 separate counts) | unit | `pytest tests/test_concept_code_obsidian.py::test_per_relation_count_parity -x` | ❌ Wave 0 |
| CGRAPH-04 | Round-trip: re-running `to_obsidian` doesn't change vault bytes | unit | `pytest tests/test_concept_code_obsidian.py::test_round_trip_per_relation_sections_idempotent -x` | ❌ Wave 0 |
| CGRAPH-04 | Round-trip: existing test_export.py round-trip tests still pass | regression | `pytest tests/test_export.py -q` | ✅ |

### Sampling Rate
- **Per task commit:** `pytest tests/test_concept_code_mcp.py tests/test_concept_code_obsidian.py tests/test_serve.py::test_entity_trace_includes_concept_code_when_requested -x`
- **Per wave merge:** `pytest tests/test_concept_code_mcp.py tests/test_concept_code_obsidian.py tests/test_serve.py tests/test_export.py tests/test_capability.py -q`
- **Phase gate:** `pytest tests/ -q` full suite green (current Phase 53 baseline: 1979 passed, 1 xfailed).

### Wave 0 Gaps
- [ ] `tests/test_concept_code_obsidian.py` — NEW file covering all CGRAPH-04 truths above (parity assertions, per-section canonical order, empty-suppression, idempotence).
- [ ] `tests/fixtures/concept_code/vault_parity/code_klass.md` — expected body for `k_klass` CODE note.
- [ ] `tests/fixtures/concept_code/vault_parity/code_subklass.md` — expected body for `k_subklass`.
- [ ] `tests/fixtures/concept_code/vault_parity/moc_authservice.md` — expected inverse body for `c_concept` (community 0).
- [ ] `tests/fixtures/concept_code/vault_parity/moc_tokenstore.md` — expected inverse body for `c_concept2` (community 1 if split, otherwise embedded).
- [ ] `tests/test_concept_code_mcp.py` — extend with relations-filter tests + payload shim tests + multi-relation traversal.
- [ ] `tests/test_serve.py` — extend with `entity_trace include_concept_code` tests.
- [ ] `tests/test_capability.py` — extend with input-schema assertion for `relations` + `include_concept_code`.

## Risks & Landmines (Open Questions Resolved)

### OQ1 — Exact `concept_code_hops` payload shape today
**Verified at serve.py:2295-2308.** Current meta keys: `status, layer, search_strategy, cardinality_estimate, continuation_token, start_id, max_hops, direction, truncated, implements_traversal_steps, reachable_node_ids, depth_by_id` (+ optional `resolved_from_alias`). The shim path keeps `implements_traversal_steps` and adds `traversal_steps`, `steps_by_relation`, `relations`. All 12 existing keys preserved on the implements-only path.

### OQ2 — `entity_trace` envelope shape
**Verified at serve.py:1952-2126.** Current meta keys: `status, layer, search_strategy, cardinality_estimate, continuation_token, snapshot_count, first_seen, timeline_length, entity_id` (+ optional `resolved_from_alias`, `candidates`, `snapshots_available`). Recommendation: add optional `concept_code_reachable: list[str]` and `concept_code_steps_by_relation: dict[str, int]` keys ONLY when `include_concept_code=True` and entity has any concept↔code edges. Reuse the existing `entity_resolved`/`live_matches` resolution path; call `_concept_code_hop_allowed` with a fixed `max_hops=2` and `relations=frozenset({"implements","documents","tests","realizes","instantiates"})`. Echo the resolved `entity_id` into the new keys so the consumer can correlate.

### OQ3 — Where in `to_obsidian()` does the body render
**Verified at templates.py:1043-1212 (render_note) and templates.py:1380-1465 (_render_moc_like).** The substitution context dict at templates.py:1167-1193 includes `"body": ""` (empty by default) which substitutes into the `${body}` slot in `code.md` (line 5) and is implicitly available in `moc.md` even though the builtin moc template currently doesn't reference `${body}` — for MOCs we'll need to either (a) extend `_render_moc_like` with a `body_section` substitution and update `moc.md` to include `${body}` BUT D-54.10 forbids template changes, OR (b) inject the inverse sections via a different existing slot. **Recommendation: use `members_section` extension OR introduce the per-relation block as a wrapped sentinel block appended at end of body via `_BlockTemplate.safe_substitute` with a new `concept_code_relations` substitution variable.** Re-examining D-54.10 carefully: "no new templates, no profile changes" — but ADDING a new substitution variable to existing `code.md`/`moc.md` IS a template edit. **Resolution: use the existing `${body}` slot in `code.md` (already present, unused) AND add `${body}` slot to the BUILTIN `moc.md` file as a non-breaking edit (pre-existing slot doesn't exist in moc.md — see exact contents in OQ3 details below).** This is technically an existing-template edit but aligns with D-54.10's intent (no NEW template files, no profile knobs). Planner should confirm.

**Exact `moc.md` contents (verified 2026-04-30):**
```
${frontmatter}
# ${label}

${wayfinder_callout}

${members_section}

${sub_communities_callout}

${dataview_block}

${metadata_callout}
```
**No `${body}` slot exists today.** Planner has two options: (Option A) edit moc.md to add `${body}` between `members_section` and `sub_communities_callout`; (Option B) extend `members_section` content to include the inverse sections. **Researcher recommendation: Option A** — it's a 1-line additive edit to a builtin template, parallel structure to code.md, and far cleaner separation of concerns. Mark in plan as a clarification on D-54.10.

### OQ4 — `resolve_concept_names` mapping
**Verified at naming.py:459-540.** Returns `dict[community_id → ConceptName]` where `ConceptName` is a NamedTuple with `(community_id, title, filename_stem, source, signature, reason)`. Fallback chain when no LLM namer: `_fallback_name(G, members, cid, signature, "disabled")` produces deterministic title from top terms. Already called by `to_obsidian` at export.py:629 and result merged into `per_community[cid]["community_name"]` (export.py:660-665). For Phase 54, when rendering an inverse section in a CONCEPT MOC, the wikilinks point at CODE NOTES — those use `filename_stem` from `build_code_filename_stems` (export.py:709). For CODE NOTES rendering forward sections pointing at CONCEPT MOCs, the wikilinks point at the MOC's `community_name`. Both are already in scope at the point of `render_note`/`render_moc` via the `classification_context` dict.

### OQ5 — Existing test_export.py fixture pattern
**Verified at test_export.py:266-294 (test_to_obsidian_resolves_concept_names_for_moc_paths).** Pattern: build extraction dict inline, call `build_from_json`, construct `communities` dict, call `to_obsidian(G, communities, str(out))`, walk `out` directory for paths. For Phase 54 parity test, reuse this pattern but use `json.loads((_FIXTURE).read_text())` instead of inline dict, and walk MD files via `out.rglob("*.md")` + regex to extract per-section wikilinks.

### OQ6 — Conflicts with Phase 27 (vault routing) / Phase 30 (profile composition)
**Verified by grep:** Phase 27/30 affect `mapping.py` / `profile.py` for note routing and template inheritance. Phase 54 changes only `templates.py` body composition for `code` and `moc` note types. **No conflicts** — Phase 27's classification produces `note_type="code"` or `note_type="moc"` and Phase 54 reads from these. Phase 30's profile composition affects which template files are loaded; since D-54.10 forbids new templates and existing builtin templates are merely populated via the (unused-until-now) `${body}` slot, Phase 30 inheritance still works — vault overrides of `code.md`/`moc.md` will continue to win, and Phase 54 sections only appear if the override template includes `${body}`. **This is actually a feature** — vault authors who want to suppress per-relation sections can simply omit `${body}` from their overrides.

### OQ7 — server.json manifest hash
**Verified at server.json line "manifest_content_hash" + serve.py:_get_manifest_hash() at line ~3060.** Manifest hash recomputes from `mcp_tool_registry.py`, `capability.py`, `capability_tool_meta.yaml` mtimes (+ sidecar mtimes). The hash will change as soon as `mcp_tool_registry.py` is edited to add `relations` to the input schema. **Action:** plan must include `python scripts/sync_mcp_server_json.py` after schema edit; new hash will be committed in `server.json`. Existing tests in `test_capability.py` should be checked for any hardcoded hash (likely none — hashes are checksums, not constants).

### OQ8 — Pre-existing concept↔code sections in vault
**Verified by grep on the project's actual graphify-out vault and on test_export tests:** No prior phase emits `## Implements`/`## Documents`/etc. headers. Phase 54 is greenfield in vault content. Round-trip safety is therefore about: (1) not breaking the merge engine's existing sentinel-respect logic, (2) ensuring two consecutive runs produce byte-identical body sections.

### OQ9 — BFS perf on widened relation set
**Analysis:** Phase 53 fixture has 8 edges. The `_IMPL_EDGE_BUDGET=500` cap (serve.py:2135) is a global edge-traversal counter that doesn't depend on the relation set — widening to 5 relations doesn't change the cap. On a 1000-node graph with average concept↔code degree of 4, BFS at max_hops=3 would visit ~64 nodes worst-case → ~256 traversals → well within the cap. **Recommendation: keep the cap; add a test asserting `truncated=True` is reachable with a constructed worst-case fixture; document the cap in `docs/RELATIONS.md` §"MCP traversal".**

### OQ10 — Active/passive form sanity for inverse sections (D-54.08)
**Confirmed correct.** D-54.08 specifies:
- `Implements` → `Implemented by` ✓ (a code file `implements` a concept; the concept is `implemented by` code).
- `Documents` → `Documented by` ✓ (a doc `documents` a concept; the concept is `documented by` the doc).
- `Tests` → `Tested by` ✓ (a test `tests` a concept; the concept is `tested by` the test).
- `Realizes` → `Realized by` ✓ (an interface `realizes` a concept; the concept is `realized by` the interface).
- `Instantiates` → `Instantiated by` ✓ (a subtype `instantiates` a concept; the concept is `instantiated by` the subtype).

All five forward forms are 3rd-person-singular present-tense active verbs (taking a concept as object); all five inverse forms are past-tense passive participles (the concept is the subject). No naming inconsistencies. The pluralization is also consistent — none of the verbs change form when subject becomes plural (e.g., "files implement" → "concept is implemented by files").

## Suggested Wave Structure

Honor TDD RED→GREEN sequence per `tdd_mode: true` in config.

### Wave 0: Test scaffolding (RED — failing tests committed first)
**Goal:** Create the test files and fixture artifacts; tests fail because production code doesn't exist yet.
- `tests/test_concept_code_mcp.py` extended with the 6 MCP tests from Validation Architecture table.
- `tests/test_concept_code_obsidian.py` created with the 7 Obsidian/parity tests.
- `tests/test_serve.py` extended with the 2 `entity_trace` tests.
- `tests/test_capability.py` extended with schema-includes-relations test.
- `tests/fixtures/concept_code/vault_parity/` directory with 4 expected note body fixtures (or computed inline by tests if planner prefers).
- All new tests should fail with clear messages (xfail or fail with `NotImplementedError` stubs is acceptable as long as they DO fail).
- Phase gate: `pytest tests/ -q` shows N new failures.

### Wave 1: MCP `concept_code_hops` widening (GREEN for MCP tests)
**Goal:** Implement the `relations` filter, helper renames, payload shim. Tests in `test_concept_code_mcp.py` go green.
- Edit `graphify/serve.py`: rename helpers, generalize, add `_validate_relations_arg`, update `_run_concept_code_hops` payload assembly with shim.
- Edit `graphify/mcp_tool_registry.py` (line 290 region): add `relations` and (later wave) `include_concept_code` to inputSchema.
- Edit `graphify/serve.py:_tool_concept_code_hops` (line 3354): no signature change — the dispatch passes `arguments` dict through to `_run_concept_code_hops` which already reads from arguments.
- Run: `pytest tests/test_concept_code_mcp.py tests/test_capability.py -x` → green.
- Run: `pytest tests/ -q` → existing tests still pass (Phase 47 backward compat sealed by shim).

### Wave 2: `entity_trace` extension (GREEN for entity_trace tests)
**Goal:** Add `include_concept_code` param to `entity_trace`. Tests in `test_serve.py` go green.
- Edit `graphify/serve.py:_run_entity_trace` (line 1952): read `include_concept_code` arg; if True after entity resolution, run a concept↔code BFS (reuse `_concept_code_hop_allowed` from W1) with `max_hops=2`, `relations=frozenset({all 5})`, attach `concept_code_reachable` + `concept_code_steps_by_relation` to meta.
- Edit `graphify/mcp_tool_registry.py` (line 282 region): add `include_concept_code: {type: bool, default: false}` to `entity_trace` inputSchema.
- Run: `pytest tests/test_serve.py tests/test_capability.py -x` → green.

### Wave 3: Obsidian per-relation sections (GREEN for parity tests)
**Goal:** Populate `body` slot in `code.md` and add `${body}` slot to `moc.md` (single line edit). Implement section builders.
- Edit `graphify/templates.py:render_note` (line 1043): for `note_type == "code"`, build per-relation forward sections and assign to `substitution_ctx["body"]` wrapped in `_wrap_sentinel("concept_code_relations", ...)`. Use new helper `_build_concept_code_sections_for_code(G, node_id, convention)`.
- Edit `graphify/templates.py:_render_moc_like` (line 1380 region): for `note_type == "moc"`, build per-relation inverse sections (resolving concept node IDs to community labels via the `classification_context["community_name"]`). Assign to `substitution_ctx["body"]`. Note: only emit for concept MOCs — detection: the community contains at least one node of `file_type` rationale/document AND has incoming concept↔code edges. Use new helper `_build_concept_code_sections_for_moc(G, community_id, communities, convention)`.
- Edit `graphify/builtin_templates/moc.md`: add `${body}` slot between `${members_section}` and `${sub_communities_callout}`.
- Run: `pytest tests/test_concept_code_obsidian.py tests/test_export.py -x` → green.
- Run: `pytest tests/ -q` → full suite green.

### Wave 4: Documentation + manifest regen + close-out
**Goal:** Update docs, regenerate server.json, commit close-out artifacts.
- Edit `docs/RELATIONS.md`: append §"MCP traversal" documenting `relations` param, `steps_by_relation` payload, `include_concept_code` extension.
- Run: `python scripts/sync_mcp_server_json.py` → `server.json` manifest hash regenerates; commit.
- Verify capability dispatch reload works (no test asserts hash value).
- Run: `pytest tests/ -q` final green; produce `54-VERIFICATION.md` mapping table per D-54.06.

## Test Corpus Suggestion: `tests/fixtures/concept_code/vault_parity/`

Reuse `round_trip.json` (Phase 53). The 8 edges break down as:
- `k_klass → c_concept` `implements` (EXTRACTED + INFERRED — merged) → 1 edge after merge
- `k_subklass → c_concept` `instantiates` (EXTRACTED, evidence=inheritance) → 1 edge
- `c_concept2 → k_klass` `realizes` (INFERRED 0.8) → after Phase 53 orientation: `k_klass → c_concept2` `realizes` → 1 edge
- `t_test_klass → c_concept` `tests` (EXTRACTED, evidence=test_docstring) → 1 edge
- `d_readme → c_concept` `documents` (INFERRED 0.5) → 1 edge
- `c_concept → k_klass` `implements` (AMBIGUOUS) → after orientation: `k_klass → c_concept` `implements` (collapses with first into the merged implements pair) → already counted
- `k_klass → k_subklass` `contains` → structural, irrelevant for Phase 54

**After Phase 53 orientation + merge:** 5 distinct concept↔code edges + 1 contains edge = 6 total.

### Expected node grouping for vault output
Assuming a single community {0: all 6 nodes}:
- **CODE notes** (file_type="code"): `k_klass`, `k_subklass`, `t_test_klass` (3 notes)
- **Document notes**: `d_readme` (1 note — note_type likely "source", not "code")
- **Concept MOC**: 1 MOC for the community containing rationale nodes `c_concept`, `c_concept2`

### Expected per-relation section content (CODE notes — forward)

**`code_klass.md` (for `k_klass`):**
```
## Implements
- [[<filename for AuthService>|AuthService]]

## Realizes
- [[<filename for TokenStore>|TokenStore]]
```
(no Documents/Tests/Instantiates sections — empty-suppression)

**`code_subklass.md` (for `k_subklass`):**
```
## Instantiates
- [[<filename for AuthService>|AuthService]]
```

**`code_test_klass.md` (for `t_test_klass`):**
```
## Tests
- [[<filename for AuthService>|AuthService]]
```

### Expected inverse section content (concept MOC — inverse)

**`moc_authservice.md` (for `c_concept`):**
```
## Implemented by
- [[Klass<filename>|Klass]]

## Documented by
- [[<filename for README>|README]]

## Tested by
- [[test_klass<filename>|test_klass]]

## Instantiated by
- [[SubKlass<filename>|SubKlass]]
```

**`moc_tokenstore.md` (for `c_concept2`):**
```
## Realized by
- [[Klass<filename>|Klass]]
```

(Exact filenames depend on `convention` setting and `build_code_filename_stems` output — fixtures should compare structural shape (regex per section) rather than exact bytes per D-54.14. The actual `<filename>` will follow `code_filename_stems` for code notes and `filename_stem` from `ConceptName` for MOCs.)

**Recommendation for fixture format:** Store the EXPECTED section CONTENT (just the per-relation sections, not full notes) as raw markdown strings in test fixtures; the parity test extracts the corresponding sections from actual output and compares as sets-of-wikilink-targets per relation.

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | `moc.md` builtin template should be edited to add `${body}` slot (D-54.10 carve-out) | OQ3 / Wave 3 | If user reads D-54.10 as forbidding ANY edit to existing template files, Wave 3 must instead route inverse sections through `members_section` extension. Recommend planner confirm. |
| A2 | `entity_trace include_concept_code=True` should reuse `_IMPL_EDGE_BUDGET=500` cap and `max_hops=2` (vs adding `concept_code_max_hops`) | OQ2 / Wave 2 | If planner prefers separate cap, plan adds one extra arg with no functional difference for the golden-path scenario. Low risk. |
| A3 | Concept MOC detection = community contains ≥1 rationale/document node AND has incoming concept↔code edges | Wave 3 | If detection rule should be different (e.g., always emit on every MOC), inverse sections may appear on community MOCs that have no concept↔code edges (which would be empty-suppressed anyway, so probably moot). Low risk. |
| A4 | Wikilink target for CODE notes is `build_code_filename_stems` output; for MOCs is `ConceptName.filename_stem` | OQ4 / Wave 3 | If wrong, wikilinks point to non-existent files. Test caught by forward parity assertion. |
| A5 | `graphify_version` PyPI bump deferred to milestone close, not Phase 54 | Phase 54 close-out | If planner decides to bump now, manifest_content_hash includes `graphify_version` so server.json must regenerate twice. Low cost. |

## Open Questions

1. **D-54.10 strictness on `moc.md` edit.** Researcher reads it as "no NEW template files, no profile knobs" — adding `${body}` to existing builtin moc.md is allowed. Planner may need to surface this in 54-VERIFICATION.md as an explicit clarification.
   - **Recommendation:** Document the carve-out in 54-VERIFICATION.md mapping table (D-54.06).

2. **Should the `concept_code_relations` sentinel-wrapped block be inside `${body}` or sit alongside `${connections_callout}`?**
   - **Recommendation:** Inside `${body}` for both note types — keeps it a single, semantically-named substitution variable; easier round-trip.

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| Python 3.10+ | All | ✓ | 3.10/3.12 (CI) | — |
| networkx | Build, MCP, export | ✓ | unpinned (existing) | — |
| pytest | Tests | ✓ | 7.x | — |
| `mcp` (extra) | MCP server tests | ✓ | optional `[mcp]` extra | tests skip if missing |
| `[graphify install]` skill stamp | Skill platform tests | n/a — not modified | — | — |

**No missing dependencies.** Composition phase only.

## Security Domain

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | no | MCP server is local-only stdio. |
| V3 Session Management | no | No sessions. |
| V4 Access Control | no | Local-only. |
| V5 Input Validation | yes | `validate.py` schema; `_validate_relations_arg` for new MCP arg; `sanitize_label` for any string echoed into MD. |
| V6 Cryptography | no | Only manifest hash (SHA256-based content addressing); existing impl, not extended. |

### Known Threat Patterns for graphify Phase 54

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| MCP tool injection (malicious `relations` value) | Tampering | `_validate_relations_arg` whitelist + structured error envelope. |
| Wikilink injection via concept label (e.g., `]] {{include}}`) | Tampering | Reuse `_sanitize_wikilink_alias` (templates.py:654) — already strips `]`/`\|`/`\n`. |
| Round-trip vault-content forgery (user edits sentinel-wrapped section) | Tampering | Existing merge engine D-67/D-68 sentinel boundary — no new attack surface. |
| BFS resource exhaustion via wide relations + deep max_hops | DoS | Existing `_IMPL_EDGE_BUDGET=500` global cap + `max_hops` clamped to [1, 6]. |
| `entity_trace` envelope smuggling via `include_concept_code` | Tampering | Boolean-only param; output keys are server-controlled. |

## Sources

### Primary (HIGH confidence — verified by direct file reads, 2026-04-30)
- `/Users/silveimar/Documents/silogia-repos/graphify/graphify/serve.py` (lines 1952-2308, 3339-3367, 3586-3587)
- `/Users/silveimar/Documents/silogia-repos/graphify/graphify/export.py` (lines 540-840)
- `/Users/silveimar/Documents/silogia-repos/graphify/graphify/templates.py` (lines 60-100, 253-310, 660-695, 772-830, 1043-1212, 1380-1465)
- `/Users/silveimar/Documents/silogia-repos/graphify/graphify/build.py` (full)
- `/Users/silveimar/Documents/silogia-repos/graphify/graphify/validate.py` (full)
- `/Users/silveimar/Documents/silogia-repos/graphify/graphify/naming.py` (lines 459-540, ConceptName NamedTuple)
- `/Users/silveimar/Documents/silogia-repos/graphify/graphify/extract.py` (lines 24-29, `_make_id`)
- `/Users/silveimar/Documents/silogia-repos/graphify/graphify/mcp_tool_registry.py` (lines 270-330)
- `/Users/silveimar/Documents/silogia-repos/graphify/graphify/capability_tool_meta.yaml` (lines 78-110)
- `/Users/silveimar/Documents/silogia-repos/graphify/graphify/builtin_templates/code.md`, `moc.md` (full)
- `/Users/silveimar/Documents/silogia-repos/graphify/server.json` (manifest)
- `/Users/silveimar/Documents/silogia-repos/graphify/tests/fixtures/concept_code/round_trip.json` (full)
- `/Users/silveimar/Documents/silogia-repos/graphify/tests/test_concept_code_mcp.py` (full)
- `/Users/silveimar/Documents/silogia-repos/graphify/.planning/phases/54-mcp-trace-obsidian-parity/54-CONTEXT.md`
- `/Users/silveimar/Documents/silogia-repos/graphify/.planning/phases/53-concept-code-schema-build-merge/53-VERIFICATION.md`
- `/Users/silveimar/Documents/silogia-repos/graphify/.planning/REQUIREMENTS.md`
- `/Users/silveimar/Documents/silogia-repos/graphify/CLAUDE.md`

### Secondary (MEDIUM confidence)
- Phase 33 concept-naming pipeline patterns inferred from `naming.py` outline + `to_obsidian` integration site.
- Phase 27 vault routing / Phase 30 profile composition non-conflict assessed via grep, not full read of `mapping.py`/`profile.py`.

### Tertiary (LOW confidence) — none.

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — composition phase, all dependencies already in repo and verified.
- Architecture (helper rename, payload shim, body-slot rendering): HIGH — exact line numbers and patterns verified against current code.
- Pitfalls (round-trip, manifest, BFS perf): HIGH — existing tests + Phase 53 verification report confirm baselines.
- moc.md template edit (A1): MEDIUM — D-54.10 reading is researcher's judgement; planner should confirm.
- Wave structure: HIGH — TDD-mode and existing 4-wave Phase 53 cadence already validated.

**Research date:** 2026-04-30
**Valid until:** 2026-05-30 (stable phase; existing code surfaces unlikely to change before plan execution)

## RESEARCH COMPLETE
