# Stack Research

**Project:** graphify v1.5 — Diagram Intelligence & Excalidraw Bridge
**Researched:** 2026-04-22
**Focus:** What new dependencies, formats, and integrations are needed to produce Excalidraw diagrams from the knowledge graph?

---

## Verdict: No New Required Dependencies

v1.5 adds zero new required Python dependencies. All diagram generation uses stdlib (`json`, `hashlib`, `base64`) plus the already-required `networkx`. The `mcp_excalidraw` MCP server is optional — the pure-Python path (direct `.excalidraw.md` file generation) is mandatory and must work standalone.

---

## Core Technologies

### Python 3.10+ (existing)
The entire pipeline stays on the existing Python 3.10/3.12 CI targets. No version bump required. All new modules (`diagram.py`, additions to `analyze.py`, `profile.py`, `seed.py`) follow existing conventions.

### networkx (existing, no version change)
Graph traversal for seed extraction, subgraph slicing, and community layout uses existing networkx APIs: `G.subgraph()`, `nx.spring_layout()`, `nx.kamada_kawai_layout()`, `nx.bfs_tree()`. No new graph algorithms are required.

### hashlib / json / base64 (stdlib, existing)
Element ID generation uses `hashlib.sha256(node_id.encode())[:16]` — stable, deterministic, not label-derived. JSON serialization for `.excalidraw` scene format uses stdlib `json`. No third-party serialization needed.

### mcp_excalidraw (optional external MCP server)
An optional MCP server with 21 verified tools. The 3 critical tools are:
- `batch_create_elements` — bulk element creation
- `import_scene` — replace entire scene
- `export_scene` — retrieve scene JSON

When available, these tools allow live Obsidian canvas updates. When absent, graphify falls back to writing `.excalidraw.md` files directly. The pure-Python path must always work.

---

## Excalidraw File Format (Critical Specification)

Excalidraw files saved as Obsidian markdown use a specific format that must be followed exactly:

```
---
excalidraw-plugin: parsed
tags: [excalidraw]
---
==⚠  Switch to EXCALIDRAW VIEW in the MORE OPTIONS menu of this document. ==

## Drawing
` `` `json
{"type":"excalidraw","version":2,"source":"graphify",...}
` `` `
%%
```

Key constraints:
- **Frontmatter key:** `excalidraw-plugin: parsed` (not `raw`)
- **Section header:** `## Drawing` (exact, case-sensitive)
- **Compression:** `compress: false` — MANDATORY. LZ-String compression breaks pure-Python round-trips and agent readability. This is a one-way door: once files are generated with a given compression setting, changing it requires re-generating all diagrams.
- **Font family:** `fontFamily: 5` (Excalidraw's "hand-drawn" default; do NOT use 1 or 3)
- **Element IDs:** `sha256(node_id.encode())[:16]` hex — stable across re-runs, not derived from labels

---

## Compression Format: The One-Way Door

This is the single most consequential format decision in v1.5:

- `compress: false` → raw JSON in the `## Drawing` block → readable by Python, agents, diffs
- LZ-String compression → compact but requires JS decompression → breaks pure-Python path

**Decision: always write `compress: false`.** Changing this after vault files exist requires migrating every diagram file. Lock this in Phase 1 and document it as immutable.

---

## Layout Algorithms

Three layout strategies map to diagram types:

| Diagram Type | Algorithm | Notes |
|---|---|---|
| dependency graph | `nx.spring_layout(seed=42)` | Force-directed, good for general graphs |
| architecture | `nx.kamada_kawai_layout()` | Aesthetic, stress-minimizing |
| concept map | `nx.spring_layout(seed=42)` | Same as dependency |
| sequence | custom linear | Nodes positioned left-to-right by topological sort |
| mindmap | radial from root | BFS layers, concentric rings |

All layouts produce normalized `(x, y)` coordinates scaled to Excalidraw canvas units (multiply by 200 for comfortable spacing).

---

## No-Go Technologies

- **Jinja2 / template engines:** Not needed; string substitution handles Excalidraw JSON
- **LZ-String / lzstring Python ports:** Do not add — compress: false eliminates the need
- **pygraphviz / graphviz layouts:** Already optional in graphify; not needed for Excalidraw
- **Any JS runtime:** Pure-Python path must work without Node.js
