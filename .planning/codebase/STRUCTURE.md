# Codebase Structure

**Analysis Date:** 2026-04-09

## Directory Layout

```
graphify/
├── graphify/                    # Main package
│   ├── __init__.py             # Lazy imports for external API
│   ├── __main__.py             # CLI entrypoint, platform install/uninstall
│   ├── skill.md                # Claude Code skill (main platform)
│   ├── skill-*.md              # Platform variants (codex, opencode, claw, droid, trae, windows)
│   ├── detect.py               # File discovery, classification, corpus validation
│   ├── extract.py              # Tree-sitter AST extraction + LLM semantic extraction
│   ├── build.py                # Merge extractions, construct NetworkX graph
│   ├── cluster.py              # Leiden/Louvain community detection
│   ├── analyze.py              # God nodes, surprising connections, knowledge gaps
│   ├── report.py               # Render GRAPH_REPORT.md
│   ├── export.py               # HTML, JSON, SVG, GraphML, Obsidian vault, Neo4j Cypher
│   ├── wiki.py                 # Wikipedia-style markdown articles per community
│   ├── serve.py                # MCP stdio server for agent queries
│   ├── security.py             # URL validation, SSRF blocking, label sanitization, path confinement
│   ├── validate.py             # JSON schema enforcement for extractions
│   ├── cache.py                # SHA256-based semantic cache (skip unchanged files)
│   ├── ingest.py               # Fetch URLs (tweet/arxiv/pdf/web) → annotated markdown
│   ├── watch.py                # File watcher for live graph updates
│   ├── hooks.py                # Git post-commit/post-checkout hook installation
│   ├── benchmark.py            # Performance measurement (tokens, time, stats)
│   └── manifest.py             # (stub - placeholder)
├── tests/                       # Test suite
│   ├── test_detect.py
│   ├── test_extract.py
│   ├── test_build.py
│   ├── test_cluster.py
│   ├── test_analyze.py
│   ├── test_export.py
│   ├── test_report.py
│   ├── test_cache.py
│   ├── test_ingest.py
│   ├── test_hooks.py
│   ├── test_watch.py
│   ├── test_languages.py       # Multi-language extraction tests
│   ├── test_security.py
│   ├── test_confidence.py
│   ├── test_hypergraph.py
│   ├── test_benchmark.py
│   ├── test_multilang.py
│   ├── test_rationale.py
│   ├── test_semantic_similarity.py
│   ├── test_claude_md.py
│   ├── test_install.py
│   ├── fixtures/               # Test data
│   │   ├── extraction.json     # Sample extraction output
│   │   ├── sample.py           # Python code fixture
│   │   └── graphify-out/       # Expected output fixtures
│   │       └── cache/          # Cache fixtures
│   └── __init__.py
├── worked/                      # Reference graphs (worked examples)
│   ├── example/                # Simple example corpus
│   │   └── raw/                # Input files
│   ├── httpx/                  # httpx library analysis
│   │   └── raw/
│   ├── mixed-corpus/           # Multi-language example
│   │   └── raw/
│   └── karpathy-repos/         # Karpathy repo analysis
├── input_docs/                  # Test input (Ideaverse vault - NOT committed normally)
├── graphify-out/               # Output directory (created at runtime)
│   ├── graph.json              # Node-link format (for loading)
│   ├── GRAPH_REPORT.md         # Human-readable summary
│   ├── graph.html              # Interactive HTML viz (vis.js)
│   ├── graph.svg               # Static layout (Graphviz)
│   ├── graph.cypher            # Neo4j import script
│   ├── wiki/                   # Obsidian vault
│   │   ├── index.md            # Navigation
│   │   ├── community-0.md      # One per community
│   │   └── god-node-X.md       # One per god node
│   ├── cache/                  # File hashes for semantic cache
│   └── manifest.json           # File list + metadata
├── .claude/                     # Claude Code configuration
│   ├── skills/
│   │   └── graphify/
│   │       └── SKILL.md        # Installed skill copy
│   └── CLAUDE.md               # Skill registration
├── .github/
│   └── workflows/              # CI/CD (pytest on Python 3.10, 3.12)
├── pyproject.toml              # Package metadata, dependencies
├── CLAUDE.md                   # Project-level instructions (architecture, testing, security)
├── ARCHITECTURE.md             # High-level architecture (this document's peer)
├── README.md                   # User guide
├── SECURITY.md                 # Threat model and mitigations
└── CHANGELOG.md                # Version history
```

## Directory Purposes

**`graphify/`:**
- Purpose: Main package - pipeline stages + supporting utilities
- Contains: 19 Python modules (extract.py is largest at 2719 lines)
- Each module is either a pipeline stage or cross-cutting concern (security, validation, cache, etc.)

**`tests/`:**
- Purpose: Unit test suite (pytest)
- Contains: 20+ test files, one per module, plus fixtures and example graphs
- Patterns: Pure unit tests, no network calls, filesystem ops confined to `tmp_path`

**`worked/`:**
- Purpose: Reference graphs for documentation and debugging
- Contains: 3-4 worked examples (httpx library, simple example, mixed-language corpus)
- Output: Stored raw inputs in `*/raw/` subdirectories (NOT committed)

**`input_docs/`:**
- Purpose: Test corpus (Ideaverse Pro vault structure)
- Contains: Large markdown vault (~1000+ files)
- Note: Present in this repo for integration testing, not in typical user repos

**`graphify-out/`:**
- Purpose: Output directory (created at runtime)
- Contains: graph.json, GRAPH_REPORT.md, HTML/SVG/Cypher exports, wiki/ vault, cache/
- Committed: No (in .gitignore)

**`.claude/`:**
- Purpose: Installed Claude Code skill and metadata
- Contains: SKILL.md (copy of graphify/skill.md), version stamp
- Created by: `graphify install` command
- Committed: No (in .gitignore)

## Key File Locations

**Entry Points:**
- `graphify/__main__.py`: CLI entrypoint, platform install/uninstall, `graphify` command
- `graphify/skill.md`: Claude Code skill (50K lines, orchestrates full pipeline)
- `graphify/serve.py`: MCP server for agent queries

**Configuration:**
- `pyproject.toml`: Package metadata, dependencies (tree-sitter variants, graspologic optional)
- `CLAUDE.md`: Architecture overview, build/test commands, security notes

**Core Logic:**
- `graphify/detect.py`: File discovery, type classification, corpus validation
- `graphify/extract.py`: Language-specific AST extraction (Python, TypeScript, Go, Rust, Java, C++, etc.) + LLM semantic extraction
- `graphify/build.py`: Extraction merge, graph construction, schema validation
- `graphify/cluster.py`: Community detection, cohesion scoring
- `graphify/analyze.py`: Insights extraction (god nodes, surprises, gaps)
- `graphify/report.py`: Markdown report generation
- `graphify/export.py`: Multi-format output (HTML, JSON, SVG, GraphML, Obsidian, Cypher)

**Supporting:**
- `graphify/security.py`: URL validation, SSRF blocking, label sanitization, path confinement
- `graphify/validate.py`: JSON schema enforcement for node/edge dicts
- `graphify/cache.py`: SHA256-based semantic cache
- `graphify/ingest.py`: URL fetching (tweet/arxiv/pdf/web)
- `graphify/serve.py`: MCP server (BFS/DFS, search, subgraph queries)
- `graphify/wiki.py`: Wikipedia-style markdown generator
- `graphify/watch.py`: File watcher for live updates
- `graphify/hooks.py`: Git hook installation
- `graphify/benchmark.py`: Performance measurement

**Testing:**
- `tests/test_*.py`: One per module, pure unit tests
- `tests/fixtures/extraction.json`: Sample extraction output for testing
- `tests/fixtures/sample.py`: Python code fixture

**Documentation:**
- `CLAUDE.md`: Project architecture, build/test commands, security model
- `ARCHITECTURE.md`: Codebase architecture (high-level)
- `SECURITY.md`: Threat model, mitigations
- `README.md`: User guide, installation, usage examples

## Naming Conventions

**Files:**
- `extract.py`, `build.py`, `cluster.py`: Pipeline stages named by function
- `test_<module>.py`: Test file for each module (test_extract.py for extract.py)
- `skill.md`, `skill-*.md`: Platform variant skills (skill-codex.md, skill-opencode.md, etc.)
- `graph.json`, `graph.html`, `graph.svg`: Output files using `graph.` prefix

**Directories:**
- `graphify/`: Main package (lowercase, matches CLI command)
- `tests/`: Pytest convention
- `graphify-out/`: Output directory (hyphenated, conventional)
- `.claude/`, `.codex/`, `.claw/`: Platform config directories (dot-prefixed)

**Classes/Functions:**
- Private: `_function_name()`, `_ClassName` (underscore prefix)
- Public: `function_name()`, `ClassName`
- Constants: `CONSTANT_NAME` (uppercase)
- Examples:
  - `extract()` - main extraction entrypoint
  - `build_from_json()`, `build()` - graph construction
  - `cluster()`, `score_all()` - community detection
  - `god_nodes()`, `surprising_connections()` - analysis
  - `validate_extraction()` - schema validation
  - `validate_url()`, `sanitize_label()` - security
  - `_partition()`, `_split_community()` - private cluster helpers
  - `_is_file_node()` - private analysis helper

**Variables:**
- Node IDs: `node_id`, `nid` (slug format, e.g., `transformer`, `extract_python`)
- Edge IDs: `(source, target)` tuples (NetworkX convention)
- Communities: `cid` (community ID, integer 0+)
- Files: `path`, `Path(...)` objects
- Data dicts: `extraction`, `nodes`, `edges`, `node`, `edge`
- Graphs: `G` (NetworkX graph variable)
- Examples: `source`, `target`, `relation`, `confidence`, `source_file`, `source_location`

## Where to Add New Code

**New Language (e.g., Ruby):**
1. Add `extract_ruby()` function in `graphify/extract.py`
   - Pattern: parse tree-sitter, walk AST, extract classes/functions/calls
   - Register in `extract()` dispatch: add `.rb` suffix check
2. Register suffix in `collect_files()` in `extract.py`
3. Add `.rb` to `CODE_EXTENSIONS` in `detect.py`
4. Add `.rb` to `_WATCHED_EXTENSIONS` in `watch.py` (if supporting watch mode)
5. Add tree-sitter package to `pyproject.toml` dependencies
6. Add fixture file in `tests/fixtures/sample.rb`
7. Add tests in `tests/test_languages.py`

**New Export Format (e.g., ArangoDB):**
1. Add `to_arangodb()` function in `graphify/export.py`
   - Parameters: `G: nx.Graph, out_path: Path`
   - Return: None (writes file)
   - Example: write ArangoDB JSOND format or JavaScript import script
2. Add function to `__init__.py` lazy import map
3. Call from skill.md export orchestration
4. Add tests in `tests/test_export.py`

**New Analysis (e.g., Betweenness Centrality):**
1. Add function to `graphify/analyze.py`
   - Takes: `G: nx.Graph`, optional `communities: dict[int, list[str]]`
   - Returns: dict or list of dicts with results
   - Examples: `betweenness_nodes()`, `coupling_metrics()`
2. Call from skill.md analysis orchestration
3. Add results to GRAPH_REPORT.md via `report.py` generation
4. Add tests in `tests/test_analyze.py`

**New Platform Support (e.g., Claude 2.0):**
1. Create `graphify/skill-claude2.md` by copying `skill.md`
2. Customize for Claude 2.0 syntax/APIs
3. Add platform config dict entry in `__main__.py`:
   ```python
   "claude2": {
       "skill_file": "skill-claude2.md",
       "skill_dst": Path(".claude2") / "skills" / "graphify" / "SKILL.md",
       "claude_md": True,
   }
   ```
4. Test: `graphify install --platform claude2`

**Utility Functions:**
- Shared helpers: `graphify/` directory (not nested)
- Examples: `_make_id()`, `_sanitize_label()`, `_read_text()` in extract.py
- Pattern: Use underscore prefix for module-local helpers, avoid single-letter names

**Tests:**
- Location: `tests/test_<module>.py` (parallel to `graphify/<module>.py`)
- Structure:
  ```python
  from pathlib import Path
  from graphify.<module> import <function>
  
  FIXTURES = Path(__file__).parent / "fixtures"
  
  def test_<function>_<scenario>():
      # Arrange
      input_data = ...
      
      # Act
      result = <function>(input_data)
      
      # Assert
      assert result.key == expected
  ```
- Patterns:
  - Load fixtures from `tests/fixtures/`
  - Use `tmp_path` for filesystem operations (no side effects outside test)
  - No network calls (mock or skip)
  - Test error paths: invalid input, edge cases, empty inputs

## Special Directories

**`graphify-out/`:**
- Purpose: Graph output directory
- Generated: Yes (created by pipeline)
- Committed: No (.gitignore excludes `graphify-out/`)
- Contents:
  - `graph.json` - NetworkX node-link format
  - `GRAPH_REPORT.md` - Human-readable markdown
  - `graph.html` - Interactive vis.js visualization
  - `graph.svg` - Static Graphviz layout
  - `graph.cypher` - Neo4j import script
  - `graph.gml` - GraphML format
  - `wiki/` - Obsidian vault (index.md + community/god-node articles)
  - `cache/` - SHA256 hashes for semantic cache (skip unchanged files)
  - `manifest.json` - File list + metadata

**`tests/fixtures/`:**
- Purpose: Test fixtures and expected outputs
- Generated: No (committed)
- Committed: Yes
- Contents:
  - `extraction.json` - Sample extraction output for build/report tests
  - `sample.py` - Python code fixture for language tests
  - `graphify-out/` - Expected output fixtures (for regression testing)

**`.claude/`:**
- Purpose: Claude Code platform configuration
- Generated: Yes (created by `graphify install`)
- Committed: No (.gitignore excludes `.claude/`)
- Contents:
  - `skills/graphify/SKILL.md` - Installed skill copy
  - `CLAUDE.md` - Updated with graphify skill registration

**`worked/`:**
- Purpose: Reference graphs for documentation
- Generated: Partially (computed graphs in subdirs)
- Committed: Input structure yes, computed outputs vary
- Contents: Example corpora with raw inputs and computed graphs

---

*Structure analysis: 2026-04-09*
