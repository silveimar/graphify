# Phase 21: Profile Extension & Template Bootstrap - Context

**Gathered:** 2026-04-23
**Status:** Ready for planning

<domain>
## Phase Boundary

Extend `profile.yaml` with a `diagram_types:` section (ATOMIC update across `_VALID_TOP_LEVEL_KEYS`, `_DEFAULT_PROFILE`, `validate_profile()`, and the first reader in `seed.py` — all in Plan 21-01), and ship a CLI `graphify --init-diagram-templates [--force]` that writes 6 real `.excalidraw.md` stubs with `compress: false` locked as a one-way format door. Route the `gen-diagram-seed` tag write-back exclusively through `vault_adapter.py::compute_merge_plan`, enforced by a grep denylist test. No skill file, no mcp_excalidraw integration, no styled template art — those belong in Phase 22 and beyond.

</domain>

<decisions>
## Implementation Decisions

### Stub Content Shape
- **D-01:** Each of the 6 `.excalidraw.md` stubs written by `--init-diagram-templates` contains a **minimal empty scene** — valid frontmatter + empty `## Text Elements` block + `## Drawing` block with `{"type":"excalidraw","version":2,"source":"graphify","elements":[],"appState":{"viewBackgroundColor":"#ffffff","gridSize":null},"files":{}}`. Goal: lock the file format correctly; fill with content later. Styled style-guides (full 8-10 element scenes demonstrating the look of each diagram type) are **deferred** to a future phase.
- **D-02:** Frontmatter on every stub includes exactly: `excalidraw-plugin: parsed`, `compress: false`, and a tag list that includes the diagram-type name. Font family 5 (Excalifont) is declared in appState where applicable, even though no text elements exist yet — so later phases don't need to rewrite appState to pick up the brand font.

### Profile Atomicity (Plan 21-01 — ATOMIC rule)
- **D-03:** All four profile.py changes land in the same plan and same commit sequence: (1) add `"diagram_types"` to `_VALID_TOP_LEVEL_KEYS`, (2) extend `_DEFAULT_PROFILE` with the 6 built-in entries, (3) extend `validate_profile()` to validate each `diagram_types` entry's shape, (4) first reader in `seed.py` (template recommender) calls `load_profile()['diagram_types']`. No half-landed states.
- **D-04:** Each `diagram_types` entry has fields: `name` (str, required), `template_path` (str, optional — defaults to `Excalidraw/Templates/{name}.excalidraw.md`), `trigger_node_types` (list[str], optional default `[]`), `trigger_tags` (list[str], optional default `[]`), `min_main_nodes` (int, optional default `2`), `naming_pattern` (str, optional — template-able string). Missing optional fields degrade gracefully.
- **D-05:** Six built-in defaults: `architecture`, `workflow`, `repository-components`, `mind-map`, `cuadro-sinoptico`, `glossary-graph`.

### Template Recommender (seed.py)
- **D-06:** **Match semantics = OR.** A `diagram_types` entry matches a seed/community if ANY node in the seed has a type in `trigger_node_types` OR ANY tag in the community matches `trigger_tags`. Match also requires `|main_nodes| >= min_main_nodes`.
- **D-07:** **Tiebreak = highest `min_main_nodes` wins** when multiple entries match. Ties within that beat fall back to declaration order in the profile. This favors the most specific / richest type.
- **D-08:** **Resolution order:** profile `diagram_types` match (per D-06/D-07) → existing Phase 20 layout heuristic via `_TEMPLATE_MAP` → built-in fallback. Never throws on a missing `diagram_types:` section or absent profile.

### CLI `--init-diagram-templates` (Plan 21-02)
- **D-09:** **Path default:** when a profile entry omits `template_path`, or no profile exists, the stub is written to `{vault_root}/Excalidraw/Templates/{name}.excalidraw.md` — the Obsidian Excalidraw plugin convention.
- **D-10:** **Partial-state behavior without `--force` = idempotent fill-in.** Write missing stubs, skip any that already exist, print `Wrote N, skipped M (already exist). Use --force to overwrite.` No abort on partial state.
- **D-11:** **`--force`** overwrites all stubs unconditionally. Single flag, global scope — no per-type control.
- **D-12:** When `diagram_types:` declares a subset (e.g., only 3 types), `--init-diagram-templates` writes only those 3 stubs. Built-in defaults kick in only when the section is absent entirely.

### Tag Write-Back Trigger
- **D-13:** `gen-diagram-seed` tag write-back is **triggered during `graphify --diagram-seeds`**, not during `--init-diagram-templates`. Init only writes stubs — it performs zero vault note writes. After `build_all_seeds` identifies user seeds, for each main_node whose source note exists in the vault, the tag `gen-diagram-seed` is merged into that note's frontmatter via `vault_adapter.py::compute_merge_plan`.
- **D-14:** The grep denylist test scope: forbids `Path.write_text`, `write_note_directly`, and `open(..., 'w')` calls targeting vault note paths (`.md` files under the configured vault_dir) anywhere in `seed.py`, `export.py`, or `__main__.py`. Writes to `Excalidraw/Templates/*.excalidraw.md` by the init command are allowed (templates, not notes).
- **D-15:** `lzstring` package import is also forbidden by the same denylist test — enforces the `compress: false` one-way door.

### Claude's Discretion
- Exact tag-merge call shape into `compute_merge_plan` (union vs append), reported counts formatting, and argparse wiring — Claude may choose idiomatic patterns consistent with existing CLI commands.
- Whether to cache the profile-to-recommender resolution per seed-build run or recompute per seed — performance detail.
- Whether to add an optional `trigger_mode: and|or` per-entry override (noted as a possibility in discussion; default `or` per D-06). Claude may include this if it comes for free, else skip.

### Folded Todos
- **Create Graphify master key files in work vault** (`todos/create-master-keys-work-vault.md`, relevance 0.6). Matched on keywords `graphify, files, vault, templates, keys`. Folded into Phase 21 scope because `--init-diagram-templates` produces exactly the "master key" Excalidraw template files the todo describes. Acceptance: running `graphify --init-diagram-templates` in the work vault produces the 6 templates at the D-09 default path.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Roadmap + Requirements
- `.planning/ROADMAP.md` §Phase 21 — goal, cross-phase rules, success criteria, plan breakdown
- `.planning/REQUIREMENTS.md` — PROF-01, PROF-02, PROF-03, PROF-04, TMPL-01, TMPL-02, TMPL-03, TMPL-04, TMPL-05, TMPL-06
- `.planning/PROJECT.md` — Ideaverse Integration vision, backward-compatibility constraint, template-injection-as-data model

### Prior Phase Decisions (Must Read)
- `.planning/phases/20-diagram-seed-engine/20-CONTEXT.md` — seed build pipeline + template recommender call site
- `.planning/phases/20-diagram-seed-engine/20-01-PLAN.md` — `detect_user_seeds`, `possible_diagram_seed` auto-tagging source
- `.planning/phases/20-diagram-seed-engine/20-02-PLAN.md` — `seed.py` orchestrator, `_TEMPLATE_MAP`, layout heuristic (the fallback layer in D-08)
- `.planning/phases/19-vault-promotion-script-layer-b/19-CONTEXT.md` — `vault_adapter.py::compute_merge_plan` invariants
- `.planning/codebase/STRUCTURE.md` — module roles
- `.planning/codebase/CONVENTIONS.md` — atomic commit + test discipline

### Implementation Anchors (Must Read)
- `graphify/profile.py` — lines 36-80: `_DEFAULT_PROFILE`, `_VALID_TOP_LEVEL_KEYS`, `validate_profile()` at line 174
- `graphify/seed.py` — `_TEMPLATE_MAP` at line 44; `_VALID_LAYOUT_TYPES`; existing `suggested_template` output at lines 270, 359-360 (the insertion point for D-08 profile-first resolution)
- `graphify/vault_adapter.py` — `compute_merge_plan` (the ONLY allowed vault note write path per D-13)
- `graphify/__main__.py` — `_PLATFORM_CONFIG`, existing `--diagram-seeds` flag (Phase 20), argparse patterns

### External
- Obsidian Excalidraw plugin docs — `.excalidraw.md` file format spec (frontmatter + Text Elements + Drawing fence). No URL captured; format is documented in plugin README.

### Security / Threat Model
- `SECURITY.md` — path confinement rules for `graphify-out/` and vault writes
- Existing Phase 20 SECURITY.md — precedent for threat registration and denylist test pattern (see D-14/D-15)

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `graphify/profile.py::_deep_merge` (line 121) — use when layering user profile over defaults so missing `diagram_types` fields inherit from built-ins
- `graphify/profile.py::safe_frontmatter_value` (line 376), `_dump_frontmatter` (line 449) — reuse for writing `.excalidraw.md` frontmatter
- `graphify/profile.py::validate_vault_path` (line 355) — use to confine template writes under vault_dir
- `graphify/seed.py::_TEMPLATE_MAP` + `suggested_template` output field — already wired into seed dicts; extend, don't replace
- `graphify/vault_adapter.py::compute_merge_plan` — sole authorized vault note writer (D-13/D-14 enforcement)
- Existing `graphify/builtin_templates/*.md` directory pattern — if stubs ship as pkg-data, colocate at `graphify/builtin_templates/diagram/*.excalidraw.md`. Open question left to planner: ship as files vs generate in code — D-01 (minimal empty) makes generation-in-code trivial, so probably no pkg-data needed.

### Established Patterns
- Profile top-level keys follow the existing naming (lowercase, underscore) — `diagram_types` fits
- `validate_profile()` returns `list[str]` of error messages (not raising) — D-03's validator extension follows same shape
- CLI flags in `__main__.py` are argparse subcommand-free booleans (`--diagram-seeds`, `--obsidian`, etc.) — `--init-diagram-templates` and `--force` follow the same pattern
- Tests use `tmp_path`, no network, one test file per module (`tests/test_profile.py`, `tests/test_seed.py`, new `tests/test_init_templates.py` likely)

### Integration Points
- `seed.py` template recommender: insert profile-first resolution layer before the existing `_TEMPLATE_MAP` fallback (around lines 270 + 359)
- `__main__.py` CLI dispatch: new `--init-diagram-templates` and `--force` flags; after `build_all_seeds` runs, call the tag-write-back routine via `compute_merge_plan`
- `tests/`: grep denylist test may live in `tests/test_architecture.py` (if exists) or a new `tests/test_denylist.py`

</code_context>

<specifics>
## Specific Ideas

- Roadmap explicitly names 6 diagram types with specific identifiers — do not rename: `architecture`, `workflow`, `repository-components`, `mind-map`, `cuadro-sinoptico`, `glossary-graph`.
- `compress: false` is a one-way door decision (from ROADMAP.md Phase 21 cross-phase rules) — never revisit without opening a new phase.
- Scene JSON shape is fixed by the roadmap success criterion: `{"type":"excalidraw","version":2,"source":"graphify","elements":[...],"appState":{"viewBackgroundColor":"#ffffff","gridSize":null},"files":{}}` — match byte-for-byte keys, values may vary per stub.

</specifics>

<deferred>
## Deferred Ideas

- **Styled style-guide templates** — full 8-10 element scenes with colors, fonts, spacing that demonstrate each diagram type's visual character. User wants this as its own future phase. Candidate scope: after Phase 22 ships the skill and the first real diagrams exist, style the templates based on what works. Do NOT bundle with Phase 21.
- **Per-entry `trigger_mode: and|or` override** — considered, declined for v1. Default OR (D-06) is expected to be sufficient. Revisit if real usage shows false matches.
- **`obsidian.excalidraw_templates_dir` profile key** — considered, declined. Default path hardcoded per D-09 (Excalidraw/Templates/{name}.excalidraw.md) suffices; can be promoted to a profile key later if users ask.
- **Template recommender scoring ("most trigger matches wins")** — considered, declined. D-07 min_main_nodes tiebreak is more predictable.

### Reviewed Todos (not folded)
- None — the one matched todo was folded (see D-folded in decisions).

</deferred>

---

*Phase: 21-profile-extension-template-bootstrap*
*Context gathered: 2026-04-23*
