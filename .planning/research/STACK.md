# Stack Research — graphify v1.4 (Agent Discoverability & Obsidian Workflows)

**Domain:** Python CLI + library + MCP stdio server — incremental milestone on a shipped product
**Researched:** 2026-04-17
**Confidence:** HIGH (MCP SDK, radon, APScheduler, jsonschema all verified on PyPI + Context7); MEDIUM for manifest format (MCP v2 migration in flight, no registry-spec-1.0 yet); MEDIUM for SPAR-Kit (no Python package on PyPI, implemented as protocol/prompts not library).

---

## Scope Discipline (read first)

This is a **SUBSEQUENT milestone** on a production codebase. The existing core stack is locked and working:

- Python 3.10 + 3.12 (CI matrix)
- `networkx` 3.4.2, `tree-sitter` >=0.23.0 (+ 16 language parsers), `mcp` 1.27.0, `graspologic` (Leiden), `PyYAML` 6.0.3, `sentence-transformers` 5.4.1, `watchdog` 6.0.0, `pypdf`, `python-docx`, `openpyxl`.

**Not re-researched.** All recommendations below answer exactly one question: *what new pin gets added to `pyproject.toml` (and to which optional extra) for each v1.4 phase?* Everything that can be done with the stdlib **is** done with the stdlib, per the "no new required deps" constraint already established by the `[dedup]`, `[obsidian]`, `[leiden]` precedent.

---

## Recommended Stack (per phase)

### Phase 12 — Heterogeneous Extraction Routing

| Technology | Version | Purpose | Why Recommended |
|------------|---------|---------|-----------------|
| **`concurrent.futures.ThreadPoolExecutor`** | stdlib (3.10+) | Parallel fan-out of LLM extraction calls across a file batch | Extraction is **I/O-bound** (HTTP to Anthropic/OpenAI/local endpoints), not CPU-bound. The GIL is released during `socket.recv`, so threads beat `multiprocessing` (no pickle cost, no process setup) and beat `asyncio` (the Anthropic SDK call path in `graphify/extract.py` is synchronous today; going asyncio would force a rewrite of every extractor). Pool size = number of endpoints ≈ 4–8. This is literally the one-liner option. |
| **`radon`** | 6.0.1 | Cyclomatic complexity + maintainability index from Python source | `radon.complexity.cc_visit(source)` and `radon.metrics.mi_visit` run on raw source (their own AST walk, no tree-sitter hook). Mature (since 2012), zero transitive deps beyond `mando`+`colorama`, pure-Python, Python 3.10/3.12 compatible. Returns per-function `ComplexityVisitor` objects with `.complexity`, `.name`, `.lineno` — trivially aggregatable into a per-file score. |
| **tree-sitter-derived metrics** (stdlib only) | n/a | Nesting depth, import count, node count — **non-Python** languages | For the 15 other languages graphify already parses, `radon` doesn't help. Piggyback on the tree-sitter `Tree` that `graphify/extract.py` already produces: walk the tree counting `max_depth`, `len(import_nodes)`, `len(function_nodes)`. Pure-Python, reuses existing parse, no new library. |

**Integration path:** New module `graphify/routing.py` exposing `score_complexity(path, source, tree=None) -> ComplexityScore` (dict with `cc`, `nesting_depth`, `imports`, `node_count`, `recommended_tier`). `extract.py` imports it and consults the score before dispatching to `extract_python_llm()` vs an eventual `extract_python_llm_cheap()`. Parallelism sits **outside** individual extractors: a new `extract.extract_batch(paths, max_workers=N)` wraps the existing single-file extractors in a `ThreadPoolExecutor`.

**Optional extra:** New `[routing]` extra pinning only `radon`. Tree-sitter metric walker has no new dep. `ThreadPoolExecutor` is stdlib.

```toml
[project.optional-dependencies]
routing = ["radon>=6.0.1"]
```

### Phase 13 — Agent Capability Manifest

| Technology | Version | Purpose | Why Recommended |
|------------|---------|---------|-----------------|
| **JSON Schema draft 2020-12** (no library) | n/a | Manifest schema format | MCP's own `Tool.inputSchema` already uses JSON Schema. A capability manifest that *describes* the MCP server is a flat JSON/YAML document — writing it out only needs `json.dumps()`. We do not need a validator at write time. |
| **`jsonschema`** | 4.26.0 | **Optional** validator for `graphify validate-manifest` CLI and CI guard | Same library MCP SDK itself already depends on transitively (`pip show mcp` shows `jsonschema` as required). Installing `[mcp]` already brings it in, so our `[manifest]` validator costs **zero extra install weight** for anyone with `[mcp]`. Draft 2020-12 supported. |
| **`PyYAML`** | 6.0.3 | Manifest file format (`.mcp/manifest.yaml` optional alt) | Already in `[obsidian]` extra. Reuse. |

**Emerging-standard finding (MEDIUM confidence):** There is **no settled "MCP server registry manifest 1.0" spec** as of 2026-04. The `modelcontextprotocol/python-sdk` v2 migration (on `main` branch, not yet released to PyPI — latest release is v1.27.0 on the `v1.x` branch) reworks `get_server_capabilities()` into an `initialize_result` property but does **not** introduce a separate manifest file format. The community has divergent stabs (`schema.org/SoftwareApplication`, OpenAPI-style JSON, ad-hoc `server.json`). **Recommendation: ship a graphify-native manifest now under our own schema, JSON-Schema-validatable, and plan a migration when a registry standard lands.** This is directly analogous to how `[obsidian]` shipped the vault profile before any community standard existed.

**Proposed manifest shape** (informs Phase 13 requirements, not locked here):

```json
{
  "$schema": "https://graphify.dev/schemas/manifest-v1.json",
  "name": "graphify",
  "version": "0.5.0",
  "description": "Any input to knowledge graph...",
  "mcp": {
    "transport": "stdio",
    "tools": [ { "name": "query_graph", "inputSchema": {...}, "outputSchema": {...} } ]
  },
  "capabilities": {
    "slash_commands": ["/trace", "/connect", "/drift", "/emerge"],
    "output_formats": ["html", "json", "obsidian", "neo4j"],
    "languages": ["py", "js", "ts", "go", "rs", "java", "cpp", ...]
  },
  "discovery": {
    "install_command": "pip install graphifyy[mcp]",
    "invoke_command": "graphify serve"
  }
}
```

**Integration path:** New module `graphify/manifest.py` — pure stdlib except the optional validator. CLI: `graphify manifest [--format json|yaml] [--validate]`. Placement in `__main__.py` as a new subcommand alongside `install`, `uninstall`, `run`, `query`, `watch`, `serve`. The manifest is generated by **introspecting** `serve.py` — we walk registered handlers (`on_call_tool` dispatch table) to auto-populate the `tools` array instead of maintaining a hand-written copy.

**Optional extra:** None new. Bundled under the implicit "core" for `graphify manifest` (just stdlib `json`). The validator reuses `jsonschema` which is transitively in `[mcp]`.

### Phase 14 — Obsidian Thinking Commands

| Technology | Version | Purpose | Why Recommended |
|------------|---------|---------|-----------------|
| **Existing `graphify/commands/` infrastructure** | n/a | Slash command distribution | Phase 11 already shipped `/trace`, `/connect`, `/drift`, `/emerge` as static markdown prompts under `graphify/commands/` wired into `_PLATFORM_CONFIG`'s `commands_dst` for Claude Code. Phase 14 is a **content + install-path** extension, not a new dependency. The `pyproject.toml` already lists `commands/*.md` under `[tool.setuptools.package-data]`. |
| **`PyYAML`** | 6.0.3 (existing `[obsidian]` extra) | Parse vault profile to know which Obsidian folder hierarchy to target | Already a v1.0 dep. No change. |

**Integration path:** Extend `_PLATFORM_CONFIG` in `__main__.py` so every harness (not just `claude`) gets `commands_enabled=True` where the harness supports slash commands. Codex, OpenCode, Trae all now document `/commands` directories — add them. Write new command files under `graphify/commands/` (e.g. `obsidian-trace.md`) that explicitly reference vault paths from the Ideaverse profile.

**Optional extra:** None new. Everything fits under existing `[obsidian]` + package_data.

### Phase 15 — Async Background Enrichment

| Technology | Version | Purpose | Why Recommended |
|------------|---------|---------|-----------------|
| **`asyncio.Queue` + `asyncio.Task`** | stdlib (3.10+) | In-process task queue for post-build derivers | Honcho's own deriver pattern (see research) is a **worker-pool polling a DB queue**; that's overkill for a CLI process. Graphify runs in-process, single-invocation, and the trigger is either (a) the existing `graphify watch` loop (already event-driven via `watchdog`), or (b) a post-build hook. We don't need persistence across process boundaries — enrichment state lives in `graphify-out/` JSON files. `asyncio.Queue` + a handful of worker tasks inside one event loop is the right weight. |
| **`APScheduler`** | 3.11.2 (**optional**) | Periodic staleness re-scoring if `graphify watch` is used as a long-lived daemon | Only needed if users want graphify to self-trigger enrichment on a wall-clock schedule (e.g., "re-rank god nodes every 30 minutes"). `BackgroundScheduler` runs in a thread, integrates cleanly with `watchdog`. **Add only if Phase 15 requirements explicitly call for timed triggers** — otherwise this is scope creep and `asyncio.Queue` alone is sufficient. |
| **`watchdog`** | 6.0.0 (existing `[watch]` extra) | File-change-triggered enrichment | Already present. Reuse. |

**Integration path:** New module `graphify/enrich.py` with `async def run_derivers(graph_path, passes=[...])`. Each "deriver" is a plain async function `async def enrich_descriptions(graph) -> dict[node_id, patch]` that reads the graph, computes a patch, writes through a lock (reuse `_append_annotation` / `_save_agent_edges` atomic-write patterns already in `serve.py`). CLI wiring: `graphify enrich [--watch]` calls `asyncio.run(run_derivers(...))`. Honcho's worker count, polling interval, and queue semantics are **explicitly NOT ported** — those exist because Honcho is a multi-tenant service, graphify is a local tool.

**Optional extra:** New `[enrich]` extra. Pin APScheduler only if wall-clock triggers are in requirements.

```toml
[project.optional-dependencies]
enrich = ["apscheduler>=3.11.2"]  # only if timed triggers are required
```

Otherwise: **no new extra**. `asyncio` is stdlib.

### Phase 16 — Graph Argumentation Mode

| Technology | Version | Purpose | Why Recommended |
|------------|---------|---------|-----------------|
| **Existing `graphify/autoreason.py`** (Phase 9) | n/a | LLM orchestration for 4-perspective tournaments | Phase 9 already ships the tournament runner with 4 lenses × 4 rounds (A/B/AB/blind-Borda). Phase 16's argumentation flow is the **same abstraction**: spawn N personas, they argue over a shared substrate, synthesize. Extend the existing module; do **not** add a second LLM orchestration path. |
| **`networkx` subgraph views** | 3.4.2 (existing core) | SPAR-Kit's ABSTRACT substrate implementation | SPAR-Kit's POPULATE→ABSTRACT→RUMBLE→KNIT protocol is a **prompt pattern**, not a Python library. There is no `pip install spar-kit`. ABSTRACT is just "constrained subgraph view given a question" — `nx.subgraph()` + `nx.ego_graph()` already implement it. POPULATE pulls context from the graph (already done by `serve.py`'s MCP tools). RUMBLE is the N-perspective LLM argument (the autoreason tournament). KNIT is the synthesis writer (report.py pattern). |

**SPAR-Kit finding (MEDIUM confidence):** `synthanai/spar-kit` on GitHub (referenced in the roadmap) is a **protocol specification + prompt set**, not a distributable Python package. There is no PyPI release. The correct integration is to adopt the protocol's phase names as our own code structure (`populate`, `abstract`, `rumble`, `knit` functions in `graphify/argue.py`) and implement each using stack we already have.

**Integration path:** New module `graphify/argue.py` reusing `autoreason.py`'s `_call_llm` + persona-dispatch logic. Add MCP tool `argue_question(question: str, scope: NodeID | CommunityID | None) -> ArgumentResult` in `serve.py` following the existing `_tool_*` pattern (text_body + SENTINEL + json(meta) envelope preserved per D-02).

**Optional extra:** None new. Lives entirely in core graphify + whatever LLM caller `autoreason.py` uses today.

### Phase 17 — Conversational Graph Chat

| Technology | Version | Purpose | Why Recommended |
|------------|---------|---------|-----------------|
| **Existing MCP tools in `serve.py`** | n/a | Structured graph access surface | `query_graph`, `graph_summary`, `entity_trace`, `connect_topics`, `drift_nodes`, `newly_formed_clusters`, `get_node` already cover the NL-query surface. Phase 17 does **not need** a new NL→query parser — it needs a **skill prompt** that teaches the host LLM how to compose these tools. The translation is done by the host LLM (Claude, Letta), not by graphify. |
| **No new dep** — regex intent fallback (stdlib) | n/a | Optional offline fallback for simple `/ask` command | If Phase 17 requirements include a harness-free fallback, implement as a **regex-to-tool dispatcher** (~100 LoC) in `graphify/chat.py`. E.g., `r"what connects (?P<a>\w+) (?:and|to) (?P<b>\w+)"` → `entity_trace(a) ∩ entity_trace(b)`. Keep it narrow — any query the regex doesn't match falls back to a raw `query_graph` with a message. |

**Integration path:** New skill-level prompt file `graphify/commands/ask.md` that documents the tool composition patterns. New MCP tool **not required** — if added for symmetry, it'd be `chat_query(question: str) -> list[GraphMCPResponse]` that just dispatches to the regex router with MCP-envelope output.

**Optional extra:** None new. **Do NOT add an LLM-as-router dep** (e.g., `anthropic`, `openai`, `litellm` as required). The host harness is the router; graphify stays transport-agnostic.

### Phase 18 — Focus-Aware Graph Context

| Technology | Version | Purpose | Why Recommended |
|------------|---------|---------|-----------------|
| **Existing `networkx` ego-graph** | 3.4.2 (core) | Compute 1-hop + 2-hop neighborhoods around focus node | `nx.ego_graph(G, focus_id, radius=1)` is one call. No new dep. |
| **Agent-reported focus** (stdlib only) | n/a | The active file is passed as an MCP tool argument | The host harness knows what the user is editing (Claude Code tracks current buffer; Obsidian plugins can expose it). Graphify should **not** try to independently watch what's focused — that's a `watchdog` rabbit hole (Focus in an IDE isn't a filesystem event). Accept `file_path` as input to `get_focus_context(file_path: str)` and do a graph lookup. |
| **`watchdog`** | 6.0.0 (existing `[watch]` extra, optional use) | Only if Phase 18 requirements explicitly request push-based focus tracking from graphify side | Default stance: NOT needed. Pull-model via MCP tool call covers 95% of the case. |

**Integration path:** New MCP tool `_tool_get_focus_context` in `serve.py` returning `{node, edges, community, connected_nodes}`. New community lookup helper `graphify/focus.py` (pure function over the existing graph JSON). Obsidian-side consumption is a Dataview query in a template added under `graphify/builtin_templates/` — already packaged.

**Optional extra:** None new.

### SEED-002 — Harness Memory Export (paired with Phase 13)

| Technology | Version | Purpose | Why Recommended |
|------------|---------|---------|-----------------|
| **`PyYAML`** | 6.0.3 (existing `[obsidian]` extra) | Schema file parsing for `graphify/harness_schemas/*.yaml` | Already a dep. The seed itself calls this out: "Dependencies: PyYAML (already optional); no new required deps". |
| **stdlib `string.Template`** | stdlib | Format harness-specific `CLAUDE.md` / `AGENTS.md` files | Phase 2 of v1.0 already chose `string.Template` over Jinja2 for exactly this reason (listed under project Constraints). Keep the precedent. |
| **No new dep for cross-harness format** | n/a | There is no emerging standard to adopt | See below — the schemas diverge and no convergence point has emerged. |

**Cross-harness format convergence (MEDIUM confidence, based on current state):**

| Harness | Memory file(s) | Schema characteristics |
|---------|---------------|------------------------|
| Claude Code | `CLAUDE.md` (global + project), optional `.claude/skills/*/SKILL.md` | Freeform markdown, convention-based headings (`# Developer Profile`, `# Project`, etc.). No enforced schema. Sub-directory hook + skill registrations appended as distinct markdown sections. |
| Cursor | `.cursor/rules/*.mdc` | Markdown with frontmatter (`description`, `globs`, `alwaysApply`), one file per rule. Closer to a schema than CLAUDE.md but still per-file. |
| Letta | In-memory `memory_blocks` (core/persona/human) — **not file-based** | SQL/API-backed blocks with `label`, `value`, `limit`. Exported via API, not a repo file. |
| OpenClaw | `.openclaw/skills/*/SKILL.md` | Mirrors Claude Code convention — same freeform markdown. |
| Codex | `.agents/skills/*/SKILL.md` + per-project `AGENTS.md` | Markdown, convention-based like Claude. |
| Factory Droid | `.factory/skills/*/SKILL.md` | Mirrors the pattern. |

**Finding: there is no de-facto standard — `CLAUDE.md`-shaped freeform markdown is the closest thing to a lingua franca** because it's human-editable, diff-friendly, and every markdown-capable harness can read it. Letta is the outlier (API-backed blocks). The pragmatic SEED-002 format is:

- **Canonical storage:** graphify-native schema in `graphify/harness_schemas/canonical.yaml` (structured, validatable, our own schema).
- **Export shapes:** `CLAUDE.md`-style markdown (Claude/Codex/OpenClaw/Factory/Trae all eat this), `.cursor/rules/*.mdc` (for Cursor), a JSON API dump (for Letta via its API).
- **No universal import/export spec to adopt.** Ship our own canonical schema and treat every harness as a renderer target — exactly the same pattern as the v1.0 vault profile.

**Integration path:** New modules `graphify/harness_export.py` + `graphify/harness_import.py`. Schema files in `graphify/harness_schemas/`. New CLI subcommands `graphify export-harness` / `graphify import-harness`.

**Optional extra:** None new. Reuses `[obsidian]` for PyYAML.

---

## Supporting Libraries (rollup across phases)

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| `radon` | >=6.0.1 | Python cyclomatic complexity (Phase 12) | Only for `.py` files. Other languages use tree-sitter walk. |
| `apscheduler` | >=3.11.2 | Wall-clock task scheduling (Phase 15) | **Only if** Phase 15 requirements demand time-based triggers. Default: do not add. |
| `jsonschema` | >=4.26.0 | Manifest validator (Phase 13) | Already transitively installed by `[mcp]`. No extra pin unless user wants standalone validation without MCP. |

---

## Development Tools

| Tool | Purpose | Notes |
|------|---------|-------|
| `pytest` | Test runner (already CI-configured) | No change. Phase 12 needs `tmp_path` fixtures with fake per-tier endpoints; use `unittest.mock` stdlib (no `pytest-mock`). |
| `tree-sitter` | Shared parse tree (already core) | Already built. Phase 12 metric walker reuses existing `Tree` objects — do not re-parse. |

---

## Installation

**New optional extras to add to `pyproject.toml`:**

```toml
[project.optional-dependencies]
routing = ["radon>=6.0.1"]
# [enrich] only if Phase 15 requires wall-clock triggers:
# enrich = ["apscheduler>=3.11.2"]

# Existing extras stay unchanged:
mcp = ["mcp"]
neo4j = ["neo4j"]
pdf = ["pypdf", "html2text"]
watch = ["watchdog"]
leiden = ["graspologic"]
office = ["python-docx", "openpyxl"]
obsidian = ["PyYAML"]
dedup = ["sentence-transformers"]
video = ["faster-whisper", "yt-dlp"]

# Update [all] to include the new extras:
all = [
  "mcp", "neo4j", "pypdf", "html2text", "watchdog", "graspologic",
  "python-docx", "openpyxl", "PyYAML", "faster-whisper", "yt-dlp",
  "sentence-transformers",
  "radon",
  # "apscheduler",   # only if [enrich] lands
]
```

**Install combinations:**

```bash
# Minimal Phase 12 (routing + parallel extraction)
pip install "graphifyy[routing,mcp]"

# Full v1.4 surface for power users
pip install "graphifyy[all]"

# CI-matching (Python 3.10 and 3.12):
pip install -e ".[mcp,pdf,watch,routing]"
```

---

## Alternatives Considered

| Recommended | Alternative | When to Use Alternative |
|-------------|-------------|-------------------------|
| `ThreadPoolExecutor` (Phase 12) | `asyncio` / `aiohttp` | Only if we rewrite the entire `extract.py` LLM call path to be async. **Not worth it** until the Anthropic/OpenAI SDKs drop their sync interface. |
| `ThreadPoolExecutor` (Phase 12) | `multiprocessing.Pool` | If extraction ever becomes CPU-bound (e.g., heavy local tokenizer work). Today's bottleneck is the network call, not AST parse. |
| `radon` (Phase 12) | `mccabe` (0.7.0) | If we only ever need cyclomatic complexity. Radon includes MI, Halstead metrics, and raw-LOC too — more useful for tier classification. McCabe is a one-trick pony wired for flake8. |
| `radon` (Phase 12) | `lizard` (1.21.3) | If we want *multi-language* cyclomatic complexity without writing tree-sitter walkers. Lizard supports C/C++/Java/Python/etc. in one tool. **Consider lizard if** Phase 12 requirements demand CC for non-Python languages and a tree-sitter walker is too much work; otherwise radon (Python) + tree-sitter walker (everything else) is cleaner because it reuses existing parse output. |
| Custom JSON manifest (Phase 13) | `schema.org/SoftwareApplication` | If graphify ships an `https://graphify.dev/` website with JSON-LD embeds for SEO / agent discovery. Not relevant for in-repo manifest consumption. |
| `asyncio.Queue` (Phase 15) | `redis` + `rq` / Celery | If enrichment ever needs cross-machine scaling or persistence across CLI invocations. Today's scope is single-machine in-process — these are massive overkill. |
| Regex NL-router (Phase 17) | `langchain` / `llama-index` | **Never.** Framework lock-in, heavy transitive deps (pydantic pinning, SDK pinning). The host harness is already an LLM — use it, don't bundle our own. |
| Agent-reported focus (Phase 18) | `watchdog` push-model focus tracking | If a UAT surfaces that pull-model latency is unacceptable. Default: pull. |

---

## What NOT to Use

| Avoid | Why | Use Instead |
|-------|-----|-------------|
| **FastAPI / Starlette / uvicorn** (as graphify-required deps) | Graphify has no HTTP server need. MCP is stdio. `mcp` pulls these transitively for users who want HTTP transport — we don't expose that. | MCP stdio server (existing). |
| **LangChain / LlamaIndex / Haystack** | Framework lock-in, massive transitive dependency tree (pydantic, tiktoken, many SDKs), opinion clash with graphify's graph-native model. | Direct LLM SDK calls (already done in autoreason) + regex router + host-harness composition. |
| **Celery / RQ / Dramatiq** (Phase 15) | Requires Redis / RabbitMQ broker, persistence layer, worker process lifecycle. Graphify is a CLI; we do not run brokers. | `asyncio.Queue` in-process (or `APScheduler` if timed triggers are genuinely required). |
| **Trio** (Phase 12/15) | Would require green-field async rewrite; anyio already bridges trio↔asyncio if ever needed, and anyio is already a transitive dep of `mcp`. | `ThreadPoolExecutor` + `asyncio` stdlib. |
| **MCP Python SDK v2 (main branch)** | Not released to PyPI as of 2026-04-17. The v1.27.0 stable on `v1.x` is the production line. Migrating to v2 (constructor-pattern handlers, manual `jsonschema` validation) is a breaking change touching every `_tool_*` in `serve.py` — that's an entire separate phase, not a v1.4 scope item. | `mcp` 1.x (current). Monitor v2 release; migration is a future milestone. |
| **`pydantic` as a direct dep** | Already a transitive dep via `mcp`. Pinning it directly invites version conflicts — `mcp` bumps pydantic on its own schedule and our pin could block that. | Let `mcp` manage the pydantic version. If we need validation outside the MCP surface, use `jsonschema` (also already transitive). |
| **`spar-kit` as if it's a PyPI library** | It is not. It's a prompt-protocol spec. Writing `pip install spar-kit` in install docs will fail. | Implement the POPULATE→ABSTRACT→RUMBLE→KNIT phases as four functions in `graphify/argue.py` using networkx + existing autoreason orchestrator. |
| **`jinja2` for any new templating** (Phase 14 commands, Phase 13 manifest, SEED-002 harness files) | The project explicitly chose `string.Template` in v1.0 to avoid Jinja2. Keep that precedent. | `string.Template` (stdlib). |
| **Watchdog-based focus tracking** (Phase 18) | IDE focus is not a filesystem event. `watchdog` will either miss it or false-trigger. | Host harness reports focus via MCP tool argument (pull model). |
| **New LLM routing libraries** (Phase 12) like `litellm`, `instructor`, `outlines` | Scope creep. The routing decision (fast/cheap vs powerful) is a dict lookup on complexity score → endpoint config. | Simple `dict[Tier, EndpointConfig]` in `graphify/routing.py`, wired through the existing extract.py LLM caller. |
| **A universal harness memory standard** (SEED-002) | There isn't one. Adopting a premature "standard" is a maintenance tax. | Ship graphify's own canonical schema + per-harness renderers (same pattern as v1.0 vault profile). |

---

## Stack Patterns by Variant

**If user has `[mcp]` installed (most common):**
- Phase 13 validator is "free" (jsonschema is already there).
- `graphify serve` exposes new Phase 16/17/18 tools alongside existing ones.

**If user has only core (no extras):**
- Phases 12/15/16/17/18 still work (no new required deps).
- Phase 13 manifest generation works (stdlib `json`), only the `--validate` flag requires `[mcp]` OR a standalone `jsonschema` install.

**If user wants the full v1.4 surface:**
- `pip install graphifyy[all,routing]` (update `[all]` to include `routing`).

**If user is running `graphify watch` as a long-lived process (Phase 15 with scheduling):**
- Add `[enrich]` only if Phase 15 requirements include wall-clock triggers, otherwise skip.

---

## Version Compatibility

| Package A | Compatible With | Notes |
|-----------|-----------------|-------|
| `mcp` 1.27.0 | `jsonschema` 4.26.0, `pydantic` (SDK-pinned), `anyio` 4.13.0, Python 3.10/3.12 | All green. No pin conflicts with existing graphify deps. |
| `radon` 6.0.1 | Python 3.10–3.13, pure-Python, no C extensions | Safe for CI matrix. `mando` + `colorama` transitive — both tiny and stable. |
| `APScheduler` 3.11.2 | Python 3.9+, works with asyncio and threading | Only pin if added. v4 exists but in pre-release churn — stick to 3.x line. |
| `jsonschema` 4.26.0 | JSON Schema draft 2020-12 | Matches MCP's own schema surface. |
| `tree-sitter` >=0.23.0 (existing) | Phase 12 metric walker uses `Tree.root_node.walk()` cursor API | Already used in `extract.py`. No change. |
| `watchdog` 6.0.0 (existing) | Phase 18 is **not** extended to use watchdog — focus is pull-model | No version bump needed. |

---

## Integration Summary — Where Each Module Lands

| Phase | New Module(s) | Extends | Optional Extra |
|-------|---------------|---------|----------------|
| 12 Heterogeneous Extraction Routing | `graphify/routing.py` | `graphify/extract.py` (new `extract_batch`), `cache.py` (per-tier cache keys) | `[routing]` = `radon` |
| 13 Agent Capability Manifest | `graphify/manifest.py` | `__main__.py` (new `manifest` subcommand), introspects `serve.py` | — (reuses `[mcp]` for validator) |
| 14 Obsidian Thinking Commands | `graphify/commands/obsidian-*.md` (static prompts) | `_PLATFORM_CONFIG` in `__main__.py` (enable `commands_dst` for more harnesses) | — (reuses `[obsidian]` + package_data) |
| 15 Async Background Enrichment | `graphify/enrich.py` + optional `graphify/schedulers.py` | `__main__.py` (new `enrich` subcommand), `watch.py` (deriver hook) | Optional `[enrich]` = `apscheduler` (only if timed triggers) |
| 16 Graph Argumentation Mode | `graphify/argue.py` | `autoreason.py` (reuse LLM caller), `serve.py` (new MCP tool) | — |
| 17 Conversational Graph Chat | `graphify/chat.py` + `graphify/commands/ask.md` | `serve.py` (new MCP tool, optional) | — |
| 18 Focus-Aware Graph Context | `graphify/focus.py` + Obsidian template | `serve.py` (new MCP tool `_tool_get_focus_context`) | — |
| SEED-002 Harness Memory Export | `graphify/harness_export.py`, `harness_import.py`, `harness_schemas/*.yaml` | `__main__.py` (two new subcommands) | — (reuses `[obsidian]`) |

**Net change to `pyproject.toml`: one new extra (`[routing] = radon`), one conditional extra (`[enrich] = apscheduler` only if Phase 15 requires scheduling), and update `[all]` to include `radon` (and optionally `apscheduler`).**

---

## Sources

- `/modelcontextprotocol/python-sdk` (Context7) — MCP server patterns, v1→v2 migration guide, capabilities/manifest surface. Verified **v1.27.0 on PyPI** (latest), v2 on `main` branch not yet released. HIGH confidence.
- `/rubik/radon` (Context7) — `cc_visit`, `ComplexityVisitor`, CLI & Python API. Verified **6.0.1** on PyPI. HIGH confidence.
- `/terryyin/lizard` (Context7) — multi-language CC, Python API. Verified **1.21.3** on PyPI. HIGH confidence. Not recommended for Phase 12 primary path but noted as alternative.
- `/agronholm/apscheduler` (Context7) — `BackgroundScheduler`, trigger types. Verified **3.11.2** on PyPI. HIGH confidence.
- `/python-jsonschema/jsonschema` (Context7) — draft 2020-12 support. Verified **4.26.0** on PyPI, already transitive in `mcp`. HIGH confidence.
- `/plastic-labs/honcho` (Context7) — deriver architecture (env vars, queue payload creation, worker scaling). Explicit finding: Honcho's deriver is a **DB-queue-polling multi-worker service**, which is the wrong shape for graphify's in-process CLI model. Takeaway is the **conceptual pattern** (enrichment passes on a queue), not the implementation. HIGH confidence.
- `/agronholm/anyio` (Context7) — transitive dep of `mcp` already present. No direct action needed. HIGH confidence.
- `/gorakhargosh/watchdog` (Context7) — existing `[watch]` extra. No version change. HIGH confidence.
- `pyproject.toml` (reading) — existing extras: `mcp`, `neo4j`, `pdf`, `watch`, `leiden`, `office`, `obsidian`, `dedup`, `video`, `all`. Version `0.4.7`. HIGH confidence.
- `graphify/serve.py` (reading, first 120 lines) — MCP envelope (`text_body + SENTINEL + json(meta)`), annotation JSONL atomic-write pattern, dedup report alias map. All new Phase 16/17/18 MCP tools follow this envelope. HIGH confidence.
- `graphify/__main__.py` (reading, first 120 lines) — `_PLATFORM_CONFIG` dict structure; Phase 14 extension point. HIGH confidence.
- `.planning/seeds/SEED-002-harness-memory-export.md` — seed's own dep note ("PyYAML; no new required deps") confirms the direction. HIGH confidence.
- `.planning/ROADMAP.md` v1.4 phase list — informs-by citations (Honcho, Letta, SPAR-Kit, smolcluster, Obsidian-Claude Codebook). HIGH confidence.
- SPAR-Kit protocol — **NOT found as a PyPI package**. Referenced in roadmap as `synthanai/spar-kit`. Treated as a prompt-protocol spec, implemented via existing stack. MEDIUM confidence (negative finding verified via library-ID searches).
- MCP capability manifest standard — **NOT found as an adopted spec** in MCP v1.27.0 docs or v2 migration guide. Community-ad-hoc. Graphify ships its own schema. MEDIUM confidence (negative finding).

---
*Stack research for: graphify v1.4 (Agent Discoverability & Obsidian Workflows) — subsequent milestone, scope-limited to new phases only.*
*Researched: 2026-04-17*
