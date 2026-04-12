# Project Research Summary

**Project:** graphify v1.1 — Context Persistence & Agent Memory
**Domain:** Python CLI library — graph delta analysis, MCP write-back, Obsidian round-trip awareness
**Researched:** 2026-04-12
**Confidence:** HIGH

## Executive Summary

graphify v1.1 extends a proven pure-function batch pipeline with three persistence and write-back layers without restructuring the existing seven-stage core. All three features (graph delta analysis, MCP mutation tools, Obsidian round-trip awareness) integrate at the pipeline's edges only: new modules `snapshot.py` and `delta.py` attach after `export()`, extensions to `serve.py` add sidecar annotation files alongside the read-only graph, and extensions to `merge.py` add a `PARTIAL_UPDATE` action path that preserves user-authored content while refreshing graphify-managed sections. Zero existing pipeline stages need changes; all stack additions are stdlib-only.

The recommended approach is strict data separation between pipeline-owned state (`graph.json`) and agent-owned state (`annotations.jsonl`, `proposed_notes.json`, `vault-manifest.json`). The pipeline's JSON output is never mutated by MCP tools. This invariant is the load-bearing architectural constraint for v1.1 — violating it causes silent data loss when the pipeline re-runs. The patterns are well-validated against seven reference repositories: Honcho's peer model drives the annotation schema, CPR's summary+archive pattern drives delta report format, Letta-Obsidian's proposal queue drives the `propose_vault_note` flow, and Context Constitution's staleness-as-first-class principle drives per-node metadata design.

The primary risks are all in Phase 7 (MCP Write-Back): concurrent annotation writes need JSONL append semantics rather than read-modify-write JSON, peer identity must default to `"anonymous"` and never derive from environment variables, and `propose_vault_note` must write only to a staging directory with vault writes deferred until explicit human approval. The secondary risk is in Phase 6: staleness detection must use SHA256 hash comparison as the authoritative signal, not mtime alone, to handle file renames and clock skew. Phase 8 is the lowest risk — it extends existing well-tested merge engine logic with a new action type.

## Key Findings

### Recommended Stack

v1.1 requires no new dependencies. All features use existing required dependencies (`networkx`, `json`, `os`, `datetime`, `pathlib`, `hashlib` from stdlib) plus the existing optional `mcp` extra. Graph snapshots use `networkx.readwrite.json_graph.node_link_data(G, edges="links")` — the exact format already used in `serve.py`'s `_load_graph()` — so round-trip fidelity is guaranteed without new code. MCP mutation tools are plain Python async functions within the existing `serve.py` dispatcher; the MCP SDK imposes no restriction on handler-side state mutation (confirmed against official docs).

**Core technologies:**
- `networkx.readwrite.json_graph` (3.4.2, already installed): Graph snapshot serialization — verified round-trip of all node/edge attributes; 500-node graph serializes in 0.9ms, deserializes in 1.9ms
- `json` + `os.replace()` (stdlib): Annotation persistence and atomic writes — same pattern as `cache.py`; JSONL append preferred over full-file rewrite for concurrency safety
- `os.stat().st_mtime` / `hashlib.sha256` (stdlib): Two-tier staleness detection — fast mtime gate, hash confirmation on mismatch; ghost detection when `source_file` no longer exists
- `mcp` 1.27.0 (existing optional extra): MCP mutation tools via `call_tool` handler extension — additive, no structural change to `serve.py`
- `uuid.uuid4()` (stdlib): Session and proposal IDs — UUID4 only (never UUID1, which embeds MAC address)

### Expected Features

**Must have (table stakes — Phase 6):**
- Graph snapshot persistence: `graphify-out/snapshots/{timestamp}.json`, FIFO retention (default 10), automatic pruning on every write
- Node-level diff: added / removed / community-migrated sets from set arithmetic on `G.nodes()`
- Edge-level diff: added / removed edges from set arithmetic on `G.edges()`
- `GRAPH_DELTA.md`: two-tier output — summary section (~500 words, agent-context-sized) + archive JSON (full machine-readable diff, not auto-loaded)
- Per-node `extracted_at` (ISO-8601 UTC timestamp at build time) and `source_modified_at` (`os.stat().st_mtime`) metadata
- Staleness flag: nodes where hash comparison shows source changed since extraction; `GHOST` status for nodes whose `source_file` no longer exists

**Must have (table stakes — Phase 7):**
- `annotate_node`, `tag_node`, `flag_importance` MCP tools writing to `annotations.jsonl` (JSONL, append-only)
- `add_edge` MCP tool writing to `agent-edges.json` sidecar
- Peer identity: `peer_id` (explicit config or `"anonymous"`) and `session_id` (UUID4) on all write tools
- `get_annotations` MCP tool: read path for accumulated knowledge
- `propose_vault_note` MCP tool: writes only to `graphify-out/proposals/{uuid}.json`; human approval required via `graphify approve-proposal {id}` CLI

**Must have (table stakes — Phase 8):**
- `vault-manifest.json`: content hashes of all graphify-written notes, updated atomically after each `apply_merge_plan`
- User-modified note detection: manifest hash comparison on re-run; `user_modified: bool` flag on `MergeAction`
- `PARTIAL_UPDATE` merge action: rewrites frontmatter + refreshes sentinel-delimited sections; leaves user content outside sentinels intact
- User-space sentinel block (`<!-- GRAPHIFY_USER_START -->` / `<!-- GRAPHIFY_USER_END -->`) in all built-in templates, inviolable on UPDATE

**Should have (competitive differentiators — v1.1.x after validation):**
- `graphify diff <snapshot-a> <snapshot-b>` CLI command for arbitrary snapshot comparison
- Session-scoped graph views via `start_session` MCP tool and session-filtered annotation reads
- `get_peer_summary` MCP tool (annotation footprint per peer_id)
- Community migration grouping in delta report (top 3 migrations by (old_community, new_community) pair)
- ORPHAN user-modification tracking in vault-manifest
- Confidence decay metadata (timestamp arithmetic: <30d=fresh, 30-90d=aging, >90d=stale)
- Annotation TTL pruning: `graphify annotations prune --older-than 90d` (explicit, never auto)

**Defer (v1.2+):**
- LLM-assisted annotation enrichment — adds latency and token cost at query time
- Real-time vault watching for change detection — event loop conflicts with watch.py
- User-content-aware conflict resolution distinguishing user-edited sentinel content from corrupted sentinel

### Architecture Approach

v1.1 is additive at the pipeline's edges. The seven-stage pipeline (`detect -> extract -> build -> cluster -> analyze -> report -> export`) is untouched. Two new modules (`snapshot.py`, `delta.py`) attach after `export()`; `serve.py` gains four mutation tool handlers and annotation/proposal state loaded at startup; `merge.py` gains `detect_user_edits()`, `merge_with_user_blocks()`, and the `PARTIAL_UPDATE` action; `__main__.py` gains a `snapshot` subcommand. No existing module is restructured. Phases 6 and 7 have no cross-dependency and can be built in parallel; Phase 8 depends on Phase 7's proposal flow via existing merge engine hooks.

**Major components:**
1. `snapshot.py` (NEW, ~200 lines) — Save/load/diff graph snapshots; attach staleness metadata (`extracted_at`, `source_modified_at`, `source_hash`, `stale`, `ghost`); FIFO pruning on every write; reads `cache.py` mtime read-only
2. `delta.py` (NEW, ~150 lines) — Render diff dict into GRAPH_DELTA.md (summary tier) and `delta/{timestamp}-archive.json` (archive tier); CPR summary+archive pattern; no LLM calls
3. `serve.py` extensions — Four new MCP write tools (`annotate_node`, `add_edge`, `flag_importance`, `propose_vault_note`); JSONL append to `annotations.jsonl`; proposal staging to `graphify-out/proposals/`; mtime-based graph reload check (`_reload_if_stale`)
4. `merge.py` extensions — `detect_user_edits()` and `merge_with_user_blocks()` functions; `PARTIAL_UPDATE` action type; `graphify_body_hash` frontmatter field for drift detection; `vault-manifest.json` written atomically after each `apply_merge_plan`

### Critical Pitfalls

1. **MCP mutations corrupt graph.json** — Never mutate `G` in-place from MCP handlers; write ONLY to `annotations.jsonl` sidecar; add `_reload_if_stale()` mtime check so read tools see fresh pipeline output after a re-run; highest-priority design decision for Phase 7

2. **annotations.json concurrent write corruption** — Use JSONL append-only (one JSON object per line); append is atomic for small writes on all major filesystems; no locking required; compact (deduplicate) at server startup only; never read-modify-write the full JSON file

3. **propose_vault_note allows arbitrary vault writes** — Tool writes ONLY to `graphify-out/proposals/{uuid}.json` (never to vault); filename is server-generated UUID4; `validate_vault_path()` from `security.py` runs at approval time, not at proposal time; content sanitization runs at approval time too

4. **Staleness detection misses file renames and clock skew** — Use SHA256 hash as the authoritative staleness signal (matching `cache.py`); mtime is a fast first gate only; check `source_file` existence and report `GHOST` status when the file no longer exists

5. **Snapshot directory grows unbounded** — Prune inside `save_snapshot()` on every write (not as a separate optional command); default cap = 10 snapshots; compress full snapshots via `gzip` (stdlib); test: write 15 snapshots, assert only 10 remain

6. **Peer identity leaks machine data** — `peer_id` defaults to `"anonymous"`, never `os.environ["USER"]` or `socket.gethostname()`; `session_id` is `uuid.uuid4()` only; add `graphify-out/` to `.gitignore` template installed by `graphify install`

7. **User note body overwritten on re-run** — Extend merge engine with `PARTIAL_UPDATE` action; detect user modifications via `graphify_body_hash` stored in frontmatter; preserve all content outside sentinel markers verbatim; notes without sentinel markers fall through to v1.0 UPDATE behavior (backward compatible)

## Implications for Roadmap

Based on research, suggested phase structure:

### Phase 6: Graph Delta Analysis
**Rationale:** No dependency on Phase 7 or Phase 8; delivers standalone value (agents can see what changed between runs); validates the snapshot format before write-back tools depend on it; lowest implementation risk (pure stdlib, no MCP changes)
**Delivers:** `graphify-out/snapshots/` with FIFO retention; `GRAPH_DELTA.md` (summary tier); `delta/{timestamp}-archive.json` (archive tier); `graphify snapshot` CLI subcommand; per-node `extracted_at`, `source_modified_at`, `source_hash`, `stale`, `ghost` attributes; staleness report in delta summary
**Addresses:** Graph snapshot persistence (P1), node/edge diff (P1), GRAPH_DELTA.md (P1), per-node metadata (P1), staleness flagging (P2)
**Avoids:** Pitfall 1 (unbounded snapshot growth — prune in `save_snapshot()`); Pitfall 5 (meta-staleness — hash-based staleness, ghost detection)
**New modules:** `snapshot.py`, `delta.py`
**Extended modules:** `__main__.py` (snapshot subcommand)

### Phase 7: MCP Write-Back with Peer Modeling
**Rationale:** Can be built in parallel with Phase 6 (no shared dependency); must complete before Phase 8 because Phase 8's `propose_vault_note` approval flow uses the merge engine; highest security surface area — peer identity and staging architecture must be locked before any annotation tool is written
**Delivers:** `annotate_node`, `tag_node`, `flag_importance`, `add_edge` MCP tools; `annotations.jsonl` JSONL sidecar; `propose_vault_note` with staging to `graphify-out/proposals/`; `graphify approve-proposal` CLI; `get_annotations` read tool; peer_id + session_id on all write operations
**Uses:** `uuid.uuid4()` for session/proposal IDs; `sanitize_label()` from `security.py` on all agent-supplied strings; `os.replace()` atomic write pattern from `cache.py`
**Implements:** MCP WriteTools component in `serve.py`; Proposal Queue (Letta-Obsidian pattern); Append-Only Persistence pattern
**Avoids:** Pitfall 2 (MCP mutation breaks read-only invariant — `_reload_if_stale`, no `G` mutation); Pitfall 3 (concurrent write corruption — JSONL append); Pitfall 6 (peer identity leak — `"anonymous"` default, UUID4 only); Pitfall 7 (arbitrary vault writes — staging-only, UUID4 filenames, approval-time validation)

### Phase 8: Obsidian Round-Trip Awareness
**Rationale:** Depends on Phase 7's `propose_vault_note` approval flow (uses `apply_merge_plan` under the hood); extends existing v1.0 sentinel block grammar — lowest new-code footprint; protects user vault content from overwrites, which is the trust-critical feature for vault-writing workflows
**Delivers:** `vault-manifest.json` (content hashes of all graphify-written notes); user-modified detection on re-run; `user_modified: bool` flag in merge plan dry-run output; `PARTIAL_UPDATE` merge action; user-space sentinel block in all built-in templates; graceful degradation when manifest is absent
**Implements:** RoundTripDetector component in `merge.py`; Sentinel-Block Round-Trip pattern
**Avoids:** Pitfall 4 (merge conflict on user-modified body — `PARTIAL_UPDATE` action, `graphify_body_hash` frontmatter field, backward-compatible fallback for notes without sentinels)

### Phase Ordering Rationale

- Phase 6 first because it has no dependencies and delivers visible delta output that validates the snapshot format before Phase 7 consumes it
- Phase 7 second because `propose_vault_note` (a Phase 7 deliverable) is required for Phase 8's vault write approval flow; the security architecture must be established before any vault interaction
- Phase 8 last because it depends on both the merge engine (v1.0, already built) and the proposal approval flow (Phase 7); bugs here have the highest user-visible impact (overwriting curated vault content)
- Phases 6 and 7 can be implemented in parallel since they share no module-level dependency; they only converge in Phase 8

### Research Flags

Phases likely needing deeper research during planning:
- **Phase 7:** JSONL compaction performance — benchmark compaction time for large annotation files (>10K records) before committing to startup-time compaction
- **Phase 7:** MCP session identity transport — MCP stdio does not carry session metadata in transport headers; caller-supplied peer_id/session_id is the only option; needs explicit documentation and fallback test coverage
- **Phase 8:** `graphify_body_hash` frontmatter round-trip — confirm PyYAML does not add unexpected quoting or folding that would break hash comparison on subsequent reads

Phases with standard patterns (skip research-phase):
- **Phase 6:** Snapshot serialization, diff computation, and pruning are verified stdlib patterns; `node_link_data` round-trip confirmed against live NetworkX 3.4.2; no research phase needed
- **Phase 6:** Staleness metadata schema is directly derived from `cache.py`'s existing SHA256 pattern
- **Phase 8:** Sentinel block grammar already established in v1.0 `merge.py`; `PARTIAL_UPDATE` is an additive action type on a well-tested code path

## Confidence Assessment

| Area | Confidence | Notes |
|------|------------|-------|
| Stack | HIGH | All decisions verified against live Python 3.10+ runtime; `node_link_data` round-trip benchmarked; MCP SDK mutation capability confirmed against official docs; no speculative dependencies |
| Features | HIGH | Grounded in codebase audit of `serve.py`, `merge.py`, `cache.py`, `export.py` and cross-checked against 7 reference repos and 12 articles |
| Architecture | HIGH | Based on direct reading of `serve.py`, `merge.py`, `cache.py`, `PROJECT.md`, and gap analysis; all components integrate at clearly identified pipeline boundaries |
| Pitfalls | HIGH | All 7 critical pitfalls grounded in actual graphify code paths with specific line references and validated external repo patterns; recovery strategies included |

**Overall confidence:** HIGH

### Gaps to Address

- **JSONL compaction performance:** Research recommends startup-time compaction but does not benchmark against large annotation files. Validate during Phase 7 implementation with a 10K-record annotation file; target <500ms compaction time.
- **PyYAML frontmatter round-trip for `graphify_body_hash`:** Confirm PyYAML does not add unexpected quoting or folding on the hash string field. Add a round-trip test in Phase 8.
- **Snapshot compression load time:** PITFALLS.md recommends gzip-compressed full snapshots; STACK.md benchmarks uncompressed only. Verify gzip load time for a 5K-node compressed snapshot stays under the 50ms target.
- **`graphify-out/` in .gitignore:** Required before Phase 7 ships. Confirm `graphify install` already creates or updates `.gitignore` and add this entry if absent — this is a pre-Phase 7 prerequisite.

## Sources

### Primary (HIGH confidence)
- `graphify/serve.py` — verified read-only MCP server architecture, `_load_graph()` pattern, `call_tool` dispatcher; line 22: `json_graph.node_link_graph(data, edges="links")`
- `graphify/merge.py` — MergeAction vocabulary, sentinel block grammar, field policy table, `compute_merge_plan` flow
- `graphify/cache.py` — SHA256 file hash pattern, `os.replace()` atomic write, `file_hash()` function
- `graphify/security.py` — `sanitize_label`, `validate_graph_path`, `safe_filename`, `validate_vault_path`
- Live NetworkX 3.4.2 runtime — `node_link_data` round-trip verified; 500-node serialize 0.9ms, deserialize 1.9ms; set arithmetic diff verified
- `modelcontextprotocol.io/docs/concepts/tools` (official MCP docs) — tool handlers are plain async functions; no mutation restriction
- `pip3 index versions mcp` — confirmed mcp 1.27.0 is current latest

### Secondary (MEDIUM confidence)
- `.planning/notes/repo-gap-analysis.md` — 7 reference repos: honcho (peer model, session scoping), context-constitution (staleness-first), cpr (summary+archive delta pattern), letta-obsidian (propose_obsidian_note staging, human approval), llm-council, spar-kit, smolcluster
- `.planning/notes/april-research-gap-analysis.md` — 12 articles including Sarah Wooders / Letta on memory harness, Harrison Chase on memory ownership
- `.planning/PROJECT.md` — v1.1 active requirements list, milestone goal, key decisions, constraints

### Tertiary (LOW confidence)
- Python stdlib `uuid` module docs — UUID1 MAC address risk, UUID4 randomness guarantee
- Python `fcntl` advisory lock docs — cited as fallback option; JSONL append strategy preferred

---
*Research completed: 2026-04-12*
*Ready for roadmap: yes*
