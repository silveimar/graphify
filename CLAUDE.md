# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Build & Test Commands

```bash
pip install -e ".[all]"          # install with all optional deps (mcp, neo4j, pdf, watch, leiden, office, routing)
pip install -e ".[mcp,pdf,watch]" # install with CI-matching deps
pip install -e ".[routing]"      # PyYAML + radon for heterogeneous routing (Phase 12)
pytest tests/ -q                  # run all tests
pytest tests/test_extract.py -q   # run a single test file
pytest tests/test_extract.py::test_name -q  # run a single test
graphify --help                   # verify CLI works
```

**Package version** (`pyproject.toml`, PyPI name `graphifyy`): the CLI resolves it via `importlib.metadata`. After a shipped milestone (or any PyPI-facing release), bump, reinstall, sync MCP `server.json` (manifest hash includes `graphify_version`), then test:

```bash
python scripts/bump_version.py 1.1.0   # example next minor
pip install -e ".[mcp,pdf,watch]"
python scripts/sync_mcp_server_json.py
pytest tests/ -q
```

No linter or formatter is configured. CI runs pytest on Python 3.10 and 3.12.

## Architecture

graphify is a Claude Code skill backed by a Python CLI library. The skill file (`graphify/skill.md`) orchestrates the library; the library can be used standalone via the `graphify` CLI.

### Pipeline

```
detect() → extract() → build_graph() → cluster() → analyze() → report() → export()
```

Each stage is a single function in its own module under `graphify/`. They communicate through plain dicts and NetworkX graphs — no shared state, no side effects outside `graphify-out/`. For **non-vault** runs (`ResolvedOutput.source == "default"`), routing-audit and related artifact paths use a **single cwd-relative** `graphify-out/` via `default_graphify_artifacts_dir()` (not a nested `…/corpus-subdir/graphify-out/`). Legacy nested folders may still exist on disk; graphify does not delete them.

### Key modules

| Module | Role |
|--------|------|
| `detect.py` | File discovery with `.graphifyignore` support |
| `extract.py` | Dual extraction: deterministic tree-sitter AST for code, LLM for docs/images |
| `build.py` | Merges extraction dicts into a single `nx.Graph` |
| `cluster.py` | Leiden community detection (graph-topology-based, no embeddings) |
| `analyze.py` | God nodes, surprising connections, suggested questions |
| `report.py` | Renders `GRAPH_REPORT.md` from graph + analysis |
| `export.py` | HTML viz (vis.js), JSON, SVG, GraphML, Obsidian vault, Neo4j Cypher |
| `wiki.py` | Wikipedia-style markdown articles per community |
| `serve.py` | MCP stdio server exposing graph queries + CLI `query` traversal |
| `__main__.py` | CLI entrypoint, skill install/uninstall for 7 platforms |
| `security.py` | All external input validation (URLs, paths, labels) |
| `validate.py` | Schema enforcement for extraction output |
| `hooks.py` | Git post-commit/post-checkout hook install |
| `cache.py` | SHA256-based semantic cache so re-runs skip unchanged files |

### Extraction output schema

Every extractor returns `{"nodes": [...], "edges": [...]}` where each node has `id`, `label`, `source_file`, `source_location` and each edge has `source`, `target`, `relation`, `confidence` (EXTRACTED/INFERRED/AMBIGUOUS). `validate.py` enforces this before `build_graph()`.

### Multi-platform support

The CLI installs skill files and hooks for Claude Code, Codex, OpenCode, OpenClaw, Factory Droid, Trae, and Trae CN. Platform configs live in `_PLATFORM_CONFIG` dict in `__main__.py`. Each platform has its own skill file variant (`skill.md`, `skill-codex.md`, etc.).

### Adding a new language

1. Add `extract_<lang>()` in `extract.py` (tree-sitter parse → walk → nodes/edges)
2. Register suffix in `extract()` dispatch and `collect_files()`
3. Add suffix to `CODE_EXTENSIONS` in `detect.py` and `_WATCHED_EXTENSIONS` in `watch.py`
4. Add tree-sitter package to `pyproject.toml`
5. Add fixture in `tests/fixtures/` and tests in `tests/test_languages.py`

## Upstream Sync

This is a fork. The original repo is configured as the `upstream` remote (local bare clone at `graphify-origin`). To sync new upstream releases:

1. `git fetch upstream` — pull the new vN branch
2. `git checkout vN && git push origin vN` — push it to the fork
3. `gh pr create --base main --head vN` — PR it into main

Never commit directly to vN branches — they are clean import points from upstream. All custom work (e.g. ideaverse-integration) lives on feature branches merged into `main`.

## Testing Conventions

- One test file per module (`tests/test_<module>.py`)
- All tests are pure unit tests — no network calls, no filesystem side effects outside `tmp_path`
- PyPI package name is `graphifyy` (temporary); CLI and internal references use `graphify`

## Security

All external input passes through `graphify/security.py`: URL validation, redirect blocking, size caps, path confinement to `graphify-out/`, label sanitization (HTML-escape, control char strip). See `SECURITY.md` for the full threat model.

<!-- GSD:project-start source:PROJECT.md -->
## Project

**Ideaverse Integration — Configurable Vault Adapter**

A configurable output adapter for graphify that injects knowledge graph data (nodes, edges, communities, analysis) into existing Obsidian vaults as properly-structured notes. Instead of graphify's current flat dump, the adapter reads a framework profile from the target vault (`.graphify/profile.yaml` + templates) and produces notes with correct frontmatter, wikilinks, tags, Dataview queries, folder placement, and naming conventions. When no vault profile exists, graphify falls back to a built-in default profile producing Ideaverse-compatible ACE structure.

**Core Value:** Graphify can inject knowledge into any Obsidian vault framework — Ideaverse, custom fusions, or future frameworks — without code changes, driven entirely by a declarative vault-side profile.

### Constraints

- **Python 3.10+**: Must work on CI targets (Python 3.10 and 3.12)
- **No new required dependencies**: Profile parsing uses stdlib (`yaml` via PyYAML already optional, `json` stdlib). Template rendering uses simple string substitution, not Jinja2.
- **Backward compatible**: Running `graphify --obsidian` without a profile in the target vault must produce output similar to current behavior
- **Existing test patterns**: Pure unit tests, no network calls, no filesystem side effects outside `tmp_path`
- **Security**: All file paths confined to output directory per `security.py` patterns. Template placeholders must be sanitized (no injection via node labels).
<!-- GSD:project-end -->

<!-- GSD:stack-start source:codebase/STACK.md -->
## Technology Stack

## Languages
- **Python** 3.10+ - Core CLI library and all pipeline stages (`graphify/`)
- **JavaScript** - HTML visualization (vis.js integration in `graphify/export.py`)
- **Markdown** - Skill files for 7 different AI coding assistant platforms
## Runtime
- **Python** 3.10, 3.12 (CI tested on both)
- Standard library only for core features; optional dependencies for extended functionality
- **pip** / **setuptools**
- Lockfile: Not used (pure setuptools, no lock file)
- PyPI package name: `graphifyy` (CLI/imports: `graphify`)
## Frameworks
- **NetworkX** - Graph data structure and manipulation (primary abstraction)
- **tree-sitter** >=0.23.0 - Deterministic AST parsing for code extraction
- **graspologic** (optional: leiden)
- **html2text** (optional: pdf extraction)
## Key Dependencies
- **networkx** - Graph representation and algorithms (no version pin)
- **tree-sitter** >=0.23.0 - Code parsing backbone
- **tree-sitter-{language}** (16 packages) - Language-specific parsers for code extraction
- **mcp** (optional) - Model Context Protocol server for agent integration (`graphify/serve.py`)
- **neo4j** (optional) - Direct push to Neo4j instances (`graphify/export.py:push_to_neo4j`)
- **graspologic** (optional) - Leiden clustering (better than Louvain, wrapped in `graphify/cluster.py`)
- **python-docx** (optional) - Office document extraction (docx)
- **openpyxl** (optional) - Excel spreadsheet extraction (xlsx)
- **pypdf** (optional) - PDF text extraction
- **watchdog** (optional) - File system monitoring for incremental re-runs
## Configuration
- No `.env` file required for core functionality
- Optional environment variables for Neo4j when using `--neo4j-push`:
- URLs for web/tweet/arxiv ingest validated via `graphify/security.py` (SSRF, redirect protection)
- `pyproject.toml` - Single source of truth for dependencies, entry points, and skill file packaging
## Platform Requirements
- Python 3.10+ with pip
- tree-sitter C parser (built from wheel)
- Optional: graspologic (requires scikit-learn, scipy)
- Python 3.10+ standalone
- No system dependencies required for core (tree-sitter wheels include binaries)
- Deployment targets:
<!-- GSD:stack-end -->

<!-- GSD:conventions-start source:CONVENTIONS.md -->
## Conventions

## Naming Patterns
- Lowercase with underscores: `extract.py`, `validate.py`, `security.py`
- Test files: `test_<module>.py` (one per module: `test_extract.py` pairs with `extract.py`)
- Skills/platform variants: `skill.md`, `skill-codex.md`, `skill-opencode.md`, etc.
- Lowercase with underscores: `validate_url()`, `safe_fetch()`, `god_nodes()`
- Private helpers (module-level): leading underscore: `_make_id()`, `_read_text()`, `_is_file_node()`
- Import handlers: `_import_python()`, `_import_js()`, `_import_java()` (language-specific)
- Lowercase with underscores: `source_files`, `node_ids`, `communities`
- Constants: UPPERCASE_WITH_UNDERSCORES: `_MAX_FETCH_BYTES = 52_428_800`, `_BLOCKED_HOSTS = {...}`
- Dict/list parameters with clear semantics: `extraction`, `data`, `edges`, `nodes` (not `d`, `e`)
- Loop variables: short names when semantically clear: `n` for node, `e` for edge, `i` for index
- Type hints on all functions (checked via mypy-like reasoning in code): `def validate_url(url: str) -> str:`
- Use `from __future__ import annotations` for forward compatibility (present in all modules)
- Dict types explicit: `dict[int, list[str]]` (not `Dict`)
- Optional types: `str | None` (not `Optional[str]`)
- Callable types: `Callable | None`
- Generated by `_make_id()` - stable, deterministic transformation of names
- Lowercase alphanumeric + underscores: `transformer`, `extract_python`, `n_attention`
- Special prefixes in tests: `n_` for test nodes (`n_transformer`, `n_concept_attn`)
## Code Style
- No formatter configured (see CLAUDE.md)
- 4-space indentation (Python convention)
- Docstrings on functions and classes (not enforced, but present in public APIs)
- Comments above code blocks, not inline (prefer readable code names)
- No linter configured (see CLAUDE.md)
- Consistent with PEP 8 spirit, but not enforced by tooling
- Tests run on Python 3.10 and 3.12 (CI requirement from pyproject.toml)
- Imports at top: stdlib, then third-party, then local
- `from __future__ import annotations` as first import
- Module docstring (single-line) as first line after future import
- Example from `extract.py`:
## Import Organization
- None detected - uses relative imports (`.extract`, `.security`) within graphify package
- Absolute imports from package root: `from graphify.security import validate_url`
## Error Handling
- Domain-specific exceptions raised with clear messages: `raise ValueError(f"Blocked URL scheme ...")`
- Validation before processing: `validate_extraction(data)` returns list of errors (not raising immediately)
- Warning messages to stderr: `print(f"[graphify] ... warning", file=sys.stderr)`
- Silent fallback (Leiden → Louvain): try-except ImportError to gracefully degrade
- Example from `security.py`:
- Return list of error strings: `validate_extraction(data: dict) -> list[str]`
- Empty list = valid, non-empty = errors found
- Example from `validate.py`:
## Logging
- Errors and warnings to stderr: `print(f"[graphify] ...", file=sys.stderr)`
- Info/progress to stdout (if needed)
- Prefix with `[graphify]` for CLI visibility
- Example from `build.py`:
- During library calls (suppress output from graspologic to prevent corrupting terminal)
- Use `contextlib.redirect_stdout()` to suppress third-party output
- Example from `cluster.py`:
## Comments
- High-level algorithm explanation (e.g., node deduplication strategy in `build.py`)
- Non-obvious design decisions (e.g., why a fallback strategy exists)
- Security/invariant notes (e.g., "dangling edges are expected for stdlib imports")
- Complex regex patterns with explanation
- Do NOT comment trivial code: `x = 1  # set x to 1` is noise
- Not used in Python codebase
- Docstrings: present on public functions and classes
- Example from `security.py`:
## Function Design
- Helper functions break logic into steps: `_read_text()`, `_resolve_name()`, `_find_body()`
- Language-specific import handlers: `_import_python()`, `_import_js()` (separate functions, not nested)
- Max file size: `extract.py` is 2000+ lines due to multi-language extraction (exception, not rule)
- Explicit parameters, not `**kwargs` (except where needed for compatibility)
- Dataclass for complex configs: `LanguageConfig` in `extract.py` (25 fields organized logically)
- Position-dependent: `path` first, then optional parameters
- Example from `extract.py`:
- Always explicit: functions return dicts (extraction format) or graphs or lists
- Consistent shape: extraction always returns `{"nodes": [...], "edges": [...]}`
- No implicit None returns - return empty dict/list if nothing found
- Example from `validate.py`:
## Module Design
- No `__all__` defined, but clear public API via `__init__.py`
- Lazy loading in `__init__.py`:
- Allows `graphify install` before heavy dependencies are loaded
- `__init__.py` is minimal - only exposes lazy-loaded functions
- No barrel file pattern for grouping modules (each module is standalone)
- Tests import directly from modules: `from graphify.extract import extract_python`
## Edge Attributes Schema
- `source`, `target`: node IDs
- `relation`: type of edge ("contains", "method", "imports", "calls", etc.)
- `confidence`: "EXTRACTED", "INFERRED", or "AMBIGUOUS"
- `source_file`: path where edge was found
- `weight`: float (usually 1.0 for structural edges)
- Optional `confidence_score`: float (for INFERRED edges, typically 0.5-1.0)
- `id`: unique identifier (lowercased, underscore-separated)
- `label`: human-readable name (e.g., "Transformer", "extract_python()")
- `file_type`: "code", "document", "paper", "image", "rationale"
- `source_file`: where it was found (file path or empty for concepts)
- `source_location`: optional (e.g., "L42" for line number)
<!-- GSD:conventions-end -->

<!-- GSD:architecture-start source:docs/ARCHITECTURE.md -->
## Architecture

## Pattern Overview
- Single-direction data flow through 7 pipeline stages
- Each stage is a pure function returning plain dicts/NetworkX graphs
- No shared mutable state between stages
- Deterministic extraction via tree-sitter AST + semantic LLM analysis
- Community detection with optional splitting for scale
- Multiple export formats (HTML, JSON, SVG, GraphML, Obsidian vault, Neo4j Cypher)
## Pipeline
```
```
## Layers
- Purpose: Discover files, classify by type, validate corpus size
- Location: `graphify/detect.py`
- Contains: File classification (code/document/paper/image), sensitivity checking (skip secrets), paper detection heuristics
- Depends on: `pathlib`, regex
- Used by: CLI entrypoint, skill orchestration
- Purpose: Parse code via tree-sitter AST, analyze docs/images via LLM
- Location: `graphify/extract.py` (2719 lines - largest module)
- Contains: Language-specific extractors (Python, TypeScript, Go, Rust, Java, C++, etc.), import handlers, call graph walking, semantic extraction via Claude API
- Depends on: tree-sitter (py/ts/go/rs/java/cpp...), `cache.py`, `security.py`, `validate.py`
- Used by: Build layer, CLI
- Purpose: Merge extractions, validate schema, construct graph
- Location: `graphify/build.py` (70 lines)
- Contains: `build_from_json()`, `build()` - combines dicts into single NetworkX graph
- Depends on: `validate.py`, networkx
- Used by: Cluster layer, skill
- Purpose: Community detection and scoring
- Location: `graphify/cluster.py` (132 lines)
- Contains: Leiden (graspologic) with Louvain fallback, community splitting, cohesion scoring
- Depends on: networkx, graspologic (optional)
- Used by: Analyze layer, skill
- Purpose: Extract insights - god nodes, surprising connections, knowledge gaps
- Location: `graphify/analyze.py` (523 lines)
- Contains: God node ranking (degree), cross-file/cross-community edge detection, knowledge gap detection (isolated, thin communities, high ambiguity)
- Depends on: networkx
- Used by: Report layer, skill
- Purpose: Generate markdown audit trail
- Location: `graphify/report.py` (155 lines)
- Contains: Confidence breakdown, community summaries, gap analysis, suggested questions
- Depends on: datetime
- Used by: Export layer, skill
- Purpose: Generate multiple output formats
- Location: `graphify/export.py` (989 lines)
- Contains: HTML (vis.js + sidebar), JSON, SVG, GraphML, Obsidian vault, Neo4j Cypher, Wiki (markdown articles per community)
- Depends on: networkx, html, json, math, graphviz (for SVG), `security.py`
- Used by: CLI, skill
- URL validation: scheme checks, IP range blocking, cloud metadata protection
- Redirect validation: re-validates all redirects to prevent open-redirect SSRF
- Label sanitization: strips control chars, caps length for HTML embedding
- Path confinement: graph paths must stay inside `graphify-out/`
- Used by: extract, ingest, export, serve
- Validates node/edge dicts before graph assembly
- Checks required fields: node={id, label, file_type, source_file}, edge={source, target, relation, confidence, source_file}
- Validates confidence values: EXTRACTED, INFERRED, AMBIGUOUS
- Used by: build
- Skips unchanged files to save LLM tokens
- Caches by file hash, stores in `graphify-out/cache/`
- Used by: extract
- Saves as annotated markdown with metadata (title, author, date)
- Used by: Manual integration, CLI
- Exposes graph query tools to Claude and agents
- BFS/DFS traversal, node search, subgraph extraction
- Used by: Skill for agent interaction
- One article per community + god node articles
- Index.md with navigation
- Cross-community links with edge counts
- Used by: Export layer
- Rebuilds code extraction on file changes
- Used by: Optional watch mode
- Auto-refresh graph after code changes
- Multi-platform support (7 platforms)
- Used by: Installation
- Token cost, extraction time, graph stats
- Used by: Skill, debugging
## Data Flow - Detailed Example
## State Management
- No global state - graph is built fresh each run
- Node deduplication happens at three levels:
- Leiden produces deterministic partitions (seed=42)
- Communities are re-indexed by size descending for consistent ordering
- Cohesion scores computed post-partition
- Extraction results cached by file hash in `graphify-out/cache/`
- Re-runs skip unchanged files (LLM calls skipped)
- Cache invalidated on file modification
## Key Abstractions
- Represents: class, function, variable, concept, document, image
- Identity: stable `id` (slugified from name/path)
- Attributes: `label` (display name), `source_file`, `source_location`, `file_type`, `community` (assigned after clustering)
- Examples: `transformer`, `extract_python`, `api_endpoint`, `ml_model_training_concept`
- Represents: relationship between nodes
- Types (relation): `defines_class`, `defines_function`, `calls`, `imports`, `contains`, `references`, `semantically_similar_to`, etc.
- Confidence: `EXTRACTED` (AST-found, high confidence), `INFERRED` (LLM with confidence_score 0.0-1.0), `AMBIGUOUS` (uncertain)
- Attributes: `source_file` (where detected), `relation` type, `confidence`, optional `confidence_score` for INFERRED
- Examples: `class_A → contains → method_x` (EXTRACTED), `AuthService → imports → TokenValidator` (EXTRACTED), `Component → semantically_similar_to → Template` (INFERRED 0.85)
- Represents: cluster of closely-related nodes
- Identified by: integer community_id (0 = largest after splitting)
- Metrics: cohesion score (0.0-1.0, ratio of actual/possible internal edges)
- Contains: typically 3-20 real nodes (method/class stubs filtered from display)
- Example: Community 0 = "transformer layer" (Transformer, Attention, LayerNorm, etc.)
- `code` - source code (py, ts, js, go, rs, java, cpp, c, rb, swift, kt, cs, scala, php, lua, zig, ps1, ex, m, jl)
- `document` - markdown/text (md, txt, rst)
- `paper` - academic PDF (detected via signal heuristics)
- `image` - visual content (png, jpg, jpeg, gif, webp, svg)
- `rationale` - synthetic explanation nodes (semantic extraction)
## Entry Points
- Location: `graphify/__main__.py` (652 lines)
- Entrypoint: `__main__.py` exposes: `install`, `uninstall`, `run`, `query`, `watch` commands
- Platform config: dict of 8 platforms (Claude Code, Codex, OpenCode, OpenClaw, Factory Droid, Trae, Trae CN, Windows)
- Skill files: 7 platform variants (`skill.md`, `skill-codex.md`, etc.) installed to platform-specific directories
- Hook registration: updates `.claude/CLAUDE.md`, `.codex/hooks.json`, OpenCode plugins, git hooks
- Location: `graphify/skill.md` (50K lines - Claude Code / Codex agent prompt)
- Role: Coordinates pipeline, handles user prompts (`/graphify`), integrates detection → extraction → build → cluster → analyze → report → export
- Handles: LLM integration for semantic extraction, caching, multi-file corpus
- Location: `graphify/serve.py` (325 lines)
- Entrypoint: stdio server for agents
- Exposes: graph loading, BFS/DFS traversal, node search, subgraph extraction
## Cross-Cutting Concerns
- Approach: Uses `print()` to stderr for warnings/errors, stdout for user-facing output
- Patterns:
- All external input passes through `graphify/security.py`
- URL validation: scheme checks, IP range blocking, cloud metadata endpoints, redirect validation
- Path validation: graph paths confined to `graphify-out/`
- Label sanitization: HTML-escape, control char strip, length cap (256 chars)
- Extraction schema: validated by `validate.py` before graph construction
- Node/edge required fields enforced
- Approach: API keys passed via environment variables (Claude API key for semantic extraction)
- Not persisted in graph - only token cost metrics stored
- OAuth for Github/Arxiv/PDF URLs handled by `ingest.py`
- Strategy: Fail loudly with actionable messages, but continue when safe
- Patterns:
<!-- GSD:architecture-end -->

<!-- GSD:skills-start source:skills/ -->
## Project Skills

No project skills found. Add skills to any of: `.claude/skills/`, `.agents/skills/`, `.cursor/skills/`, or `.github/skills/` with a `SKILL.md` index file.
<!-- GSD:skills-end -->

<!-- GSD:workflow-start source:GSD defaults -->
## GSD Workflow Enforcement

Before using Edit, Write, or other file-changing tools, start work through a GSD command so planning artifacts and execution context stay in sync.

Use these entry points:
- `/gsd-quick` for small fixes, doc updates, and ad-hoc tasks
- `/gsd-debug` for investigation and bug fixing
- `/gsd-execute-phase` for planned phase work

Do not make direct repo edits outside a GSD workflow unless the user explicitly asks to bypass it.
<!-- GSD:workflow-end -->

<!-- GSD:profile-start -->
## Developer Profile

> Profile not yet configured. Run `/gsd-profile-user` to generate your developer profile.
> This section is managed by `generate-claude-profile` -- do not edit manually.
<!-- GSD:profile-end -->
