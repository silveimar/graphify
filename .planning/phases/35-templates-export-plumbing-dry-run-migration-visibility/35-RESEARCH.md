# Phase 35: Templates, Export Plumbing & Dry-Run/Migration Visibility - Research

**Researched:** 2026-04-28  
**Domain:** Python CLI, Obsidian export merge safety, migration preview artifacts  
**Confidence:** HIGH

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
- **D-01:** Add a dedicated user-facing command shaped as `graphify update-vault --input work-vault/raw --vault ls-vault`.
- **D-02:** The workflow is not vault-to-vault. The source is the raw corpus under `work-vault/raw/`; the Obsidian vault target is `ls-vault`.
- **D-03:** `update-vault` must not imply a destructive full rebuild of `ls-vault`. It previews and applies graphify-managed note updates inside an existing vault.
- **D-04:** Preview is the default. Writes require an explicit apply path.
- **D-05:** The command runs the full graphify pipeline from `--input` by default so one command can go from raw corpus to vault preview/apply. Existing caches may make reruns cheap, but consuming prebuilt artifacts is not the default user flow.
- **D-06:** Legacy surfacing should combine the existing manifest with a bounded vault scan: read `vault-manifest.json` first, then scan `ls-vault` for legacy `_COMMUNITY_*` files and graphify-managed fingerprints.
- **D-07:** Identity matching should trust manifest node/community identity first, graphify-managed frontmatter second, and filename heuristics last.
- **D-08:** Unmatched legacy `_COMMUNITY_*` files are reported as ORPHAN review-only entries. They are never deleted or moved automatically.
- **D-09:** When an old legacy note matches a new Graphify-owned note identity, preserve the v1.8 path contract. Prefer showing the new path action plus a legacy mapping note while preserving the old file as an ORPHAN/review item unless the user cleans it manually.
- **D-10:** Preview output should include both a human-readable summary and structured machine-readable artifacts.
- **D-11:** Preview mode should write both Markdown and JSON migration plan artifacts in the artifacts directory so humans can review and agents/tests can consume the same plan.
- **D-12:** The human preview should balance readability with safety: grouped counts with representative rows are acceptable, but risky cases must be expanded.
- **D-13:** Always expand `SKIP_CONFLICT`, `SKIP_PRESERVE`, `ORPHAN`, and `REPLACE` rows in terminal output even if non-risky actions are summarized.
- **D-14:** Applying writes requires `--apply --plan-id <id>` where the plan id comes from the preview artifact. `--apply` alone is not enough.
- **D-15:** CODE notes should include the resolved repo identity in frontmatter as `repo: <identity>`.
- **D-16:** CODE notes should include a repo tag such as `repo/graphify` for Obsidian filtering.
- **D-17:** Manifests should record repo identity both per note entry and in run-level metadata so repo drift is easy to audit.
- **D-18:** If preview detects existing managed notes from a different repo identity, it should report `SKIP_CONFLICT` until the user explicitly resolves or overrides the drift.
- **D-19:** Dry-run and preview output should show resolved repo identity in a top banner and include it in CODE note rows.

### Claude's Discretion
- For `D-09`, planners may choose the exact wording and data shape for legacy mapping notes, as long as old files are not updated in place, v1.8 paths remain canonical, and legacy files remain review-only unless the user acts manually.
- For `D-12`, planners may choose the default number of representative rows per low-risk action group, as long as risky actions listed in `D-13` are always expanded and `--verbose` or equivalent can reveal all rows.

### Deferred Ideas (OUT OF SCOPE)
None - discussion stayed within Phase 35 scope.
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| COMM-02 | User sees legacy `_COMMUNITY_*` files surfaced as migration candidates or orphans instead of silently ignored. | Add a bounded scan plus manifest/frontmatter/filename matching cascade; unmatched `_COMMUNITY_*` becomes ORPHAN review-only. [VERIFIED: `35-CONTEXT.md`, `graphify/merge.py`] |
| REPO-04 | User sees resolved repo identity recorded consistently in CODE note filenames, frontmatter, tags, and output manifests. | CODE filename stems already use repo identity; Phase 35 must extend frontmatter/tag and manifest metadata. [VERIFIED: `graphify/naming.py`, `graphify/export.py`, `tests/test_export.py`] |
| MIG-01 | User can run an automated migration command for the real `work-vault` to `ls-vault` update path. | Add `update-vault` in `graphify/__main__.py` using `--input` raw corpus and `--vault` target vault. [VERIFIED: `35-CONTEXT.md`, `graphify/__main__.py`] |
| MIG-02 | User can preview migration effects in dry-run mode before any vault writes occur. | Existing `to_obsidian(dry_run=True)` returns `MergePlan` and tests assert dry-run writes no Markdown files. [VERIFIED: `graphify/export.py`, `tests/test_integration.py`] |
| MIG-03 | User sees old managed paths mapped to new Graphify-owned paths when note identity can be matched. | Existing manifests store `node_id`, `note_type`, and `community_id`; extend this identity data and legacy scan rows into migration artifacts. [VERIFIED: `graphify/merge.py`, `tests/test_merge.py`] |
| MIG-04 | User can review CREATE, UPDATE, SKIP_PRESERVE, SKIP_CONFLICT, REPLACE, and ORPHAN outcomes before committing to migration. | `MergeAction` already defines the exact action vocabulary and `format_merge_plan()` renders grouped output. [VERIFIED: `graphify/merge.py`, `tests/test_merge.py`] |
| MIG-06 | User never has legacy vault notes automatically deleted during migration. | Existing `apply_merge_plan()` skips ORPHAN and never deletes orphan paths; preserve this invariant for legacy `_COMMUNITY_*` surfacing. [VERIFIED: `graphify/merge.py`, `tests/test_merge.py`] |
</phase_requirements>

## Summary

Phase 35 should be planned as a thin orchestration and metadata extension over the existing Obsidian export stack, not a replacement renderer. The current code already has repo identity resolution, CODE filename stems, profile/template rendering, merge action vocabulary, user-modified detection, dry-run `MergePlan` output, atomic writes, and ORPHAN non-deletion behavior. [VERIFIED: `graphify/naming.py`, `graphify/export.py`, `graphify/merge.py`]

The missing work is the dedicated `graphify update-vault` command, preview artifact persistence, legacy scan/matching, repo identity propagation into CODE frontmatter/tags/manifests, repo drift conflict classification, and apply-by-plan-id validation. These are Phase 35 responsibilities; the human migration guide and broader skill/security sweep remain Phase 36 scope. [VERIFIED: `.planning/ROADMAP.md`, `35-CONTEXT.md`]

**Primary recommendation:** Build `update-vault` as a preview-first command that runs the existing pipeline from `--input`, renders through `to_obsidian(dry_run=True)`, enriches the `MergePlan` with migration metadata, writes `migration-plan-<id>.json` and `.md`, and only calls `apply_merge_plan()` when invoked with `--apply --plan-id <id>`. [VERIFIED: `35-CONTEXT.md`, `graphify/export.py`, `graphify/merge.py`]

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|--------------|----------------|-----------|
| Raw corpus graph rebuild | CLI / Pipeline | Filesystem | `run` already delegates corpus processing to `run_corpus`; `update-vault` should follow that entry-point pattern. [VERIFIED: `graphify/__main__.py`] |
| Vault profile/template rendering | Export / Templates | Profile | `to_obsidian()` owns profile-driven classify/render/merge orchestration; templates own frontmatter/body emission. [VERIFIED: `graphify/export.py`, `graphify/templates.py`] |
| Merge safety and apply writes | Merge engine | Filesystem | `compute_merge_plan()` is pure preview; `apply_merge_plan()` is the only vault write layer for generated notes. [VERIFIED: `graphify/merge.py`] |
| Migration plan persistence | CLI / Migration helper | Merge engine | Plan ID, JSON/Markdown artifacts, and apply gate are command workflow concerns layered over `MergePlan`. [VERIFIED: `35-CONTEXT.md`] |
| Legacy note discovery | Migration helper | Merge engine | Existing manifest supplies strong identity; bounded vault scan supplements missing legacy `_COMMUNITY_*` and graphify fingerprints. [VERIFIED: `35-CONTEXT.md`, `graphify/merge.py`] |
| Repo identity drift detection | Migration helper / Merge metadata | Naming | `resolve_repo_identity()` supplies current identity; migration must compare it against manifest/frontmatter identity and emit SKIP_CONFLICT. [VERIFIED: `graphify/naming.py`, `35-CONTEXT.md`] |

## Project Constraints (from .cursor/rules/)

- `.cursor/rules/graphify.mdc` contains only `alwaysApply: true` and no additional actionable implementation directives. [VERIFIED: `.cursor/rules/graphify.mdc`]
- Repository rules require Python 3.10+ compatibility, no new required dependencies, pure unit tests using `tmp_path`, no network calls in tests, and all external input through existing sanitization/path helpers. [VERIFIED: `CLAUDE.md`]
- No formatter or linter is configured; CI runs pytest on Python 3.10 and 3.12. [VERIFIED: `CLAUDE.md`]

## Standard Stack

### Core

| Library / Module | Version | Purpose | Why Standard |
|------------------|---------|---------|--------------|
| Python stdlib: `argparse`, `json`, `hashlib`, `datetime`, `pathlib`, `os.replace` | Python 3.10.19 installed | CLI parsing, plan IDs, plan artifacts, path handling, atomic writes | Existing CLI and manifest writers use stdlib; no new required dependencies. [VERIFIED: environment, `graphify/__main__.py`, `graphify/merge.py`] |
| `graphify.pipeline.run_corpus` | local module | Full graphify pipeline from raw input | `update-vault` must run the full pipeline from `--input` by default. [VERIFIED: `35-CONTEXT.md`, `graphify/__main__.py`] |
| `graphify.export.to_obsidian` | local module | Profile-driven Obsidian render plus merge-plan construction | Existing export path returns `MergePlan` on dry-run and `MergeResult` on apply. [VERIFIED: `graphify/export.py`] |
| `graphify.merge` | local module | Action vocabulary, pure preview, atomic apply, manifest I/O | Already defines CREATE, UPDATE, SKIP_PRESERVE, SKIP_CONFLICT, REPLACE, ORPHAN and non-deleting ORPHAN behavior. [VERIFIED: `graphify/merge.py`] |
| `graphify.naming` | local module | Repo identity normalization/resolution and CODE filename stems | Existing CODE paths are repo-prefixed and collision-safe. [VERIFIED: `graphify/naming.py`, `tests/test_naming.py`] |
| NetworkX | 3.4.2 installed | Graph object passed through export/classify/render | Current graphify pipeline already depends on NetworkX. [VERIFIED: environment, `pyproject.toml`] |

### Supporting

| Library / Module | Version | Purpose | When to Use |
|------------------|---------|---------|-------------|
| PyYAML | 6.0.3 installed, optional extra | Vault profile parsing | Required only when reading user `.graphify/profile.yaml`; do not add as a new required dependency. [VERIFIED: environment, `pyproject.toml`, `graphify/output.py`] |
| `graphify.detect._save_output_manifest` / `_load_output_manifest` | local module | Output-manifest run history | Extend or mirror for run-level repo identity metadata if planner chooses to use output manifest for migration audit. [VERIFIED: `graphify/detect.py`] |
| `graphify.profile.safe_filename`, `safe_tag`, `safe_frontmatter_value`, `validate_vault_path` | local module | Filename/tag/frontmatter/path safety | Use for every new repo tag, plan path, legacy-scan path, and frontmatter value. [VERIFIED: `graphify/profile.py`, `graphify/templates.py`, `graphify/merge.py`] |

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| `to_obsidian()` + `MergePlan` | A separate migration renderer | Reimplements profile/template/merge safety and risks drift from normal export behavior. Avoid. [VERIFIED: `graphify/export.py`, `graphify/merge.py`] |
| `apply_merge_plan()` | Direct file writes from `update-vault` | Bypasses atomic writes, user-preservation, path validation, and ORPHAN non-deletion. Avoid. [VERIFIED: `graphify/merge.py`] |
| JSON-only preview | Markdown-only preview | Locked decision requires both human-readable and machine-readable artifacts. [VERIFIED: `35-CONTEXT.md`] |

**Installation:** No new required package installation should be planned. Existing verification commands:

```bash
python3 --version
pytest --version
graphify --help
```

**Version verification:** `python3 --version` returned 3.10.19, `pytest --version` returned 9.0.3, `graphify --help` succeeded, `networkx` is installed at 3.4.2, and `PyYAML` is installed at 6.0.3. [VERIFIED: local environment probe]

## Architecture Patterns

### System Architecture Diagram

```text
graphify update-vault --input work-vault/raw --vault ls-vault
        |
        v
Resolve target vault + profile + repo identity
        |
        v
Run full graphify pipeline from raw corpus
detect -> extract -> build_graph -> cluster -> analyze/report/export artifacts
        |
        v
Render Obsidian notes through to_obsidian(dry_run=True)
        |
        v
Compute MergePlan + load vault-manifest.json
        |
        v
Bounded legacy scan (_COMMUNITY_* + graphify fingerprints)
        |
        v
Enrich migration rows: repo identity, legacy mapping, risky outcomes
        |
        +--> Preview default: print banner + write migration-plan-<id>.json/.md
        |
        +--> Apply gate: --apply --plan-id <id> loads artifact, validates target/identity, apply_merge_plan()
```

### Recommended Project Structure

```text
graphify/
├── __main__.py          # Add update-vault command parsing and help text.
├── migration.py         # New focused orchestration helpers for plan IDs, legacy scan, artifact I/O, apply validation.
├── export.py            # Minimal extension points for repo metadata/rendered note metadata, not a parallel renderer.
├── merge.py             # Extend dataclasses/formatting only where action metadata belongs.
├── templates.py         # Add CODE repo frontmatter/tag emission through existing sanitized frontmatter builder.
└── detect.py            # Reuse output-manifest patterns if run-level migration metadata needs shared writer behavior.

tests/
├── test_migration.py    # New unit tests for legacy scan, plan artifacts, apply gate, repo drift.
├── test_main_flags.py   # CLI subprocess tests for update-vault parsing/default preview/apply errors.
├── test_export.py       # Repo identity frontmatter/tag/manifest assertions.
└── test_merge.py        # Any MergeAction metadata/formatting extensions.
```

### Pattern 1: Preview-First Command

**What:** Default `update-vault` execution should build or refresh graph artifacts, compute a migration plan, write preview artifacts, and perform zero vault note writes. [VERIFIED: `35-CONTEXT.md`, `tests/test_integration.py`]  
**When to use:** Always, unless `--apply --plan-id <id>` is present. [VERIFIED: `35-CONTEXT.md`]  
**Example:**

```python
# Source: graphify/export.py and graphify/merge.py
plan = to_obsidian(G, communities, str(vault_dir), profile=profile, dry_run=True)
preview = build_migration_preview(plan, repo_identity=resolved.identity)
write_migration_artifacts(artifacts_dir, preview)
```

### Pattern 2: Plan-ID Apply Gate

**What:** Applying must load the JSON preview artifact by plan ID, validate that it matches the requested vault/input/repo identity, then apply only approved CREATE/UPDATE/REPLACE actions through `apply_merge_plan()`. [VERIFIED: `35-CONTEXT.md`, `graphify/merge.py`]  
**When to use:** `graphify update-vault --input work-vault/raw --vault ls-vault --apply --plan-id <id>`. [VERIFIED: `35-CONTEXT.md`]  
**Example:**

```python
# Source: Phase 35 context + merge.py apply contract
if apply and not plan_id:
    raise SystemExit("error: --apply requires --plan-id from a preview artifact")
artifact = load_migration_plan(artifacts_dir, plan_id)
validate_plan_matches_request(artifact, input_dir, vault_dir, repo_identity)
result = apply_merge_plan(artifact.plan, vault_dir, rendered_notes, profile, manifest_path=manifest_path, old_manifest=manifest)
```

### Pattern 3: Legacy Matching Cascade

**What:** Match old files to new note identities by manifest identity first, graphify-managed frontmatter second, filename heuristics last. [VERIFIED: `35-CONTEXT.md`, `graphify/merge.py`]  
**When to use:** During preview artifact enrichment before terminal output. [VERIFIED: `35-CONTEXT.md`]  
**Example identity fields:** `node_id`, synthetic `_moc_<cid>`, `community_id`, `note_type`, `target_path`, repo identity. [VERIFIED: `graphify/export.py`, `graphify/merge.py`]

### Anti-Patterns to Avoid

- **Vault-to-vault migration:** The locked workflow is raw corpus to target vault, not Obsidian source vault to Obsidian target vault. [VERIFIED: `35-CONTEXT.md`]
- **Deleting or moving legacy notes automatically:** Legacy `_COMMUNITY_*` files are review-only and ORPHAN rows are never deleted by apply. [VERIFIED: `35-CONTEXT.md`, `graphify/merge.py`]
- **Direct file writes from CLI:** Use `apply_merge_plan()` for vault writes and atomic artifact writers for preview files. [VERIFIED: `graphify/merge.py`, `graphify/detect.py`]
- **Treating repo drift as normal update:** Existing managed notes with a different repo identity must become SKIP_CONFLICT until explicit resolution/override. [VERIFIED: `35-CONTEXT.md`]
- **Silent risky-row summarization:** SKIP_CONFLICT, SKIP_PRESERVE, ORPHAN, and REPLACE must always be expanded in terminal output. [VERIFIED: `35-CONTEXT.md`]

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Vault note merge logic | Custom diff/patch writer | `compute_merge_plan()` and `apply_merge_plan()` | Already handles frontmatter policies, sentinel blocks, manifest user-modified detection, atomic writes, and ORPHAN safety. [VERIFIED: `graphify/merge.py`] |
| Repo identity normalization | New slug function | `normalize_repo_identity()` / `resolve_repo_identity()` | Existing helper enforces path-safe repo identity and CLI > profile > git > directory precedence. [VERIFIED: `graphify/naming.py`] |
| CODE filename generation | New filename scheme | `build_code_filename_stems()` | Existing helper prefixes repo identity and handles deterministic collisions. [VERIFIED: `graphify/naming.py`] |
| Template/frontmatter serialization | Ad hoc string concatenation | `render_note()`, `_build_frontmatter_fields()`, `_dump_frontmatter()` | Existing template layer centralizes sanitization and field ordering. [VERIFIED: `graphify/templates.py`, `graphify/profile.py`] |
| Path confinement | String prefix checks for vault writes | `validate_vault_path()` and merge `_validate_target()` | Existing validators resolve paths against vault directory. [VERIFIED: `graphify/profile.py`, `graphify/merge.py`] |
| Preview formatting from scratch | Separate action vocabulary | Extend or wrap `format_merge_plan()` | Existing formatter is tested for the six action groups and deterministic ordering. [VERIFIED: `graphify/merge.py`, `tests/test_merge.py`] |

**Key insight:** The hard part is not rendering Markdown; it is preserving user-owned vault state while making migration intent auditable. The existing merge engine owns that invariant and should remain the single write path. [VERIFIED: `graphify/merge.py`, `tests/test_merge.py`]

## Runtime State Inventory

| Category | Items Found | Action Required |
|----------|-------------|-----------------|
| Stored data | `graphify-out/vault-manifest.json` entries store content hashes, target paths, node IDs, note types, community IDs, and user-block flags. [VERIFIED: `graphify/merge.py`, `tests/test_merge.py`] | Extend manifest schema to include repo identity at run and per-note level; preserve backward compatibility for existing entries without repo fields. |
| Live service config | None. Phase 35 targets local filesystem Obsidian vault notes and local graphify artifacts only. [VERIFIED: `35-CONTEXT.md`] | No external service migration task. |
| OS-registered state | None. No launchd/systemd/Task Scheduler state participates in `update-vault`. [VERIFIED: codebase search and phase scope] | No action. |
| Secrets/env vars | None required for core update path. LLM naming may use existing optional environment setup, but Phase 35 must not introduce new secret keys. [VERIFIED: `CLAUDE.md`, `graphify/naming.py`] | No new env vars. |
| Build artifacts | `graphify-out/`, `concept-names.json`, `repo-identity.json`, `output-manifest.json`, and `vault-manifest.json` are local sidecars. [VERIFIED: `graphify/export.py`, `graphify/detect.py`, `graphify/merge.py`] | Migration plan artifacts should live in the artifacts directory, be atomic, and not be ingested as corpus. |

## Common Pitfalls

### Pitfall 1: Preview Writes Too Much
**What goes wrong:** Dry-run creates vault notes, mutates `vault-manifest.json`, or updates concept/repo sidecars unexpectedly. [VERIFIED: `tests/test_integration.py`, `graphify/export.py`]  
**Why it happens:** The existing non-dry-run path writes sidecars and applies notes; migration preview adds new artifacts, so write boundaries can blur. [VERIFIED: `graphify/export.py`]  
**How to avoid:** In preview, only write `migration-plan-<id>.json` and `.md` to artifacts; keep vault notes and vault manifest unchanged. [VERIFIED: `35-CONTEXT.md`]  
**Warning signs:** Tests find new `.md` files in `ls-vault` after preview or changed `vault-manifest.json`.

### Pitfall 2: Legacy Scan Escapes the Vault
**What goes wrong:** A scan follows symlinks or unbounded recursion into unrelated directories. [VERIFIED: `graphify/detect.py`, `graphify/merge.py`]  
**Why it happens:** Legacy discovery is filesystem work and easy to implement with broad `rglob()`. [VERIFIED: phase scope]  
**How to avoid:** Bound the scan to the target vault, ignore hidden/noise dirs where appropriate, and validate every candidate path through existing vault path confinement before reporting. [VERIFIED: `graphify/profile.py`, `graphify/merge.py`]  
**Warning signs:** Migration artifacts include paths outside the target vault.

### Pitfall 3: Repo Drift Hidden by Filename Match
**What goes wrong:** A note from another repo matches by filename and is updated as if it belongs to the current repo. [VERIFIED: `35-CONTEXT.md`]  
**Why it happens:** Filename heuristics are the weakest matching tier. [VERIFIED: `35-CONTEXT.md`]  
**How to avoid:** Compare manifest/frontmatter repo identity before allowing UPDATE/REPLACE; emit SKIP_CONFLICT on mismatch. [VERIFIED: `35-CONTEXT.md`, `graphify/naming.py`]  
**Warning signs:** Existing `repo` metadata differs from resolved repo banner but the action is UPDATE.

### Pitfall 4: ORPHAN Semantics Become Cleanup Semantics
**What goes wrong:** ORPHAN rows are treated as delete/move operations on apply. [VERIFIED: `35-CONTEXT.md`, `graphify/merge.py`]  
**Why it happens:** Migration workflows often conflate "old file detected" with "cleanup old file." [VERIFIED: `35-CONTEXT.md`]  
**How to avoid:** Keep ORPHAN review-only and never pass it to a deletion path; tests should assert legacy files still exist after apply. [VERIFIED: `graphify/merge.py`, `tests/test_merge.py`]  
**Warning signs:** `apply` changes, deletes, or renames `_COMMUNITY_*` files.

### Pitfall 5: Manifest Schema Extension Breaks Old Runs
**What goes wrong:** Existing `vault-manifest.json` entries without repo fields become unreadable or lose user-modified detection. [VERIFIED: `tests/test_merge.py`]  
**Why it happens:** Phase 8 manifest tests assume older entry shapes are tolerated. [VERIFIED: `tests/test_merge.py`]  
**How to avoid:** Treat missing repo identity as unknown; only mark SKIP_CONFLICT when a concrete existing repo differs from the current identity. [VERIFIED: `35-CONTEXT.md`, `tests/test_merge.py`]  
**Warning signs:** Existing manifest tests fail or old manifests are rewritten during preview.

## Code Examples

Verified patterns from local sources:

### Dry-Run Through Existing Export

```python
# Source: graphify/export.py
plan = to_obsidian(
    G,
    communities,
    output_dir=str(vault_notes_dir),
    profile=profile,
    repo_identity=cli_repo_identity,
    dry_run=True,
)
```

### Apply Through Existing Merge Engine

```python
# Source: graphify/merge.py
result = apply_merge_plan(
    plan,
    vault_dir,
    rendered_notes,
    profile,
    manifest_path=manifest_path,
    old_manifest=manifest,
)
```

### CODE Repo Metadata Extension Point

```python
# Source: graphify/templates.py and Phase 35 locked decisions
if note_type == "code":
    frontmatter_fields["repo"] = repo_identity
    tag_list.append(f"repo/{safe_tag(repo_identity)}")
```

### Migration Artifact Shape

```python
# Source: Phase 35 locked decisions + MergePlan dataclass
{
    "plan_id": plan_id,
    "input": str(input_dir.resolve()),
    "vault": str(vault_dir.resolve()),
    "repo_identity": repo_identity,
    "summary": plan.summary,
    "actions": [dataclasses.asdict(action) for action in plan.actions],
    "legacy_mappings": legacy_mappings,
}
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Flat/default Obsidian dump | Profile-driven Atlas/Sources/Graphify taxonomy | v1.0-v1.8 progression [VERIFIED: `.planning/ROADMAP.md`] | Phase 35 must preserve v1.8 canonical paths. |
| `_COMMUNITY_*` community overview output | MOC-only community output | Phase 34 [VERIFIED: `.planning/STATE.md`, `.planning/ROADMAP.md`] | Legacy `_COMMUNITY_*` files are migration evidence, not new output. |
| Generic god-node notes | Repo-prefixed CODE notes | Phase 34 [VERIFIED: `.planning/STATE.md`, `graphify/naming.py`] | Repo identity must be consistent across filenames/frontmatter/tags/manifests. |
| Direct `--obsidian --dry-run` console preview only | `update-vault` preview artifacts plus apply-by-plan-id | Phase 35 target [VERIFIED: `35-CONTEXT.md`] | Plans need artifact persistence and stale-plan validation. |

**Deprecated/outdated:**
- `_COMMUNITY_*` generation: hard-deprecated as default output; Phase 35 should surface legacy files only. [VERIFIED: `.planning/REQUIREMENTS.md`, `.planning/STATE.md`]
- `--apply` without a plan ID: explicitly insufficient for writes. [VERIFIED: `35-CONTEXT.md`]

## Assumptions Log

All claims in this research were verified against local code, local planning artifacts, or local environment probes. No `[ASSUMED]` claims are required.

## Open Questions (RESOLVED)

1. **RESOLVED: Repo drift override is not implemented in Phase 35.**
   - Resolution: repo drift remains a blocking `SKIP_CONFLICT` classification until the user resolves the conflicting note/manifest state manually or in a later explicitly planned override feature. Phase 35 must not add `--allow-repo-drift` or any equivalent bypass flag. [VERIFIED: `35-CONTEXT.md` D-18]
   - Planning impact: preview and apply must both enforce repo drift classification. Apply may only write validated CREATE, UPDATE, and REPLACE actions from the reviewed classified plan; `SKIP_CONFLICT` rows stay non-writable.

2. **RESOLVED: Migration artifacts are stored under `<artifacts_dir>/migrations/` and retained indefinitely in Phase 35.**
   - Resolution: preview writes `migration-plan-<plan_id>.json` and `migration-plan-<plan_id>.md` under the artifacts directory's `migrations/` subdirectory. Phase 35 performs no automatic pruning, deletion, or retention rotation. [VERIFIED: `35-CONTEXT.md` D-10, D-11, D-14]
   - Planning impact: apply loads exactly `migration-plan-<plan_id>.json` from that directory after validating the plan id as a content digest.

3. **RESOLVED: No prebuilt-graph shortcut is in Phase 35 scope.**
   - Resolution: `update-vault` runs the full graphify pipeline from `--input` by default and Phase 35 does not add a `--graph`, `--from-graph`, or equivalent shortcut. [VERIFIED: `35-CONTEXT.md` D-05]
   - Planning impact: tests and CLI wiring should cover the raw-corpus-to-vault workflow only.

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|-------------|-----------|---------|----------|
| Python | CLI and tests | yes | 3.10.19 | CI also covers Python 3.12. [VERIFIED: local environment, `CLAUDE.md`] |
| pytest | Validation | yes | 9.0.3 | none needed. [VERIFIED: local environment] |
| graphify CLI | Smoke/help checks | yes | command available | `python -m graphify` subprocess pattern exists in tests. [VERIFIED: local environment, `tests/test_main_flags.py`] |
| NetworkX | Graph pipeline/export | yes | 3.4.2 | required dependency in `pyproject.toml`. [VERIFIED: local environment, `pyproject.toml`] |
| PyYAML | Vault profile parsing | yes | 6.0.3 | built-in default profile when no profile is loaded; profile YAML needs optional extra. [VERIFIED: local environment, `pyproject.toml`, `graphify/output.py`] |

**Missing dependencies with no fallback:** None found for Phase 35 planning. [VERIFIED: local environment probe]

**Missing dependencies with fallback:** None found. [VERIFIED: local environment probe]

## Validation Architecture

### Test Framework

| Property | Value |
|----------|-------|
| Framework | pytest 9.0.3 [VERIFIED: local environment] |
| Config file | none detected; repository convention is direct pytest commands. [VERIFIED: `CLAUDE.md`] |
| Quick run command | `pytest tests/test_migration.py tests/test_export.py tests/test_merge.py tests/test_main_flags.py -q` |
| Full suite command | `pytest tests/ -q` |

### Phase Requirements -> Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|--------------|
| COMM-02 | Legacy `_COMMUNITY_*` files are surfaced as matched candidates or ORPHAN rows and not silently ignored. | unit | `pytest tests/test_migration.py::test_legacy_community_files_surface_as_orphans -q` | no - Wave 0 |
| REPO-04 | CODE notes contain `repo: <identity>`, `repo/<identity>` tag, repo-prefixed filename, and manifest repo identity. | unit/integration | `pytest tests/test_export.py::test_code_notes_record_repo_identity_in_frontmatter_tags_and_manifest -q` | no - Wave 0 |
| MIG-01 | `graphify update-vault --input work-vault/raw --vault ls-vault` runs the raw-corpus-to-vault preview path. | CLI integration | `pytest tests/test_main_flags.py::test_update_vault_preview_default_runs_pipeline -q` | no - Wave 0 |
| MIG-02 | Preview default writes migration plan artifacts but no vault Markdown notes. | CLI/unit | `pytest tests/test_migration.py::test_preview_writes_artifacts_but_no_vault_notes -q` | no - Wave 0 |
| MIG-03 | Matched legacy managed paths are mapped to new Graphify-owned paths in JSON and Markdown artifacts. | unit | `pytest tests/test_migration.py::test_legacy_manifest_identity_maps_old_path_to_new_path -q` | no - Wave 0 |
| MIG-04 | Terminal preview shows all six action classes and expands risky classes. | unit/CLI | `pytest tests/test_migration.py::test_preview_expands_risky_action_rows -q` | no - Wave 0 |
| MIG-06 | Applying a plan never deletes or moves legacy `_COMMUNITY_*` notes or ORPHAN rows. | unit | `pytest tests/test_migration.py::test_apply_never_deletes_legacy_orphan_files -q` | no - Wave 0 |

### Sampling Rate

- **Per task commit:** Run the narrow test created or changed by the task, usually one of `tests/test_migration.py`, `tests/test_export.py`, `tests/test_merge.py`, or `tests/test_main_flags.py`. [VERIFIED: repository test conventions]
- **Per wave merge:** `pytest tests/test_migration.py tests/test_export.py tests/test_merge.py tests/test_main_flags.py -q`
- **Phase gate:** `pytest tests/ -q` before `/gsd-verify-work`; note that `REQUIREMENTS.md` records two baseline detect failures as separate `/gsd-debug` scope. [VERIFIED: `.planning/REQUIREMENTS.md`, `CLAUDE.md`]

### Wave 0 Gaps

- [ ] `tests/test_migration.py` - covers COMM-02, MIG-02, MIG-03, MIG-04, MIG-06.
- [ ] `tests/test_main_flags.py` additions - covers MIG-01 CLI parsing and apply gate.
- [ ] `tests/test_export.py` additions - covers REPO-04 frontmatter/tag/manifest propagation.
- [ ] `tests/test_merge.py` additions - covers any MergeAction metadata, repo drift conflict kind, or formatter changes.

## Security Domain

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|------------------|
| V2 Authentication | no | No auth/session surface in local CLI migration. [VERIFIED: phase scope] |
| V3 Session Management | no | No session state. [VERIFIED: phase scope] |
| V4 Access Control | yes | Local filesystem authority only; enforce target vault path confinement and explicit `--apply --plan-id`. [VERIFIED: `35-CONTEXT.md`, `graphify/merge.py`] |
| V5 Input Validation | yes | Use `safe_filename`, `safe_tag`, `safe_frontmatter_value`, `validate_vault_path`, and merge `_validate_target`. [VERIFIED: `graphify/profile.py`, `graphify/templates.py`, `graphify/merge.py`] |
| V6 Cryptography | yes | Use SHA-256 for plan IDs/content hashes; do not hand-roll cryptographic primitives. [VERIFIED: `graphify/merge.py`, `graphify/naming.py`] |

### Known Threat Patterns for Phase 35

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| Path traversal via `--input`, `--vault`, legacy paths, or plan ID | Tampering | Resolve paths, validate vault-relative writes, and reject plan IDs that imply paths. [VERIFIED: `graphify/merge.py`, `graphify/profile.py`] |
| Stale or mismatched plan artifact applied to another vault | Tampering | Store and validate input path, vault path, repo identity, plan ID, and created timestamp before apply. [VERIFIED: `35-CONTEXT.md`] |
| Repo identity injection into frontmatter/tags | Tampering | Normalize with `normalize_repo_identity()`, emit tag with `safe_tag()`, emit frontmatter with existing dumper. [VERIFIED: `graphify/naming.py`, `graphify/templates.py`, `graphify/profile.py`] |
| Silent overwrite of user-modified notes | Tampering | Preserve manifest hash detection and SKIP_PRESERVE behavior. [VERIFIED: `graphify/merge.py`, `tests/test_merge.py`] |
| Legacy cleanup data loss | Tampering / Repudiation | Report ORPHAN only; never delete or move legacy notes automatically. [VERIFIED: `35-CONTEXT.md`, `graphify/merge.py`] |

## Sources

### Primary (HIGH confidence)
- `.planning/phases/35-templates-export-plumbing-dry-run-migration-visibility/35-CONTEXT.md` - locked decisions and scope.
- `.planning/REQUIREMENTS.md` - Phase 35 requirements and out-of-scope constraints.
- `.planning/ROADMAP.md` - Phase 35 success criteria and Phase 36 boundary.
- `.planning/STATE.md` - carry-forward v1.8 decisions and prior phase contracts.
- `CLAUDE.md` - project commands, architecture, tests, and security constraints.
- `graphify/__main__.py` - CLI patterns for `run`, `--obsidian`, repo identity flags, and help text.
- `graphify/export.py` - `to_obsidian()`, dry-run, repo identity sidecar, CODE filename injection, merge plan call.
- `graphify/merge.py` - action vocabulary, manifest I/O, pure preview, atomic apply, formatter, ORPHAN safety.
- `graphify/templates.py` - CODE template rendering, frontmatter fields, tags, wikilink safety.
- `graphify/naming.py` - repo identity normalization/resolution and CODE filename stems.
- `graphify/detect.py` - output-manifest patterns and self-ingestion guards.
- `tests/test_export.py`, `tests/test_merge.py`, `tests/test_main_flags.py`, `tests/test_integration.py`, `tests/test_templates.py` - current validation patterns.

### Secondary (MEDIUM confidence)
- Local environment probes for Python, pytest, graphify CLI, NetworkX, and PyYAML versions.
- Stale planning graph status: graph exists, last built 2026-04-14, stale by 347 hours, and Phase 35 queries returned no useful results. Treat graph-derived context as approximate. [VERIFIED: `gsd-tools graphify status/query`]

### Tertiary (LOW confidence)
- None.

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH - Phase 35 is internal codebase work and uses existing modules plus verified local dependencies.
- Architecture: HIGH - Existing CLI/export/merge/template boundaries are clear and tested.
- Pitfalls: HIGH - Pitfalls are derived from locked decisions and existing safety tests.

**Research date:** 2026-04-28  
**Valid until:** 2026-05-28 for internal code patterns; re-check if Phase 34 implementation changes before planning.
