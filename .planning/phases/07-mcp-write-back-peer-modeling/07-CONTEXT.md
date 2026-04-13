# Phase 7: MCP Write-Back with Peer Modeling - Context

**Gathered:** 2026-04-12
**Status:** Ready for planning

<domain>
## Phase Boundary

Agents can annotate, flag, and propose notes on the knowledge graph across sessions, with full provenance and a human-in-the-loop for vault writes. This phase extends `serve.py` with mutation MCP tools, adds JSONL/JSON sidecar persistence for annotations and agent-edges, introduces peer identity and session tracking, and adds `propose_vault_note` with staging to `graphify-out/proposals/`. A new `graphify approve` CLI command enables human review before any vault write. `graph.json` is never mutated by MCP tools — all agent state lives in sidecars.

</domain>

<decisions>
## Implementation Decisions

### Annotation Persistence & Lifecycle
- **D-01:** Annotations persist forever across pipeline re-runs. If a referenced node ID disappears from the graph, the annotation becomes orphaned but is never automatically deleted. Agents/users clean up manually.
- **D-02:** Two separate sidecar files: `annotations.jsonl` for node annotations and flags (JSONL append-only), `agent-edges.json` for agent-discovered edges. Different data shapes justify separate files.
- **D-03:** JSONL compaction (dedup/pruning) runs once at MCP server startup only. Append-only during operation for crash safety. No compaction during writes.

### Peer Identity & Session Model
- **D-04:** `peer_id` is an explicit optional string parameter on every mutation tool. Defaults to `"anonymous"` if omitted. Never auto-detected from environment variables or machine identity.
- **D-05:** `session_id` is a server-generated UUID4 created when the MCP server starts. All mutations during that server lifetime share the same session_id. No caller coordination needed.
- **D-06:** Session-scoped views via filter parameters on `get_annotations` tool: optional `peer_id`, `session_id`, and `time_range` filters. Returns all annotations by default, filtered subset when params provided.

### Proposal Approval Flow
- **D-07:** `graphify approve` is a non-interactive CLI. Lists all pending proposals with summary. `graphify approve <id>` to accept, `graphify approve --reject <id>` to reject, `graphify approve --all` for batch accept. Composable, scriptable.
- **D-08:** Proposals carry full note spec: suggested filename, target folder, full markdown content, frontmatter dict, note_type, peer_id, session_id, timestamp, and a rationale field explaining why the agent proposed it.
- **D-09:** Proposals persist in `graphify-out/proposals/` until explicitly approved or rejected. No automatic expiry. User can clean up with `graphify approve --reject-all` or manually.
- **D-10:** Approved proposals go through the existing merge engine (`compute_merge_plan` + `apply_merge_plan`). The proposal's note_type and target folder are suggestions — the merge engine applies the vault profile, handles conflicts, and respects `preserve_fields`. Full v1.0 pipeline guarantees.
- **D-11:** `graphify approve` requires an explicit `--vault` flag for the target vault path. No implicit state discovery. Matches D-73 pattern of explicit CLI utilities.

### MCP Tool Surface Design
- **D-12:** Three separate mutation tools: `annotate_node` (free-text annotation), `flag_node` (importance: high/medium/low), `add_edge` (agent-inferred relationship). Clear intent per tool, matches MCP best practice.
- **D-13:** MCP server auto-reloads `graph.json` via mtime check before every read tool call. If mtime changed since last load, reload graph. Ensures agents always see fresh pipeline output. Negligible overhead (one `stat()` call).
- **D-14:** `propose_vault_note` accepts structured fields: `title`, `note_type`, `body_markdown`, `suggested_folder`, `tags[]`, `rationale`. The approval flow + merge engine assembles the final note with proper frontmatter from the vault profile. Agent doesn't need to know frontmatter format.
- **D-15:** Mutation tools return the full record written, including generated UUID `record_id`, `timestamp`, and `session_id`. Agent can reference records later for linking or context.
- **D-16:** Single-server assumption: only one MCP server instance runs at a time. Annotations loaded at startup + appended in-memory during the session. No multi-writer coordination needed.

### Claude's Discretion
- Internal JSONL record schema (exact field names beyond the required peer_id/session_id/timestamp)
- Compaction algorithm details (dedup strategy, handling of superseded annotations)
- `agent-edges.json` internal format (array vs object, indexing)
- Error messages for invalid node IDs, malformed inputs
- `_reload_if_stale()` implementation details (mtime caching, thread safety)
- Proposal JSON schema in `graphify-out/proposals/` (file naming, UUID format)

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Architecture & Existing Code
- `graphify/serve.py` — Current MCP server implementation (7 read-only tools, `_load_graph`, `_filter_blank_stdin`, handler dispatch pattern). All new tools extend this file.
- `graphify/security.py` — `sanitize_label()` must be applied to all agent-supplied strings in mutation tools. `validate_vault_path()` runs at proposal approval time.
- `graphify/cache.py` — `os.replace()` atomic write pattern; `file_hash()` for SHA256. Reuse for `agent-edges.json` atomic writes.
- `graphify/__main__.py` — CLI `main()` uses manual `sys.argv` parsing. New `approve` subcommand follows existing `snapshot` pattern from Phase 6.
- `graphify/merge.py` — `compute_merge_plan()` + `apply_merge_plan()` for proposal approval path. Approved proposals feed through this pipeline.
- `graphify/profile.py` — `load_profile()` for vault profile discovery at approval time.

### Research & Design
- `.planning/research/SUMMARY.md` — v1.1 research synthesis: Phase 7 architecture, critical pitfalls (#1 graph.json mutation, #3 concurrent write corruption, #6 peer identity leak, #7 arbitrary vault writes)
- `.planning/notes/repo-gap-analysis.md` — honcho peer model, letta-obsidian `propose_obsidian_note` staging pattern

### Requirements
- `.planning/REQUIREMENTS.md` — MCP-01 through MCP-10 acceptance criteria

### Prior Phase Context
- `.planning/phases/06-graph-delta-analysis-staleness/06-CONTEXT.md` — Phase 6 decisions (snapshot format, staleness model) that Phase 7 depends on

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `serve.py` handler dispatch pattern (`_handlers` dict + `@server.call_tool()` async wrapper) — new mutation tools plug into this same pattern
- `security.py::sanitize_label()` — apply to all agent-supplied strings (annotation text, edge relations, proposal content)
- `security.py::validate_vault_path()` — apply at proposal approval time to confine vault writes
- `cache.py` atomic write pattern (`os.replace(tmp, target)`) — reuse for `agent-edges.json` saves
- `merge.py::compute_merge_plan()` + `apply_merge_plan()` — proposal approval flow feeds approved notes through this pipeline
- `snapshot.py::save_snapshot()` — FIFO retention pattern could inform proposal cleanup (though proposals don't auto-expire per D-09)

### Established Patterns
- MCP tool registration via `@server.list_tools()` returning `types.Tool` objects with JSON Schema `inputSchema`
- Tool handlers are sync functions returning strings; async wrapper in `call_tool()` catches exceptions
- `_load_graph()` reads once at startup — will be extended with `_reload_if_stale()` mtime check
- `__main__.py` CLI uses `sys.argv` manual parsing, not argparse — new `approve` command follows this
- `graphify-out/` as standard output directory (`.gitignore`d, created at runtime)

### Integration Points
- **MCP server:** New mutation tools added to `serve.py` alongside existing read tools. Same `_handlers` dict pattern.
- **CLI:** `graphify approve` added as new subcommand in `__main__.py::main()`, following Phase 6's `snapshot` pattern.
- **Merge engine:** `graphify approve <id> --vault <path>` loads vault profile, constructs a note from proposal fields, feeds it through `compute_merge_plan` + `apply_merge_plan`.
- **Sidecar files:** `annotations.jsonl` and `agent-edges.json` live in `graphify-out/` alongside `graph.json`.

</code_context>

<specifics>
## Specific Ideas

No specific requirements — open to standard approaches

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>

---

*Phase: 07-mcp-write-back-peer-modeling*
*Context gathered: 2026-04-12*
