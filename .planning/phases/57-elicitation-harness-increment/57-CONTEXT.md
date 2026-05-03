# Phase 57: Elicitation & harness increment - Context

**Gathered:** 2026-05-03
**Status:** Ready for planning

<domain>
## Phase Boundary

Deliver one observable, well-tested improvement to the elicitation → extraction → harness pipeline:

1. Add scripted unit tests for **sidecar-collision merge semantics** (nodes + edges) in `build()`.
2. Update `docs/ELICITATION.md` in place with **Trust Boundaries** and v1.11 **Non-Goals** sections.
3. Harden the **existing `import-harness` surface** (CLI + MCP) with documented canonical mapping and explicit guard tests.
4. Lock down **import off-by-default** semantics with guard tests on three guarantees.

No new harness target formats. No true inverse round-trip. No new CLI/MCP commands. The phase clarifies and locks down what already exists; it does not extend functionality.

</domain>

<decisions>
## Implementation Decisions

### ELIC-01 — Scripted elicitation scenario tests
- **D-01:** New scenario coverage = **sidecar collision behavior** in `graphify/build.py:281-299` (the `elicitation` arg / `merge_elicitation_into_build_inputs` path).
- **D-02:** Coverage spans **nodes AND edges**: node-id collision (elicitation wins), duplicate edges, same source/target with conflicting `relation`, and confidence preservation across the merge.
- **D-03:** Failure modes in scope: malformed sidecar JSON, missing required fields, sidecar with edges referencing absent nodes. Happy-path artifact-shape assertions on the resulting graph.
- **D-04:** Sidecar on-disk schema assertions (file shape / ordering) are out of scope here — handled by `validate.py` territory.

### HARN-01 — Incremental capability lane
- **D-05:** Lane chosen = **inverse-import guards on the existing surface** (NOT a new export target format, NOT a new round-trip).
- **D-06:** "Inverse-import" in this phase means the **already-shipped** `graphify import-harness` CLI (`graphify/__main__.py:2512+`) and the MCP `import_harness` tool (`graphify/serve.py:3724+`). No new code paths.
- **D-07:** Deliverable = documented canonical mapping (the `graphify.harness.interchange/v1` schema as it exists today, in prose) + lock-in guard tests. The doc lives in the ELIC-02 deliverable (`docs/ELICITATION.md`) under the trust-boundaries section, NOT in a new doc.

### HARN-02 — Import off-by-default guard surface
- **D-08:** Guard tests must prove three guarantees:
  1. **Refuses vault-rooted output** — `import-harness` with `--output` resolving inside any vault path is rejected unless the user passes an explicit confirmation flag. Today's `harness_import.json` lands in `artifacts_dir` only — codify that this cannot be coerced into a vault path.
  2. **Never auto-invoked from pipelines** — no other graphify command (`run`, `watch`, `update-vault`, `elicit`, `doctor`) calls `import_harness_path` / `import_harness_bytes` transitively. Asserted via call-site grep / import-graph test.
  3. **MCP tool requires explicit args** — `import_harness` MCP tool refuses to run without an explicit `path` argument; no defaults, no auto-discovery.
- **D-09:** Size caps and prompt-injection sanitization (`MAX_HARNESS_IMPORT_BYTES`, `sanitize_harness_text`) are **out of scope** — already covered in Phase 40 work. Reference, do not re-test.

### ELIC-02 — Trust-boundaries documentation
- **D-10:** Update `docs/ELICITATION.md` **in place** (not a new `TRUST-BOUNDARIES.md`, not a full rewrite). Add two sections: `## Trust Boundaries` and `## Milestone Non-Goals (v1.11)`.
- **D-11:** Trust Boundaries section explicitly addresses three surfaces:
  - **Where elicitation reads/writes** — `resolve_output()` contract; sidecar at `artifacts_dir/elicitation.json`; never reads from vault config without explicit user consent.
  - **What `import-harness` will and will not do** — off-by-default; refuses vault-rooted output; requires explicit path; no MCP auto-discovery. (Doc and HARN-02 guard tests point at the same invariants.)
  - **LLM trust posture during `elicit`** — what free-text from `--demo` / interactive elicitation is sanitized vs trusted; how labels are escaped before HTML / Obsidian export.
- **D-12:** Sidecar merge precedence (the build.py invariant) is NOT separately documented in the trust boundaries — ELIC-01 tests are the canonical record of that contract. Doc may reference the test module.

### Claude's Discretion
- Test file layout (extend `tests/test_elicit.py` and `tests/test_harness_import.py` vs new `tests/test_phase57_guards.py`) — planner picks based on existing conventions.
- Exact name of the explicit confirmation flag for vault-rooted output (e.g., `--allow-vault-write`) — researcher/planner to choose, must be visible enough to be deliberate.
- Whether the "no auto-invocation" guard test uses static import-graph analysis or runtime grep over source — either is acceptable.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Phase scope & requirements
- `.planning/ROADMAP.md` §"Phase 57: Elicitation & harness increment" — goal, success criteria, requirement IDs.
- `.planning/REQUIREMENTS.md` lines 29–32, 65–68 — ELIC-01, ELIC-02, HARN-01, HARN-02 definitions and the requirement-to-phase index.

### Prior milestone artifacts (precedent / non-goals reference)
- `.planning/milestones/v1.10-ROADMAP.md` — v1.10 close-out narrative (referenced for non-goal framing).
- `docs/ELICITATION.md` — current state (52 lines, Phase 39 / SEED-001 framing); the file ELIC-02 will update in place.
- `docs/MIGRATION_V1_8.md` — historical context for the elicitation pipeline shape.

### Code surfaces touched / referenced
- `graphify/build.py` (lines 281–299) — `build()` elicitation merge semantics; ELIC-01's load-bearing invariant.
- `graphify/elicit.py` — Phase 39 state machine, `ELICITATION_SIDECAR_FILENAME`, sidecar shape.
- `graphify/harness_import.py` — `import_harness_path`, `import_harness_bytes`, `_sanitize_extraction`, `_sniff_format`.
- `graphify/__main__.py` (lines 2512–2580) — `import-harness` CLI argparse + output resolution.
- `graphify/serve.py` (lines 3724–3793) — MCP `import_harness` tool delegation.
- `graphify/security.py` — `MAX_HARNESS_IMPORT_BYTES`, `sanitize_harness_text` (referenced by guard tests; not re-tested).
- `graphify/output.py` — `resolve_output()` (trust-boundary doc references this contract).
- `graphify/harness_interchange.py` — `INTERCHANGE_SCHEMA_ID = "graphify.harness.interchange/v1"`; canonical-mapping doc describes this schema as-is.

### Existing test fixtures (extend, don't duplicate)
- `tests/test_elicit.py` — Phase 39 elicitation tests; ELIC-01 extends this module's patterns.
- `tests/test_harness_import.py` — Phase 40 import tests; HARN-02 guards extend here.
- `tests/test_harness_interchange.py` — schema round-trip tests.
- `tests/test_mcp_harness_io.py` — MCP-side harness IO; HARN-02 MCP guard test belongs adjacent.

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `graphify.elicit.merge_elicitation_into_build_inputs` — already merges sidecars into the build pipeline; ELIC-01 tests target its outputs.
- `graphify.harness_import.import_harness_path(strict=...)` — already supports a strict mode; HARN-02 vault-output guard can extend or wrap this entrypoint.
- `graphify.security.sanitize_harness_text` and `MAX_HARNESS_IMPORT_BYTES` — already enforce size + injection caps; guard tests reference but do not re-implement.
- `graphify.output.resolve_output` — single resolution path for `run`, `--obsidian`, `elicit`, `import-harness`, `doctor`. Vault-rooted-output guard hooks into the resolved path.

### Established Patterns
- **Pure unit tests, no network, no fs side effects outside `tmp_path`** (CLAUDE.md) — applies to all new tests.
- **`from __future__ import annotations`** as first import in every module — extend tests follow this.
- **Domain-specific exceptions with clear messages** (`ValueError(f"Blocked URL scheme ...")` style) — guard rejection messages must be actionable.
- **`[graphify]` stderr prefix** for warnings — vault-rooted-output rejection should follow the same convention if surfaced to the user.

### Integration Points
- `import-harness` CLI argparse currently lives inside `__main__.py` — vault-output guard either lives in `harness_import.py` (called by both CLI and MCP, single source of truth — preferred) or is duplicated at each entrypoint.
- The "no auto-invocation" guard test is a meta-test over the codebase — picks up any future regression where another command starts calling import.

</code_context>

<specifics>
## Specific Ideas

- "One observable improvement" framing from the roadmap is the operative constraint — resist any temptation to add a second test scenario or a second harness format under the same phase.
- The trust-boundary doc and the HARN-02 guard tests are designed to point at the same invariant from two directions (prose + executable) — they should be reviewed as a pair during planning.
- Inverse-import as a real round-trip is explicitly deferred (see Deferred Ideas below). This phase only locks down the existing surface.

</specifics>

<deferred>
## Deferred Ideas

- **Real inverse round-trip** (harness_export → harness_import → graph equality) — would be a meaningful capability but introduces new code surface; belongs in a future milestone's harness phase, not Phase 57.
- **New harness target format** (e.g., a second model's memory format) — orthogonal capability extension; deferred to a future "harness expansion" phase if/when a concrete second target is identified.
- **Sidecar on-disk schema assertions** (field ordering, schema version field) — overlaps with `validate.py` work and would expand ELIC-01 beyond "one scenario". Deferred.
- **Re-testing size caps and prompt-injection sanitization** — already covered by Phase 40; re-testing here would duplicate. Reference only.
- **Refactoring `docs/ELICITATION.md` into a milestone-current overview** — bigger writing job than ELIC-02 needs; deferred to a docs-pass phase if/when the doc grows further.

</deferred>

---

*Phase: 57-elicitation-harness-increment*
*Context gathered: 2026-05-03*
