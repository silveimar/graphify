# Phase 36: Migration Guide, Skill Alignment & Regression Sweep - Context

**Gathered:** 2026-04-29T06:36:00Z
**Status:** Ready for planning

<domain>
## Phase Boundary

Phase 36 closes v1.8 by making the shipped behavior explainable, consistent, and verifiable. It owns the Markdown migration guide, all platform skill/docs alignment for the v1.8 Obsidian export contract, regression tests proving the contract, and final security/sanitization evidence. It builds on Phase 35's `update-vault` preview/apply path and now also includes automatic legacy-note archiving during apply. It does not redesign the Obsidian adapter, introduce destructive deletion, or add unrelated vault-selection/product features.

</domain>

<decisions>
## Implementation Decisions

### Migration Guide And Archive Behavior
- **D-01:** The migration guide should be generic first: document the `--input` raw corpus plus `--vault` Obsidian target pattern for any vault, with `work-vault/raw` -> `ls-vault` as the canonical example rather than the entire framing.
- **D-02:** Phase 36 should implement automatic legacy-note archiving as part of migration apply, not just document manual cleanup.
- **D-03:** Archive happens by default when applying a reviewed migration plan. Users should not need a separate archive flag for normal apply.
- **D-04:** Archived legacy notes go outside the vault notes tree under `graphify-out/migrations/archive/`, preserving enough original relative path information for review and rollback.
- **D-05:** The guide must treat backup as a hard prerequisite before apply/archive, then place rollback instructions immediately after the apply step.

### Skill And Documentation Alignment
- **D-06:** Update all shipped platform skill variants directly so every installed platform reflects the v1.8 Obsidian behavior.
- **D-07:** Add exact shared-phrase tests that assert every variant contains required v1.8 wording and omits stale `_COMMUNITY_*` generated-output claims.
- **D-08:** English docs are in scope. Leave localized READMEs (`README.ja-JP.md`, `README.ko-KR.md`, `README.zh-CN.md`) for a later translation pass.
- **D-09:** Planner may choose the cleanest command framing for skills, but the result must clearly distinguish existing-vault migration/update from lower-level Obsidian export and must not confuse users about when writes happen.

### Regression Gate
- **D-10:** Planner may choose the exact focused/full test cadence, but the evidence must be strong enough for milestone audit.
- **D-11:** Prioritize docs/skills/security contract meta-tests: required phrases, forbidden legacy claims, and a sanitizer coverage matrix.
- **D-12:** Automatic archive-by-default needs both helper-level and CLI-level tests using `tmp_path`.
- **D-13:** The two known baseline failures (`test_detect_skips_dotfiles`, `test_collect_files_from_dir`) should be fixed only if they block the full Phase 36 verification gate.

### Security And Sanitization Proof
- **D-14:** VER-03 evidence should include a sanitizer coverage matrix in tests and verification/security artifacts. Each input class should map to the helper and test that proves it.
- **D-15:** Archive path safety is Claude/planner discretion, with hard constraints: rollback must be clear, vault files must not be deleted, and archive movement must be confinement-safe.
- **D-16:** Automatic archive-by-default should be treated as fully mitigated behavior, not an accepted risk, if it is review-plan-driven, reversible, confined to artifacts, and covered by tests.

### Claude's Discretion
- Exact guide filename/location, section order, and wording are up to the planner as long as the guide covers backup, validation, dry-run, migration command, review, cleanup/archive, rollback, and rerun steps.
- Exact skill command framing is up to the planner, as long as all variants stop claiming legacy `_COMMUNITY_*` overview notes are generated and clearly describe safe preview/apply behavior.
- Exact archive path layout under `graphify-out/migrations/archive/` is up to the planner, as long as it preserves reviewability and rollback.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Phase Definition
- `.planning/ROADMAP.md` — Phase 36 goal, requirements, success criteria, and Phase 35 dependency.
- `.planning/REQUIREMENTS.md` — Traceability for `MIG-05`, `VER-01`, `VER-02`, and `VER-03`.
- `.planning/PROJECT.md` — v1.8 milestone goal, target features, constraints, and out-of-scope boundaries.
- `.planning/STATE.md` — Carry-forward v1.8 decisions and current phase state.

### Prior Phase Contracts
- `.planning/phases/33-naming-repo-identity-helpers/33-CONTEXT.md` — Repo identity precedence, concept naming policy, cache/provenance, and sink-safety decisions.
- `.planning/phases/34-mapping-cluster-quality-note-classes/34-CONTEXT.md` — MOC-only output, CODE note identity, CODE filenames, and Phase 36 docs boundary.
- `.planning/phases/35-templates-export-plumbing-dry-run-migration-visibility/35-CONTEXT.md` — `update-vault` command shape, preview/apply safety, legacy surfacing, repo identity propagation, and Phase 36 boundary.
- `.planning/phases/35-templates-export-plumbing-dry-run-migration-visibility/35-VERIFICATION.md` — Verified Phase 35 behavior that Phase 36 must document and regression-test.

### Docs And Skill Surfaces
- `README.md` — English user docs to update with v1.8 migration/update guidance.
- `CHANGELOG.md` — Release notes surface for v1.8 behavior changes if planner chooses to update it.
- `graphify/skill.md` — Main skill variant and current source of stale `_COMMUNITY_*` output wording.
- `graphify/skill-codex.md` — Codex skill variant to align.
- `graphify/skill-copilot.md` — Copilot skill variant to align.
- `graphify/skill-opencode.md` — OpenCode skill variant to align.
- `graphify/skill-claw.md` — Claw skill variant to align.
- `graphify/skill-droid.md` — Factory Droid skill variant to align.
- `graphify/skill-trae.md` — Trae skill variant to align.
- `graphify/skill-windows.md` — Windows skill variant to align.
- `graphify/skill-aider.md` — Aider skill variant to align if it contains the Obsidian export block.

### Implementation And Test Surfaces
- `graphify/migration.py` — Migration preview/apply, plan validation, and new archive behavior.
- `graphify/__main__.py` — `update-vault` CLI command and help text.
- `graphify/export.py` — Obsidian dry-run/render context, repo identity, and merge-plan construction.
- `graphify/merge.py` — Merge action vocabulary, apply behavior, manifest metadata, and non-delete safety.
- `graphify/profile.py` — `validate_vault_path`, `safe_filename`, `safe_tag`, `safe_frontmatter_value`, and profile validation helpers.
- `graphify/templates.py` — Frontmatter, wikilink, tag, and template sink safety.
- `graphify/naming.py` — Repo identity and LLM/fallback concept-name validation.
- `tests/test_migration.py` — Migration preview/apply/archive tests.
- `tests/test_main_flags.py` — CLI/help/apply gate tests.
- `tests/test_skill_files.py` — Skill variant drift tests.
- `tests/test_export.py`, `tests/test_merge.py`, `tests/test_templates.py`, `tests/test_profile.py`, `tests/test_naming.py` — Existing v1.8 behavior and sanitizer coverage homes.

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `graphify/migration.py` already owns `run_update_vault()`, migration artifacts, plan IDs, request matching, drift checks, and preview/apply orchestration.
- `graphify/merge.py` already separates write actions from `SKIP_PRESERVE`, `SKIP_CONFLICT`, and `ORPHAN`; archive logic should preserve the no-delete invariant.
- `graphify/profile.py` already exposes path and sink sanitizers that Phase 36 should use or verify for archive paths, profile paths, tags, frontmatter, and filenames.
- `tests/test_skill_files.py` already exists as a natural home for exact shared-phrase and forbidden-legacy-claim checks.
- `tests/test_migration.py` and `tests/test_main_flags.py` already cover Phase 35 preview/apply behavior and should be extended for archive-by-default.

### Established Patterns
- Tests are pure pytest functions, use `tmp_path` for filesystem effects, and avoid network calls.
- Platform skill variants are separate Markdown files under `graphify/`; Phase 36 should update each shipped variant rather than relying on users to infer from the main skill.
- Safety-sensitive user operations are preview-first, artifact-backed, and explicit about writes.
- Existing project convention is to report warnings to stderr with `[graphify]` and keep library APIs explicit and side-effect-bounded.

### Integration Points
- Extend `run_update_vault()` apply handling to archive legacy review rows by default after a matching reviewed plan is accepted.
- Add archive metadata to migration artifacts or result summaries so users can review what moved and roll back.
- Update README/guide and skill variants to describe the same command semantics and output taxonomy.
- Add contract tests that fail if skill/docs drift back to legacy `_COMMUNITY_*` overview claims or omit v1.8 safety wording.
- Add a sanitizer matrix test or equivalent artifact that proves paths, templates, profile values, LLM labels, and repo identity inputs hit the intended helpers.

</code_context>

<specifics>
## Specific Ideas

- The migration guide should be reusable, but the canonical example remains `graphify update-vault --input work-vault/raw --vault ls-vault`.
- Archive-by-default means apply is no longer purely note writes; planners must make the archive movement reviewed, reversible, and visible.
- Archive location should be outside the vault note tree: `graphify-out/migrations/archive/`.
- Backups are not optional prose; they are a prerequisite step in the guide.
- Localized READMEs are deliberately out of scope for this phase.

</specifics>

<deferred>
## Deferred Ideas

- Localized README translation/synchronization for v1.8 migration guidance.
- Any destructive cleanup or deletion workflow for legacy notes.
- Broader multi-vault selector or explicit vault-selection UX beyond the current `--vault` flag.

</deferred>

---

*Phase: 36-Migration Guide, Skill Alignment & Regression Sweep*
*Context gathered: 2026-04-29T06:36:00Z*
