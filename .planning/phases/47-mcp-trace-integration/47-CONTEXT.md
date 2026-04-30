# Phase 47: MCP & Trace Integration - Context

**Gathered:** 2026-04-30
**Status:** Ready for planning

<domain>
## Phase Boundary

**Roadmap baseline:** Agents and narrative commands can **find and walk** typed concept↔implementation links through **MCP** and **`/trace` or `entity_trace`**, with documentation updated when capability surfaces change (**CCODE-03**, **CCODE-04**). Phase 46 shipped schema, merge, and security for **`implements` / `implemented_by`**; this phase adds **query/traversal surfaces** and **golden-path tests**, not new relation strings unless requirements change.

**Explicitly later / other phases:** `.graphifyignore` / nested `graphify-out` consolidation (**Phase 48**); CLI `--version` echo (**Phase 49**).

</domain>

<decisions>
## Implementation Decisions

### Manifest, capability export, and release discipline

- **D-47.01:** When MCP surface changes for concept↔code (**CCODE-03**), keep **full stack** in lockstep: `graphify/mcp_tool_registry.py` (tool definitions), handler **docstrings** (including `Examples:` for manifest grammar), **`graphify/capability_tool_meta.yaml`** per-tool defaults, **regenerated `server.json`** (so `manifest_content_hash` / tool_count match), and **any capability/manifest tests** that assert tool lists or hashes.
- **D-47.02:** Documentation split for tool↔relation semantics: a **short pointer/table** in **`docs/RELATIONS.md`** (which MCP paths expose or traverse `implements` / `implemented_by`) plus **fuller narrative** in **`docs/ARCHITECTURE.md`** or **`.planning/codebase/`** pipeline docs — **both**, not one or the other.
- **D-47.03:** **Skill / harness parity:** when tool **names** or **counts** change, update **every** platform skill variant and SEED harness tables that **enumerate** MCP tools (strict parity — no “see canonical only” escape hatch for this milestone).

### Claude's Discretion

- **MCP naming vs existing `entity_trace`:** Today `entity_trace` is **temporal snapshot** tracing (`serve._run_entity_trace`), not concept↔code hop tracing. User did not select the “surface / naming” gray area — **planner** proposes whether to extend with a mode parameter, add a new tool (e.g. `concept_link_trace`), or satisfy CCODE-04 primarily via **`/trace`** + `query_graph` — subject to REQ wording and backward compatibility.
- **`/trace` slash mapping, walk depth, relation filters, golden-path fixture shape** — not discussed; planner defaults acceptable unless SPEC is added later.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Planning & requirements

- `.planning/ROADMAP.md` — Phase 47 goal, success criteria, Depends on Phase 46.
- `.planning/REQUIREMENTS.md` — **CCODE-03**, **CCODE-04** (open rows for Phase 47).
- `.planning/PROJECT.md` — v1.10 milestone framing (MCP + `/trace` MVP).
- `.planning/phases/046-concept-code-schema-build-merge-security/046-CONTEXT.md` — relation taxonomy (**D-46.xx**), merge rules; Phase 47 must stay consistent.

### Code (implementation anchors)

- `graphify/serve.py` — MCP handlers; existing **`entity_trace`** = snapshot timeline (do not assume it already satisfies CCODE-04 without design pass).
- `graphify/mcp_tool_registry.py` — tool schemas and names exposed to MCP.
- `graphify/capability.py` — manifest build, hash, `graphify capability` export path.
- `graphify/capability_tool_meta.yaml` — per-tool manifest metadata (**D-47.01**).
- `server.json` — regenerated manifest artifact (`_meta.manifest_content_hash`, tool_count).
- `graphify/build.py` — `implements` / `implemented_by` normalization (consumers of graph shape).
- `graphify/validate.py` — `KNOWN_EDGE_RELATIONS` / warnings posture.

### Documentation

- `docs/RELATIONS.md` — vocabulary + **new** thin MCP↔relation pointer (**D-47.02**).
- `docs/ARCHITECTURE.md` (or equivalent under `.planning/codebase/`) — narrative for MCP/trace in pipeline (**D-47.02**).

### Skills / harness

- `graphify/skill.md` and platform variants (`skill-codex.md`, etc.) — enumerated tool lists (**D-47.03**).

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable assets

- **`build_mcp_tools()` / `mcp_tool_registry`** — single registry for MCP tool names and input schemas; extend here first.
- **`capability.py` + `capability_tool_meta.yaml` + `server.json` regeneration`** — established Phase 13 manifest pipeline; follow **`CLAUDE.md`** sync steps when package version bumps affect hash.
- **`docs/RELATIONS.md`** — canonical relation list post–Phase 46; right place for a small “MCP surfaces” cross-reference.

### Established patterns

- Hybrid **text + JSON meta** envelope for graph tools (`QUERY_GRAPH_META_SENTINEL` pattern in `serve.py`).
- **Security:** labels/paths through **`security.py`** for any new user-facing fields in tool I/O (**CCODE-05** already satisfied for relations; keep parity for new payloads).

### Integration points

- **`graph query` CLI** (if extended) should stay aligned with MCP semantics where shared.
- **Tests:** prefer pure helpers (pattern used by `_run_entity_trace`, `_run_query_graph`) so golden paths avoid full MCP runtime where possible.

</code_context>

<specifics>
## Specific Ideas

- Discuss session used **`-chain`** after this context: run **`/gsd-plan-phase 47 --auto`** (or equivalent) so plan → execute follows without a second `/clear` handoff if your GSD runtime supports it.
- ROADMAP was missing a GSD-parseable `### Phase 47:` heading (v1.10 phases lived only in `<details>`); a detail section was added so **`gsd-sdk query init.phase-op 47`** resolves.

</specifics>

<deferred>
## Deferred Ideas

- **Rename or overload `entity_trace`** for concept↔code vs temporal trace — deferred to planner (**D-47** discretion block).
- **Strict `/trace` slash behavior**, multi-hop walk policy, and **fixture** choice — deferred to planner unless user adds `/gsd-spec-phase 47` before plan.

**None — discussion stayed within selected manifest scope** for explicit user decisions.

</deferred>

---

*Phase: 47-MCP & Trace Integration*
*Context gathered: 2026-04-30*
