# Feature Research: v1.4 Agent Discoverability & Obsidian Workflows

**Domain:** Heterogeneous extraction routing, agent capability self-description, Obsidian thinking commands, async background enrichment, graph-argued decisions, conversational graph chat, focus-aware graph context, harness memory export
**Researched:** 2026-04-17
**Confidence:** HIGH — grounded in MCP 2025-11-25 spec (fetched), Honcho documentation (fetched), SPAR-Kit protocol docs (fetched), MCP registry server.json spec (fetched), plus audited internal notes (`.planning/notes/april-research-gap-analysis.md`, `.planning/notes/repo-gap-analysis.md`, `.planning/notes/april-2026-v1.3-priorities.md`, `.planning/notes/agent-memory-research-gap-analysis.md`) and live codebase state (`graphify/serve.py`, `graphify/extract.py`, `graphify/commands/*.md`, `graphify/snapshot.py`, `graphify/delta.py`). MEDIUM confidence on Letta sleep-time compute specifics (docs.letta.com blocked; characterized from April-2026 research notes and Arxiv 2504.13171 abstract framing that's already informed prior phases).

---

## Scope Reminder

This research is scoped exclusively to v1.4 new features. Existing v1.0–v1.3 capabilities are called out as **dependencies**, not re-researched. The seven v1.4 phases plus SEED-002 are:

- **Phase 12 — Heterogeneous Extraction Routing:** AST-metric-driven file-to-model routing; parallel extraction across endpoints. _(Pulled forward from v1.3 deferral.)_
- **Phase 13 — Agent Capability Manifest (+ SEED-002 Harness Memory Export):** Machine-readable self-description of graphify's MCP surface + harness-agnostic memory serialization.
- **Phase 14 — Obsidian Thinking Commands:** Graphify-aware slash commands designed for enriched vaults — distinct from Phase 11's repo-oriented `/context`, `/trace`, `/connect`, `/drift`, `/emerge`, `/ghost`, `/challenge`.
- **Phase 15 — Async Background Enrichment:** Post-build derivers that enrich descriptions, detect patterns, refresh staleness, summarize communities — without blocking the pipeline.
- **Phase 16 — Graph Argumentation Mode:** Graph as SPAR-Kit ABSTRACT substrate; personas RUMBLE over subgraphs; KNIT produces advisory recommendations.
- **Phase 17 — Conversational Graph Chat:** NL → structured traversal; grounded narrative answers; anti-fabrication guardrails carried forward from Phase 11.
- **Phase 18 — Focus-Aware Graph Context:** File-level "what am I editing?" → `get_focus_context(file_path)` returning neighborhood + community + connected nodes.

Baseline dependencies already built (v1.0–v1.3):

- `extract.py` LanguageConfig-driven dispatch, tree-sitter AST, `cache.py` hash skip
- `serve.py` token-aware 3-layer `graph_query`, cardinality estimator, bidirectional BFS, 5 write tools (annotate/flag/add_edge/propose_vault_note/get_annotations), telemetry-driven hot/cold, 2-hop derived edges
- `snapshot.py` + `delta.py` FIFO snapshot, GRAPH_DELTA.md, FRESH/STALE/GHOST staleness, peer identity
- `analyze.py` autoreason tournament (4 lenses × A/B/AB/Borda), god nodes, surprising connections
- `graphify/commands/*.md` 7 interactive slash commands (repo-oriented, not vault-oriented)
- `profile.py` + `merge.py` vault profile adapter, sentinel blocks, user-modified detection, `propose_vault_note` approval CLI
- `dedup.py` fuzzy + embedding entity merge with alias redirect

---

## Feature Landscape

### Phase 12: Heterogeneous Extraction Routing

**Ecosystem reality:** Dev-tool harnesses (Aider, Continue, Cursor, Cody, Cline) do **not** route individual files to different models based on AST complexity. Their multi-model story is role-based:

- **Aider** uses `main model` / `weak model` / `editor model` — role-separated, not complexity-separated. The weak model summarizes git commits; the editor model applies diffs; the main model does the reasoning. User configures roles globally; no per-file decision.
- **Continue** has role slots (`chat`, `edit`, `autocomplete`, `apply`, `embed`, `rerank`) — the user configures which model fills each slot. Routing is role→model, not file→model.
- **Cursor** picks one model per request (user-chosen from model picker); no per-file heterogeneity.
- **Cline** supports multiple providers (OpenRouter/Anthropic/Bedrock) but routing is user-selected per conversation.

Closest analog is **smolcluster** (YuvrajSingh-mist) which adapts workload distribution across heterogeneous hardware by device capability — but that's a training/inference cluster, not a code-extraction tool. **Conclusion: graphify is pioneering here. There is no "table stakes" for file-complexity-to-model routing; the table stakes are for model-role separation.**

#### Table Stakes (Users Expect These)

| Feature | Why Expected | Complexity | Depends On | Notes |
|---------|--------------|------------|------------|-------|
| Role-based model configuration (main/weak/helper) | Aider pattern; Continue pattern. Users expect to say "use Haiku for X, Opus for Y" without touching code. | MEDIUM | Existing extract.py LanguageConfig + new config loader | Two slots: `extraction.primary_model` and `extraction.boilerplate_model`. Default: both point to same model (backward compat). Configure via env var or profile section. No per-file decision logic yet — just two-tier capacity. |
| Graceful degradation to single model | Not every user wants to configure two endpoints; running with one must be seamless. | LOW | Role config above | If `boilerplate_model` unset, fall back to `primary_model` for all files. No warnings. Document the fallback explicitly. |
| Per-file model stamp in node metadata | Users need to see which model generated which node for trust/audit purposes. Cognee, Honcho, and LangGraph all stamp producer identity on memory artifacts. | LOW | Existing node attribute dict | Add `extracted_by_model: "claude-haiku-4" \| "claude-opus-4-7"` to node metadata at extraction time. Surface in GRAPH_REPORT.md optionally. |
| Parallel extraction across endpoints | Once two models are in play, sequential extraction wastes the parallelism opportunity. Existing users already wait for large repos. | MEDIUM | Role config + asyncio/concurrent.futures | `concurrent.futures.ThreadPoolExecutor` with `max_workers=2` (one per endpoint). Simple round-robin assignment by file-routing decision. No new required deps — stdlib. |

#### Differentiators (Competitive Advantage)

| Feature | Value Proposition | Complexity | Depends On | Notes |
|---------|-------------------|------------|------------|-------|
| AST-metric-driven complexity classifier | No other dev tool routes files by AST complexity. The signal is available because graphify already parses every file via tree-sitter. | MEDIUM | Existing tree-sitter parse + new `graphify/complexity.py` | Compute per-file: `node_count` (AST depth proxy), `cyclomatic_complexity` (count of `if`/`for`/`while`/`case` nodes), `import_count`, `symbol_count`. Threshold-based classification: `simple` (< 50 AST nodes, < 5 imports) vs. `complex` (≥ 50 nodes OR ≥ 10 imports). Thresholds must be config-exposed; users tune for their codebase. |
| Per-file-type defaults | Config files, test fixtures, generated code are always "simple" regardless of AST count. Docstring-only modules rarely need Opus. | LOW | File-type classification (existing in `detect.py`) | Table: `.json/.toml/.yaml` → boilerplate; `.md/.rst` → primary (semantic content); `.py/.ts/.rs` → complexity-classified; `tests/**` → boilerplate unless AST metrics override. |
| Token-cost reporting per run | Users care about cost; the value prop of routing IS cost savings. Without a cost delta line, the feature is invisible. | LOW | Extraction metadata + simple multiplication by published per-token rates | Emit at end of run: `cost_summary: {primary_model_tokens: N, boilerplate_model_tokens: M, estimated_cost_delta_vs_single_model: $X}`. Hardcoded rate table, user-overridable via config. Doesn't call pricing APIs. |
| Bounded staleness for parallel extraction | Smolcluster pattern: allow slow file to use slightly older cache entry if re-extraction blocks the pipeline. Graphify-specific: useful for incremental `graphify watch` re-runs. | MEDIUM | Cache hash + extraction timestamp | If a file's extraction thread exceeds `max_extraction_seconds`, surface a warning and use the cached version (marked STALE via existing staleness machinery). Explicit; never silent. |
| Vision-model routing for `.png`/`.jpg`/architecture diagrams | Images currently go to the general model; a vision-specialized endpoint could extract architecture diagrams far better. Previously part of Phase 12 expansion, deferred from v1.3. | MEDIUM | Role config extended to `vision_model` slot | Third slot for image extraction. Falls back to `primary_model` if unset. Separable from the AST-metric feature; can ship independently. |

#### Anti-Features

| Anti-Feature | Why Avoid | Alternative |
|--------------|-----------|-------------|
| Learned routing (training a classifier on past runs) | Requires a training dataset graphify doesn't have and won't have at v1.4 scale. The signal (AST metrics) is linear and explainable; a learned classifier sacrifices debuggability. | Threshold-based routing with config-exposed thresholds. Users tune for their codebase; behavior is deterministic and auditable. |
| Automatic model selection from a registry of 20+ models | Continue tried this; users complained about unpredictable behavior and cost surprises. | Fixed two-tier slot system. User explicitly chooses `primary` and `boilerplate` models. No auto-discovery. |
| Fallback to cached extraction when primary model errors | Silent degradation means the user doesn't know they got a worse graph. | Fail loudly to stderr with `[graphify] Opus call failed; falling back to cached node from 2026-03-01. Re-run with --force to retry.` Never silent. |
| Routing on LOC alone | LOC correlates poorly with extraction complexity; a 2000-line config file is trivial, a 50-line metaclass is hard. | Multi-metric: AST node count + imports + cyclomatic complexity. LOC is one input, not THE input. |
| Per-node model routing (e.g., "send this function to a different model mid-extraction") | Breaks the extraction-per-file atomicity guarantee. Creates race conditions in parallel execution. | Whole-file routing only. Extraction is per-file; the routing decision is made once per file. |

---

### Phase 13: Agent Capability Manifest (+ SEED-002 Harness Memory Export)

**Ecosystem reality — MCP self-description:** The MCP spec (2025-11-25, fetched) has a **capability negotiation handshake**, not a rich manifest:

- `initialize` request: client declares `clientInfo` (`name`, `version`) + `capabilities` (e.g. `elicitation`, `roots`, `sampling`).
- `initialize` response: server declares `serverInfo` (`name`, `version`) + `capabilities` (`tools`, `resources`, `prompts`, each with optional sub-flags like `listChanged: true`).
- Discovery of actual surface happens AFTER handshake via `tools/list`, `resources/list`, `prompts/list` — each returns `name`, `title`, `description`, `inputSchema` per item.

**Ecosystem reality — MCP registry:** The emerging registry (github.com/modelcontextprotocol/registry, fetched) uses `server.json` with `name` (reverse-DNS like `io.github.graphify/graphify`), `description`, `title`, `version`, `repository`, `websiteUrl`, `packages` (npm/pypi/nuget/oci/mcpb), `remotes` (HTTP/SSE endpoints), and `_meta` for publisher-provided custom metadata under `io.modelcontextprotocol.registry/publisher-provided`. **smithery.ai** and **mcp.dev** exist as third-party aggregators but don't define new schema; they consume the same `server.json` + `/initialize` surface.

**What agents actually use to decide "should I use this server":** From MCP spec + registry reality, the decision signal is three-tiered:

1. **Discovery tier** (before calling): `name`, `description`, `title`, `repository`, `packages[].identifier`, `packages[].registryType` — enough to decide "is this the right *kind* of tool."
2. **Capability tier** (after initialize): `serverInfo`, declared capabilities (`tools: {listChanged: true}`), protocol version.
3. **Tool-level tier** (after `tools/list`): Per-tool `name`, `title`, `description`, `inputSchema`. Agents filter candidate tools by description match against task. THIS is where most selection actually happens — most clients (Claude Desktop, VS Code) just list all tools and let the LLM pick.

**What SEED-002 adds:** SEED-002 isn't about agent discoverability — it's about **memory portability**. Harness Memory Export serializes graphify's internal state (graph + annotations + agent-edges + elicited facts) out to portable artifacts (`SOUL.md`, `HEARTBEAT.md`, `USER.md`, `operating-model.json`, `AGENTS.md`, `CLAUDE.md`). Inverse direction (ingest external `CLAUDE.md`/`AGENTS.md` into the graph) is also in scope. Harrison Chase's "Your harness, your memory" framing is the source; Sarah Wooders/Letta's "memory-harness" validates the lock-in threat.

#### Table Stakes (Users Expect These) — Manifest

| Feature | Why Expected | Complexity | Depends On | Notes |
|---------|--------------|------------|------------|-------|
| MCP `initialize` handshake compliance | The baseline — any MCP server MUST respond to `initialize` with `serverInfo` + capabilities. graphify's `serve.py` already does this via the `mcp` library. Audit for protocol-version compliance (2025-11-25). | LOW | Existing `serve.py` | Verify `protocolVersion` negotiation, `capabilities` declaration, `notifications/initialized` handling. Add a test that asserts the declared capabilities match the actually-implemented tools (drift detection). |
| Per-tool `description` + `inputSchema` | The tool-level selection tier — agents pick by description. graphify has 12+ tools; descriptions must be crisp and task-matched ("query a knowledge graph by node ID" not "returns node data"). | LOW | Existing tool registration in `serve.py` | Audit all tool descriptions for agent-action verbs ("query", "search", "annotate"). Add `title` field (human-friendly) alongside `name` (machine). Ensure `inputSchema` declares `required` vs. optional params. |
| `server.json` file at repo root | Required for MCP registry listing. Reverse-DNS name, version, repository, package info. | LOW | Repo metadata | Generate `server.json` matching registry spec: `name: "io.github.graphify/graphify"`, `packages: [{registryType: "pypi", identifier: "graphifyy", transport: "stdio"}]`. CI job validates against registry schema. |
| Human-readable capability README | Registries render this for users; agents sometimes parse it. | LOW | Standard README section | New section in repo README listing: "graphify exposes N MCP tools: [list with descriptions]. Required runtime: Python 3.10+. Recommended for: codebase understanding, knowledge-graph-grounded chat." |

#### Table Stakes — Harness Memory Export (SEED-002)

| Feature | Why Expected | Complexity | Depends On | Notes |
|---------|--------------|------------|------------|-------|
| Export to `CLAUDE.md` (Claude Code-native format) | Claude Code is graphify's default harness; users expect native-format export. Pattern is established — graphify already installs a CLAUDE.md fragment. | LOW | Existing annotations + agent-edges + graph | New module `graphify/harness_export.py`. Renders graph summary + top god nodes + annotations into CLAUDE.md Markdown sections. Idempotent re-write preserves user-authored blocks via v1.1 sentinel grammar. |
| Export to `AGENTS.md` (harness-neutral) | Emerging convention for harness-agnostic agent definitions (seen in OpenCode, factory, cross-tool CI configs). | LOW | Same as CLAUDE.md export | Parallel renderer with different Markdown shape (YAML frontmatter + behavior blocks). Defer to after CLAUDE.md validates the approach. |
| `graphify export-harness [--format claude\|agents\|all]` CLI | CLI is the only way users can invoke the export without running the skill pipeline. Matches v1.0's `--obsidian` / `--validate-profile` utility-flag pattern (D-73). | LOW | `__main__.py` + `harness_export.py` | Follow D-73: CLI is utilities-only. Export itself writes to `graphify-out/harness/` (confined by security.py). |

#### Differentiators — Manifest

| Feature | Value Proposition | Complexity | Depends On | Notes |
|---------|-------------------|------------|------------|-------|
| Capability manifest as first-class MCP resource | Expose `graphify://capabilities/manifest` as an MCP `resource` (per spec). Agents can `resources/read` it without calling `tools/list` — useful for agents that filter servers BEFORE connecting tool-by-tool. | MEDIUM | `serve.py` resource registration | New resource with JSON payload: `{tools: [{name, description, cost_class, requires_graph: true/false}], graph_stats: {node_count, ready_for_queries: bool}, freshness: last_build_time}`. Fields beyond MCP spec minimums. |
| `cost_class` annotation on tools | Token-economy signal. `graph_summary` is cheap; `graph_query depth=4` can be expensive. Agents deciding among similar servers want to know. | LOW | Per-tool metadata | Three-tier label: `cheap` / `moderate` / `expensive`. Declared statically in server code. Not a live estimate — just a hint. |
| Self-describing `graphify.status()` tool | Agents query this first to decide "is there even a graph here, or should I call `/graphify` first?" The "no graph" case is currently surfaced inconsistently across commands. | LOW | Existing graph-presence check in `serve.py` | New MCP tool returning `{graph_present: bool, node_count: int, last_build: iso8601, staleness_summary: {fresh: N, stale: M, ghost: K}, recommended_first_action: "graphify run" \| "query"}`. One-shot discovery. |
| Deep link into MCP registry | Once graphify ships a `server.json`, publishing to the registry is a one-command step. Distribution multiplier — users find graphify via registry searches for "knowledge graph" or "codebase understanding." | LOW | `server.json` + registry publish workflow | CI job runs registry validation. Manual publish initially; automatable later. Zero code in graphify; purely packaging/CI. |
| Version compatibility manifest | MCP spec evolves (2025-11-25 is current). graphify should declare min/max supported spec version separately from its own version. | LOW | Version string in serve.py | `supported_mcp_versions: ["2025-11-25", "2025-06-18"]` in capability manifest resource. Helps registries and clients filter by protocol version. |

#### Differentiators — Harness Memory Export

| Feature | Value Proposition | Complexity | Depends On | Notes |
|---------|-------------------|------------|------------|-------|
| Inverse import: `graphify import-harness <CLAUDE.md>` | Closes the loop — users with existing harness memory can bring it INTO graphify without starting over. The anti-lock-in positioning only works bidirectionally. | HIGH | YAML/Markdown parser + new `harness_import.py` | Parse CLAUDE.md / AGENTS.md Markdown sections → extraction events → nodes with `source_file: "CLAUDE.md"`, `file_type: "harness_memory"`. Reuses existing extraction pipeline downstream of parse. |
| Canonical schema layer | Lock-in resistance comes from having ONE canonical shape that all exports derive from. Without it, each format is bespoke and the maintenance tax compounds. | MEDIUM | New `graphify/harness_schemas/` directory | `canonical.yaml` defines the neutral shape; `claude.yaml`, `agents.yaml`, `soul.yaml` are field-mapping overlays. Users can add `harness_schemas/custom.yaml` for their own target. |
| Round-trip guarantee with manifest | Export → import → export produces identical output (modulo timestamps). Makes harness switching actually viable. | HIGH | Manifest of exported fields + field-mapping table | Track `exported_at`, `exported_by_peer`, `source_nodes` for each output Markdown section. On re-import, align by node_id. Lossless round-trip tested via fixture pairs. |
| Companion resource for Agent Capability Manifest | Manifest says WHAT graphify exposes; Export says HOW its memory travels. Shipping together signals a coherent "agent-portability" story. | LOW | Both Phase 13 + SEED-002 | Registry listing, README section, and one blog-shaped docs page treat them as a unit. |

#### Anti-Features

| Anti-Feature | Why Avoid | Alternative |
|--------------|-----------|-------------|
| Proprietary "graphify manifest" schema | A new schema that competes with `server.json` creates a proliferation problem and won't be adopted by registries. | Extend `server.json` via `_meta` custom-metadata field. Publish under our namespace (`io.graphify.metadata/*`). Stays registry-compatible. |
| Authentication layer in the manifest | MCP uses OAuth/bearer tokens at the transport layer. Re-implementing auth at the manifest tier is wasted work. | Declare required auth class in manifest (`auth_required: none` for stdio; `auth_required: oauth` for hypothetical remote). Don't implement the auth. |
| Dynamic capability advertisement (tools appearing mid-session) | MCP supports `tools/list_changed` notifications but complex state machines produce bugs in agents that cache tool lists. | Declare full tool list at init. Use `listChanged: false` for v1.4. Future phase may enable dynamic surface if real use case emerges. |
| Auto-publish to MCP registry on every release | Registry is curated; spamming releases degrades the registry for everyone. | Manual publish with CI pre-validation. Humans decide which versions appear. |
| Running the export on every graph build | Harness memory changes less frequently than the graph; running export unconditionally wastes write I/O and pollutes diffs. | Explicit `graphify export-harness` command. Skill can call it on demand. Watch-mode does NOT auto-export. |
| Full agent-execution-trace export | Exporting every MCP call log creates enormous files and privacy risk. Not what users want; they want portable *memory*, not audit logs. | Export only the materialized memory artifacts (graph summary, annotations, god nodes, decision trail from autoreason). Logs stay in `graphify-out/telemetry.json` (local only). |

---

### Phase 14: Obsidian Thinking Commands

**Ecosystem reality:** The **Obsidian-Claude-Codebook** (April 2026 research source) canonicalized a pattern of 12 Obsidian-Claude slash commands that turn vaults into "thinking OS." Characteristic of the codebook pattern (drawn from research notes and SEED-001 framing): vault-oriented commands operate on *ideas, beliefs, patterns, and voice* — things graphify's vault export already enriches via MOC/Thing/Person notes, wikilinks, and community folders.

**The Phase 11 vs Phase 14 distinction** (critical for this research):

| Axis | Phase 11 (SHIPPED in v1.3) | Phase 14 (NEW in v1.4) |
|------|----------------------------|------------------------|
| Context | Code repository | Obsidian vault (enriched by v1.0 adapter) |
| Target user | Developer mid-coding | Vault power user (Nick Milo / Eleanor Konik / Ideaverse patterns) |
| Graph source | `graphify-out/graph.json` from code extraction | Graph from vault-extracted MD + frontmatter + wikilinks |
| Output style | Narrative grounded in code nodes | Note-shaped output; creates vault notes, Dataview queries, MOC entries |
| Command surface | `/context`, `/trace`, `/connect`, `/drift`, `/emerge`, `/ghost`, `/challenge` | `/moc`, `/wayfind`, `/related`, `/orphan`, `/drift-notes`, `/voice`, `/bridge` (tentative names) |

**What vault power users actually want from AI integration:**

From existing notes (`april-research-gap-analysis.md`, `repo-gap-analysis.md`, SEED-001) + Ideaverse-framework conventions already ingested in v1.0:

- **MOC generation from graph communities** — "give me a Map of Content for community 7" → produces a properly-formatted MOC note with Dataview queries.
- **Wayfinder auto-generation** — navigational breadcrumbs across vault hierarchy (Atlas/ → Community → Dots).
- **Related-note discovery grounded in graph neighborhood** — NOT just wikilink-based; uses graph edges (semantic similarity, bridge edges) to surface unlinked-but-related notes.
- **Orphan surfacing** — notes that exist in the vault but aren't in any graph community (or vice-versa).
- **Voice preservation** — some version of Phase 11's `/ghost` but scoped to vault-author style (their prose, their conceptual framings) vs. codebase style.
- **Drift across vault revisions** — what ideas moved communities across the last N graphify runs.
- **Note-bridge discovery** — find vault notes that bridge two communities (the human analog of Phase 11's `/connect`).

#### Table Stakes (Users Expect These)

| Feature | Why Expected | Complexity | Depends On | Notes |
|---------|--------------|------------|------------|-------|
| `/moc <community-id-or-label>` generates a new MOC note | v1.0 Ideaverse adapter creates MOCs at graphify build-time. Power users want on-demand MOC creation during thinking sessions, not just at build. | LOW | v1.0 `templates.py` MOC renderer + `profile.py` default profile + new MCP tool | New MCP tool `compose_moc(community)` returns rendered MD. Skill writes to vault via `propose_vault_note` (v1.1) — human-in-the-loop. NEVER auto-writes. |
| `/related <note-path>` returns graph-neighbor notes | Table stakes for any vault-aware assistant. Obsidian's native graph is topology-only; graphify adds semantic-similarity + bridge-edge neighbors. | LOW | Existing `serve.py` neighborhood query + vault path → node ID resolver | Returns three buckets: `same_community: []`, `bridge_neighbors: []`, `semantically_similar: []`. Each entry is a wikilink-formatted path. |
| `/orphan` surfaces vault-orphan vs graph-orphan notes | Vault users are paranoid about orphan notes (Ideaverse explicitly teaches MOC discipline to prevent them). Graphify can distinguish "user-orphan" from "graph-orphan" where v1.0 already tracks both. | MEDIUM | v1.0 merge.py ORPHAN action + v1.1 vault-manifest | Two-section output: notes-not-in-graph (may have been user-authored; surface for review), nodes-not-in-vault (graphify didn't generate a note; may need profile tweaking). Uses existing `vault-manifest.json`. |
| `/wayfind <note-path>` returns hierarchy breadcrumbs | Ideaverse's wayfinder pattern — where does this note sit in the Atlas? v1.0 already generates wayfinder blocks at build-time. This surfaces the same data on demand. | LOW | v1.0 wayfinder generation + `serve.py` | Returns: `Atlas/ > Maps/ > community_7 > this_note`. Pure graph traversal; no new module. |

#### Differentiators (Competitive Advantage)

| Feature | Value Proposition | Complexity | Depends On | Notes |
|---------|-------------------|------------|------------|-------|
| `/bridge <topic-a> <topic-b>` discovers a *vault note* that could bridge them | Phase 11's `/connect` finds a path; for vault users, the actionable output is "which note should you expand (or create) to link these?" Graphify knows; vault can't. | MEDIUM | Phase 11 `/connect` internals + god-node detection on the path | After finding shortest-path between two topics' communities, surface the most-connected node on the path AND any existing vault note backing it. If no vault note exists → `propose_vault_note` draft. |
| `/drift-notes` with per-note community-movement | Vault owners want to see which notes changed conceptual homes between runs. Phase 11's `/drift` is graph-level; this is note-level with MD output. | LOW | v1.1 delta + vault-manifest | Filter delta to nodes with community migration AND a backing vault note. Output as wikilinks grouped by old→new community. |
| `/voice <topic>` grounded in author prose | Vault users want AI to speak in their voice. `/ghost` in Phase 11 used annotation-grounded prose; Phase 14 version grounds in *vault-note text* (docstring for vault authors). | HIGH | serve.py text retrieval for nodes with vault-backing + LLM sampling | Surface top-5 user-authored note excerpts for a topic; pass to LLM-sampling MCP primitive (clients like Claude Desktop support it). Same anti-impersonation disclaimer as Phase 11: "based on your notes, not your mind." |
| Commands emit Dataview queries as output artifacts | Vault power users live in Dataview. Outputting a Dataview query string alongside prose lets them drop it straight into a note. | MEDIUM | v1.0 Dataview query embedding + command renderer | Each command optionally returns `dataview_query: "LIST FROM #community/transformer WHERE status != draft"`. User pastes; lives in vault permanently. |
| Profile-driven command behavior | Ideaverse framework has specific MOC conventions; Eleanor Konik's framework differs; commands should adapt to the active profile (`.graphify/profile.yaml`). | MEDIUM | v1.0 profile + each command | Each command reads `profile.yaml` `templates.moc`, `folder_mapping.moc`, `wayfinder.format`. No hardcoded output shapes; all profile-driven. Matches v1.0 backward-compat guarantees. |

#### Anti-Features

| Anti-Feature | Why Avoid | Alternative |
|--------------|-----------|-------------|
| Duplicating Phase 11 commands verbatim with vault output | Seven names collide; users confused about which to use. Maintenance burden doubled. | Different command names. Phase 11 is `/trace entity`; Phase 14 is `/trace-note wikilink`. Phase 11 is `/connect topic topic`; Phase 14 is `/bridge note note`. Signal vault vs. code unambiguously. |
| Auto-writing MOCs and wayfinders on command invocation | v1.1 established the `propose_vault_note → human approval` pattern precisely to prevent this. Auto-write undoes that guarantee. | All commands that would modify the vault go through `propose_vault_note`. Read-only commands (like `/related`, `/orphan`) return markdown-formatted text; user decides where to paste. |
| Obsidian-plugin integration | v1.0 explicitly scoped this out. Graphify outputs markdown + frontmatter; plugin work is a different project. | Commands are `.claude/commands/*.md` Skills files that consume the MCP server. Compatible with any Obsidian Claude-Code setup, zero plugin code. |
| Live vault-file watching for command-trigger | Letta-Obsidian does this via file watcher; graphify's architecture avoids ambient capture (D-18). Watch mode re-extracts code, not commands. | Commands are explicit user invocation — via slash command in the harness. No file-watcher-to-command linkage. |
| Vault-writing commands that bypass sentinel grammar | v1.1 sentinel blocks (`GRAPHIFY_USER_START`/`END`) are inviolable. A command that edits outside them (or inside a user-authored sentinel) violates the trust boundary. | All vault writes go through v1.0 `compute_merge_plan` + `apply_merge_plan`. Sentinel grammar enforced by the merge engine, not by command implementers. |
| Voice-mode that impersonates the author without a disclaimer | The `/ghost` pattern in Phase 11 added an anti-impersonation guard. The vault equivalent must carry forward: "This is graphify echoing your notes. It is not you." | Every `/voice` output begins with a fixed disclaimer block. Anti-fabrication guard: refuse to generate voice output if backing note text is missing. |

---

### Phase 15: Async Background Enrichment

**Ecosystem reality:**

- **Honcho (plastic-labs, fetched):** Derivers generate **representations** (peer identity models from interaction history), **summaries** (session summaries), and **peer cards** (structured peer metadata). Triggered automatically when messages or sessions are created. Race prevention via **session-based queue processing** — derivation work per session executes sequentially; parallel deriver instances work across different sessions. This is the established pattern — queue + session-scoping.
- **Letta sleep-time compute (MEDIUM confidence, docs blocked):** From April-2026 research notes: sleep-time compute is background reflection on memory (consolidation, summarization, pattern detection) that runs when the agent isn't actively processing a user turn. Trigger is end-of-turn or explicit scheduler. Payoff is improved retrieval quality and reduced context pressure at next user turn. (Arxiv 2504.13171 framing consistent with this; full text blocked.) Letta avoids racing by running sleep-time compute on a *separate agent* (the "sleep-time agent") that shares memory blocks but has its own reasoning loop — coordination is via explicit memory-block locks.
- **Cognee "memify":** Usage-weighted representations built via background passes.

**Common thread:** Background enrichment is never *real-time rebuild*. It's **queued, idempotent, session/snapshot-scoped**, and **advisory** — the foreground pipeline is never blocked waiting for derivers.

**Critical anti-pattern for graphify:** v1.1 `delta.py` already computes staleness at the snapshot-comparison layer. Phase 15 must NOT compete with this — it enriches nodes, not snapshots. The two systems coexist via separate artifacts.

#### Table Stakes (Users Expect These)

| Feature | Why Expected | Complexity | Depends On | Notes |
|---------|--------------|------------|------------|-------|
| Async deriver queue separate from foreground pipeline | Honcho's queue pattern. The pipeline completes and writes graph.json; derivers enqueue and run. Pipeline must NEVER wait for derivers. | MEDIUM | New `graphify/derivers.py` + queue file `graphify-out/deriver_queue.jsonl` | Simple file-backed queue. Each line: `{deriver_id: str, target_node_id: str, priority: int, enqueued_at: iso8601}`. Separate process reads + executes. No new required deps — Python stdlib `multiprocessing` or subprocess. |
| `graphify derive` CLI command | Users run derivers explicitly, not ambiently. Matches D-73 skill-is-driver shape. | LOW | derivers.py + __main__.py | Command reads queue, executes all pending derivers, updates `enrichments.json` sidecar. Idempotent — running twice produces same result. |
| Enrichment sidecar distinct from graph.json | graph.json is pipeline output; `enrichments.json` is deriver output. Never mutate graph.json from a deriver. | LOW | New sidecar file + serve.py merge on read | `{node_id: {description_enriched: "...", detected_patterns: [...], derived_at: iso8601, deriver_version: "v1"}}`. MCP `get_node` merges enrichment into response at read time. |
| Rebuild-safety: deriver results survive graph rebuild when node identity stable | Agents wastes value if running `/graphify` after derivers wipes their output. Stable-ID preservation is the contract. | LOW | enrichments.json keyed by node_id | On rebuild, node IDs that still exist retain their enrichment; nodes that vanish get their enrichment garbage-collected after N snapshots. Uses v1.1 FRESH/STALE/GHOST machinery to identify stale enrichments. |
| Deriver discovery via entry points | Users/agents add custom derivers without modifying graphify core. | MEDIUM | Python `pyproject.toml` entry points | `graphify.derivers` entry-point group. Built-ins register via same mechanism. Third-party derivers install as pip packages. |

#### Differentiators (Competitive Advantage)

| Feature | Value Proposition | Complexity | Depends On | Notes |
|---------|-------------------|------------|------------|-------|
| Four built-in derivers matching research signals | Honcho: summaries + representations. Letta: reflection. Cognee: patterns. graphify: `description_enrichment`, `pattern_detection`, `community_summary`, `staleness_refresh`. | HIGH | Built-in deriver implementations + LLM sampling | **(1) description_enrichment:** For nodes with thin `label` and rich `source_file`, extract docstring/comment → generate 1-line description. **(2) pattern_detection:** Across last N snapshots, detect recurring community-migration patterns ("transformer nodes keep jumping to attention community"). **(3) community_summary:** Per-community natural-language 2-sentence summary. **(4) staleness_refresh:** Scan v1.1 STALE nodes and decide whether to re-extract or demote. Each is 1 plan. |
| Session-queue pattern for concurrent derivers | Honcho's session-scoping prevents race. graphify's analog: partition derivers by community — one process per community max. | MEDIUM | derivers.py + community → process-slot map | Enrichments mutated on the same community execute sequentially; parallel across communities. Matches graphify's existing community partition. |
| Bounded-staleness tolerance for deriver output | Letta's "sleep-time" insight — it's OK if enrichment is slightly stale relative to graph build, as long as the contract is explicit. | LOW | enrichments.json timestamp + read-time TTL check | If `derived_at < graph_built_at - 30d`, mark enrichment as potentially stale in the MCP response (`"enrichment_staleness": "aging"`). Agents see the freshness signal and can decide whether to trust. |
| Deriver dry-run for previewing cost | LLM-sampling-based derivers have real token cost. Users preview before committing. | LOW | derivers.py + cost estimator | `graphify derive --dry-run` outputs: "This run would process 47 nodes via description_enrichment at ~12K tokens (~$0.04)." No actual LLM calls. |
| Post-build hook integration | `graphify run` can optionally enqueue derivers at build-end via `--enrich` flag. Opt-in, not default. | LOW | Existing pipeline + queue enqueue | After successful build, optionally append `derive_after_build` marker to queue. User runs `graphify derive` later; or CI runs it async. |

#### Anti-Features

| Anti-Feature | Why Avoid | Alternative |
|--------------|-----------|-------------|
| Real-time rebuild on every file-change in the corpus | Conflicts with `delta.py`'s snapshot-comparison design (one build produces one snapshot; deltas compute at snapshot boundaries). Real-time contradicts this. | Derivers are post-build passes. Snapshot boundaries defined by `graphify run` invocations, not file-change events. Watch mode triggers EXTRACTION only; enrichment is still explicit. |
| Blocking the pipeline waiting for derivers to complete | Defeats the whole "async" point. Users who wait on the pipeline get slower runs for optional enrichment. | Pipeline completes, writes graph.json, returns control. Derivers queue and run later. Enrichment appears in later MCP reads; never gates the build. |
| Derivers that can mutate graph.json | graph.json is the pipeline's ground truth. Derivers write to sidecar only. | Separate `enrichments.json`. MCP server merges enrichment with node data at query time. Pipeline re-builds overwrite graph.json but leave enrichments.json alone. |
| Derivers that run arbitrary user-supplied Python | Security escalation — derivers get LLM keys, graph access, filesystem. Arbitrary user code inherits all of that. | Entry-point-registered derivers only. Documented trust boundary: installing a third-party deriver = trusting it like any pip package. |
| LLM-sampling derivers without budget caps | Easy to burn $100+ on a large graph. Users who didn't realize won't forgive. | Every LLM-sampling deriver declares `max_tokens_per_run` in its manifest. `graphify derive` enforces the cap and reports cost post-run. |
| Implicit deriver invocation from MCP `get_node` | Turning a read into a potentially-expensive computation breaks the MCP primitive's cost model. Agents can't budget if reads can unexpectedly invoke LLM calls. | Derivers run via explicit `graphify derive` CLI. MCP reads return enrichment if present, empty if not. No lazy computation. |

---

### Phase 16: Graph Argumentation Mode

**Ecosystem reality (SPAR-Kit docs, fetched):**

- **POPULATE:** Instantiates distinct personas with coherent, conflicting worldviews (Visionary/North, Challenger/East, Pragmatist/South, Sage/West). Not generic perspectives — characters with genuine disagreement built in.
- **ABSTRACT (v8.0+):** Constructs a "shared cognitive map" before debate. Elevated from sub-activity to dedicated step after validation showed **+40% synthesis quality improvement**. This is the key step for graphify.
- **RUMBLE:** Structured dialectic across multiple rounds. Three intensities: "clash" (4+ rounds), "rumble" (8+), "domain" (4+). Personas defend positions rather than listing trade-offs.
- **KNIT:** Moderator synthesizes tensions — identifies patterns and contradictions, not false balance.
- **Output:** Actionable recommendations grounded in dialectical reasoning (not raw arguments).

**Why graphify is uniquely positioned (strategic synthesis from internal notes):**

> "The single most important insight from this research is from SPAR-Kit: the ABSTRACT step — building a shared cognitive map before structured debate — is the step that makes multi-perspective analysis genuinely valuable. Graphify already builds that cognitive map. No other tool in this space has the structured representation pre-built." — `.planning/notes/repo-gap-analysis.md`

Graphify's knowledge graph IS SPAR-Kit's ABSTRACT. Competitors running multi-perspective analysis start with raw prose; graphify starts with nodes, communities, god nodes, bridge edges, and cross-file relationships. That structural head-start is the differentiator.

**Phase 9 (autoreason tournament) already implements A/B/AB/Borda.** Phase 16 extends to full POPULATE→ABSTRACT→RUMBLE→KNIT for a user-posed question about the codebase.

#### Table Stakes (Users Expect These)

| Feature | Why Expected | Complexity | Depends On | Notes |
|---------|--------------|------------|------------|-------|
| User-posed question triggers argumentation | Otherwise it's just another autoreason pass. The whole point is user-initiated decision support. | LOW | New MCP tool / skill command | `argue(question: str)` tool. Question is natural language: "Should we refactor the auth module?" No structured query language. |
| Subgraph selection given question (SPAR-Kit POPULATE analog) | Not every node is relevant. Send the whole graph = token blowout. Must scope. | MEDIUM | v1.3 Phase 9.2 bidirectional BFS + cardinality estimator | Translate question into seed nodes (keyword match + embedding if available) → expand via BFS with budget. Return at most 50 nodes. Reuses token-aware budget from v1.3. |
| 2–4 personas argue over subgraph | SPAR-Kit minimum for genuine tension. Single-persona = no debate. | LOW | Phase 9 tournament persona machinery | Personas: Architect, Maintainer, Security-reviewer, Newcomer (recycled from Phase 9 lens list with SPAR-Kit persona framing). Each reads the subgraph + question → stakes out position. |
| Structured output with decision + rationale | SPAR-Kit output format: "actionable recommendations grounded in dialectical reasoning." Not raw arguments. | MEDIUM | KNIT synthesis + output template | Output format: `{verdict: str, rationale: [argument_points], tensions_unresolved: [open_questions], graph_evidence: [node_ids]}`. Written to `GRAPH_ARGUMENT.md` parallel to v1.2 `GRAPH_ANALYSIS.md`. |
| Advisory-only framing everywhere | The tool informs; the human decides. Auto-applying argumentation output to the codebase violates this. | LOW | Output template + docs | Every output file ends with fixed disclaimer: "This is graphify's advisory synthesis. It does not replace human decision-making; it stress-tests your thinking against the graph's structure." |

#### Differentiators (Competitive Advantage)

| Feature | Value Proposition | Complexity | Depends On | Notes |
|---------|-------------------|------------|------------|-------|
| Graph-as-ABSTRACT substrate | Unique to graphify. SPAR-Kit tools bring their own ABSTRACT; graphify brings a structural one built from the user's actual code. The subgraph IS the cognitive map. | MEDIUM | Subgraph selection + explicit "ABSTRACT" payload to personas | Each persona's prompt includes: `(1) the question, (2) the subgraph serialized as `{nodes, edges, communities, god_nodes, bridges}`, (3) persona identity. Identical ABSTRACT across personas eliminates confirmation bias. |
| Graph-grounded citation requirement | Personas MUST cite node IDs when arguing. Prevents fabrication at the source (carried from Phase 11 anti-fabrication guard). | MEDIUM | Output parser + graph-ID lookup | Argument format: "The auth module is load-bearing [cite: node_auth_middleware]." Post-hoc validator checks every `[cite: X]` → valid graph node. Invalid cites → argument rejected, persona re-prompted. |
| INTERROGATE step (SPAR-Kit optional) | After KNIT, stress-test: "what would have to be true for this recommendation to be wrong?" Deepens the output at configurable cost. | MEDIUM | Separate interrogation-persona pass | Opt-in: `argue --interrogate`. Adds 1 persona round specifically challenging the synthesis. |
| Configurable intensity (clash / rumble / domain) | SPAR-Kit intensities map to token budget. Users pick depth vs. cost. | LOW | Round-count parameter | CLI: `argue --intensity clash` (2 rounds, 2 personas), `rumble` (4 rounds, 3 personas), `domain` (6 rounds, 4 personas). Default: `clash`. |
| Persona memory across sessions | Personas remember past arguments on same/related questions. Useful for longitudinal decisions ("we discussed this 3 months ago — here's what changed"). | HIGH | v1.1 annotation sidecar + new argument-history index | Argument outputs stored in `graphify-out/arguments/{uuid}.json` keyed by question + subgraph-hash. On re-argue with similar question, surface prior arguments and changes since. |

#### Anti-Features

| Anti-Feature | Why Avoid | Alternative |
|--------------|-----------|-------------|
| Auto-applying argumentation output to code | Single worst possible outcome: LLM-synthesized refactor applied without human review. | Output is ADVISORY. graphify never edits code files. Argue produces `.md`; humans act. |
| Personas that fabricate nodes to support arguments | Undermines the whole graph-grounded value prop. Phase 11's lesson applies. | Mandatory `[cite: node_id]` format + post-hoc validator. Arguments without valid cites are rejected, persona re-prompted once, then dropped. |
| Replacing Phase 9 autoreason tournament | Autoreason is for diagnostic analysis ("what's wrong with this codebase?"); argumentation is for decision support ("should we do X?"). Different purposes. | Both coexist. `GRAPH_ANALYSIS.md` (Phase 9) for diagnosis; `GRAPH_ARGUMENT.md` (Phase 16) for decisions. |
| Unbounded persona round count | Debates spiral. Cost balloons. Output quality plateaus after ~4 rounds per SPAR-Kit research. | Hard cap: 6 rounds per argument. Configurable via intensity; not unbounded. |
| Vision/image input in subgraph | Out of scope for Phase 16. Keeps subgraph-serialization simple. | Text-only subgraph representation. Future phase if user demand warrants. |
| Consensus-forcing synthesis | Real disagreement is the signal. Forcing KNIT to produce a single "winning" answer destroys it. | Output format includes `tensions_unresolved: [...]` as first-class. If personas genuinely disagree, synthesis says so. |

---

### Phase 17: Conversational Graph Chat

**Ecosystem reality (Letta-Obsidian README, fetched):** Chat sidebar is a "Modal chat UI with support for reasoning displays, tool calls, and rich responses" — users ask natural-language questions about their vault; agent reasons over synced files with persistent memory.

**What users typically ask** (extrapolated from letta-obsidian patterns + internal research notes):

- *Topology:* "What connects module X to module Y?" "What depends on the auth module?" "Which files import pandas?"
- *Communities:* "Explain community 3." "What is the main theme of the largest cluster?" "Why did this group of files cluster together?"
- *Centrality:* "What are the most fragile parts?" "Which nodes are god nodes and why?"
- *Change:* "What changed since last run?" "What's new in the transformer community?"
- *Exploration:* "Show me the neighborhood of `extract_python`." "What files are related to this concept?"

**NL → structured traversal patterns** (synthesized from MCP tool usage + graph query shapes):

| NL intent | Translation |
|-----------|-------------|
| "connects X to Y" | `query_graph(start=X, end=Y, mode=path)` — existing Phase 9.2 tool |
| "explain community N" | `graph_summary(community=N)` — existing Phase 11 `/context` tool |
| "what depends on X" | `query_graph(start=X, direction=inbound, depth=2)` |
| "fragile parts" | `god_nodes` + high-edge-concentration detection — existing analyze.py |
| "changed since last run" | `get_delta()` — existing v1.1 GRAPH_DELTA.md machinery |
| "neighborhood of X" | `query_graph(start=X, depth=1)` |

**Anti-fabrication is non-negotiable** — Phase 11 already established this. Phase 17 must carry forward.

#### Table Stakes (Users Expect These)

| Feature | Why Expected | Complexity | Depends On | Notes |
|---------|--------------|------------|------------|-------|
| NL → MCP tool-call translation | The whole point. User asks in English; graphify translates to structured query. | MEDIUM | LLM-sampling MCP primitive OR client-side LLM + tool-list | Two-path: (1) client LLM (Claude Desktop, Claude Code) already picks tools — graphify's job is to describe tools clearly; (2) standalone skill file that an agent reads and uses as its system prompt. Prefer path 2 — less coupling. |
| Answer grounded in cited graph content | Users can't distinguish hallucinated graph content from real. Citations are the trust mechanism. | MEDIUM | Tool result → answer renderer | Every fact in the answer cites `[node:node_id]` or `[edge:source→target]`. Answer template enforces the citation format; post-hoc validator rejects uncited claims. |
| "No relevant graph content" response | Graceful handling when the graph doesn't know the answer. Better than fabrication. | LOW | Pre-query check + fixed response template | If query results are empty: "The graph doesn't cover that topic. Consider running `/graphify` on the relevant files, or asking about [top 3 nearby topics]." |
| Conversation history tied to graph state | Follow-up questions ("what about X's dependencies?") need context from the prior answer. | MEDIUM | v1.1 session scoping + session-aware MCP tools | MCP tool `chat_session(session_id, message)` maintains short context of prior tool calls + answers within a session. Session expires per config. |

#### Differentiators (Competitive Advantage)

| Feature | Value Proposition | Complexity | Depends On | Notes |
|---------|-------------------|------------|------------|-------|
| Grounded in structured graph vs. raw file content | Letta-Obsidian reads raw files; graphify reasons over extracted-and-deduplicated graph nodes. More signal, less noise. | MEDIUM | Existing graph + MCP tools | No new feature — this is the inherent advantage. Surface it in docs: "graphify's chat cites nodes, not chunks." |
| Automatic suggestion of follow-up queries | After an answer, graphify suggests 2–3 follow-ups grounded in the graph ("you might also want to know about Y, since it shares a community with X"). | MEDIUM | Graph neighborhood of answer nodes | Post-answer renderer computes: from answer's cited nodes, find high-centrality neighbors not yet discussed → suggest. Reuses Phase 11's "thinking partner" voice. |
| Chat-to-argue handoff | When a chat query turns into a decision ("should we refactor?"), seamlessly escalate to Phase 16 argumentation. | MEDIUM | Phase 16 integration | If answer detects decision-framing keywords ("should", "could we", "is it worth"), offer: "This looks like a decision. Want me to run `/argue` over this subgraph?" User accepts → pipelines into argumentation. |
| Chat output as vault note | User asks a question; answer is useful enough to save. One-command persistence to vault. | MEDIUM | v1.1 propose_vault_note + chat history | "Save this as a note?" → generates MD with question/answer/cited-nodes → proposes via v1.1 approval CLI. Human-in-the-loop preserved. |
| Transparent query display | Power users want to see the translated MCP call. Debuggability + trust. | LOW | Answer renderer + verbose mode | `/chat --verbose "what depends on auth?"` shows: `> query_graph(start="auth", direction=inbound) → 4 nodes`, then the prose answer. |

#### Anti-Features

| Anti-Feature | Why Avoid | Alternative |
|--------------|-----------|-------------|
| Chat answering without any tool call | If graphify produces answers without querying the graph, it's just ChatGPT with extra steps. The value is graph-grounding. | Enforce: every answer must include at least one graph citation. If no citations → emit "no relevant graph content" response. |
| Fabricating node IDs or edges in answers | Single worst failure mode. Erodes trust instantly and permanently. | Cite format `[node:id]` validated post-hoc. Invalid cites → answer rejected, regenerated once, then fall back to "no relevant graph content." |
| Open-ended conversation memory | Cross-session memory for a chat interface creates privacy and context-bloat concerns. | Session-scoped chat history only. New session = fresh context. Persistence is via save-as-note, not session memory. |
| Voice-style matching without disclosure | Same anti-impersonation rule as Phase 11 `/ghost` and Phase 14 `/voice`. | Chat answers in neutral tool-voice, not user-voice. Voice mode is an explicit opt-in via `/voice`. |
| Real-time vault watching to auto-update chat context | Defeats session-scoping and conflicts with watch.py's single-responsibility (code re-extraction). | User must explicitly re-run `/graphify` to refresh graph; chat uses current graph state only. |
| Answers longer than 500 tokens | Mirrors Phase 11 discipline. Chat answers that sprawl lose readers. | Hard cap in skill file. Exceeding the cap triggers a summarization pass, not truncation. |

---

### Phase 18: Focus-Aware Graph Context

**Ecosystem reality (Letta-Obsidian, fetched):** The plugin has "Intelligent File Change Detection" comparing file sizes and timestamps, auto-syncing on change. Focus-mode specifics are NOT documented in the README — the plugin's actual focus-mode trigger and granularity are implementation details not public. Internal notes summarize Letta's focus as: "tracks which note the user is currently viewing, injects it as a memory block into the agent's context."

**Granularity question — what should "focus" mean in graphify?**

| Option | Trigger | Graph resolution | Complexity |
|--------|---------|------------------|------------|
| Git HEAD | `git log -1` checkout moved | File-set in latest commit | LOW — already in `hooks.py` |
| Active editor file | Harness-supplied context | One file → one node | MEDIUM — requires harness cooperation |
| Cursor position | IDE/LSP signal | Function/class at cursor | HIGH — requires LSP integration |
| Working directory | `pwd` of harness process | Directory → cluster | LOW |

For v1.4, **active editor file is the sweet spot:** harnesses (Claude Code, Cursor, Continue) can supply the active-file path via MCP tool argument. Finer granularity (cursor) defers to future; coarser (git HEAD) is a nice-to-have supplement.

#### Table Stakes (Users Expect These)

| Feature | Why Expected | Complexity | Depends On | Notes |
|---------|--------------|------------|------------|-------|
| `get_focus_context(file_path)` MCP tool | The anchor feature. Accepts a file path, returns the node + neighborhood + community + connected nodes. | MEDIUM | `serve.py` + existing neighborhood query | Returns `{node, edges, community: {id, label, members_summary}, neighbors_1hop: [...], neighbors_2hop_sample: [...]}`. Uses v1.3 token-aware budget for size control. |
| File-path-to-node-id resolution | Users/agents pass a path; graphify needs to find the matching node. Must handle absolute, relative, and ambiguous cases. | LOW | Existing `source_file` node attribute + resolver | Tries exact match → suffix match → normalized-path match. Returns match confidence. Ambiguous → top-3 candidates for user disambiguation. |
| Graceful "no graph for this file" response | Harness might focus on a file graphify hasn't extracted. Must handle without error. | LOW | Pre-check + fixed response template | If no node matches: `{focus: null, reason: "file_not_in_graph", suggestion: "run /graphify to include this file"}`. Agents handle gracefully. |
| Focus context as a graph "zoom" | Users viewing a file want the graph scoped to their work. Visualization aid. | MEDIUM | Focus tool + viz command | `graphify focus <file_path>` CLI command re-renders HTML viz scoped to the file's 2-hop neighborhood. Uses existing `export.py` HTML generator with pre-filtered graph. |

#### Differentiators (Competitive Advantage)

| Feature | Value Proposition | Complexity | Depends On | Notes |
|---------|-------------------|------------|------------|-------|
| Focus-aware chat routing | Phase 17 chat can implicitly scope to focus file. "What's this connected to?" → resolves "this" to focus file. | LOW | Phase 17 chat + Phase 18 focus | Chat tool accepts optional `focus_file` param. If present, queries default to that subgraph. Explicit focus; no ambient capture. |
| Focus-filtered analysis lenses | Phase 9 autoreason tournament can run on focus subgraph only. "Analyze auth.py specifically" rather than whole-graph. | MEDIUM | Phase 9 + Phase 18 | `analyze --focus auth.py` runs full tournament on just the file's 2-hop neighborhood. Faster, cheaper, more actionable. |
| Git-HEAD-complement for "what changed here" | When focus file overlaps with recent commits, surface the change history. Integrates with v1.1 delta. | MEDIUM | Existing hooks.py + delta.py | Focus tool optionally returns `recent_changes: [{snapshot_id, nodes_added, nodes_removed}]` for the focus file's nodes. Useful for onboarding to a codebase. |
| Focus transfer to Phase 14 vault commands | If focus file has a backing vault note (via v1.1 vault-manifest), `/related`, `/bridge`, `/orphan` scope to that note automatically. | MEDIUM | Phase 14 + Phase 18 + v1.1 vault-manifest | Commands read `focus_note` from focus-context. Seamless switch between code-focus and vault-focus modes. |
| `focus_snapshot` for agent session context | Agent begins a task by setting focus; all subsequent MCP calls implicitly carry focus context unless overridden. Reduces repetitive parameter passing. | MEDIUM | serve.py session state + v1.1 session_id | New MCP tool `set_focus(session_id, file_path)`. Subsequent calls in session inherit focus unless overridden. Explicit setup, not ambient. |

#### Anti-Features

| Anti-Feature | Why Avoid | Alternative |
|--------------|-----------|-------------|
| Real-time cursor-position tracking | Requires IDE/LSP integration; out of scope for a Python CLI library. | Harness-supplied `file_path` on each MCP call. Granularity is file-level; cursor-level deferred. |
| Ambient focus capture (filesystem watcher) | D-18 explicitly constrains this — watch.py is for code re-extraction, not cross-feature wiring. | Explicit `set_focus` or per-call `focus_file` parameter. Focus is always an explicit signal. |
| Multi-file focus (e.g., "these 5 files") | Most use cases are single-file. Multi-file blurs into query territory. | If user wants multi-file: use Phase 17 chat with explicit file list. Focus is one file. |
| Focus that auto-adjusts depth | Harness signals focus; graphify doesn't guess at depth. | Fixed defaults (depth=2); user can override via explicit param. No learning/heuristics. |
| Persistent focus across sessions | Focus is task-scoped; persisting across sessions creates confusion when a new task starts. | Focus lives in session state (via v1.1 session_id). New session = fresh focus. |
| Focus that mutates the graph or enrichments | Read-only operation. Any mutation belongs to v1.1 write tools, not focus. | `get_focus_context` is read-only. No side effects. |

---

## Feature Dependencies

```
Phase 12: Heterogeneous Extraction Routing
  role-based model config (primary + boilerplate + vision slots)
      └──required by──> per-file complexity classifier
      └──required by──> parallel extraction across endpoints
      └──required by──> token-cost reporting
  AST-metric classifier (graphify/complexity.py)
      └──enhances──> existing extract.py LanguageConfig dispatch
      └──feeds──> per-file model stamp in node metadata

Phase 13: Agent Capability Manifest
  MCP initialize handshake (existing in serve.py)
      └──required by──> capability manifest resource
      └──required by──> cost_class tool annotation
      └──required by──> self-describing graphify.status() tool
  server.json at repo root
      └──required by──> MCP registry listing
      └──required by──> version compatibility manifest

  SEED-002 Harness Memory Export
    canonical schema layer
        └──required by──> CLAUDE.md export
        └──required by──> AGENTS.md export
        └──required by──> harness_import.py (inverse direction)
    round-trip manifest
        └──enhances──> graphify import-harness
        └──enhances──> graphify export-harness

Phase 14: Obsidian Thinking Commands
  v1.0 profile.py + templates.py + merge.py (built)
      └──required by──> /moc, /wayfind, /orphan
  v1.1 propose_vault_note + approval CLI (built)
      └──required by──> /bridge (when emitting new notes)
  Phase 17 chat
      └──enhances──> /voice (natural-language retrieval)

Phase 15: Async Background Enrichment
  async deriver queue (new)
      └──required by──> description_enrichment deriver
      └──required by──> pattern_detection deriver
      └──required by──> community_summary deriver
      └──required by──> staleness_refresh deriver
  entry-point registration
      └──enables──> third-party derivers
  v1.1 FRESH/STALE/GHOST (built)
      └──consumed by──> staleness_refresh deriver

Phase 16: Graph Argumentation Mode
  v1.3 Phase 9.2 bidirectional BFS + budget (built)
      └──required by──> subgraph selection (SPAR-Kit POPULATE analog)
  Phase 9 tournament persona machinery (built)
      └──required by──> persona prompt construction
  graph-grounded citation validator
      └──required by──> anti-fabrication guard
  subgraph ABSTRACT payload
      └──unique to graphify (no competitor has this)

Phase 17: Conversational Graph Chat
  existing MCP tool surface (query_graph, graph_summary, get_delta)
      └──required by──> NL → tool-call translation
  graph-grounded citation validator
      └──required by──> answer grounding
  Phase 16 argue tool
      └──enhances──> chat-to-argue handoff
  Phase 18 focus context
      └──enhances──> focus-aware chat routing

Phase 18: Focus-Aware Graph Context
  existing neighborhood query in serve.py (built)
      └──required by──> get_focus_context MCP tool
  v1.1 vault-manifest.json (built)
      └──required by──> focus transfer to vault commands (Phase 14)
  v1.1 session_id (built)
      └──required by──> set_focus MCP tool + session-scoped focus

Cross-phase dependencies:
  Phase 13 Capability Manifest ← Phase 12 cost-class labels (cheap extraction hint)
  Phase 13 Capability Manifest ← Phase 15 deriver-available flag
  Phase 14 Obsidian Commands ← Phase 17 Chat (for /voice natural-language retrieval)
  Phase 14 Obsidian Commands ← Phase 18 Focus (auto-scope when focus has vault note)
  Phase 16 Argue ← Phase 17 Chat (decision keywords trigger handoff)
  Phase 17 Chat ← Phase 18 Focus (focus file → implicit chat scope)
  Phase 18 Focus ← Phase 16 Argue (analyze --focus scopes argument subgraph)
```

### Dependency Notes

- **Phase 12 has no upstream deps beyond existing extract.py.** Fully parallelizable with other v1.4 phases. Likely ships first (complexity classifier is simple; role-config is trivial).
- **Phase 13 Manifest and SEED-002 Export are natural companions** but independent: Manifest ships without Export; Export ships without Manifest. SEED-002 activation rule explicitly suggests shipping them together.
- **Phase 14 Obsidian commands depend on v1.0 profile + v1.1 write-back** — both built. Low new-code risk; mostly `.claude/commands/*.md` skill files + new MCP tools on existing infrastructure.
- **Phase 15 Async Enrichment must NOT block the pipeline** — enforced architecturally via queue file separation. Pipeline never awaits derivers; derivers run via explicit `graphify derive` CLI.
- **Phase 16 Argumentation's unique value comes from graph-as-ABSTRACT** — the dependency on v1.3 subgraph selection (bidirectional BFS + budget) is load-bearing. Shipping without it means sending unbounded graphs to personas.
- **Phase 17 Chat benefits from Phase 16 and Phase 18 but doesn't require them.** Could ship alone as a read-only NL-to-MCP translator.
- **Phase 18 Focus is small, widely-reusable, and unblocks Phase 14 and Phase 17 enhancements.** Consider shipping early for cross-phase leverage.
- **Phase 13 + SEED-002 together form the "agent discoverability" payload.** Phase 12, 15, 18 form the "infrastructure" payload. Phase 14, 16, 17 form the "user-facing interaction" payload. These three bundles inform phase-ordering in the roadmapper.

---

## MVP Definition

### Phase 12 — Launch With

- [ ] Two-tier model config (`primary_model`, `boilerplate_model`) via env var or profile
- [ ] Complexity classifier: AST nodes + cyclomatic + imports → `simple` | `complex` buckets
- [ ] Per-file-type defaults (`.json/.toml/.yaml` → boilerplate)
- [ ] Parallel extraction via `concurrent.futures.ThreadPoolExecutor`
- [ ] Per-node `extracted_by_model` metadata
- [ ] Token-cost summary line in pipeline output

### Phase 13 + SEED-002 — Launch With

- [ ] Audit of all existing MCP tool descriptions for agent-action verbs
- [ ] `server.json` at repo root matching registry spec
- [ ] `graphify://capabilities/manifest` MCP resource with full tool list + cost_class
- [ ] `graphify.status()` MCP tool (graph presence + stats + recommended first action)
- [ ] `graphify export-harness --format claude` producing CLAUDE.md (renamed in docs to avoid user-file collision)
- [ ] Canonical schema layer (`graphify/harness_schemas/canonical.yaml`)
- [ ] README capability section + `_meta` publisher-provided metadata

### Phase 14 — Launch With

- [ ] `/moc <community>` — compose MOC via v1.0 template + `propose_vault_note`
- [ ] `/related <note-path>` — three-bucket output (same community / bridge / semantically similar)
- [ ] `/orphan` — vault-orphan vs graph-orphan distinction
- [ ] `/wayfind <note-path>` — hierarchy breadcrumbs from profile
- [ ] All commands profile-driven (adapt to `.graphify/profile.yaml`)
- [ ] All write operations through `propose_vault_note` (no auto-write)

### Phase 15 — Launch With

- [ ] File-backed queue at `graphify-out/deriver_queue.jsonl`
- [ ] `graphify derive` CLI (read queue, execute, write `enrichments.json`)
- [ ] Built-in: `description_enrichment` deriver
- [ ] Built-in: `community_summary` deriver
- [ ] Enrichment sidecar separate from graph.json; MCP `get_node` merges at read time
- [ ] Entry-point registration for third-party derivers
- [ ] `graphify derive --dry-run` cost preview

### Phase 16 — Launch With

- [ ] `argue(question)` MCP tool / skill command
- [ ] Subgraph selection via keyword + BFS with budget cap (≤50 nodes)
- [ ] 3-persona default: Architect / Maintainer / Newcomer (recycled from Phase 9)
- [ ] Mandatory `[cite: node_id]` format + post-hoc validator
- [ ] `GRAPH_ARGUMENT.md` output (parallel to `GRAPH_ANALYSIS.md`)
- [ ] Advisory-only disclaimer in every output

### Phase 17 — Launch With

- [ ] Standalone skill file describing NL-to-MCP-tool translation (no new MCP tools required initially)
- [ ] Every answer cites `[node:id]` / `[edge:a→b]` with post-hoc validation
- [ ] "No relevant graph content" response template
- [ ] Suggested follow-up queries based on cited-node neighbors
- [ ] Hard 500-token answer cap (mirrors Phase 11)

### Phase 18 — Launch With

- [ ] `get_focus_context(file_path)` MCP tool (node + 1-hop + 2-hop sample + community)
- [ ] File-path → node-id resolver (exact / suffix / normalized / top-3 ambiguous)
- [ ] "File not in graph" response shape
- [ ] `graphify focus <path>` CLI (renders focus-scoped HTML viz)
- [ ] `set_focus(session_id, file_path)` for session-carried focus

### Add After Validation (v1.4.x)

- [ ] Phase 12 vision-model routing (separate slot)
- [ ] Phase 12 bounded-staleness tolerance for parallel extraction
- [ ] Phase 13 MCP registry publishing workflow (CI)
- [ ] Phase 14 `/voice`, `/bridge`, `/drift-notes` (built on top of Phase 17 + MVP commands)
- [ ] Phase 15 `pattern_detection` + `staleness_refresh` derivers
- [ ] Phase 16 INTERROGATE step (opt-in via `--interrogate`)
- [ ] Phase 16 persona memory across sessions
- [ ] Phase 17 chat-to-argue handoff
- [ ] Phase 17 save-answer-as-vault-note flow
- [ ] Phase 18 focus-filtered analysis lenses (`analyze --focus <file>`)
- [ ] Phase 18 focus transfer to vault commands

### Future Consideration (v1.5+)

- [ ] Learned routing (Phase 12) — requires training dataset that doesn't yet exist
- [ ] Phase 15 real-time deriver pipeline — contradicts current snapshot-boundary design
- [ ] Phase 17 cross-session conversation memory — privacy and context-bloat concerns
- [ ] Phase 18 cursor-level focus granularity — requires LSP integration

---

## Feature Prioritization Matrix

| Feature | User Value | Implementation Cost | Priority |
|---------|------------|---------------------|----------|
| **Phase 12** | | | |
| Role-based model config (2-slot) | HIGH (cost savings materialize) | LOW | P1 |
| Complexity classifier + threshold routing | HIGH (differentiator; no competitor has it) | MEDIUM | P1 |
| Parallel extraction | HIGH (latency win on large repos) | MEDIUM | P1 |
| Token-cost reporting | HIGH (feature invisibility without it) | LOW | P1 |
| Per-node `extracted_by_model` | MEDIUM (audit/trust) | LOW | P2 |
| Vision-model routing | MEDIUM (serves image-heavy vaults) | MEDIUM | P2 |
| Bounded-staleness tolerance | LOW (edge case) | MEDIUM | P3 |
| **Phase 13 + SEED-002** | | | |
| MCP tool description audit | HIGH (agent-picks-us moment) | LOW | P1 |
| `server.json` at repo root | HIGH (registry prerequisite) | LOW | P1 |
| Capability manifest resource | HIGH (three-tier discovery complete) | MEDIUM | P1 |
| `graphify.status()` tool | HIGH (first-call discoverability) | LOW | P1 |
| `graphify export-harness --format claude` | HIGH (lock-in exit) | LOW | P1 |
| Canonical schema layer | MEDIUM (needed for multi-format but low user impact day 1) | MEDIUM | P2 |
| Inverse `import-harness` | MEDIUM (closes loop; asymmetric without it) | HIGH | P2 |
| Registry auto-publish CI | LOW (manual fine for v1.4) | LOW | P3 |
| **Phase 14** | | | |
| `/moc <community>` | HIGH (core vault workflow) | LOW | P1 |
| `/related <note>` | HIGH (table stakes; competitor baseline) | LOW | P1 |
| `/orphan` | HIGH (vault-user paranoia pain) | MEDIUM | P1 |
| `/wayfind <note>` | MEDIUM (existing wayfinder tooling) | LOW | P2 |
| Profile-driven command output | HIGH (framework adaptation) | MEDIUM | P2 |
| `/voice`, `/bridge`, `/drift-notes` | MEDIUM (advanced user features) | HIGH | P2 |
| **Phase 15** | | | |
| Async deriver queue | HIGH (architecture foundation) | MEDIUM | P1 |
| `description_enrichment` built-in | HIGH (biggest node-quality win) | MEDIUM | P1 |
| `community_summary` built-in | HIGH (surfaces into reports) | MEDIUM | P1 |
| Entry-point deriver registration | HIGH (extension story) | MEDIUM | P1 |
| `graphify derive --dry-run` | HIGH (cost trust) | LOW | P1 |
| Post-build hook integration | MEDIUM | LOW | P2 |
| `pattern_detection` deriver | MEDIUM (multi-snapshot; needs >1 run) | MEDIUM | P2 |
| `staleness_refresh` deriver | LOW (partially covered by v1.1) | MEDIUM | P3 |
| **Phase 16** | | | |
| `argue(question)` MCP tool | HIGH (core feature) | MEDIUM | P1 |
| Subgraph selection with budget | HIGH (cost control) | MEDIUM | P1 |
| `[cite: node_id]` mandatory format | HIGH (anti-fabrication) | MEDIUM | P1 |
| `GRAPH_ARGUMENT.md` output | HIGH (actionable artifact) | MEDIUM | P1 |
| Advisory-only framing | HIGH (trust / liability) | LOW | P1 |
| Configurable intensity | MEDIUM | LOW | P2 |
| INTERROGATE step | MEDIUM (adds ~40% quality per SPAR-Kit) | MEDIUM | P2 |
| Persona memory across sessions | LOW (longitudinal only) | HIGH | P3 |
| **Phase 17** | | | |
| Skill file for NL-to-tool translation | HIGH (feature exists or doesn't) | LOW | P1 |
| Cited-answer enforcement | HIGH (anti-fabrication) | MEDIUM | P1 |
| "No graph content" response | HIGH (graceful failure) | LOW | P1 |
| Suggested follow-ups | MEDIUM | LOW | P2 |
| Chat-to-argue handoff | MEDIUM (requires Phase 16) | LOW | P2 |
| Save-as-vault-note | MEDIUM (persistent value) | MEDIUM | P2 |
| Verbose mode (show the tool call) | LOW (power users only) | LOW | P3 |
| Cross-session memory | LOW (privacy + bloat concerns) | HIGH | P3 (deferred) |
| **Phase 18** | | | |
| `get_focus_context(file_path)` | HIGH (core tool) | MEDIUM | P1 |
| File-path → node resolver | HIGH (unblocks everything) | LOW | P1 |
| "File not in graph" graceful response | HIGH (UX) | LOW | P1 |
| `graphify focus <path>` CLI viz | MEDIUM (power user) | MEDIUM | P2 |
| `set_focus(session_id, path)` | MEDIUM (enables session-carried focus) | MEDIUM | P2 |
| Git-HEAD focus complement | LOW (supplement) | MEDIUM | P3 |

**Priority key:**
- P1: Must have for v1.4 launch — defines the milestone
- P2: Should have, add when capacity allows; may split into `v1.4.x`
- P3: Defer to v1.5+ or revisit after UAT

---

## Competitor Feature Analysis

| Feature | Continue / Aider / Cursor / Cline | Letta / Letta-Obsidian | Honcho | SPAR-Kit | Cognee | **Graphify v1.4 Plan** |
|---------|-----------------------------------|------------------------|--------|----------|--------|-------------------------|
| **Multi-model routing** | Role-based slots (chat/edit/autocomplete/apply/embed), user-configured globally | N/A | N/A | N/A | N/A | Role-based (primary/boilerplate/vision) + **AST-metric complexity classifier per file** (unique) |
| **MCP capability manifest** | Consumer of MCP — not a server publisher | N/A | Has its own non-MCP API | N/A | N/A | Full MCP 2025-11-25 compliance + `graphify.status()` + cost_class labels + registry listing |
| **Harness memory export** | N/A (each harness owns its memory) | Exports Letta memory blocks to own format | Honcho = the memory; exports to JSON | N/A | N/A | Canonical schema layer + CLAUDE.md / AGENTS.md / (future) SOUL.md; **inverse import** |
| **Obsidian thinking commands** | N/A | Chat sidebar over raw vault | N/A | N/A | N/A | Vault-scoped `/moc`, `/related`, `/orphan`, `/wayfind`, `/voice`, `/bridge`, `/drift-notes` — **profile-driven**, graph-grounded |
| **Async background enrichment** | N/A | Sleep-time compute via separate agent | Async derivers (queue + session-scoping) | N/A | memify background passes | Queue + `graphify derive` CLI; 4 built-ins (description / pattern / community / staleness); entry-point extensions |
| **Graph argumentation** | N/A | N/A | N/A | Full POPULATE→ABSTRACT→RUMBLE→KNIT; own ABSTRACT construction | N/A | SPAR-Kit protocol with **graph as pre-built ABSTRACT substrate** (unique); `[cite: node_id]` enforcement |
| **Conversational graph chat** | N/A | Chat sidebar over raw file content | N/A | N/A | Chat over graph nodes with embedding search | NL-to-MCP translation; **answers cite nodes** (vs. file chunks); suggest-follow-ups |
| **Focus-aware context** | Edit-mode uses selection/cursor | File-level focus memory block | N/A | N/A | N/A | File-level `get_focus_context` + session-carried focus; focus transfer to Phase 14/17 |

**The graphify-unique cells** (where no competitor matches):

1. **AST-metric complexity routing** (Phase 12) — no dev-tool routes by parse-tree complexity.
2. **Graph as SPAR-Kit ABSTRACT substrate** (Phase 16) — structural head-start no prose-based tool has.
3. **Profile-driven Obsidian commands** (Phase 14) — adapts to Ideaverse, Sefirot, custom frameworks via v1.0 profile system.
4. **Graph-grounded chat with citation enforcement** (Phase 17) — vector-search-based chat (Cognee) surfaces chunks; graphify surfaces nodes with verifiable IDs.
5. **Cross-harness neutrality** (Phase 13 + SEED-002) — Letta exports Letta format; graphify targets many formats canonically.
6. **Vault round-trip awareness** (inherited from v1.1, leveraged by Phase 14) — no competitor preserves user edits across re-runs with sentinel grammar.

These six cells define v1.4's competitive positioning. Marketing/docs should lead with them.

---

## Anti-Feature Summary (Actionable Do-Not-Build List)

Collected here for roadmapper reference. Each entry is one-line for roadmap decision speed.

- **Do NOT build learned routing in Phase 12** — threshold-based stays debuggable; no training data exists at v1.4 scale.
- **Do NOT build real-time rebuild in Phase 15** — contradicts delta.py's snapshot-boundary design; breaks v1.1 FRESH/STALE/GHOST semantics.
- **Do NOT build auto-apply argumentation in Phase 16** — advisory-only per SPAR-Kit anti-consensus ethos; auto-apply is the single worst failure mode.
- **Do NOT build fabricating chat in Phase 17** — cited-node enforcement is non-negotiable; uncited answers erode trust instantly.
- **Do NOT build cursor-level focus in Phase 18** — requires LSP integration; out of scope for Python CLI library.
- **Do NOT build proprietary manifest schema in Phase 13** — extend `server.json` via `_meta`; don't compete with MCP registry.
- **Do NOT build auto-write vault commands in Phase 14** — v1.1 `propose_vault_note + approve` is the trust boundary.
- **Do NOT build authentication in capability manifest** — MCP handles at transport layer; manifest declares auth class, doesn't implement.
- **Do NOT build derivers that mutate graph.json** — sidecar-only (`enrichments.json`); graph.json stays pipeline-owned.
- **Do NOT build ambient focus-capture via filesystem watch** — D-18 enforces explicit signals; watch.py is for code re-extraction only.
- **Do NOT duplicate Phase 11 commands verbatim in Phase 14** — distinct naming (`/trace` is code, `/trace-note` is vault); avoid confusion.
- **Do NOT build voice-mode impersonation without disclosure** — carried from Phase 11 `/ghost` anti-impersonation guard.
- **Do NOT build persistent focus across sessions** — focus is task-scoped; cross-session persistence creates confusion.
- **Do NOT build automatic deriver-invocation on MCP reads** — breaks MCP primitive cost model; agents can't budget lazy-computed reads.
- **Do NOT build consensus-forcing synthesis in Phase 16** — disagreement is the signal; `tensions_unresolved` is first-class output.

---

## Sources

### External (fetched, HIGH confidence)

- **MCP Specification 2025-11-25** (`modelcontextprotocol.io/specification`, `modelcontextprotocol.io/docs/concepts/architecture`) — capability negotiation, `initialize` handshake, `serverInfo`/`capabilities` declaration, tool discovery via `tools/list`, resources/prompts primitives, lifecycle management.
- **MCP Registry server.json spec** (`github.com/modelcontextprotocol/registry/.../generic-server-json.md`) — fields: `name` (reverse-DNS), `description`, `title`, `version`, `repository`, `websiteUrl`, `packages` (npm/pypi/nuget/oci/mcpb), `remotes`, `_meta` (publisher-provided under `io.modelcontextprotocol.registry/publisher-provided` namespace).
- **Honcho docs** (`github.com/plastic-labs/honcho`) — derivers produce representations, summaries, peer cards; triggered on message/session creation; race prevention via session-based queue processing with parallel cross-session derivers.
- **SPAR-Kit protocol** (`github.com/synthanai/spar-kit`) — POPULATE (distinct persona worldviews), ABSTRACT (shared cognitive map, +40% synthesis quality), RUMBLE (4/8/6 rounds by intensity), KNIT (moderator synthesis of tensions, not consensus). Output: actionable recommendations grounded in dialectical reasoning.
- **Letta-Obsidian README** (`github.com/letta-ai/letta-obsidian`) — chat sidebar, interactive memory blocks, file-change detection via size+mtime. Focus-mode specifics NOT public in README.

### External (MEDIUM confidence, docs blocked)

- **Letta sleep-time compute** (`docs.letta.com`, `letta.com/blog/sleep-time-compute`, `arxiv.org/abs/2504.13171`) — all returned by domain filter. Characterized from internal notes (`april-research-gap-analysis.md`, `repo-gap-analysis.md`) and cross-referenced against Honcho deriver pattern (similar shape).
- **Continue / Aider / Cursor routing specifics** (`docs.continue.dev`, `aider.chat`) — access blocked. Characterized from open-source `pyproject.toml` / README content + prior art on role-slot configuration that's well-established in the community.

### Internal (codebase + notes, HIGH confidence)

- `.planning/PROJECT.md` — v1.4 scope definition and Phase 12 pull-forward rationale
- `.planning/ROADMAP.md` — Phase 12–18 one-line descriptions with informed-by citations
- `.planning/seeds/SEED-002-harness-memory-export.md` — SEED activation trigger, canonical schema layer, inverse-import scope
- `.planning/milestones/v1.3-research/FEATURES.md` — tone, structure, competitor-analysis format (direct template)
- `.planning/notes/april-research-gap-analysis.md` — 12-document research corpus synthesizing ecosystem direction
- `.planning/notes/repo-gap-analysis.md` — 7-repo competitive analysis (Honcho, Letta, SPAR-Kit, Smolcluster, CPR, LLM Council, Letta-Obsidian) with strategic synthesis pointing to graph-as-ABSTRACT
- `.planning/notes/april-2026-v1.3-priorities.md` — Phase 12 deferral rationale, Phase 14 naming distinction
- `.planning/notes/agent-memory-research-gap-analysis.md` — exclusions (no vector search, no 4-tier memory consolidation)
- `graphify/serve.py` — existing 12+ MCP tools, capability surface, session scoping, 3-layer graph_query
- `graphify/commands/*.md` — 7 existing Phase 11 slash commands (context/trace/connect/drift/emerge/ghost/challenge) establishing the skill-file pattern and anti-fabrication discipline carried forward
- `graphify/extract.py` — LanguageConfig dispatch, tree-sitter parse layer (AST-metric source)
- `graphify/snapshot.py`, `graphify/delta.py` — v1.1 infrastructure consumed by Phase 15 staleness_refresh deriver
- `graphify/profile.py`, `graphify/templates.py`, `graphify/merge.py` — v1.0 infrastructure consumed by Phase 14

---
*Feature research for: graphify v1.4 — Agent Discoverability & Obsidian Workflows*
*Researched: 2026-04-17*
