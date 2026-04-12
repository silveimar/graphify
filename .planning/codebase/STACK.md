# Technology Stack

**Analysis Date:** 2026-04-09

## Languages

**Primary:**
- **Python** 3.10+ - Core CLI library and all pipeline stages (`graphify/`)

**Secondary:**
- **JavaScript** - HTML visualization (vis.js integration in `graphify/export.py`)
- **Markdown** - Skill files for 7 different AI coding assistant platforms

## Runtime

**Environment:**
- **Python** 3.10, 3.12 (CI tested on both)
- Standard library only for core features; optional dependencies for extended functionality

**Package Manager:**
- **pip** / **setuptools**
- Lockfile: Not used (pure setuptools, no lock file)
- PyPI package name: `graphifyy` (CLI/imports: `graphify`)

## Frameworks

**Core:**
- **NetworkX** - Graph data structure and manipulation (primary abstraction)
  - `nx.Graph` is the canonical in-memory representation
  - `networkx.readwrite.json_graph` for serialization
  - `nx.community.louvain_communities` for fallback clustering

**Code Analysis:**
- **tree-sitter** >=0.23.0 - Deterministic AST parsing for code extraction
  - Language parsers: python, javascript, typescript, go, rust, java, c, c++, ruby, c#, kotlin, scala, php, swift, lua, zig, powershell, elixir, objective-c, julia
  - All tree-sitter-* packages listed in `pyproject.toml` lines 16-35
  - Version guard required: `graphify/validate.py` enforces tree-sitter >=0.23.0 (issue #127)

**Clustering:**
- **graspologic** (optional: leiden)
  - High-quality Leiden community detection if installed
  - Falls back to NetworkX's Louvain if not
  - stderr redirection required on Windows PowerShell 5.1 to prevent ANSI escape corruption (issue #19, `graphify/cluster.py` lines 34-40)

**Document Conversion:**
- **html2text** (optional: pdf extraction)
  - Converts HTML to markdown when available
  - Falls back to regex stripping if not installed

## Key Dependencies

**Critical:**
- **networkx** - Graph representation and algorithms (no version pin)
- **tree-sitter** >=0.23.0 - Code parsing backbone
- **tree-sitter-{language}** (16 packages) - Language-specific parsers for code extraction

**Infrastructure:**
- **mcp** (optional) - Model Context Protocol server for agent integration (`graphify/serve.py`)
- **neo4j** (optional) - Direct push to Neo4j instances (`graphify/export.py:push_to_neo4j`)
  - Uses `neo4j.GraphDatabase` driver with Bolt protocol
- **graspologic** (optional) - Leiden clustering (better than Louvain, wrapped in `graphify/cluster.py`)
- **python-docx** (optional) - Office document extraction (docx)
- **openpyxl** (optional) - Excel spreadsheet extraction (xlsx)
- **pypdf** (optional) - PDF text extraction
- **watchdog** (optional) - File system monitoring for incremental re-runs

## Configuration

**Environment:**
- No `.env` file required for core functionality
- Optional environment variables for Neo4j when using `--neo4j-push`:
  - `NEO4J_URI` (default: `bolt://localhost:7687`)
  - `NEO4J_USER` (default: `neo4j`)
  - `NEO4J_PASSWORD` (required if pushing)
- URLs for web/tweet/arxiv ingest validated via `graphify/security.py` (SSRF, redirect protection)

**Build:**
- `pyproject.toml` - Single source of truth for dependencies, entry points, and skill file packaging
  - Entry point: `graphify = "graphify.__main__:main"`
  - Package data: skill files for 7 platforms (`skill.md`, `skill-codex.md`, etc.) included in wheel

## Platform Requirements

**Development:**
- Python 3.10+ with pip
- tree-sitter C parser (built from wheel)
- Optional: graspologic (requires scikit-learn, scipy)

**Production:**
- Python 3.10+ standalone
- No system dependencies required for core (tree-sitter wheels include binaries)
- Deployment targets:
  - Claude Code (skill install: `graphify install`)
  - Codex, OpenCode, OpenClaw, Factory Droid, Trae, Trae CN (platform-specific skill installs)
  - Standalone CLI: `graphify <path>` or `graphify --help`

---

*Stack analysis: 2026-04-09*
