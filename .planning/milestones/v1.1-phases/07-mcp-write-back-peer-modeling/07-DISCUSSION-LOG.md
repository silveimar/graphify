# Phase 7: MCP Write-Back with Peer Modeling - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-04-12
**Phase:** 07-mcp-write-back-peer-modeling
**Areas discussed:** Annotation persistence & lifecycle, Peer identity & session model, Proposal approval flow, MCP tool surface design

---

## Annotation Persistence & Lifecycle

| Option | Description | Selected |
|--------|-------------|----------|
| Annotations survive forever | Annotations in annotations.jsonl persist across re-runs. Orphaned annotations kept. | ✓ |
| Annotations expire with nodes | Annotations referencing missing node IDs auto-pruned on re-run. | |
| Annotations get staleness flags | FRESH/STALE/GHOST pattern applied to annotations. | |

**User's choice:** Annotations survive forever
**Notes:** None

| Option | Description | Selected |
|--------|-------------|----------|
| Separate files | annotations.jsonl for annotations/flags, agent-edges.json for edges. | ✓ |
| Single annotations.jsonl | All agent mutations in one JSONL file with type discriminator. | |

**User's choice:** Separate files
**Notes:** None

| Option | Description | Selected |
|--------|-------------|----------|
| Server startup only | Compact once when MCP server starts. Append-only during operation. | ✓ |
| Threshold-triggered | Compact when file exceeds size threshold. | |
| You decide | Claude picks best strategy. | |

**User's choice:** Server startup only
**Notes:** None

---

## Peer Identity & Session Model

| Option | Description | Selected |
|--------|-------------|----------|
| Explicit parameter | peer_id is optional string param on every mutation tool, defaults to "anonymous". | ✓ |
| Server config at startup | peer_id set once at server start via flag. | |
| Both: config default + per-call override | Server default with per-call override option. | |

**User's choice:** Explicit parameter
**Notes:** None

| Option | Description | Selected |
|--------|-------------|----------|
| Server-generated UUID per connection | session_id generated at server start, shared by all mutations in that lifetime. | ✓ |
| Caller-supplied session_id | Agent passes session_id as parameter. | |
| You decide | Claude picks best session model. | |

**User's choice:** Server-generated UUID per connection
**Notes:** None

| Option | Description | Selected |
|--------|-------------|----------|
| Filter parameters on get_annotations | Optional peer_id, session_id, time_range filters. Returns all by default. | ✓ |
| Separate get_session_annotations tool | Dedicated tool returning only current session annotations. | |

**User's choice:** Filter parameters on get_annotations
**Notes:** None

---

## Proposal Approval Flow

| Option | Description | Selected |
|--------|-------------|----------|
| List + per-proposal approve/reject | Non-interactive CLI: approve <id>, --reject <id>, --all for batch. | ✓ |
| Interactive TUI walkthrough | Interactive session showing each proposal with approve/reject/edit. | |
| Dry-run first, then batch apply | Two-step: --dry-run preview then --apply. | |

**User's choice:** List + per-proposal approve/reject
**Notes:** None

| Option | Description | Selected |
|--------|-------------|----------|
| Full note spec | Proposal includes filename, folder, content, frontmatter, note_type, peer/session, rationale. | ✓ |
| Minimal: content + target path | Just markdown content and target path. | |
| You decide | Claude picks metadata balance. | |

**User's choice:** Full note spec
**Notes:** None

| Option | Description | Selected |
|--------|-------------|----------|
| Persist until explicitly rejected | No automatic expiry. User approves, rejects, or --reject-all. | ✓ |
| Expire after N days | Auto-expire after configurable period. | |
| Expire on next pipeline run | Cleared on pipeline re-run. | |

**User's choice:** Persist until explicitly rejected
**Notes:** None

| Option | Description | Selected |
|--------|-------------|----------|
| Through merge engine | Approved proposals feed into compute_merge_plan + apply_merge_plan with full profile. | ✓ |
| Direct write from proposal | Proposal content written as-is, bypassing merge safety. | |
| You decide | Claude picks based on merge engine capabilities. | |

**User's choice:** Through merge engine
**Notes:** None

| Option | Description | Selected |
|--------|-------------|----------|
| Explicit --vault flag | graphify approve --vault /path/to/vault <id>. No implicit state. | ✓ |
| Discover from last run metadata | Auto-discover vault path from graphify-out/ metadata. | |

**User's choice:** Explicit --vault flag
**Notes:** None

---

## MCP Tool Surface Design

| Option | Description | Selected |
|--------|-------------|----------|
| Three separate tools | annotate_node, flag_node, add_edge as distinct tools. | ✓ |
| Unified mutate tool | Single tool with mutation_type discriminator. | |
| Four tools: split annotate + tag | Separate annotate, tag, flag, and add_edge tools. | |

**User's choice:** Three separate tools
**Notes:** None

| Option | Description | Selected |
|--------|-------------|----------|
| Mtime check on every read tool call | Check graph.json mtime before reads, reload if changed. | ✓ |
| Manual reload tool | Explicit reload_graph MCP tool agent calls. | |
| You decide | Claude picks reload strategy. | |

**User's choice:** Mtime check on every read tool call
**Notes:** None

| Option | Description | Selected |
|--------|-------------|----------|
| Structured fields | Tool accepts title, note_type, body_markdown, suggested_folder, tags[], rationale. | ✓ |
| Raw markdown with metadata | Full markdown including frontmatter plus metadata. | |
| You decide | Claude picks based on merge engine needs. | |

**User's choice:** Structured fields
**Notes:** None

| Option | Description | Selected |
|--------|-------------|----------|
| Return record with ID | Full record returned including UUID record_id, timestamp, session_id. | ✓ |
| Just success/failure message | Simple confirmation string. | |

**User's choice:** Return record with ID
**Notes:** None

| Option | Description | Selected |
|--------|-------------|----------|
| Single-server assumption | One MCP server at a time. Annotations loaded at startup + appended in-memory. | ✓ |
| Multi-server safe reads | Re-read JSONL on every get_annotations call. | |

**User's choice:** Single-server assumption
**Notes:** None

---

## Claude's Discretion

- Internal JSONL record schema (exact field names beyond required peer_id/session_id/timestamp)
- Compaction algorithm details
- agent-edges.json internal format
- Error messages for invalid inputs
- _reload_if_stale() implementation details
- Proposal JSON schema and file naming

## Deferred Ideas

None — discussion stayed within phase scope
