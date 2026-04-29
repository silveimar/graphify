# Phase 40: multi-harness-memory-inverse-import-injection-defenses - Context

**Gathered:** 2026-04-29
**Status:** Ready for planning

<domain>
## Phase Boundary

Deliver **multi-harness memory portability with inverse import**, **canonical schema mappings**, **CLI + MCP parity** on validation/sanitization, and **SECURITY.md** coverage for harness import/export threats. Satisfies **PORT-01–PORT-05** and **SEC-01–SEC-04**. Phase **41** vault-selector/`--vault` UX stays out of scope.

Phase **39** remains authoritative for elicitation artifact shapes and merge semantics — Phase **40** must not break `elicitation.json` / harness markdown contracts without an explicit migration note.

</domain>

<decisions>
## Implementation Decisions

### PORT-01 — Second export target
- **D-01:** The milestone’s **second first-class direction** is **canonical JSON manifest interchange** (versioned schema under `graphify/harness_schemas/` or adjacent artifacts), **not** a new AGENTS/Codex markdown writer in this phase. Additional markdown-emitter targets can follow once interchange is stable.

### Import / CLI (PORT-03, PORT-05)
- **D-02:** **Single top-level command** `graphify import-harness <path>` with **`--format auto|claude|...`** (extend enum as formats land). **Subcommand-per-format** is out for Phase 40 unless planner finds a hard conflict.
- **D-03:** **File path input** for Phase 40; **stdin / URL** deferred. Output/artifacts follow **`resolve_output()`** and existing path confinement; **`--out`** or equivalent must stay consistent with other graphify commands (planner details exact flag mirroring `harness export` / `elicit`).

### Sanitization (SEC-01)
- **D-04:** **Layered default:** reuse **label / sink sanitization** and project **security** helpers; add **obvious injection-pattern guards** for imported harness text; allow **low-risk provenance / flags on nodes** where useful for audit. **Not** “reject entire file on first match” as the default (that remains an optional strict mode only if explicitly specified in a plan).

### MCP parity (SEC-03)
- **D-05:** **Same milestone:** MCP entry points for harness import/export must call the **same library code paths and validation** as the CLI (no second implementation). If a tool is stubbed, it must not claim parity — either ship real parity or defer the tool surface to a follow-up (planner must not leave silent mismatch).

### Round-trip (PORT-04)
- **D-06:** Tests assert **semantic preservation** of key **node ids, labels, and relations** within **documented limits**; allow **formatting / whitespace drift** where export is not byte-frozen. **Not** full byte-identical round-trip as the default bar unless a plan adds deterministic export hooks.

### SECURITY.md (SEC-04)
- **D-07:** **Full subsection** for harness import/export: **threats, mitigations, trust boundaries**, and **traceability to SEC-*/PORT-*** in REQUIREMENTS — not a one-paragraph pointer only.

### Claude's Discretion
- Exact JSON manifest schema filename/layout, `import-harness` flag names, strict-mode opt-in, and MCP tool names are **planner/researcher** within D-01–D-07.
- Which **claude** import parser** details** (frontmatter vs body) — follow existing `harness_export` / schema patterns.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Phase & requirements
- `.planning/ROADMAP.md` — Phase 40 goal, v1.9, dependency note on Phase 39.
- `.planning/REQUIREMENTS.md` — **PORT-01–PORT-05**, **SEC-01–SEC-04**.
- `.planning/PROJECT.md` — v1.9 milestone themes.

### Prior phase contract
- `.planning/phases/39-tacit-to-explicit-onboarding-elicitation/39-CONTEXT.md` — Elicitation + harness compatibility decisions; **do not violate** without migration note.

### Implementation surfaces
- `graphify/harness_export.py` — Export pipeline, placeholder normalization, fidelity manifest.
- `graphify/harness_schemas/claude.yaml` — Existing Claude block schema.
- `graphify/security.py` — Path confinement, sanitization patterns.
- `graphify/validate.py` — Extraction schema for import output.
- `graphify/serve.py` — MCP tool registration patterns (parity with CLI).

### Seeds & threat context
- `.planning/seeds/SEED-002-harness-memory-export.md` — Portability and inverse-import intent.
- `SECURITY.md` — Phase 40 extends with harness I/O subsection per **D-07**.

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable assets
- **`export_claude_harness`** and **`claude.yaml`** — Template for forward export; interchange JSON should reference the same conceptual tokens where possible.
- **`validate_extraction` / `build_from_json`** — Import must emit dicts that pass validation without bypass.
- **Phase 39 `graphify/elicit.py`** — Sidecar and harness markdown paths; import must not corrupt merged elicitation nodes.

### Integration points
- **`graphify/__main__.py`** — New `import-harness` branch beside `harness export` / `elicit`.
- **`serve.py`** — MCP tools mirroring CLI for harness I/O per **D-05**.

</code_context>

<specifics>
## Specific Ideas

- **JSON interchange first** per **D-01** — prioritize a clean, versioned artifact over multiple markdown emitters in one phase.

</specifics>

<deferred>
## Deferred Ideas

- **Phase 41** — `--vault`, multi-vault selector, doctor alignment (**explicitly not Phase 40**).
- Additional **markdown harness emitters** (e.g. Codex AGENTS bundle) after interchange lands (**D-01**).
- **Stdin/URL import** — deferred per **D-03**.

</deferred>

---

*Phase: 40-multi-harness-memory-inverse-import-injection-defenses*
*Context gathered: 2026-04-29*
