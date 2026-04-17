# Architecture Research — graphify v1.4

**Domain:** Python CLI library + MCP server + multi-platform skill bundles for knowledge-graph over source/docs
**Researched:** 2026-04-17
**Confidence:** HIGH (findings grounded in direct reads of `__main__.py`, `serve.py`, `watch.py`, `extract.py`, `cache.py`, `manifest.py` and PROJECT.md / ROADMAP.md)

## Existing architecture recap (what v1.4 extends)

### Layered view

```
┌────────────────────────────────────────────────────────────────────┐
│  Skill layer  (graphify/skill*.md — 7 platform variants)           │
│  = pipeline driver (D-73).  CLI is utilities; skill calls library. │
├────────────────────────────────────────────────────────────────────┤
│  Agent surface                                                     │
│  ┌──────────────────────┐  ┌──────────────────────────────────┐    │
│  │ MCP stdio server     │  │ .claude/commands/*.md slash cmds │    │
│  │ graphify/serve.py    │  │ graphify/commands/*.md           │    │
│  │ 18 tools, D-02 env.  │  │ (context/trace/connect/drift/    │    │
│  │ D-16 alias redirect  │  │  emerge/ghost/challenge)         │    │
│  └──────────┬───────────┘  └──────────┬───────────────────────┘    │
├─────────────┼─────────────────────────┼──────────────────────────── │
│             └──────────┬──────────────┘                             │
│  Pipeline (pure funcs, plain dicts / nx.Graph)                      │
│  detect → extract → build → cluster → analyze → report → export     │
│  detect.py  extract.py  build.py  cluster.py  analyze.py  report.py │
│             │            │                                          │
│             ▼            ▼                                          │
│  cache.py (SHA-256 per-file, AST + semantic)                        │
│  validate.py (schema gate before build)                             │
│  security.py (URL/path/label sanitization for ALL external inputs)  │
├─────────────────────────────────────────────────────────────────────┤
│  Post-pipeline modules                                              │
│  wiki.py · dedup.py · batch.py · merge.py (Obsidian) ·              │
│  snapshot.py · delta.py · profile.py · templates.py · mapping.py    │
├─────────────────────────────────────────────────────────────────────┤
│  Sidecars under graphify-out/ (all JSON, atomic write via .tmp+rename)│
│  graph.json · telemetry.json · agent-edges.json · annotations.jsonl ·│
│  proposals/ · snapshots/ · vault-manifest.json · dedup_report.json · │
│  cache/ · needs_update (flag)                                       │
└─────────────────────────────────────────────────────────────────────┘
```

### Integration conventions (must-honor for v1.4)

- **D-02 MCP envelope:** every tool returns `text_body + "\n---GRAPHIFY-META---\n" + json.dumps(meta)`. Constant in `graphify/serve.py:744` as `QUERY_GRAPH_META_SENTINEL`. All new MCP tools MUST use it.
- **D-16 alias redirect:** `serve.py:91 _load_dedup_report()` produces `_alias_map: dict[str,str]`, then every `_run_*` helper uses a local `_resolve_alias(node_id)` closure. New tools that accept `node_id`/`label` MUST thread through alias resolution.
- **D-18 compose, don't plumb:** new MCP tools reuse `_bfs`, `_dfs`, `_bidirectional_bfs`, `_score_nodes`, `_subgraph_to_text`, `_estimate_cardinality`, `_load_graph`. No new `graphify/*.py` whose sole purpose is wiring serve helpers.
- **D-73 skill drives, CLI doesn't:** multi-step pipeline work goes into `skill.md`, not into a Python CLI verb. CLI is discrete utilities (`install`, `query`, `approve`, `benchmark`, `save-result`, per `__main__.py:1580–1770`).
- **Tool dispatch:** in `serve.py:2147` the `_handlers` dict maps tool name → `_tool_<name>` closure; new tools register by (1) appending a `types.Tool(...)` in `list_tools()` (`serve.py:1687`) and (2) adding a handler entry. Handlers delegate to a top-level pure `_run_<name>(G, ..., arguments)` helper so the logic is unit-testable without stdio.
- **Multi-platform install:** `_PLATFORM_CONFIG` in `__main__.py:49–130` — each platform has `skill_file` and optional `commands_src_dir`/`commands_dst`. Commands install via `_install_commands()` (`__main__.py:133`) which hardcodes filename whitelist in `_uninstall_commands()` (`__main__.py:153`). Adding new commands requires editing that whitelist.
- **Cache key shape:** `cache.py:20 file_hash()` = SHA-256 of file bytes. `save_cached`/`load_cached` are per-path, path-relative to `root`. There is NO model-identity component in cache keys today — Phase 12 must extend the key.

## Feature-by-feature integration plans

### Phase 12 — Heterogeneous Extraction Routing

**Router location:** new `graphify/routing.py` (~150–250 LOC). NOT inside `extract.py` (already 2817 LOC, overloaded).

- Responsibility: given a list of `Path`, compute a **complexity class** (`trivial` / `simple` / `complex`) using AST metrics (cyclomatic complexity, nesting depth, import count) and return a **work plan**: `list[{path, class, model, endpoint}]`.
- **Integration points:**
  - `graphify/extract.py:2652 extract()` — new keyword arg `router: Router | None = None`. When provided, per-file `extractor` call is replaced by a dispatch through the router that can select either (a) the existing tree-sitter extractor or (b) a downgraded LLM-free fast path for trivial files. Parallelism sits in `extract()`, not in `routing.py` (router is pure classifier).
  - `graphify/cache.py:20 file_hash()` — add an optional `model_id: str = ""` parameter so cache key becomes `SHA256(bytes) + ":" + model_id`. Older callers keep passing no model_id → backward compatible. Phase 12 callers pass the chosen model so two different routing decisions don't cross-contaminate the cache. Preserve determinism: tree-sitter extraction returns the same AST nodes regardless of route choice, so cache hits remain valid across runs when routing is stable.
  - `graphify/skill.md` — semantic-extraction pipeline step reads `routing.plan(files)` and shards LLM calls across endpoints.
- **Parallelism:** use `concurrent.futures.ThreadPoolExecutor` (not multiprocessing — tree-sitter parsers hold C state that doesn't fork-clone cleanly on macOS). Bound worker pool size (default 4) and expose via `GRAPHIFY_EXTRACT_WORKERS` env var. Deterministic result order by sorting per-file results by `(path, node.id)` before `build_from_json()`.
- **Determinism guarantee:** tree-sitter ASTs are input-deterministic, so parallel scheduling does not change node IDs. The only non-determinism is dict ordering in `all_nodes`/`all_edges` — solved by the post-extraction sort. Document this in `.planning/milestones/v1.4-phases/12-CONTEXT.md`.
- **New sidecar:** `graphify-out/routing.json` = `{ file → {class, model, tokens_used, ms} }`. Written by `extract()` when router is active; consumed by Phase 15 enrichment (skip already-expensive files) and by `benchmark.py` (routing cost/quality telemetry).
- **Flags D-73:** ✓ — router is a pure helper, pipeline driver stays in skill. No new CLI verb.

### Phase 13 — Agent Capability Manifest (+ SEED-002 Harness Memory Export)

**Static + runtime, not either/or.**

- **New module:** `graphify/capability.py` (~200 LOC). `graphify/manifest.py` stays as-is (it's just a back-compat shim over `detect.save_manifest`/`load_manifest` and renaming it invites breakage).
- **Static generator:** `capability.build_manifest() -> dict` produces a schema-shaped dict describing MCP tools + CLI surface + sidecar formats + skill trigger, pulled by introspection from `serve.py`'s `list_tools()` (requires a small refactor: lift the tool-list construction into a top-level `CAPABILITY_TOOLS` list that both `list_tools()` and `capability.build_manifest()` read).
- **Persistence:** manifest written to **package resource** `graphify/capability.json` at build-time (via `setup.py` build hook) AND emitted to **`graphify-out/manifest.json`** on every full pipeline run so it stays in sync with the currently-installed version.
- **Runtime MCP tool:** new `_tool_capability_describe(arguments)` in `serve.py`. Returns the static manifest + live state (graph stats, alias map size, sidecar freshness). Registered in `_handlers` and `list_tools()`.
- **Discovery registration:**
  - Skill frontmatter (`skill.md`) gets a new `capability_manifest: graphify-out/manifest.json` line — other skills can read this to discover graphify's surface.
  - `pyproject.toml` → new entry point `graphify.capability = "graphify.capability:cli"` for `graphify capability` subcommand (dump JSON to stdout).
- **SEED-002 Harness Memory Export:** new module `graphify/harness_export.py` (NOT bundled into `capability.py` — different concern).
  - **Direction:** bidirectional. The primary direction is **export** (graph.json + annotations + agent-edges → SOUL/HEARTBEAT/USER harness files), but also accept **import** (read existing `.claude/CLAUDE.md` USER block → seed `annotations.jsonl` with peer_id="harness:user"). Keeps harness the source of truth for user prefs while graphify seeds the graph side.
  - **Schema config:** `graphify/harness_schemas/*.yaml` (new data dir, packaged via `[tool.setuptools.package-data]`). One schema per harness target: `claude.yaml`, `codex.yaml`, `letta.yaml`, `honcho.yaml`. Each declares `soul: {...}`, `heartbeat: {...}`, `user: {...}` blocks with placeholder lists (`{{ god_nodes }}`, `{{ recent_deltas }}`, etc.) — reuses Phase 2 `string.Template.safe_substitute` pattern from `templates.py` to keep "no Jinja2" constraint intact.
  - **CLI:** `graphify harness export <target>` and `graphify harness import <path>`. Both go in `__main__.py` as new `elif cmd == "harness":` branches (mirrors the `hook`/`approve` pattern).
  - **New sidecar:** `graphify-out/harness/<target>-SOUL.md`, `<target>-HEARTBEAT.md`, `<target>-USER.md`.
- **Does Phase 13 manifest need Phase-14/17 tools to exist?** No — the manifest is descriptive, not declarative. It can describe only the tools present at the version that generates it. Adding Phase-14/17 tools later is additive; the manifest regenerates with each run.

### Phase 14 — Obsidian Thinking Commands

- **Where they live:** keep `graphify/commands/` as the single source of truth; DON'T split into a subdirectory. Instead, add YAML frontmatter to each command file and a **target filter** in `_PLATFORM_CONFIG`.
  - Frontmatter shape (example for a new `/moc-expand` command):
    ```
    ---
    target: obsidian
    requires: vault-manifest.json
    mcp_tools: [graph_summary, get_community]
    ---
    ```
  - `_install_commands()` at `__main__.py:133` gains a `target_filter` read: commands with `target: code` install on all platforms; commands with `target: obsidian` install only when the platform's `cfg["obsidian_commands"] = True` is set. Claude Code (the only `commands_enabled=True` platform today) gets both sets by default; a new install flag `--no-obsidian-commands` can suppress.
- **The whitelist in `_uninstall_commands()` (`__main__.py:153`) is a maintenance hazard** — migrate it away from a hardcoded tuple to reading `graphify/commands/*.md` at runtime and keying by filename. Existing Phase-11 commands remain installed; the migration is transparent. Do this refactor in Plan 00 of Phase 14.
- **New commands** (Obsidian-scoped, reuse existing MCP tools — D-18): `/moc-expand`, `/vault-health`, `/note-provenance`, `/round-trip-check`. All read `vault-manifest.json` and call existing tools (`get_community`, `graph_summary`, `get_node` w/ provenance) — no new MCP tools, no new Python modules.
- **Multi-platform install:** only Claude Code + Windows today install commands. For non-Claude-Code harnesses (Codex, OpenCode, etc.), skill files get inline command descriptions instead — follow the existing pattern where each platform has its own skill variant.

### Phase 15 — Async Background Enrichment

- **Deriver runner location:** new `graphify/enrich.py` (~250 LOC) as a library module + a CLI subcommand **`graphify enrich`** in `__main__.py`. Do NOT fold into `watch.py`.
  - Reason: `watch.py` is filesystem-change-driven (debounced rebuild). Enrichment runs on a cadence or on demand — different trigger shape. Overloading `watch` muddles the contract (`watch --enrich` would have two lifecycles in one process).
  - Reason: the skill can invoke `graphify enrich` directly between full rebuilds (D-73 honored — skill is driver).
- **Subcommand shape:** `graphify enrich [--pass description|patterns|staleness|summaries] [--budget TOKENS] [--graph PATH]`. Default runs all four passes.
- **New sidecar:** `graphify-out/enrichment.json`. Structure:
  ```
  {
    "descriptions": { node_id: { "text": str, "confidence": str, "source_pass": "description", "generated_at": iso } },
    "patterns": [ { "pattern_id": str, "nodes": [...], "detected_at": iso } ],
    "staleness_overrides": { node_id: "FRESH|STALE|GHOST" },
    "community_summaries": { community_id: { "summary": str, "generated_at": iso } }
  }
  ```
- **Graph.json — DO NOT MUTATE.** Enrichment writes only to `enrichment.json`. This preserves snapshot integrity (Phase 6 delta machinery diffs graph.json and would thrash on every derivation). A read-side merge in `serve.py`'s `_load_graph` (optional overlay) is introduced instead: `_load_enrichment(out_dir) -> dict` and `_overlay_enrichment(G, enrichment)` that mutates the in-memory copy only.
- **Trigger points:** (a) `graphify enrich` manual, (b) post-build hook (`hooks.py` already has git post-commit registration — add a `--enrich` flag that schedules `graphify enrich` after `graphify watch` rebuilds), (c) skill invocation.
- **Concurrency with serve:** enrichment writes atomically via `.tmp` + `os.replace` (same pattern as `_save_telemetry`, `_save_agent_edges`). Serve's `_reload_if_stale()` pattern is already graph.json-mtime-driven; add parallel mtime watch for `enrichment.json` in the same function.
- **Phase dependency on 12:** enrichment benefits from `routing.json` (skip description-generation on already-LLM-extracted files), but can run without it. Soft dependency.

### Phase 16 — Graph Argumentation Mode

- **Substrate module:** new `graphify/argue.py` (~300 LOC). NOT an extension of `analyze.py`.
  - Reason: `analyze.py` is god-nodes + surprising-connections + suggest_questions — graph-metric territory, no LLM orchestration. The autoreason tournament logic actually lives in **`skill.md:1324–1546`**, not in `analyze.py` (the module only provides `render_analysis_context` as a context-builder). Phase 16 argumentation is structurally parallel: module provides **subgraph selection + perspective seeding**, skill drives the debate.
- **Input shape:** `argue.populate(G, topic: str, *, scope: "topic"|"subgraph"|"community", budget: int) -> ArgumentPackage`. Accepts either a free-text topic (falls back to `_score_nodes` + BFS-expansion, same shape as `query_graph`) OR an explicit subgraph selection (list of node_ids). Dual-mode is important because "Should we refactor auth?" is topic-driven, but "argue about this community" is selection-driven. Don't force one shape.
- **Output:** `ArgumentPackage` dataclass with `subgraph`, `perspectives: list[PerspectiveSeed]`, `evidence: list[NodeCitation]`. Skill consumes it, runs the debate, writes result to `GRAPH_ARGUMENT.md` (parallels Phase 9's `GRAPH_ANALYSIS.md`).
- **New MCP tool:** `argue_topic(topic, scope, budget)` — thin wrapper over `argue.populate()` returning the ArgumentPackage as JSON-in-meta. Skill then orchestrates the personas (LLM calls happen in the skill, not in Python — D-73).
- **Reuse:** pulls `_score_nodes`, `_bfs`, `_subgraph_to_text` from serve via module import (D-18).
- **Dependency:** soft on Phase 9/9.1 tournament machinery — reuses the "no finding as first-class Borda option" pattern from `analyze.py:render_analysis_context`. Argumentation adds structured disagreement on top of that lens framework.

### Phase 17 — Conversational Graph Chat

- **Tool, not standalone skill.** Add MCP tool `chat(query: str, session_id: str | None)` to `serve.py`. Reasons:
  - Skill-internal invocation has no natural home for session state. MCP `chat` can piggyback on `_session_id` already initialized at `serve.py:1683`.
  - An `_run_chat()` helper keeps the D-18 compose rule: translate question → `_score_nodes` → (BFS | community lookup | god_nodes | shortest_path) → `_subgraph_to_text` → narrative response.
- **Prompt templating:** skill.md owns prompt templates (D-73); `chat` MCP tool returns a **structured packet** in meta: `{"question": str, "traversal": {"strategy": str, "seeds": [...], "visited": [...]}, "citations": [{node_id, label, source_file}], "narrative_hint": str}`. The agent/skill renders the human-facing narrative. This keeps `serve.py` free of LLM calls (it has never made one, consistent with existing design).
- **Citations in meta envelope:** every claim the chat response references is paired with `{"node_id": ..., "label": ..., "source_file": ...}` in `meta["citations"]`. Downstream UIs (Obsidian panel from Phase 18) render these as clickable wikilinks.
- **No standalone skill file.** The existing `graphify/skill.md` gains a `## Conversational mode` section documenting the round-trip. This is consistent with Phase 11, where slash commands are `.claude/commands/*.md` stubs that call MCP tools — new `/ask` or `/chat` command file in `graphify/commands/` (follows Phase 14 target-filter scheme, `target: both`).

### Phase 18 — Focus-Aware Graph Context

- **Who reports focus:** **agent via MCP tool argument.** No filesystem side-channel.
  - Rationale: the v1.1 MCP surface design is stateless-per-call; a file-watcher side-channel would introduce a second state path that contradicts that. Also, file-watchers in the MCP server process add cross-platform portability burden (Windows + macOS semantics diverge).
- **Tool shape:** `get_focus_context(focus_hint, budget)` where `focus_hint` is a dict, not a bare path. Shape:
  ```
  {
    "file_path": "graphify/extract.py",              # required
    "function_name": "extract",                       # optional
    "line": 2652,                                     # optional (for future line-level mapping)
    "neighborhood_depth": 1,                          # optional, default 2
    "include_community": true                         # optional
  }
  ```
  This is extensible — `line`/`function_name` land now as metadata but can drive tighter neighborhoods later. Bare `file_path` arg would need breaking change to extend.
- **New `_run_focus_context()` in serve.py:** resolve file → matching node ids (currently `source_file` is `str | list[str]` per Phase 10 schema change — must handle both); BFS at specified depth; emit subgraph text + community summary + citation list.
- **New sidecar:** none. Focus is per-query, not persisted.
- **Downstream Obsidian integration:** Phase 14 `/note-provenance` command can invoke `get_focus_context` for the active-note's `source_file` frontmatter — a concrete consumer, validates the tool shape.

### SEED-002 summary (scoped inside Phase 13 above)

Already covered in Phase 13. Key decisions: new module `graphify/harness_export.py`, new data dir `graphify/harness_schemas/*.yaml`, new CLI `graphify harness [export|import] <target>`, new sidecar `graphify-out/harness/`.

## Build-order dependency graph

```
             ┌──────────────────────┐
             │ Phase 12 Routing      │◄─── standalone; only touches extract.py + cache.py
             │ (graphify/routing.py) │
             └────────────┬──────────┘
                          │ (soft: routing.json feeds enrichment skip-list)
                          ▼
             ┌──────────────────────┐      ┌─────────────────────────┐
             │ Phase 15 Enrichment   │      │ Phase 18 Focus Context  │
             │ (graphify/enrich.py)  │      │ (serve.py tool only)    │
             └────────────┬──────────┘      └──────────┬──────────────┘
                          │ (enrichment.json readable by chat)     │
                          ▼                                        │
             ┌──────────────────────┐                              │
             │ Phase 17 Chat         │◄─────────────────────────────┘
             │ (serve.py tool)       │       (chat cites focus results when agent threads them)
             └────────────┬──────────┘
                          │ (chat tool is one more entry in the manifest)
                          ▼
┌─────────────────────────────────┐     ┌──────────────────────────────┐
│ Phase 14 Obsidian Commands      │     │ Phase 13 Capability Manifest │
│ (graphify/commands/, target:    │◄────┤ (graphify/capability.py +    │
│  obsidian frontmatter)          │     │  harness_export.py)          │
└────────────┬────────────────────┘     └──────────┬───────────────────┘
             │ (commands register themselves in manifest)              │
             ▼                                                         │
             [phase 14 commands appear in next regeneration of manifest]
                                                                       │
┌─────────────────────────────────┐                                    │
│ Phase 16 Argumentation          │◄───────────────────────────────────┘
│ (graphify/argue.py + skill.md)  │  (argumentation is also surfaced in manifest)
└─────────────────────────────────┘
```

### Suggested linear order with rationale

1. **Phase 12 first.** Zero dependency on other v1.4 phases, and it gates enrichment's cost model. Completing 12 first means Phase 15 descriptions can be routed smartly and cache keys don't need post-hoc migration. Risk: schema change to `cache.py` is the most invasive piece of v1.4 — do it early so downstream phases inherit the stable key format.
2. **Phase 18 in parallel with 12.** No code overlap (touches only `serve.py`). Small, testable, unblocks Phase 14's `/note-provenance`.
3. **Phase 15.** Depends on Phase 12's `routing.json` softly — builds on stable cache + extraction format. Delivers `enrichment.json` sidecar that Phase 17 chat can read.
4. **Phase 17.** Reuses Phase 18's focus-context pattern (agent can pass focus-hint in chat args) and Phase 15's enrichment overlays (for richer citations).
5. **Phase 16.** Leans on Phase 9's tournament architecture (already shipped) and Phase 17's citation-in-meta pattern. Deferred until chat exists so argumentation UX shares a citation format.
6. **Phase 14.** Needs the commands-whitelist refactor (Plan 00) before new commands can be added cleanly. Then emits `/moc-expand` etc. Depends on Phase 18 (for `/note-provenance`) and benefits from Phase 17 chat being queryable.
7. **Phase 13 last.** Manifest is descriptive; run it last so it captures the full surface in one pass. Earlier drafts are possible but wasted work if the surface is still shifting. SEED-002 harness export bundles with Phase 13 because both are "advertise graphify to external systems".

**Alternative:** Phase 13 could ship in two waves — wave A (manifest generator + runtime tool, empty of new tools) shipped after Phase 12 to establish the plumbing; wave B (full manifest with Phases 14–18 entries) at the tail. This adds integration-cost but reduces risk of shipping a Phase-13 manifest that's immediately stale.

## Sidecar / graph.json schema additions

| Sidecar | Phase | Writer | Consumer | Atomicity |
|---------|-------|--------|----------|-----------|
| `graphify-out/routing.json` | 12 | `extract()` via `routing.py` | `enrich.py`, `benchmark.py` | `.tmp` + `os.replace` |
| `graphify-out/enrichment.json` | 15 | `enrich.py` | `serve.py` (overlay), Phase 17 chat, Phase 14 `/vault-health` | `.tmp` + `os.replace` |
| `graphify-out/manifest.json` | 13 | `capability.py` (build + run) | external agents, Phase 17 chat, skill frontmatter | `.tmp` + `os.replace` |
| `graphify-out/harness/<target>-{SOUL,HEARTBEAT,USER}.md` | 13/SEED-002 | `harness_export.py` | external harnesses | direct write (markdown, not structured) |
| `graphify-out/GRAPH_ARGUMENT.md` | 16 | skill.md (driver) using `argue.py` package | humans, `/ghost`, `/challenge` | direct write |

**`graph.json` changes:** none required. All v1.4 state lives in sidecars. This preserves Phase 6 delta/snapshot semantics — graph.json snapshots remain comparable across runs without Phase-15 noise mutating fields.

## New modules / files — file-path concrete list

| Phase | New file | Size estimate | Concern |
|-------|---------|---------------|---------|
| 12 | `graphify/routing.py` | 150–250 LOC | File complexity classification + model selection |
| 12 | `tests/test_routing.py` | ~200 LOC | Router unit tests, determinism regression test |
| 13 | `graphify/capability.py` | ~200 LOC | Manifest generator + `graphify capability` CLI |
| 13 | `graphify/harness_export.py` | ~300 LOC | SOUL/HEARTBEAT/USER export + import |
| 13 | `graphify/harness_schemas/claude.yaml` | ~50 LOC YAML | Schema template |
| 13 | `graphify/harness_schemas/letta.yaml` | ~50 LOC YAML | Schema template |
| 13 | `graphify/harness_schemas/honcho.yaml` | ~50 LOC YAML | Schema template |
| 13 | `graphify/harness_schemas/codex.yaml` | ~50 LOC YAML | Schema template |
| 13 | `tests/test_capability.py`, `tests/test_harness_export.py` | ~300 LOC each | Unit tests |
| 14 | `graphify/commands/moc-expand.md` | prompt MD | Obsidian `/moc-expand` command |
| 14 | `graphify/commands/vault-health.md` | prompt MD | Obsidian `/vault-health` |
| 14 | `graphify/commands/note-provenance.md` | prompt MD | Obsidian `/note-provenance` |
| 14 | `graphify/commands/round-trip-check.md` | prompt MD | Obsidian `/round-trip-check` |
| 14 | `tests/test_commands_install.py` (extend) | ~100 LOC | Verify frontmatter-driven install filters |
| 15 | `graphify/enrich.py` | ~250 LOC | Deriver passes + overlay writer |
| 15 | `tests/test_enrich.py` | ~300 LOC | Per-pass unit tests |
| 16 | `graphify/argue.py` | ~300 LOC | Populate/abstract/subgraph selection substrate |
| 16 | `tests/test_argue.py` | ~250 LOC | Unit tests on populate/subgraph selection |
| 16 | `graphify/commands/argue.md` | prompt MD | `/argue <topic>` command |
| 17 | `graphify/commands/ask.md` (or `chat.md`) | prompt MD | `/ask <question>` invoking chat MCP |
| 17 | (serve.py additions — no new module) | ~150 LOC in serve.py | `_run_chat()` + `_tool_chat` |
| 17 | `tests/test_serve.py` (extend) | ~200 LOC | Chat tool round-trip + citation schema |
| 18 | (serve.py additions — no new module) | ~80 LOC in serve.py | `_run_focus_context()` + `_tool_get_focus_context` |
| 18 | `tests/test_serve.py` (extend) | ~100 LOC | Focus context tool tests |

## Integration with existing modules — touch table

| Existing module | Phases that touch it | Nature of change |
|---|---|---|
| `graphify/__main__.py` | 12 (env var), 13 (`harness`/`capability` subcommands), 14 (commands-whitelist refactor), 15 (`enrich` subcommand) | Additive subcommand `elif` branches + `_PLATFORM_CONFIG` extension |
| `graphify/extract.py` | 12 | `extract()` signature gains `router:` kwarg; dispatch wrapped |
| `graphify/cache.py` | 12 | `file_hash()` gains `model_id` kwarg (backward compat default) |
| `graphify/serve.py` | 13, 16, 17, 18 | New `_run_*`/`_tool_*`/`types.Tool(...)` + `_handlers` entries; possible `_load_enrichment` overlay helper |
| `graphify/skill.md` | 12, 14, 15, 16, 17 | New pipeline sections for router, enrichment, argumentation, chat |
| `graphify/watch.py` | 15 (optional) | Optional `--enrich` post-rebuild hook — safe no-op if enrichment module absent |
| `graphify/commands/` | 14, 16, 17 | New `.md` prompt files with `target:` frontmatter |
| `pyproject.toml` | 13 | New optional extra `harness`, package_data for `harness_schemas/*.yaml` |

## Conflicts with existing decisions — flags

- **None identified.** All proposals keep D-02 (MCP envelope), D-16 (alias redirect), D-18 (compose not plumb), D-73 (skill drives), D-74 (`to_obsidian()` stays a notes pipeline) intact.
- **Watch point:** Phase 15's overlay-read in `_load_graph` adds a branch to the hottest path in `serve.py`. Guard with a fast-path `enrichment.json` existence check to avoid any cost when users don't run enrichment.
- **Watch point:** `_uninstall_commands()` whitelist is the single most fragile spot. Migrate it to directory-scan before adding Phase-14 commands; otherwise Phase 14 introduces a permanent hand-maintained list.

## Anti-patterns to avoid in v1.4

- **DON'T write enrichment into `graph.json`.** Phase 6's delta machinery expects graph.json stable across runs except for structural changes. Enrichment must stay overlay-only.
- **DON'T put argumentation LLM orchestration in `argue.py`.** That belongs in the skill. `argue.py` is a substrate (subgraph selection + perspective seeds); the debate loop lives where the autoreason tournament lives — in `skill.md`. Doing otherwise breaks D-73.
- **DON'T auto-ship a new MCP tool without a manifest entry.** Phase 13 should be the penultimate phase; any earlier-introduced tool (13 chat, 16 argue, 18 focus) automatically appears in the final manifest regeneration — no manual advertisement step.
- **DON'T overload `watch.py`.** Enrichment is a different trigger shape; fold them into one at the cost of clarity.
- **DON'T hardcode new model identifiers or endpoints in `routing.py`.** Keep model selection table as a YAML (`graphify/routing_models.yaml`) so users can retarget without code edits — consistent with `harness_schemas/` shape.

## Confidence and open questions

- **HIGH confidence:** file paths, integration points, D-* alignment, existing module touch surface. All grounded in direct code reads.
- **MEDIUM confidence:** ThreadPoolExecutor vs ProcessPoolExecutor for Phase 12 parallelism — depends on whether tree-sitter Python bindings release the GIL during parse. If they do (likely — they delegate to C), threads are the right call. Worth a 30-line benchmark in Phase 12 Plan 01.
- **MEDIUM confidence:** whether `enrichment.json` overlay read should happen inside `_load_graph` or be a separate `_load_enrichment_overlay` called post-load. Preference: post-load — keeps `_load_graph` unchanged for tests that mock it.
- **LOW confidence / open:** precise shape of Phase 13 harness schemas. The four targets (claude/codex/letta/honcho) have different memory models; converging on one `{SOUL, HEARTBEAT, USER}` trio may need per-target escape hatches. Recommend starting with one target (claude) and generalizing after.
