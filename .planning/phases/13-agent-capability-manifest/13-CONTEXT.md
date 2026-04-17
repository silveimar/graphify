# Phase 13: Agent Capability Manifest (+ SEED-002 Harness Memory Export) - Context

**Gathered:** 2026-04-17
**Status:** Ready for planning

<domain>
## Phase Boundary

Deliver **agent discoverability** for graphify: MCP-compliant **static `server.json`** (registry discovery) plus **runtime `graphify-out/manifest.json`**; **`capability_describe`** MCP tool returning merged static + live state; **`graphify capability`** CLI with `--validate` / `--stdout`; **introspection-driven** generation from `serve.py` (never hand-maintained lists); **manifest hash in every MCP `meta`** for drift detection; **Wave A** (plumbing + partial tool surface after Phases 12 + 18) and **Wave B** (full 14–18 surface + **SEED-002 `graphify harness export`**). Full REQ set: **MANIFEST-01..10**, **HARNESS-01..08** per `.planning/REQUIREMENTS.md`.

**Execution waves** remain as in ROADMAP (single phase entry, not split into decimal phases).

</domain>

<decisions>
## Implementation Decisions

### Wave A: incomplete tool surface (machine-readable manifest)

- **D-01:** **`server.json` and `graphify-out/manifest.json` list only tools actually registered** in `serve.py::list_tools()` **at generation time** — **no** placeholder entries, **no** “planned” tool names, **no** speculative MCP tools that do not exist yet. Wave A honesty is **live introspection truth only**.
- **D-02:** **Narrative roadmap** for upcoming tools (Phases 14–17) stays in **human docs only** (e.g. `.planning/ROADMAP.md`, `graphify/skill.md`, project README) — **not** embedded in the machine-readable manifest JSON payload.

### CI: `graphify capability --validate`

- **D-03:** On validation failure: **non-zero exit**; **stderr** is **stable and copy-paste friendly**: print **expected** content-hash (or committed artifact checksum per planner schema), **actual** value, **path(s)** to the committed **`server.json`** (and any paired artifact the gate compares), and the **exact command** to regenerate (e.g. `graphify capability --stdout > server.json`). **No** huge unified diffs **by default** in the minimal failure path.

### MANIFEST-07: manifest hash in MCP `meta`

- **D-04:** Manifest content-hash in **`meta` is recomputed when manifest-relevant state changes**, aligned with existing **`serve.py` reload** semantics: **invalidate / recompute** on the **same triggers** as graph/sidecar reload (e.g. `_reload_if_stale` or a **narrower** allowlist of files: `graph.json`, telemetry, annotations, dedup report, enrichment overlay when present — planner refines the exact file set). **Not** fixed only at process start; **not** required to re-hash from full JSON on every single RPC if cache invalidation matches state changes.

### Claude's Discretion

- Exact **hash algorithm** (e.g. SHA-256 of canonical JSON bytes) and **field order** for canonical serialization.
- Whether **stderr** in CI mode adds an **optional** `--verbose` diff snippet (default remains minimal per D-03).
- **Wave B** packaging order with SEED-002 relative to manifest regen tasks — ROADMAP already orders Wave B last; planner splits plans accordingly.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Milestone & requirements

- `.planning/ROADMAP.md` — § "Phase 13: Agent Capability Manifest (+ SEED-002 Harness Memory Export)" (goal, depends, execution waves, success criteria, plans note)
- `.planning/REQUIREMENTS.md` — § "Agent Capability Manifest (Phase 13)" (MANIFEST-01..10), § "Harness Memory Export (SEED-002)" (HARNESS-01..08)
- `.planning/research/SUMMARY.md` — v1.4 build order and cross-phase edges

### Cross-cutting invariants (ROADMAP milestone block)

- **D-02** MCP envelope (`text_body` + `---GRAPHIFY-META---` + JSON `meta` + status codes) — applies to **`capability_describe`** and all tools
- **`graph.json` read-only**; manifest and harness outputs are **sidecars / repo-root `server.json`** only
- **`security.py`** for any path surfaced in manifest or export

### Code touchpoints

- `graphify/serve.py` — `@server.list_tools()`, handlers, `_reload_if_stale`, MCP response envelope construction
- `graphify/__main__.py` — CLI dispatch for new subcommands (`graphify capability`, `graphify harness export`)

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets

- **`serve.py::list_tools()`** — Single registration point for MCP tools; Phase 13 introspection should enumerate from here + handler metadata (MANIFEST-05).
- **Existing MCP envelope helpers** — Hash in `meta` extends current D-02 shaping.

### Established Patterns

- **Atomic sidecar writes** — `.tmp` + `os.replace` (used across routing, dedup, etc.) — apply to `manifest.json` updates from pipeline runs.
- **JSON Schema validation** — Requirement MANIFEST-04 references draft 2020-12 via existing deps.

### Integration Points

- **Pipeline / `build.py` / `__main__.py`** — Where “full pipeline run” regenerates `graphify-out/manifest.json` (MANIFEST-02).
- **Skill frontmatter** — MANIFEST-08 adds `capability_manifest:` pointer for discoverability.

</code_context>

<specifics>
## Specific Ideas

No additional “like product X” references — decisions above plus locked REQs drive implementation.

</specifics>

<deferred>
## Deferred Ideas

None from this discussion — scope stayed within Phase 13.

</deferred>

---

*Phase: 13-agent-capability-manifest*
*Context gathered: 2026-04-17*
