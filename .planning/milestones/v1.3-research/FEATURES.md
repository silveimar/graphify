# Feature Research: v1.1 Context Persistence & Agent Memory

**Domain:** Graph delta analysis, MCP write-back with peer modeling, Obsidian round-trip awareness
**Researched:** 2026-04-12
**Confidence:** HIGH — grounded in codebase audit of existing graphify modules (merge.py, serve.py, cache.py, export.py), cross-checked against repo-gap-analysis.md (7 repos: honcho, context-constitution, cpr, letta-obsidian, llm-council, spar-kit, smolcluster) and april-research-gap-analysis.md (12 articles).

---

## Scope Reminder

This research is scoped exclusively to v1.1 new features. V1.0 shipped its full Obsidian vault adapter (profile, templates, mapping, merge engine). The three v1.1 phases are:

- **Phase 6 — Graph Delta Analysis:** Snapshot persistence, run-over-run diff, per-node staleness metadata, GRAPH_DELTA.md
- **Phase 7 — MCP Write-Back with Peer Modeling:** Mutation tools on the MCP server, peer identity tracking, session-scoped views, `propose_vault_note`
- **Phase 8 — Obsidian Round-Trip Awareness:** Detect user-modified note bodies on re-run, extend merge engine to preserve user-authored content blocks without sentinel reliance

---

## Feature Landscape

### Phase 6: Graph Delta Analysis

#### Table Stakes (Users Expect These)

Features that any "persistent graph" tool must have. Missing these means the graph is still treated as a one-shot export with no run history.

| Feature | Why Expected | Complexity | Depends On | Notes |
|---------|--------------|------------|------------|-------|
| Graph snapshot persistence | Tools like CPR, honcho, and letta all store prior state; without it, every re-run is amnesiac | LOW | `export.py` JSON output, `pathlib` | Write `graphify-out/snapshots/{timestamp}.json` (copy of `graph.json`) after each successful build. Naming: ISO-8601 UTC timestamp. Keep N snapshots (configurable, default 10) with simple FIFO eviction. No new deps — stdlib only. |
| Node-level diff (new/removed/migrated nodes) | Agents and users need to see what changed — new modules, deleted files, concept drift | MEDIUM | `nx.Graph` node iteration, prior snapshot | Compare current `graph.json` node IDs against latest snapshot. Produce three sets: added, removed, and community-migrated. Community migration = same node_id, different community_id. |
| Edge-level diff (new/removed edges, confidence changes) | Edges capture relationships; appearing or disappearing edges signal architectural change | MEDIUM | Same as node diff | Compare edge `(source, target, relation)` tuples. Track edges where confidence changed from EXTRACTED to INFERRED or vice versa. |
| `GRAPH_DELTA.md` output | Agents need the delta as readable context, not raw JSON. CPR's summary+archive pattern: one file loaded into context, one archived for search. | MEDIUM | Node diff + edge diff | Two-section output: **Summary** (counts, top movers, biggest community shifts — loaded by agent context) and **Full Diff** (complete per-node/edge changes — searchable but not loaded). Write to `graphify-out/GRAPH_DELTA.md`. |
| Per-node `extracted_at` metadata | Context Constitution: staleness is first-class. Agents must know when each node was last extracted to trust or question graph claims. | LOW | `datetime`, node attribute dict | Stamp `extracted_at: ISO-8601` on every node at build time. Store in graph JSON. No visual output needed — available to MCP and delta analysis. |
| Per-node `source_modified_at` metadata | Pairing extraction time with source-file mtime allows staleness detection: "this node was extracted 3 months ago from a file that was modified 2 weeks ago" | LOW | `os.stat().st_mtime`, `detect.py` file list | At extraction time, record `source_modified_at` from `os.stat(path).st_mtime_ns` (nanosecond precision, OS-portable) converted to ISO-8601. |

#### Differentiators (Competitive Advantage)

| Feature | Value Proposition | Complexity | Depends On | Notes |
|---------|-------------------|------------|------------|-------|
| Staleness flagging in delta report | Highlights nodes where `source_modified_at > extracted_at` (source changed, node not re-extracted due to cache hit or skip) — surfaces trust gaps | MEDIUM | Per-node metadata above + cache.py hash comparison | A node is "stale" when its source file mtime is newer than its `extracted_at`. Report stale node count in GRAPH_DELTA.md summary section. |
| Community migration tracking | Shows that "the auth cluster merged with the user cluster" — more meaningful than raw node counts | MEDIUM | Node diff + community_id comparison | Group migrated nodes by (old_community, new_community) pair. Show top 3 migrations in summary. |
| Configurable snapshot retention | CPR: user controls when compression happens. Here: user controls how many snapshots to keep. | LOW | Snapshot persistence above | `graphify snapshot --keep N` or profile setting `snapshots.keep: 10`. FIFO eviction when limit reached. |
| `graphify diff <snapshot-a> <snapshot-b>` CLI command | Power users and CI pipelines need to compare arbitrary snapshots, not just current vs. latest | MEDIUM | Snapshot persistence + diff engine | Load two snapshots, run same diff logic, output GRAPH_DELTA.md equivalent. Flag `--format json` for machine consumption. |
| Confidence decay metadata | Nodes that haven't been re-extracted in N days get a `confidence_decay: low/medium/high` field — signals that LLM-extracted relationships may have drifted | LOW | `extracted_at` + configurable decay schedule | Compute at delta time: `days_since_extraction = (now - extracted_at).days`. Thresholds: `<30=fresh`, `30-90=aging`, `>90=stale`. No model changes needed — purely timestamp arithmetic. |

#### Anti-Features

| Anti-Feature | Why Avoid | Alternative |
|--------------|-----------|-------------|
| Automatic snapshot on every build (non-configurable) | Storage balloons on large repos with frequent re-runs; user has no control | Snapshot only on explicit `graphify snapshot` command OR on flag `--snapshot`. The skill can call this after a successful build. |
| Full graph stored in GRAPH_DELTA.md | Delta reports loaded into agent context must be small. A 10K-node graph as delta text overflows context windows. | Summary section: ~50 lines max. Full diff: separate `graphify-out/snapshots/delta-{timestamp}.md` written but not auto-loaded. |
| Binary snapshot format | Binary diffs are unreadable, can't be grep'd, and add complexity with no benefit at graphify's scale | Always JSON. Gzip compression optional for large graphs via `snapshots.compress: true` in profile. |
| Snapshot-to-snapshot semantic diffing (LLM-assisted) | Interesting but defers to Phase 9 (multi-perspective analysis). LLM diff of graph changes is Phase 15 territory. | Structural diff only: node IDs, community assignments, edge triples. No LLM calls in Phase 6. |

---

### Phase 7: MCP Write-Back with Peer Modeling

#### Table Stakes (Users Expect These)

Any agent memory layer must be writable. A read-only MCP server means agents can't build knowledge through graphify.

| Feature | Why Expected | Complexity | Depends On | Notes |
|---------|--------------|------------|------------|-------|
| `annotate_node` MCP tool | Honcho, letta all allow agents to annotate entities. Agents need to attach reasoning ("this module is the authentication bottleneck") to nodes. | MEDIUM | serve.py MCP server + new `annotations.json` | Write `{node_id, text, peer_id, session_id, timestamp}` to `graphify-out/annotations.json`. Append-only. No graph mutation — annotations are a sidecar. Returns the annotation ID. |
| `add_edge` MCP tool | Agents discover relationships not in the AST (e.g., "this function conceptually depends on that design decision doc"). Without write-back, that insight is lost. | MEDIUM | serve.py + graph mutation | Add an edge to the loaded graph with `confidence: INFERRED`, `source: "agent"`, and the peer metadata. Persist to a new `graphify-out/agent-edges.json` sidecar (not mixed into graph.json, which is pipeline output). |
| `flag_importance` MCP tool | Agents identifying god nodes worth human attention ("this is the load-bearing abstraction"). Surfaces high-value nodes for human review. | LOW | serve.py + annotations.json | Writes `{node_id, importance: "high/critical", note, peer_id, timestamp}` to annotations.json. Separate `importance` key so it can be filtered independently. |
| Peer identity tracking on all write tools | Honcho's core innovation: WHO annotated what matters. Without peer identity, multiple agents produce undifferentiated noise. | LOW | All mutation tools above | Every write tool accepts `peer_id: str` (agent name or session identifier) and `session_id: str`. Both stored in annotations.json alongside every mutation. Peer identity is caller-supplied — no auth, no verification (trust boundary is local filesystem). |
| Annotation persistence across re-runs | Annotations must survive the pipeline re-running and overwriting graph.json. Otherwise agents lose memory on every build. | LOW | `annotations.json` as separate file from `graph.json` | Pipeline never touches `annotations.json`. On MCP server load, read both `graph.json` (pipeline output) and `annotations.json` (agent sidecar). Merge at query time: when `get_node` is called, append annotations for that node_id. |
| `tag_node` MCP tool | Lightweight categorization without full annotation text. Agents tagging nodes with context ("reviewed", "needs-attention", "auth-critical"). | LOW | serve.py + annotations.json | Writes `{node_id, tags: [...], peer_id, session_id, timestamp}`. Tags are additive — subsequent calls add to the set, don't replace. |

#### Differentiators (Competitive Advantage)

| Feature | Value Proposition | Complexity | Depends On | Notes |
|---------|-------------------|------------|------------|-------|
| Session-scoped graph views | Honcho's session scoping: an agent querying within session X sees the same starting state regardless of what other sessions have annotated since. Prevents annotation noise from leaking across sessions. | MEDIUM | serve.py session context + annotations.json | MCP `start_session` tool returns a `session_id`. Read tools accept optional `session_id` to scope annotation retrieval to that session. No graph mutation required — just filters annotation reads. |
| `get_annotations` MCP tool | Agents need to query what has been learned about a node across sessions — the accumulated knowledge layer. Without this, write-back has no read path. | LOW | annotations.json + serve.py | Returns all annotations for a node_id (or all nodes if unspecified), filterable by peer_id, session_id, tag, date range. |
| `propose_vault_note` MCP tool with human approval | Letta-obsidian's `propose_obsidian_note` pattern: agents can materialize graph insights as vault notes, but NEVER without human review. Closes the loop: agent reads graph → discovers insight → proposes vault note → human approves → note enters vault. | HIGH | serve.py + merge.py `compute_merge_plan` + new approval mechanism | Agent calls `propose_vault_note({title, body, note_type, community})`. Graphify writes a pending proposal to `graphify-out/proposals/{uuid}.json`. Human reviews via `graphify proposals list` and `graphify proposals apply {uuid}`. The apply step runs the merge engine (compute_merge_plan + apply_merge_plan) against the target vault. NEVER auto-apply. |
| `get_peer_summary` MCP tool | Shows what a specific agent/peer has contributed across all sessions — their annotation footprint on the graph. Enables audit and cleanup. | LOW | annotations.json filtering by peer_id | Returns annotation count, node coverage, most-annotated nodes, session history for a given peer_id. |
| Annotation expiry / TTL | Annotations from stale sessions (e.g., a coding assistant session 6 months ago) become noise. TTL allows automatic pruning. | LOW | annotations.json + timestamp comparison | `graphify annotations prune --older-than 90d` CLI command. Does not auto-prune — explicit command only. |

#### Anti-Features

| Anti-Feature | Why Avoid | Alternative |
|--------------|-----------|-------------|
| MCP tools that mutate `graph.json` directly | graph.json is pipeline output. Mutating it means re-runs silently overwrite agent work. | Sidecar files: `annotations.json` for notes/tags, `agent-edges.json` for agent-discovered edges. Pipeline never touches sidecars. |
| Authentication / peer identity verification | Trust boundary is the local filesystem. Adding auth adds complexity without protecting against the actual threat (a local user). | Caller-supplied peer_id with no verification. Document the trust model. |
| Streaming / real-time annotation feed | Interesting but out of scope. MCP is request-response; streaming is a different protocol. | Request-response only. If real-time annotation feed is needed (v1.3+), that's a different architecture. |
| Auto-applying `propose_vault_note` | Agents writing vault notes without human review is a data integrity risk. One bad LLM reasoning step overwrites carefully curated vault content. | Always require explicit human approval step. The proposal lives in `graphify-out/proposals/` until approved. |
| LLM-assisted annotation enrichment (auto-summarizing annotations) | Phase 15 territory. Doing LLM calls inside the MCP server creates latency and token cost at query time. | Store raw annotations. If summarization is needed, do it as a batch offline pass in a future phase. |
| Per-node graph mutation (add/remove nodes via MCP) | Node identity is derived from source file AST. Agent-invented nodes have no source_file, breaking the extraction schema. | `add_edge` is sufficient for agent-discovered relationships. Nodes remain pipeline-owned. |

---

### Phase 8: Obsidian Round-Trip Awareness

#### Table Stakes (Users Expect These)

Any tool that writes to a human-curated vault must not destroy user edits on re-run. V1.0 already preserves frontmatter fields via `preserve_fields`. V1.1 extends this to body content.

| Feature | Why Expected | Complexity | Depends On | Notes |
|---------|--------------|------------|------------|-------|
| User-authored body content block detection | Users add content below graphify's generated sections (personal notes, connections to other ideas, inline comments). V1.0's sentinel blocks protect graphify-managed content. V1.1 must also protect user content OUTSIDE sentinels. | MEDIUM | merge.py `_parse_sentinel_blocks` + existing body merge logic | The merge engine already uses sentinel block markers (`<!-- GRAPHIFY_START:block_name -->` / `<!-- GRAPHIFY_END:block_name -->`). Content outside these markers is "user space". Extend `_merge_body_blocks` to: 1) detect content outside all sentinel blocks, 2) classify it as user-authored, 3) preserve it verbatim on UPDATE. Already partially true — the current engine splices only sentinel blocks, leaving surrounding content. Audit and add explicit test coverage. |
| Detect notes modified since last graphify run | Without knowing which notes the user edited, every UPDATE triggers full re-render, creating unnecessary churn and potential overwrites. | MEDIUM | merge.py + `cache.py` file_hash pattern | Record a content hash of each written note in `graphify-out/vault-manifest.json` (path → hash). On re-run, compare current note hash against manifest. If different → user has modified it; apply extra-conservative merge (never overwrite user-space content, only refresh sentinel blocks). If same → safe to do full UPDATE per v1.0 logic. |
| Merge plan surfacing of user-modified notes | Users need visibility into which of their edited notes will be touched on re-run, so they can review before applying. V1.0's `--dry-run` outputs action types. V1.1 should add a "user-modified" flag. | LOW | MergeAction + vault-manifest.json above | Add `user_modified: bool` to MergeAction (or as a new conflict_kind). `--dry-run` output shows `[user-modified]` badge next to UPDATE actions for notes the user has edited. |
| Vault manifest persistence | The `vault-manifest.json` must survive between runs to enable modification detection. Single source of truth for "what graphify last wrote." | LOW | `pathlib`, `json`, security.py path validation | Write `graphify-out/vault-manifest.json` as `{relative_vault_path: content_hash}` after each `apply_merge_plan` call. Update incrementally (don't rewrite whole file on partial re-runs). |

#### Differentiators (Competitive Advantage)

| Feature | Value Proposition | Complexity | Depends On | Notes |
|---------|-------------------|------------|------------|-------|
| User-content-aware conflict resolution | When a user has modified a graphify-managed sentinel block, the current engine raises `SKIP_CONFLICT (malformed_sentinel)`. V1.1 should distinguish: user edited INSIDE a sentinel (conflict) vs. user added content OUTSIDE sentinels (safe, preserve it). | MEDIUM | merge.py `_parse_sentinel_blocks` + `_locate_sentinel_block_ranges` | Current `_MalformedSentinel` covers structural corruption of sentinel markers. This feature adds content-drift detection: if a sentinel block's content differs from what graphify would generate, flag it as user-edited rather than corrupted. New conflict_kind: `"user_edited_managed_block"`. |
| "User-space" section at note bottom | Instead of relying on users knowing not to edit sentinel blocks, emit a designated user-space section at the bottom of each note: `<!-- GRAPHIFY_USER_START -->` ... `<!-- GRAPHIFY_USER_END -->`. Content here is always preserved, never regenerated. | LOW | templates.py + merge.py | Add a `user_space` sentinel block to all built-in templates, placed at the bottom. The block is empty on CREATE. On UPDATE, its content is always preserved verbatim, never diffed. Makes the preservation contract visible to users. |
| Vault manifest diff in `--dry-run` | Show users which notes they've modified since last run, alongside what graphify would change. "You edited: auth.py.md, transformer.md. Graphify will update: auth.py.md (refresh connections only)." | LOW | vault-manifest.json + --dry-run output | Extend `format_merge_plan` to include a "user-modified notes" section in dry-run output. Does not block the merge; informational only. |
| Graceful degradation without vault manifest | If `vault-manifest.json` doesn't exist (first run after upgrade to v1.1, or user deleted it), fall back to v1.0 merge behavior with a warning. Never error. | LOW | vault-manifest.json load path | `load_vault_manifest()` returns `{}` if file missing. Missing manifest = treat all existing notes as potentially user-modified → apply conservative merge (preserve user-space, only refresh sentinels). |
| ORPHAN note tracking in manifest | V1.0 already detects orphan notes (notes in vault for nodes no longer in graph). V1.1 extends: flag orphans modified by user (user may have deliberately kept them) vs. unmodified orphans (safe to flag for deletion). | MEDIUM | vault-manifest.json + merge.py ORPHAN action | Compare orphan note hash against manifest. If different from what graphify wrote → user modified → mark `user_modified: true` on the ORPHAN action → never auto-delete. If same → safe to list as deletion candidate in dry-run. |

#### Anti-Features

| Anti-Feature | Why Avoid | Alternative |
|--------------|-----------|-------------|
| Full two-way sync (reading user prose back into graph nodes) | Parsing arbitrary user-edited markdown as structured graph data is a scope explosion (parser, conflict resolution, schema enforcement). V1.0 explicitly scoped this out. | One-direction write with conservative preservation. User edits survive; they don't flow back into the graph. If user wants to add a concept, they run `/graphify` on the relevant file. |
| Auto-deleting orphan notes | Even unmodified orphan notes might be valuable to the user. Auto-deletion is a data loss risk. | `--dry-run` shows orphans as deletion candidates. User must explicitly run `graphify prune-orphans` to delete. Never auto-delete. |
| Watching vault for changes in real time | Letta-obsidian does this; graphify's watch.py only watches code files. Extending to vault note changes creates event loop conflicts and scope creep. | Batch detection on `--obsidian` re-run via vault-manifest.json comparison. No real-time vault watching in v1.1. |
| Overwriting user-space sentinel content | The user-space block (`<!-- GRAPHIFY_USER_START -->`) must be inviolable. Any logic that might overwrite it defeats its purpose. | On UPDATE: always copy user-space block content verbatim from existing note. On CREATE: emit empty user-space block. No exceptions. |

---

## Feature Dependencies

```
Phase 6: Graph Delta Analysis
  snapshot persistence (graphify-out/snapshots/)
      └──required by──> node/edge diff engine
      └──required by──> GRAPH_DELTA.md generation
      └──required by──> `graphify diff <a> <b>` CLI command

  per-node extracted_at metadata
      └──required by──> staleness flagging
      └──required by──> confidence decay metadata

  per-node source_modified_at metadata
      └──required by──> staleness flagging

  staleness flagging
      └──enhances──> GRAPH_DELTA.md (staleness section in summary)

Phase 7: MCP Write-Back
  annotations.json sidecar
      └──required by──> annotate_node MCP tool
      └──required by──> add_edge MCP tool
      └──required by──> flag_importance MCP tool
      └──required by──> tag_node MCP tool
      └──required by──> get_annotations MCP tool
      └──required by──> get_peer_summary MCP tool

  peer identity tracking (peer_id, session_id on all writes)
      └──required by──> session-scoped graph views
      └──required by──> get_peer_summary MCP tool

  propose_vault_note MCP tool
      └──requires──> merge.py compute_merge_plan (v1.0, already built)
      └──requires──> apply_merge_plan (v1.0, already built)
      └──requires──> proposals/{uuid}.json storage
      └──requires──> `graphify proposals list/apply` CLI commands

Phase 8: Obsidian Round-Trip
  vault-manifest.json
      └──required by──> user-modified note detection
      └──required by──> ORPHAN user-modification detection
      └──required by──> vault manifest diff in --dry-run

  user-authored body content detection
      └──requires──> merge.py _parse_sentinel_blocks (v1.0, already built)
      └──requires──> merge.py _merge_body_blocks (v1.0, already built)
      └──enhances by──> user-space sentinel block in templates

Cross-phase dependencies:
  Phase 6 snapshot → Phase 7 session-scoped views (snapshots let MCP load a specific run's graph)
  Phase 6 extracted_at → Phase 7 get_node (surface staleness in node details)
  Phase 7 annotations.json → Phase 8 vault manifest (annotation IDs referenced in proposed notes)
  Phase 8 vault-manifest.json → Phase 7 propose_vault_note (check if target note is user-modified before proposing)
```

### Dependency Notes

- **Snapshot persistence requires no new deps:** `json`, `datetime`, `pathlib`, `shutil` — all stdlib. The graph JSON is already produced by `export.py`; snapshot is a copy.
- **Annotations sidecar is append-only until pruning:** Never modify existing entries. Prune only via explicit CLI command. This keeps the write path simple and atomic.
- **`propose_vault_note` requires merge.py from v1.0:** The proposal apply step runs the full `compute_merge_plan` + `apply_merge_plan` pipeline. This is already built and tested; Phase 7 only adds the proposal storage and approval CLI.
- **Vault-manifest.json and vault-adapter run together:** The manifest must be updated atomically with `apply_merge_plan`. If apply partially fails, manifest should reflect only the succeeded paths (already tracked in `MergeResult.succeeded`).
- **User-space sentinel extends merge.py sentinel grammar:** The `<!-- GRAPHIFY_USER_START -->` / `<!-- GRAPHIFY_USER_END -->` block uses the existing sentinel parser. No new parser needed — this is just a new reserved block name with an inviolable preservation policy.

---

## MVP Definition

### Phase 6 — Launch With

- [ ] Snapshot persistence: write `graphify-out/snapshots/{timestamp}.json` after successful build, FIFO retention (default 10)
- [ ] Node diff: added / removed / community-migrated node sets
- [ ] `GRAPH_DELTA.md`: summary section (counts, top movers) + full diff section — two tiers, one file
- [ ] `extracted_at` and `source_modified_at` per-node metadata — stored in graph JSON
- [ ] Staleness flag: nodes where source_modified_at > extracted_at surfaced in delta summary

### Phase 7 — Launch With

- [ ] `annotate_node`, `tag_node`, `flag_importance` MCP tools — write to `annotations.json`
- [ ] `add_edge` MCP tool — write to `agent-edges.json`
- [ ] Peer identity (peer_id, session_id) on all write tools
- [ ] `get_annotations` MCP tool — read annotations for a node
- [ ] `propose_vault_note` MCP tool + approval CLI (`graphify proposals list/apply`)

### Phase 8 — Launch With

- [ ] `vault-manifest.json` — written by apply_merge_plan, read on re-run
- [ ] User-modified note detection via manifest hash comparison
- [ ] `user_modified` flag in MergeAction, surfaced in `--dry-run` output
- [ ] User-space sentinel block (`<!-- GRAPHIFY_USER_START -->`) in all built-in templates with inviolable preserve policy

### Add After Validation (v1.1.x)

- [ ] `graphify diff <a> <b>` CLI command — compare arbitrary snapshots
- [ ] Session-scoped graph views via MCP (`start_session` / session-filtered reads)
- [ ] `get_peer_summary` MCP tool
- [ ] ORPHAN user-modification tracking in manifest
- [ ] Confidence decay metadata (timestamp arithmetic, no model changes)
- [ ] Annotation TTL pruning (`graphify annotations prune --older-than 90d`)

### Future Consideration (v1.2+)

- [ ] LLM-assisted annotation enrichment (auto-summarizing annotation clusters) — Phase 15
- [ ] Real-time vault watching for change detection — Phase 15
- [ ] User-content-aware conflict resolution (distinguish user-edited sentinel content from corrupted sentinel) — assess after v1.1 usage

---

## Feature Prioritization Matrix

| Feature | User Value | Implementation Cost | Priority |
|---------|------------|---------------------|----------|
| Snapshot persistence | HIGH (enables all delta features) | LOW (copy JSON, stdlib only) | P1 |
| Node/edge diff engine | HIGH (core delta value) | MEDIUM | P1 |
| GRAPH_DELTA.md | HIGH (agent-consumable context) | MEDIUM | P1 |
| `extracted_at` / `source_modified_at` per-node | HIGH (staleness tracking foundation) | LOW (datetime stamp at build) | P1 |
| `annotate_node` / `tag_node` / `flag_importance` MCP tools | HIGH (enables agent memory) | MEDIUM | P1 |
| Peer identity (peer_id, session_id) | HIGH (Honcho pattern; without it, write-back is noise) | LOW (parameter threading) | P1 |
| `annotations.json` sidecar | HIGH (persistence layer for MCP write-back) | LOW (append-only JSON) | P1 |
| `propose_vault_note` + approval CLI | HIGH (closes agent→vault loop safely) | HIGH (proposal storage + CLI approval workflow) | P1 |
| `vault-manifest.json` | HIGH (enables round-trip detection) | LOW (hash map, stdlib) | P1 |
| User-modified note detection | HIGH (prevents data loss on re-run) | MEDIUM (manifest comparison + merge integration) | P1 |
| User-space sentinel block in templates | MEDIUM (UX clarity, but existing sentinel engine already mostly protects user content) | LOW (new template block + policy rule) | P2 |
| `add_edge` MCP tool | MEDIUM (useful for agent-discovered relationships) | MEDIUM (agent-edges.json sidecar + graph loading) | P2 |
| Staleness flagging in delta report | MEDIUM (useful insight, but not blocking) | LOW (timestamp comparison) | P2 |
| `graphify diff <a> <b>` CLI | MEDIUM (power users + CI) | MEDIUM | P2 |
| Session-scoped graph views | MEDIUM (honcho pattern, but single-user workflow reduces urgency) | MEDIUM | P2 |
| `get_peer_summary` | LOW (audit feature) | LOW | P3 |
| Confidence decay metadata | LOW (informational, no action taken) | LOW | P3 |
| Annotation TTL pruning | LOW (nice hygiene feature) | LOW | P3 |
| Community migration tracking in delta | MEDIUM (meaningful signal) | LOW (group migrated nodes by old/new community pair) | P2 |

---

## Competitor Feature Analysis

| Feature | Honcho | Context Constitution / Letta | CPR (EliaAlberti) | Letta-Obsidian | Graphify v1.1 Plan |
|---------|--------|------------------------------|-------------------|----------------|--------------------|
| **Peer identity on writes** | Users and agents as equal peers with async-derived representations | Agent identity via context blocks | User-controlled (no peer concept) | Agent writes under Letta's agent identity | peer_id + session_id on all MCP write tools; caller-supplied, no auth |
| **Session scoping** | Session-scoped memory views | Token context per session | Explicit /preserve and /resume commands | Focus mode (currently viewed note as session context) | `start_session` MCP tool + session-filtered annotation reads |
| **Staleness tracking** | Async derivers rebuild stale representations | First-class staleness; sleep-time compute for reflection | N/A | File size + mtime for sync detection | `extracted_at` + `source_modified_at` per node; staleness flag in delta |
| **Delta output** | Evolving representation (no explicit diff) | Context evolves silently | Summary header + raw archive pattern | File change events (no semantic diff) | GRAPH_DELTA.md with two-tier (summary + full diff), mirroring CPR pattern |
| **Human-approval write-back** | No (agent writes directly) | No (context is agent-owned) | No (user-triggered) | Yes: `propose_obsidian_note` requires approval | Yes: `propose_vault_note` → `graphify proposals apply` |
| **Annotation persistence** | Permanent (honcho backend) | Context blocks in Letta memory | Session log files | Letta memory blocks | `annotations.json` sidecar, pipeline-independent |
| **Round-trip preservation** | N/A (not a file-writing tool) | N/A | N/A | File watcher syncs vault→agent; agent writes are new notes | vault-manifest.json + user-modified detection + user-space sentinel block |

---

## Sources

- graphify codebase audit: `graphify/serve.py` (7 existing MCP read tools), `graphify/merge.py` (sentinel block grammar, MergeAction types, field policy table), `graphify/cache.py` (SHA256 file-hash cache pattern), `graphify/export.py` (graph JSON output)
- `.planning/notes/repo-gap-analysis.md` — analysis of 7 repos: honcho (peer model, session scoping), context-constitution (staleness-first), cpr (summary+archive delta pattern), letta-obsidian (propose_obsidian_note, human approval), llm-council (multi-perspective), spar-kit (structured argumentation), smolcluster (heterogeneous routing)
- `.planning/notes/april-research-gap-analysis.md` — analysis of 12 articles: memory-harness (Sarah Wooders / Letta), Harrison Chase on memory ownership, AI Engineer London 2026 on codebase understanding, Five Things AI Can't Replace on context ownership
- `.planning/PROJECT.md` — v1.1 active requirements list and milestone goal

---
*Feature research for: graphify v1.1 — Context Persistence & Agent Memory*
*Researched: 2026-04-12*
