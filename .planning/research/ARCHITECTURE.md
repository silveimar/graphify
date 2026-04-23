# Architecture Research

**Project:** graphify v1.5 — Diagram Intelligence & Excalidraw Bridge
**Researched:** 2026-04-22
**Focus:** How do v1.5 diagram features integrate into the existing pipeline? What new modules are needed and what existing modules must change?

---

## Greenfield Confirmation

v1.5 diagram features are fully greenfield — no existing code references Excalidraw, diagram generation, or seed selection. The integration points are clean. The primary constraint is that `profile.py` must expand `_VALID_TOP_LEVEL_KEYS` to include diagram-related config keys, and this must happen atomically with any `diagram_types` additions.

---

## New Modules

### `graphify/diagram.py`
Primary new module. Responsible for:
- Accepting a subgraph (`nx.Graph`) and a diagram type string
- Running the appropriate layout algorithm
- Producing a valid Excalidraw JSON scene dict
- Writing the `.excalidraw.md` file with correct frontmatter and `## Drawing` block
- Validating element IDs are `sha256(node_id.encode())[:16]` hex

This module has no dependencies outside stdlib + networkx. It does NOT call the MCP server — that is handled by `serve.py` / `mcp_tool_registry`.

### `graphify/seed.py`
Seed selection module. Responsible for:
- Accepting the full graph and analysis results
- Selecting up to `max_seeds=20` seed nodes using configurable strategies: god nodes, community hubs, user-specified
- Expanding subgraphs around each seed (BFS to configurable depth, default 2)
- Returning a list of `(seed_node_id, subgraph, diagram_type_hint)` tuples

Hard cap: `max_seeds=20`. Exceeding this cap must raise a warning and truncate, not silently generate 100+ diagrams.

---

## Modified Modules

### `graphify/analyze.py`
Gains `diagram_hints(G, communities) -> dict[int, str]` function. Maps community_id → recommended diagram type based on topology:
- Linear chains (avg degree < 1.5, diameter > 5) → `sequence`
- Dense clusters (density > 0.4) → `concept_map`
- Layered DAGs (few back-edges) → `architecture`
- Default → `dependency_graph`

This function is called before `seed.py` so seeds can be type-annotated.

### `graphify/profile.py`
`_VALID_TOP_LEVEL_KEYS` must be expanded to include diagram config keys:
- `diagrams` (top-level section)
- `diagram_types` (list of enabled types)
- `max_seeds` (int, default 20)
- `diagrams_folder` (vault-relative path)
- `diagram_index_note` (filename for the index note)

**Atomic constraint:** Any addition to `diagram_types` config handling must be accompanied by a corresponding entry in `_VALID_TOP_LEVEL_KEYS`. A mismatch causes valid config keys to be silently dropped during profile loading.

### `graphify/serve.py` + `mcp_tool_registry`
Must be updated atomically when MCP diagram tools are added. The `mcp_tool_registry` dict maps tool names to handler functions — adding a handler without registering it (or vice versa) causes silent failures. The 3 critical `mcp_excalidraw` tools (`batch_create_elements`, `import_scene`, `export_scene`) must be registered as optional, with graceful fallback when `mcp_excalidraw` is unavailable.

### `graphify/export.py` (Obsidian vault export path)
The existing `--obsidian` export path in `export.py` gains a diagram generation step. After writing community notes, it calls `seed.py` to select seeds, then `diagram.py` to generate each diagram, then writes the diagram index note. This keeps diagram generation inside the existing export flow rather than adding a new CLI flag (for the standard case).

### `graphify/__main__.py` + skill files
New CLI flag: `--diagrams` (opt-in for non-Obsidian users). For Obsidian users, diagrams are generated automatically when `--obsidian` is used and diagrams are configured in the vault profile. Skill files for all 7 platforms must be updated to document the new diagram capabilities.

---

## Build Order (Strict)

Dependency chain within v1.5:

```
analyze.py (add diagram_hints)
    ↓
profile.py (expand _VALID_TOP_LEVEL_KEYS)
    ↓
seed.py (new module, depends on analyze hints)
    ↓
mcp_tool_registry + serve.py  ← atomic pair
    ↓
vault_adapter / export.py (wires diagram generation into Obsidian export)
    ↓
__main__.py + skill files (expose new flags and document capabilities)
```

Violations of this order create circular import risks or missing-registry failures. The `mcp_tool_registry + serve.py` step is marked atomic — both files must be updated in the same commit.

---

## Data Flow: Diagram Generation

```
build_graph() → cluster() → analyze()
                                ↓
                    diagram_hints(G, communities)
                                ↓
                    seed.py: select seeds (≤20)
                    seed.py: expand subgraphs
                                ↓
                    diagram.py: layout algorithm
                    diagram.py: generate Excalidraw JSON
                    diagram.py: write .excalidraw.md
                                ↓
                    export.py: write diagram index note
                    export.py: tag write-back via propose_vault_note
```

---

## Tag Write-Back: Trust Boundary

Tag write-back uses the existing `propose_vault_note` mechanism from vault_adapter. This is a trust boundary — graphify proposes changes; the user or Obsidian plugin applies them. Format: `#graphify/diagram/<type>`. This must NOT directly modify arbitrary vault note frontmatter — only append to the graphify-managed tag section.

---

## Excalidraw Scene Schema (Minimum Valid)

```json
{
  "type": "excalidraw",
  "version": 2,
  "source": "graphify",
  "elements": [
    {
      "id": "<sha256[:16]>",
      "type": "rectangle",
      "x": 0, "y": 0,
      "width": 160, "height": 60,
      "strokeColor": "#1e1e1e",
      "backgroundColor": "#e7f5ff",
      "text": "<label>",
      "fontFamily": 5
    }
  ],
  "appState": {
    "gridSize": null,
    "viewBackgroundColor": "#ffffff"
  },
  "files": {}
}
```

The `compress` field must be absent or set to `false` at the `.excalidraw.md` file level (frontmatter does not carry it — it is encoded in the JSON structure's absence of a `compressed` wrapper).

---

## Security Considerations

- Diagram labels are node labels from the graph — they pass through `security.py`'s label sanitization (HTML-escape, control char strip, 256-char cap) before embedding in Excalidraw JSON
- Vault paths for diagram files must pass through existing path confinement checks (output must stay inside `graphify-out/` or the configured vault diagrams folder)
- Element IDs derived from `sha256` are safe — no user input reaches the hash directly without going through node ID normalization first
