# Phase 2: Template Engine - Context

**Gathered:** 2026-04-11
**Status:** Ready for planning

<domain>
## Phase Boundary

A pure rendering layer that turns graph nodes and communities into note *strings* (frontmatter + body) using configurable templates. This phase delivers `graphify/templates.py` — a standalone module that loads built-in and user-supplied templates, pre-renders sections (frontmatter, connections, wayfinder, dataview, members) as string blocks, and substitutes them via `string.Template.safe_substitute()`.

The engine produces strings and target filenames. It does NOT write files, classify nodes into note types, or merge with existing notes — those belong to Phase 3 (classification), Phase 4 (merge), and Phase 5 (integration/IO).

</domain>

<decisions>
## Implementation Decisions

### Placeholder language (D-17)
- **D-17:** Templates use `string.Template.safe_substitute()` with `${var}` syntax. Unknown placeholders are left untouched so user templates can freely embed Templater tokens (`<% tp.date.now() %>`, `<% tp.file.title %>`) that resolve at note-open time inside Obsidian
- **D-18:** Templates receive **pre-rendered sections** as scalars, not low-level lists. The substitution context exposes: `${label}`, `${frontmatter}`, `${wayfinder_callout}`, `${connections_callout}`, `${members_section}` (MOC-only), `${dataview_block}` (MOC-only), `${metadata_callout}`, `${body}`. Each section variable is an **empty string when absent** so templates stay declarative with no conditional logic
- **D-19:** `resolve_filename(label, convention)` is the single entry point used for BOTH disk filenames and wikilink targets. Engine-owned coupling — guarantees `[[target]]` always resolves because wikilinks and filenames go through the same function

### Template discovery and override (D-20)
- **D-20:** User templates live at `.graphify/templates/{moc,thing,statement,person,source,community}.md`. Strict per-type filenames — no profile mapping layer. At render time: if `<vault>/.graphify/templates/<type>.md` exists and validates, use it; otherwise use the built-in. Path resolution goes through `security.py` path confinement
- **D-21:** Built-in templates ship as real markdown files under `graphify/builtin_templates/{moc,thing,statement,person,source,community}.md`, loaded via `importlib.resources`. Real `.md` files are reviewable in git, can embed callouts and dataview blocks without Python triple-string escaping. `pyproject.toml` adds `builtin_templates/*.md` to package-data
- **D-22:** Template validation uses the Phase 1 pattern: `validate_template(text: str, required: set[str]) -> list[str]` returns an error list. When a user template is invalid (unknown `${var}` that isn't a known Templater `<% %>` token, or missing a required placeholder like `${frontmatter}`), the engine logs `[graphify] template error: thing.md — unknown ${foo}` to stderr and **falls back to the built-in for that type** while continuing to render the rest. Follows Phase 1's "validate, report, don't crash" convention

### Frontmatter construction (D-23)
- **D-23:** Frontmatter is built as a Python `dict[str, Any]` with **insertion-order = emission order**, then dumped via an internal `_dump_frontmatter(d: dict) -> str` helper that produces YAML by hand. No PyYAML dependency on the render path. Hand-rolled dumper handles: scalars via `safe_frontmatter_value` (Phase 1), YAML **block-form lists** (`tags:\n  - a\n  - b`) for list-valued fields, and date-only ISO (`2026-04-11`) for `created:`
- **D-24:** Ideaverse frontmatter field order: `up`, `related`, `collections`, `created`, `tags`, then graphify-owned fields (`type`, `file_type`, `source_file`, `source_location`, `community`, `cohesion` for MOCs). Block-form lists are required for Properties UI chip rendering and Obsidian Linter compatibility
- **D-25:** **List-valued fields** (YAML block lists): `up`, `related`, `collections`, `tags`. **Scalar fields** (for Supercharged Links CSS selectors): `type`, `file_type`, `source_file`, `source_location`, `community`, `created`, `cohesion`
- **D-26:** `up:` is still a list (even when it contains one wikilink) for Ideaverse consistency: `up:\n  - "[[Parent MOC]]"`. Wikilinks inside frontmatter scalars are quoted because `[` is a YAML-special char (Phase 1 `safe_frontmatter_value` handles this)
- **D-27:** `created:` on first render = ISO date of the graphify run (today in `YYYY-MM-DD`). Phase 4's `preserve_fields` list keeps it stable across re-runs

### MOC body composition (D-28)
- **D-28:** Dataview query is **fully configurable via profile** at `obsidian.dataview.moc_query`. The profile value is itself a `${}`-substituted template string. Default: `TABLE file.folder as Folder, type, source_file\nFROM #community/${community_tag}\nSORT file.name ASC`. The engine substitutes `${community_tag}` (and `${folder}`) before emitting the ```` ```dataview ```` block. Users override to match Sefirot/Ideaverse query style with `WHERE`, `LIMIT`, custom columns
- **D-29:** Below-threshold communities (MAP-05) render as a `> [!abstract] Sub-communities` callout inside the parent MOC. Each mini-community becomes a nested bullet: `- **<group name>:** [[member1]], [[member2]], [[member3]]`. No separate MOC file is written for below-threshold communities — they exist only as inline listings in their parent
- **D-30:** MOC member lists are **grouped by note type** using nested callouts: `> [!info] Things`, `> [!info] Statements`, `> [!info] People`, `> [!info] Sources`. Each group lists members as `- [[Wikilink]]`. Groups with zero members are omitted. This keeps 40+ member communities scannable
- **D-31:** MOC section order in built-in template: `${frontmatter}` → `# ${label}` → `${wayfinder_callout}` → `${members_section}` (grouped callouts) → Sub-communities callout (if any) → `${dataview_block}` → `${metadata_callout}`

### Non-MOC note body composition (D-32)
- **D-32:** Thing/Statement/Person/Source built-in templates share the same scaffold: `${frontmatter}` → `# ${label}` → `${wayfinder_callout}` → `${body}` (empty string by default, user fills in) → `${connections_callout}` → `${metadata_callout}`. No type-specific body sections — simpler built-in surface and all variation comes from user template overrides
- **D-33:** `${connections_callout}` format: `> [!info] Connections\n> - [[Target|Target Display]] — relation [CONFIDENCE]`. Uses the same relation + confidence display as existing `to_obsidian()`. Aliased wikilinks (see D-36) keep the callout readable
- **D-34:** `${metadata_callout}` format: `> [!abstract] Metadata\n> source_file: ...\n> source_location: ...\n> community: ...`. Duplicates frontmatter fields for reading-view visibility. Backlinks section is NOT emitted — Obsidian core generates the Backlinks pane automatically

### Wayfinder composition (D-35)
- **D-35:** Wayfinder is a single `> [!note] Wayfinder` callout with `Up:` and `Map:` rows. Derivation:
  - **Thing / Statement / Person / Source** → `Up: [[<parent MOC>|Parent MOC display]]` + `Map: [[Atlas|Atlas]]`
  - **MOC** → `Up: [[Atlas|Atlas]]` + `Map: [[Atlas|Atlas]]` (MOCs sit under the configured Atlas root)
  - **Community Overview** (same as MOC) → same as MOC
  - Atlas root is configurable via `profile.obsidian.atlas_root` (default: `"Atlas"`)
- **D-35a:** Wayfinder frontmatter coupling: the same derivation populates the `up:` frontmatter list so Supercharged Links and Dataview `FROM [[parent]]` queries work. `up:` is derived from classification output (Phase 3), not hardcoded in the template

### Filename and wikilink convention (D-36)
- **D-36:** `title_case` → `Title_Case_Underscored.md` (words capitalized, spaces replaced with underscores). `kebab-case` → `title-case-kebab.md`. `preserve` → `safe_filename(label)` from Phase 1 (strips unsafe chars, NFC-normalizes, 200-char cap with hash suffix)
- **D-37:** **Wikilinks are always auto-aliased** to the human label: `[[Neural_Network_Theory|Neural Network Theory]]` regardless of convention. The engine pairs `resolve_filename(label, convention)` with the original label for every wikilink emission. Reading view shows clean display text; disk stays convention-compliant
- **D-38:** Filename convention applies **uniformly** — disk filename, wikilink target, frontmatter `up:` wikilink targets, Dataview `FROM [[name]]` expressions — all go through the same `resolve_filename()` to prevent any mismatch

### Callout vocabulary (D-39)
- **D-39:** Built-in templates use this callout palette (matches user's Sefirot vault idioms):
  - `> [!note] Wayfinder` — navigation
  - `> [!info] Connections` / `> [!info] Things` / etc. — neutral information and grouped lists
  - `> [!abstract] Metadata` / `> [!abstract] Sub-communities` — summary/overview content
  - Dataview remains a ```` ```dataview ```` code fence, not a callout
- Users can swap callout types via template override; engine does not enforce specific types

### Module organization (D-40)
- **D-40:** New `graphify/templates.py` module — standalone, imports from `graphify.profile` only (for `safe_filename`, `safe_frontmatter_value`, `safe_tag`). No imports from `graphify.export`. Added to `graphify/__init__.py` lazy imports (`render_note`, `render_moc`, `render_community_overview`, `resolve_filename`). Phase 5 wires these into the refactored `to_obsidian()`
- **D-41:** Public API surface:
  - `render_note(node_id, G, profile, note_type, classification_context) -> tuple[str, str]` → returns `(filename, rendered_text)`
  - `render_moc(community_id, G, communities, profile, classification_context) -> tuple[str, str]`
  - `render_community_overview(...)` — same signature as `render_moc` but for Community Overview (distinct from MOC in Ideaverse)
  - `resolve_filename(label: str, convention: str) -> str` — single source of truth for filename ↔ wikilink
  - `load_templates(vault_dir: Path) -> dict[str, string.Template]` — discovers user overrides + built-ins
  - `validate_template(text: str, required: set[str]) -> list[str]`
- **D-42:** `classification_context` is a typed dict containing fields Phase 3 will populate (`parent_moc_label`, `sibling_labels`, `community_tag`, `note_type`, `folder`, `members_by_type`). Phase 2 defines the shape; Phase 3 produces it; Phase 2 consumes it. Phase 2 can render with a **synthetic classification_context** for testing without Phase 3

### Claude's Discretion
- Exact wording of built-in template body text (e.g., placeholder body comments like `<!-- fill in -->`)
- Whether `_dump_frontmatter` lives in `templates.py` or is extracted to `profile.py` as a general helper (Claude picks during implementation)
- Test fixture design for the 6 built-in templates (one fixture per type vs shared minimal graph)
- Exact regex for "unknown `${var}`" detection in `validate_template` — must distinguish graphify placeholders from Templater `<% %>` tokens and from literal `$` in user content

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Phase 1 foundations (must import from)
- `graphify/profile.py` L186 — `safe_frontmatter_value(value)` for YAML scalar quoting
- `graphify/profile.py` L204 — `safe_tag(name)` for community tag slugification
- `graphify/profile.py` L218 — `safe_filename(label, max_len)` as input to `resolve_filename` for the `preserve` convention
- `graphify/profile.py` L15 — `_DEFAULT_PROFILE` dict — extend with `obsidian.dataview.moc_query` and `obsidian.atlas_root` defaults; extend `naming.convention` handling

### Phase 1 patterns (must follow)
- `graphify/validate.py` — Validation returns `list[str]` of errors, never raises (pattern for `validate_template`)
- `graphify/security.py` L188+ — `sanitize_label` reference for any new sanitization helpers
- `graphify/__init__.py` — Lazy import registration pattern for `templates.py` exports

### Existing code (reference only — do NOT modify in this phase)
- `graphify/export.py` L440-679 — Current `to_obsidian()` frontmatter/callout/dataview patterns. Phase 5 rewires this; Phase 2 only reads it for reference on node iteration and community iteration idioms
- `graphify/export.py` L484-490 — `_dominant_confidence` helper — pattern for computing a node's dominant edge confidence (used in `${connections_callout}` rendering)
- `graphify/export.py` L568-575 — `_community_reach` helper — relevant for MOC bridge-node logic if later reused

### Requirements
- `.planning/REQUIREMENTS.md` — GEN-01 (frontmatter), GEN-02 (wikilinks), GEN-03 (user override), GEN-04 (six built-ins), GEN-05 (Dataview in MOCs), GEN-06 (wayfinder), GEN-07 (naming convention)
- `.planning/REQUIREMENTS.md` — MAP-05 (below-threshold collapse — Phase 2 renders, Phase 3 classifies)

### Prior phase context
- `.planning/phases/01-foundation/01-CONTEXT.md` — Decisions D-05 through D-16 for profile schema, safety helpers, and module conventions this phase builds on

### Target vault conventions (read for context)
- `input_docs/2026-4-8 10-1-29-Plantilla_agenda_SEFIROT.md` L2437-2503 — Full list of Obsidian plugins the user's vault has installed (Dataview, Templater, Obsidian Linter, List Callouts, Supercharged Links, Properties core). Shapes callout palette, Dataview query format, and Templater coexistence decision
- `input_docs/2026-4-8 10-1-29-Plantilla_agenda_SEFIROT.md` L2978-3001 — Example Dataview queries with `TABLE ... FROM ... WHERE ... SORT ... LIMIT` syntax showing the richness users will want in `obsidian.dataview.moc_query`
- `input_docs/2026-4-8 10-1-29-Plantilla_agenda_SEFIROT.md` L2560-2613 — Ideaverse+Sefirot folder architecture the default profile must align with

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `profile.py:safe_frontmatter_value()` — quote-on-demand YAML scalar emitter; exact helper `_dump_frontmatter` will call for every scalar value
- `profile.py:safe_filename()` — used by `resolve_filename()` for the `preserve` convention and as the final safety pass for `title_case` / `kebab-case` outputs (length cap, NFC, collision hash)
- `profile.py:safe_tag()` — used to derive `${community_tag}` for Dataview query substitution (matches Phase 1 FIX-03 slug format)
- `profile.py:_deep_merge()` — Phase 2 extends `_DEFAULT_PROFILE` by adding `obsidian.dataview.moc_query` and `obsidian.atlas_root` — user profiles still deep-merge correctly
- `export.py:_dominant_confidence()` — logic to reuse for connections callout confidence display (copy pattern, not import — keeps `templates.py` free of `export.py` dependency)

### Established Patterns
- **Optional dependencies** — `importlib.resources` is stdlib; no new optional dep needed for built-in template loading
- **Validation returns error lists** — `validate_template` follows `validate_profile` / `validate_extraction` signature
- **Lazy imports** — `templates.py` functions added to `__init__.py` lazy-load map, same as Phase 1 `load_profile` / `validate_profile`
- **`from __future__ import annotations`** + single-line module docstring, matching every other module

### Integration Points
- `__init__.py` — lazy import map gets: `render_note`, `render_moc`, `render_community_overview`, `resolve_filename`, `load_templates`, `validate_template`
- `pyproject.toml` — `[tool.setuptools.package-data]` gets `graphify = ["builtin_templates/*.md"]` entry
- `profile.py::_DEFAULT_PROFILE` — extended in-place to add `obsidian.dataview.moc_query` and `obsidian.atlas_root` defaults
- Phase 5 callsite — `to_obsidian()` will call `render_note()` and `render_moc()` with classification context from Phase 3, then write results with Phase 4 merge logic. Phase 2 outputs must be consumable directly by `(out / filename).write_text(rendered)`

### Creative Options the Architecture Enables
- `templates.py` can be tested end-to-end with a synthetic `classification_context` dict — no dependency on Phase 3 being done first, no filesystem IO. Pure unit tests over pure functions
- User template authoring feedback loop: write `.graphify/templates/moc.md`, re-run graphify, see errors in stderr or output in vault. No code changes required
- Future v2 enhancements (TMPL-01 conditionals, TMPL-02 loops) have a clean extension point — they'd augment `validate_template` to allow new syntax and extend the substitution context

</code_context>

<specifics>
## Specific Ideas

- **Target vault plugin surface shaped several decisions** — the user's vault has Dataview, Templater, Obsidian List Callouts, Supercharged Links, Obsidian Linter, and Properties (core) all installed. Built-in templates must coexist with these, not ignore them: `string.Template.safe_substitute()` passes through Templater tokens, callouts are used heavily (not plain headings), YAML block lists work best with Properties UI chip rendering
- **Dataview queries are not boilerplate for this user** — example queries in the Sefirot doc use `TABLE file.folder as Folder FROM #sefira/X SORT file.mtime DESC LIMIT 20`. Hardcoding a basic `TABLE source_file, type` would feel primitive. `obsidian.dataview.moc_query` must be a full template string, not just a columns list
- **Callout palette matches user's writing style** — Sefirot doc uses `> [!note]`, `> [!important]`, `> [!info]`, `> [!abstract]`, `> [!quote]`, `> [!remark]`, `> [!summary]`, `> [!tip]`, `> [!success]`, `> [!warning]`. Built-in templates pick from this palette (note/info/abstract) so output looks native to the vault
- **`up:` is always a list** — even for single-parent cases. Matches Ideaverse convention and keeps the YAML shape stable if future phases add multi-parent classification
- **Underscored filenames + aliased wikilinks** — disk-safe on all filesystems, reading-view clean in Obsidian. The small cost is every wikilink emits as `[[Neural_Network_Theory|Neural Network Theory]]` — the engine must always pair filename with label when emitting wikilinks
- **No backlinks section in templates** — Obsidian core generates the Backlinks pane automatically; hand-rolling a `## Backlinks` section in templates would duplicate and quickly go stale
- **Templater coexistence is a feature, not an accident** — users can put `<% tp.date.now() %>` or `<% tp.file.creation_date() %>` in their custom graphify templates and those tokens will survive graphify rendering untouched, then resolve when Obsidian opens the note

</specifics>

<deferred>
## Deferred Ideas

- **Conditional template blocks** (`{{#if_god_node}}...{{/if}}`) — v2 requirement TMPL-01, needs a non-string.Template engine. Out of scope
- **Connection loop blocks** (`{{#connections}}...{{/connections}}`) — v2 requirement TMPL-02, same reason. The pre-rendered `${connections_callout}` approach is the v1 substitute
- **Per-community template overrides** — v2 CFG-03. A community-specific template (e.g., "the ML community uses a custom MOC layout") would require template selection by community ID, not note type. Add to backlog
- **Dataview query templates per note type in profile** — v2 TMPL-03. For v1, only MOCs get a configurable Dataview query; Thing/Statement/Person/Source built-ins embed no queries
- **Custom color palettes in profile for graph.json** — v2 CFG-01, belongs to a different module (`export.py` graph.json writing) anyway
- **Type-specific Thing/Statement/Person/Source body sections** (`> [!abstract] Definition`, `> [!quote] Claim`) — rejected in favor of uniform scaffold (D-32). If user wants per-type sections, they write custom templates
- **Markdown-body content generation** (filling in `${body}` with LLM-generated prose) — out of scope; graphify is a structural renderer, not a content generator
- **Akiflow / Google Calendar / Efforts integration** — these are Ideaverse Pro concerns outside graphify's knowledge-graph mandate (noted explicitly in PROJECT.md "Out of Scope")

</deferred>

---

*Phase: 02-template-engine*
*Context gathered: 2026-04-11*
