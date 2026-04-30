# Architecture

**Analysis Date:** 2026-04-09

## Pattern Overview

**Overall:** Linear functional pipeline with stateless transformations

**Key Characteristics:**
- Single-direction data flow through 7 pipeline stages
- Each stage is a pure function returning plain dicts/NetworkX graphs
- No shared mutable state between stages
- Deterministic extraction via tree-sitter AST + semantic LLM analysis
- Community detection with optional splitting for scale
- Multiple export formats (HTML, JSON, SVG, GraphML, Obsidian vault, Neo4j Cypher)

## Pipeline

```
detect() → extract() → build_graph() → cluster() → analyze() → report() → export()
```

**Data flow:**
1. `detect()` - File discovery with `.graphifyignore` support
   - Returns: `{"total_files": int, "file_list": [Path], "total_words": int}`

2. `extract()` - Dual extraction: tree-sitter AST for code, LLM for docs/images
   - Returns: `{"nodes": [...], "edges": [...], "hyperedges": [...], "input_tokens": int, "output_tokens": int}`
   - Node schema: `{id, label, file_type, source_file, source_location}`
   - Edge schema: `{source, target, relation, confidence, source_file}` — canonical `relation` vocabulary and hyperedge verbs: `docs/RELATIONS.md`
   - Confidences: `EXTRACTED` (AST), `INFERRED` (LLM with score), `AMBIGUOUS` (uncertain)

3. `build_graph()` - Merges extraction results into NetworkX undirected graph
   - Deduplicates nodes (semantic overwrites AST)
   - Validates schema via `validate.py`
   - Returns: `nx.Graph` with node/edge attributes

4. `cluster()` - Leiden/Louvain community detection
   - Splits oversized communities (>25% of graph, min 10 nodes)
   - Isolates become single-node communities
   - Returns: `{community_id: [node_ids]}`

5. `analyze()` - Extract insights: god nodes, surprising connections, knowledge gaps
   - God nodes: Top 10 most-connected real entities (excludes file-level hubs, concept nodes)
   - Surprising connections: Cross-file edges or cross-community edges by betweenness centrality
   - Knowledge gaps: Isolated nodes, thin communities, high ambiguity
   - Returns: `{"god_nodes": [...], "surprising_connections": [...], "knowledge_gaps": [...]}`

6. `report()` - Renders `GRAPH_REPORT.md`
   - Summary: node/edge counts, confidence breakdown, token cost
   - Communities: cohesion scores, key nodes
   - Gaps: isolated nodes, thin communities, ambiguous edges
   - Suggested questions (future expansion)

7. `export()` - Multiple format outputs
   - HTML (vis.js + dark UI, max 5000 nodes)
   - JSON (networkx node-link format)
   - SVG (Graphviz dot layout)
   - GraphML (XML graph format)
   - Obsidian vault (markdown + wikilinks)
   - Neo4j Cypher (CREATE statements)

## Layers

**Detection Layer (`detect.py`):**
- Purpose: Discover files, classify by type, validate corpus size
- Location: `graphify/detect.py`
- Contains: File classification (code/document/paper/image), sensitivity checking (skip secrets), paper detection heuristics
- Depends on: `pathlib`, regex
- Used by: CLI entrypoint, skill orchestration

**Extraction Layer (`extract.py`):**
- Purpose: Parse code via tree-sitter AST, analyze docs/images via LLM
- Location: `graphify/extract.py` (2719 lines - largest module)
- Contains: Language-specific extractors (Python, TypeScript, Go, Rust, Java, C++, etc.), import handlers, call graph walking, semantic extraction via Claude API
- Depends on: tree-sitter (py/ts/go/rs/java/cpp...), `cache.py`, `security.py`, `validate.py`
- Used by: Build layer, CLI

**Build Layer (`build.py`):**
- Purpose: Merge extractions, validate schema, construct graph
- Location: `graphify/build.py` (70 lines)
- Contains: `build_from_json()`, `build()` - combines dicts into single NetworkX graph
- Depends on: `validate.py`, networkx
- Used by: Cluster layer, skill

**Cluster Layer (`cluster.py`):**
- Purpose: Community detection and scoring
- Location: `graphify/cluster.py` (132 lines)
- Contains: Leiden (graspologic) with Louvain fallback, community splitting, cohesion scoring
- Depends on: networkx, graspologic (optional)
- Used by: Analyze layer, skill

**Analysis Layer (`analyze.py`):**
- Purpose: Extract insights - god nodes, surprising connections, knowledge gaps
- Location: `graphify/analyze.py` (523 lines)
- Contains: God node ranking (degree), cross-file/cross-community edge detection, knowledge gap detection (isolated, thin communities, high ambiguity)
- Depends on: networkx
- Used by: Report layer, skill

**Reporting Layer (`report.py`):**
- Purpose: Generate markdown audit trail
- Location: `graphify/report.py` (155 lines)
- Contains: Confidence breakdown, community summaries, gap analysis, suggested questions
- Depends on: datetime
- Used by: Export layer, skill

**Export Layer (`export.py`):**
- Purpose: Generate multiple output formats
- Location: `graphify/export.py` (989 lines)
- Contains: HTML (vis.js + sidebar), JSON, SVG, GraphML, Obsidian vault, Neo4j Cypher, Wiki (markdown articles per community)
- Depends on: networkx, html, json, math, graphviz (for SVG), `security.py`
- Used by: CLI, skill

**Supporting Layers:**

`security.py` (197 lines) - Input validation, SSRF protection
- URL validation: scheme checks, IP range blocking, cloud metadata protection
- Redirect validation: re-validates all redirects to prevent open-redirect SSRF
- Label sanitization: strips control chars, caps length for HTML embedding
- Path confinement: graph paths must stay inside `graphify-out/`
- Used by: extract, ingest, export, serve

`validate.py` (71 lines) - Schema enforcement
- Validates node/edge dicts before graph assembly
- Checks required fields: node={id, label, file_type, source_file}, edge={source, target, relation, confidence, source_file}
- Validates confidence values: EXTRACTED, INFERRED, AMBIGUOUS
- Used by: build

`cache.py` (138 lines) - SHA256-based semantic cache
- Skips unchanged files to save LLM tokens
- Caches by file hash, stores in `graphify-out/cache/`
- Used by: extract

`ingest.py` (291 lines) - Fetch URLs (tweet/arxiv/pdf/web)
- Saves as annotated markdown with metadata (title, author, date)
- Used by: Manual integration, CLI

`serve.py` (325 lines) - MCP stdio server
- Exposes graph query tools to Claude and agents
- BFS/DFS traversal, node search, subgraph extraction
- Used by: Skill for agent interaction

`wiki.py` (214 lines) - Wikipedia-style markdown articles
- One article per community + god node articles
- Index.md with navigation
- Cross-community links with edge counts
- Used by: Export layer

`watch.py` (162 lines) - File watching for live graph updates
- Rebuilds code extraction on file changes
- Used by: Optional watch mode

`hooks.py` (196 lines) - Git post-commit/post-checkout hooks
- Auto-refresh graph after code changes
- Multi-platform support (7 platforms)
- Used by: Installation

`benchmark.py` (129 lines) - Performance measurement
- Token cost, extraction time, graph stats
- Used by: Skill, debugging

## Data Flow - Detailed Example

**User runs: `/graphify .`**

1. **Detect phase:**
   - Walks filesystem from root, respects `.graphifyignore`
   - Classifies files: `.py` → code, `.md` → document, `arxiv.pdf` → paper, `.png` → image
   - Skips `.env`, `*.pem`, credential files (security patterns)
   - Returns file list + word count estimate

2. **Extract phase:**
   ```
   For each code file (AST path):
     - tree-sitter parse → walk AST
     - Extract: classes → defines_class edge, functions → defines_function
     - Extract: calls → calls edge (with confidence: EXTRACTED/INFERRED based on precision)
     - Extract: imports → imports edge
     - Cache result by file hash
   
   For each doc/image (semantic path):
     - Check cache: if unchanged, skip
     - Call Claude API with file content
     - Extract: concepts, relationships, summaries
     - Validate schema
     - Store confidence scores (typically INFERRED for LLM, AMBIGUOUS for uncertain)
   ```

3. **Build phase:**
   - Combine all nodes from all extractions into single `nodes` list
   - Combine all edges, validate that source/target exist in node set
   - Create `nx.Graph()`, add nodes with attributes (label, source_file, etc.)
   - Add edges with attributes (relation, confidence, source_file)
   - Store hyperedges if present (group relationships)

4. **Cluster phase:**
   - Run Leiden algorithm on graph
   - For each community: calculate cohesion (actual edges / max possible edges)
   - If community > 25% of graph AND >= 10 nodes: re-cluster the subgraph
   - Index communities by size descending for determinism

5. **Analyze phase:**
   - God nodes: sort nodes by degree, filter out file-level hubs and concept nodes
   - Surprising connections: detect cross-file edges or cross-community edges by betweenness
   - Knowledge gaps: find isolated nodes (degree <= 1), thin communities (< 3 nodes), high ambiguity edges (> 20%)

6. **Report phase:**
   - Generate markdown: summary, communities, god nodes, surprises, gaps, ambiguous edges
   - Example: "Transformer - 42 edges" (most connected abstraction)

7. **Export phase:**
   - Write `graph.json` (node-link format for loading)
   - Write `GRAPH_REPORT.md` (human-readable)
   - Write `graph.html` (vis.js interactive)
   - Write `graph.svg` (Graphviz layout)
   - Write `wiki/index.md` + `wiki/community-0.md`, etc. (Obsidian vault)
   - Write `graph.cypher` (Neo4j import)

## State Management

**Graph construction:**
- No global state - graph is built fresh each run
- Node deduplication happens at three levels:
  1. Within file: extractor's `seen_ids` set prevents duplicate node IDs per file
  2. Between files: NetworkX `add_node()` is idempotent, semantic overwrites AST
  3. Before build: skill merges cached + new semantic results using explicit `seen` set

**Community stability:**
- Leiden produces deterministic partitions (seed=42)
- Communities are re-indexed by size descending for consistent ordering
- Cohesion scores computed post-partition

**Caching:**
- Extraction results cached by file hash in `graphify-out/cache/`
- Re-runs skip unchanged files (LLM calls skipped)
- Cache invalidated on file modification

## Key Abstractions

**Node:**
- Represents: class, function, variable, concept, document, image
- Identity: stable `id` (slugified from name/path)
- Attributes: `label` (display name), `source_file`, `source_location`, `file_type`, `community` (assigned after clustering)
- Examples: `transformer`, `extract_python`, `api_endpoint`, `ml_model_training_concept`

**Edge:**
- Represents: relationship between nodes
- Types (relation): `defines_class`, `defines_function`, `calls`, `imports`, `contains`, `references`, `semantically_similar_to`, etc.
- Confidence: `EXTRACTED` (AST-found, high confidence), `INFERRED` (LLM with confidence_score 0.0-1.0), `AMBIGUOUS` (uncertain)
- Attributes: `source_file` (where detected), `relation` type, `confidence`, optional `confidence_score` for INFERRED
- Examples: `class_A → contains → method_x` (EXTRACTED), `AuthService → imports → TokenValidator` (EXTRACTED), `Component → semantically_similar_to → Template` (INFERRED 0.85)

**Community:**
- Represents: cluster of closely-related nodes
- Identified by: integer community_id (0 = largest after splitting)
- Metrics: cohesion score (0.0-1.0, ratio of actual/possible internal edges)
- Contains: typically 3-20 real nodes (method/class stubs filtered from display)
- Example: Community 0 = "transformer layer" (Transformer, Attention, LayerNorm, etc.)

**File Type:**
- `code` - source code (py, ts, js, go, rs, java, cpp, c, rb, swift, kt, cs, scala, php, lua, zig, ps1, ex, m, jl)
- `document` - markdown/text (md, txt, rst)
- `paper` - academic PDF (detected via signal heuristics)
- `image` - visual content (png, jpg, jpeg, gif, webp, svg)
- `rationale` - synthetic explanation nodes (semantic extraction)

## Entry Points

**CLI (`graphify/__main__.py`):**
- Location: `graphify/__main__.py` (652 lines)
- Entrypoint: `__main__.py` exposes: `install`, `uninstall`, `run`, `query`, `watch` commands
- Platform config: dict of 8 platforms (Claude Code, Codex, OpenCode, OpenClaw, Factory Droid, Trae, Trae CN, Windows)
- Skill files: 7 platform variants (`skill.md`, `skill-codex.md`, etc.) installed to platform-specific directories
- Hook registration: updates `.claude/CLAUDE.md`, `.codex/hooks.json`, OpenCode plugins, git hooks

**Skill orchestration (`graphify/skill.md` and variants):**
- Location: `graphify/skill.md` (50K lines - Claude Code / Codex agent prompt)
- Role: Coordinates pipeline, handles user prompts (`/graphify`), integrates detection → extraction → build → cluster → analyze → report → export
- Handles: LLM integration for semantic extraction, caching, multi-file corpus

**MCP Server (`graphify/serve.py`):**
- Location: `graphify/serve.py` (325 lines)
- Entrypoint: stdio server for agents
- Exposes: graph loading, BFS/DFS traversal, node search, subgraph extraction

## Cross-Cutting Concerns

**Logging:**
- Approach: Uses `print()` to stderr for warnings/errors, stdout for user-facing output
- Patterns:
  - Detection: "warning: corpus below 50K words - graph may not add value"
  - Extraction: "[graphify] Extraction warning: {N} issues - {first_error}"
  - Build: Dangling edges to stdlib logged as warnings only
  - Cluster: Leiden/Louvain output suppressed to prevent ANSI corruption on Windows

**Validation:**
- All external input passes through `graphify/security.py`
- URL validation: scheme checks, IP range blocking, cloud metadata endpoints, redirect validation
- Path validation: graph paths confined to `graphify-out/`
- Label sanitization: HTML-escape, control char strip, length cap (256 chars)
- Extraction schema: validated by `validate.py` before graph construction
- Node/edge required fields enforced

**Authentication:**
- Approach: API keys passed via environment variables (Claude API key for semantic extraction)
- Not persisted in graph - only token cost metrics stored
- OAuth for Github/Arxiv/PDF URLs handled by `ingest.py`

**Error Handling:**
- Strategy: Fail loudly with actionable messages, but continue when safe
- Patterns:
  - File read errors: skip file, log warning (permission, encoding)
  - Tree-sitter parse errors: skip file, continue
  - LLM API errors: skip semantic extraction, use AST only
  - Dangling edges (stdlib imports): expected, not an error
  - Corrupted graph.json: fatal error, prompt rebuild

---

*Architecture analysis: 2026-04-09*
