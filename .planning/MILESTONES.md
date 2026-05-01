# Milestones

## v1.10 Stability, Baselines & Concept↔Code MVP (Shipped: 2026-05-01)

**Phases completed:** 8 phase tracks (45–52), 14 plans

**Known deferred items at close:** 5 open artifact audit items acknowledged — quick-task slug present only as registry entry; 4 dormant seeds unchanged (see `STATE.md` — Deferred Items)

**Key accomplishments:**

- **HYG / baselines:** Shared **`corpus_prune`** + **`build_prior_files`** across **`detect`** and **`extract.collect_files`**; manifest skip **`stderr`**; optional **`corpus.dot_graphify`** + doctor track/apply; formal **`45-VERIFICATION.md`** (Phase **50** gap closure).
- **Concept↔code MVP:** Validated relation types, deterministic **`build`** merge + **`graph.json`** parity, **`sanitize_label_md`** on relations; MCP **`concept_code_hops`** + **`47-VERIFICATION`** / Phase **51** REQ mapping (**D-51.03**).
- **Output hygiene:** Doctor **`self_ingest_graphifyignore_hint_redundant`**; nested **`graphify-out`** pruning + canonical **`artifacts_dir`**; **`48-VERIFICATION.md`** (Phase **52**).
- **CLI provenance:** **`graphify --version`** / **`-V`**, success-footer **`[graphify] version`**, directional skill-stamp warnings; **`graphify.version.package_version()`** single reader.

---

## v1.9 Onboarding, Harness Portability & Vault CLI (Shipped: 2026-04-30)

**Phases completed:** 13 phases, 48 plans, 55 tasks
**Known deferred items at close:** 2 (see `STATE.md` — Milestone close acknowledgment v1.9)

**Key accomplishments:**

- v1.8 planning docs now use the canonical taxonomy and community-size contract that downstream Phase 32-36 executors must follow.
- v1.8 profile defaults now resolve Obsidian note folders under `Atlas/Sources/Graphify/`, validate taxonomy and `mapping.min_community_size`, and warn on deprecated community overview output.
- Taxonomy-resolved mapping contexts now route Obsidian notes under the Graphify subtree with canonical `mapping.min_community_size` community behavior.
- Doctor diagnostics now surface the same v1.8 profile preflight errors and warnings as direct profile validation, with warning-only community overview guidance kept nonfatal.
- Red pytest contract suite for cached concept names, deterministic fallbacks, repo identity precedence, MOC naming sinks, and CLI `--repo-identity` parsing
- Stdlib repo identity resolver plus vault profile schema for repo.identity and bounded concept naming controls
- Cache-backed concept MOC names with deterministic fallbacks, provenance sidecar records, and unsafe LLM title rejection
- Repo identity and concept naming now flow through CLI and Obsidian export, with durable sidecar provenance and sanitized generated MOC titles
- CODE note contracts with default cluster floor 6 and built-in safe template rendering
- Deterministic cluster routing metadata with CODE-only god-node classification and capped CODE member rollups
- Repo-aware CODE note filenames with deterministic collision provenance and MOC-only community export dispatch
- CODE notes and concept MOCs now link bidirectionally using final rendered concept labels and safe template sinks
- Concept MOCs now link to generated CODE notes using exact collision-safe filename stems while preserving sanitized display aliases
- Review-first Obsidian migration previews with deterministic plan IDs, durable artifacts, legacy ORPHAN visibility, and non-destructive apply filtering
- Resolved repo identity now appears consistently in CODE note filenames, frontmatter, tags, and vault manifests
- Preview-first raw corpus to Obsidian vault updates with reviewed plan-id apply gates and repo-drift conflict visibility
- Reviewed `update-vault --apply --plan-id` now archives legacy Obsidian notes under plan-scoped `graphify-out/migrations/archive/` paths with rollback metadata and helper/CLI regression coverage.
- Generic-first v1.8 migration guide with README and CLI help aligned around preview-first `update-vault`, reviewed apply, archive evidence, and rollback.
- Packaged graphify skill variants now share one tested v1.8 Obsidian contract for MOC-only output, preview-first `update-vault`, backup-before-apply, archive evidence, and no destructive deletion.
- Executable sanitizer coverage and final security validation for v1.8 Obsidian migration readiness.
- Install-time Claude/AGENTS guidance now matches the v1.8 Obsidian navigation contract and is covered by regression tests.
- Phase 34 validation metadata was ratified into a Nyquist-discoverable, evidence-aligned state without changing shipped runtime behavior.
- v1.8 milestone audit metadata debt was closed and Phase 37 planning/validation tracking was ratified for deterministic closeout automation.
- Reconciled — intent satisfied without a second execution branch
- Library core for hybrid elicitation: `run_scripted_elicitation`, `build_extraction_from_session`, `save_elicitation_sidecar`, and tests proving `validate_extraction` passes.
- `build()` accepts optional `elicitation` extraction; `merge_elicitation_into_build_inputs` loads `elicitation.json` when present.
- Fast-path SOUL/HEARTBEAT/USER emission from session state via `write_elicitation_harness_markdown`; harness CLI test hardened against stdout noise.
- `graphify elicit` registered with onboarding help text; skills include empty/tiny corpus pointer to CLI and docs.
- `docs/ELICITATION.md` documents discovery-first workflow, artifact paths, merge order, ELIC IDs, and phase 40/41 non-goals; README links to it.
- Complete
- Complete
- Complete
- Complete
- Complete
- Complete
- Complete

---

## v1.8 Output Taxonomy & Cluster Quality (Shipped: 2026-04-29)

**Phases completed:** 7 phases, 25 plans, 55 tasks

**Known deferred items at close:** 5 (see `STATE.md` — Deferred Items, milestone close acknowledgment)

**Key accomplishments:**

- v1.8 planning docs now use the canonical taxonomy and community-size contract that downstream Phase 32-36 executors must follow.
- v1.8 profile defaults now resolve Obsidian note folders under `Atlas/Sources/Graphify/`, validate taxonomy and `mapping.min_community_size`, and warn on deprecated community overview output.
- Taxonomy-resolved mapping contexts now route Obsidian notes under the Graphify subtree with canonical `mapping.min_community_size` community behavior.
- Doctor diagnostics now surface the same v1.8 profile preflight errors and warnings as direct profile validation, with warning-only community overview guidance kept nonfatal.
- Red pytest contract suite for cached concept names, deterministic fallbacks, repo identity precedence, MOC naming sinks, and CLI `--repo-identity` parsing
- Stdlib repo identity resolver plus vault profile schema for repo.identity and bounded concept naming controls
- Cache-backed concept MOC names with deterministic fallbacks, provenance sidecar records, and unsafe LLM title rejection
- Repo identity and concept naming now flow through CLI and Obsidian export, with durable sidecar provenance and sanitized generated MOC titles
- CODE note contracts with default cluster floor 6 and built-in safe template rendering
- Deterministic cluster routing metadata with CODE-only god-node classification and capped CODE member rollups
- Repo-aware CODE note filenames with deterministic collision provenance and MOC-only community export dispatch
- CODE notes and concept MOCs now link bidirectionally using final rendered concept labels and safe template sinks
- Concept MOCs now link to generated CODE notes using exact collision-safe filename stems while preserving sanitized display aliases
- Review-first Obsidian migration previews with deterministic plan IDs, durable artifacts, legacy ORPHAN visibility, and non-destructive apply filtering
- Resolved repo identity now appears consistently in CODE note filenames, frontmatter, tags, and vault manifests
- Preview-first raw corpus to Obsidian vault updates with reviewed plan-id apply gates and repo-drift conflict visibility
- Reviewed `update-vault --apply --plan-id` now archives legacy Obsidian notes under plan-scoped `graphify-out/migrations/archive/` paths with rollback metadata and helper/CLI regression coverage.
- Generic-first v1.8 migration guide with README and CLI help aligned around preview-first `update-vault`, reviewed apply, archive evidence, and rollback.
- Packaged graphify skill variants now share one tested v1.8 Obsidian contract for MOC-only output, preview-first `update-vault`, backup-before-apply, archive evidence, and no destructive deletion.
- Executable sanitizer coverage and final security validation for v1.8 Obsidian migration readiness.
- Install-time Claude/AGENTS guidance now matches the v1.8 Obsidian navigation contract and is covered by regression tests.
- Phase 34 validation metadata was ratified into a Nyquist-discoverable, evidence-aligned state without changing shipped runtime behavior.
- v1.8 milestone audit metadata debt was closed and Phase 37 planning/validation tracking was ratified for deterministic closeout automation.

---

## v1.7 Vault Adapter UX & Template Polish (Shipped: 2026-04-28)

**Phases completed:** 5 phases (27–31), 14 plans
**Requirements:** 13/13 satisfied (VAULT-08..15, TMPL-01..03, CFG-02..03)
**Audit verdict:** passed (5/5 phases verified, 5/5 Nyquist ratified)
**Tests:** 1801 passing / 1 xfailed
**Timeline:** 2026-04-27 → 2026-04-28 (~2 days, 173 commits)

**Key accomplishments:**

- **Phase 27 — Vault Detection & Profile-Driven Output Routing:** Lazy per-mode profile loader, `output.ResolvedOutput` contract consumed across the pipeline, profile-declared destination for `graphify-out/` instead of vault-root dump (VAULT-08/09/10).
- **Phase 28 — Self-Ingestion Hardening:** Atomic `output-manifest.json` with FIFO N=5 + GC + renamed-notes-dir recovery wired post-export in both CLI branches; D-26 stable `artifacts_dir` anchor across notes_dir rename (VAULT-11/12/13).
- **Phase 29 — Doctor Diagnostics & Dry-Run Preview:** New `graphify/doctor.py` pipeline-stage module + `graphify doctor --dry-run` reporting profile detection, output destination, ignore-list, would_self_ingest hint; additive `skipped` return from `detect.detect()` as single source of truth (VAULT-14/15).
- **Phase 30 — Profile Composition:** `extends:` / `includes:` with deterministic deep-merge, cycle detection, path-confined includes, and full `--validate-profile` provenance (CFG-02/03).
- **Phase 31 — Template Engine Extensions:** `_BlockTemplate` subclass with `{{#if_X}}` conditional sections (TMPL-01), `{{#connections}}` iteration loops (TMPL-02), per-note-type `dataview_queries` profile key with `_KNOWN_NOTE_TYPES` validation + per-key provenance (TMPL-03); D-16 single-pass FSM expansion BEFORE substitution as the layered defense for block-syntax injection.

**Known deferred items at close:** 4 (see STATE.md Deferred Items)

---

## v1.6 Hardening & Onboarding (Shipped: 2026-04-28)

**Phases completed:** 4 phases, 5 plans, 0 tasks

**Key accomplishments:**

- Patched `RoutingAudit.flush` and `write_manifest_atomic` to perform read-merge-write keyed by row identity (file path / tool name) before atomic `.tmp + os.replace` commit, preventing subpath-scoped runs from erasing sibling manifest rows.
- Created AUDIT.md at the phase directory enumerating all 5 on-disk manifest writers with D-06 column shape, contract preamble, D-08 migration policy, and PATCHED/LOCKED/DEFERRED dispositions for MANIFEST-12 acceptance.
- None.
- Authored CONFIGURING_V1_5.md as a single-file root-level guide walking the v1.5 pipeline end-to-end (vault-promote → --diagram-seeds → --init-diagram-templates → install excalidraw → /excalidraw-diagram), including a complete annotated `.graphify/profile.yaml` with all six built-in `diagram_types` plus a custom `decision-tree` entry, a reference-quality MCP tool integration section quoting `list_diagram_seeds` / `get_diagram_seed` / `_resolve_alias` verbatim from source, plus a one-line README cross-link and tracker-hygiene fixes for REQUIREMENTS.md and ROADMAP.md.

---

## v1.5 Diagram Intelligence & Excalidraw Bridge (Shipped: 2026-04-27)

**Phases completed:** 4 phases, 11 plans, 4 tasks

**Key accomplishments:**

- Extracted `knowledge_gaps()` from `report.py` into `analyze.py`, added verbatim 4-namespace `tag_taxonomy` + `profile_sync` to `profile.py`, shipped `question.md` + `quote.md` templates, and scaffolded 13-stub `test_vault_promote.py` — all 1449 tests green.
- Implemented pure in-memory `vault_promote.py` with 7-folder classifier (claimed-set priority dispatch, Questions bypass, code filter), full Ideaverse frontmatter renderer with EXTRACTED-only `related:`, and 3-layer taxonomy merge with auto-detected tech tags — 611 lines, 9 tests green, 1458 total suite passing.
- Atomic note writer with SHA-256 manifest, D-13 overwrite-self-skip-foreign policy, append-first import-log, and PyYAML-optional profile write-back wired to `graphify vault-promote` CLI.
- README.md
- Added `possible_diagram_seed` auto-tagging to `god_nodes()` and `_cross_community_surprises()`, introduced `detect_user_seeds()` reader for the `gen-diagram-seed[/type]` tag contract, and locked tag write-back to `graphify.merge.compute_merge_plan` via a grep denylist test.
- Shipped `graphify/seed.py` (13-step `build_all_seeds` orchestrator, 6-predicate D-05 layout heuristic, >60%-Jaccard single-pass dedup, max-20 auto-seed cap-before-I/O, deterministic sha256 element IDs, atomic-write + manifest-last lifecycle) and the `graphify --diagram-seeds [--graph <path>] [--vault <path>]` CLI flag; 27 new unit tests cover every must-have truth; full suite 1512 passed.
- Added `list_diagram_seeds` + `get_diagram_seed` as the MANIFEST-05 atomic pair — module-level never-raise cores, closure-local `_resolve_alias` per D-16, path-traversal defense via `_SEED_ID_RE`, budget-capped truncation, 12 unit tests, capability_tool_meta.yaml + server.json refreshed; full suite 1524 passed.
- Extended `profile.py` schema with a `diagram_types:` section (6 built-in defaults — architecture, workflow, repository-components, mind-map, cuadro-sinoptico, glossary-graph) and wired `seed.py::build_seed` as the first consumer — all four hunks landed atomically in one commit per PROF-02, with D-06 gating (`min_main_nodes` threshold) and D-07 tiebreak (highest-min wins; declaration-order fallback) both covered by tests.
- Added `graphify --init-diagram-templates [--force]` CLI and a new `graphify/excalidraw.py` module that writes one `.excalidraw.md` stub per profile `diagram_types` entry (6 built-in defaults from Plan 21-01). Every stub hardcodes `compress: false` with a valid Excalidraw scene JSON; every target passes through `validate_vault_path`. A new TMPL-06 denylist test enforces that `seed.py`, `export.py`, and `__main__.py` never write directly to vault `.md` files, and a lzstring-import scan locks the `compress: false` one-way door across the entire `graphify/` tree.
- 1. [Rule 3 — blocking] write_diagram stub during Task 3 commit

---

## v1.4 Agent Discoverability & Obsidian Workflows (Shipped: 2026-04-22)

**Delivered:** Graphify transitioned from a tool you run to a tool agents can find, trust, compose with, and improve in the background. Agent discoverability lands via an introspection-driven MCP capability manifest (static `server.json` + live `manifest.json` with drift detection) plus SEED-002 harness-memory export (SOUL/HEARTBEAT/USER triplet for the Claude harness). Obsidian workflow depth arrives through vault-scoped thinking commands (`/graphify-moc`, `/graphify-related`, `/graphify-orphan`, `/graphify-wayfind`) enforced behind a `propose_vault_note + approve` trust boundary. Graph quality over time comes from heterogeneous extraction routing (cheap/mid/expensive classes with cost ceiling), async background enrichment (four-pass overlay-only `enrichment.json` coordinated via `fcntl.flock`), focus-aware context zoom (`get_focus_context` BFS ego-graph), grounded two-stage chat with `{node_id, label, source_file}` citations, and SPAR-Kit graph-argumentation (4-lens rotation, blind-label shuffle, Jaccard early-stop).

**Phases completed:** 9 phase directories (7 core: 12, 13, 14, 15, 16, 17, 18 + 2 gap closure: 18.1, 18.2), 32 plans
**Timeline:** 2026-04-17 → 2026-04-22 (6 days)
**Codebase delta:** 155 files changed, +35,754 / −2,481 lines across 165 commits
**Requirements:** 72/86 P1+P2 shipped (14 P2 items intentionally deferred as documented carve-outs)
**Audit:** `.planning/milestones/v1.4-MILESTONE-AUDIT.md` — status `passed` (7/7 phases, 7/7 integration seams, 4/4 E2E flows)

### Key Accomplishments

1. **Agent Capability Manifest + SEED-002 Harness Export** (Phase 13) — Introspection-driven MCP 2025-11-25-compliant `server.json` (validated against JSON Schema draft 2020-12) plus runtime `manifest.json` merging 22 tool definitions with live graph stats / alias-map size / sidecar freshness. Every MCP response envelope carries `meta.manifest_content_hash` so agents detect drift between advertised and live surface. CI `graphify capability --validate` fails if the manifest drifts from `serve.py::list_tools()`. SEED-002 `graphify harness export --target claude` produces `graphify-out/harness/claude-{SOUL,HEARTBEAT,USER}.md` with byte-equal round-trip fidelity and an annotations allow-list (excluded by default).

2. **Heterogeneous Extraction Routing** (Phase 12) — Per-file AST-metric complexity classifier routes extraction across cheap/mid/expensive model tiers with parallel fan-out via a central semaphore + global 429 `threading.Event`. `GRAPHIFY_COST_CEILING` aborts pre-flight before any expensive LLM call; `model_id` participates in the cache key so re-running extraction with a different model produces a distinct cache entry. `routing.json` sidecar records a per-file `{class, model, endpoint, tokens_used, ms}` audit trail; `routing_models.yaml` is the single source of truth. HARD-gated `cache.py::file_hash()` key format for all downstream v1.4 phases.

3. **Async Background Enrichment** (Phase 15) — Four-pass background enricher (description → patterns → community summaries → staleness) writes overlay-only `enrichment.json` so `graph.json` stays read-only to enrichment forever. Event-driven via `watch.py` post-rebuild hook; coordinates with foreground `/graphify` runs through `fcntl.flock`; snapshot-pinned at process start for deterministic output. Every pass threads node IDs through `_resolve_alias` (D-16) and commits via atomic `.tmp` + `os.replace`.

4. **Obsidian Thinking Commands** (Phase 14) — Four vault-scoped slash commands (`/graphify-moc`, `/graphify-related`, `/graphify-orphan`, `/graphify-wayfind`) with `target: obsidian|code|both` frontmatter filtering. Write-path commands route through a mandatory `propose_vault_note` + `graphify approve` trust boundary. Plan 00 refactor migrated `_uninstall_commands()` from a hardcoded whitelist to a directory-scan, so future commands register automatically.

5. **Conversational Graph Chat + Focus-Aware Context** (Phases 17, 18) — `chat(query, session_id)` is structurally two-stage: Stage 1 emits tool calls only, Stage 2 composes the answer from tool results only (no fabrication). Every claim is cited to `{node_id, label, source_file}`; empty results return templated fuzzy suggestions. `get_focus_context(focus_hint)` returns a BFS ego-graph + community summary for a structured hint; pull-model only. Phase 18 codified the v1.3 CR-01 snapshot-double-nesting fix by renaming `snapshot.py::root` → `project_root` with a sentinel dataclass.

6. **Graph Argumentation Mode (SPAR-Kit)** (Phase 16) — `argue.py` populates a SPAR-Kit-style `ArgumentPackage`; `skill.md` orchestrates the LLM debate using the Phase 9 blind-label harness (per-round shuffle). Mandatory `{claim, cites: [node_id]}` schema rejects any fabricated node IDs at the envelope layer; round cap 6; `dissent` and `inconclusive` are valid outputs. `GRAPH_ARGUMENT.md` is advisory-only.

### Architectural Decisions Locked

- **D-02 MCP envelope** (Phase 13→all) — `text_body + "\n---GRAPHIFY-META---\n" + json(meta)` on every new MCP tool.
- **D-16 alias threading** (Phase 9→all) — every new handler threads IDs through `_resolve_alias`.
- **D-18 compose don't plumb** (Phase 11→all) — new tools compose `analyze.py` / `delta.py` / `snapshot.py`; only genuinely new algorithms earn modules (`enrich.py`, `argue.py`).
- **`graph.json` read-only** — all new state in atomic `.tmp` + `os.replace` sidecars; grep-CI guards that only `build.py` + `__main__.py` call `_write_graph_json`.
- **Snapshot double-nesting guard** (Phase 18) — `snapshot.py::root` → `project_root` rename with sentinel dataclass codifies v1.3 CR-01.
- **Recursion guard** — `argue_topic` declares `composable_from: []` HARD CONSTRAINT; `chat` never calls `chat` (two-stage tool-call separation).

### Known Deferred Items

- **SEED-002 inverse-import** — requires quarantine + prompt-injection defenses; v1.4 is export-only (OQ-4).
- **SEED-002 multi-harness schemas** — prove canonical pattern on `claude.yaml` first (OQ-5).
- **SEED-001 Tacit-to-Explicit Elicitation Engine** — revisit if onboarding/discovery becomes the theme.
- **Phase 19 Vault Promotion Script (Layer B)** — VAULT-01..05 moved to v1.5 via scope reconciliation 2026-04-23 (commit `0f6304b`).
- **14 P2 carve-outs** — ROUTE-08..10, OBSCMD-09..12, ARGUE-11..13, CHAT-10..12; documented as `deferred:` in originating plan SUMMARYs.

### Audit Trail

Initial audit 2026-04-22 20:32 returned `gaps_found`: Phase 13 missing all three verification artifacts + MANIFEST-06 metadata PARTIAL (`chat` + `get_focus_context` absent from `capability_tool_meta.yaml`). Phase 18.1 produced Phase 13 retrofit artifacts (commits `33f9f84`, `63d2480`, `1eda4be`); Phase 18.2 added missing tools with set-equality guard test (commits `59298c8`, `37aad87`, `012a90b`). Re-audit 2026-04-22 21:45 upgraded status to `passed`. Full timeline in `.planning/milestones/v1.4-MILESTONE-AUDIT.md`.

Known deferred items at close: 6 open artifacts (see STATE.md `## Deferred Items`).

### Archives

- Full phase detail: `.planning/milestones/v1.4-ROADMAP.md`
- Requirements: `.planning/milestones/v1.4-REQUIREMENTS.md`
- Milestone audit: `.planning/milestones/v1.4-MILESTONE-AUDIT.md`
- Per-phase artifacts: `.planning/milestones/v1.4-phases/`

---

## v1.3 Intelligent Analysis Continuation (Shipped: 2026-04-17)

**Delivered:** Graphify is production-viable on multi-source codebases — agents query it without blowing their token budget (Phase 9.2), extraction produces dramatically better graphs via cross-file semantic clustering + entity deduplication (Phase 10), and humans get a live thinking partner via seven MCP-backed slash commands (Phase 11). The static `GRAPH_TOUR.md` artifact concept was replaced with interactive `/context`, `/trace`, `/connect`, `/drift`, `/emerge`, `/ghost`, `/challenge` command files that ship via `graphify install`.

**Phases completed:** 3 phases (9.2, 10, 11), 19 plans
**Timeline:** 2026-04-16 → 2026-04-17 (2 days)
**Codebase delta:** 108 files changed, +24,057 / −161 lines (~16,481 LOC in `graphify/`, 16,529 LOC in `tests/`)
**Test suite:** 1,234 passing (up from 1,023 at v1.2), no regressions
**Requirements:** 14/15 satisfied (TOKEN-04 Bloom filter stretch — explicitly deferred per Phase 9.2 D-09)

### Key Accomplishments

1. **Progressive Graph Retrieval** (Phase 9.2) — Token-aware 3-layer MCP `query_graph` response (Layer 1 compact summaries, Layer 2 edge details, Layer 3 full subgraph) with `budget: int` parameter that clamps response size. Deterministic cardinality estimator emits a pre-execution estimate so agents can abort before paying for exploding multi-hop queries. Bidirectional BFS for depth ≥ 3 with 3-state status return (`ok` / `frontiers_disjoint` / `budget_exhausted`) replaces the old exponential-path implementation. New D-02 hybrid response envelope — `text_body + "\n---GRAPHIFY-META---\n" + json(meta)` with status codes — becomes the canonical MCP contract that Phases 10 and 11 inherit.

2. **Cross-File Semantic Extraction with Entity Deduplication** (Phase 10) — File clustering via import-graph connected components capped by top-level directory, with a token-budgeted soft cap (default 50,000 tokens per cluster) and import-topological ordering for cluster emission. New `graphify/dedup.py` merges fuzzy-matched (`difflib.SequenceMatcher ≥ 0.90`) and embedding-similar (`sentence-transformers all-MiniLM-L6-v2` cosine ≥ 0.85) entities with both signals required to agree. Edge re-routing with weight sum + confidence_score max + EXTRACTED > INFERRED > AMBIGUOUS enum precedence. MCP `query_graph` transparently redirects merged-away IDs with `resolved_from_alias` meta. Opt-in via `--dedup` flag; vault runs use separate `--obsidian-dedup` to control wikilink forward-mapping.

3. **Narrative Mode as Interactive Slash Commands** (Phase 11) — Five new MCP tools (`graph_summary`, `entity_trace`, `connect_topics`, `drift_nodes`, `newly_formed_clusters`) compose existing `analyze.py` / `delta.py` / `snapshot.py` primitives (D-18: no new graphify/ modules). Seven `.claude/commands/*.md` files (`/context`, `/trace`, `/connect`, `/drift`, `/emerge`, `/ghost`, `/challenge`) ship via extended `_PLATFORM_CONFIG` in `__main__.py` with `commands_enabled: True` on Claude Code + Windows and a `--no-commands` opt-out. Snapshot-chain walkers use explicit `del G_snap` memory discipline verified via weakref tests. All new tools inherit the Phase 9.2 envelope contract and Phase 10 alias-redirect contract.

4. **Quality gates caught production bugs early** — Phase 11's gsd-code-reviewer found 2 critical runtime bugs that all unit tests had missed: (a) `list_snapshots()` called with `graphify-out/` where it internally re-prepends `graphify-out/snapshots/` — all 4 snapshot-chain tools would have always returned `insufficient_history` in production (tests passed `tmp_path` directly and never tripped the double-nesting), and (b) `_cursor_install()` called without its required `project_dir` argument — `TypeError` on `graphify install --platform=cursor`. Both auto-fixed by `gsd-code-review-fix` with regression tests that match production path semantics.

### Architectural Decisions Locked

- **D-02 (Phase 9.2):** MCP responses use hybrid `text_body + SENTINEL + json(meta)` envelope with status codes — all future MCP tools inherit
- **D-09 (Phase 9.2):** TOKEN-04 Bloom filter + 2-3 hop materialized cache deferred beyond v1.3 — orthogonal to token economy, belongs in a performance milestone
- **D-16 (Phase 10):** MCP `query_graph` transparently redirects merged-away aliases — preserves agent callsites across dedup without breaking
- **D-18 (Phase 11):** No new `graphify/*.py` modules — Phase 11 is plumbing over existing primitives; new analysis algorithms belong in separate phases
- **BLOCKER 3 fix (Phase 11):** Windows platform has native `.claude/commands/` support; `_PLATFORM_CONFIG` treats it identically to Claude Code (not grouped with non-Claude platforms)

### Known Deferred Items

- **TOKEN-04** (stretch, Phase 9.2) — Bloom filter probe skip + 2-3-hop materialized cache. Deferred per D-09 to a future performance milestone where it's the focused scope rather than an add-on.
- **Sibling thinking-skill project** (conditional, Phase 11) — `/ghost` and `/challenge` shipped in graphify this cycle, but the door is preserved for migrating them to a companion skill if scope/voice diverges post-v1.3.

### Archives

- Full phase detail: `.planning/milestones/v1.3-ROADMAP.md`
- Requirements: `.planning/milestones/v1.3-REQUIREMENTS.md`
- Per-phase artifacts: `.planning/phases/09.2-*`, `.planning/phases/10-*`, `.planning/phases/11-*`

---

## v1.2 Intelligent Analysis & Cross-File Extraction (Shipped: 2026-04-15)

**Delivered:** LLM-assisted multi-perspective graph analysis via autoreason tournament (A/B/AB/blind-Borda rounds across 4 lenses), per-edge MCP query telemetry with hot-path strengthening and decay of unused edges, 2-hop A→C derived edges with INFERRED confidence, and hot/cold paths surfaced in `GRAPH_REPORT.md`. Analysis output is scoped to a dedicated `GRAPH_ANALYSIS.md` file — `GRAPH_REPORT.md` remains the mechanical metrics artifact (D-80 separation).

**Phases completed:** 3 phases (09, 09.1, 09.1.1), 9 plans
**Timeline:** 2026-04-14 → 2026-04-15 (2 days of code + 1 day of retroactive lifecycle cleanup 2026-04-15/16)
**Codebase delta:** 6 code files changed, +1083 / −6 lines (9.1.1 was planning-only, zero code delta)
**Test suite:** 1023 passing (up from 1000 at v1.1), no regressions
**Requirements:** 10/10 satisfied
**Audit:** Passed (10/10 REQ-IDs, 5/5 integration links WIRED, 3/3 E2E flows COMPLETE) — see `.planning/milestones/v1.2-MILESTONE-AUDIT.md`

### Key Accomplishments

1. **Autoreason Tournament Analysis** (Phase 9) — `render_analysis_context()` in `analyze.py` serializes the graph (nodes, edges, communities, god nodes, surprising connections) for tournament LLM prompts. `render_analysis()` in `report.py` produces the final `GRAPH_ANALYSIS.md` with per-lens sections, cross-lens synthesis (convergences + tensions), overall verdict, and tournament rationale (A/B/AB Borda scores). Tournament orchestration lives in `skill.md` (~260 lines, 6-step protocol A1–A6) with 4 independent lenses × 4 rounds × blind judges. "No finding" competes as a first-class Borda option — prevents hallucinated problems on clean graphs. 23 new tests (9 for context, 14 for report).

2. **Query Telemetry & Usage-Weighted Edges** (Phase 9.1) — `serve.py` records every MCP traversal to a `telemetry.json` sidecar with atomic `os.replace()` writes. Per-edge traversal counters feed a weight formula with exponential decay of unused edges. After N traversals of A→B→C, a direct A→C derived edge is proposed with `confidence=INFERRED`, `confidence_score=0.7`, and a `via` field naming the intermediate node. Neighbor-identity skip in `_check_derived_edges` prevents self-loops when `neighbor == a`. `report.py` emits a new "Usage Patterns" section with hot/cold paths classified via percentile thresholds.

3. **Pipeline Integration** (Phase 9.1, Plan 3) — Telemetry decay fires on every rebuild; usage data flows into all three `generate()` call sites and both rebuild points in `skill.md`. The graph's `agent-edges.json` and `annotations.jsonl` sidecars use the same atomic-write pattern as telemetry — no partial-write corruption possible mid-query.

4. **Retroactive Milestone Lifecycle Cleanup** (Phase 9.1.1) — Planning-only phase that closed three structural gaps found by `/gsd-audit-milestone`: (a) generated retroactive `09.1-VERIFICATION.md` from existing UAT/VALIDATION/SECURITY evidence, (b) created project-level `.planning/REQUIREMENTS.md` with 10 v1.2 REQ-IDs and a full traceability matrix back to file:line anchors, (c) reconciled scope contradictions across `ROADMAP.md` / `STATE.md` / `PROJECT.md` into a consistent narrow-v1.2 narrative, moving phases 9.2/10/11/12 into a new v1.3 milestone and renaming the old v1.3 → v1.4. Zero code changes; audit status upgraded `gaps_found → passed`.

### Architectural Decisions Locked

- **D-80: GRAPH_ANALYSIS.md is separate from GRAPH_REPORT.md** — tournament output never mutates the mechanical metrics artifact. Verified behaviorally in 09-HUMAN-UAT.md.
- **D-83: Every lens always appears as a section** — `report.py` iterates all lens_results with no filtering, so Clean verdicts (e.g., "3-0 unanimous for incumbent") are visible rather than silently omitted.
- **Blind Borda judges** — judge prompts use shuffled neutral labels (Analysis-1/2/3) with no role identity disclosed; shuffle rotation enforced across 3 judges.
- **Telemetry atomicity** — `telemetry.json`, `agent-edges.json`, and `annotations.jsonl` use `os.replace()` for all writes; no torn reads during concurrent MCP queries.
- **Narrow-scope milestone policy** — v1.2 closed when 2/6 originally-planned phases completed the intent. Remaining scope queued into v1.3 with clear origin anchoring rather than leaving v1.2 open indefinitely.

### Known Gaps / Deferred

- 09.1-SECURITY.md lacks structured YAML frontmatter (no `threats_total`/`threats_open` fields) — all 7 threats marked CLOSED in the table body but grep-based frontmatter extraction returns empty. Non-blocking tech debt.
- v1.2 was never formally instantiated via `/gsd-new-milestone`; REQUIREMENTS.md was created post-hoc by Phase 9.1.1, so SUMMARY.md files for 09 and 09.1 predate it and have no `requirements_completed` frontmatter. Non-blocking; audit accepted as documented.
- Remaining v1.2-origin scope (Progressive Graph Retrieval, Cross-File Semantic Extraction, Narrative Mode, Heterogeneous Extraction Routing) carried forward to v1.3.

### Archives

- `.planning/milestones/v1.2-ROADMAP.md` — full phase detail with plan breakdowns
- `.planning/milestones/v1.2-REQUIREMENTS.md` — 10 v1.2 REQ-IDs with traceability table (file:line evidence)
- `.planning/milestones/v1.2-MILESTONE-AUDIT.md` — final audit report (passed)

---

## v1.1 Context Persistence & Agent Memory (Shipped: 2026-04-13)

**Delivered:** Persistent, evolving context layer — graphify is no longer a one-shot graph builder. Agents can read AND write to the knowledge graph across sessions, users see how their corpus changes over time, and Obsidian vault notes survive round-trip re-runs with user content preservation.

**Phases completed:** 5 phases (6–8.2), 12 plans, ~117 commits
**Timeline:** 2026-04-12 → 2026-04-13 (2 days)
**Codebase delta:** 13,520 LOC across 26 Python modules (`graphify/`) — 3,663 insertions across 13 files
**Test suite:** 1,000 passing (up from 872 at v1.0)
**Requirements:** 25/25 satisfied
**Audit:** Passed (25/25 requirements, 5/5 phases, 25/25 integration, 3/3 flows)

### Key Accomplishments

1. **Graph Delta Analysis & Staleness** (Phase 6) — `snapshot.py` and `delta.py` modules deliver run-over-run comparison with `GRAPH_DELTA.md` output, snapshot persistence with FIFO retention, per-node provenance metadata (`extracted_at`, `source_hash`, `source_mtime`), three-state staleness classification (FRESH/STALE/GHOST), and community migration tracking. `graphify snapshot` CLI subcommand with `--name/--cap/--from/--to/--delta` flags.

2. **MCP Write-Back with Peer Modeling** (Phase 7) — 5 new MCP tools (`annotate_node`, `flag_node`, `add_edge`, `propose_vault_note`, `get_annotations`) with JSONL/JSON sidecar persistence, peer identity tracking (`peer_id`, `session_id`, `timestamp`), mtime-based graph reload, and startup compaction. `graph.json` is never mutated by agent tools.

3. **Human-in-the-Loop Proposals** (Phase 7, Plan 3) — `graphify approve` CLI subcommand for listing, approving, rejecting, and batch-processing agent-proposed vault notes. Proposals stage to `graphify-out/proposals/` with UUID4 filenames; vault is untouched until explicit approval.

4. **Obsidian Round-Trip Awareness** (Phase 8) — Content-hash manifest (`vault-manifest.json`) tracks what graphify wrote per note. On re-run, user-modified notes receive `SKIP_PRESERVE`. User sentinel blocks (`<!-- GRAPHIFY_USER_START -->` / `<!-- GRAPHIFY_USER_END -->`) provide inviolable preservation zones that survive even REPLACE strategy and `--force` mode. Dry-run enhanced with source annotations and summary preamble.

5. **Pipeline Integration & MCP Enhancements** (Phases 8.1–8.2) — Auto-snapshot and auto-delta on every `/graphify` run (skill.md wiring). Approve path threaded through vault manifest for user-modified detection. MCP `get_node` surfaces provenance fields and staleness classification. New `get_agent_edges` query tool with peer/session/node filtering.

### Architectural Decisions Locked

- peer_id defaults to `"anonymous"` — never derived from environment variables (security: prevents machine identity leaking into committed annotation files)
- `graph.json` is read-only pipeline ground truth — all agent state lives in JSONL/JSON sidecars
- Proposal filenames are server-generated UUID4 — never derived from agent-supplied input
- Content-hash manifest uses content-only SHA256 (no path) to avoid macOS symlink mismatch
- User sentinel blocks are inviolable even for REPLACE strategy — user content always wins
- Multiple USER_START/END pairs per note supported

### Known Gaps / Deferred

- **WIRING-01** (low): `_approve_and_write_proposal` hardcodes manifest path to `Path('graphify-out')` — doesn't respect `--out-dir` override
- 6 human verification items pending (real vault E2E tests for Phases 8 and 8.1)
- Template engine extensions (TMPL-01/02/03, CFG-02/03) deferred to v1.2+

### Archives

- `.planning/milestones/v1.1-ROADMAP.md` — full phase detail with success criteria and plan descriptions
- `.planning/milestones/v1.1-REQUIREMENTS.md` — 25 v1.1 requirements with traceability table
- `.planning/milestones/v1.1-MILESTONE-AUDIT.md` — audit report with integration verification

---

## v1.0 Ideaverse Integration — Configurable Vault Adapter (Shipped: 2026-04-11)

**Delivered:** Configurable output adapter that injects graphify knowledge graphs into any Obsidian vault framework via a declarative `.graphify/profile.yaml`. Replaces the monolithic `to_obsidian()` with a four-component pipeline (profile → mapping → templates → merge) and wires it behind two new CLI entry points. Backward-compatible when no vault profile exists (default profile emits Ideaverse ACE Atlas/ layout).

**Phases completed:** 5 phases, 22 plans, ~172 commits
**Timeline:** 2026-04-09 → 2026-04-11 (2 days)
**Codebase delta:** 11,620 LOC across 24 Python modules (`graphify/`) + 10,500 LOC across 33 test files (`tests/`)
**Test suite:** 872 passing (up from pre-milestone baseline)
**Requirements:** 31/33 satisfied (2 de-scoped via D-74 — see Out of Scope in archived requirements)

### Key Accomplishments

1. **Configurable vault profile system** (Phase 1: Foundation) — `.graphify/profile.yaml` discovery, deep-merge over built-in defaults, schema validation with actionable errors, path-traversal guard (`validate_vault_path`). Standalone `profile.py` module with no `export.py` coupling (D-16). Ships `_DEFAULT_PROFILE` constant producing Ideaverse ACE Atlas/ layout.

2. **Safety helpers + pre-existing bug fixes** (Phase 1 Plan 2) — `safe_filename` with NFC normalization (FIX-04) and 200-char length cap (FIX-05), `safe_tag` handling slashes / plus signs / digit-at-start (FIX-03), `safe_frontmatter_value` neutralizing YAML injection (FIX-01), and deterministic filename deduplication sorted on `(source_file, label)` (FIX-02). PyYAML added as optional `obsidian` extra.

3. **Template engine with placeholder substitution** (Phase 2: Template Engine) — `graphify/templates.py` delivers 6 built-in note types (MOC, Thing, Statement, Person, Source, Community Overview) via `string.Template.safe_substitute` with KNOWN_VARS + two-phase Dataview wrap. User template overrides in `.graphify/templates/` with built-in fallback on error. Wayfinder navigation callouts. Configurable filename conventions.

4. **Mapping engine with dual-evaluation classification** (Phase 3: Mapping Engine) — `graphify/mapping.py` classifies every graph node into exactly one note type via first-match-wins precedence: attribute rules (`compile_rules` + `_match_when`) override topology fallbacks (god nodes → Things, communities above threshold → MOCs, source files → Sources, default → Statements). Configurable community-to-MOC threshold; below-threshold communities collapse into sub-community callouts. Source-file extension routing.

5. **Merge engine with field-level policies** (Phase 4: Merge Engine) — `graphify/merge.py` delivers a pure `compute_merge_plan` (CREATE/UPDATE/SKIP_PRESERVE/SKIP_CONFLICT/REPLACE/ORPHAN actions) and atomic `apply_merge_plan` (`.tmp` + fsync + `os.replace`). 14-key built-in field-policy table (D-64), hand-rolled YAML frontmatter reader as strict inverse of `_dump_frontmatter`, D-67 sentinel block protection for graphify-owned body regions, content-hash skip for idempotent re-runs, D-72 orphan preservation. Four configurable merge strategies (`update` / `skip` / `replace`). 28/28 must-haves verified.

6. **Integration & CLI** (Phase 5: Integration & CLI) — Refactored `to_obsidian()` in `graphify/export.py` orchestrates the four-module pipeline behind a single entry point. `graphify --obsidian [--graph <path>] [--obsidian-dir <path>] [--dry-run]` and `graphify --validate-profile <vault-path>` land in `__main__.py:691-740`. `validate_profile_preflight` runs a four-layer preflight (schema → templates → dead-rules → path-safety). `format_merge_plan` + `split_rendered_note` public helpers support dry-run formatting. All 9 skill platform variants updated with the new pipeline patterns.

### Architectural Decisions Locked

- **D-73** — CLI is utilities-only; the skill is the pipeline driver. `graphify --obsidian` and `graphify --validate-profile` exist as direct utility entry points, but the full detect→extract→build→cluster→analyze→report→export pipeline runs via the skill (`graphify/skill.md`), not via a single CLI verb. Avoids rebuilding agent orchestration in Python.
- **D-74** — De-scope `.obsidian/graph.json` generation from `to_obsidian()` — the library entry point is a notes pipeline, not a vault-config-file manager. OBS-01 and OBS-02 moved to Out of Scope. The underlying `safe_tag()` invariant (slug form `community/<slug>`) remains and is anchored by `tests/test_profile.py::test_obs01_obs02_safe_tag_regression_anchor`.

Other locked decisions (D-01..D-72) are recorded in the archived phase contexts and in `.planning/milestones/v1.0-MILESTONE-AUDIT.md`.

### Verification

- All 5 phases have passing VERIFICATION.md artifacts (Phase 01 was retroactive to close the audit's evidence gap — commit `ffdb076`)
- 12/12 cross-phase integration key-links WIRED (verified by `gsd-integration-checker`)
- 5/5 primary user flows traced end-to-end (2 of them additionally live-verified against a 3-node graph fixture)
- Milestone audit run #2: `status: passed` — see `.planning/milestones/v1.0-MILESTONE-AUDIT.md`

### Known Gaps / Deferred

- **OBS-01, OBS-02** — `.obsidian/graph.json` read-merge-write management. Deliberately de-scoped via D-74. Revisit if a future release needs plugin-side graph.json management.
- **SUMMARY.md frontmatter schema drift** — Phases 2/3/5 used inconsistent field names (`requirements-completed`, `requirements`, `requirements_closed`) or omitted the field. Non-blocking; future housekeeping.
- **Nyquist validation artifacts** — Only Phase 1 has `VALIDATION.md`. Phases 2-5 shipped without Nyquist coverage. Advisory only per workflow config.

### Archives

- `.planning/milestones/v1.0-ROADMAP.md` — full phase detail (success criteria, plan descriptions, requirements mapping)
- `.planning/milestones/v1.0-REQUIREMENTS.md` — 33 v1 requirements with traceability table + Out of Scope for D-74 items
- `.planning/milestones/v1.0-MILESTONE-AUDIT.md` — audit runs 1 and 2, integration trace, 3-source cross-reference

---
