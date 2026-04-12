# Pitfalls Research: v1.1 Context Persistence & Agent Memory

**Domain:** Adding graph persistence, MCP mutations, annotation storage, and bidirectional merge to an existing pure-function CLI pipeline
**Researched:** 2026-04-12
**Confidence:** HIGH — grounded in graphify's existing codebase (serve.py, merge.py, cache.py, security.py), gap analysis from 7 reference repositories, and PROJECT.md v1.1 requirements

---

## Critical Pitfalls

Mistakes that cause rewrites, data loss, or silent corruption.

---

### Pitfall 1: Snapshot Storage Grows Unbounded

**What goes wrong:**
`graphify-out/snapshots/` accumulates one full graph JSON per run with no eviction policy. A codebase re-indexed daily accumulates hundreds of megabytes. The snapshot directory also contains index metadata (e.g. a manifest JSON listing all snapshots); if that file is never pruned it grows without bound. At scale, users notice the `graphify-out/` directory dwarfs the codebase itself.

**Why it happens:**
The cache module (`cache.py`) uses a content-addressed hash-per-file scheme that naturally evicts stale entries when source files change. Snapshot storage is different: each snapshot is a full graph state keyed by run timestamp, not by content hash. There is no natural eviction trigger. First implementations copy the cache pattern without realizing the semantics differ.

**How to avoid:**
Implement a two-tier retention policy at snapshot write time, not as a separate cleanup job:
- **Keep**: The last N snapshots (default: 10), configurable in `graphify-out/snapshots/manifest.json`
- **Archive**: Compress snapshots older than N using `gzip` (stdlib, no new dependency) into `graphify-out/snapshots/archive/`
- **Prune**: Delete archived snapshots older than configurable TTL (default: 30 days)

Apply the CPR summary+archive pattern: each snapshot writes two files — `{timestamp}-summary.json` (lightweight: node count, edge count, community count, top-5 god nodes) and `{timestamp}-full.json.gz` (compressed full graph). Load only the summary into agent context; the full diff is on-demand.

```python
def _prune_snapshots(snapshot_dir: Path, keep: int = 10) -> None:
    entries = sorted(snapshot_dir.glob("*-summary.json"))
    for old in entries[:-keep]:
        full = old.with_name(old.name.replace("-summary.json", "-full.json.gz"))
        old.unlink(missing_ok=True)
        full.unlink(missing_ok=True)
```

Write this into `snapshot.py::save_snapshot()` so pruning is automatic on every write. Never leave pruning to a separate manual command.

**Warning signs:**
- `graphify-out/snapshots/` grows by megabytes per run
- Manifest JSON exceeds 1 MB
- Users report slow `--obsidian` runs (iterating the snapshots directory to find the latest)

**Phase to address:** Phase 6 (Delta Analysis) — must be in the initial snapshot write path.

---

### Pitfall 2: MCP Mutation Tools Break the Pure-Function Invariant of serve.py

**What goes wrong:**
Adding `annotate_node`, `add_edge`, `flag_importance` tools to `serve.py` requires the server to hold mutable state. The current `serve()` function loads the graph once at startup into `G` (a module-level NetworkX graph) and serves it as a read-only resource. Adding mutation tools that modify `G` in place create a shared-mutable-state problem: tool A modifies `G`, tool B reads a mutated `G`, a re-run of the CLI replaces `graphify-out/graph.json` and `G` is now stale, mutation state is lost without any warning to the agent.

**Why it happens:**
MCP servers are long-lived processes. `serve.py`'s `G` variable is initialized once at `serve()` startup and never refreshed. Write-back tools that mutate `G` do so against a potentially stale snapshot. When the CLI re-runs and writes a new `graph.json`, the MCP server is still holding the old `G` — mutations are silently discarded when the server restarts.

**How to avoid:**
Separate the graph state from the annotation state into two distinct persistence layers:

1. **Graph state** (`graph.json`): read-only within the MCP server, always loaded fresh from disk at tool call time for read tools (use a `_reload_if_stale()` check comparing `graph.json` mtime vs. load time). Never mutate `G` in-place.

2. **Annotation state** (`annotations.json`): the only write target for MCP mutation tools. Annotations are a separate file, not embedded into `graph.json`. Reads merge `graph.json` + `annotations.json` at query time.

```python
# In serve.py — reload-on-stale pattern for read tools
def _reload_if_stale(state: _ServerState) -> nx.Graph:
    mtime = Path(state.graph_path).stat().st_mtime
    if mtime > state.loaded_at:
        state.G = _load_graph(state.graph_path)
        state.loaded_at = mtime
    return state.G
```

Mutation tools write only to `annotations.json` via atomic write (temp file + `os.replace()`). They never touch `graph.json`. This keeps the pure-function invariant of the extraction pipeline intact.

**Warning signs:**
- A mutation tool handler accesses `G.nodes[nid]` and modifies attributes in place
- `serve.py` has no mtime check before reading graph data
- Annotations are embedded as node attributes in `graph.json`

**Phase to address:** Phase 7 (MCP Write-Back) — design decision must be locked before any mutation tool is implemented.

---

### Pitfall 3: annotations.json Corruption Under Concurrent Access

**What goes wrong:**
Two MCP tool calls arrive near-simultaneously (possible when an agent spawns parallel tool calls). Both call `annotate_node`, both read `annotations.json`, both modify their in-memory copy, and both write. The second write silently overwrites the first. Result: one annotation is lost. No error is raised; the agent believes both annotations were saved.

**Why it happens:**
The current `cache.py` uses `os.replace()` after a temp write — atomic at the OS level for single-writer scenarios. But two concurrent readers + two concurrent writers create a read-modify-write race: read(A) → read(B) → write(A) → write(B, discarding A's change).

**How to avoid:**
Use file locking for all annotation writes. Python's `fcntl.flock()` (POSIX) or `msvcrt.locking()` (Windows) provide advisory locks. Since graphify already targets Python 3.10+ and the constraint is "no new required dependencies," use a cross-platform lock via a lock file:

```python
import fcntl
import contextlib

@contextlib.contextmanager
def _annotation_lock(lock_path: Path):
    with open(lock_path, "w") as lf:
        try:
            fcntl.flock(lf, fcntl.LOCK_EX)
            yield
        finally:
            fcntl.flock(lf, fcntl.LOCK_UN)
```

For Windows compatibility (where `fcntl` is absent), fall back to a `threading.Lock()` — sufficient since a single MCP server process is single-process even if async. The async MCP event loop is single-threaded; concurrent tool calls are awaited not threaded. Document this assumption.

Alternative that avoids all locking complexity: make annotation writes append-only (JSONL format, one JSON object per line). Read = load all lines and merge. Write = append one line. Append to a file is atomic for small writes on all major filesystems. Compaction (rewrite to deduplicated JSON) happens on startup only.

The JSONL append pattern is strongly preferred — simpler, testable, and matches the CPR session log pattern.

**Warning signs:**
- `annotations.json` is read, modified in Python dict, then written back as a full file rewrite
- No lock or append-only strategy is used
- Tests don't simulate concurrent writes

**Phase to address:** Phase 7 (MCP Write-Back) — choose JSONL append before the first annotation tool is implemented.

---

### Pitfall 4: Obsidian Merge Conflicts Between Graphify-Generated and User-Authored Content

**What goes wrong:**
v1.0's merge engine uses sentinel blocks to separate graphify-managed content from user-authored content within a note. The round-trip (Phase 8) must detect user modifications to sentinel-protected content and decide how to merge them. The failure mode: graphify re-runs, detects a user-modified block, and either (a) silently overwrites user edits with the freshly-generated content, or (b) raises `SKIP_CONFLICT` and writes nothing, leaving stale graphify content in place. Both are wrong.

**Why it happens:**
The v1.0 merge engine has six action types (`CREATE`, `UPDATE`, `SKIP_PRESERVE`, `SKIP_CONFLICT`, `REPLACE`, `ORPHAN`). `SKIP_CONFLICT` fires on `malformed_sentinel` or `malformed_frontmatter`. But user-modified content WITHIN a sentinel block (the user edited the body of a graphify-generated note) is not a conflict — it is legitimate user authorship that must be preserved while still allowing the graphify-managed frontmatter to update.

**How to avoid:**
Extend `merge.py`'s action vocabulary with a `PARTIAL_UPDATE` action. This action:
1. Rewrites the frontmatter section (graphify-managed, field-policy-driven as in v1.0)
2. Leaves the note body below the sentinel intact (user-authored)
3. Updates only the sentinel-delimited graphify-managed sections within the body if the node data changed

The key invariant: user text outside sentinel blocks is never touched. User text inside sentinel blocks is preserved if the sentinel is detected as user-modified (detect modification by hashing the sentinel content at last-write time and storing the hash in the frontmatter as `graphify_body_hash`).

```python
# In merge.py — add to MergeAction.action valid set
_VALID_ACTIONS = frozenset({..., "PARTIAL_UPDATE"})

# In compute_merge_plan — classify
if existing_body_hash != stored_graphify_hash:
    action = "PARTIAL_UPDATE"  # user modified body; update frontmatter only
```

**Warning signs:**
- Users report edited notes being overwritten on re-run
- The `SKIP_CONFLICT` rate is high in dry-run output (users manually modified notes)
- `merge.py`'s `apply_merge_plan()` has no branch for body-vs-frontmatter distinction

**Phase to address:** Phase 8 (Obsidian Round-Trip) — extend the merge engine before any round-trip detection is implemented.

---

### Pitfall 5: Staleness Metadata Becomes Stale Itself (Meta-Staleness)

**What goes wrong:**
Each node carries `extracted_at` (when graphify last processed the node) and `source_modified_at` (when the source file was last modified). The delta report flags nodes where `source_modified_at > extracted_at` as stale. But if the user renames a source file, the node's `source_file` path no longer exists. The node is not flagged as stale (the old path is stored and no comparison is made) — it becomes a ghost node: valid-looking but disconnected from any actual file.

Second-order problem: if `extracted_at` is stored as an absolute timestamp, nodes extracted before a machine clock adjustment (NTP sync, timezone change, system migration) will have incorrect staleness classifications.

**Why it happens:**
Staleness metadata is a simple comparison: `source_modified_at > extracted_at`. It does not account for file renames, moves, or deletions. It also does not account for clock skew between systems.

**How to avoid:**
Store staleness metadata in two layers:
1. **Path-based**: `source_file` + `source_modified_at` (mtime from `os.stat()`)
2. **Hash-based**: `source_hash` (SHA256 of file contents at extraction time, consistent with `cache.py`'s `file_hash()`)

Staleness check order:
1. If `source_file` does not exist → `GHOST` status (file was deleted or renamed)
2. If `source_hash` differs from current `file_hash(source_file)` → `STALE` (file was modified)
3. If `source_hash` matches → `FRESH` (no change, regardless of mtime)

Use hash comparison as the authoritative staleness signal, not mtime. This matches `cache.py`'s existing pattern and avoids clock-skew false positives.

For ghost nodes, the delta report should prominently surface them as requiring either re-extraction (if the file was renamed) or pruning (if it was deleted).

**Warning signs:**
- Staleness check uses only `mtime` comparison
- `source_file` path is not checked for existence before computing staleness
- Delta report shows nodes as FRESH when their source files were deleted

**Phase to address:** Phase 6 (Delta Analysis) — staleness schema must be correct from the first snapshot.

---

### Pitfall 6: Peer Identity Tracking Leaks Sensitive Information

**What goes wrong:**
Annotations stored in `annotations.json` carry `peer_id` and `session_id` to track which agent or user session produced an annotation. If `peer_id` is set to a value derived from machine hostname, username, API key prefix, or other environmental data, the annotation file becomes a sensitive artifact. Pushing `graphify-out/` to a public repository (a common developer workflow) would expose machine identity, user identity, or API key fragments.

Second-order: if `session_id` is a UUID derived from a timestamp + machine ID (as Python's `uuid.uuid1()` does), it embeds MAC address information in the annotation file.

**Why it happens:**
The Honcho-inspired peer model requires tracking WHO annotated what. The obvious implementation pulls identity from the environment — `os.environ.get("USER")`, `socket.gethostname()`, or Claude session metadata. These are convenient but sensitive.

**How to avoid:**
Use only user-controlled, explicitly-provided identity, not environment-derived identity:
- `peer_id` must be explicitly set in graphify config or passed as a CLI flag: `graphify mcp --peer-id myagent`. If not set, default to the anonymous string `"anonymous"` (not to hostname or username).
- `session_id` must be a UUID4 (random, not time+MAC). Use `uuid.uuid4()` exclusively.
- Add `graphify-out/` to the default `.gitignore` template that `graphify install` creates. Add an explicit note in the annotations schema that `graphify-out/annotations.json` may contain session metadata and should not be committed to public repositories.

```python
import uuid
def new_session_id() -> str:
    return str(uuid.uuid4())  # random, no MAC address

def resolve_peer_id(cli_flag: str | None) -> str:
    if cli_flag:
        return sanitize_label(cli_flag)[:64]  # user-provided, sanitized
    return "anonymous"  # never derive from environment
```

**Warning signs:**
- `peer_id` is assigned from `os.environ.get("USER")` or `socket.gethostname()`
- `session_id` is generated with `uuid.uuid1()`
- No `.gitignore` guidance for `graphify-out/`

**Phase to address:** Phase 7 (MCP Write-Back) — peer identity schema must be defined before the first annotation is written.

---

### Pitfall 7: propose_vault_note Allows Agent-Driven Arbitrary File Writes

**What goes wrong:**
The `propose_vault_note` MCP tool is supposed to require human approval before writing to the vault. If the approval gate is not implemented atomically — if the tool writes the note and then asks for approval, or if the approval check can be bypassed by a crafted tool argument — an agent can write arbitrary content to arbitrary paths inside the vault. Combined with path traversal via the note title (e.g., a note titled `../../.ssh/authorized_keys`), this is a remote code execution risk.

**Why it happens:**
The Letta-Obsidian reference implementation (`propose_obsidian_note`) writes to a staging area and requires human approval. Implementing this correctly requires: (1) never writing to the target path until approval is confirmed, (2) validating the target path before staging, and (3) ensuring the approval mechanism is synchronous and cannot be skipped by the agent.

**How to avoid:**
Implement a strict two-step flow:
1. `propose_vault_note` writes ONLY to a staging directory (`graphify-out/proposals/{uuid}.json`) containing the proposed note content and target path. Returns a proposal ID. Never writes to the vault.
2. A separate human-facing command (`graphify approve-proposal {id}`) reads the staged proposal, validates the target path via `validate_vault_path()` from `security.py`, confirms with the user (terminal prompt or `--yes` flag), and only then writes.

All path validation must happen at write time (step 2), not at proposal time (step 1), because the vault root may have changed between steps.

The note content must pass through the existing frontmatter sanitization pipeline (`safe_frontmatter_value`, `safe_tag`, `safe_filename` from `profile.py`). Never write raw agent-supplied content to the vault without sanitization.

```python
# serve.py — propose_vault_note handler
def _tool_propose_vault_note(arguments: dict) -> str:
    title = sanitize_label(arguments.get("title", ""))[:200]
    content = arguments.get("content", "")  # sanitized at approval time
    proposal = {
        "id": str(uuid.uuid4()),
        "title": title,
        "content": content,  # raw, not yet written
        "proposed_at": datetime.datetime.utcnow().isoformat(),
        "peer_id": state.peer_id,
    }
    # Write ONLY to staging — never to vault
    staging = Path("graphify-out/proposals") / f"{proposal['id']}.json"
    staging.parent.mkdir(parents=True, exist_ok=True)
    staging.write_text(json.dumps(proposal, ensure_ascii=False), encoding="utf-8")
    return f"Proposal {proposal['id']} staged. Run: graphify approve-proposal {proposal['id']}"
```

**Warning signs:**
- `propose_vault_note` writes to the vault directory (not to `graphify-out/proposals/`)
- Path validation happens before staging rather than at approval time
- Agent-supplied note title is used directly in path construction without `safe_filename()`
- No human-in-the-loop confirmation step exists in the implementation

**Phase to address:** Phase 7 (MCP Write-Back) — staging-only pattern must be the architecture from day one.

---

## Technical Debt Patterns

Shortcuts that seem reasonable but create long-term problems.

| Shortcut | Immediate Benefit | Long-term Cost | When Acceptable |
|----------|-------------------|----------------|-----------------|
| Embedding annotations into `graph.json` node attributes | Single file to manage | Every annotation write requires rewriting the full graph JSON; concurrent access corrupts the graph; CI/CD pipeline re-runs lose all annotations (graph.json is regenerated) | Never — annotations must be a separate file |
| Storing full graph in each snapshot (uncompressed) | Simple implementation | Storage grows by graph size per run; for large codebases (5K+ nodes) each snapshot is multi-MB | Never for production; acceptable for a proof-of-concept only |
| Loading graph.json once at serve() startup and never reloading | Simple in-memory access | Stale reads after CLI re-runs; mutation tools modify stale state; no way to refresh without restarting the MCP server | Acceptable only for read-only MCP servers with no mutation tools |
| Using os.environ USER/hostname as peer_id | Zero config | Leaks machine identity in annotation files committed to repos | Never — always use explicit config or "anonymous" |
| Writing vault notes directly from propose_vault_note without staging | Simpler implementation | Bypasses human approval gate; enables agent-driven arbitrary file writes | Never — staging is non-negotiable |
| JSONL append for annotations without periodic compaction | No locking needed, crash-safe | File grows unbounded; reads must scan entire file; duplicate annotations for same node accumulate | Acceptable for MVP; add compaction (load → deduplicate → rewrite) at startup before v1.1 ships |

---

## Integration Gotchas

Common mistakes when connecting new v1.1 features to existing graphify modules.

| Integration | Common Mistake | Correct Approach |
|-------------|----------------|------------------|
| `serve.py` + mutation tools | Adding mutation tools to `_handlers` dict that modify `G` directly | Keep `G` as read-only; write-back tools write ONLY to `annotations.json` via `_annotations_write()` helper |
| `cache.py` + snapshot persistence | Reusing `cache_dir()` for snapshots (conflates extraction cache with run history) | Create a separate `snapshot_dir()` returning `graphify-out/snapshots/`; do not mix cache and snapshot storage |
| `merge.py` + round-trip detection | Treating user-modified sentinel blocks as `SKIP_CONFLICT` | Add `PARTIAL_UPDATE` action that rewrites frontmatter only while preserving body; detect via `graphify_body_hash` stored in frontmatter |
| `security.py` + annotation writes | Forgetting to call `validate_graph_path()` on the annotations file path | Annotations path must pass `validate_graph_path()` before every write; the path is fixed (`graphify-out/annotations.jsonl`) but the check must be there for CI enforcement |
| `security.py` + proposal vault path | Validating vault path at proposal time (before user confirms) | Validate vault path at approval time only; `propose_vault_note` writes to `graphify-out/proposals/` which is always valid |
| `profile.py` + round-trip merge | Reusing `_DEFAULT_FIELD_POLICIES` for the new `graphify_body_hash` field | Add `graphify_body_hash: "replace"` to `_DEFAULT_FIELD_POLICIES` in `merge.py` so it is always refreshed on UPDATE |
| `analyze.py` + delta report | Running god-node analysis on the delta (new/removed nodes only) instead of the full graph | Delta analysis compares two full graphs; god-node ranking runs on each full graph independently, then changes are diffed |

---

## Performance Traps

Patterns that work at small scale but fail as usage grows.

| Trap | Symptoms | Prevention | When It Breaks |
|------|----------|------------|----------------|
| Loading full graph JSON for every read tool call (no caching) | MCP query latency spikes; server pegged on large graphs | Load once at startup; use mtime-based reload only when graph.json changes | ~500 nodes (50ms reads become seconds for BFS) |
| Full snapshot diff (node-by-node Python dict comparison) | GRAPH_DELTA.md generation takes >10 seconds | Use NetworkX's built-in set operations: `set(G1.nodes()) - set(G2.nodes())` for additions/removals; avoid per-node attribute comparison unless needed | ~2000 nodes |
| Scanning entire `annotations.jsonl` on every read | MCP annotation reads slow; large annotation files cause tool timeouts | Build an in-memory index of `{node_id: [annotation_indices]}` at server startup; rebuild index on file change | ~10,000 annotations |
| Writing snapshot manifest JSON with full metadata for every snapshot | Manifest grows proportionally to snapshot count; loading manifest to find latest snapshot becomes slow | Manifest stores only `{timestamp, summary_path, full_path, node_count}` (not full node lists); cap manifest at last 100 entries | ~100 snapshots |
| Uncompressed full-graph snapshots | `graphify-out/snapshots/` fills disk; slow snapshot loading | Compress full snapshots with `gzip` (stdlib `gzip.open()`, no new dependency); summary snapshots remain uncompressed for fast access | ~5 runs on a 10K-node graph |

---

## Security Mistakes

Domain-specific security issues for v1.1 features.

| Mistake | Risk | Prevention |
|---------|------|------------|
| Accepting agent-supplied `peer_id` without sanitization | Agent injects control characters or HTML into annotation metadata; stored in `annotations.jsonl` and read back into MCP responses | Run `sanitize_label()` (from `security.py`) on all peer_id and session_id values before storing |
| Using annotation `content` field directly in MCP tool response without sanitization | XSS-equivalent in agents that render MCP tool responses as HTML; stored malicious content replayed to future agents | Run `sanitize_label()` on annotation content at read time before returning in MCP response |
| Proposal staging directory path not validated | Agent supplies `../../../etc/cron.d/graphify` as staging subpath | Staging directory is hardcoded to `graphify-out/proposals/` by server logic, not derived from agent input; proposal filename is server-generated UUID4, never agent-supplied |
| Delta report embedding raw node labels without HTML escaping | `GRAPH_DELTA.md` is rendered in Obsidian which processes markdown; malicious node label (`<script>alert()</script>`) executes in Obsidian's embedded browser pane | Apply `html.escape()` to all node labels before embedding in `GRAPH_DELTA.md`; already done in `export.py` for HTML viz — same pattern applies to delta markdown |
| `propose_vault_note` content written to staging without size cap | Agent supplies 100MB string as note content; fills `graphify-out/proposals/` | Cap proposal content at `_MAX_TEXT_BYTES` from `security.py` (10 MB) before staging |
| Annotation timestamp stored as agent-supplied string | Agent lies about when annotation was made; disrupts temporal analysis of peer behavior | `timestamp` in annotations is always `datetime.datetime.utcnow().isoformat()` from server side; never accepted from agent input |

---

## "Looks Done But Isn't" Checklist

Things that appear complete in v1.1 but are missing critical pieces.

- [ ] **Snapshot persistence:** Snapshots write and load correctly — but verify pruning runs automatically on every `save_snapshot()` call, not only when a separate `--prune` flag is passed
- [ ] **MCP mutations:** `annotate_node` saves to `annotations.jsonl` — but verify the MCP server's in-memory annotation index is updated after each write (so subsequent `query_graph` calls reflect the new annotation without restarting the server)
- [ ] **Delta report:** `GRAPH_DELTA.md` shows new/removed nodes — but verify community migration is tracked (a node moving from community 2 to community 0 is a significant structural change that must appear in the delta)
- [ ] **Staleness metadata:** `extracted_at` and `source_modified_at` are stored on nodes — but verify `source_hash` is also stored and used as the authoritative staleness signal (not mtime alone)
- [ ] **Peer identity:** `peer_id` is stored on annotations — but verify it defaults to `"anonymous"` when `--peer-id` is not passed and is never derived from `os.environ` or `socket.gethostname()`
- [ ] **Round-trip merge:** User-authored content below sentinel blocks is preserved on re-run — but verify that a note with NO sentinel blocks (user created the note manually in Obsidian before graphify ran) produces `CREATE` action, not `SKIP_CONFLICT`
- [ ] **propose_vault_note:** Staging writes succeed — but verify that the approval step calls `validate_vault_path()` from `security.py` at write time, not at proposal time
- [ ] **Annotation JSONL:** Append writes work — but verify compaction (deduplication of annotations for the same node) runs at server startup to prevent unbounded growth

---

## Recovery Strategies

When pitfalls occur despite prevention.

| Pitfall | Recovery Cost | Recovery Steps |
|---------|---------------|----------------|
| Snapshot directory filled disk | MEDIUM | Delete `graphify-out/snapshots/` entirely; re-run graphify to generate fresh baseline; no code data is lost (snapshots are derived from graph.json) |
| annotations.jsonl corrupted by concurrent write | LOW | Validate each JSONL line independently; skip malformed lines; compact the file by rewriting only valid lines; data loss is bounded to the concurrent write window |
| User-authored content overwritten by merge bug | HIGH | Restore from vault's git history (recommend users keep vault in git); if no git, content is unrecoverable; implement `--dry-run` as mandatory first step before any re-run on edited vaults |
| Ghost nodes flooding delta report (source files moved) | LOW | Run `graphify --prune-ghosts` to remove nodes whose `source_file` no longer exists; re-run extraction on the new paths |
| peer_id leaking sensitive data in committed annotations | HIGH | Rotate: remove `graphify-out/annotations.jsonl` from git history using `git filter-repo`; add `graphify-out/` to `.gitignore` immediately; regenerate annotations with `"anonymous"` peer_id |
| propose_vault_note written malicious content before approval gate | HIGH | Delete `graphify-out/proposals/` directory; audit vault for unexpected files; implement staging-only pattern as emergency patch |

---

## Pitfall-to-Phase Mapping

| Pitfall | Prevention Phase | Verification |
|---------|------------------|--------------|
| Snapshot unbounded growth (P1) | Phase 6 (Delta Analysis) | `save_snapshot()` test: write 15 snapshots, assert only 10 remain in `graphify-out/snapshots/`; assert archived ones are compressed |
| MCP mutation breaks read-only invariant (P2) | Phase 7 (MCP Write-Back) | `serve.py` test: mutation tool call does not modify `G` in-place; `graph.json` mtime unchanged after annotation write |
| annotations.json concurrent write corruption (P3) | Phase 7 (MCP Write-Back) | JSONL append test: simulate two concurrent append writes; assert both entries are readable in final file |
| Obsidian merge conflict on user-modified body (P4) | Phase 8 (Obsidian Round-Trip) | `merge.py` test: note with user-modified body below sentinel produces `PARTIAL_UPDATE`, not `SKIP_CONFLICT`; user body is preserved in output |
| Staleness metadata meta-staleness (P5) | Phase 6 (Delta Analysis) | `snapshot.py` test: node with deleted `source_file` is classified `GHOST`, not `FRESH`; hash comparison used over mtime for STALE classification |
| Peer identity leaking sensitive data (P6) | Phase 7 (MCP Write-Back) | `annotations.py` test: `resolve_peer_id(None)` returns `"anonymous"`; `new_session_id()` returns UUID4 (no MAC component: `uuid.UUID(s).version == 4`) |
| propose_vault_note arbitrary file write (P7) | Phase 7 (MCP Write-Back) | `serve.py` test: `propose_vault_note` writes ONLY to `graphify-out/proposals/`; vault directory is unchanged after tool call; path traversal in title is blocked at approval time |

---

## Sources

- graphify codebase: `graphify/serve.py` (MCP server architecture, read-only invariant), `graphify/merge.py` (action vocabulary, sentinel blocks, field policies), `graphify/cache.py` (hash-based storage pattern, `os.replace()` atomic write), `graphify/security.py` (`sanitize_label`, `validate_graph_path`, path confinement model)
- `.planning/PROJECT.md` v1.1 requirements (snapshot persistence, MCP write-back, peer identity, `propose_vault_note`, Obsidian round-trip, per-node staleness metadata)
- `.planning/notes/repo-gap-analysis.md` (Honcho peer model, CPR summary+archive pattern, Letta-Obsidian `propose_obsidian_note` staging architecture, Context Constitution staleness-as-first-class, smolcluster bounded staleness)
- Python stdlib: `uuid` module docs (uuid1 MAC address risk, uuid4 randomness guarantee), `fcntl` POSIX advisory locks, `gzip` compression, `os.replace()` atomicity guarantees

---
*Pitfalls research for: v1.1 Context Persistence & Agent Memory — graphify*
*Researched: 2026-04-12*
