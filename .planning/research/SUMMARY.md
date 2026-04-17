# Project Research Summary — graphify v1.4 Agent Discoverability & Obsidian Workflows

**Milestone:** v1.4 (Phases 12–18 + SEED-002 Harness Memory Export)
**Synthesized:** 2026-04-17
**Inputs:** `.planning/research/STACK.md` (340 lines), `FEATURES.md` (741 lines), `ARCHITECTURE.md` (288 lines), `PITFALLS.md` (607 lines)
**Confidence (overall):** HIGH on stack, features, architecture; HIGH on pitfalls (includes v1.3 post-mortem grounding).

---

## What v1.4 Is For (TL;DR)

v1.4 turns graphify from a tool you run into a tool that **agents find, trust, compose with, and improve in the background**. It ships seven phases plus SEED-002 Harness Memory Export that collectively cover three outcomes: (a) *agent discoverability* — a self-describing MCP capability manifest + portable harness-memory export so graphify is findable via MCP registries and not locked into any single harness; (b) *Obsidian workflow depth* — vault-scoped thinking commands that leverage v1.0's profile adapter and v1.1's sentinel-preserved round-trip; (c) *graph quality over time* — heterogeneous file-to-model routing for cost-aware extraction, async background enrichment derivers, focus-aware zoom, conversational chat, and SPAR-Kit graph-argumentation — all layered on top of v1.0–v1.3 invariants (graph.json is read-only, sidecars are atomic, peer_id defaults to `"anonymous"`, everything routes through `security.py`).

The competitive wedge surfaced by FEATURES.md is that graphify is the *only* tool with a pre-built ABSTRACT substrate (the graph itself) that SPAR-Kit-style multi-perspective argumentation can plug into, the *only* dev tool routing by AST complexity rather than role, and the *only* harness-agnostic memory exporter with bidirectional round-trip. These differentiators are where marketing/docs should lead.

---

## Key Findings by Dimension

### Stack (STACK.md) — one new extra, conditional second

Net change is exactly **one new required optional extra** (`[routing] = radon>=6.0.1`) and **one conditional** (`[enrich] = apscheduler>=3.11.2`, only if Phase 15 requires wall-clock triggers). Everything else rides on stdlib or existing extras. No new required dependencies. Verified versions via Context7: `mcp` 1.27.0 (v2 not PyPI-released yet), `radon` 6.0.1, `apscheduler` 3.11.2, `jsonschema` 4.26.0 (already transitive via `[mcp]`). Negative findings: **SPAR-Kit has no PyPI package** (it is a prompt-protocol spec); **no MCP manifest standard has stabilized** — graphify ships its own schema under `_meta` namespace.

### Features (FEATURES.md) — six graphify-unique capability cells

AST-metric complexity routing (Phase 12); graph-as-SPAR-Kit-ABSTRACT substrate (Phase 16); profile-driven Obsidian commands (Phase 14); graph-grounded chat with citation enforcement (Phase 17); cross-harness memory neutrality (Phase 13 + SEED-002); vault round-trip awareness (v1.1 leveraged by Phase 14). Table stakes grounded in MCP 2025-11-25, Honcho deriver pattern, SPAR-Kit POPULATE→ABSTRACT→RUMBLE→KNIT. Per-phase P1/P2/P3 prioritization matrix defines MVP tightly.

### Architecture (ARCHITECTURE.md) — zero D-invariant conflicts

All seven phases preserve D-02 (MCP envelope), D-16 (alias redirect), D-18 (compose don't plumb), D-73 (skill drives, CLI = utilities). Every phase lands as **new module + additive extensions** — no rewrites. `graph.json` stays read-only; all new state lives in sidecars. Single maintenance-hazard found: `_uninstall_commands()` hardcoded whitelist in `__main__.py:153` must migrate to directory-scan before Phase 14 commands.

### Pitfalls (PITFALLS.md) — 11 critical, 9 moderate, 1 regression-risk category

Pitfall 20 codifies the v1.3 CR-01 bug into permanent regression: rename `snapshot.py` `root` → `project_root` with sentinel dataclass asserting `not path.name == "graphify-out"`. Cross-phase composition risks (15↔12, 16↔17, 14↔17, 13 describing non-determinism) are hypothesized but grounded.

---

## Stack Additions (Single Authoritative Table)

| Phase | Optional extra | Library | Version | Rationale |
|-------|---------------|---------|---------|-----------|
| 12 Routing | **NEW: `[routing]`** | `radon` | `>=6.0.1` | Cyclomatic complexity + MI for Python. Non-Python piggybacks on existing tree-sitter Tree. |
| 12 Routing | stdlib | `concurrent.futures.ThreadPoolExecutor` | 3.10+ | I/O-bound LLM fan-out. ARCHITECTURE: tree-sitter C state doesn't fork-clone on macOS. STACK: async would require rewriting every extractor. |
| 13 Manifest | reuses `[mcp]` transitive | `jsonschema` | `>=4.26.0` | Optional validator for `graphify capability --validate`. |
| 13/SEED-002 | reuses `[obsidian]` | `PyYAML` | `6.0.3` | Harness schemas in `graphify/harness_schemas/*.yaml`. |
| 13/SEED-002 | stdlib | `string.Template` | 3.10+ | Keeps v1.0 "no Jinja2" precedent. |
| 14 Commands | reuses `[obsidian]` + package_data | n/a | n/a | `graphify/commands/*.md` + frontmatter target filter. |
| 15 Enrichment | stdlib | `asyncio.Queue` + `Task` | 3.10+ | Honcho DB-queue is wrong shape for a CLI. |
| 15 Enrichment | **CONDITIONAL: `[enrich]`** | `apscheduler` | `>=3.11.2` | Only if wall-clock triggers required (open question OQ-1). |
| 16 Argumentation | core only | `networkx` subgraph views | existing | `nx.ego_graph` IS SPAR-Kit ABSTRACT. |
| 17 Chat | core only | existing MCP tools | — | Host harness is router; no langchain/llama-index. |
| 18 Focus | core only | `nx.ego_graph` | existing | Pull-model via MCP arg. |

**Net `pyproject.toml` change:** one new `[routing]` extra; one conditional `[enrich]`; update `[all]` accordingly.

### Cross-dimension contradictions — reconciled

| Observation | STACK | FEATURES | ARCHITECTURE | Resolution |
|-------------|-------|----------|--------------|------------|
| Phase 17 chat surface | Skill file, MCP tool optional | Skill file; NO new MCP tools initially | **Add MCP tool** `chat(query, session_id)` — skill has no home for session state | **ARCHITECTURE wins.** Ship MCP tool + structured citation packet in meta. |
| Phase 13 manifest location | `graphify manifest` on demand | `server.json` repo root + MCP resource | Both static (`server.json`) AND runtime (`graphify-out/manifest.json`) | **Both.** Different consumers (MCP registry vs live-state). |
| SEED-002 harness_export location | New modules `harness_export.py` + `harness_import.py` | Scoped inside Phase 13 | **NEW module `graphify/harness_export.py` — NOT bundled into `capability.py`** | All three agree. Keep separate modules (different concerns). |
| Phase 12 parallelism | `ThreadPoolExecutor` (stdlib) | parallel extraction | ThreadPool, not ProcessPool (macOS fork issues) | All agree. |
| Phase 15 triggers | asyncio.Queue; APScheduler conditional | queue + `graphify derive` CLI; entry-point derivers | new CLI subcommand; do NOT fold into `watch.py` | All agree — CLI-driven explicit invocation. |

---

## Feature Categories for Requirements Definition (Three Bundles)

### Bundle A — Infrastructure (Phase 12 + Phase 18 + Phase 15)

| | Phase 12 Routing | Phase 18 Focus | Phase 15 Enrichment |
|--|------------------|----------------|---------------------|
| **Table stakes** | Role-based model config, parallel extraction, per-node `extracted_by_model` stamp, token-cost summary (FEATURES — Aider/Continue precedent) | `get_focus_context(file_path)`, file-path→node resolver, "file not in graph" response (FEATURES — letta-obsidian reads raw files; graphify reasons over nodes) | File-backed queue, `graphify derive` CLI, enrichment sidecar distinct from graph.json, entry-point registration (FEATURES — Honcho session-queue) |
| **Differentiators** | AST-metric classifier (no dev tool does this), per-file-type defaults, vision-model routing | Focus-aware chat routing, focus-filtered analysis, git-HEAD complement, focus transfer to vault commands | 4 built-ins (description/pattern/community/staleness), session-queue per community, dry-run cost preview |
| **Anti-features** | No learned routing; no 20+ model auto-discovery; no silent cache fallback; no per-node mid-file routing | No real-time cursor tracking (LSP out of scope); no ambient filesystem watcher (D-18); no multi-file focus; no persistent cross-session focus | **NO real-time rebuild** (contradicts delta.py); NO blocking pipeline; **NO graph.json mutation** (Pitfall 3); NO arbitrary user-Python; NO LLM without budget caps; NO implicit deriver on MCP `get_node` |

### Bundle B — Discovery (Phase 13 + SEED-002)

| | Phase 13 Capability Manifest | SEED-002 Harness Memory Export |
|--|------------------------------|-------------------------------|
| **Table stakes** | MCP `initialize` handshake compliance (2025-11-25), per-tool description+inputSchema audit, `server.json` at repo root, README capability section | Export `CLAUDE.md` + `AGENTS.md`, `graphify export-harness [--format claude\|agents\|all]` CLI |
| **Differentiators** | Manifest as first-class MCP resource `graphify://capabilities/manifest`, `cost_class` annotations, self-describing `graphify.status()`, `_meta` publisher-provided metadata, version compatibility | Inverse import (closes lock-in-exit loop), canonical schema layer, round-trip byte-equal manifest, companion to Phase 13 |
| **Anti-features** | NO proprietary schema (extend `server.json._meta`); NO auth in manifest (MCP transport handles); NO dynamic tool-appearance; NO auto-publish to registry | **NO annotations by default** (Pitfall 11); NO full MCP-call-trace export (privacy); NO auto-export on build; **NO unquarantined inverse import** (Pitfall 9) |

### Bundle C — Interaction (Phase 17 + Phase 14 + Phase 16)

| | Phase 17 Chat | Phase 14 Obsidian Commands | Phase 16 Argumentation |
|--|---------------|----------------------------|------------------------|
| **Table stakes** | NL → MCP tool-call translation, grounded answer with `[node:id]` citations, "no relevant graph content" template, session history (FEATURES — letta-obsidian chat sidebar) | `/moc`, `/related`, `/orphan`, `/wayfind`, profile-driven, writes through `propose_vault_note` | `argue(question)` MCP tool, subgraph ≤50-node budget, 3-persona default, mandatory `[cite: node_id]`, `GRAPH_ARGUMENT.md` output, advisory-only |
| **Differentiators** | Grounded in structured graph (Cognee surfaces chunks; graphify surfaces nodes), auto-suggest follow-ups, chat-to-argue handoff, save-as-vault-note | `/bridge`, `/voice`, `/drift-notes`, Dataview output, profile-driven Ideaverse/Sefirot adaptation | **Graph-as-ABSTRACT substrate (unique per SPAR-Kit)**, citation-grounded, INTERROGATE step (+40% quality), clash/rumble/domain intensity, persona memory |
| **Anti-features** | **NO chat without tool call**; **NO fabricated IDs** (Pitfall 7); NO cross-session memory (privacy); NO voice-matching without disclosure; NO answers > 500 tokens | NO duplicating Phase 11 names; NO auto-write bypassing `propose_vault_note`; NO Obsidian-plugin integration; NO file-watcher triggers | NO auto-applying to code; **NO fabrication** (Pitfall 5); NOT a Phase 9 replacement; round cap 6; **NO consensus-forcing**; **Phase 16 MUST NOT call Phase 17** (Pitfall 18) |

---

## Recommended Build Order with Dependency Graph

### Reconciliation of two independent orderings

- **FEATURES.md implicit:** Infrastructure (12→18→15) → Discovery (13+SEED-002) → Interaction (17→14→16).
- **ARCHITECTURE.md explicit:** 12 → 18 (parallel) → 15 → 17 → 16 → 14 → 13.

### Reconciled order (adopted — ARCHITECTURE.md order + Phase 13 two-wave compromise)

```
1. Phase 12 Routing            ──► HARD gates cache.py key format (router_version + model_id).
                                    Must land first so downstream phases inherit stable keys.
2. Phase 18 Focus              ──► Parallel with 12. No code overlap (serve.py only).
                                    Small, testable. Unblocks Phase 14 /note-provenance.
3. Phase 13 Wave A (plumbing)  ──► Manifest generator + `graphify capability` CLI + runtime
                                    MCP tool. Describes surface present at this point; sets
                                    the introspection pattern for 14/15/16/17 to auto-register.
4. Phase 15 Enrichment         ──► Soft-depends on Phase 12 routing.json (skip-list). Writes
                                    enrichment.json that Phase 17 chat can read.
5. Phase 17 Chat               ──► Soft-depends on Phase 18 (focus_hint in args) + Phase 15
                                    (enrichment overlay for citations).
6. Phase 16 Argumentation      ──► Soft-depends on Phase 17 citation format. Reuses Phase 9
                                    blind-label harness. MUST NOT call Phase 17 (Pitfall 18).
7. Phase 14 Obsidian Commands  ──► HARD-depends on Phase 18 (/note-provenance) + Plan 00
                                    commands-whitelist refactor. Soft-depends on Phase 17
                                    for /voice.
8. Phase 13 Wave B + SEED-002  ──► Final manifest regeneration with all 14–18 tools present.
                                    SEED-002 bundled — both advertise graphify externally.
```

### Dependency classification

| Edge | Type | Rationale |
|------|------|-----------|
| 12 → cache.py key format | HARD | `file_hash()` gains `model_id` kwarg, backward compat for old callers but must land before Phase 15. |
| 12 → 15 (routing.json skip-list) | SOFT | Enrichment runs without routing.json; quality degrades gracefully. |
| 18 → 12 | NONE | Fully parallelizable. |
| 13A → 14/15/16/17/18 | SOFT | Introspection pattern established; downstream phases register into it. |
| 17 → 16 | SOFT | Phase 16 could predate; shipping 17 first shares citation-packet format. |
| 18 → 14 `/note-provenance` | HARD | Concrete consumer of `get_focus_context`. |
| Commands-whitelist refactor → 14 | HARD | Must land before any new command or we have a permanent hand-maintained list. |
| 13B → all prior | HARD | Manifest as last-wave descriptive pass captures full surface. |
| 16 ← 17 tool call | **FORBIDDEN** | Pitfall 18: recursion + non-determinism. Manifest declares `composable_from: []`. |

---

## Top Pitfalls v1.4 Must Design Around (Must-Prevent List)

| # | Pitfall | Owning phase(s) | Prevention strategy |
|---|---------|-----------------|---------------------|
| **1** | **Router silent quality regression** — cheap model for dense file; validates but recall drops 30–60%; cached as "correct" | Phase 12 | Hard floor per `file_type` (code always ≥ mid-tier); canary probes (every N-th cheap route re-run on expensive, ratio ≥ 0.6); `router_version` in cache key |
| **2** | **Concurrent-extraction stampede** — N parallel 429 retries = thundering herd; cost ceiling blown | Phase 12 | Central `threading.Semaphore` sized by provider concurrency (default 4); pre-flight `GRAPHIFY_COST_CEILING`; global 429 backoff via shared `threading.Event`; idempotent dedup at retry |
| **3** | **Background enrichment overwrites `graph.json`** — violates v1.1 read-only invariant | Phase 15 | Enrichment writes ONLY `enrichment.jsonl` + `enrichment_index.json`; `fcntl.flock` on `.enrichment.lock` shared with foreground; `_write_graph_json` private + grep-CI test only `build.py`+`__main__.py` call it; enrichment consumes snapshot not live; merge-on-read |
| **4** | **Debate fabricates nodes/edges** — Challenger invents `rm_rf_command`; Judge accepts; transcript indistinguishable from truth | Phase 16 | `{"claim", "cites": [node_id]}` mandatory schema; validator every turn, unknown cites → `[FABRICATED]` + re-prompt; temp ≤ 0.4; no consensus-forcing (`dissent`/`inconclusive` valid) |
| **5** | **NL-chat fabricates node names** — single-LLM invents plausible answer for nonexistent entity | Phase 17 | Two-stage pipeline structurally enforced (Stage 1 tool-call only, Stage 2 answer from results only); empty results → templated fuzzy suggestions; post-process grep rejects uncited phrases; `sanitize_label` on all free text |
| **6** | **Focus-object spoofing** — post-prompt-injection agent reports `/etc/passwd`; errors leak filesystem structure | Phase 18 | `security.py::validate_graph_path(base=vault_root)`; silent-ignore non-corpus (no error echo); `reported_at` ≤ 5 min freshness; 500 ms debounce |
| **7** | **SEED-002 inverse-import prompt-injection** — compromised CLAUDE.md carries adversarial content; fires in downstream LLM stages | SEED-002 + Phase 12/16/17 | Quarantine to `imported_memory/` with `trusted: false`; downstream filters or wraps as untrusted; instruction-pattern scrubbing; NEVER auto-import |
| **8** | **Snapshot path double-nesting (codifies v1.3 CR-01)** — `graphify-out/` passed as `root`; `tmp_path` tests hide it | Phase 12, 15, 17, 18 | Rename `root` → `project_root` in `snapshot.py`; sentinel dataclass `ProjectRoot(Path)` asserts `not path.name == "graphify-out"`; integration test with nested-dir fixture |

---

## Integration Decisions Locked by Research

- **Router is NEW module `graphify/routing.py`**, NOT extended into `extract.py` (already 2817 LOC). Router is pure classifier; parallelism in `extract()`.
- **Router uses `radon` for Python + tree-sitter walker for other languages** — reuses existing parse output, keeps `[routing]` extra tiny. Not `lizard` (bigger multi-language lib).
- **Parallelism = `ThreadPoolExecutor`**, NOT asyncio (sync SDK path), NOT multiprocessing (tree-sitter C state, macOS fork). GIL releases on `socket.recv`.
- **Enrichment writes overlay sidecar ONLY; graph.json pipeline-owned.** Merge-on-read in `_load_enrichment_overlay` (post-load, per ARCHITECTURE medium-confidence preference). Grep-CI guard.
- **Enrichment pins `--snapshot-id` at start**; does NOT follow new snapshots mid-run. Foreground `/graphify` takes same lock → foreground wins, enrichment SIGTERM-aborts cleanly.
- **Manifest is STATIC (`server.json` repo root) + RUNTIME (`graphify-out/manifest.json` + MCP resource).** Extends MCP `server.json` via `_meta` — no competing schema.
- **Manifest generated from LIVE registry**, never hand-maintained (Pitfall 12). Hash embedded in every response envelope; CI `graphify manifest --validate` gate.
- **Manifest declares `deterministic: false` for LLM-backed tools** (Pitfall 19). Per-tool `cacheable_until` hint.
- **Phase 16 SUBSTRATE in `graphify/argue.py`; ORCHESTRATION in `skill.md`** (D-73; parallels Phase 9 autoreason tournament where LLM loop lives in skill.md:1324–1546).
- **Phase 16 MUST NOT compose Phase 17 chat as primitive** (Pitfall 18). Debate uses lower-level deterministic `graph_context(node_id)`. Manifest declares chat `composable_from: []`.
- **Focus is PULL-MODEL via MCP arg** (`focus_hint` dict with optional `function_name`/`line`/`neighborhood_depth`/`include_community`), NOT filesystem watcher.
- **Phase 17 `chat` tool returns STRUCTURED PACKET in meta**, does NOT render narrative. `serve.py` has never made an LLM call and won't. Citations in `meta["citations"]` as `{node_id, label, source_file}`.
- **SEED-002 `harness_export.py` is SEPARATE module from `capability.py`** — different concerns. Start with `claude.yaml`; generalize.
- **SEED-002 exports EXCLUDE annotations by default** (Pitfall 11). Allow-list only `id/label/source_file/relation/confidence`; `--include-annotations` runs secret-scanner regex suite.
- **SEED-002 imports are TRUSTED=FALSE by default** (Pitfall 9). Downstream LLM stages (12/16/17) check flag, fence untrusted content.
- **Phase 14 commands prefix `/graphify-*`** (Pitfall 14). SKIP_PRESERVE sentinel reused; single registry shared with Phase 11.
- **Phase 14 pipeline-triggering commands require explicit opt-in install + cost-preview banner** (Pitfall 15). `trigger_pipeline: true` frontmatter flag.
- **Commands-whitelist refactor is Phase 14 Plan 00** — migrate `_uninstall_commands()` hardcoded tuple in `__main__.py:153` to directory-scan.

---

## Open Questions That Must Be Resolved in Requirements Scoping

| # | Question | Proposed route |
|---|----------|----------------|
| OQ-1 | **Phase 15 scheduler:** need APScheduler wall-clock triggers? | **Default NO.** Ship without `[enrich]` extra. Revisit v1.4.x if UAT demands "re-enrich every 30 min". Honcho's pattern is queue-polling. |
| OQ-2 | **Phase 12 routing granularity:** per-file or per-function? | **Per-file only.** Per-function breaks extraction atomicity and creates parallel race conditions (FEATURES anti-feature). |
| OQ-3 | **Phase 13 manifest location:** `server.json` + `graphify-out/manifest.json`? | **Both.** `server.json` (MCP registry discovery, version-controlled); `graphify-out/manifest.json` (live state, dynamic). |
| OQ-4 | **SEED-002 inverse-import scope:** v1.4 or v1.4.x? | **v1.4 but P2.** Asymmetric without it (Harrison Chase framing says bidirectional non-negotiable). If capacity tight, slip to v1.4.x with positioning note. |
| OQ-5 | **SEED-002 harness schema count:** 4 targets or 1? | **One at launch (`claude.yaml`).** Generalize to AGENTS.md in v1.4.x. Letta/Honcho are API-backed, different handling. |
| OQ-6 | **Phase 16 INTERROGATE + persona memory:** MVP or v1.4.x? | **v1.4.x.** P2 per prioritization matrix. Add `--interrogate` opt-in post-UAT. |
| OQ-7 | **Phase 14 `/voice`/`/bridge`/`/drift-notes`:** MVP or v1.4.x? | **v1.4.x.** HIGH complexity + soft-depends on Phase 17 stabilizing. P1: `/moc`, `/related`, `/orphan`, `/wayfind`. |

---

## Regression-Risk Table — v1.0–v1.3 Guards v1.4 MUST Preserve

| Guard | Established in | v1.4 regression vector | Mitigation |
|-------|----------------|------------------------|------------|
| `security.py::validate_url` SSRF + redirect re-validation | v1.0 | Phase 14 fetches user URL; Phase 17 chat accepts URL-shaped text | All external URLs through `validate_url`; forbid direct `urllib`/`requests` in new modules |
| `security.py::validate_graph_path` confinement to `graphify-out/` | v1.0 | Phase 15 sidecar path computed from input; Phase 18 `focus_hint.file_path` bypassed; SEED-002 export target escapes | All new file I/O through `validate_graph_path(path, base=...)` |
| `sanitize_label` / `sanitize_label_md` | v1.0 | Phase 17 echoes user query into MD; Phase 14 renders node label as raw HTML; Phase 16 transcript embeds unescaped prompts | All label renders in new output go through existing helpers |
| `peer_id` default = `"anonymous"` | v1.2 | Phase 15 adds `socket.gethostname()` "for debugging"; Phase 18 session focus adds machine ID | CI asserts `peer_id` never reads `os.environ`/`socket.gethostname()`/`platform.node()` |
| `graph.json` read-only from library (atomic `os.replace` sidecars) | v1.1 D-invariant | **Phase 15 writes directly** (Pitfall 3); Phase 16 argument persists into graph | Single-writer grep-CI test — only `build.py` + `__main__.py` call `_write_graph_json`; private underscore |
| Atomic `.tmp` + `os.replace` on sidecars | v1.2 concurrent-MCP | Phase 13 manifest, Phase 15 index, Phase 18 session cache written naively | New sidecar writes use temp+rename; shared I/O helper |
| `yaml.safe_load` (no `yaml.load`) — T-10-04 | Phase 10 | Phase 14 frontmatter parser or SEED-002 schema loader uses `yaml.load` | CI grep asserts no `yaml.load(` outside allow-listed test fixtures |
| Phase 9 blind-label harness (shuffled A/B, stripped persona phrases) | Phase 9 | Phase 16 orchestrator skips shuffling → systematic Defender bias (Pitfall 6) | Phase 16 imports Phase 9 harness as-is; regression test replays Phase 9 bias suite |
| Snapshot `root` = project root (not `graphify-out/`) — Phase 11 CR-01 | v1.3 | Phase 12/15/17/18 readers re-introduce double-nesting (Pitfall 20) | Rename `root` → `project_root` in `snapshot.py`; sentinel dataclass; nested-dir fixture test |
| Phase 11 `_cursor_install()` signature (CR-02) | v1.3 | Phase 14 commands-whitelist refactor regresses platform installers | `_install_commands` signature tests; per-`_PLATFORM_CONFIG` round-trip test |
| v1.1 `propose_vault_note + approve` trust boundary + sentinel blocks | v1.1 | Phase 14 `/moc` or `/bridge` auto-writes bypassing approval | All Phase 14 vault writes go through `compute_merge_plan`+`apply_merge_plan`; sentinel enforced by merge engine |
| v1.3 dedup alias map (`_alias_map`, `_resolve_alias`) — D-16 | Phase 10 | Phase 15 enrichment/17 chat citation not alias-resolved | Every new handler threads IDs through `_resolve_alias`; Pitfall 17 mitigation |
| MCP envelope `text_body + SENTINEL + json(meta)` — D-02 | v1.3 9.2 | Phase 13/16/17/18 MCP tools | Every new `_tool_*` uses existing envelope helper; integration test asserts sentinel |
| Manifest hand-maintenance banned | v1.4 Phase 13 (new) | Dev adds v1.5 tool and updates manifest.md by hand | Introspection-only manifest; CI `manifest --validate` gate; manifest hash in every response |

---

## Traceability Crosswalk (Phase → REQ-ID prefix → Citations)

| Phase | REQ prefix | FEATURES citation | Top PITFALLS risks | STACK extra / new module | ARCHITECTURE module |
|-------|-----------|-------------------|--------------------|--------------------------|---------------------|
| 12 Routing | `ROUTE-*` | "AST-metric classifier (unique)" | Pitfall 1, 2, 20 | `[routing]` = radon; ThreadPoolExecutor | `graphify/routing.py` + `extract.py:2652` + `cache.py:20 file_hash()` |
| 13 Manifest | `MANIFEST-*` | "three-tier discovery; `_meta`" | Pitfall 12, 13, 19 | reuses `[mcp]` → jsonschema; stdlib json | `graphify/capability.py` + `serve.py _tool_capability_describe` |
| 14 Obsidian Cmds | `OBSCMD-*` | "/moc, /related, /orphan, /wayfind; profile-driven" | Pitfall 14, 15, 16 | reuses `[obsidian]` + package_data | `graphify/commands/*.md` + `__main__.py:133` refactor |
| 15 Enrichment | `ENRICH-*` | "4 built-in derivers; Honcho session-queue" | **Pitfall 3 CRIT**, 4, 17 | stdlib asyncio; conditional `[enrich]` | `graphify/enrich.py` + CLI + `enrichment.json` |
| 16 Argumentation | `ARGUE-*` | "graph as ABSTRACT (unique); `[cite: node_id]`" | Pitfall 5, 6, 18 | reuses networkx + autoreason | `graphify/argue.py` + `skill.md` + `serve.py argue_topic` |
| 17 Chat | `CHAT-*` | "NL→MCP; grounded citations (vs Cognee chunks)" | Pitfall 7, 16, 19 | core only | `serve.py _run_chat()` + `_tool_chat` + `commands/ask.md` |
| 18 Focus | `FOCUS-*` | "`get_focus_context`; pull-model" | **Pitfall 8 CRIT**, 20 | core only (nx.ego_graph) | `serve.py _run_focus_context()` + `_tool_get_focus_context` |
| SEED-002 Harness | `HARNESS-*` | "canonical schema; inverse import" | **Pitfall 9 CRIT**, 10, **11 CRIT** | reuses `[obsidian]` PyYAML + stdlib Template | `graphify/harness_export.py` + `harness_import.py` + `harness_schemas/*.yaml` |

---

## Confidence Assessment

| Area | Confidence | Notes |
|------|------------|-------|
| **Stack** | HIGH | All pins verified Context7. MEDIUM only on negative findings (no MCP manifest standard; SPAR-Kit not PyPI). |
| **Features** | HIGH | MCP 2025-11-25 + Honcho docs + SPAR-Kit + MCP registry server.json all fetched. MEDIUM on Letta sleep-time compute (docs.letta.com blocked). |
| **Architecture** | HIGH | Direct reads of `__main__.py`, `serve.py`, `watch.py`, `extract.py`, `cache.py`, `manifest.py`. MEDIUM on ThreadPool vs ProcessPool (benchmark in Plan 01 confirms). LOW on precise SEED-002 schema shape across 4 targets. |
| **Pitfalls** | HIGH | Grounded in v1.3 post-execution REVIEW.md (the 2 production-breaking bugs user called out) + `security.py` source + project invariants. MEDIUM on cross-phase composition risks (15↔12, 16↔17, 14↔17). |

### Gaps That Need Attention During Planning

- **Phase 15 scheduler (OQ-1)** must land in REQUIREMENTS.md before Phase 15 Plan 01 — determines whether `[enrich]` extra ships.
- **SEED-002 inverse-import scope (OQ-4)** — Harrison Chase framing says bidirectional non-negotiable, but FEATURES rates HIGH complexity.
- **SEED-002 harness target count (OQ-5)** — 1 vs 4 affects plan sequencing and test matrix.
- **Phase 16 INTERROGATE + persona memory (OQ-6)** + **Phase 14 `/voice`/`/bridge`/`/drift-notes` (OQ-7)** — v1.4-vs-v1.4.x split should be decided up front.
- **Commands-whitelist refactor positioning** — Plan 00 of Phase 14; confirm plan count reflects this.

---

## Sources (Aggregated)

### Primary research dimensions
- `.planning/research/STACK.md` (340 lines) — stack additions, alternatives, What NOT to Use
- `.planning/research/FEATURES.md` (741 lines) — table stakes/differentiators/anti-features per phase; competitor matrix
- `.planning/research/ARCHITECTURE.md` (288 lines) — module touch table, dependency graph, sidecar schema, D-invariant reconciliation
- `.planning/research/PITFALLS.md` (607 lines) — 11 critical + 9 moderate pitfalls, regression table, "looks done" checklist, recovery strategies

### External (fetched, HIGH confidence)
- MCP Specification 2025-11-25 (`modelcontextprotocol.io/specification`)
- MCP Registry `server.json` spec (`github.com/modelcontextprotocol/registry`)
- Honcho (`github.com/plastic-labs/honcho`) — explicit finding: DB-queue wrong shape for CLI
- SPAR-Kit protocol (`github.com/synthanai/spar-kit`) — POPULATE/ABSTRACT/RUMBLE/KNIT; NOT PyPI
- `/modelcontextprotocol/python-sdk` Context7 — MCP 1.27.0; v2 not PyPI-released
- `/rubik/radon` Context7 — v6.0.1 verified
- `/agronholm/apscheduler` Context7 — v3.11.2 (3.x stable)
- `/python-jsonschema/jsonschema` Context7 — v4.26.0, draft 2020-12
- Letta-Obsidian README

### External (MEDIUM confidence)
- Letta sleep-time compute (`docs.letta.com`, Arxiv 2504.13171) — docs blocked
- Continue/Aider/Cursor routing specifics — docs blocked

### Internal (HIGH confidence, first-party)
- `.planning/PROJECT.md` — v1.4 scope + Phase 12 pull-forward
- `.planning/ROADMAP.md` — Phase 12–18 descriptions with informed-by citations
- `.planning/seeds/SEED-002-harness-memory-export.md` — activation trigger; canonical schema
- `.planning/notes/april-research-gap-analysis.md`, `repo-gap-analysis.md`, `april-2026-v1.3-priorities.md`, `agent-memory-research-gap-analysis.md`
- `.planning/milestones/v1.3-phases/10-cross-file-semantic-extraction/10-REVIEW.md`, `11-narrative-mode-slash-commands/11-REVIEW.md` — CR-01 snapshot double-nesting; CR-02 `_cursor_install` — basis for Pitfall 20
- `graphify/security.py`, `serve.py`, `__main__.py`, `extract.py`, `cache.py`, `snapshot.py`, `delta.py`, `profile.py`, `templates.py`, `merge.py`, `commands/*.md`

---

### Executive Summary

v1.4 makes graphify agent-discoverable, vault-workflow-rich, and self-improving in the background — adding 7 phases (12 Routing, 13 Manifest, 14 Obsidian Commands, 15 Enrichment, 16 Argumentation, 17 Chat, 18 Focus) plus SEED-002 Harness Export to a shipped v1.3 product, with exactly one new required optional extra (`[routing] = radon`) and zero D-invariant conflicts.

### Roadmap Implications

Suggested phases: **8** (7 numbered + SEED-002 bundled with Phase 13).

1. **Phase 12 Routing** — gates cache.py key format; must land first.
2. **Phase 18 Focus** — parallel with 12, no overlap, unblocks Phase 14.
3. **Phase 13 Wave A (plumbing)** — establishes introspection pattern for 14–18 auto-registration.
4. **Phase 15 Enrichment** — soft-depends on Phase 12 routing.json.
5. **Phase 17 Chat** — soft-depends on 18 + 15 (citation overlay).
6. **Phase 16 Argumentation** — reuses Phase 9 blind-label; MUST NOT call Phase 17.
7. **Phase 14 Obsidian Commands** — HARD-depends on 18 + commands-whitelist refactor Plan 00.
8. **Phase 13 Wave B + SEED-002** — final manifest regeneration with full surface; bundled external-advertising wave.

### Research Flags

Needs deeper research during planning: **Phase 15** (scheduler decision OQ-1), **SEED-002** (harness target count OQ-5, inverse-import scope OQ-4), **Phase 13** (manifest location already settled, but wave A/B split needs requirements ratification).

Standard patterns (skip additional research): **Phase 12** (thread pool + radon well-documented), **Phase 18** (pull-model via MCP arg, existing nx.ego_graph), **Phase 17** (MCP tool + skill prompt, pattern from Phase 11 commands), **Phase 16** (parallels Phase 9 autoreason tournament structure), **Phase 14** (extends Phase 11 commands infrastructure).

### Confidence

Overall: **HIGH** on stack/architecture/pitfalls; **HIGH** on features with MEDIUM for Letta sleep-time compute (docs blocked). Gaps listed above.
