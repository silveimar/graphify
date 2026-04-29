# Phase 32: Profile Contract & Defaults - Context

**Gathered:** 2026-04-28
**Status:** Ready for planning

<domain>
## Phase Boundary

Phase 32 locks the v1.8 default vault taxonomy, profile keys, validation behavior, and compatibility precedence before downstream export behavior changes. This phase is the contract layer: it updates defaults, schema validation, profile preflight/doctor surfaces, and planning requirement wording so later phases can implement rendering, migration, and note-class behavior against one stable contract.

</domain>

<decisions>
## Implementation Decisions

### Default Taxonomy Shape
- **D-01:** All generated Obsidian notes produced by the built-in/default profile must live under the Graphify-owned subtree `Atlas/Sources/Graphify/`.
- **D-02:** Concept MOCs must live under `Atlas/Sources/Graphify/MOCs/`.
- **D-03:** Default non-MOC generated notes should use typed subfolders under `Atlas/Sources/Graphify/`, such as `Things/`, `Statements/`, `People/`, and `Sources/`.
- **D-04:** The v1.8 default taxonomy covers Markdown vault notes only. Manifests, dry-run artifacts, audit files, and other non-note artifacts keep existing `graphify-out` behavior in this phase.
- **D-05:** Built-in bucket names should be explicit and stable: `Graphify`, `MOCs`, and `_Unclassified`, while still respecting previously established naming standards.

### Profile Contract Keys
- **D-06:** Use `mapping.min_community_size` as the canonical profile key for the cluster-quality floor.
- **D-07:** Existing requirement wording that says `clustering.min_community_size` must be revised to `mapping.min_community_size`.
- **D-08:** Add a top-level `taxonomy:` block for v1.8 taxonomy version/default folder semantics.
- **D-09:** Profiles that explicitly request deprecated community overview output should produce hard-deprecated warnings in Phase 32, not fatal errors yet.
- **D-10:** New v1.8 defaults should live directly in `_DEFAULT_PROFILE` so `load_profile()`, `validate_profile()`, preflight, and doctor all see the same contract.

### Validation Severity And Messages
- **D-11:** Unsupported `taxonomy:` keys and malformed taxonomy folder entries are validation errors. They should fail `--validate-profile` to prevent silent misrouting.
- **D-12:** Deprecated community overview warnings should name the deprecated setting/template and point users toward MOC-only output plus migration guidance.
- **D-13:** `mapping.moc_threshold` is invalid immediately in v1.8. Users must migrate to `mapping.min_community_size`.
- **D-14:** Update requirements/traceability to reflect the immediate `mapping.moc_threshold` break instead of preserving CLUST-04's current legacy-precedence wording.
- **D-15:** v1.8 validation findings should surface through both `graphify --validate-profile` and `graphify doctor`, sharing the same validator/preflight source.

### Compatibility And Precedence
- **D-16:** If `taxonomy:` and explicit `folder_mapping` both define folder placement, `taxonomy:` wins.
- **D-17:** Existing user profiles that do not add the new `taxonomy:` or `mapping.min_community_size` keys should fail validation. Backward compatibility is not required for this branch because there is no active profile being used now.
- **D-18:** Update all v1.8 requirement and roadmap references during Phase 32 so later phases inherit the new contract.

### Folded Todos
- **D-19:** Fold `.planning/todos/pending/fix-ls-vault-profile-routing.md` into this phase. The no-profile/default contract must ensure Obsidian/vault note output does not dump generated notes into the vault root; default vault note paths should use the Graphify-owned subtree.

### Claude's Discretion
- **D-20:** For non-vault runs, preserve prior output behavior unless implementation research shows it conflicts with the v1.8 contract. The no-root guarantee applies to Obsidian/vault note output.

</decisions>

<specifics>
## Specific Ideas

- The user intentionally chose a clean v1.8 contract break over backward compatibility for legacy profile keys.
- The planner should not preserve `mapping.moc_threshold` via aliases or soft precedence unless it first updates this context with a new user decision.
- The phrase "no profile being used now" is important: the strict validation posture is acceptable because the immediate target workflow does not depend on an existing custom profile.

</specifics>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Planning Contract
- `.planning/ROADMAP.md` — Phase 32 goal, success criteria, and all v1.8 phase references that must be updated for the new contract.
- `.planning/REQUIREMENTS.md` — Existing TAX/COMM/CLUST traceability; must be revised where it conflicts with `mapping.min_community_size`, invalid `mapping.moc_threshold`, and taxonomy precedence.
- `.planning/PROJECT.md` — Current milestone goals and locked v1.8 decisions.
- `.planning/STATE.md` — Current phase state and active milestone context.
- `.planning/todos/pending/fix-ls-vault-profile-routing.md` — Folded todo for vault-root dumping/profile routing.

### Code Contract
- `graphify/profile.py` — `_DEFAULT_PROFILE`, `_VALID_TOP_LEVEL_KEYS`, `validate_profile()`, `validate_profile_preflight()`, and profile safety helpers.
- `graphify/mapping.py` — Current `mapping.moc_threshold` community routing behavior that Phase 32 must replace.
- `graphify/templates.py` — MOC/community rendering and note-type template contracts.
- `graphify/doctor.py` — Doctor/preflight reporting surface for shared validation findings.
- `tests/test_profile.py` — Existing profile schema/default/preflight tests to extend or update.

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `graphify.profile._DEFAULT_PROFILE` already centralizes built-in profile defaults and is the correct home for v1.8 default taxonomy and canonical `mapping.min_community_size`.
- `graphify.profile.validate_profile()` already validates top-level keys, nested dict shapes, path traversal, bool-vs-int pitfalls, and output/profile sections using an accumulated error-list pattern.
- `graphify.profile.validate_profile_preflight()` already provides the shared validation/preflight surface that can feed both `--validate-profile` and doctor-style reporting.
- `graphify.doctor.run_doctor()` and `format_report()` already surface profile validation and recommended fixes in user-facing output.

### Established Patterns
- Profile schema additions are atomic across `_DEFAULT_PROFILE`, `_VALID_TOP_LEVEL_KEYS`, `validate_profile()`, and tests.
- Validation returns lists of actionable strings instead of raising for ordinary profile mistakes.
- Path-like profile fields should reject absolute paths, `~`, and traversal early, with write-time `validate_vault_path()` as a second line of defense.
- Tests for profile changes belong primarily in `tests/test_profile.py`, with integration coverage added where export behavior changes later.

### Integration Points
- `graphify/mapping.py::_assemble_communities()` currently reads `profile["mapping"]["moc_threshold"]`; Phase 32 should move this contract to `mapping.min_community_size` and reject legacy usage.
- `graphify/templates.py::_render_moc_like()` consumes classification context and should not own taxonomy precedence decisions.
- Future rendering/export phases should consume the taxonomy/profile contract from the profile layer instead of hardcoding folder paths independently.

</code_context>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope.

</deferred>

---

*Phase: 32-profile-contract-defaults*
*Context gathered: 2026-04-28*
