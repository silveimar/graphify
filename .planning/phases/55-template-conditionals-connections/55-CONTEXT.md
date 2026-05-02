# Phase 55: Template conditionals & connection loops - Context

**Gathered:** 2026-05-02
**Status:** Ready for planning

<domain>
## Phase Boundary

Extend the `string.Template`-based block engine (shipped in Phase 31, v1.7) with **two narrow additions** and produce **the user-facing reference doc** that has been missing since v1.7:

1. **`if_note_type_<X>` predicate family** — 6 builtin names matching `_KNOWN_NOTE_TYPES` (thing/statement/person/source/code/moc), evaluated against the `note_type` parameter passed into `render_note`. Templates can branch on type without authors having to materialize `extra.note_type` via Phase 30 mapping rules.
2. **`predicate_flags:` profile.yaml key** — flat dict mapping a name → simple node-attribute rule that registers into `_PREDICATE_CATALOG` at profile-load time, so authors can declare custom flag predicates per vault without code changes. Validated at `validate_profile_preflight` time.
3. **`docs/TEMPLATES.md`** — canonical user-facing reference for the entire block surface (predicates, `{{#connections}}`, ordering, sanitization). Resolves the v1.7-shipped-but-undocumented gap.

**Out of scope (locked):**
- The `_BlockTemplate` engine itself, the FSM in `_expand_blocks`, the `(relation, label)` sort, sanitization sinks, the D-16 ordering invariant, and `if_attr_<name>` semantics — all locked from Phase 31, do not modify.
- Scoped template overrides (`template_overrides:` per-community / per-mapping-rule) — Phase 56 / CFG-01.
- Per-note-type Dataview query templates — Phase 56 / TMPL-03.
- Override-precedence collision validation — Phase 56 / CFG-02.
- Switching off `string.Template` to Jinja2 (ROADMAP-locked: "no Jinja2 dependency").
- Loud preflight failure / strict block-error abort — keeps current "warn + fall back to builtin" UX.

</domain>

<decisions>
## Implementation Decisions

### Phase scope
- **D-55.01:** Phase 55 is an **EXTEND** phase, not a closure. Add new predicate forms + new profile key + user docs. Engine remains intact.
- **D-55.02:** ROADMAP Success Criterion 2 ("pytest covers nested + empty-iterable cases") is **already satisfied** by Phase 31 tests `test_nested_blocks_rejected_with_specific_error`, `test_nested_if_in_if_rejected`, `test_connections_empty_loop_renders_nothing`. 55-VERIFICATION.md must cite these as evidence; planner does not need to re-add equivalent tests, only NEW tests for the NEW surface (note_type predicates, predicate_flags, docs/TEMPLATES.md examples).
- **D-55.03:** ROADMAP Success Criterion 3 ("`validate_profile_preflight` flags malformed blocks") is **already satisfied** at the wiring level (`profile.py:1453` calls `validate_template`). Phase 55 confirms via test that `predicate_flags:` and unknown `if_note_type_*` references go through the same validation path.

### Predicate surface
- **D-55.04:** Add `if_note_type_<X>` for all 6 known note types (thing, statement, person, source, code, moc). Symmetric, future-proof.
- **D-55.05:** Validation behavior for unknown note-type suffix: **reject at preflight** (mirrors how unknown predicates are rejected today). Do NOT silently evaluate-false — that masks typos.
- **D-55.06:** Implementation reads from the `note_type` parameter that `render_note` already takes (templates.py:996+ test confirms this is plumbed end-to-end). No need to read `node.note_type` attribute. Add a new field to `BlockContext` (e.g., `note_type: str | None`) and a new predicate evaluator branch.
- **D-55.07:** Add `predicate_flags:` as a top-level profile.yaml key. Schema: `dict[str, dict]` where key is the predicate name suffix (e.g., `is_published`) and value is a node-attribute rule (the simplest viable: `{attr: <attr_name>, equals: <value>}` or just `{attr: <attr_name>}` for truthy). Templates reference as `{{#if_flag_<name>}}` to avoid name-collision with `if_attr_*` and the catalog.
- **D-55.08:** `predicate_flags` validation at `validate_profile_preflight`: reject duplicate names, names colliding with `_PREDICATE_CATALOG`, names colliding with `if_attr_` prefix, and rules referencing unknown attrs (best-effort). Errors flow through the same channel as block validation errors.

### Phase 55 / Phase 56 boundary
- **D-55.09:** **Phase 55 = engine surface.** Adds predicate NAMES and the profile-side mechanism to register MORE predicate names. **Phase 56 = profile composition surface.** Adds keys for declaring template OVERRIDES (per-community, per-mapping-rule) and per-note-type Dataview queries. Different keys (`predicate_flags:` vs `template_overrides:`), different jobs.
- **D-55.10:** If during Phase 55 implementation a question arises about `predicate_flags:` interacting with `extends:` / `includes:` profile composition, resolve by inheriting the same merge semantics Phase 30 uses for any other top-level profile key (no Phase-55-specific composition rule). Phase 56 will revisit override scoping.

### Documentation
- **D-55.11:** New file `docs/TEMPLATES.md`. Required sections (locked):
  1. Conditional blocks (catalog + `if_attr_*` + new `if_note_type_*` + new `if_flag_*`)
  2. Connection loops (`{{#connections}}…{{/connections}}` + `${conn.<field>}` + `${conn_<field>}` table + sort key)
  3. Ordering invariant (D-16: blocks expand BEFORE `${}` substitution)
  4. Sanitization (label/HTML sinks, T-31-01 contract)
  5. Predicate catalog table (name → semantics → typical use)
  6. Authoring `predicate_flags:` (profile-yaml example)
  7. Validation behavior (what `graphify doctor` and `--validate-profile` flag, fallback contract)
  8. Backward-compatibility (block-free templates remain byte-identical — ROADMAP criterion 4)
- **D-55.12:** Examples in `docs/TEMPLATES.md` should be **executable as fixtures** where reasonable — at least one example per section gets a corresponding test in `tests/test_docs_templates_examples.py` that lifts the markdown fence and runs it through `_BlockTemplate` + `_expand_blocks`. Prevents the doc from rotting against the engine.
- **D-55.13:** No `docs/MIGRATION_V1_11.md`. PROFILE-CONFIGURATION.md gets a one-line "see `docs/TEMPLATES.md` for block syntax" pointer; nothing more.

### Preflight UX
- **D-55.14:** Keep current behavior — block validation errors at `validate_profile_preflight` flow to the same error channel; runtime `load_templates` falls back to builtin and warns to stderr. No abort, no exit-code escalation. Phase 55 documents this contract; does not change it.

### Claude's Discretion
- Test layout: split `predicate_flags` tests into a new file `tests/test_predicate_flags.py` vs append to `tests/test_templates.py` — planner chooses based on file-size / cohesion.
- Naming of the `predicate_flags` rule schema's inner keys (`{attr, equals}` vs `{path, value}` vs other) — planner / researcher chooses based on existing profile.yaml convention; should match Phase 30's mapping-rules style.
- Whether `if_flag_<name>` block rendering should support a parameter (e.g., `{{#if_flag_is_published_true}}` vs runtime-evaluated rule) — planner decides; default is **rule evaluated at render time**.
- Doc placement of the predicate catalog reference table (inline in `docs/TEMPLATES.md` vs cross-link to `graphify/templates.py` docstring).

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Roadmap & Requirements
- `.planning/ROADMAP.md` §Phase 55 — goal, success criteria, dependencies (Phase 31)
- `.planning/REQUIREMENTS.md` §TMPL — TMPL-01, TMPL-02 (the two requirements this phase closes)
- `.planning/milestones/v1.7-ROADMAP.md` §Phase 31 — the prior phase whose engine Phase 55 extends; success criteria 1–4 are **locked** and must not regress

### Implementation surface (READ-ONLY for Phase 55 except for noted additions)
- `graphify/templates.py:177-340` — `_BlockTemplate`, `BlockContext`, `_PREDICATE_CATALOG`, `_eval_predicate`, `_build_edge_records`, `_expand_blocks` (all D-04..D-16 invariants)
- `graphify/templates.py:395-540` — `validate_template` block-syntax validation
- `graphify/templates.py:1043+` — `render_note` integration point where `note_type` flows in
- `graphify/profile.py:1332-1453` — `validate_profile_preflight` (already calls `validate_template`); Phase 55 adds `predicate_flags` validation here
- `graphify/profile.py:179` — `_REQUIRED_PER_TYPE` (Layer 2 reference)

### Test infrastructure
- `tests/test_templates.py` — 208 tests; block-engine section starts at L2510 with explicit fence `# Covers conditional blocks…`
- `tests/test_templates.py::test_nested_blocks_rejected_with_specific_error` (L2838)
- `tests/test_templates.py::test_nested_if_in_if_rejected` (L2852)
- `tests/test_templates.py::test_connections_empty_loop_renders_nothing` (L2767)
- `tests/test_templates.py::test_if_attr_*` (L2613-2670) — escape-hatch contract
- `tests/test_profile.py` — composition + preflight tests; new `predicate_flags` validation tests land here or alongside

### User-facing docs (Phase 55 produces / touches)
- `docs/PROFILE-CONFIGURATION.md` — existing profile schema reference; gets a 1-line pointer to TEMPLATES.md
- `docs/TEMPLATES.md` — **NEW**, canonical user reference for the block engine
- `docs/CONFIGURING_V1_5.md`, `docs/CONFIGURING_V1_5-RUNBOOK.md` — older config refs; do NOT cross-link (would invite stale-doc rot)

### Builtin templates (no changes expected)
- `graphify/builtin_templates/code.md`, `moc.md`, `thing.md`, `statement.md`, `person.md`, `source.md` — exemplar templates; Phase 55 may add a single illustrative `{{#if_note_type_*}}` use to one builtin if the planner finds it pedagogically helpful, otherwise unchanged.

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- **`_PREDICATE_CATALOG` dict** (templates.py:252) — Phase 55's `if_note_type_*` and `predicate_flags:` both register entries into this same catalog. One pattern to follow.
- **`BlockContext` dataclass** (templates.py:206) — frozen, three fields today. Phase 55 adds `note_type: str | None` (and possibly a `node_attrs: dict` view for `predicate_flags:` evaluators). Stays frozen.
- **`_IF_ATTR_RE` pattern** (templates.py:196) — regex-driven escape hatch. `if_note_type_*` and `if_flag_*` follow the same pattern: regex `^if_note_type_([a-z_]+)$` and `^if_flag_([a-z_][a-z0-9_]*)$`.
- **`_KNOWN_NOTE_TYPES`** — already defined for TMPL-03 / Dataview path; Phase 55 reuses it as the validation set for `if_note_type_<X>`.
- **`_load_builtin_template` / `load_templates`** (templates.py:588, 600) — the load path that already calls `validate_template` and falls back on errors. No changes needed for Phase 55 except possibly threading the active profile's `predicate_flags` into the context that gets handed downstream.

### Established Patterns
- **Predicate registration is dict-keyed by full name** — `if_god_node`, not `god_node`. Phase 55 follows: register `if_note_type_thing`, `if_note_type_moc`, etc. (or use a regex evaluator branch in `_eval_predicate` like `_IF_ATTR_RE`).
- **Validation runs at preflight, render trusts it** — D-09/D-10 invariant in `_expand_blocks` defensive checks. Phase 55 must NOT add render-time validation; all new checks land in `validate_template` / `validate_profile_preflight`.
- **Sanitization sinks are non-negotiable** — every value reaching the rendered text passes `_sanitize_wikilink_alias` or equivalent. New predicates emit boolean only (no string), so no new sink needed; new `predicate_flags:` rule values are NOT rendered (only consulted), so no sink needed either.
- **Docs that require runtime values are kept tested** — pattern from Phase 53/54 (CGRAPH-04 parity tests). `docs/TEMPLATES.md` examples follow.

### Integration Points
- `render_note(node_id, G, profile, note_type, ctx)` — already takes `note_type`. Phase 55 plumbs it into `BlockContext`. Search call sites for any non-test caller passing `None` or omitting; expect zero in production paths.
- `profile.load_profile(...)` → returned dict carries `predicate_flags` (new). Phase 55 plumbs it into the rendering call chain (load_templates / render_note's profile arg already covers this — no new function signatures expected).

</code_context>

<specifics>
## Specific Ideas

- The `predicate_flags:` namespace `if_flag_<name>` is deliberately distinct from `if_attr_<name>`. Reason: `if_attr_*` is a raw-attribute escape hatch (no profile config required); `if_flag_*` is a profile-declared, validation-checked predicate. Authors and reviewers can tell at a glance which mechanism is in play.
- Doc tone for `docs/TEMPLATES.md`: terse reference, not tutorial. Each section is "what / when / example / pitfall." Pattern follows `docs/RELATIONS.md` (the post-Phase-54 reference).
- Validation rule `predicate_flags: { is_published: { attr: is_published } }` — when value is just `{attr: <name>}`, evaluator returns `bool(node.get(attr))`. When `{attr: <name>, equals: <value>}`, evaluator returns `node.get(attr) == value`. Two-shape schema is enough; richer rules are out of scope.

</specifics>

<deferred>
## Deferred Ideas

- **Composite predicates** (`{{#if_god_node_AND_isolated}}` or boolean composition syntax) — out of scope. Authors flatten into precomputed `predicate_flags:` rules or use nested templates. Note for a future phase if real demand surfaces.
- **`{{#unless_*}}` / negation operator** — out of scope. Authors invert by restructuring (`{{#if_not_isolated}}` would require `predicate_flags: { not_isolated: { attr: isolated, equals: false } }`). Note for future.
- **Block-level template inclusion / partials** (`{{> snippet}}`) — out of scope. Phase 30 `extends:` / `includes:` covers profile-level composition; per-template partials are a separate feature.
- **Override precedence + collision matrix for `predicate_flags`** under `extends:` chains — Phase 56 territory (CFG-02 covers this for template_overrides; the same machinery may extend to `predicate_flags`).
- **`docs/MIGRATION_V1_11.md`** — explicitly NOT created. If a future v1.12 wants a milestone-transition note, that's its decision.
- **Loud preflight UX** — `graphify doctor` exiting non-zero on block errors. Real demand may surface from CI users; revisit then.

</deferred>
