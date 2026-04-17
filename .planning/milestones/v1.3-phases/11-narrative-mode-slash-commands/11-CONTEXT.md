# Phase 11: Narrative Mode as Interactive Slash Commands - Context

**Gathered:** 2026-04-17
**Status:** Ready for planning
**Mode:** `--auto` (single-pass; recommended defaults auto-selected — see DISCUSSION-LOG.md for trace)

<domain>
## Phase Boundary

Replace the originally-scoped `GRAPH_TOUR.md` static artifact with a suite of **MCP-backed slash commands** that turn graphify's knowledge graph into a live thinking partner. Each command ships as a `.claude/commands/*.md` skill file — a thin wrapper that invokes graphify's MCP server and lets Claude render narrative output from the tool response.

**In-scope (core 5, required):**
- `/context` — full graph-backed life-state summary (active god nodes, top communities, recent deltas) — SLASH-01
- `/trace <entity>` — entity evolution across graph snapshots (first-seen, modifications, current community, staleness history) — SLASH-02
- `/connect <topic-a> <topic-b>` — shortest surprising bridge paths between two topics — SLASH-03
- `/drift` — nodes whose community / centrality / edge density has trended consistently across recent runs — SLASH-04
- `/emerge` — newly-formed clusters detected by comparing current snapshot to previous (uses v1.1 delta machinery) — SLASH-05

**In-scope (stretch 2, budget-permitting):**
- `/ghost` — answer in the user's voice grounded in their graph contributions — SLASH-06
- `/challenge <belief>` — pressure-test a belief against supporting vs. contradicting graph evidence — SLASH-07

**Out-of-scope (belongs elsewhere):**
- Heterogeneous extraction routing (Phase 12, v1.4)
- New analysis algorithms (Phase 11 composes existing `analyze.py` + `delta.py` + `snapshot.py` primitives; doesn't invent new analytics)
- Obsidian plugin development or `.obsidian/graph.json` management (out of scope per PROJECT.md)
- Sibling thinking-command project (`/ghost`, `/challenge` may migrate there post-v1.3 if scope exceeds graphify proper)

</domain>

<decisions>
## Implementation Decisions

### Wrapper Shape & Invocation Contract

- **D-01:** Each `.claude/commands/*.md` file is a **Claude Code slash-command skill** (not a pure bash script). Contract: the `.md` contains a prompt that instructs Claude to (1) call the relevant MCP tool(s) against `graphify-out/graph.json`, (2) render a narrative response from the tool output. Matches existing graphify skill.md orchestration pattern — Claude reads tool output, authors markdown narrative. No shelling to `graphify` CLI from inside the command prompt.
- **D-02:** **Output format is Claude-authored markdown with embedded tables/lists** — not raw JSON and not static narrative. MCP tools return structured data (`{"summary": ..., "top_communities": [...], "recent_delta": {...}}`); Claude renders into a thinking-partner-grade paragraph+bullet output. Consistency via a short "rendering guidelines" section in each command file (tone, depth, call-to-action suggestions).
- **D-03:** **Argument parsing** lives in the command prompt itself. Claude parses `$ARGUMENTS` (Claude Code convention) — e.g., `/trace Transformer` → Claude sends `Transformer` as the `entity` param to the MCP tool. No separate argparse layer; Claude Code passes `$ARGUMENTS` as a string to the prompt.

### MCP Endpoint Gap Plan

- **D-04:** **Add new MCP tools to `graphify/serve.py` as needed; no new `graphify/` module.** Explicit ROADMAP directive: *"No new graphify/ module is required unless an MCP query is missing."* All net-new query surface lives alongside the existing 13 tools in `serve.py`. Research phase must produce an exact per-command endpoint map — which commands reuse existing tools as-is, which need composition wrappers, which need brand-new tools.
- **D-05:** **Preliminary endpoint gap analysis** (subject to research-phase validation — see Canonical Refs for primary sources):
  - `/context` → likely **new MCP tool** (e.g., `graph_summary` or `context_digest`) combining `god_nodes` + top communities by size + `graph_diff` against most recent previous snapshot. No existing single tool returns all three.
  - `/trace <entity>` → likely **new MCP tool** (e.g., `entity_trace`) that walks `graphify-out/snapshots/*.json` and reconstructs per-entity timeline (first-seen timestamp, community-id series, staleness series). Reuses `load_snapshot` + `classify_staleness` from v1.1.
  - `/connect <a> <b>` → **composes existing primitives**: `shortest_path` (existing MCP tool) + `surprising_connections` (analyze.py, not yet MCP-exposed). May need a thin composition tool `connect_topics` or render purely from two separate tool calls in the command prompt.
  - `/drift` → likely **new MCP tool** (e.g., `drift_nodes`) consuming last N snapshots and computing per-node trend vectors (Δcommunity, Δdegree, Δedge-density). N defaults to the configured snapshot retention cap (currently 10 per v1.1 `save_snapshot` cap).
  - `/emerge` → **new MCP tool** (e.g., `newly_formed_clusters`) using `graph_diff` between current and previous snapshot, filtered to communities that didn't exist before. v1.1 delta machinery covers the diff; this tool adds the cluster-level framing.
- **D-06:** **Entity-label resolution**: `/trace` accepts label-first, fuzzy-matched, falling back to exact node ID. Reuses `_find_node(G, label)` from `serve.py:734`. If multiple matches, MCP tool returns a disambiguation list; command prompt asks the user to re-invoke with a specific ID.
- **D-07:** **Respect Phase 10's alias redirect contract** — any new MCP tool that accepts a node identifier must transparently handle `resolved_from_alias` / `merged_from` mappings established in Phase 10 (D-16). Entity queries for pre-dedup names still resolve to their canonical node with a visible `resolved_from_alias` meta field.

### Layered Response Contract (inherited from Phase 9.2)

- **D-08:** **All new MCP tools MUST emit Phase-9.2-compatible hybrid responses** — `text_body` + `SENTINEL('\n---GRAPHIFY-META---\n')` + `json(meta)` with a `status` field. Accepted status values include `ok`, `no_data`, `insufficient_history`, plus any Phase-9.2 codes (`frontiers_disjoint`, `budget_exhausted`) when the underlying query applies. Keeps agent clients consuming the same envelope.
- **D-09:** **Token budget parameter**: every new MCP tool accepts `budget: int` (Phase 9.2 pattern) and returns a 3-layer response when relevant — Layer 1 compact summary (always ≤budget), Layer 2 medium detail, Layer 3 full trace. For /context and /drift this means a top-N summary first; `/trace` and `/emerge` Layer 2/3 surface full timelines. Default budget is Phase-9.2's standard (500 tokens).

### Graceful Degradation

- **D-10:** **Missing graph**: any command invoked when `graphify-out/graph.json` does not exist returns a status `no_graph` with a human-readable hint: `"No graph found at graphify-out/graph.json. Run /graphify to build one, then re-invoke this command."` The command prompt renders this hint verbatim, no Claude embellishment.
- **D-11:** **Insufficient snapshot history**: `/trace`, `/drift`, `/emerge` require ≥2 snapshots. Status `insufficient_history` when fewer exist, with a `snapshots_available: N` meta field. Command prompt explains to the user how to accumulate history (run `/graphify` multiple times; snapshots auto-save per v1.1).
- **D-12:** **Ambiguous entity**: `/trace` with a label that fuzzy-matches multiple nodes returns status `ambiguous_entity` + a list of candidate `{id, label, source_file}` tuples. Command prompt lists candidates and prompts re-invoke.

### Installation & Distribution

- **D-13:** **Slash commands ship via `graphify install`** — extend `_PLATFORM_CONFIG` in `__main__.py` so each of the 7 existing platforms (Claude Code, Codex, OpenCode, OpenClaw, Factory Droid, Trae, Trae CN) installs the matching `.claude/commands/*.md` (or equivalent platform path) alongside the main skill file. Bundled by default.
- **D-14:** **`--no-commands` opt-out flag** on `graphify install` for users who only want the skill file. Same flag on `graphify uninstall` removes them. Installation is idempotent (re-run upgrades command files in place).
- **D-15:** **Command file location pattern**: each platform gets its own subfolder in `graphify/` (e.g., `graphify/commands/context.md`, `graphify/commands/trace.md`) packaged via `pyproject.toml`. Per-platform variants only if a platform's command format diverges meaningfully from Claude Code's `.md` prompt format. Start with Claude-Code-first; other platforms inherit until divergence forces a variant.
- **D-16:** **Discoverability**: add a one-line section to each platform's installed skill file ("Available slash commands: /context /trace /connect /drift /emerge") so users who installed only via `graphify install` see what's available. Does not add new dependencies.

### Scope Policing

- **D-17:** **Core 5 first, stretch 2 conditional** — `/ghost` and `/challenge` (SLASH-06, SLASH-07) only ship in Phase 11 if research + planning come in under ~60% of estimated budget. Otherwise deferred to a v1.4 sibling skill or follow-up phase. Rationale: ROADMAP marks them stretch and permits migration out of graphify.
- **D-18:** **No new graph algorithms** — Phase 11 is plumbing. If a command needs an algorithm not yet in `analyze.py` / `delta.py` / `snapshot.py`, the algorithm itself is a separate plan (or phase), not a slash-command task. Keeps the "thin wrapper" promise honest.
- **D-19:** **No UI framework** — these are markdown prompts rendered in Claude Code's chat surface. No Textual, no Rich, no web UI.

### Claude's Discretion

- Exact MCP tool names (e.g., `graph_summary` vs `context_digest`) — final names chosen during planning to harmonize with existing 13-tool naming (verb_object vs object_verb).
- Exact prompt template wording inside each `.md` command file — Claude authors the default; user-facing tone matches the existing `graphify/skill.md` voice.
- Internal representation of snapshot timelines returned by `entity_trace` (list of snapshot records vs. compressed run-length encoding) — pick whichever serializes clearest under 500-token Layer 1 budget.
- Whether `connect_topics` ships as a standalone composition MCP tool or the `/connect` command prompt chains two existing tool calls. Decide during planning based on code-reuse across future commands.
- Fallback when `graphify-out/snapshots/` exists but no `GRAPH_DELTA.md` — regenerate on demand (via `analyze.py:graph_diff`) or report `stale_delta`.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Phase Scope & Motivation
- `.planning/ROADMAP.md` §"v1.3 Intelligent Analysis Continuation" → Phase 11 section (lines 143–162) — full goal statement, requirements list, and 6 success criteria
- `.planning/REQUIREMENTS.md` §"Human Thinking Partner via Slash Commands" (lines 26–36) — SLASH-01..07 full requirement text
- `.planning/PROJECT.md` §"Current Milestone: v1.3 Intelligent Analysis Continuation" — priority ordering and motivation for interactive slash commands over static `GRAPH_TOUR.md`
- `.planning/notes/april-2026-v1.3-priorities.md` §"Phase 11" — original rationale for the static-to-interactive pivot

### Prior Phase Decisions (Carry Forward)
- `.planning/phases/09.2-progressive-graph-retrieval/09.2-CONTEXT.md` — D-02 hybrid response envelope (`text_body` + SENTINEL + json meta), status codes, 3-layer progressive disclosure, `budget` parameter. **All new MCP tools in Phase 11 MUST conform.**
- `.planning/phases/10-cross-file-semantic-extraction/10-CONTEXT.md` — D-16 alias redirect contract. Any new MCP tool accepting node identifiers MUST route merged-away IDs to canonical nodes with `resolved_from_alias` meta.
- `.planning/phases/10-cross-file-semantic-extraction/10-VERIFICATION.md` — confirms Phase 10 alias layer shipped and is verifiable in `serve.py`.

### Existing Code Phase 11 Extends or Wraps
- `graphify/serve.py` — MCP server, 13 existing tools. **The file Phase 11 primarily modifies.** Key existing tools: `query_graph`, `get_node`, `get_neighbors`, `get_community`, `god_nodes`, `graph_stats`, `shortest_path`, `get_annotations`, `get_agent_edges`. See lines 1050–1200 for the tool registration block.
- `graphify/analyze.py` — `god_nodes()`, `surprising_connections()`, `graph_diff()`, `suggest_questions()`. Source material for `/context`, `/connect`, `/emerge` composition tools.
- `graphify/delta.py` — `graph_diff()`, `classify_staleness()`. Source material for `/emerge` and `/trace`.
- `graphify/snapshot.py` (via `graphify/__init__.py` lazy re-exports: `save_snapshot`, `load_snapshot`, `list_snapshots`, `snapshots_dir`, `auto_snapshot_and_delta`). Source material for `/trace`, `/drift`, `/emerge`.
- `graphify/__main__.py` — `_PLATFORM_CONFIG` dict (lines ~100+) and the `install`/`uninstall` code path. Phase 11 extends it to ship command files. Existing snapshot CLI lives at lines 1257–1370.
- `graphify/skill.md` — canonical skill orchestration prompt; voice/tone reference for new command prompts.

### Installation Reference (platform variants)
- `graphify/skill.md` + 8 sibling variants (`skill-codex.md`, `skill-opencode.md`, `skill-aider.md`, `skill-claw.md`, `skill-copilot.md`, `skill-droid.md`, `skill-trae.md`, `skill-windows.md`) — existing per-platform skill file pattern Phase 11 mirrors for command files.

### Security
- `graphify/security.py` — label sanitization applies to any user-supplied argument echoed into a command response (e.g., `/trace <entity>` rendering the entity name back). Mandatory per SECURITY.md.

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- **`serve.py` tool-registration pattern** (`types.Tool(name=..., description=..., inputSchema=...)` at lines ~1054–1200) — Phase 11 extends this block with any net-new MCP tools. Same file, same pattern.
- **`_load_graph()`** (serve.py:416) and **`_find_node()`** (serve.py:734) — reused by entity-resolution in `/trace`.
- **`_record_traversal()`** (serve.py:139) and `_edge_weight()` (serve.py:218) — Phase 9.1 telemetry, already recording per-edge usage. `/connect` and `/context` inherit this instrumentation for free.
- **`_subgraph_to_text()`** (serve.py:664) — existing layered renderer; any new MCP tool returning subgraph data should reuse it for consistency.
- **`graphify/analyze.py` `surprising_connections`** — ready-made scoring function for `/connect`. Not MCP-exposed yet; Phase 11 adds the exposure.
- **Snapshot storage** in `graphify-out/snapshots/` — v1.1 already maintains 10 historical snapshots by default. `/trace`, `/drift`, `/emerge` consume these directly via `load_snapshot`.

### Established Patterns
- **Hybrid response envelope** (Phase 9.2) — `text_body` + `\n---GRAPHIFY-META---\n` + `json(meta)`. All new MCP tools follow it.
- **3-layer progressive disclosure** (Phase 9.2) — `budget` parameter, Layer 1 summary, Layer 2/3 on follow-up. New tools inherit.
- **Status-coded responses** (Phase 9.2) — tools return a `status` field with a small enum; clients branch on it. Phase 11 adds `no_graph`, `insufficient_history`, `ambiguous_entity`, `no_data` where relevant.
- **Alias redirect** (Phase 10 D-16) — `resolved_from_alias` in meta when an ID maps via dedup. Phase 11 new tools MUST honor this for any identifier input.
- **Lazy module loading in `graphify/__init__.py`** — new `snapshot`/`delta` re-exports follow same pattern. If Phase 11 adds composition helpers they go here too (unlikely; thin wrappers should live in `serve.py`).
- **Platform variant skill files** — 8 platform variants already exist. Command files follow the same duplication-with-variance pattern only where platforms diverge.

### Integration Points
- **MCP server registration** (`serve.py:serve()`, line 1026): net-new tools register inside this function.
- **`__main__.py` install/uninstall** (lines ~500–700 region): extend `_PLATFORM_CONFIG` entries with `commands_dir` + `commands_files` keys.
- **`pyproject.toml` `tool.setuptools.package-data`**: add `graphify/commands/*.md` so command files package into the wheel.
- **`tests/`** — one test file per new module (`tests/test_commands.py` or extend `tests/test_serve.py` for MCP-tool additions; `tests/test_install.py` for install-path changes).
- **`SECURITY.md`** — if any new MCP tool echoes user input, extend the threat model section.

### Creative Options
- Aggregating `god_nodes` + top communities + delta for `/context` could live as a one-shot `graph_summary` MCP tool OR as a Claude-orchestrated sequence of three existing tool calls. The former is cleaner for non-Claude agents; the latter ships faster. Recommend one-shot composition tool for future-proofing.
- `/trace` could back its timeline with either snapshots (current v1.1 storage) or an always-on JSONL event log (nicer granularity, new infra). Snapshots are the boring-but-shipped choice.

</code_context>

<specifics>
## Specific Ideas

- **Thinking-partner voice** — per PROJECT.md milestone theme: commands should read as a partner pressing on the user's thinking, not a pretty-printed report. `/drift` suggesting "you've been circling X — want to look at Y?" beats a bulleted change list.
- **Budget discipline** — Phase 9.2 set the tone: every response Layer-1-fits-in-500-tokens by default. Phase 11 must not reintroduce unbounded responses.
- **Snapshot-as-memory frame** — `/trace`, `/drift`, `/emerge` all rely on the snapshot cadence. Messaging in command prompts should hint "you have N snapshots; richer insight with more runs." Encourages habitual re-runs.

</specifics>

<deferred>
## Deferred Ideas

- **Sibling thinking-skill project** — if `/ghost` and `/challenge` exceed graphify's scope during planning, they migrate to a companion skill. Keeps graphify a graph-only tool. Revisit after Phase 11 planning estimate.
- **Always-on JSONL event log** for finer-grained `/trace` timelines (vs. coarser snapshot-bounded timelines). Adds infra — not Phase 11 scope. Capture as v1.4+ seed.
- **Command file platform variants beyond Claude Code** — only materialize if a platform meaningfully diverges. Until evidence of divergence, single source of truth keeps maintenance cheap.
- **Slash commands inside Obsidian vault** (via plugin or codeblock embedding) — out of scope per PROJECT.md "no plugin development." Revisit if `/ghost` etc. move to a vault-side sibling skill.

</deferred>

---

*Phase: 11-narrative-mode-slash-commands*
*Context gathered: 2026-04-17 (--auto mode, single-pass, recommended-default selection)*
