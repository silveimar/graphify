# Feature Research

**Project:** graphify v1.5 — Diagram Intelligence & Excalidraw Bridge
**Researched:** 2026-04-22
**Focus:** What features does v1.5 need to deliver, what should be deferred, and what are anti-features?

---

## Table Stakes (Must Have)

These are required for v1.5 to be coherent. Without them the feature set is incomplete.

### 1. Diagram Type Support (5 types minimum)
Users expect to generate at least: dependency graphs, architecture diagrams, concept maps, sequence diagrams, and mindmaps. Each type maps to a distinct layout algorithm and visual treatment. Attempting to use a single layout for all types produces unreadable diagrams.

**Constraint:** Each diagram type must be registered in `profile.py`'s `_VALID_TOP_LEVEL_KEYS` list. This list and the `diagram_types` dict must be updated atomically — a mismatch causes silent drops of valid config keys.

### 2. Seed-Based Subgraph Extraction
Diagrams are not the full graph — they are focused views. The `seed.py` module selects up to N nodes as "seeds" (god nodes, community hubs, or user-specified) and expands a subgraph around each. The `max_seeds` cap is **20** — beyond this, element count explodes and Excalidraw becomes unusable.

### 3. Excalidraw .excalidraw.md File Generation
The primary output is a `.excalidraw.md` file per diagram, placed in the Obsidian vault's configured diagrams folder. The file must be valid for direct opening in Obsidian + Excalidraw plugin without any post-processing.

### 4. Pure-Python Path (No MCP Required)
All diagram generation must work without the `mcp_excalidraw` MCP server. The pure-Python path writes `.excalidraw.md` files directly. This is not optional — it is the primary path. MCP integration is an enhancement on top.

### 5. Tag Write-Back via propose_vault_note
When a diagram is generated for a node/community, graphify writes back a tag to the corresponding vault note via the existing `propose_vault_note` trust boundary. This links notes to their diagrams and enables Obsidian navigation. Tag format: `#graphify/diagram/<type>`.

### 6. Stable Element IDs
Diagram elements must have stable IDs across re-runs so Excalidraw preserves user edits (arrow adjustments, label moves). IDs are `sha256(node_id.encode())[:16]` hex. Never derive IDs from labels — labels change, node IDs do not.

---

## Should Have (Differentiators)

These make v1.5 genuinely useful rather than a toy demo.

### 7. MCP Tool Integration (21 tools, 3 critical)
When `mcp_excalidraw` is available, graphify uses `batch_create_elements`, `import_scene`, and `export_scene` for live canvas updates. This enables incremental diagram updates without file replacement. The tool registry in `mcp_tool_registry` must be updated atomically with `serve.py` changes.

### 8. Community-Level Diagrams
One diagram per detected community (from `cluster.py`) showing the community's internal structure. Auto-named from community label. Generated as part of the standard `--obsidian` export flow.

### 9. God-Node Architecture Diagrams
The top N god nodes (by degree from `analyze.py`) become the seeds for an architecture-level diagram showing cross-community connections. This is the "10,000-foot view" diagram.

### 10. Diagram Index Note
A single `Diagrams.md` index note in the vault listing all generated diagrams with wikilinks, diagram type, seed count, and generation timestamp. Updated on each `graphify` run.

### 11. analyze.py Diagram Hints
`analyze.py` gains a `diagram_hints()` function that suggests which diagram type best fits each community based on graph topology (e.g., linear chains → sequence, dense clusters → concept map, layered DAGs → architecture).

---

## Defer to v2+

### Auto-Layout Refinement via MCP
Using `mcp_excalidraw` to retrieve user-edited layouts and persist them as "pinned" coordinates is valuable but complex. Defer.

### Animated / Interactive Diagrams
Excalidraw supports embedded links and some interactivity. Exploring this is v2+ work.

### PDF/SVG Export of Diagrams
Exporting generated Excalidraw diagrams to PDF or SVG via headless Obsidian is out of scope for v1.5.

### Multi-Vault Diagram Sync
Propagating diagrams across multiple vaults. Deferred.

### Natural Language Diagram Queries
"Show me how AuthService connects to the database" as a freeform query generating a diagram. Requires significant LLM integration work beyond current scope.

---

## Anti-Features (Explicitly Exclude)

- **Generating diagrams for every node** — max_seeds=20 cap is a hard limit; generating hundreds of diagrams floods the vault
- **LZ-String compressed output** — breaks pure-Python path, breaks agent readability, creates migration burden
- **Label-derived element IDs** — unstable across renames, breaks Excalidraw's edit preservation
- **Requiring mcp_excalidraw for any core functionality** — must remain optional
- **Overwriting user-edited diagram content** — when a `.excalidraw.md` already exists, graphify must check for user edits before overwriting (use file hash or timestamp)
