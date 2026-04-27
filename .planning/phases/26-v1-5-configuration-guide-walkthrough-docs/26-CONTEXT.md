# Phase 26: v1.5 Configuration Guide & Walkthrough Docs - Context

**Gathered:** 2026-04-27
**Status:** Ready for planning

<domain>
## Phase Boundary

Deliver a single-file user-facing guide (`CONFIGURING_V1_5.md`) that walks a new user end-to-end through the v1.5 pipeline (`vault-promote` → `--diagram-seeds` → `--init-diagram-templates` → `install excalidraw` → skill invocation) on a sample vault, ships a complete annotated example `.graphify/profile.yaml` with one custom `diagram_type` beyond the 6 built-ins, documents the `list_diagram_seeds` and `get_diagram_seed` MCP tools (invocation shape, return schema, `_resolve_alias` traversal-defense behavior), and is reachable from `README.md`.

**In scope:** Authoring `CONFIGURING_V1_5.md`; an example profile snippet with annotated D-06 gating + D-07 tiebreak rationale; an MCP integration section keyed to `serve.py:2553+`; a one-line link insertion in `README.md`.

**Out of scope:** New features, code changes to `seed.py`/`__main__.py`/`serve.py`, new test fixtures, sample-vault repo content, screenshot generation, README restructuring beyond the link insertion, translation of new content into the locale READMEs (`README.ja-JP.md`, `README.ko-KR.md`, `README.zh-CN.md` — those follow downstream).

</domain>

<decisions>
## Implementation Decisions

### Guide Location & Filename
- **D-01:** Guide lives at repo root as `CONFIGURING_V1_5.md` (uppercase, snake-case after `CONFIGURING_`). Matches existing convention — `INSTALLATION.md`, `ARCHITECTURE.md`, `SECURITY.md`, `CHANGELOG.md`, `CLAUDE.md` are all top-level. No `docs/` directory exists today; this phase does NOT introduce one.

### Sample Vault Approach
- **D-02:** Walkthrough uses an **inline-described synthetic vault** — no in-repo fixture, no external vault dependency. Describe the vault structure with a tree diagram (e.g., `Atlas/Maps/`, `Atlas/Dots/Things/`, 5–10 illustrative notes) and show synthetic note snippets in fenced code blocks.
- **D-03:** Reader copies snippets into their own vault to follow along; the guide does NOT promise an executable demo path. This keeps the doc maintenance-free as commands evolve and avoids adding `examples/` to the repo footprint.

### Custom diagram_type Example (DOCS-02)
- **D-04:** The custom diagram_type shown beyond the 6 built-ins is **`decision-tree`**.
- **D-05:** D-06 gating annotation: fire only when the source node has **≥3 outbound branches** (concrete, defensible threshold readers can adapt).
- **D-06:** D-07 tiebreak annotation: when multiple candidate nodes pass D-06 gating, prefer the node with **highest betweenness centrality** (justifies "this node is the natural decision pivot").
- **D-07:** The example profile is COMPLETE — every required `diagram_types:` field present, plus the new `decision-tree` entry — not a stub. Frontmatter for built-in types is annotated inline (one-line comments) explaining the D-06 / D-07 mechanism so readers transfer the pattern to their own custom types.

### MCP Tool Docs Structure (DOCS-03)
- **D-08:** A dedicated `## MCP Tool Integration` section near the end of `CONFIGURING_V1_5.md` covers both tools. NOT a separate appendix file, NOT inlined per pipeline step.
- **D-09:** Per tool: invocation shape (tool name + argument schema), return schema (top-level keys, types), and a `_resolve_alias` traversal-defense subsection citing the closure-local pattern at `serve.py:1234-1250` (chat core canonical reference) and noting the same pattern repeats at `serve.py:1399-1403, 1526, 1815, 1990, 2590, 2686`.
- **D-10:** Section is written so an agent author can integrate the tools **without reading source** — DOCS-03 acceptance criterion. Minimum content: tool signature, one realistic invocation example with arguments, one realistic return-value example, one paragraph on alias-cycle defense.

### README Integration (DOCS-04)
- **D-11:** Insert a new third-level subsection `### v1.5 Configuration Guide` directly under the existing `## Obsidian vault adapter (Ideaverse integration)` H2 (currently README.md:329). v1.5 features (vault-promote, diagram-seeds, init-diagram-templates, excalidraw skill) are all extensions of the Obsidian adapter — content stays grouped.
- **D-12:** The subsection is a **one-line pitch + link** to `CONFIGURING_V1_5.md`, not a duplicated abstract. Avoid drift between README and guide.
- **D-13:** Place the subsection AFTER the existing `### Vault Promotion — graphify vault-promote` subsection (README.md:378) so the chronological install→use→configure flow reads naturally.

### Tone & Style
- **D-14:** Match existing `INSTALLATION.md` / `ARCHITECTURE.md` tone — direct, command-first, fenced bash blocks, no marketing language, no emojis. CLAUDE.md project conventions apply (4-space indent in any embedded Python; YAML examples must be valid).
- **D-15:** No screenshots in this phase. Keep guide pure text + code blocks; defer visual aids to a future enrichment phase.

### Claude's Discretion
- Internal section ordering of the walkthrough (the four pipeline commands run in a fixed order, so this is mostly already determined by the pipeline itself).
- Exact wording, headings beyond the major H2s above, troubleshooting/FAQ depth (can be omitted entirely if it adds bulk without value).
- Whether to include a brief "What's new in v1.5" framing paragraph at the top (recommended; keep it under 5 lines).

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Phase scope & requirements
- `.planning/ROADMAP.md` §"Phase 26" (lines 257–268) — goal, success criteria, requirements list
- `.planning/REQUIREMENTS.md` lines 33–36 — DOCS-01 through DOCS-04 verbatim text
- `.planning/REQUIREMENTS.md` lines 71–74 — REQ→Phase mapping table (currently "TBD" — must be updated to Phase 26 during execution)

### v1.5 pipeline source surfaces (the things being documented)
- `graphify/__main__.py` lines 1192–1478 — CLI dispatch for `--diagram-seeds`, `--init-diagram-templates` (Phase 20 SEED-01..08, Phase 21 TMPL-01..05)
- `graphify/__main__.py` lines 2224–2255 — `vault-promote` subcommand (Phase 19, Layer B)
- `graphify/seed.py` — diagram seed generation, gating logic (D-06/D-07 referenced in this guide)
- `graphify/serve.py` lines 2553+ — `list_diagram_seeds` (`_run_list_diagram_seeds_core`) and `get_diagram_seed` (`_run_get_diagram_seed_core`) MCP tool cores
- `graphify/serve.py` lines 1234–1250 — canonical `_resolve_alias` closure pattern (chat core); the traversal-defense story to document for DOCS-03

### Existing user-facing docs (style + insertion targets)
- `README.md` §"Obsidian vault adapter (Ideaverse integration)" line 329 — the H2 the new subsection nests under
- `README.md` §"Vault Promotion — `graphify vault-promote`" line 378 — the existing v1.5-adjacent subsection the new link follows
- `INSTALLATION.md`, `ARCHITECTURE.md`, `SECURITY.md` — root-level docs to mirror in tone, structure, and fenced-block formatting
- `CLAUDE.md` §"Architecture" + §"Multi-platform support" — confirms the v1.5 surface area and platform-config terminology used in the guide

### Project context
- `.planning/PROJECT.md` — "Ideaverse Integration — Configurable Vault Adapter" framing for the guide intro paragraph
- `CLAUDE.md` lines 90+ (project section) — declared constraints (no new required deps, backward compat, security via `security.py`)

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- **Existing root-level docs convention:** `INSTALLATION.md`, `ARCHITECTURE.md`, `SECURITY.md` provide a copy-pasteable structural template — opening summary paragraph, fenced bash blocks, no nav/TOC scaffolding needed.
- **README §"Obsidian vault adapter" yaml block (lines 343–365):** existing example `.graphify/profile.yaml` with `folder_mapping`, `naming`, `merge`, `mapping_rules` keys. The Phase 26 example profile EXTENDS this shape (must remain consistent — same keys, same indentation) and adds the v1.5 `diagram_types:` block on top.
- **`serve.py` MCP tool core functions are already self-documenting** via parameter names and return-dict keys at lines 2562 (`_run_list_diagram_seeds_core`) and 2667 (`_run_get_diagram_seed_core`). Doc author can read signatures + return assembly to derive the schema without instrumentation.

### Established Patterns
- **Single-file user-facing guides at repo root** (no `docs/` tree). Phase 26 must NOT introduce `docs/`.
- **Fenced bash blocks for CLI examples** with a leading comment line stating intent, used throughout README.md (e.g., lines 367–375).
- **Annotated YAML examples** with inline `# comments` explaining each key — the README precedent at lines 343–365 is the style template.
- **`[graphify]`-prefixed stderr lines** in CLI output (per CLAUDE.md "Logging" conventions). Any sample command output in the guide should include these prefixes verbatim to match real terminal output.
- **`_resolve_alias` is a closure-local pattern** repeated 7+ times in `serve.py` — every MCP tool that accepts a node-id argument re-implements the same alias-resolution + cycle-guard logic. The doc explains it ONCE in the MCP section as a cross-cutting traversal-defense behavior, not per-tool.

### Integration Points
- **Pipeline command order is fixed by the codebase** — `vault-promote` (creates/refreshes vault) → `--diagram-seeds` (emits seeds JSON to `graphify-out/seeds/`) → `--init-diagram-templates` (writes template stubs to vault) → `install excalidraw` (skill install) → skill invocation. The walkthrough must follow this exact order.
- **The example `.graphify/profile.yaml` must be parseable by the existing profile loader** (PyYAML, optional dep). Cannot include any field the loader rejects. Profile schema lives in the profile-loader code path (Phase 21 TMPL deliverables) — verify against actual loader before publishing.
- **README.md insertion point** is line 378 (after the `### Vault Promotion` subsection, before line 399's `## Worked examples` H2). New subsection lives in this gap.

</code_context>

<specifics>
## Specific Ideas

- **Decision-tree custom type** is the chosen DOCS-02 illustration: D-06 gating threshold ≥3 outbound branches, D-07 tiebreak by betweenness centrality. Reader walks away knowing how to invent their own custom type because they've seen a fully-specified non-built-in worked example.
- **MCP section is reference-quality** — agent authors should be able to call `list_diagram_seeds` and `get_diagram_seed` from a fresh repo without ever opening `serve.py`. Treat DOCS-03 as a contract: anything an integrator needs is in the guide.
- **Roadmap stale-stub flag:** `.planning/ROADMAP.md` line 268 lists Phase 26 plans as `23-01-PLAN.md — Patch dedup.py edge-merge...` — that's a copy-paste artifact from Phase 23, same defect class as the Phase 25 issue logged in obs `3120`. Planner should overwrite this stub with the actual Phase 26 plan name.

</specifics>

<deferred>
## Deferred Ideas

- **Locale README updates** (`README.ja-JP.md`, `README.ko-KR.md`, `README.zh-CN.md`) — out of scope here; track as a follow-up translation phase or backlog item.
- **Screenshots / animated GIFs** in the guide — defer to a future docs-polish phase.
- **`docs/` directory + multi-guide index** — defer until there are ≥3 distinct user-facing guides that warrant a tree. Not justified by Phase 26 alone.
- **Executable in-repo sample vault under `examples/v1_5_walkthrough/`** — explicitly declined here (D-02). If the team later wants an executable demo, that's its own phase (fixture authoring + CI smoke test to keep it from rotting).
- **Troubleshooting / FAQ section depth** — left to Claude's discretion in this phase; if substantive content emerges, fine; if not, omit rather than pad.
- **Roadmap entry stub fix for Phase 26** (line 268 of `.planning/ROADMAP.md`) — the planner should fix this as part of the plan-creation step or note it for a roadmap-hygiene cleanup.

</deferred>

---

*Phase: 26-v1-5-configuration-guide-walkthrough-docs*
*Context gathered: 2026-04-27*
