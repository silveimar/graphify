# Phase 35: Templates, Export Plumbing & Dry-Run/Migration Visibility - Context

**Gathered:** 2026-04-29T05:05:47.296Z
**Status:** Ready for planning

<domain>
## Phase Boundary

Phase 35 makes the v1.8 Obsidian export/update path previewable and runnable without silent overwrites, hidden legacy artifacts, or repo identity drift. It owns the dedicated update command for the real `work-vault/raw/` to `ls-vault` workflow, migration preview artifacts, legacy `_COMMUNITY_*` surfacing, repo identity propagation into CODE note metadata, and the safety gate before writes. Phase 36 owns the migration guide, skill alignment, and regression/security sweep.

</domain>

<decisions>
## Implementation Decisions

### Migration Command Shape
- **D-01:** Add a dedicated user-facing command shaped as `graphify update-vault --input work-vault/raw --vault ls-vault`.
- **D-02:** The workflow is not vault-to-vault. The source is the raw corpus under `work-vault/raw/`; the Obsidian vault target is `ls-vault`.
- **D-03:** `update-vault` must not imply a destructive full rebuild of `ls-vault`. It previews and applies graphify-managed note updates inside an existing vault.
- **D-04:** Preview is the default. Writes require an explicit apply path.
- **D-05:** The command runs the full graphify pipeline from `--input` by default so one command can go from raw corpus to vault preview/apply. Existing caches may make reruns cheap, but consuming prebuilt artifacts is not the default user flow.

### Legacy Note Matching
- **D-06:** Legacy surfacing should combine the existing manifest with a bounded vault scan: read `vault-manifest.json` first, then scan `ls-vault` for legacy `_COMMUNITY_*` files and graphify-managed fingerprints.
- **D-07:** Identity matching should trust manifest node/community identity first, graphify-managed frontmatter second, and filename heuristics last.
- **D-08:** Unmatched legacy `_COMMUNITY_*` files are reported as ORPHAN review-only entries. They are never deleted or moved automatically.
- **D-09:** When an old legacy note matches a new Graphify-owned note identity, preserve the v1.8 path contract. Prefer showing the new path action plus a legacy mapping note while preserving the old file as an ORPHAN/review item unless the user cleans it manually.

### Review Output And Apply Gate
- **D-10:** Preview output should include both a human-readable summary and structured machine-readable artifacts.
- **D-11:** Preview mode should write both Markdown and JSON migration plan artifacts in the artifacts directory so humans can review and agents/tests can consume the same plan.
- **D-12:** The human preview should balance readability with safety: grouped counts with representative rows are acceptable, but risky cases must be expanded.
- **D-13:** Always expand `SKIP_CONFLICT`, `SKIP_PRESERVE`, `ORPHAN`, and `REPLACE` rows in terminal output even if non-risky actions are summarized.
- **D-14:** Applying writes requires `--apply --plan-id <id>` where the plan id comes from the preview artifact. `--apply` alone is not enough.

### Repo Identity Propagation
- **D-15:** CODE notes should include the resolved repo identity in frontmatter as `repo: <identity>`.
- **D-16:** CODE notes should include a repo tag such as `repo/graphify` for Obsidian filtering.
- **D-17:** Manifests should record repo identity both per note entry and in run-level metadata so repo drift is easy to audit.
- **D-18:** If preview detects existing managed notes from a different repo identity, it should report `SKIP_CONFLICT` until the user explicitly resolves or overrides the drift.
- **D-19:** Dry-run and preview output should show resolved repo identity in a top banner and include it in CODE note rows.

### Claude's Discretion
- For `D-09`, planners may choose the exact wording and data shape for legacy mapping notes, as long as old files are not updated in place, v1.8 paths remain canonical, and legacy files remain review-only unless the user acts manually.
- For `D-12`, planners may choose the default number of representative rows per low-risk action group, as long as risky actions listed in `D-13` are always expanded and `--verbose` or equivalent can reveal all rows.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Phase Definition
- `.planning/ROADMAP.md` - Phase 35 goal, requirements, success criteria, and Phase 36 boundary.
- `.planning/REQUIREMENTS.md` - Traceability for `COMM-02`, `REPO-04`, `MIG-01`, `MIG-02`, `MIG-03`, `MIG-04`, and `MIG-06`.
- `.planning/PROJECT.md` - v1.8 milestone goal and core constraints.
- `.planning/STATE.md` - Carry-forward v1.8 decisions and current milestone state.

### Prior Phase Contracts
- `.planning/phases/32-profile-contract-defaults/32-CONTEXT.md` - v1.8 taxonomy, strict profile validation, `mapping.min_community_size`, and deprecated community overview warnings.
- `.planning/phases/33-naming-repo-identity-helpers/33-CONTEXT.md` - repo identity precedence, concept naming, and identity sidecar expectations.
- `.planning/phases/34-mapping-cluster-quality-note-classes/34-CONTEXT.md` - MOC-only output, CODE note identity, CODE filenames, and Phase 35 migration boundaries.

### Code Integration Points
- `graphify/__main__.py` - CLI entry point and existing flag parsing patterns.
- `graphify/output.py` - vault detection and output destination resolution.
- `graphify/export.py` - `to_obsidian()`, repo identity resolution, concept naming, CODE filename injection, dry-run return path, and merge-plan construction.
- `graphify/merge.py` - merge action vocabulary, `compute_merge_plan()`, `apply_merge_plan()`, `format_merge_plan()`, manifest loading/saving, ORPHAN behavior, and safety rules.
- `graphify/templates.py` - frontmatter generation, note rendering, CODE/MOC template context, wikilink and tag safety.
- `graphify/profile.py` - `safe_filename`, `safe_tag`, `safe_frontmatter_value`, `_dump_frontmatter`, and profile validation helpers.

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `graphify.merge.MergeAction`, `MergePlan`, and `format_merge_plan()` already provide the action vocabulary and grouped dry-run output shape for `CREATE`, `UPDATE`, `SKIP_PRESERVE`, `SKIP_CONFLICT`, `REPLACE`, and `ORPHAN`.
- `graphify.merge.compute_merge_plan()` already detects ORPHAN entries from previously managed paths and never deletes them.
- `graphify.merge.apply_merge_plan()` only writes `CREATE`, `UPDATE`, and `REPLACE`; it skips `SKIP_PRESERVE`, `SKIP_CONFLICT`, and `ORPHAN`.
- `graphify.export.to_obsidian()` already returns a `MergePlan` when `dry_run=True` and writes `repo-identity.json` on non-dry-run exports.
- `graphify.output.resolve_output()` already separates vault note destination from artifacts directory and is the closest model for `--vault` / `--input` output resolution.

### Established Patterns
- Safety-sensitive behavior is preview-first and action-vocabulary driven rather than implicit filesystem mutation.
- User content wins: user-modified notes receive `SKIP_PRESERVE`, unmanaged files receive `SKIP_CONFLICT`, and orphaned managed files are reported but not deleted.
- Manifest writers use JSON sidecars and atomic write patterns.
- Profile/template/filename values must pass through existing sanitization helpers before reaching filenames, tags, frontmatter, wikilinks, or Dataview-adjacent content.

### Integration Points
- Add the dedicated `update-vault` command in `graphify/__main__.py`, using `--input`, `--vault`, `--apply`, and `--plan-id`.
- Reuse the existing pipeline and `to_obsidian()` path rather than creating a separate renderer.
- Extend manifest data produced by `merge.py`/`export.py` with repo identity run metadata and per-note repo identity where applicable.
- Extend dry-run/preview formatting with repo identity banner/rows and persistent Markdown/JSON migration plan artifacts.
- Add bounded legacy scanning that supplements manifest-based matching without deleting or moving legacy files.

</code_context>

<specifics>
## Specific Ideas

- The real workflow is `work-vault/raw/` as source corpus into `ls-vault` as the existing Obsidian vault.
- The command should feel like an update/review operation, not a rebuild or a vault-to-vault migration.
- Preview artifacts need stable plan IDs because applying requires `--apply --plan-id <id>`.
- Legacy `_COMMUNITY_*` files are review-only evidence. They should be visible, but graphify should not update them in place or delete them automatically.
- Repo identity should be obvious in preview output because drift is a user-facing risk, not only an internal metadata concern.

</specifics>

<deferred>
## Deferred Ideas

None - discussion stayed within Phase 35 scope.

</deferred>

---

*Phase: 35-templates-export-plumbing-dry-run-migration-visibility*
*Context gathered: 2026-04-29T05:05:47.296Z*
