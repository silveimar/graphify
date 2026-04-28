# Phase 30: Profile Composition - Context

**Gathered:** 2026-04-28
**Status:** Ready for planning

<domain>
## Phase Boundary

Compose vault profiles from fragments via `extends:` (single-parent inheritance) and `includes:` (ordered mixin list), with deterministic merge order and cycle detection. Add per-community template overrides (community-MOC level) selected by fnmatch glob against community ID or label, first-match-wins. Extend `--validate-profile` to print the merge chain, per-key field provenance, and the resolved community-template rule list.

Closes CFG-02 (composition) and CFG-03 (per-community template overrides) — the long-deferred profile-polish backlog from v1.0.

</domain>

<decisions>
## Implementation Decisions

### Composition Primitives (CFG-02)

- **D-01:** Profiles support BOTH `extends:` and `includes:` with distinct semantics. `extends:` = single-parent inheritance chain (string only, not a list). `includes:` = ordered list of mixin fragments. Familiar mental model from ESLint/Spectral/TS configs.
- **D-02:** Merge order when both are present: parent chain via `extends:` resolved first (depth-first, post-order — root ancestor's fields are the foundation), then `includes:` layered in declared order (sequential `_deep_merge`, last wins), then this profile's own fields applied last as the most-specific override.
- **D-03:** `extends:` MUST be a string (single parent only). Multi-base composition is expressed exclusively via `includes:`. This keeps the two primitives semantically distinct: `extends` = inheritance, `includes` = mixins.
- **D-04:** Cycle detection: report `[graphify] profile error: extends/includes cycle detected: a.yaml → b.yaml → c.yaml → a.yaml` to stderr and exit non-zero from `--validate-profile`. From `load_profile()`, follow the existing graceful-fallback contract — print the error and fall back to `_DEFAULT_PROFILE` so graphify never crashes from a bad vault profile.
- **D-05:** Hard recursion-depth cap of 8 levels in addition to cycle detection. Belt-and-suspenders against pathological YAML; emits a clear error when exceeded.

### Fragment Path Resolution (CFG-02)

- **D-06:** Paths in `extends:`/`includes:` resolve **relative to the file containing the directive** (sibling-relative). Users may organize fragments anywhere under `.graphify/` — `.graphify/fragments/`, `.graphify/bases/`, top-level — graphify does not impose a directory convention.
- **D-07:** Strict path confinement: every resolved path MUST stay inside the vault's `.graphify/` directory. Absolute paths, `../` escapes that exit `.graphify/`, and symlinks pointing outside are rejected with a clear error. Reuses the v1.0 `validate_vault_path()` path-traversal guard contract. No org-wide or `~/.graphify/` user-global fragments in this phase.
- **D-08:** Fragments may be **partial profiles** — only the fully-composed profile is required to pass `validate_profile()`. Individual fragments can omit otherwise-required fields like `folder_mapping`. This matches ESLint/TS-config conventions where a "recommended" base is meant to be extended, not used standalone.

### Per-Community Template Overrides (CFG-03)

- **D-09:** New top-level profile key: `community_templates: [...]`. Mirrors `mapping_rules` shape; adds one entry to `_VALID_TOP_LEVEL_KEYS`. Stays at the top level (not nested under `obsidian:`) so the override is portable to other future export targets.
- **D-10:** Each rule has explicit field selector: `{match: 'label' | 'id', pattern: <str|int>, template: <relative-path>}`. No magic auto-detection — the user states which field they want to match.
- **D-11:** Pattern syntax is **fnmatch-style globs** (`transformer*`, `auth-?`, `[Aa]rchitecture*`). Stdlib `fnmatch`, no new deps. Matches the `.gitignore`/`.graphifyignore` mental model already used elsewhere in graphify.
- **D-12:** Override scope is **MOC-only** — applies to the community's MOC note; member nodes (Things, Statements, People, Sources) keep their type-based templates. Smallest, clearest scope; cleanly maps to the existing `community-overview-template.md` concept.
- **D-13:** First-match-wins precedence — consistent with v1.0 `mapping_rules`. Rules are evaluated top-to-bottom; first rule whose `match`/`pattern` hits the community wins. No-match falls back to the default community template (existing behavior unchanged).

### --validate-profile Output (CFG-02 + CFG-03)

- **D-14:** Every `--validate-profile` run prints three new sections in plain text (no new flags required):
  1. **Merge chain:** `base.yaml → fusion-base.yaml → profile.yaml` (in resolution order)
  2. **Field provenance:** dotted-key list showing which file contributed each leaf field (e.g., `folder_mapping.thing ← base.yaml`, `naming.convention ← fusion-base.yaml`)
  3. **Resolved community templates:** the `community_templates` rule list as written (pattern → template path), with a note that actual community-to-template assignments require a graph (run after `graphify`)
- **D-15:** "Lost fields when removing an `extends:` ref" (success criterion 4) is satisfied by the field-provenance table — users remove the reference, re-run `--validate-profile`, and the provenance table reveals exactly which keys disappeared. No separate diff engine, no `--explain-removal` flag in this phase.
- **D-16:** Output stays in plain text (matches existing `--validate-profile` style). No `--json` output, no tree-style nesting in this phase. Both deferred for now.
- **D-17:** `--validate-profile` remains **graph-blind** — it does not auto-load `graphify-out/graph.json`. Resolved community-template *assignments* against real community labels are out of scope for this phase; the rule list is dumped as-written.

### Claude's Discretion

- File-format details (delimiters, whitespace, ordering) within the `--validate-profile` output — match the existing visual style.
- Internal API: how `load_profile()` is split between resolution (chain walk) and merge (deep-merge) is an implementation detail; the resolver MUST be the single source of truth used by both `load_profile()` (production) and `--validate-profile` (preflight) so they cannot diverge.
- Cycle/depth check ordering and exact error wording.
- Test fixture layout under `tests/fixtures/profiles/` — pick a clear convention.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Phase Specifications & Roadmap
- `.planning/ROADMAP.md` §"Phase 30: Profile Composition" — goal, dependencies (none), success criteria 1–4, requirement mapping (CFG-02/CFG-03).
- `.planning/REQUIREMENTS.md` §"Profile Composition (deferred from v1.0)" — CFG-02 (extends/includes mechanism, cycle detection, deterministic merge order), CFG-03 (per-community template overrides, first-match-wins consistent with v1.0 mapping engine).
- `.planning/PROJECT.md` §"Constraints" — Python 3.10+, no new required deps (PyYAML already optional under the obsidian/all extras), backward compatible, pure unit tests with `tmp_path`, profile sanitization.

### Existing Profile System (must extend, not replace)
- `graphify/profile.py` — full module. Specifically: `_deep_merge()` (lines 156–166), `load_profile()` (lines 167–202), `validate_profile()` (line 207+), `validate_profile_preflight()` (the `--validate-profile` engine), `_DEFAULT_PROFILE` (lines 36–105), `_VALID_TOP_LEVEL_KEYS` (line 105) — must add `extends`, `includes`, `community_templates`.
- `graphify/__main__.py:1265–1280` — current `--validate-profile <vault-path>` CLI dispatch. Output extension lives here.
- `graphify/security.py` — `validate_vault_path()` and path-traversal guards. All fragment-path resolution flows through this contract.

### Prior Decisions That Apply Here
- `.planning/phases/27-vault-detection-profile-driven-output-routing/27-CONTEXT.md` — vault detection establishes the `.graphify/` directory contract that fragments live under.
- `.planning/phases/04-merge-engine/` (v1.0) — D-02 deep-merge, D-64 per-key field policies, D-65 user-overrides-defaults are the merge-semantics precedent the composition resolver must respect.
- `.planning/phases/03-mapping-engine/` (v1.0) — `mapping_rules` first-match-wins precedent that `community_templates` mirrors per success criterion 2.

### Codebase Maps
- `.planning/codebase/STRUCTURE.md` — module layout.
- `.planning/codebase/ARCHITECTURE.md` — pipeline boundaries.
- `.planning/codebase/CONVENTIONS.md` — error-handling and validation patterns (errors-as-list-of-strings from `validate.py`).

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `graphify/profile.py::_deep_merge()` — recursive override-wins-at-leaf merge. The composition resolver wraps this; it does not replace it. New code calls `_deep_merge` once per fragment in the composed chain.
- `graphify/profile.py::validate_profile()` — already returns `list[str]` of error strings (empty == valid). New cycle/depth/path errors append to the same list, same pattern.
- `graphify/profile.py::validate_profile_preflight()` — the `--validate-profile` engine. Extend its output, do not duplicate logic in `__main__.py`.
- `_VALID_TOP_LEVEL_KEYS` whitelist (line 105) — schema-extension surface. Add `extends`, `includes`, `community_templates`.
- `graphify/security.py::validate_vault_path()` — path-traversal guard reused for fragment-path resolution.
- `fnmatch` (stdlib) — already used elsewhere in graphify for `.graphifyignore` matching; same pattern syntax for `community_templates`.

### Established Patterns
- **Errors-as-list, not raise:** `validate_profile()` accumulates error strings; the caller decides whether to raise or fall back. Composition errors (cycle, depth, path-escape) follow the same pattern.
- **Graceful fallback in `load_profile()`:** any profile error → print to stderr, return `_deep_merge(_DEFAULT_PROFILE, {})`. Composition must preserve this — graphify never crashes from a bad vault profile.
- **First-match-wins for ordered rule lists:** `mapping_rules` precedent. `community_templates` adopts the identical evaluation strategy.
- **Deep-merge with per-key policies:** Phase 4 D-64 introduced field-level policy overrides (`replace`/`union`/`preserve`). Composition must continue to honor these — `merge.field_policies` from any layer in the chain participates in the deep-merge.

### Integration Points
- `load_profile()` becomes a thin wrapper around a new resolver function (e.g., `_resolve_profile_chain()`) that walks `extends:`/`includes:`, detects cycles, enforces depth, and returns the composed dict.
- `validate_profile_preflight()` calls the same resolver, records the chain order, the per-key provenance during merge, and the unresolved `community_templates` list, then emits them in `--validate-profile` output.
- Obsidian export path (`graphify/export.py::to_obsidian` → community-MOC rendering) consults `community_templates` for the override path before falling back to the default `community-overview-template.md`. New code surface in export is small — the resolver does the heavy lifting.
- `graphify doctor` (Phase 29) is unchanged in this phase but indirectly benefits: when a vault is detected and the profile composes cleanly, `doctor` continues to report success; cycle/depth errors surface via `load_profile()`'s stderr path which `doctor` already captures.

</code_context>

<specifics>
## Specific Ideas

- The merge chain rendering in `--validate-profile` should look like: `base.yaml → fusion-base.yaml → profile.yaml` — arrows, in resolution order, root-most ancestor first.
- Field provenance should be a flat dotted-key list, not a nested tree, for grep-ability.
- Recommended example layout (documentation only — not enforced):
  ```
  .graphify/
    profile.yaml          # extends: bases/fusion.yaml, includes: [mixins/team-tags.yaml]
    bases/
      fusion.yaml         # extends: ../core.yaml
      core.yaml
    mixins/
      team-tags.yaml
    fragments/
      community-overrides.yaml
  ```

</specifics>

<deferred>
## Deferred Ideas

- **`--validate-profile --json`** output for tooling/CI consumption. Plain text only in this phase.
- **`--explain-removal <fragment>`** targeted-diff CLI flag. Field provenance table covers the success criterion; explicit removal-explanation flag deferred.
- **Tree-style provenance rendering** with nested ASCII tree visualization. Plain dotted keys this phase.
- **Auto-resolving community-to-template assignments** by loading `graphify-out/graph.json` during `--validate-profile`. Validate-profile stays graph-blind in this phase.
- **Org-wide / user-global fragments** (absolute paths, `~/.graphify/`). Strict in-vault confinement only this phase — revisit if a multi-vault use case emerges.
- **Extending overrides beyond MOC notes** (per-community templates for Things, Statements, etc.). MOC-only this phase; the schema is forward-compatible if we later need per-type overrides via a `templates:` dict.
- **Multi-parent `extends:` (string-or-list)** — single-parent only this phase to keep `extends:` semantically distinct from `includes:`.
- **Regex pattern syntax** for `community_templates` matching. fnmatch only this phase; regex deferred unless real-world patterns demand it.

</deferred>

---

*Phase: 30-profile-composition*
*Context gathered: 2026-04-28*
