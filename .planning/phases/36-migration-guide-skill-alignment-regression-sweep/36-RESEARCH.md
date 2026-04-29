# Phase 36: Migration Guide, Skill Alignment & Regression Sweep - Research

**Researched:** 2026-04-29  
**Domain:** Obsidian migration safety, platform skill drift prevention, docs/test/security regression coverage  
**Confidence:** HIGH

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

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

### Deferred Ideas (OUT OF SCOPE)
- Localized README translation/synchronization for v1.8 migration guidance.
- Any destructive cleanup or deletion workflow for legacy notes.
- Broader multi-vault selector or explicit vault-selection UX beyond the current `--vault` flag.
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| MIG-05 | User receives a Markdown migration guide with backup, validation, dry-run, migration command, review, cleanup, rollback, and rerun steps. | Use one generic-first English guide plus README pointer; include backup as prerequisite and rollback immediately after apply/archive. [VERIFIED: .planning/REQUIREMENTS.md] [VERIFIED: .planning/phases/36-migration-guide-skill-alignment-regression-sweep/36-CONTEXT.md] |
| VER-01 | Maintainer can verify v1.8 behavior with pure unit tests that use `tmp_path` and perform no network calls. | Extend existing pytest suites under `tests/` and keep filesystem effects under `tmp_path`; current project convention is pure unit tests. [VERIFIED: CLAUDE.md] [VERIFIED: tests/test_migration.py] [VERIFIED: tests/test_main_flags.py] |
| VER-02 | Maintainer can confirm skill files and CLI docs use the same v1.8 Obsidian export behavior. | Add shared-phrase and forbidden-phrase contract tests in `tests/test_skill_files.py`, and update `README.md` plus all package-data skill variants. [VERIFIED: tests/test_skill_files.py] [VERIFIED: pyproject.toml] |
| VER-03 | Maintainer can confirm all new path, template, profile, LLM-label, and repo-identity inputs pass through existing security/sanitization helpers. | Add a sanitizer coverage matrix test/artifact mapping input classes to `validate_vault_path`, `validate_sibling_path`, `safe_filename`, `safe_tag`, `safe_frontmatter_value`, `_sanitize_wikilink_alias`, `_sanitize_generated_title`, and `normalize_repo_identity`. [VERIFIED: graphify/profile.py] [VERIFIED: graphify/templates.py] [VERIFIED: graphify/naming.py] |
</phase_requirements>

## Summary

Phase 36 is not a new export architecture phase; it is a closure and regression phase over the Phase 35 migration path. Phase 35 already verified that `graphify update-vault --input work-vault/raw --vault ls-vault` is preview-first, writes migration artifacts under `graphify-out/migrations/`, requires `--apply --plan-id`, rejects stale plans, surfaces legacy `_COMMUNITY_*` files as review-only `ORPHAN` rows, and never deletes legacy files. [VERIFIED: .planning/phases/35-templates-export-plumbing-dry-run-migration-visibility/35-VERIFICATION.md]

The primary implementation change is archive-by-default during apply, after the reviewed plan has been validated and after the applicable CREATE/UPDATE/REPLACE write plan succeeds. This should be implemented in `graphify/migration.py`, not in `merge.py`, because archive semantics apply only to migration preview/apply rows and should not change the generic merge engine's non-delete behavior. [VERIFIED: graphify/migration.py] [VERIFIED: graphify/merge.py]

The rest of the phase should align user-facing docs and shipped skill files with the v1.8 contract, then add tests that make future drift obvious. The highest-risk regressions are stale `_COMMUNITY_*` generated-output claims, unclear preview-vs-apply wording, archive paths escaping the artifact directory, and sanitizer coverage being present in code but not traceable to VER-03. [VERIFIED: .planning/phases/36-migration-guide-skill-alignment-regression-sweep/36-CONTEXT.md] [VERIFIED: graphify/skill.md] [VERIFIED: tests/test_skill_files.py]

**Primary recommendation:** Plan Phase 36 as four small plans: archive-by-default helpers, migration guide/README/CLI wording, platform skill shared-phrase alignment, and sanitizer/security regression evidence.

## Project Constraints (from .cursor/rules/)

No `.cursor/rules/*.md` files were found in this workspace during research. [VERIFIED: Glob .cursor/rules/*.md]

Project-level constraints still apply from `CLAUDE.md`: Python 3.10+ support, no new required dependencies, no configured formatter/linter, pytest as the verification gate, pure unit tests without network calls, and security-sensitive inputs going through existing validation/sanitization helpers. [VERIFIED: CLAUDE.md]

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Migration preview/apply orchestration | CLI / Python library boundary | Export/Merge helpers | `graphify __main__.py` parses `update-vault` and delegates to `run_update_vault()`, while `migration.py` owns preview/apply orchestration. [VERIFIED: graphify/__main__.py] [VERIFIED: graphify/migration.py] |
| Legacy-note archive movement | Migration helper layer | Filesystem/artifact layer | Archive decisions depend on migration preview rows, reviewed plan IDs, and legacy `ORPHAN` metadata, so they belong beside `filter_applicable_actions()` and `_merge_plan_from_preview()`. [VERIFIED: graphify/migration.py] |
| Generic merge behavior | Merge engine | Templates/profile | `apply_merge_plan()` writes CREATE/UPDATE/REPLACE and skips non-write actions; Phase 36 should not alter this generic contract. [VERIFIED: graphify/merge.py] [VERIFIED: .planning/phases/35-templates-export-plumbing-dry-run-migration-visibility/35-VERIFICATION.md] |
| Documentation and migration guide | Docs layer | CLI help | `README.md` currently documents the older Obsidian adapter shape and lacks the Phase 35 `update-vault` workflow, so Phase 36 should add the migration guide and link it from README. [VERIFIED: README.md] |
| Platform skill behavior text | Packaged skill files | Package data metadata | `pyproject.toml` packages the shipped skill variants; updating only `skill.md` would leave installed variants stale. [VERIFIED: pyproject.toml] [VERIFIED: graphify/skill.md] |
| Sanitizer regression proof | Test layer | Security artifact | Existing helpers already cover path, filename, tag, frontmatter, wikilink alias, template-title, and repo identity sinks; Phase 36 should prove their coverage in one matrix. [VERIFIED: graphify/profile.py] [VERIFIED: graphify/templates.py] [VERIFIED: graphify/naming.py] |

## Standard Stack

### Core

| Library / Module | Version | Purpose | Why Standard |
|------------------|---------|---------|--------------|
| Python | 3.10.19 available locally | Runtime for implementation and tests | Project supports Python 3.10+ and CI runs 3.10/3.12. [VERIFIED: python3 --version] [VERIFIED: CLAUDE.md] |
| pytest | 9.0.3 available locally | Unit and CLI subprocess regression tests | Existing suite uses pytest and `tmp_path`; no alternate test framework is configured. [VERIFIED: pytest --version] [VERIFIED: tests/test_migration.py] |
| stdlib `pathlib`, `json`, `os`, `shutil`, `hashlib` | Python stdlib | Confined archive paths, artifact metadata, atomic-ish file operations | Project constraint says no new required dependencies; Phase 35 migration code already uses stdlib path/artifact helpers. [VERIFIED: CLAUDE.md] [VERIFIED: graphify/migration.py] |
| Existing graphify helpers | in-repo | `validate_vault_path`, `safe_filename`, `safe_tag`, `safe_frontmatter_value`, `_sanitize_wikilink_alias`, `normalize_repo_identity` | These are already the standard sanitizer surfaces for vault paths, filenames, tags, YAML values, wikilinks, and repo identity. [VERIFIED: graphify/profile.py] [VERIFIED: graphify/templates.py] [VERIFIED: graphify/naming.py] |

### Supporting

| Library / Module | Version | Purpose | When to Use |
|------------------|---------|---------|-------------|
| PyYAML | optional `obsidian` extra | Profile parsing and tests that import `yaml` | Keep optional; tests already use `pytest.importorskip("yaml")` for profile-dependent CLI paths. [VERIFIED: pyproject.toml] [VERIFIED: tests/test_main_flags.py] |
| `subprocess` | Python stdlib | CLI-level tests | Existing `tests/test_main_flags.py` invokes `python -m graphify` with a local `PYTHONPATH`. [VERIFIED: tests/test_main_flags.py] |

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| In-repo archive helper | A new dependency or external backup tool | Violates the "no new required dependencies" constraint and would be harder to cover with pure `tmp_path` tests. [VERIFIED: CLAUDE.md] |
| Exact shared-phrase tests | Snapshotting entire skill files | Full snapshots would be brittle because skill files are large and platform-specific; phrase tests target the contract drift Phase 36 actually owns. [VERIFIED: tests/test_skill_files.py] |
| Updating only `skill.md` | Generate other variants later | `pyproject.toml` packages multiple variants directly, and Context D-06 requires direct updates. [VERIFIED: pyproject.toml] [VERIFIED: 36-CONTEXT.md] |

**Installation:** No new packages should be installed for Phase 36. [VERIFIED: CLAUDE.md]

## Architecture Patterns

### System Architecture Diagram

```text
Raw corpus (--input)
  -> run_update_vault()
  -> dry-run to_obsidian(return_render_context=True)
  -> build_migration_preview()
  -> write migration-plan-{id}.json/.md
  -> user reviews + backs up vault
  -> update-vault --apply --plan-id {id}
  -> load_migration_plan() + validate_plan_matches_request()
  -> apply_merge_plan(CREATE/UPDATE/REPLACE only)
  -> archive reviewed legacy ORPHAN rows to graphify-out/migrations/archive/
  -> print preview/apply summary with archive paths
```

### Recommended Project Structure

```text
graphify/
├── migration.py        # archive helper + apply orchestration
├── __main__.py         # update-vault help/output wording only
├── skill*.md           # platform variant wording alignment
└── builtin_templates/  # no Phase 36 change expected

tests/
├── test_migration.py   # helper-level archive tests
├── test_main_flags.py  # CLI-level archive/apply tests
├── test_skill_files.py # required/forbidden shared phrase tests
├── test_profile.py     # sanitizer coverage matrix rows
├── test_templates.py   # template/wikilink/Dataview sink matrix rows
└── test_naming.py      # LLM label/repo identity matrix rows

docs or repo root/
└── MIGRATION_V1_8.md   # recommended generic-first migration guide filename
```

### Pattern 1: Preview-Then-Apply With Plan-ID Revalidation

**What:** Generate a deterministic preview artifact first, then apply only a reviewed plan whose digest and request metadata still match the current run. [VERIFIED: graphify/migration.py]

**When to use:** Every migration apply path, including archive-by-default. [VERIFIED: graphify/migration.py]

**Example:**

```python
# Source: graphify/migration.py
loaded = load_migration_plan(resolved.artifacts_dir, str(plan_id))
validate_plan_matches_request(
    loaded,
    raw,
    vault,
    resolved_repo.identity,
    current_preview=preview,
)
applicable_plan = _merge_plan_from_preview(loaded, resolved.notes_dir)
result = apply_merge_plan(...)
```

### Pattern 2: Keep Merge Generic, Put Migration-Specific Effects in `migration.py`

**What:** `filter_applicable_actions()` currently includes only CREATE, UPDATE, and REPLACE, and ORPHAN/SKIP rows are excluded from `apply_merge_plan()`. [VERIFIED: graphify/migration.py]

**When to use:** Add archive movement after generic apply, using the loaded preview rows as the review source of truth. [VERIFIED: graphify/migration.py] [VERIFIED: graphify/merge.py]

**Example:**

```python
# Source: graphify/migration.py
def filter_applicable_actions(preview: dict) -> list[dict]:
    return [
        dict(row) for row in preview.get("actions", [])
        if row.get("action") in {"CREATE", "UPDATE", "REPLACE"}
    ]
```

### Pattern 3: Confined Source and Destination Paths

**What:** Use `validate_vault_path()` for source legacy note paths and a destination confinement check rooted at `artifacts_dir / "migrations" / "archive"`. [VERIFIED: graphify/profile.py] [VERIFIED: graphify/migration.py]

**When to use:** Archive each legacy review row. Do not trust `row["path"]` from a loaded JSON plan until it has been revalidated against the target vault and archive root. [VERIFIED: graphify/migration.py]

### Pattern 4: Drift Tests Over Large Markdown Surfaces

**What:** The existing `tests/test_skill_files.py` reads packaged skill files directly from `Path(graphify.__file__).parent`. [VERIFIED: tests/test_skill_files.py]

**When to use:** Add exact shared-phrase checks for all packaged variants and exact forbidden-stale-claim checks that do not ban legitimate legacy-warning wording. [VERIFIED: 36-CONTEXT.md] [VERIFIED: tests/test_skill_files.py]

### Anti-Patterns to Avoid

- **Do not archive inside the vault notes tree:** Context requires `graphify-out/migrations/archive/`, outside generated notes. [VERIFIED: 36-CONTEXT.md]
- **Do not add a separate normal-use archive flag:** Context locks archive-by-default during apply. [VERIFIED: 36-CONTEXT.md]
- **Do not mutate `apply_merge_plan()` to move ORPHAN files:** The merge engine is shared and currently has a non-delete/non-ORPHAN-write contract. [VERIFIED: graphify/merge.py] [VERIFIED: .planning/phases/35-templates-export-plumbing-dry-run-migration-visibility/35-VERIFICATION.md]
- **Do not forbid every `_COMMUNITY_*` mention:** The docs and skills may need to explain legacy `_COMMUNITY_*` files as migration candidates; tests should forbid stale claims that graphify generates them as v1.8 output. [VERIFIED: 36-CONTEXT.md]
- **Do not update localized READMEs:** Context explicitly defers localized README synchronization. [VERIFIED: 36-CONTEXT.md]

## Recommended Plan Decomposition

### Plan 36-01: Archive-By-Default Migration Apply

Implement a helper-level archive path in `graphify/migration.py`. Recommended helper names: `archive_legacy_notes()` and `_archive_destination()` or similarly private names consistent with existing module style. [VERIFIED: graphify/migration.py]

Tasks:
- Add a confined archive destination under `artifacts_dir / "migrations" / "archive" / plan_id / <legacy-relative-path>`, preserving the legacy relative path. [VERIFIED: 36-CONTEXT.md]
- Select only loaded preview rows with `action == "ORPHAN"`, `legacy is True`, and `review_only is True`; source paths must be validated with `validate_vault_path(row["path"], vault)`. [VERIFIED: graphify/migration.py] [VERIFIED: graphify/profile.py]
- Run archive after `apply_merge_plan()` returns no failures; if writes fail, do not archive. [VERIFIED: graphify/migration.py]
- Add archive metadata to the `run_update_vault()` apply result and terminal/Markdown summary so users can review rollback paths. [VERIFIED: graphify/__main__.py] [VERIFIED: graphify/migration.py]

Validation:
- Helper-level `tmp_path` test: legacy file moves to archive, archive preserves relative path, original vault path is absent, and file contents are preserved. [VERIFIED: tests/test_migration.py]
- Helper-level path traversal test: loaded row with `../escape.md` or absolute path raises before moving anything. [VERIFIED: graphify/profile.py]
- CLI-level `tmp_path` test: `update-vault --apply --plan-id` archives legacy `_COMMUNITY_*` after preview/apply and prints or returns archive evidence. [VERIFIED: tests/test_main_flags.py]

### Plan 36-02: Migration Guide and README/CLI Alignment

Create an English migration guide and update README/CLI wording to make the v1.8 contract clear. [VERIFIED: README.md] [VERIFIED: graphify/__main__.py]

Tasks:
- Add a generic-first Markdown guide, recommended as `MIGRATION_V1_8.md`, covering backup, validation, dry-run, migration command, review, apply/archive, rollback, and rerun. [VERIFIED: 36-CONTEXT.md]
- Use `graphify update-vault --input work-vault/raw --vault ls-vault` as the canonical example but explain that `--input` is a raw corpus and `--vault` is the target Obsidian vault. [VERIFIED: graphify/__main__.py] [VERIFIED: .planning/phases/35-templates-export-plumbing-dry-run-migration-visibility/35-VERIFICATION.md]
- Update README's Obsidian adapter section, which currently documents `--obsidian --obsidian-dir` but not the Phase 35 migration command. [VERIFIED: README.md]
- Keep localized READMEs unchanged. [VERIFIED: 36-CONTEXT.md]

Validation:
- Add docs phrase assertions in `tests/test_skill_files.py` or a small docs-specific test file if cleaner. [VERIFIED: tests/test_skill_files.py]
- Verify `graphify update-vault --help` still includes the canonical command shape. [VERIFIED: tests/test_main_flags.py]

### Plan 36-03: Platform Skill Variant Alignment

Update every shipped platform skill variant packaged in `pyproject.toml`: `skill.md`, `skill-codex.md`, `skill-opencode.md`, `skill-aider.md`, `skill-copilot.md`, `skill-claw.md`, `skill-windows.md`, `skill-droid.md`, and `skill-trae.md`. [VERIFIED: pyproject.toml]

Tasks:
- Add one shared v1.8 Obsidian behavior block to each variant. Required ideas: MOC-only community output, Graphify-owned default subtree, preview-first `update-vault`, backup before apply, archive under `graphify-out/migrations/archive/`, and no destructive deletion. [VERIFIED: 36-CONTEXT.md]
- Clarify lower-level `--obsidian` export vs existing-vault migration/update so users know when writes happen. [VERIFIED: 36-CONTEXT.md]
- Remove stale claims that v1.8 generated output includes `_COMMUNITY_*` overview notes. [VERIFIED: 36-CONTEXT.md] [VERIFIED: graphify/skill.md]

Validation:
- Extend `PLATFORM_VARIANTS` tests to assert all required phrases appear in every variant. [VERIFIED: tests/test_skill_files.py]
- Add forbidden phrase tests targeting stale generated-output claims, for example "generates `_COMMUNITY_`" or "`_COMMUNITY_*` overview notes are created"; do not fail on "legacy `_COMMUNITY_*` files are surfaced". [VERIFIED: 36-CONTEXT.md]

### Plan 36-04: Sanitizer Coverage Matrix and Final Regression Gate

Add an explicit matrix test and a security/verification artifact that maps every VER-03 input class to a helper and test. [VERIFIED: 36-CONTEXT.md]

Tasks:
- Add a matrix constant in tests, likely in `tests/test_profile.py` or a new `tests/test_v18_security_matrix.py`, with rows for path, template, profile, LLM-label, repo-identity, wikilink alias, Dataview, tag, frontmatter, CODE filename, and archive destination. [VERIFIED: tests/test_profile.py] [VERIFIED: tests/test_templates.py] [VERIFIED: tests/test_naming.py]
- Ensure each row references a callable helper and a concrete test name. [VERIFIED: 36-CONTEXT.md]
- Produce or prepare content for `36-VALIDATION.md` and security evidence during execution. [VERIFIED: .planning/config.json]

Validation:
- Focused command: `pytest tests/test_migration.py tests/test_main_flags.py tests/test_skill_files.py tests/test_profile.py tests/test_templates.py tests/test_naming.py -q`. [VERIFIED: CLAUDE.md]
- Phase gate command: `pytest tests/ -q`. [VERIFIED: CLAUDE.md]

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Vault source path safety | String prefix checks on paths | `validate_vault_path()` | It resolves paths and verifies confinement relative to the vault root. [VERIFIED: graphify/profile.py] |
| Archive destination safety | Direct `archive_root / row["path"]` without checking | A small confinement helper rooted at `artifacts_dir / "migrations" / "archive"` | Archive roots are outside the vault, so they need their own resolved containment invariant. [VERIFIED: 36-CONTEXT.md] |
| YAML/frontmatter escaping | Manual quoting | `_dump_frontmatter()` and `safe_frontmatter_value()` | Existing helpers strip controls, quote YAML-special scalars, and preserve field order. [VERIFIED: graphify/profile.py] |
| Filename and CODE stem safety | Custom regex per caller | `safe_filename()` and `build_code_filename_stems()` | Existing helpers cap length, strip Obsidian/OS-problematic chars, and handle CODE collisions deterministically. [VERIFIED: graphify/profile.py] [VERIFIED: graphify/naming.py] |
| Wikilink alias safety | Raw `[[target|label]]` construction | `_emit_wikilink()` / `_sanitize_wikilink_alias()` | Existing logic handles `]]`, `|`, newlines, and control characters in aliases. [VERIFIED: graphify/templates.py] |
| Skill drift detection | Manual visual review | `tests/test_skill_files.py` phrase/forbidden checks | Existing test file already reads every platform variant and is the right contract-test home. [VERIFIED: tests/test_skill_files.py] |

**Key insight:** Phase 36 should strengthen existing contracts rather than introduce alternate safety surfaces. The project already has sanitizer and migration primitives; the missing piece is archive-specific composition and traceable regression evidence. [VERIFIED: graphify/migration.py] [VERIFIED: graphify/profile.py] [VERIFIED: graphify/templates.py] [VERIFIED: graphify/naming.py]

## Runtime State Inventory

This phase includes migration behavior and archiving, so runtime state must be considered.

| Category | Items Found | Action Required |
|----------|-------------|-----------------|
| Stored data | Existing target vault Markdown notes and `graphify-out/vault-manifest.json` influence legacy matching and repo drift. [VERIFIED: graphify/migration.py] [VERIFIED: graphify/merge.py] | Code edit plus tests; no database migration. |
| Live service config | None found; `update-vault` is local filesystem behavior and does not call external services beyond normal extraction model use. [VERIFIED: graphify/migration.py] | None. |
| OS-registered state | None found for migration/archive behavior. [VERIFIED: graphify/__main__.py] | None. |
| Secrets/env vars | None found for migration/archive behavior; repo identity is CLI/profile/git/directory derived, not secret-backed. [VERIFIED: graphify/naming.py] | None. |
| Build artifacts | Skill files are package data in `pyproject.toml`; installed copies outside the repo update only after reinstalling graphify/skill. [VERIFIED: pyproject.toml] [VERIFIED: graphify/__main__.py] | Update packaged source variants and document reinstall/update expectation if guide mentions installed skills. |

**Nothing found in category:** external database/service/OS registration state was not found in the inspected Phase 36 surfaces. [VERIFIED: graphify/migration.py] [VERIFIED: graphify/__main__.py]

## Common Pitfalls

### Pitfall 1: Archiving Before Apply Is Fully Validated

**What goes wrong:** Legacy files move even though the plan is stale, tampered, or the current preview no longer matches. [VERIFIED: graphify/migration.py]  
**Why it happens:** Archive logic is added near preview construction instead of after `load_migration_plan()` and `validate_plan_matches_request()`. [VERIFIED: graphify/migration.py]  
**How to avoid:** Call the archive helper only in the apply branch after plan validation and after `apply_merge_plan()` reports no failures. [VERIFIED: graphify/migration.py]  
**Warning signs:** Tests that call archive directly from preview without a plan ID, or CLI apply tests that do not assert stale plans leave legacy files untouched.

### Pitfall 2: Treating Archive Movement as Generic Merge Behavior

**What goes wrong:** `apply_merge_plan()` starts moving or deleting ORPHAN rows for all Obsidian exports, not only reviewed migrations. [VERIFIED: graphify/merge.py]  
**Why it happens:** ORPHAN appears in both merge and migration vocabularies, but Phase 36 archive semantics are migration-specific. [VERIFIED: graphify/merge.py] [VERIFIED: graphify/migration.py]  
**How to avoid:** Keep `filter_applicable_actions()` unchanged for writes and archive legacy review rows separately in `migration.py`. [VERIFIED: graphify/migration.py]

### Pitfall 3: Archive Path Traversal Through Loaded JSON

**What goes wrong:** A malicious or edited migration JSON row with `../` or an absolute path moves arbitrary files into the archive. [VERIFIED: graphify/migration.py]  
**Why it happens:** Loaded plan rows are JSON, and row paths must be treated as untrusted even after digest validation if code changes later expand the payload. [VERIFIED: graphify/migration.py]  
**How to avoid:** Revalidate each source with `validate_vault_path()` and each archive destination against the archive root before moving. [VERIFIED: graphify/profile.py]

### Pitfall 4: Overbroad `_COMMUNITY_*` Forbidden Tests

**What goes wrong:** Tests prevent docs from explaining legacy `_COMMUNITY_*` cleanup, even though that explanation is required. [VERIFIED: 36-CONTEXT.md]  
**Why it happens:** A naive forbidden test bans the token instead of stale generated-output claims. [VERIFIED: 36-CONTEXT.md]  
**How to avoid:** Require phrases that say v1.8 is MOC-only, and forbid stale phrases that say `_COMMUNITY_*` is generated output. [VERIFIED: 36-CONTEXT.md]

### Pitfall 5: Sanitizer Matrix Without Executable Assertions

**What goes wrong:** Verification says inputs are sanitized, but tests only document helper names without proving behavior. [VERIFIED: 36-CONTEXT.md]  
**Why it happens:** VER-03 asks for a matrix, which can become passive documentation. [VERIFIED: 36-CONTEXT.md]  
**How to avoid:** Make the matrix executable: each row includes an input sample, helper callable, expected safe output/error, and linked test name. [VERIFIED: tests/test_profile.py] [VERIFIED: tests/test_templates.py] [VERIFIED: tests/test_naming.py]

## Code Examples

### CLI Apply Gate

```python
# Source: graphify/__main__.py
if opts.apply and not opts.plan_id:
    print("error: --apply requires --plan-id from a preview artifact", file=sys.stderr)
    sys.exit(2)
```

### Existing Source Path Confinement

```python
# Source: graphify/profile.py
def validate_vault_path(candidate: str | Path, vault_dir: str | Path) -> Path:
    vault_base = Path(vault_dir).resolve()
    resolved = (vault_base / candidate).resolve()
    resolved.relative_to(vault_base)
    return resolved
```

### Existing Sanitized MOC Title Flow

```python
# Source: graphify/templates.py
community_name = _sanitize_generated_title(community_name)
community_tag = ctx.get("community_tag") or safe_tag(community_name)
filename = resolve_filename(community_name, convention) + ".md"
```

### Existing Skill Variant Test Pattern

```python
# Source: tests/test_skill_files.py
def _read(name: str) -> str:
    return (Path(graphify.__file__).parent / name).read_text(encoding="utf-8")
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Generated `_COMMUNITY_*` community overview notes | MOC-only community output under Graphify-owned v1.8 taxonomy | v1.8 Phases 32-35 | Docs/skills must stop describing `_COMMUNITY_*` as generated output. [VERIFIED: .planning/REQUIREMENTS.md] [VERIFIED: .planning/STATE.md] |
| Direct Obsidian export framing only | Existing-vault migration/update via `graphify update-vault --input ... --vault ...` | Phase 35 | Migration guide and skill text must distinguish lower-level export from reviewed update/apply. [VERIFIED: graphify/__main__.py] [VERIFIED: Phase 35 verification] |
| Legacy notes surfaced but left in place | Legacy notes archived by default during reviewed apply | Phase 36 locked decision | Planner must add archive helper/tests and rollback docs. [VERIFIED: 36-CONTEXT.md] |
| Security claims spread across individual tests | Explicit sanitizer coverage matrix | Phase 36 locked decision | Planner must make VER-03 traceable for verifier/security review. [VERIFIED: 36-CONTEXT.md] |

**Deprecated/outdated:**
- Claims that v1.8 Obsidian output generates `_COMMUNITY_*` overview notes are stale. [VERIFIED: .planning/REQUIREMENTS.md] [VERIFIED: 36-CONTEXT.md]
- README's current Obsidian adapter examples stop at `--obsidian --obsidian-dir` and do not describe `update-vault`; they need v1.8 migration guidance. [VERIFIED: README.md]

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | Recommended guide filename `MIGRATION_V1_8.md` is acceptable. [ASSUMED] | Recommended Project Structure / Plan 36-02 | Low; context leaves exact guide filename/location to planner discretion. |

## Open Questions (RESOLVED)

1. **Should archive move only unmatched legacy `ORPHAN` rows, or also matched legacy rows listed in `legacy_mappings`?**
   - What we know: Phase 35 appends unmatched legacy notes as `ORPHAN` rows and records matched old/new path pairs in `legacy_mappings`. [VERIFIED: graphify/migration.py]
   - What's unclear: Context says "legacy-note archiving by default" but does not explicitly distinguish matched legacy rows from unmatched legacy rows. [VERIFIED: 36-CONTEXT.md]
   - Recommendation: Archive every source legacy path represented by `legacy_mappings.old_path` plus legacy `ORPHAN` rows, deduped by path, after apply succeeds. This best matches "legacy notes" while preserving reviewability. [ASSUMED]
   - **RESOLVED:** Plans should archive both `legacy_mappings.old_path` sources and legacy `ORPHAN` review rows, deduped by resolved vault path, after reviewed apply succeeds.

2. **Should archive helper overwrite existing archive files?**
   - What we know: Archive paths must preserve relative path information under `graphify-out/migrations/archive/`. [VERIFIED: 36-CONTEXT.md]
   - What's unclear: Existing archive collision policy is not specified. [VERIFIED: 36-CONTEXT.md]
   - Recommendation: Include `plan_id` in the archive path so collisions are naturally avoided per reviewed plan; refuse overwrite inside a plan if duplicate paths appear. [ASSUMED]
   - **RESOLVED:** Plans should use plan-id archive subdirectories and refuse duplicate archive destinations within a single plan.

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|-------------|-----------|---------|----------|
| Python | Implementation and tests | yes | 3.10.19 | CI also covers 3.12. [VERIFIED: python3 --version] [VERIFIED: CLAUDE.md] |
| pytest | Unit/CLI regression tests | yes | 9.0.3 | None needed. [VERIFIED: pytest --version] |
| PyYAML | Profile-dependent tests | optional | not probed | Tests can continue using `pytest.importorskip("yaml")`. [VERIFIED: tests/test_main_flags.py] |

**Missing dependencies with no fallback:** None identified. [VERIFIED: pyproject.toml]  
**Missing dependencies with fallback:** PyYAML may be absent in minimal environments; existing tests skip profile-dependent paths when unavailable. [VERIFIED: tests/test_main_flags.py]

## Validation Architecture

Nyquist validation is enabled in `.planning/config.json`, so Phase 36 should produce validation evidence. [VERIFIED: .planning/config.json]

### Test Framework

| Property | Value |
|----------|-------|
| Framework | pytest 9.0.3 locally; pytest suite is project standard. [VERIFIED: pytest --version] [VERIFIED: CLAUDE.md] |
| Config file | none found during research; tests are direct pytest modules under `tests/`. [VERIFIED: CLAUDE.md] |
| Quick run command | `pytest tests/test_migration.py tests/test_main_flags.py tests/test_skill_files.py tests/test_profile.py tests/test_templates.py tests/test_naming.py -q` |
| Full suite command | `pytest tests/ -q` |

### Phase Requirements -> Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|--------------|
| MIG-05 | Migration guide covers backup, validation, dry-run, migration command, review, cleanup/archive, rollback, and rerun. | docs contract | `pytest tests/test_skill_files.py -q` or a new docs test | Partially; extend `tests/test_skill_files.py`. [VERIFIED: tests/test_skill_files.py] |
| VER-01 | Pure unit tests use `tmp_path` and no network calls. | unit/CLI subprocess | `pytest tests/test_migration.py tests/test_main_flags.py -q` | Yes; extend existing files. [VERIFIED: tests/test_migration.py] [VERIFIED: tests/test_main_flags.py] |
| VER-02 | Skill files and CLI docs share v1.8 wording. | contract | `pytest tests/test_skill_files.py tests/test_main_flags.py -q` | Yes; extend existing files. [VERIFIED: tests/test_skill_files.py] [VERIFIED: tests/test_main_flags.py] |
| VER-03 | New path/template/profile/LLM-label/repo-identity inputs pass through sanitizer helpers. | unit/security contract | `pytest tests/test_profile.py tests/test_templates.py tests/test_naming.py tests/test_migration.py -q` | Yes; add matrix rows to existing files or one new security matrix test. [VERIFIED: tests/test_profile.py] [VERIFIED: tests/test_templates.py] [VERIFIED: tests/test_naming.py] |

### Sampling Rate

- **Per task commit:** Run focused tests for touched surfaces: migration/CLI, skill/docs, or sanitizer files. [VERIFIED: CLAUDE.md]
- **Per wave merge:** Run the quick run command above. [VERIFIED: CLAUDE.md]
- **Phase gate:** Run `pytest tests/ -q` before `/gsd-verify-work`. [VERIFIED: CLAUDE.md]

### Wave 0 Gaps

- [ ] `tests/test_migration.py` - add archive helper-level tests for MIG-05/MIG-06-adjacent archive behavior and VER-01. [VERIFIED: tests/test_migration.py]
- [ ] `tests/test_main_flags.py` - add CLI apply archive evidence test for VER-01/VER-02. [VERIFIED: tests/test_main_flags.py]
- [ ] `tests/test_skill_files.py` - add required v1.8 phrase and forbidden stale `_COMMUNITY_*` generated-output claim tests for VER-02. [VERIFIED: tests/test_skill_files.py]
- [ ] `tests/test_v18_security_matrix.py` or equivalent rows in existing test files - add sanitizer matrix for VER-03. [VERIFIED: 36-CONTEXT.md]

## Security Domain

Security enforcement is enabled by default because `.planning/config.json` does not disable it. [VERIFIED: .planning/config.json]

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|------------------|
| V2 Authentication | no | No auth/session surface in this phase. [VERIFIED: graphify/migration.py] |
| V3 Session Management | no | No session/cookie surface in this phase. [VERIFIED: graphify/migration.py] |
| V4 Access Control | yes | Plan-ID validation and request matching gate apply/archive to reviewed artifacts only. [VERIFIED: graphify/migration.py] |
| V5 Input Validation | yes | `validate_vault_path`, archive-root confinement, `safe_filename`, `safe_tag`, `safe_frontmatter_value`, `_sanitize_wikilink_alias`, and `normalize_repo_identity`. [VERIFIED: graphify/profile.py] [VERIFIED: graphify/templates.py] [VERIFIED: graphify/naming.py] |
| V6 Cryptography | yes | SHA-256 plan IDs and digest recomputation detect tampered migration artifacts; no custom crypto beyond hashing is needed. [VERIFIED: graphify/migration.py] |

### Known Threat Patterns for Archive-By-Default and Docs/Skill Drift

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| Path traversal in loaded migration rows | Tampering / Elevation of privilege | Validate source paths with `validate_vault_path()` and destination paths against the archive root. [VERIFIED: graphify/profile.py] |
| Stale or tampered plan archive movement | Tampering | Keep `load_migration_plan()` digest check and `validate_plan_matches_request()` current-preview check before archive. [VERIFIED: graphify/migration.py] |
| User data loss via failed apply then archive | Denial of service | Archive only after `apply_merge_plan()` has no failures; preserve file contents and relative paths in archive. [VERIFIED: graphify/migration.py] |
| Confusing docs causing writes without backup | Repudiation / Information loss | Migration guide must make backup a hard prerequisite and place rollback immediately after apply/archive. [VERIFIED: 36-CONTEXT.md] |
| Skill drift causing stale `_COMMUNITY_*` expectations | Integrity | Required/forbidden phrase tests across packaged variants. [VERIFIED: tests/test_skill_files.py] [VERIFIED: pyproject.toml] |
| Template or label injection through docs examples | Tampering | Continue using existing template/frontmatter/wikilink sanitizers and prove coverage in matrix. [VERIFIED: graphify/templates.py] [VERIFIED: graphify/profile.py] |

### VER-03 Sanitizer Coverage Matrix Recommendation

| Input Class | Helper / Invariant | Existing Evidence | Phase 36 Test Requirement |
|-------------|--------------------|-------------------|---------------------------|
| Vault-relative note paths | `validate_vault_path()` | Used by legacy scan and row-to-action conversion. [VERIFIED: graphify/migration.py] | Add archive source traversal test. |
| Archive destination paths | New archive-root confinement helper | Not present yet. [VERIFIED: graphify/migration.py] | Add destination traversal/refuse-overwrite tests. |
| Profile output paths | `validate_sibling_path()` and `validate_profile()` | Output mode validation exists. [VERIFIED: graphify/profile.py] | Include in matrix row. |
| Filenames and CODE stems | `safe_filename()`, `build_code_filename_stems()` | Existing profile/naming tests cover invalid chars, length caps, collisions. [VERIFIED: tests/test_profile.py] [VERIFIED: tests/test_naming.py] | Include in matrix row. |
| Tags | `safe_tag()` | Existing profile tests cover slash/space/empty handling. [VERIFIED: tests/test_profile.py] | Include in matrix row. |
| Frontmatter values | `safe_frontmatter_value()`, `_dump_frontmatter()` | Existing profile tests cover YAML quoting and control stripping. [VERIFIED: tests/test_profile.py] | Include in matrix row. |
| Wikilink aliases | `_sanitize_wikilink_alias()` via `_emit_wikilink()` | Template code sanitizes `]]`, `|`, and controls. [VERIFIED: graphify/templates.py] | Include explicit row if not already asserted by existing tests. |
| Generated concept titles / LLM labels | `_sanitize_generated_title()`, `resolve_concept_names()` rejection | Tests reject unsafe LLM titles and sanitize generated MOC titles. [VERIFIED: tests/test_templates.py] [VERIFIED: tests/test_naming.py] | Include in matrix row. |
| Template block syntax | `_expand_blocks()` before `safe_substitute()` | Template code documents ordering invariant. [VERIFIED: graphify/templates.py] | Include row with `{{#connections}}` injection sample. |
| Repo identity | `normalize_repo_identity()` / `resolve_repo_identity()` | Existing naming tests cover precedence and CODE prefix. [VERIFIED: tests/test_naming.py] | Include row for path-segment rejection. |

## Sources

### Primary (HIGH confidence)

- `.planning/phases/36-migration-guide-skill-alignment-regression-sweep/36-CONTEXT.md` - locked decisions, constraints, canonical surfaces.
- `.planning/REQUIREMENTS.md` - MIG-05, VER-01, VER-02, VER-03 traceability.
- `.planning/ROADMAP.md` - Phase 36 goal and success criteria.
- `.planning/STATE.md` - v1.8 carry-forward decisions and Phase 35 decisions.
- `.planning/phases/35-templates-export-plumbing-dry-run-migration-visibility/35-VERIFICATION.md` - verified migration preview/apply behavior.
- `graphify/migration.py` - preview/apply, plan validation, legacy scan, applicable action filtering.
- `graphify/__main__.py` - `update-vault` CLI parser/help/apply gate.
- `graphify/merge.py` - merge action vocabulary and generic apply behavior.
- `graphify/profile.py` - profile validation and path/frontmatter/tag/filename safety helpers.
- `graphify/templates.py` - template, wikilink, generated-title, Dataview, CODE repo sinks.
- `graphify/naming.py` - repo identity and concept-name safety.
- `tests/test_migration.py`, `tests/test_main_flags.py`, `tests/test_skill_files.py`, `tests/test_profile.py`, `tests/test_templates.py`, `tests/test_naming.py` - existing validation homes.
- `README.md`, `pyproject.toml`, `CLAUDE.md`, `.planning/config.json` - docs, package data, project constraints, validation config.

### Secondary (MEDIUM confidence)

- Stale `.planning/graphs/graph.json` status: graph exists but is stale by 349 hours; graph queries for migration/sanitizer/skill returned no nodes, so graph context did not materially guide the plan. [VERIFIED: gsd graphify status/query]

### Tertiary (LOW confidence)

- None.

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH - verified from `CLAUDE.md`, `pyproject.toml`, and local `python3`/`pytest` versions.
- Architecture: HIGH - verified from current source modules and Phase 35 verification.
- Pitfalls: HIGH - derived from locked decisions and current code seams.
- Archive collision policy: MEDIUM - plan-id subdirectory recommendation is inferred from existing plan-id artifact structure and context discretion.

**Research date:** 2026-04-29  
**Valid until:** 2026-05-06 for implementation details, because Phase 36 is actively changing migration/docs behavior.
