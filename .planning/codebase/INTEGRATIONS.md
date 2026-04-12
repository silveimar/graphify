# External Integrations

**Analysis Date:** 2026-04-09

## APIs & External Services

**Web Content Fetching:**
- Twitter/X oEmbed API - Fetch tweet content
  - Endpoint: `https://publish.twitter.com/oembed`
  - Method: HTTP GET with URL encoding
  - Fallback: Returns URL stub if API fails
  - File: `graphify/ingest.py:_fetch_tweet()` lines 69-99

- arXiv API - Fetch academic paper abstracts
  - Endpoint: `https://export.arxiv.org/abs/{arxiv_id}`
  - Method: HTML scraping (regex extraction)
  - Parses title, abstract, authors from HTML
  - File: `graphify/ingest.py:_fetch_arxiv()` lines 131-146

- Generic web pages - HTTP GET with User-Agent
  - Uses urllib with redirect validation
  - Converts HTML to markdown via html2text (optional fallback: regex stripping)
  - File: `graphify/ingest.py:_fetch_webpage()` lines 102-128

**URL Classification:**
- Twitter/X (x.com, twitter.com)
- arXiv (arxiv.org)
- GitHub (github.com)
- YouTube (youtube.com, youtu.be)
- PDF URLs (*.pdf)
- Images (*.png, *.jpg, *.jpeg, *.webp, *.gif)
- Other web pages
- File: `graphify/ingest.py:_detect_url_type()` lines 27-44

## Data Storage

**Databases:**
- **Neo4j** (optional, push-only)
  - Connection: Bolt protocol (`bolt://localhost:7687` default)
  - Driver: `neo4j.GraphDatabase`
  - Auth: User/password required for `--neo4j-push` operations
  - Usage: MERGE operations (safe to re-run, no duplicates)
  - File: `graphify/export.py:push_to_neo4j()` lines 839-902
  - Cypher generation: `graphify/export.py:to_cypher()` lines 304-324 (manual import alternative)
  - Command: `graphify <path> --neo4j-push bolt://localhost:7687`

**File Storage:**
- **Local filesystem only** - All output to `graphify-out/` directory
  - `graph.json` - NetworkX graph in JSON format
  - `GRAPH_REPORT.md` - Analysis report with god nodes and communities
  - `index.html` - Interactive vis.js visualization
  - `graph.svg` - Static SVG export
  - `graph.graphml` - GraphML format (Gephi-compatible)
  - `cypher.txt` - Cypher commands for Neo4j (if `--neo4j` flag used)
  - `wiki/` - Obsidian vault (if `--obsidian` flag used)
  - Git hook cache files (`.graphify_version`, `.graphify_python`)

**Caching:**
- **SHA256-based semantic cache** (local only)
  - File: `graphify/cache.py`
  - Stores extraction results per file hash
  - Re-runs skip unchanged files
  - Location: `graphify-out/.cache/` (inferred from `cache.py` lines 114+)

## Authentication & Identity

**Auth Provider:**
- **None** - graphify is self-contained
- Neo4j credentials: User must supply URI, username, password for `--neo4j-push`
- Claude Code installation: Multi-platform via `graphify install [--platform P]`
  - Platforms: claude, windows, codex, opencode, claw, droid, trae, trae-cn
  - File: `graphify/__main__.py:_PLATFORM_CONFIG` lines 49-90

**Skill Registration:**
- Registers itself in `~/.claude/CLAUDE.md` for Claude Code (if not already registered)
- Installs platform-specific skill file to user's config directory
- Stores version file to track updates (`.graphify_version`)
- File: `graphify/__main__.py:install()` lines 93-133

## Monitoring & Observability

**Error Tracking:**
- None configured - errors logged to stderr

**Logs:**
- Standard output: Progress messages, summary stats
- Standard error: Warnings (e.g., skill version mismatch), errors (import failures, fetch failures)
- Structured: Version info via `importlib.metadata` or "unknown" fallback
- File: `graphify/__main__.py` lines 10-14

## CI/CD & Deployment

**Hosting:**
- GitHub repository (`https://github.com/silveimar/graphify`)
- PyPI package: `graphifyy` (temporary name, PyPI publish)

**CI Pipeline:**
- GitHub Actions (inferred from recent commits)
  - Tests: Python 3.10, 3.12
  - Command: `pytest tests/ -q`
  - Install: `pip install -e ".[mcp,pdf,watch]"` (CI-matching deps)

**Deployment:**
- PyPI distribution: `pip install graphifyy`
- Skill auto-install: 7 platform variants (Claude Code, Codex, etc.)
- Git hook installation: `graphify install --hooks` (installs post-commit/post-checkout)

## Environment Configuration

**Required env vars:**
- None for core functionality
- Optional for Neo4j push:
  - `NEO4J_URI` - Database connection string
  - `NEO4J_USER` - Database user
  - `NEO4J_PASSWORD` - Database password

**Secrets location:**
- No secrets stored by graphify itself
- Git hooks: Stores `.graphify_version` in project (version tracking only)
- User config: Installs skill files in user's home directory under `.claude/`, `.agents/`, `.config/`, `.claw/`, `.factory/`, `.trae/`, etc.

## Webhooks & Callbacks

**Incoming:**
- Git hooks (optional install):
  - `post-commit` - Auto-rebuild graph after commits
  - `post-checkout` - Auto-rebuild graph after branch switches
  - File: `graphify/hooks.py`

**Outgoing:**
- MCP (Model Context Protocol) server - Stdio-based tool exposure
  - Tools: `query_graph`, `get_node`, `get_neighbors`, `get_community`, `god_nodes`, `graph_stats`, `shortest_path`
  - Transport: Stdio (Claude Desktop / MCP-compatible orchestrators)
  - File: `graphify/serve.py:serve()` lines 107-150
  - Command: `graphify query --mcp` or `graphify <path> --mcp`

## External Validation

**URL validation:**
- Scheme: http/https only (blocks file://, ftp://, data:, etc.)
- IP ranges: Blocks private (10.x, 127.x, 192.168.x), reserved, loopback, link-local
- Cloud metadata: Blocks Google Cloud (metadata.google.internal, metadata.google.com)
- Redirect validation: Re-validates every redirect target (prevents open-redirect SSRF)
- File: `graphify/security.py:validate_url()` lines 26-64

**Fetch limits:**
- Binary download cap: 50 MB
- Text/HTML cap: 10 MB
- Timeout: 30 seconds per request
- File: `graphify/security.py` lines 15-16, 87-99

---

*Integration audit: 2026-04-09*
