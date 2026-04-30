# v1.5 Configuration Guide

This guide walks through the full v1.5 pipeline end-to-end on a sample Obsidian vault: promoting graph nodes into vault folders (`vault-promote`), generating per-cluster diagram seeds (`--diagram-seeds`), writing Excalidraw template stubs (`--init-diagram-templates`), installing the Excalidraw skill (`install --platform excalidraw`), and invoking it from your AI client (`/excalidraw-diagram`). It also ships a complete annotated `.graphify/profile.yaml` reference and a reference-quality MCP tool integration section for `list_diagram_seeds` and `get_diagram_seed`.

## Prerequisites

**Requirements:**

- Python 3.10+
- `pip install -e ".[all]"` from the repository root (PyYAML is required for profile parsing)
- An Obsidian vault directory you can write to
- A `graphify-out/graph.json` already produced by a prior `graphify` run

## Sample vault layout

The walkthrough assumes a synthetic vault that follows the same Atlas/* folder mapping shown in the existing README example. Copy this structure into your own vault to follow along:

```
~/vaults/myproject/
├── Atlas/
│   ├── Maps/
│   │   └── Project Overview.md
│   ├── Dots/
│   │   ├── Things/
│   │   │   ├── AuthService.md
│   │   │   ├── TokenValidator.md
│   │   │   └── SessionStore.md
│   │   ├── Statements/
│   │   │   └── Auth must be stateless.md
│   │   └── People/
│   │       └── Alice Researcher.md
│   └── Sources/
│       └── Clippings/
│           └── RFC 7519 — JWT.md
└── .graphify/
    └── profile.yaml
```

The five-to-ten illustrative notes above are placeholders; substitute your own filenames. The `.graphify/profile.yaml` referenced is the one shown in full in the [profile reference](#the-graphifyprofileyaml-reference) section below.

## Step 1 — Promote nodes into the vault

```bash
# promote graph nodes into Atlas/* folders
graphify vault-promote --vault ~/vaults/myproject --threshold 3
```

Expected stderr summary:

```
[graphify] vault-promote complete: promoted=...; skipped=...
```

`vault-promote` is write-only: it never overwrites foreign files (any note not recorded as graphify-authored in `graphify-out/vault-manifest.json`). Self-authored files are overwritten only when their on-disk hash still matches the manifest. The `--threshold` flag gates the minimum node degree required for promotion; nodes below threshold are recorded under `skipped=`.

## Step 2 — Generate diagram seeds

```bash
# emit per-seed JSON + seeds-manifest.json under graphify-out/seeds/
graphify --diagram-seeds --vault ~/vaults/myproject
```

Expected stderr summary:

```
[graphify] diagram-seeds complete: {<summary dict>}
```

`--vault` is optional. When supplied, tag write-back is routed through the merge planner so existing vault tags are preserved under the union policy. Each emitted seed is a JSON file under `graphify-out/seeds/` named by its canonical `seed_id`; a manifest at `graphify-out/seeds/seeds-manifest.json` indexes them.

## Step 3 — Initialize Excalidraw template stubs

```bash
# write one .excalidraw.md stub per profile diagram_types entry
graphify --init-diagram-templates --vault ~/vaults/myproject
```

Expected stderr summary:

```
[graphify] init-diagram-templates complete: wrote <N> stub(s) (force=False)
```

`--vault` is required for this command and exits with `error: --vault PATH required` if omitted. If the vault has no `.graphify/profile.yaml` or its `diagram_types:` block is empty, the command falls back to writing the six built-in defaults (`architecture`, `workflow`, `repository-components`, `mind-map`, `cuadro-sinoptico`, `glossary-graph`). All emitted stubs hard-code `compress: false` in their Excalidraw frontmatter; this is a deliberate one-way door so downstream tooling can patch elements deterministically.

## Step 4 — Install the Excalidraw skill

```bash
# copies skill-excalidraw.md -> .claude/skills/excalidraw-diagram/SKILL.md
graphify install --platform excalidraw
```

`excalidraw` is a `_PLATFORM_CONFIG` entry in `graphify/__main__.py`. Unlike the agent-platform entries, this one only places the skill file under your client's skills directory; it does not append a CLAUDE.md anchor.

## Step 5 — Invoke the skill

In your AI client, run:

```
/excalidraw-diagram
```

The skill expects three MCP servers to be present in your client's `.mcp.json`. Copy this block verbatim — graphify does not edit `.mcp.json`:

```jsonc
{
  "mcpServers": {
    "graphify":   { "command": "graphify", "args": ["serve"] },
    "obsidian":   { "command": "uvx",      "args": ["mcp-obsidian"] },
    "excalidraw": { "command": "npx",      "args": ["-y", "@excalidraw/mcp-server"] }
  }
}
```

The skill calls into `graphify` for seed retrieval, `obsidian` for note placement, and `excalidraw` for canvas generation.

## The `.graphify/profile.yaml` reference

The profile below is a strict superset of the example shown in `README.md`: same `folder_mapping`, `naming`, `merge`, and `mapping_rules` keys, plus a top-level `diagram_types:` block with all six built-ins and one custom `decision-tree` entry.

```yaml
# .graphify/profile.yaml — v1.5 reference profile
folder_mapping:
  moc: "Atlas/Maps/"
  thing: "Atlas/Dots/Things/"
  statement: "Atlas/Dots/Statements/"
  person: "Atlas/Dots/People/"
  source: "Atlas/Sources/"
  default: "Atlas/Dots/"

naming:
  convention: title_case  # or kebab-case, preserve

merge:
  strategy: update
  preserve_fields: [rank, mapState, tags, created]
  field_policies:
    tags: union  # union, replace, or preserve

mapping_rules:
  - when: { file_type: person }
    then: { note_type: person, folder: "Atlas/Dots/People/" }

diagram_types:
  # Built-in: architecture. Loader gate is min_main_nodes (D-06). Tiebreak among
  # matching types prefers the highest min_main_nodes, then declaration order (D-07).
  - name: architecture
    template_path: "Excalidraw/Templates/architecture.excalidraw.md"
    trigger_node_types: ["service", "module", "class"]
    trigger_tags: ["graph/architecture", "tech/service"]
    min_main_nodes: 4
    naming_pattern: "{main_label} — Architecture"
    layout_type: architecture
    output_path: "Atlas/Maps/Architecture/"

  - name: workflow
    template_path: "Excalidraw/Templates/workflow.excalidraw.md"
    trigger_node_types: ["function", "step", "process"]
    trigger_tags: ["graph/workflow"]
    min_main_nodes: 3
    naming_pattern: "{main_label} — Workflow"
    layout_type: workflow
    output_path: "Atlas/Maps/Workflows/"

  - name: repository-components
    template_path: "Excalidraw/Templates/repository-components.excalidraw.md"
    trigger_node_types: ["repository", "package", "module"]
    trigger_tags: ["graph/repo"]
    min_main_nodes: 3
    naming_pattern: "{main_label} — Components"
    layout_type: repository-components
    output_path: "Atlas/Maps/Repos/"

  - name: mind-map
    template_path: "Excalidraw/Templates/mind-map.excalidraw.md"
    trigger_node_types: ["concept", "topic"]
    trigger_tags: ["graph/concept"]
    min_main_nodes: 2
    naming_pattern: "{main_label} — Mind Map"
    layout_type: mind-map
    output_path: "Atlas/Maps/MindMaps/"

  - name: cuadro-sinoptico
    template_path: "Excalidraw/Templates/cuadro-sinoptico.excalidraw.md"
    trigger_node_types: ["taxonomy", "category"]
    trigger_tags: ["graph/taxonomy"]
    min_main_nodes: 3
    naming_pattern: "{main_label} — Cuadro Sinoptico"
    layout_type: cuadro-sinoptico
    output_path: "Atlas/Maps/Taxonomies/"

  - name: glossary-graph
    template_path: "Excalidraw/Templates/glossary-graph.excalidraw.md"
    trigger_node_types: ["term", "definition"]
    trigger_tags: ["graph/glossary"]
    min_main_nodes: 5
    naming_pattern: "{main_label} — Glossary"
    layout_type: glossary-graph
    output_path: "Atlas/Maps/Glossaries/"

  # Custom: decision-tree. The two policy values below — branch threshold and
  # centrality-based tiebreak — are NOT loader-enforced schema keys. They are
  # author-declared policy comments for downstream skill / agent logic.
  #
  # Policy (D-05): fire only when the source node has >=3 outbound branches.
  # Policy (D-06): on tiebreak, prefer the node with highest betweenness centrality.
  #
  # The loader still enforces min_main_nodes; the heuristic recommender only emits
  # one of the six built-in layout_type values, so we map decision-tree onto mind-map
  # downstream.
  - name: decision-tree
    template_path: "Excalidraw/Templates/decision-tree.excalidraw.md"
    trigger_node_types: ["decision", "choice", "branch"]
    trigger_tags: ["graph/decision"]
    min_main_nodes: 3
    naming_pattern: "{main_label} — Decision Tree"
    layout_type: mind-map
    output_path: "Atlas/Maps/Decisions/"
```

The `min_main_nodes` is the only numeric gate the loader enforces. Higher-level policies — "fire only when the source node has >=3 outbound branches" or "tiebreak by highest betweenness centrality" — are policies a profile author can declare in comments and enforce in their own downstream skill / agent logic. graphify's built-in recommender (`seed.py:265-289`) uses `min_main_nodes` for the gate and prefers higher `min_main_nodes` on ties (then declaration order via stable `max()`).

## MCP Tool Integration

The `graphify serve` MCP server exposes two tools that an agent author can call to discover and retrieve diagram seeds without reading any graphify source.

### `list_diagram_seeds`

Verbatim tool declaration (`graphify/serve/mcp_tool_registry.py:349`):

```python
types.Tool(
    name="list_diagram_seeds",
    description=(
        "List all available diagram seeds in graphify-out/seeds/. Returns per-seed: "
        "seed_id, main_node_label, suggested_layout_type, trigger (auto|user), node_count. "
        "D-02 envelope. Alias-resolved per D-16. Returns no_seeds envelope when "
        "directory empty or manifest missing/corrupt."
    ),
    inputSchema={
        "type": "object",
        "properties": {
            "budget": {"type": "integer", "default": 500},
        },
    },
)
```

**Arguments:**

| Name   | Type    | Required | Default |
| ------ | ------- | -------- | ------- |
| budget | integer | no       | 500     |

**Return body.** A text body followed by `QUERY_GRAPH_META_SENTINEL` and a JSON meta envelope. Each row of the text body has the shape:

```
<seed_id>\t<main_node_label>\t<suggested_layout_type>\t<trigger>\t<node_count>
```

**Return meta keys:**

| Key                  | Type                  | Always present                |
| -------------------- | --------------------- | ----------------------------- |
| status               | "ok" \| "no_seeds"    | yes                           |
| seed_count           | integer               | yes                           |
| budget_used          | integer               | yes                           |
| resolved_from_alias  | dict[str, list[str]]  | only when alias rewrite fired |

**Invocation:**

```json
{
  "tool": "list_diagram_seeds",
  "arguments": { "budget": 500 }
}
```

**Return:**

```json
{
  "content": [
    {
      "type": "text",
      "text": "auth_service_arch\tAuthService\tarchitecture\tauto\t6\nsession_store_workflow\tSessionStore\tworkflow\tuser\t4"
    }
  ],
  "meta": {
    "status": "ok",
    "seed_count": 2,
    "budget_used": 73
  }
}
```

### `get_diagram_seed`

Verbatim tool declaration (`graphify/serve/mcp_tool_registry.py:364`):

```python
types.Tool(
    name="get_diagram_seed",
    description=(
        "Return the full SeedDict for a specific seed by seed_id. Non-existent seed_id "
        "returns a not_found envelope; corrupt file returns a corrupt envelope; never "
        "crashes. D-02 envelope. Alias-resolved per D-16 on both the seed_id argument "
        "and the node IDs in the returned SeedDict body."
    ),
    inputSchema={
        "type": "object",
        "properties": {
            "seed_id": {"type": "string", "description": "Seed identifier from list_diagram_seeds"},
            "budget": {"type": "integer", "default": 2000},
        },
        "required": ["seed_id"],
    },
)
```

**Arguments:**

| Name    | Type    | Required | Default |
| ------- | ------- | -------- | ------- |
| seed_id | string  | yes      | —       |
| budget  | integer | no       | 2000    |

**Return body.** Pretty-printed JSON of the SeedDict (`graphify/seed.py:295-307`):

```json
{
  "seed_id": "<canonical_id>",
  "trigger": "auto",
  "main_node_id": "<id>",
  "main_node_label": "<label>",
  "main_nodes": [{"id": "...", "label": "...", "file_type": "...", "element_id": "..."}],
  "supporting_nodes": [{"id": "...", "label": "...", "file_type": "...", "element_id": "..."}],
  "relations": [{"source": "...", "target": "...", "relation": "...", "confidence": "..."}],
  "suggested_layout_type": "architecture",
  "suggested_template": "Excalidraw/Templates/architecture.excalidraw.md",
  "version_nonce_seed": 1234567890
}
```

`suggested_layout_type` is always one of the six built-ins: `architecture`, `workflow`, `repository-components`, `mind-map`, `cuadro-sinoptico`, `glossary-graph`.

**Return meta keys:**

| Key                  | Type                                          | Always present                |
| -------------------- | --------------------------------------------- | ----------------------------- |
| status               | "ok" \| "truncated" \| "not_found" \| "corrupt" | yes                         |
| seed_id              | string                                        | yes                           |
| node_count           | integer                                       | when status is ok or truncated |
| budget_used          | integer                                       | yes                           |
| resolved_from_alias  | dict[str, list[str]]                          | only when alias rewrite fired |

**Invocation:**

```json
{
  "tool": "get_diagram_seed",
  "arguments": { "seed_id": "auth_service_arch", "budget": 2000 }
}
```

**Return:**

```json
{
  "content": [
    {
      "type": "text",
      "text": "{\n  \"seed_id\": \"auth_service_arch\",\n  \"trigger\": \"auto\",\n  \"main_node_id\": \"auth_service\",\n  \"main_node_label\": \"AuthService\",\n  \"main_nodes\": [...],\n  \"supporting_nodes\": [...],\n  \"relations\": [...],\n  \"suggested_layout_type\": \"architecture\",\n  \"suggested_template\": \"Excalidraw/Templates/architecture.excalidraw.md\",\n  \"version_nonce_seed\": 4271833915\n}"
    }
  ],
  "meta": {
    "status": "ok",
    "seed_id": "auth_service_arch",
    "node_count": 6,
    "budget_used": 412
  }
}
```

### Alias resolution and traversal defense

Every MCP tool that accepts a node-id argument re-implements the same closure-local resolver. The canonical form lives at `graphify/serve.py:1234-1250`:

```python
def _resolve_alias(node_id: str) -> str:
    # WR-03: transitive resolution with cycle guard, in case dedup_report.json
    # ever contains chained entries (e.g. {"a": "b", "b": "c"}).
    seen: set[str] = set()
    current = node_id
    while current in _effective_alias_map and current not in seen:
        seen.add(current)
        nxt = _effective_alias_map[current]
        if nxt == current:
            break
        current = nxt
    if current != node_id:
        aliases = _resolved_aliases.setdefault(current, [])
        if node_id not in aliases:
            aliases.append(node_id)
    return current
```

The same closure is repeated at `serve.py:1399-1403, 1526, 1815, 1990, 2590, 2686`. Behavior:

- The walk handles transitive aliases — `{"a": "b", "b": "c"}` resolves `a` to `c`.
- A `seen` set guards against cycles; if the same node would be visited twice, the loop exits and the current node is returned.
- On rewrite, the original ID is appended under the canonical key in `_resolved_aliases`, and the resolution map is surfaced via the `resolved_from_alias` field in each tool's meta envelope.

The seed tools (`list_diagram_seeds`, `get_diagram_seed`) use a single-step variant at `serve.py:2590-2599` and `2686-2695`. They do not perform a transitive walk — sufficient because `seed_id` is a leaf identifier, not a graph node id traversed through chained aliases.
