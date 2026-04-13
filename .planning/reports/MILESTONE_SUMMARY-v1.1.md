# Milestone v1.1 — Project Summary

**Generated:** 2026-04-13
**Purpose:** Team onboarding and project review

---

## 1. Project Overview

**Graphify** is a Claude Code skill backed by a Python CLI library that transforms any input (code, docs, papers, images) into a knowledge graph with clustered communities, exported as HTML, JSON, Obsidian vault notes, and audit reports.

**v1.0** (shipped 2026-04-11) delivered a configurable Obsidian vault adapter — a profile-driven pipeline that reads `.graphify/profile.yaml` from a target vault and produces properly-structured notes with frontmatter, wikilinks, folder placement, and safe merge semantics. Five phases, 22 plans, 872 tests.

**v1.1 — Context Persistence & Agent Memory** makes graphify a *persistent, evolving context layer* rather than a one-shot graph builder. It adds three capabilities:

1. **Graph delta analysis** — Compare runs, see what changed, know how fresh each node is
2. **MCP write-back** — Agents can annotate, flag, and propose notes on the graph across sessions
3. **Obsidian round-trip** — User edits to graphify-injected vault notes survive re-runs

**Origin:** Gap analysis against 12 articles + 7 external repositories (llm-council, spar-kit, smolcluster, context-constitution, honcho, cpr, letta-obsidian). See `.planning/notes/april-research-gap-analysis.md` and `.planning/notes/repo-gap-analysis.md`.

**Status:** All 3 core phases (6–8) complete. 2 gap-closure phases (8.1, 8.2) planned for integration wiring and MCP query enhancements. 985 tests passing.

---

## 2. Architecture & Technical Decisions

### New Modules (v1.1)

| Module | Lines | Role |
|--------|-------|------|
| `graphify/snapshot.py` | ~149 | Graph snapshot persistence: save, load, prune (FIFO), list |
| `graphify/delta.py` | ~261 | Set-arithmetic diff, three-state staleness, GRAPH_DELTA.md rendering |

### Extended Modules

| Module | Changes |
|--------|---------|
| `graphify/serve.py` | 5 new MCP mutation/query tools, JSONL/JSON sidecar persistence, peer/session identity, mtime-based graph reload, startup compaction |
| `graphify/merge.py` | Vault manifest I/O, content-hash user-modified detection, user sentinel block parser/preservation, format_merge_plan round-trip enhancements |
| `graphify/export.py` | `to_obsidian()` extended with `force=` and manifest threading |
| `graphify/__main__.py` | `graphify snapshot` + `graphify approve` subcommands, `--force` flag |
| `graphify/extract.py` | Per-node provenance injection (`extracted_at`, `source_hash`, `source_mtime`) |

### Key Decisions

- **Decision:** Snapshots use `node_link_data` JSON serialization, one file per snapshot with FIFO retention (default 10)
  - **Why:** Matches existing `to_json()` format; atomic writes via `os.replace()`; bounded disk usage
  - **Phase:** 6 (D-01, D-02, D-03)

- **Decision:** GRAPH_DELTA.md uses summary+archive pattern — concise narrative for agent context, full tables for human search
  - **Why:** Agents need loadable summaries (~20-40 lines); humans need searchable detail
  - **Phase:** 6 (D-04, D-05), inspired by EliaAlberti/cpr

- **Decision:** Three-state staleness (FRESH/STALE/GHOST) with mtime fast-gate before SHA256 check
  - **Why:** Mtime avoids disk I/O for unchanged files; SHA256 is authoritative when mtime differs
  - **Phase:** 6 (D-08, D-09, D-10)

- **Decision:** `graph.json` is never mutated by MCP tools — all agent state lives in JSONL/JSON sidecars
  - **Why:** Pipeline owns ground truth; agent mutations in sidecars prevents silent data loss on re-run
  - **Phase:** 7 (architectural invariant, MCP-10)

- **Decision:** `peer_id` defaults to `"anonymous"` string literal — never derived from environment
  - **Why:** Prevents leaking machine identity into annotation files that may be committed to public repos
  - **Phase:** 7 (D-04), inspired by plastic-labs/honcho peer model

- **Decision:** JSONL append-only for annotations, compacted once at MCP server startup
  - **Why:** Crash-safe writes (no read-modify-write race); startup compaction keeps file bounded
  - **Phase:** 7 (D-03)

- **Decision:** `propose_vault_note` stages to `graphify-out/proposals/` — vault untouched until `graphify approve`
  - **Why:** Human-in-the-loop for vault writes; trust boundary between agent and user content
  - **Phase:** 7 (D-07, D-08), inspired by letta-ai/letta-obsidian approval pattern

- **Decision:** User-modified notes receive SKIP_PRESERVE (entire note untouched) rather than partial merge
  - **Why:** Simpler, safer — user content always wins. Sentinel blocks provide granular opt-in preservation zones for `--force` mode
  - **Phase:** 8 (D-07)

- **Decision:** Content-only SHA256 hash for vault manifest (no path in hash)
  - **Why:** Avoids macOS symlink hash mismatch (`/private/tmp` vs `/tmp`) that `cache.file_hash()` would cause
  - **Phase:** 8 (D-04)

- **Decision:** User sentinel blocks (`<!-- GRAPHIFY_USER_START/END -->`) are inviolable even under `--force` and REPLACE strategy
  - **Why:** Users who explicitly mark preservation zones must never lose that content, regardless of merge mode
  - **Phase:** 8 (D-08)

---

## 3. Phases Delivered

| Phase | Name | Status | One-Liner |
|-------|------|--------|-----------|
| 6 | Graph Delta Analysis & Staleness | Complete | Snapshot persistence, set-arithmetic diff, three-state staleness, GRAPH_DELTA.md, `graphify snapshot` CLI |
| 7 | MCP Write-Back with Peer Modeling | Complete | 5 MCP mutation/query tools, JSONL/JSON sidecars, peer/session identity, `propose_vault_note`, `graphify approve` CLI |
| 8 | Obsidian Round-Trip Awareness | Complete | Content-hash manifest, user-modified detection, user sentinel blocks, `--force` flag, dry-run source annotations |
| 8.1 | Approve & Pipeline Wiring | Planned | Thread vault manifest through approve path; wire `auto_snapshot_and_delta` into skill pipeline |
| 8.2 | MCP Query Enhancements | Planned | Provenance fields in `get_node`; `get_agent_edges` query tool |

### Phase 6 — Graph Delta Analysis & Staleness (3 plans, 2026-04-12)

**Plan 01:** Snapshot module (`save_snapshot`, `load_snapshot`, `list_snapshots`, FIFO pruning) + provenance metadata injection in `extract.py`. Two new files: `graphify/snapshot.py`, `tests/test_snapshot.py`.

**Plan 02:** Delta computation (`compute_delta` with set-arithmetic diff, `classify_staleness` for FRESH/STALE/GHOST, `render_delta_md` with summary+archive pattern). Two new files: `graphify/delta.py`, `tests/test_delta.py`.

**Plan 03:** CLI wiring — `graphify snapshot` subcommand with `--name`, `--cap`, `--from`, `--to`, `--delta` flags. `auto_snapshot_and_delta()` pipeline helper for zero-friction post-build usage.

**Verification:** 5/5 truths verified. 40 tests. 8/8 DELTA requirements satisfied.

### Phase 7 — MCP Write-Back with Peer Modeling (3 plans, 2026-04-13)

**Plan 01:** Sidecar persistence (JSONL append for annotations, atomic JSON for agent-edges) + 4 mutation tools (`annotate_node`, `flag_node`, `add_edge`, `get_annotations`) + mtime-based graph reload + startup compaction. `propose_vault_note` registered as placeholder.

**Plan 02:** `propose_vault_note` tool implementation — UUID4-named JSON proposals in `graphify-out/proposals/` with full D-08 field set and sanitization.

**Plan 03:** `graphify approve` CLI — list/approve/reject/batch operations, path-confined via `validate_vault_path`, approved proposals routed through merge engine.

**Verification:** 10/10 must-haves verified. 57 tests. 10/10 MCP requirements satisfied.

### Phase 8 — Obsidian Round-Trip Awareness (3 plans, 2026-04-13)

**Plan 01:** Vault manifest I/O (`_content_hash`, `_load_manifest`, `_save_manifest`, `_build_manifest_from_result`), MergeAction extension (`user_modified`, `has_user_blocks`, `source` fields), user-modified detection in `compute_merge_plan`.

**Plan 02:** User sentinel block parser (`_parse_user_sentinel_blocks`, `_extract_user_blocks`, `_restore_user_blocks`), preservation in `_synthesize_file_text` for both UPDATE and REPLACE strategies, `has_user_blocks` manifest field resolution.

**Plan 03:** CLI `--force` flag, manifest/force threading through `to_obsidian()`, `format_merge_plan` D-11 source annotations (`[user]`/`[both]`) and D-12 user-modified preamble.

**Verification:** 5/5 truths verified (automated). 3 items require human vault testing. 33 tests. 7/7 TRIP requirements satisfied.

---

## 4. Requirements Coverage

### Graph Delta Analysis & Staleness (DELTA-01 through DELTA-08)

- ✅ **DELTA-01**: Compare current graph run against previous run — GRAPH_DELTA.md with added/removed/changed
- ✅ **DELTA-02**: Snapshots persist to `graphify-out/snapshots/` with FIFO retention (default 10)
- ✅ **DELTA-03**: Every extracted node carries `extracted_at` and `source_hash` metadata
- ✅ **DELTA-04**: Three-state staleness: FRESH/STALE/GHOST
- ✅ **DELTA-05**: Summary+archive pattern in GRAPH_DELTA.md
- ✅ **DELTA-06**: Community migration tracked across runs
- ✅ **DELTA-07**: `graphify snapshot` CLI saves named snapshot without full pipeline re-run
- ✅ **DELTA-08**: Per-node connectivity delta (degree change, new/lost edges) in delta output

### MCP Write-Back with Peer Modeling (MCP-01 through MCP-10)

- ✅ **MCP-01**: `annotate_node` MCP tool, persisted across restarts
- ✅ **MCP-02**: `flag_node` MCP tool (high/medium/low), persisted
- ✅ **MCP-03**: `add_edge` MCP tool in `agent-edges.json` sidecar (never `graph.json`)
- ✅ **MCP-04**: JSONL append persistence for annotations (crash-safe)
- ✅ **MCP-05**: peer_id + session_id + timestamp on every record; peer_id defaults to "anonymous"
- ✅ **MCP-06**: `propose_vault_note` stages to `graphify-out/proposals/`
- ✅ **MCP-07**: `graphify approve` CLI for proposal review
- ✅ **MCP-08**: Annotations queryable via MCP with peer/session/time filters
- ✅ **MCP-09**: Session-scoped graph views via MCP
- ✅ **MCP-10**: `graph.json` never mutated by MCP tools

### Obsidian Round-Trip Awareness (TRIP-01 through TRIP-07)

- ✅ **TRIP-01**: `vault-manifest.json` written atomically with content hashes per note
- ✅ **TRIP-02**: User-modified notes detected via hash comparison on re-run
- ✅ **TRIP-03**: User-modified notes receive SKIP_PRESERVE (note: spec says UPDATE_PRESERVE_USER_BLOCKS, but D-07 decided SKIP_PRESERVE — intent fully satisfied)
- ✅ **TRIP-04**: User sentinel blocks (`<!-- GRAPHIFY_USER_START/END -->`) provide explicit preservation zones
- ✅ **TRIP-05**: `--dry-run` shows user modification status per note
- ✅ **TRIP-06**: User content always wins — sentinel blocks never overwritten
- ✅ **TRIP-07**: Per-note modification source in merge plan output

**Coverage:** 25/25 requirements satisfied at module level.

### Milestone Audit Verdict

Status: **tech_debt** — all requirements met; 4 cross-phase integration gaps found and addressed with gap-closure phases 8.1 and 8.2.

| Gap | Severity | Summary | Fix Phase |
|-----|----------|---------|-----------|
| INT-01 | High | Approve flow bypasses vault manifest | 8.1 |
| INT-02 | Medium | Skill pipeline never calls `auto_snapshot_and_delta` | 8.1 |
| INT-03 | Low | MCP `get_node` missing provenance fields | 8.2 |
| INT-04 | Low | Agent-edges not queryable via MCP | 8.2 |

---

## 5. Key Decisions Log

### Phase 6 Decisions

| ID | Decision | Rationale |
|----|----------|-----------|
| D-01 | Snapshots contain graph + communities + metadata only | Minimal, comparable, fast to save/load |
| D-02 | Single JSON file per snapshot | Atomic save, easy diffing |
| D-03 | Timestamp-based naming with optional `--name` label | Sortable, human-readable, CLI-friendly |
| D-04 | Summary+archive pattern for GRAPH_DELTA.md | Agent context window fits summary; humans search archive |
| D-08 | Provenance injected at extraction time | Data born with freshness metadata |
| D-10 | Staleness is metadata-only — pipeline unchanged | No behavior coupling; agents consume at their discretion |
| D-12 | `graphify snapshot` reads existing graph.json, no re-run | Matches D-73 (CLI = utility) |

### Phase 7 Decisions

| ID | Decision | Rationale |
|----|----------|-----------|
| D-01 | Annotations never auto-deleted | Orphaned annotations are safe; manual cleanup preferred over data loss |
| D-04 | peer_id from explicit parameter only | Security: no env var leakage |
| D-05 | session_id is server-generated UUID4 | No caller coordination needed |
| D-07 | `graphify approve` is non-interactive CLI | Composable, scriptable, D-73 pattern |
| D-10 | Approved proposals go through full merge engine | v1.0 pipeline guarantees (profile, conflicts, preserve_fields) apply |
| D-14 | `propose_vault_note` accepts structured fields, not raw markdown | Merge engine + profile assembles the final note |
| D-16 | Single-server assumption | Simplicity; no multi-writer coordination |

### Phase 8 Decisions

| ID | Decision | Rationale |
|----|----------|-----------|
| D-03 | Multiple USER_START/END pairs per note | Simpler for users, equally simple to implement |
| D-04 | Content-only SHA256 (no path in hash) | Avoids macOS symlink hash mismatch |
| D-07 | Hash mismatch → SKIP_PRESERVE (entire note) | User content always wins; sentinels provide granular opt-in |
| D-08 | Sentinel blocks inviolable even under REPLACE and --force | Explicit preservation zones must be absolute |
| D-10 | `--force` overrides D-07 but respects D-08 | Full refresh possible while keeping sentinel content |
| D-11 | Source annotation omitted for default "graphify" | v1.0 dry-run output unchanged |
| D-12 | Preamble only when user_modified > 0 | Backward compatible with v1.0 plans |

---

## 6. Tech Debt & Deferred Items

### Integration Gaps (addressed by phases 8.1 and 8.2)

- **INT-01 (High):** `graphify approve` path doesn't pass manifest to merge engine — user-modified detection, manifest updates, and SKIP_PRESERVE all bypassed for approved proposals. Fix: thread manifest params through `_approve_and_write_proposal`.
- **INT-02 (Medium):** `auto_snapshot_and_delta` never called by skill.md or `--obsidian` path — users must manually run `graphify snapshot --delta`. Fix: wire into skill.md pipeline.
- **INT-03 (Low):** MCP `get_node` doesn't return provenance fields — agents can't query node freshness via MCP. Fix: extend `_tool_get_node`.
- **INT-04 (Low):** Agent-edges not queryable via MCP — agents that called `add_edge` can't retrieve them. Fix: add `get_agent_edges` tool.

### Documentation Debt

- Phase 7 and 8 SUMMARY.md files missing `requirements_completed` frontmatter field
- TRIP-03 wording mismatch between REQUIREMENTS.md ("UPDATE_PRESERVE_USER_BLOCKS") and implementation (SKIP_PRESERVE) — D-07 documents the decision but spec not updated

### Human Verification Pending

Phase 8 has 3 manual verification items awaiting real vault testing:
1. Edit a graphify-injected note in Obsidian, re-run `--obsidian`, verify SKIP_PRESERVE behavior
2. Add user sentinel blocks, re-run with `--force`, verify sentinel content preserved
3. Run `--dry-run` on vault with modified notes, verify preamble and source annotations

### Deferred Features (v1.2+)

- Conditional template sections (`{{#if_god_node}}`) — TMPL-01
- Loop blocks for connections (`{{#connections}}`) — TMPL-02
- Custom Dataview query templates per note type — TMPL-03
- Profile includes/extends mechanism — CFG-02
- Per-community template overrides — CFG-03

### Retrospective Lessons (from v1.0, applicable to v1.1+)

1. Run phase verification at completion time, not later
2. Standardize SUMMARY.md frontmatter field names
3. Every de-scope needs three coordinated updates (REQUIREMENTS, PROJECT, regression test)
4. Always audit twice (1→reconcile→2 pattern)
5. Parallel worktree executors need "plans are tracked" post-condition

---

## 7. Getting Started

### Run the project

```bash
pip install -e ".[all]"          # Install with all optional deps
graphify --help                   # Verify CLI
pytest tests/ -q                  # Run test suite (985 tests)
```

### Key directories

| Path | Contents |
|------|----------|
| `graphify/` | Core library — 24 Python modules |
| `tests/` | 33 test files, pure unit tests |
| `graphify-out/` | Runtime output (graph.json, snapshots/, proposals/, annotations.jsonl) |
| `.planning/` | GSD planning artifacts (roadmap, phases, requirements) |

### v1.1-specific entry points

| Command / Function | What it does |
|-------------------|-------------|
| `graphify snapshot` | Save a named snapshot of the current graph |
| `graphify snapshot --from X --to Y` | Compare two specific snapshots |
| `graphify approve` | List/approve/reject agent-proposed vault notes |
| `graphify --obsidian --force` | Re-run Obsidian export, refreshing even user-modified notes |
| `graphify --obsidian --dry-run` | Preview merge plan with user-modification annotations |
| `graphify/snapshot.py` | Snapshot persistence + `auto_snapshot_and_delta()` |
| `graphify/delta.py` | `compute_delta()`, `classify_staleness()`, `render_delta_md()` |
| `graphify/serve.py` | MCP server with mutation tools (annotate, flag, add_edge, propose) |
| `graphify/merge.py` | Vault manifest, user sentinel blocks, round-trip awareness |

### Where to look first

- **New contributor to v1.1:** Start with `graphify/snapshot.py` (149 lines, cleanest new module) → `graphify/delta.py` (261 lines) → `graphify/serve.py` mutations section
- **Understanding the merge engine:** `graphify/merge.py` — search for `_content_hash`, `_load_manifest`, `_parse_user_sentinel_blocks`
- **MCP tools:** `graphify/serve.py` — look for `_tool_annotate_node`, `_tool_propose_vault_note`, `_tool_get_annotations`

### Tests

```bash
pytest tests/test_snapshot.py tests/test_delta.py -q     # Phase 6 (40 tests)
pytest tests/test_serve.py tests/test_approve.py -q       # Phase 7 (57 tests)
pytest tests/test_merge.py -q                              # Phase 8 (143 tests)
pytest tests/ -q                                           # Full suite (985 tests)
```

---

## Stats

- **Timeline:** 2026-04-12 → 2026-04-13 (2 days)
- **Phases:** 3 complete / 5 total (8.1 and 8.2 planned for gap closure)
- **Plans:** 9 complete
- **Commits:** 96
- **Files changed:** 265 (57 source files)
- **Test suite:** 872 → 985 tests (+113 new tests)
- **New modules:** 2 (`snapshot.py`, `delta.py`)
- **Contributors:** Safi, silveimar
- **Requirements:** 25/25 satisfied at module level
- **Integration score:** 21/25 (4 gaps addressed by phases 8.1, 8.2)
