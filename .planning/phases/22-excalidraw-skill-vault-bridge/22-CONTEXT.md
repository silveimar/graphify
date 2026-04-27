# Phase 22: Excalidraw Skill & Vault Bridge - Context

**Gathered:** 2026-04-27
**Status:** Ready for planning

<domain>
## Phase Boundary

Ship a deployable `excalidraw-diagram` skill plus install/uninstall wiring that orchestrates the full seeds → Excalidraw → vault pipeline. The pure-Python `.excalidraw.md` fallback path must be complete and tested before any mcp_excalidraw integration (SKILL-06 ordering invariant). `mcp_excalidraw` is never a required Python import — graphify's Python code never imports it. Skill install/uninstall must be idempotent.

In scope: `graphify/skill-excalidraw.md` (full 7-step orchestration prompt), pure-Python `.excalidraw.md` generation from SeedDict + template, new `excalidraw` entry in `_PLATFORM_CONFIG`, `graphify install excalidraw` / `graphify uninstall excalidraw` handlers, packaging via `MANIFEST.in` + `pyproject.toml`, install/uninstall/idempotency tests.

Out of scope (deferred to v1.6+): multi-seed diagrams, in-place diagram editing, layout customization beyond the 6 built-in `diagram_types`, alternate render targets (SVG-only, PNG export, etc.), automatic `.mcp.json` editing on the user's behalf.

</domain>

<decisions>
## Implementation Decisions

### Pure-Python Fallback Layout
- **D-01:** When `mcp_excalidraw` is unavailable, the fallback dispatches on `profile.diagram_types[*].layout_type`. Each layout_type maps to a small deterministic algorithm (e.g., grid for `flow`, hierarchical for `tree`, concentric for `cluster`) so output is stable for unit tests.
- **D-02:** Fallback algorithms are deterministic — no randomness, no seeded RNG, no external numerical libs. Coordinates are integer-rounded so two runs against the same SeedDict + profile produce byte-identical scene JSON.
- **D-03:** The fallback reuses `graphify/excalidraw.py::render_stub` / `write_stubs` primitives where possible. New layout helpers live in the same module (e.g., `graphify/excalidraw.py::layout_for(layout_type, nodes, edges) -> elements`).

### Install Surface (`_PLATFORM_CONFIG`)
- **D-04:** `excalidraw` becomes a new top-level key in `_PLATFORM_CONFIG` alongside `claude`/`codex`/etc. Invoked as `graphify install excalidraw` and `graphify uninstall excalidraw` (positional, matching every existing platform). The roadmap's prose `--excalidraw` reads as a label; the surface is the positional form.
- **D-05:** New entry shape: `skill_file: "skill-excalidraw.md"`, `skill_dst: Path(".claude") / "skills" / "excalidraw-diagram" / "SKILL.md"`, `claude_md: False`, `commands_enabled: False`, `supports: ["obsidian", "code"]`. Distinguishes it from assistant-host platforms while staying in the same registry.
- **D-06:** Install/uninstall are idempotent: install creates parent dirs and overwrites only if content differs; uninstall removes the file if present, no-op otherwise. Mirrors `_run_install_for_platform` / `_run_uninstall_for_platform` patterns already in `__main__.py`.
- **D-07:** Existing platform entries (claude/codex/...) are NOT modified — no side-effects on their install paths. Tests assert this explicitly.

### Vault Write Semantics
- **D-08:** When the skill writes the generated diagram to the vault and the target path already exists: refuse by default and report cleanly (skill exits without writing, prints the colliding path). User can re-run the skill flow with an explicit `force: true` argument or by deleting/moving the existing file. Matches Phase 21's `--init-diagram-templates` idempotency stance.
- **D-09:** The output path comes from `profile.yaml`'s `diagram_types[].output_path` (or analogous field — to be confirmed in research) with a built-in fallback to `Excalidraw/Diagrams/` when the field is absent. Same diagram_types object that already provides `template_path` in Phase 21 — one profile entry, two path slots (template input + diagram output).
- **D-10:** Filename pattern: `{topic}-{layout_type}.excalidraw.md`, where `{topic}` is derived from the seed (slugified), `{layout_type}` from the profile entry. Slug rules reuse `graphify/profile.py::safe_frontmatter_value`-style sanitization where applicable.

### `.mcp.json` Delivery
- **D-11:** The `.mcp.json` snippet (obsidian + excalidraw servers) lives **inside `skill-excalidraw.md`** as a fenced, copy-pasteable block. Graphify never reads, writes, or merges the user's `.mcp.json` — that file belongs to the user. Idempotency is automatic (no file write = nothing to be non-idempotent about).
- **D-12:** SKILL-05's "guard list" is a literal section in `skill-excalidraw.md` and includes at minimum: `compress: false` assertion, no LZ-String, no label-derived element IDs, no direct frontmatter writes from the skill (use the existing renderer), no multi-seed in v1.5.

### Skill Orchestration (locked from roadmap, restated for downstream)
- **D-13:** The 7-step pipeline in `skill-excalidraw.md` is fixed: (1) `list_diagram_seeds` → show user; (2) user selects seed; (3) `get_diagram_seed(seed_id)` → SeedDict; (4) read matching template from vault via mcp-obsidian (or pure-Python file read in fallback); (5) build diagram via `mcp_excalidraw` OR pure-Python fallback if unavailable; (6) export scene → write to vault at the resolved output path; (7) report `seed_id`, node count, template used, vault path written.
- **D-14:** Style rules locked: Excalifont (font family 5) for node labels, `strokeColor: "#1e1e2e"`, `backgroundColor: "transparent"`, `compress: false` frontmatter. These are restated in the skill's "style-matching rules" section.

### Claude's Discretion
- Exact public API of new layout helpers (`layout_for`, `_grid_layout`, `_tree_layout`, etc.) — researcher/planner picks names that fit existing module conventions.
- Whether layout primitives live in `graphify/excalidraw.py` or a new submodule (`graphify/excalidraw/layout.py`) — module size threshold call.
- Specific test fixture shape (which layout_types get explicit fixtures vs parametrized) — planner decides based on existing `tests/test_excalidraw.py` patterns.
- Phrasing of the `force` argument the user passes to the skill on collision (skill prompt detail, not a CLI flag).

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Phase scope
- `.planning/ROADMAP.md` §"Phase 22: Excalidraw Skill & Vault Bridge" — goal, success criteria, plan stubs, cross-phase rules.
- `.planning/REQUIREMENTS.md` §SKILL-01..SKILL-06 — the 6 REQ-IDs this phase satisfies.

### Upstream phases (locked decisions to honor)
- `.planning/phases/20-diagram-seed-engine/20-CONTEXT.md` — SeedDict shape, MCP tool contract.
- `.planning/phases/21-profile-extension-template-bootstrap/21-CONTEXT.md` — `diagram_types` profile section, template stub format, `compress: false` one-way door.

### Existing code (must read before planning)
- `graphify/excalidraw.py` — `render_stub`, `write_stubs`; the renderer to extend with layout primitives.
- `graphify/seed.py` — `build_seed`, SeedDict construction; recommender from Phase 21.
- `graphify/serve.py` §L2553–L3354 — `_run_list_diagram_seeds_core`, `_run_get_diagram_seed_core`, MCP tool registration.
- `graphify/profile.py` — `validate_profile`, `safe_frontmatter_value`, `validate_vault_path`; `diagram_types` validators.
- `graphify/__main__.py` §L49–L120 (`_PLATFORM_CONFIG`), §L238–L340 (install/uninstall handlers), §L1427–L1453 (`--init-diagram-templates` dispatch as a precedent).
- `MANIFEST.in`, `pyproject.toml` `package_data` — packaging the new `skill-excalidraw.md` so it ships with the wheel.

### Project rules
- `CLAUDE.md` — "no new required Python dependencies", testing conventions, security/path-confinement rules.
- `SECURITY.md` — path confinement and label sanitization rules; vault write paths must pass through `validate_vault_path`.

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `graphify/excalidraw.py::render_stub(diagram_type)` — already produces a single `.excalidraw.md` body string with the correct frontmatter, `## Text Elements` block, and `## Drawing` block. The fallback path will reuse this for the file shell and inject computed `elements[]` into the scene JSON.
- `graphify/excalidraw.py::write_stubs(...)` — atomic vault write with idempotency. Pattern to follow for the diagram-write step (D-08, D-09).
- `graphify/profile.py::safe_frontmatter_value`, `validate_vault_path` — sanitization primitives already imported by `excalidraw.py`. Use for naming pattern slug + path confinement.
- `graphify/serve.py` MCP tool plumbing — the skill calls these from outside Python; no direct import needed in graphify code.

### Established Patterns
- `_PLATFORM_CONFIG` is the single source of truth for install destinations. Adding `excalidraw` here propagates to every install/uninstall code path that iterates the dict (e.g., `tests/test_install.py` parametrized tests, the `set` comprehension over `cfg["skill_dst"]` for global cleanup at __main__.py:1157).
- Idempotent file writers compare existing content before writing (precedent: `_init_diagram_templates` flow at __main__.py:1427+).
- Tests are pure unit tests, no network, side-effects confined to `tmp_path`. New tests follow `tests/test_<module>.py` naming.
- Skill files are packaged via `MANIFEST.in` and `pyproject.toml` `package_data` — both must be updated when adding `skill-excalidraw.md`.

### Integration Points
- `_PLATFORM_CONFIG` (new entry) → install/uninstall handlers (no change needed if they iterate the dict generically — verify in research).
- `pyproject.toml` `package_data` glob — confirm `skill-*.md` glob already covers `skill-excalidraw.md` so packaging is automatic; otherwise add it explicitly.
- `MANIFEST.in` — same glob check.
- The skill itself (runtime artifact, not Python) calls `mcp_excalidraw` and `mcp_obsidian` — both are user-side MCP servers configured in the user's `.mcp.json`. Graphify ships the SKILL.md prompt only.

</code_context>

<specifics>
## Specific Ideas

- The skill must surface "fallback path engaged" to the user when `mcp_excalidraw` is unavailable — the user should know they got the degraded (deterministic) layout, not the polished one.
- Research should confirm whether existing `_run_install_for_platform` / `_run_uninstall_for_platform` need modification to handle a platform without `claude_md` or `commands_enabled`, or whether the dict-driven loop already supports this (Phase 19 added `antigravity` which is similar). If similar, no handler changes — only `_PLATFORM_CONFIG` grows.
- The `force` argument to the skill (D-08) is a *skill-level* argument the agent passes when invoking, not a graphify CLI flag. Document this clearly in `skill-excalidraw.md`.

</specifics>

<deferred>
## Deferred Ideas

- **Auto-merge `.mcp.json`** — the safer path is to document the snippet inside SKILL.md (D-11). If users repeatedly request automatic merging, revisit in v1.6+ as `graphify mcp install` (separate command, never amends user JSON destructively).
- **Multi-seed diagrams** — combining several seeds into one Excalidraw scene. Out of scope for v1.5; needs its own diagram type in `profile.diagram_types` and a new MCP tool.
- **Layout customization beyond `layout_type`** — e.g., user-tunable spacing, edge routing styles. Future profile fields.
- **Force-directed / spring layouts** for the fallback — adds a numerical dependency footprint we've explicitly avoided. Revisit only if deterministic per-type layouts produce visibly bad results in practice.
- **Inline overwrite-vs-cancel prompt at write time** — would make the skill conversational at step 6. Refuse-by-default + `force` (D-08) is preferred for v1.5; revisit if collisions are common.
- **Auto-suffix on collision** (`-2`, `-3`) — explicitly rejected for v1.5 (vault clutter risk). User deletes/moves and re-runs, or passes `force`.

</deferred>

---

*Phase: 22-excalidraw-skill-vault-bridge*
*Context gathered: 2026-04-27*
