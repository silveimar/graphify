# Phase 11: Narrative Mode as Interactive Slash Commands - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-04-17
**Phase:** 11-narrative-mode-slash-commands
**Mode:** `--auto` (single-pass, non-interactive; recommended defaults auto-selected by the orchestrator)
**Areas discussed:** Wrapper Shape, MCP Endpoint Gap, Response Envelope, Graceful Degradation, Installation, Scope Policing

---

## Wrapper Shape & Invocation

| Option | Description | Selected |
|--------|-------------|----------|
| Pure shell wrapper | `.md` file contains a `!graphify …` bash call; no MCP | |
| MCP invocation + Claude-authored narrative | Command prompt instructs Claude to call MCP tool(s), then render markdown narrative | ✓ |
| Static pre-rendered markdown | Command file returns a fixed template; no live data | |

**User's choice:** MCP invocation + Claude-authored narrative (auto-selected)
**Notes:** Matches ROADMAP wording ("MCP-backed slash commands"); consistent with existing graphify skill.md pattern where Claude orchestrates MCP calls. Pure shell wrapper would bypass the MCP envelope contract established in Phase 9.2.

---

## MCP Endpoint Gap Plan

| Option | Description | Selected |
|--------|-------------|----------|
| Reuse existing 13 tools exclusively | No new MCP surface; every command composes current tools | |
| Add new MCP tools to serve.py as needed | Extend serve.py's tool block; no new modules | ✓ |
| New graphify/ module for narrative analytics | Separate module housing new algorithms | |

**User's choice:** Add new MCP tools to serve.py as needed (auto-selected)
**Notes:** Explicit ROADMAP directive: *"No new graphify/ module is required unless an MCP query is missing."* Reuse existing `god_nodes`, `shortest_path`, `graph_diff` where possible; add `graph_summary`/`entity_trace`/`drift_nodes`/`newly_formed_clusters` (names TBD in planning) when composition is insufficient.

---

## Stretch Commands (/ghost, /challenge)

| Option | Description | Selected |
|--------|-------------|----------|
| In-scope, required | Ship all 7 commands as core Phase 11 deliverable | |
| Conditional ship (budget-permitting) | Core 5 required, stretch 2 only if capacity | ✓ |
| Defer entirely to v1.4 sibling skill | Phase 11 ships 5 commands only | |

**User's choice:** Conditional ship (auto-selected)
**Notes:** ROADMAP marks SLASH-06/07 explicitly as stretch and permits migration to a sibling skill. Defer decision to planning-phase after core 5 are estimated.

---

## Installation Distribution

| Option | Description | Selected |
|--------|-------------|----------|
| Bundled into graphify install (default-on) | Extend `_PLATFORM_CONFIG`; opt-out via `--no-commands` | ✓ |
| Separate install command (`graphify install-commands`) | New sub-command required for slash commands | |
| Manual copy by user | No installer support | |

**User's choice:** Bundled via graphify install (auto-selected)
**Notes:** Follows the established 7-platform skill-file install pattern. Keeps onboarding single-step. `--no-commands` opt-out preserves flexibility.

---

## Output Format per Command

| Option | Description | Selected |
|--------|-------------|----------|
| Raw JSON | MCP tool output rendered verbatim | |
| Structured tables only | Markdown tables with no prose | |
| Claude-authored markdown (prose + tables) | MCP returns data, Claude renders thinking-partner narrative | ✓ |

**User's choice:** Claude-authored markdown (auto-selected)
**Notes:** Aligned with PROJECT.md framing of v1.3 Phase 11 as "thinking partner." Raw JSON would undercut the interactive-partner value proposition.

---

## Graceful Degradation

| Option | Description | Selected |
|--------|-------------|----------|
| Silent exit / empty response | No graph → empty response | |
| Explicit hint messages per command | Return status code + human-readable hint | ✓ |
| Auto-build graph on demand | `/context` triggers `/graphify` if no graph | |

**User's choice:** Explicit hint messages (auto-selected)
**Notes:** Consistent with Phase 9.2 status-code pattern (`no_seed_nodes`, `budget_exhausted`). Auto-build-on-demand is surprising behavior; violates zero-surprise principle.

---

## Vault Assumptions

| Option | Description | Selected |
|--------|-------------|----------|
| Obsidian vault required | Commands only function inside a vault | |
| Works wherever graphify-out/ exists | Corpus-agnostic, same as graphify CLI | ✓ |

**User's choice:** Corpus-agnostic (auto-selected)
**Notes:** graphify already works on any corpus (code repo, vault, mixed). Commands must match.

---

## Snapshot History Degradation

| Option | Description | Selected |
|--------|-------------|----------|
| Require N snapshots, error if insufficient | Hard fail with instructions | |
| Graceful with explicit messaging | Status `insufficient_history` + snapshots_available count | ✓ |
| Synthesize history from git log | Use git as fallback snapshot source | |

**User's choice:** Graceful with explicit messaging (auto-selected)
**Notes:** Git-log synthesis is out of scope (no existing infra). Hard-fail is hostile to new users. Status-coded messaging matches Phase 9.2.

---

## Entity Resolution (/trace)

| Option | Description | Selected |
|--------|-------------|----------|
| Exact ID required | User must supply canonical node ID | |
| Label fuzzy-match first, ID fallback | Reuse `_find_node()`; disambiguate on multiple matches | ✓ |
| Embedding-based retrieval | Vector similarity over node labels | |

**User's choice:** Label fuzzy-match + ID fallback (auto-selected)
**Notes:** `_find_node()` already ships in serve.py:734. Embedding-based retrieval adds infra beyond thin-wrapper scope.

---

## Installation Scope

| Option | Description | Selected |
|--------|-------------|----------|
| Bundled by default, --no-commands opt-out | Install both skill + commands in one step | ✓ |
| Commands require explicit flag | `graphify install --with-commands` | |

**User's choice:** Bundled by default (auto-selected)
**Notes:** Lower-friction onboarding. Deletion or `--no-commands` preserves opt-out.

---

## Claude's Discretion

- Exact MCP tool names (e.g., `graph_summary` vs `context_digest`) — final harmonization during planning with existing 13-tool naming
- Prompt wording inside each `.md` file — Claude authors matching the existing `graphify/skill.md` voice
- Internal representation of snapshot-history payloads
- Whether `connect_topics` is a standalone MCP composition tool or a Claude-orchestrated two-call sequence

## Deferred Ideas

- Sibling thinking-skill project for `/ghost` + `/challenge`
- Always-on JSONL event log for finer-grained `/trace` timelines
- Command file platform variants beyond Claude Code (only if divergence materializes)
- Obsidian plugin / vault-side slash commands
