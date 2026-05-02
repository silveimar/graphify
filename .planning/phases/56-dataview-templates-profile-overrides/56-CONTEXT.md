# Phase 56: Dataview templates & profile overrides - Context

**Gathered:** 2026-05-02
**Status:** Ready for planning

<domain>
## Phase Boundary

Add the **profile composition surface** for declarative template overrides and harden the existing per-note-type Dataview surface with deterministic preflight validation. Three narrow additions plus one schema extension:

1. **`mapping_rule_templates:` and `note_type_templates:`** — two new top-level profile keys, each a list of `{match, pattern, template}` rules mirroring Phase 30's `community_templates:` shape (CFG-01).
2. **Optional `id:` field on `mapping_rules`** — slug-pattern, unique within the list, validated at preflight. Enables `mapping_rule_templates:` to reference a specific rule (CFG-01 prerequisite).
3. **Strict precedence ladder + intra-list collision validation** — `mapping_rule_templates > community_templates > note_type_templates > base profile template` is silently applied at render time; intra-list ambiguity (duplicate ids, duplicate exact patterns, duplicate `note_type` keys, duplicate `dataview_queries.<note_type>` across `extends:`/`includes:` chain) raises deterministic preflight errors (CFG-02).
4. **`dataview_queries:` dead-rule preflight checks** — extends Phase 31's existing per-note-type DV surface with four new validation classes; no schema or engine changes (TMPL-03).

**Out of scope (locked):**
- Promoting `dataview_queries:` to block-engine templates (would couple `_BlockTemplate` to a config key it doesn't touch today). Only `string.Template`-style `${var}` substitution remains, exactly as Phase 31 ships.
- Per-block / per-frontmatter partial overrides — every override entry replaces a **whole template path** (`community_templates:` parity). No `blocks:` dict, no `frontmatter_extra:` patch.
- A unified `template_overrides:` key with `scope:` discriminator — sibling keys win for zero migration risk and independent evolution per scope.
- Glob/regex pattern-overlap detection within a list (e.g., `Auth*` vs `AuthService`) — no canonical algorithm; users get list-order resolution at render, no warning.
- Graph-aware collision passes after build — CFG-02 is schema-only at `validate_profile_preflight` time. The validation contract stays "graph-blind."
- Any change to the Phase 31 block engine, FSM, sanitization sinks, or D-16 ordering invariant.
- Any change to Phase 55's `predicate_flags:` shape, `if_note_type_*` / `if_flag_*` predicates, or `docs/TEMPLATES.md`.
- Cross-scope collision **errors** — when a note matches in more than one list, the precedence ladder resolves silently. This is the design.
- Loud preflight UX (non-zero exit on `graphify doctor` for override errors) — keeps Phase 55 D-55.14 contract: warn + fall back to default template.

</domain>

<decisions>
## Implementation Decisions

### TMPL-03 scope
- **D-56.01:** Phase 31 already shipped per-note-type `dataview_queries:` validated at preflight. Phase 56's TMPL-03 contribution is **dead-rule hardening only** — no new shape, no engine plumbing, no scope axis. The preflight validator at `graphify/profile.py:741+` grows the four checks in D-56.02; nothing else moves.
- **D-56.02:** Four dead-rule classes added at `validate_profile_preflight` for `dataview_queries:` entries:
  1. **Unknown `${var}` references** — reject query strings referencing substitution variables outside an allowlist. The allowlist is derived from the actual variable set substituted by `_build_dataview_block` callers (planner discretion to enumerate; expected: `${community_tag}`, `${note_type}`, `${vault_root}`, plus whatever else `_build_dataview_block` plumbs in today).
  2. **Note-type with no possible mapped nodes** — reject `dataview_queries.<note_type>` entries when `mapping_rules` + `folder_mapping` prove no node will ever resolve to that note_type in the composed profile. Catches stale entries after rule edits.
  3. **Empty / whitespace-only after substitution** — Phase 31 already rejects empty raw strings; extend to (a) reject queries whose body is pure whitespace once stripped, AND (b) reject queries that would render empty if every `${var}` expanded to an empty string.
  4. **Duplicate keys across `extends:`/`includes:` chain** — when composition produces conflicting `dataview_queries.<note_type>` values from different source paths, raise a deterministic error citing all source paths. Reuses CFG-02 collision machinery (D-56.06 §4) — same code path, same error format.

### Override surface shape (CFG-01)
- **D-56.03:** Sibling keys, not a unified discriminator. Three top-level lists, each a list of `{match, pattern, template}` rules mirroring `community_templates:`:
  - `community_templates:` — **untouched from Phase 30**. No deprecation, no schema migration.
  - `mapping_rule_templates:` — `match: rule_id` (the only allowed match kind in v1.11), `pattern: <slug>` referencing a `mapping_rules[].id`, `template: <fragment-path>`.
  - `note_type_templates:` — `match: note_type`, `pattern: <one of _KNOWN_NOTE_TYPES>`, `template: <fragment-path>`.
  Each new key gets its own validator block in `validate_profile_preflight`, modeled on the existing `community_templates:` validator at `profile.py:682-735`. Both keys register into `_VALID_TOP_LEVEL_KEYS`.
- **D-56.04:** Mapping rules grow an optional `id:` field. Validation: must be a string, slug pattern (`[a-z][a-z0-9_-]*`), unique within the `mapping_rules:` list. Rules without `id:` are valid (preserves backward compat) but cannot be targeted by `mapping_rule_templates:`. `validate_rules` in `graphify/mapping.py` is the natural injection point. Duplicate `id:` raises a preflight error citing the colliding rule indices.

### CFG-02 — Precedence and collisions
- **D-56.05:** **Strict precedence ladder, applied silently at render-time selection of which template path to load:**
  1. `mapping_rule_templates` match (if any rule matches a node attributable to a specific mapping rule)
  2. `community_templates` match (if the node's community matches a rule)
  3. `note_type_templates` match (if the node's note_type matches a rule)
  4. Base profile template for the note_type
  Most-specific scope wins. **No error on cross-scope overlap** — the ladder *is* the design. Render-time tie-breaking within a list is by list order (first matching rule wins; only relevant when intra-list pattern globs overlap, which CFG-02 does not detect — see D-56.06).
- **D-56.06:** **CFG-02 collision detection is schema-only at `validate_profile_preflight`.** Four collision classes raise deterministic errors citing rule indices and source paths:
  1. **Duplicate `id:` in `mapping_rule_templates`** — two entries with the same `pattern` value targeting the same rule_id.
  2. **Duplicate exact `pattern` within the same list** — same pattern string within `community_templates`, `mapping_rule_templates`, or `note_type_templates`. (For `community_templates` this extends the existing Phase 30 validator.)
  3. **Duplicate `note_type` keys in `note_type_templates`** — two entries targeting the same `_KNOWN_NOTE_TYPES` value.
  4. **Duplicate `dataview_queries.<note_type>` across `extends:`/`includes:` chain** — when composition surfaces conflicting values for the same note_type key from different source profiles. Implementation reuses `_deep_merge_with_provenance`'s recorded `source_path` per leaf to enumerate all contributing files in the error message.

  **NOT detected (out of scope):** glob/regex pattern overlap (e.g., `Auth*` vs `AuthService` matching the same community label). No canonical algorithm; render-time list-order resolution applies.
- **D-56.07:** The collision matrix is encoded as parametric tests under `tests/test_profile.py` (or a new sibling `tests/test_template_overrides.py` — planner discretion). Each of the four classes in D-56.06 gets at least one positive (collision detected) and one negative (similar-but-non-colliding) test. Per ROADMAP CFG-02 success criterion, the matrix is the canonical reference for what does and does not collide.

### Override unit
- **D-56.08:** Every override entry's `template:` field is a **whole template path** (fragment under `.graphify/`). Render selects the matched override's file in place of the base note-type template — no merging, no patching, no per-block surgery. Mirrors the Phase 30 `community_templates:` semantics exactly. Sanitization stays at the file-load boundary (existing path-confinement checks in `community_templates:` validator port verbatim — `..`, absolute, leading `~` rejected).

### Composition with `extends:`/`includes:`
- **D-56.09:** The three new override lists inherit standard `_deep_merge_with_provenance` semantics (last-wins on list values, same as `community_templates:` today). No phase-56-specific composition rule. Cross-chain collisions surface only via D-56.06 §4 for `dataview_queries:`; for the three template lists, last-wins is the contract.

### Documentation
- **D-56.10:** Update `docs/PROFILE-CONFIGURATION.md`:
  - Add subsection per new key (`mapping_rule_templates`, `note_type_templates`, `mapping_rules.id`).
  - Add the precedence ladder (D-56.05) as a numbered list in a "How overrides resolve" subsection.
  - Cross-reference the four collision classes (D-56.06).
  - One worked example showing all three override types resolving for a single note.
- **D-56.11:** Update `docs/TEMPLATES.md` (Phase 55 deliverable) with a one-paragraph forward-pointer to the new override surface in `docs/PROFILE-CONFIGURATION.md`. No duplication of override semantics into TEMPLATES.md (which scopes to the block engine).
- **D-56.12:** No `docs/MIGRATION_V1_11.md`. No deprecation notice for `community_templates:` (it stays first-class).

### Preflight UX
- **D-56.13:** Per Phase 55 D-55.14 contract: validation errors flow through the same channel as block validation; runtime fall-back to default template + stderr warn on missing/unreadable override files (existing `community_templates:` behavior at `templates.py:1541-1577` — port the same error/warn pattern to the two new lists).

### Claude's Discretion
- **Test layout:** new `tests/test_template_overrides.py` vs additions to `tests/test_profile.py` — planner chooses based on file size + cohesion.
- **Allowlist of `${var}` names** for D-56.02 §1 — researcher / planner enumerates by reading every `_build_dataview_block` callsite.
- **Validation message format** — match the existing Phase 30 `community_templates:` and Phase 31 `dataview_queries:` validator wording (deterministic, includes index/key, names the offending value).
- **Whether `mapping_rule_templates:` validation needs a graph-aware "unreachable rule" check** (e.g., rule `id` exists but its `when:` matcher never fires) — default is **no**; out of scope unless the dead-rule pattern from D-56.02 §2 demands it for symmetry.
- **Slug regex for `mapping_rules.id:`** — planner picks; suggested `^[a-z][a-z0-9_-]*$`, max length aligned with existing slug validators in the codebase.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Roadmap & Requirements
- `.planning/ROADMAP.md` §"Phase 56" — goal, success criteria, dependencies (Phase 30 + Phase 55)
- `.planning/REQUIREMENTS.md` §TMPL-03, §CFG-01, §CFG-02 — the three requirements this phase closes (canonical wording)
- `.planning/milestones/v1.7-ROADMAP.md` §Phase 30 — `community_templates:` and `extends:`/`includes:` semantics this phase composes with (locked)
- `.planning/phases/55-template-conditionals-connections/55-CONTEXT.md` — Phase 55's deferred-ideas section that pre-scoped Phase 56's three knobs (`template_overrides:`, per-note-type DV templates, override-precedence collision validation)

### Implementation surface (READ-ONLY for Phase 56 except for noted additions)
- `graphify/profile.py:96-167` — `_DEFAULT_PROFILE` (current `dataview_queries: {}` default; no new defaults expected — both new override lists default to omitted, validator treats absence as `[]`)
- `graphify/profile.py:169-176` — `_VALID_TOP_LEVEL_KEYS` (add `mapping_rule_templates`, `note_type_templates`)
- `graphify/profile.py:181+` — `_KNOWN_NOTE_TYPES` (used to validate `note_type_templates.pattern`)
- `graphify/profile.py:236-280` — `_deep_merge` / `_deep_merge_with_provenance` (provenance map fuels D-56.06 §4 collision-source enumeration; no changes)
- `graphify/profile.py:682-735` — existing `community_templates:` validator (the canonical pattern to mirror for the two new lists; port path-confinement checks verbatim)
- `graphify/profile.py:737-763` — existing `dataview_queries:` validator (extend with the four checks in D-56.02)
- `graphify/profile.py:1041-1051` — `mapping_rules` validation entry point (delegates to `validate_rules` in `mapping.py`)
- `graphify/mapping.py` `validate_rules` — natural injection point for the optional `id:` field validation (D-56.04)
- `graphify/templates.py:1517-1610` — existing `community_templates:` runtime resolver (`_load_community_template` and helpers); the two new override lists need the parallel resolver path with the precedence ladder (D-56.05) wired in

### Test infrastructure
- `tests/test_profile.py` — composition + preflight tests; new override-list validators land here or alongside
- `tests/test_template_overrides.py` (NEW, optional per D-56.07) — collision matrix tests, precedence ladder tests
- `tests/test_mapping.py` — natural home for the `mapping_rules.id:` validation tests
- Existing `community_templates:` and `dataview_queries:` test patterns serve as the model — locate and read them before writing new tests

### User-facing docs (Phase 56 produces / touches)
- `docs/PROFILE-CONFIGURATION.md` — get the override-surface section + precedence ladder + collision classes (D-56.10)
- `docs/TEMPLATES.md` (Phase 55 output) — gets a one-paragraph forward-pointer (D-56.11)

### Prior phase context (locked)
- `.planning/phases/53-concept-code-schema-build-merge/53-CONTEXT.md` — schema discipline patterns
- `.planning/phases/54-mcp-trace-obsidian-parity/54-CONTEXT.md` — parity-test pattern for cross-surface contracts (relevant if Phase 56 grows a parity test between schema and rendered output)
- `.planning/phases/55-template-conditionals-connections/55-CONTEXT.md` — explicit Phase 55/56 boundary (D-55.09); `predicate_flags:` semantics that Phase 56 must NOT touch

### Codebase intel
- `.planning/codebase/ARCHITECTURE.md`
- `.planning/codebase/CONVENTIONS.md`
- `.planning/codebase/TESTING.md`

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- **`community_templates:` validator** (`profile.py:682-735`) — the canonical shape Phase 56 mirrors for `mapping_rule_templates:` and `note_type_templates:`. Path-confinement checks (`..`, absolute, leading `~`), unknown-key rejection, and per-rule index reporting all port verbatim.
- **`_deep_merge_with_provenance`** (`profile.py:247+`) — already records `source_path` per leaf write. D-56.06 §4 calls into the provenance map to enumerate all source profiles contributing to a colliding `dataview_queries.<note_type>`.
- **`_KNOWN_NOTE_TYPES`** (`profile.py:181+`) — same allowlist used for `dataview_queries:` validation; `note_type_templates.pattern` validates against it.
- **`_VALID_TOP_LEVEL_KEYS`** (`profile.py:172`) — central allowlist; new keys must register here or preflight rejects them as unknown.
- **`community_templates:` runtime resolver** (`templates.py:1517-1610` — `_load_community_template`, related helpers) — the warn-and-fall-back pattern (D-56.13) that the two new override resolvers reuse byte-for-byte.
- **`validate_rules`** in `graphify/mapping.py` — single point for mapping-rule schema; `id:` field validation lands here (D-56.04).

### Established Patterns
- **Validators return list of error strings; preflight aggregates** — never raise. New collision detection follows.
- **Deterministic error wording** — every error includes the offending index/key + the bad value + the rule ("must be...", "expected...", "got..."). Mirror Phase 30/31 wording.
- **Path-confinement at validator** — `..`, absolute, `~` rejection happens at preflight, not at runtime. Sanitization at file-load boundary remains the runtime defense (existing `community_templates:` resolver pattern).
- **Provenance tracking via `_deep_merge_with_provenance`** — used today for `dataview_queries`; Phase 56 leans on it for D-56.06 §4 to cite all source profiles in a collision error.
- **Last-wins on lists during `extends:`/`includes:` composition** — the three new override lists follow the same merge contract; no per-key cross-chain merge.
- **Warn + fall back to default on runtime template-load failure** — Phase 55 D-55.14 contract; D-56.13 explicitly inherits.
- **No new required deps** — stdlib only; PyYAML stays optional. Project constraint (CLAUDE.md).
- **`from __future__ import annotations`** as first import; type hints with `dict[K, V]` and `str | None`.

### Integration Points
- **Render path** (`templates.py` template-selection logic for a node) — must consult the three override lists in ladder order (D-56.05) before falling back to the base note-type template. Implementation likely extends `_load_community_template` into a more generally-named `_resolve_note_template` or composes three resolver calls in priority order.
- **`mapping_rules.id:` consumers** — currently zero. Adding `id:` is purely additive; no downstream code reads it yet. The override resolver will be the first reader.
- **`graphify doctor` / `--validate-profile`** — already calls `validate_profile_preflight`; new errors surface automatically. No CLI changes expected.
- **Builtin templates** (`graphify/builtin_templates/*.md`) — unchanged. No phase-56 builtin override file is shipped.
- **Phase 47 / Phase 54 MCP tools** — read profile composed output but do not consume override surface; no MCP changes needed.

</code_context>

<specifics>
## Specific Ideas

- **Sibling-keys rationale (D-56.03):** keeping `community_templates:` first-class avoids any deprecation/migration story during a single milestone. The three sibling lists evolve independently — if a future phase wants per-tag or per-folder overrides, it adds a fourth sibling without rewriting existing schema. Author intuition stays simple: the key name *is* the scope.
- **Precedence ladder rationale (D-56.05):** mapping_rule > community > note_type matches "narrowness" — a mapping rule targets at most one production path, a community is a cluster of nodes, and a note_type is the broadest population. Authors edit the most-specific override knowing it always wins; broad defaults stay safe.
- **CFG-02 schema-only stance (D-56.06):** the requirement says "collision matrix encoded in tests" — that's a structural contract, not a runtime guarantee. Schema-only detection is provably terminating, fast, and produces stable error messages; pattern-overlap detection is undecidable in the general case (regex intersection emptiness is not always tractable).
- **`dataview_queries.<note_type>` collision unifies with template overrides (D-56.06 §4):** the same source-path enumeration code serves both. One collision-formatter, one error template, one set of parametric tests covering all four classes.
- **Mapping rule `id:` is opt-in (D-56.04):** preserves backward compat for every existing profile. Profiles that never reference rules from `mapping_rule_templates:` need no edits.
- **Render-time fall-back is non-negotiable (D-56.13):** a missing override file must NOT block render. The Phase 55 contract is that authors get warnings, not aborted runs. Test that an override pointing at a deleted file falls back to the base template + emits exactly one stderr warning.

</specifics>

<deferred>
## Deferred Ideas

- **Per-block / per-frontmatter partial overrides** — `blocks:` dict or `frontmatter_extra:` patch. Useful but multiplies merge surface and invents block-naming conventions. Revisit if real authoring demand surfaces.
- **Unified `template_overrides:` with `scope:` discriminator** — cleaner long-term YAML, but a future cleanup phase. Would need a deprecation cycle for `community_templates:`.
- **Glob/regex pattern-overlap detection within a list** — undecidable in general; could implement a heuristic ("any two patterns where one is a strict prefix of the other") but value is low and false-positive risk is high. Defer.
- **Graph-aware collision pass after build** — would catch real-world cases where two patterns *do* match the same node despite no schema collision. Changes the validation contract from graph-blind to graph-aware. Future phase if real noise surfaces.
- **`docs/MIGRATION_V1_11.md`** — explicitly NOT created (Phase 55 D-55.13 stance carries forward).
- **`graphify doctor` non-zero exit on override errors** — keeps Phase 55 D-55.14 stance. Revisit when CI users ask.
- **Author-declared per-rule `priority:`** — would let authors override the strict ladder. Adds a third axis of reasoning during reviews. Defer unless ladder proves wrong in practice.
- **Promoting `dataview_queries:` to block-engine templates** — would couple `_BlockTemplate` to a config key it doesn't touch today. Real demand for `{{#if_*}}` inside DV queries can revisit; the `${var}` substitution that Phase 31 ships handles the common cases.
- **`note_type_templates:` per-pattern listing** — note_type_templates is a degenerate case (only one match axis: the note_type string). It could collapse to `note_type_templates: { code: code-rich.md, moc: ... }` instead of the parallel list shape. The parallel shape was chosen for consistency with the other two siblings; revisit if authors find the dict shape clearer.

</deferred>

---

*Phase: 56-dataview-templates-profile-overrides*
*Context gathered: 2026-05-02*
