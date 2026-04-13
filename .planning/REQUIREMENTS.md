# Requirements: graphify v1.1

**Defined:** 2026-04-12
**Core Value:** Graphify can inject knowledge into any Obsidian vault framework driven entirely by a declarative vault-side profile

## v1.1 Requirements

Requirements for v1.1 Context Persistence & Agent Memory. Each maps to roadmap phases 6–8.

### Graph Delta Analysis & Staleness

- [x] **DELTA-01**: User can compare current graph run against previous run and see added/removed/changed nodes and edges in `GRAPH_DELTA.md`
- [x] **DELTA-02**: Graph snapshots persist to `graphify-out/snapshots/` after each pipeline run with automatic retention (default: keep last 10)
- [x] **DELTA-03**: Every extracted node carries `extracted_at` (ISO timestamp) and `source_hash` (SHA256 of source file at extraction time) metadata
- [x] **DELTA-04**: Nodes have three-state staleness: FRESH (hash matches source), STALE (hash mismatch), GHOST (source file deleted/renamed)
- [x] **DELTA-05**: `GRAPH_DELTA.md` uses summary+archive pattern: concise summary section (loadable into agent context) plus full structural diff section (searchable but not loaded)
- [x] **DELTA-06**: Community migration is tracked: which nodes moved between communities across runs
- [x] **DELTA-07**: `graphify snapshot` CLI command saves an explicit named snapshot without requiring a full pipeline re-run
- [x] **DELTA-08**: Connectivity change metrics per node (degree delta, new/lost edges) are included in delta output

### MCP Write-Back with Peer Modeling

- [x] **MCP-01**: MCP server exposes `annotate_node` tool that adds a text annotation to any node by ID, persisted across server restarts
- [x] **MCP-02**: MCP server exposes `flag_node` tool that marks a node's importance (high/medium/low), persisted across server restarts
- [x] **MCP-03**: MCP server exposes `add_edge` tool for agent-discovered relationships, stored in `agent-edges.json` sidecar (never in pipeline `graph.json`)
- [x] **MCP-04**: All annotations persist in `graphify-out/annotations.jsonl` using JSONL append (crash-safe, no read-modify-write race)
- [x] **MCP-05**: Every annotation record includes `peer_id`, `session_id`, and `timestamp`; `peer_id` defaults to `"anonymous"` (never derived from environment)
- [x] **MCP-06**: MCP server exposes `propose_vault_note` tool that stages a proposed note to `graphify-out/proposals/` with human approval required before vault write
- [x] **MCP-07**: `graphify approve` CLI command lists pending proposals and allows user to approve/reject/edit before writing to vault
- [x] **MCP-08**: Annotations and agent-edges are queryable via MCP: filter by peer, session, or time range
- [x] **MCP-09**: Session-scoped graph views: MCP tool to retrieve annotations relevant to a specific session context
- [x] **MCP-10**: `graph.json` is never mutated by MCP tools — pipeline output is read-only ground truth; all agent state lives in sidecars

### Obsidian Round-Trip Awareness

- [x] **TRIP-01**: `apply_merge_plan` writes `vault-manifest.json` recording content hash per note at merge time
- [x] **TRIP-02**: On `--obsidian` re-run, graphify detects which notes the user has modified since last merge (hash comparison against manifest)
- [x] **TRIP-03**: User-modified notes receive `UPDATE_PRESERVE_USER_BLOCKS` merge action: graphify-managed sections refresh, user-authored content blocks preserved
- [x] **TRIP-04**: User-space sentinel blocks (`<!-- GRAPHIFY_USER_START -->` / `<!-- GRAPHIFY_USER_END -->`) provide explicit preservation zones users can add to any note
- [x] **TRIP-05**: `--dry-run` output shows which notes have user modifications and what the merge plan would do with them
- [x] **TRIP-06**: Conflict resolution: user content always wins — graphify never overwrites content between user sentinel blocks
- [x] **TRIP-07**: Merge plan output includes per-note modification source (graphify-generated, user-modified, or both) for audit trail

## v2 Requirements

Deferred to future milestones. Tracked but not in v1.1 roadmap.

### Template Engine Extensions (from v1.0)

- **TMPL-01**: Conditional template sections (`{{#if_god_node}}...{{/if}}` guards)
- **TMPL-02**: Loop blocks for connections in templates (`{{#connections}}...{{/connections}}`)
- **TMPL-03**: Custom Dataview query templates per note type in profile
- **CFG-02**: Profile includes/extends mechanism (compose profiles from fragments)
- **CFG-03**: Per-community template overrides

### Multi-Perspective Analysis (v1.2)

- **ANLZ-01**: Configurable analysis lenses (security, architecture, complexity, onboarding) with 3-stage council protocol
- **ANLZ-02**: Cross-file semantic extraction for related file clusters
- **ANLZ-03**: Narrative mode codebase walkthrough
- **ANLZ-04**: Heterogeneous extraction routing by file complexity

### Agent Discoverability & Workflows (v1.3)

- **DISC-01**: Machine-readable agent capability manifest for MCP server
- **DISC-02**: Obsidian thinking commands (`/trace`, `/connect`, `/drift`, `/emerge`)
- **DISC-03**: Async background graph enrichment
- **DISC-04**: Graph argumentation mode (structured LLM debate over graph)
- **DISC-05**: Conversational graph chat (natural-language graph querying)
- **DISC-06**: Focus-aware graph context (scope queries to current file neighborhood)

## Out of Scope

| Feature | Reason |
|---------|--------|
| Real-time vault watching for v1.1 | Scope creep; conflicts with existing `watch.py` code-only watcher; defer to v1.2+ |
| Full two-way sync (reading user prose back into graph nodes) | Scope explosion; graphify injects structure, doesn't ingest user prose |
| MCP tools that mutate `graph.json` directly | Architectural invariant: pipeline owns graph.json; violating this causes silent data loss on re-run |
| Auto-applying `propose_vault_note` without human approval | Data integrity risk; trust violation; letta-obsidian reference pattern requires explicit approval |
| Peer identity derived from environment variables | Security risk: leaks machine identity into annotation files that may be committed to public repos |
| `.obsidian/graph.json` management | De-scoped in v1.0 D-74; revisit only if user demand emerges |

## Traceability

Which phases cover which requirements. Updated during roadmap creation.

| Requirement | Phase | Status |
|-------------|-------|--------|
| DELTA-01 | Phase 6 | Complete |
| DELTA-02 | Phase 6 | Complete |
| DELTA-03 | Phase 6 | Complete |
| DELTA-04 | Phase 6 | Complete |
| DELTA-05 | Phase 6 | Complete |
| DELTA-06 | Phase 6 | Complete |
| DELTA-07 | Phase 6 | Complete |
| DELTA-08 | Phase 6 | Complete |
| MCP-01 | Phase 7 | Complete |
| MCP-02 | Phase 7 | Complete |
| MCP-03 | Phase 7 | Complete |
| MCP-04 | Phase 7 | Complete |
| MCP-05 | Phase 7 | Complete |
| MCP-06 | Phase 7 | Complete |
| MCP-07 | Phase 7 | Complete |
| MCP-08 | Phase 7 | Complete |
| MCP-09 | Phase 7 | Complete |
| MCP-10 | Phase 7 | Complete |
| TRIP-01 | Phase 8 | Complete |
| TRIP-02 | Phase 8 | Complete |
| TRIP-03 | Phase 8 | Complete |
| TRIP-04 | Phase 8 | Complete |
| TRIP-05 | Phase 8 | Complete |
| TRIP-06 | Phase 8 | Complete |
| TRIP-07 | Phase 8 | Complete |

**Coverage:**
- v1.1 requirements: 25 total
- Mapped to phases: 25
- Unmapped: 0 ✓

---
*Requirements defined: 2026-04-12*
*Last updated: 2026-04-12 — traceability confirmed after roadmap creation (25/25 mapped)*
