# Phase 36: Migration Guide, Skill Alignment & Regression Sweep - Pattern Map

**Mapped:** 2026-04-29  
**Files analyzed:** 19  
**Analogs found:** 18 / 19

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|-------------------|------|-----------|----------------|---------------|
| `graphify/migration.py` | service | file-I/O, request-response | `graphify/migration.py` | exact |
| `graphify/__main__.py` | CLI route | request-response | `graphify/__main__.py` | exact |
| `README.md` | documentation | request-response guidance | `README.md` | exact |
| `MIGRATION_V1_8.md` | documentation | migration workflow | `README.md` Obsidian section | role-match |
| `graphify/skill.md` | skill docs | request-response guidance | `tests/test_skill_files.py` + packaged variants | role-match |
| `graphify/skill-codex.md` | skill docs | request-response guidance | `graphify/skill.md` + `tests/test_skill_files.py` | role-match |
| `graphify/skill-opencode.md` | skill docs | request-response guidance | `graphify/skill.md` + `tests/test_skill_files.py` | role-match |
| `graphify/skill-aider.md` | skill docs | request-response guidance | `graphify/skill.md` + `tests/test_skill_files.py` | role-match |
| `graphify/skill-copilot.md` | skill docs | request-response guidance | `graphify/skill.md` + `tests/test_skill_files.py` | role-match |
| `graphify/skill-claw.md` | skill docs | request-response guidance | `graphify/skill.md` + `tests/test_skill_files.py` | role-match |
| `graphify/skill-droid.md` | skill docs | request-response guidance | `graphify/skill.md` + `tests/test_skill_files.py` | role-match |
| `graphify/skill-trae.md` | skill docs | request-response guidance | `graphify/skill.md` + `tests/test_skill_files.py` | role-match |
| `graphify/skill-windows.md` | skill docs | request-response guidance | `graphify/skill.md` + `tests/test_skill_files.py` | role-match |
| `tests/test_migration.py` | test | file-I/O, request-response | `tests/test_migration.py` | exact |
| `tests/test_main_flags.py` | test | CLI subprocess | `tests/test_main_flags.py` | exact |
| `tests/test_skill_files.py` | test | docs contract | `tests/test_skill_files.py` | exact |
| `tests/test_profile.py` | test | transform, validation | `tests/test_profile.py` | exact |
| `tests/test_templates.py` | test | transform, validation | `tests/test_templates.py` | exact |
| `tests/test_naming.py` | test | transform, validation | `tests/test_naming.py` | exact |
| `tests/test_v18_security_matrix.py` | test | transform, validation | `tests/test_profile.py` / `tests/test_templates.py` / `tests/test_naming.py` | role-match |

## Pattern Assignments

### `graphify/migration.py` (service, file-I/O + request-response)

**Analog:** `graphify/migration.py`

**Imports pattern** (lines 4-13):
```python
import dataclasses
import datetime
import hashlib
import json
import os
import re
from pathlib import Path

from graphify.merge import MergeAction, MergePlan, apply_merge_plan, split_rendered_note
from graphify.profile import validate_vault_path
```

**Preview/apply orchestration pattern** (lines 160-254):
```python
def run_update_vault(
    *,
    input_dir: Path,
    vault_dir: Path,
    repo_identity: str | None = None,
    apply: bool = False,
    plan_id: str | None = None,
    use_router: bool = False,
    verbose: bool = False,
) -> dict:
    """Run the preview-first raw-corpus to Obsidian vault update workflow."""
    raw = Path(input_dir).resolve()
    vault = Path(vault_dir).resolve()
    if not raw.exists():
        raise ValueError(f"input path not found: {raw}")
    if not (vault / ".obsidian").is_dir():
        raise ValueError(f"target vault must contain .obsidian: {vault}")
    if apply and not plan_id:
        raise ValueError("--apply requires --plan-id from a preview artifact")
    ...
    if apply:
        loaded = load_migration_plan(resolved.artifacts_dir, str(plan_id))
        try:
            validate_plan_matches_request(
                loaded,
                raw,
                vault,
                resolved_repo.identity,
                current_preview=preview,
            )
        except ValueError as exc:
            raise ValueError(f"stale or mismatched migration plan: {exc}") from exc
        applicable_plan = _merge_plan_from_preview(loaded, resolved.notes_dir)
        result = apply_merge_plan(...)
```

**Path validation pattern** (lines 392-403):
```python
def _row_to_action(row: dict, vault: Path) -> MergeAction:
    return MergeAction(
        path=validate_vault_path(str(row.get("path", "")), Path(vault).resolve()),
        action=row["action"],
        reason=str(row.get("reason") or "validated migration plan action"),
        changed_fields=list(row.get("changed_fields") or []),
        changed_blocks=list(row.get("changed_blocks") or []),
        conflict_kind=row.get("conflict_kind"),
        user_modified=bool(row.get("user_modified")),
        has_user_blocks=bool(row.get("has_user_blocks")),
        source=str(row.get("source") or "graphify"),
    )
```

**Digest and plan-ID validation pattern** (lines 333-383):
```python
def load_migration_plan(artifacts_dir: Path, plan_id: str) -> dict:
    """Load and verify a migration plan artifact by digest id."""
    _validate_plan_id(plan_id)
    path = (
        Path(artifacts_dir).resolve()
        / MIGRATION_ARTIFACT_DIR
        / f"migration-plan-{plan_id}.json"
    )
    ...
    recomputed = compute_migration_plan_id(loaded)
    if stored_plan_id != plan_id or recomputed != plan_id:
        raise ValueError("invalid migration plan")
    return loaded

def filter_applicable_actions(preview: dict) -> list[dict]:
    """Return only action rows that an apply step may write."""
    return [
        dict(row) for row in preview.get("actions", [])
        if row.get("action") in {"CREATE", "UPDATE", "REPLACE"}
    ]
```

**Apply-result failure gate analog** (from `graphify/merge.py`, lines 1275-1384):
```python
def apply_merge_plan(
    plan: MergePlan,
    vault_dir: Path,
    rendered_notes: dict[str, RenderedNote],
    profile: dict,
    *,
    manifest_path: Path | None = None,
    old_manifest: dict[str, dict] | None = None,
) -> MergeResult:
    """Consume a MergePlan and apply writes to disk.

    Writes ONLY CREATE, UPDATE, REPLACE actions. Skips SKIP_PRESERVE,
    SKIP_CONFLICT, and ORPHAN (D-72: orphans reported, never deleted).
    ...
    """
    ...
    for action in plan.actions:
        if action.action in ("SKIP_PRESERVE", "SKIP_CONFLICT", "ORPHAN"):
            continue
        ...
        try:
            _write_atomic(target, new_text)
            succeeded.append(target)
        except OSError as exc:
            failed.append((target, f"write failed: {exc}"))
```

**Planner guidance:** Add archive helpers in `migration.py`, not `merge.py`. Use loaded preview rows as the reviewed source of truth, call archive only after `validate_plan_matches_request()` and after `apply_merge_plan()` has no failures, and revalidate source paths with `validate_vault_path()`. Add a new archive-root confinement helper because archive destinations live outside the vault.

---

### `graphify/__main__.py` (CLI route, request-response)

**Analog:** `graphify/__main__.py`

**Top-level help pattern** (lines 1241-1248):
```python
print("  doctor                  diagnose vault/profile/output configuration (VAULT-14/15)")
print("    --dry-run               preview which files would be ingested/skipped, no writes")
print("  update-vault --input work-vault/raw --vault ls-vault")
print("                            preview/apply raw corpus updates into an Obsidian vault")
print("    --repo-identity <slug>  override profile/fallback repo identity")
print("    --router                use heterogeneous extraction router")
print("    --verbose               print all migration rows")
print("    --apply --plan-id <id>  apply a reviewed migration plan artifact")
```

**Subcommand parser and error handling pattern** (lines 2423-2462):
```python
elif cmd == "update-vault":
    # graphify update-vault --input work-vault/raw --vault ls-vault
    import argparse as _ap

    _p_uv = _ap.ArgumentParser(
        prog="graphify update-vault",
        description=(
            "Preview or apply graphify updates with: "
            "graphify update-vault --input work-vault/raw --vault ls-vault"
        ),
        epilog="Example: graphify update-vault --input work-vault/raw --vault ls-vault",
        formatter_class=_ap.RawDescriptionHelpFormatter,
    )
    ...
    if opts.apply and not opts.plan_id:
        print("error: --apply requires --plan-id from a preview artifact", file=sys.stderr)
        sys.exit(2)
    from graphify.migration import format_migration_preview, run_update_vault
    try:
        result = run_update_vault(...)
    except ValueError as exc:
        print(f"error: {exc}", file=sys.stderr)
        sys.exit(1)
    print(format_migration_preview(result["preview"], verbose=opts.verbose))
```

**Planner guidance:** Keep parser-local imports and user-facing errors consistent. If archive evidence is printed, add it through `format_migration_preview()` or an apply-summary formatter so CLI output and Markdown artifact wording stay aligned.

---

### `README.md` and `MIGRATION_V1_8.md` (documentation, migration workflow)

**Analog:** `README.md`

**Existing Obsidian docs pattern** (lines 329-376):
```markdown
## Obsidian vault adapter (Ideaverse integration)

`--obsidian` exports the knowledge graph as a structured Obsidian vault with proper frontmatter, wikilinks, tags, Dataview queries, and folder placement. The adapter is fully profile-driven — it reads a `.graphify/profile.yaml` from the target vault and generates notes that fit your vault's framework.

**How it works:**

1. **Profile loading** — discovers `.graphify/profile.yaml` in the vault. No profile? Falls back to a built-in default that produces an [Ideaverse](https://ideaverse.com)-compatible ACE structure (`Atlas/Maps/`, `Atlas/Dots/Things/`, etc.).
2. **Classification** — routes each graph node to a note type (MOC, thing, statement, person, source) based on topology (god nodes, degree) and attributes (`file_type`). Custom mapping rules supported.
3. **Template rendering** — generates markdown with YAML frontmatter, `[[wikilinks]]` to related nodes, Dataview queries for MOCs, and community tags. Override any template by placing a `<type>.md` file in `.graphify/templates/`.
4. **Merge planning** — compares new notes against existing vault notes. Preserves user-edited fields (configurable via `merge.preserve_fields`), handles orphans (nodes deleted from graph don't auto-delete notes), and supports three strategies: `update` (default), `skip`, `replace`.
5. **Atomic write** — executes the merge plan, writing only changed files. `--dry-run` previews the plan without writing.
```

**Planner guidance:** Update this section to distinguish low-level `--obsidian --obsidian-dir` export from reviewed `update-vault --input ... --vault ...` migration. The new guide should be generic-first, with `graphify update-vault --input work-vault/raw --vault ls-vault` as the canonical example, and should order steps as backup prerequisite, validation, dry-run, review, apply/archive, rollback, rerun.

---

### `graphify/skill*.md` (skill docs, request-response guidance)

**Analogs:** `tests/test_skill_files.py`, `pyproject.toml`, existing packaged `graphify/skill*.md`

**Packaged variant source of truth** (from `pyproject.toml`, lines 63-64):
```toml
[tool.setuptools.package-data]
graphify = ["skill.md", "skill-codex.md", "skill-opencode.md", "skill-aider.md", "skill-copilot.md", "skill-claw.md", "skill-windows.md", "skill-droid.md", "skill-trae.md", "skill-excalidraw.md", "builtin_templates/*.md", "commands/*.md", "routing_models.yaml", "capability_manifest.schema.json", "capability_tool_meta.yaml"]
```

**Variant contract test pattern** (from `tests/test_skill_files.py`, lines 13-29):
```python
PRIMARY_SKILL = "skill.md"
PLATFORM_VARIANTS = (
    "skill-codex.md",
    "skill-opencode.md",
    "skill-aider.md",
    "skill-copilot.md",
    "skill-claw.md",
    "skill-droid.md",
    "skill-trae.md",
    "skill-windows.md",
)
CORE_COMMANDS = ("/context", "/trace", "/connect", "/drift", "/emerge")
HEADING = "## Available slash commands"

def _read(name: str) -> str:
    return (Path(graphify.__file__).parent / name).read_text(encoding="utf-8")
```

**Consistency assertion pattern** (from `tests/test_skill_files.py`, lines 39-52):
```python
def test_platform_variant_skill_files_list_available_commands():
    for variant in PLATFORM_VARIANTS:
        text = _read(variant)
        assert HEADING in text, f"{variant} missing '{HEADING}' heading"
        for cmd in CORE_COMMANDS:
            assert cmd in text, f"{variant} missing reference to {cmd}"

def test_skill_files_discoverability_section_is_consistent():
    # All 9 files must use the exact same heading text — detect drift early
    all_files = (PRIMARY_SKILL,) + PLATFORM_VARIANTS
    headings = {f: (HEADING in _read(f)) for f in all_files}
    missing = [f for f, present in headings.items() if not present]
    assert not missing, f"Heading '{HEADING}' missing from: {missing}"
```

**Planner guidance:** Extend this file with required phrase arrays and forbidden stale-claim arrays. Do not snapshot whole skill files. Required phrases should cover MOC-only community output, Graphify-owned v1.8 subtree, preview-first `update-vault`, backup before apply, archive under `graphify-out/migrations/archive/`, and no destructive deletion. Forbidden checks should target stale generated-output claims, not every `_COMMUNITY_*` mention.

---

### `tests/test_migration.py` (test, file-I/O + request-response)

**Analog:** `tests/test_migration.py`

**Fixture pattern** (lines 8-30):
```python
def _make_vault(tmp_path: Path) -> Path:
    vault = tmp_path / "ls-vault"
    vault.mkdir()
    (vault / ".obsidian").mkdir()
    (vault / "Atlas" / "Sources" / "Graphify" / "MOCs").mkdir(parents=True)
    return vault

def _write_legacy_community(vault: Path, community_id: int = 12) -> Path:
    legacy = vault / "Atlas" / "Sources" / "Graphify" / "MOCs" / f"_COMMUNITY_{community_id}.md"
    legacy.write_text(
        "---\n"
        "graphify_managed: true\n"
        "type: community\n"
        f"community: {community_id}\n"
        "---\n"
        f"# Legacy Community {community_id}\n"
        "<!-- graphify:metadata:start -->\n"
        "legacy graphify fingerprint\n"
        "<!-- graphify:metadata:end -->\n",
        encoding="utf-8",
    )
    return legacy
```

**Preview artifact no-write pattern** (lines 137-164):
```python
def test_preview_writes_artifacts_but_no_vault_notes(tmp_path):
    """D-11/MIG-02: preview persists JSON/Markdown artifacts without touching vault notes."""
    from graphify.migration import build_migration_preview, write_migration_artifacts

    vault = _make_vault(tmp_path)
    artifacts_dir = tmp_path / "graphify-out"
    ...
    before_vault_files = {p.relative_to(vault).as_posix() for p in vault.rglob("*") if p.is_file()}
    ...
    json_path, md_path = write_migration_artifacts(preview, artifacts_dir)
    ...
    after_vault_files = {p.relative_to(vault).as_posix() for p in vault.rglob("*") if p.is_file()}
    assert after_vault_files == before_vault_files, "MIG-02 preview must not create vault Markdown notes"
```

**Apply filtering pattern to update for Phase 36** (lines 234-277):
```python
def test_apply_never_deletes_legacy_orphan_files(tmp_path):
    """D-11/MIG-06: apply filtering excludes ORPHAN/SKIP rows and legacy files remain."""
    ...
    applicable = filter_applicable_actions(preview)
    assert [row["action"] for row in applicable] == ["CREATE"], "MIG-06 apply helpers must exclude ORPHAN and SKIP rows"
    result = apply_merge_plan(...)

    assert create_target in result.succeeded
    assert legacy.exists(), "MIG-06 legacy _COMMUNITY_* files must never be deleted or moved"
```

**Planner guidance:** Phase 36 should replace the old "legacy remains" assertion with archive-by-default assertions for the migration apply helper while preserving the no-delete invariant: source path should be absent because it moved to archive, archive path should exist with identical contents, and no unrelated vault files should move.

---

### `tests/test_main_flags.py` (test, CLI subprocess)

**Analog:** `tests/test_main_flags.py`

**Subprocess runner pattern** (lines 12-36):
```python
def _graphify(args: list[str], cwd: Path, env: dict | None = None) -> subprocess.CompletedProcess:
    """Invoke `python -m graphify <args>` in cwd, return CompletedProcess.
    ...
    """
    full_env = os.environ.copy()
    worktree_root = Path(__file__).resolve().parent.parent
    existing_pp = full_env.get("PYTHONPATH", "")
    full_env["PYTHONPATH"] = (
        f"{worktree_root}{os.pathsep}{existing_pp}" if existing_pp else str(worktree_root)
    )
    ...
    return subprocess.run(
        [sys.executable, "-m", "graphify", *args],
        cwd=str(cwd),
        env=full_env,
        capture_output=True,
        text=True,
        timeout=60,
    )
```

**Update-vault fixture and preview tests** (lines 340-448):
```python
def _make_update_vault_fixture(tmp_path: Path) -> tuple[Path, Path]:
    raw = tmp_path / "work-vault" / "raw"
    raw.mkdir(parents=True)
    (raw / "alpha.py").write_text(
        "class Alpha:\n"
        "    def compute(self):\n"
        "        return 1\n",
        encoding="utf-8",
    )
    ...

def test_update_vault_preview_default_runs_pipeline(tmp_path):
    pytest.importorskip("yaml")
    raw, vault = _make_update_vault_fixture(tmp_path)

    result = _graphify(
        ["update-vault", "--input", str(raw), "--vault", str(vault)],
        cwd=tmp_path,
    )
    ...
    assert "Migration Preview - repo: graphify" in result.stdout
```

**Apply gate/help pattern** (lines 451-467):
```python
def test_update_vault_apply_without_plan_id_exits_two(tmp_path):
    raw, vault = _make_update_vault_fixture(tmp_path)

    result = _graphify(
        ["update-vault", "--input", str(raw), "--vault", str(vault), "--apply"],
        cwd=tmp_path,
    )

    assert result.returncode == 2
    assert "error: --apply requires --plan-id from a preview artifact" in result.stderr

def test_update_vault_help_lists_command_shape(tmp_path):
    result = _graphify(["update-vault", "--help"], cwd=tmp_path)

    assert result.returncode == 0
    assert "graphify update-vault --input work-vault/raw --vault ls-vault" in result.stdout
```

**Planner guidance:** Add a CLI-level apply test that previews, captures plan ID, applies it, and asserts archive evidence in stdout or artifacts. Keep `pytest.importorskip("yaml")` for profile-backed CLI paths.

---

### `tests/test_profile.py`, `tests/test_templates.py`, `tests/test_naming.py`, or `tests/test_v18_security_matrix.py` (test, transform + validation)

**Analogs:** existing sanitizer tests across profile/templates/naming.

**Profile path and sink helper imports** (from `tests/test_profile.py`, lines 14-25):
```python
from graphify.profile import (
    _DEFAULT_PROFILE,
    _VALID_TOP_LEVEL_KEYS,
    _deep_merge,
    _dump_frontmatter,
    load_profile,
    safe_filename,
    safe_frontmatter_value,
    safe_tag,
    validate_profile,
    validate_vault_path,
)
```

**Vault path tests** (from `tests/test_profile.py`, lines 315-327):
```python
def test_validate_vault_path_safe(tmp_path):
    result = validate_vault_path("Atlas/Maps/", tmp_path)
    assert result == (tmp_path / "Atlas" / "Maps").resolve()

def test_validate_vault_path_traversal_raises(tmp_path):
    with pytest.raises(ValueError, match="would escape"):
        validate_vault_path("../escape", tmp_path)

def test_validate_vault_path_absolute_outside_raises(tmp_path):
    with pytest.raises(ValueError, match="would escape"):
        validate_vault_path("/etc/passwd", tmp_path)
```

**Frontmatter/tag/filename sink tests** (from `tests/test_profile.py`, lines 335-589):
```python
def test_safe_frontmatter_value_newline():
    result = safe_frontmatter_value("line\nbreak")
    assert "\n" not in result
    assert "line break" in result

def test_safe_tag_special_chars():
    assert safe_tag("a/b+c") == "a-b-c"

def test_safe_filename_strips_all_c0_controls():
    """C0 control characters (\\x00-\\x1f) and DEL break filenames/wikilinks."""
    label = "foo" + "".join(chr(c) for c in range(0x00, 0x20)) + "\x7fbar"
    result = safe_filename(label)
    assert all(ord(c) >= 0x20 and ord(c) != 0x7f for c in result)
    assert result == "foobar"
```

**Template/wikilink sink tests** (from `tests/test_templates.py`, lines 12-45 and 444-490):
```python
def test_generated_moc_title_is_sanitized_across_sinks():
    ...
    unsafe_name = "]] | bad {{#connections}}: #tag\x00\n../escape"
    ...
    assert filename == "Bad_Connections_Tag_Escape.md"
    assert "community/bad-connections-tag-escape" in text
    assert "{{#connections}}" not in text
    assert "]] | bad" not in text
    assert "\x00" not in text
    assert "../escape" not in filename

def test_sanitize_wikilink_alias_escapes_closing_brackets():
    from graphify.templates import _sanitize_wikilink_alias
    assert "]]" not in _sanitize_wikilink_alias("Array[int]]")

def test_sanitize_wikilink_alias_escapes_pipe():
    from graphify.templates import _sanitize_wikilink_alias
    result = _sanitize_wikilink_alias("Label|Injection")
    assert "|" not in result
```

**Template implementation invariants** (from `graphify/templates.py`, lines 145-147 and 1014-1027):
```python
# Ordering invariant (D-16): block expansion runs BEFORE `safe_substitute`
# so node labels containing `{{`, `}}`, `#`, `${`, backticks, or newlines
# cannot smuggle conditional logic, fake loops, or break Dataview fences.
...
safe_community_tag = community_tag.replace("`", "").replace("\n", "").replace("\r", "")
safe_folder = folder.replace("`", "").replace("\n", "").replace("\r", "")
...
query = query.replace("```", "")
```

**Repo identity and concept-title tests** (from `tests/test_naming.py`, lines 146-173 and 238-256):
```python
def test_unsafe_llm_title_rejected(tmp_path, capsys, monkeypatch):
    ...
    unsafe_titles = iter([
        "]] | bad",
        "{{#connections}}",
        "../escape",
        "",
        "Community",
    ])
    ...
    assert name.title not in {title, "Community"}
    assert ".." not in name.filename_stem
    assert "{{#connections}}" not in name.title
    assert "]]" not in name.title
    assert name.source == "fallback"

def test_code_filename_stems_use_repo_prefix_and_safe_node_stems():
    from graphify.naming import build_code_filename_stems
    ...
    assert result["n_auth_service"] == {
        "filename_stem": "CODE_graphify_Auth_Service",
        "filename_collision": False,
        "filename_collision_hash": "",
    }
```

**Repo identity helper implementation** (from `graphify/naming.py`, lines 52-64):
```python
def normalize_repo_identity(value: str) -> str:
    """Normalize a repo identity into a short path-safe slug."""
    if "/" in value or "\\" in value or ".." in value:
        raise ValueError("repo identity must not contain path segments or '..'")

    raw = value.strip()
    slug = re.sub(r"[^a-z0-9]+", "-", raw.lower()).strip("-")
    if not slug:
        return "repo"
    if len(slug) > _REPO_IDENTITY_MAX_LEN:
        suffix = hashlib.sha256(slug.encode("utf-8")).hexdigest()[:8]
        slug = f"{slug[:_REPO_IDENTITY_MAX_LEN - 9]}-{suffix}"
    return slug
```

**Planner guidance:** A new `tests/test_v18_security_matrix.py` is acceptable if it imports existing helpers and creates an executable matrix with rows for input class, helper callable, unsafe sample, expected safe result or expected error, and existing/new test name. If adding rows to existing files instead, preserve local grouping comments and one-test-per-behavior style.

## Shared Patterns

### Preview-First Apply
**Source:** `graphify/migration.py` lines 160-254  
**Apply to:** `graphify/migration.py`, `graphify/__main__.py`, migration guide, skill wording  
**Pattern:** preview produces artifacts; apply requires plan ID; loaded plan is revalidated against the current request before side effects.

### File Path Confinement
**Source:** `graphify/profile.py` lines 1032-1087  
**Apply to:** archive source paths, archive destination helper, sanitizer matrix  
```python
def validate_vault_path(candidate: str | Path, vault_dir: str | Path) -> Path:
    """Resolve *candidate* relative to *vault_dir* and verify it stays inside.

    Raises ValueError if the resolved path escapes the vault directory.
    """
    vault_base = Path(vault_dir).resolve()
    resolved = (vault_base / candidate).resolve()
    try:
        resolved.relative_to(vault_base)
    except ValueError:
        raise ValueError(...)
    return resolved
```

### Non-Destructive Merge Boundary
**Source:** `graphify/merge.py` lines 1275-1384  
**Apply to:** archive-by-default design  
**Pattern:** keep generic merge writes limited to CREATE/UPDATE/REPLACE. Archive is a migration-specific post-apply operation, not a new generic merge action.

### Drift Contract Tests
**Source:** `tests/test_skill_files.py` lines 13-52  
**Apply to:** platform skill variant alignment, README/guide phrase checks  
**Pattern:** centralize file list constants, loop through variants, assert exact required phrases and specific forbidden phrases with clear per-file failure messages.

### Pure `tmp_path` Tests
**Source:** `tests/test_migration.py`, `tests/test_main_flags.py`, `tests/test_profile.py`  
**Apply to:** all Phase 36 tests  
**Pattern:** create complete local fixtures under `tmp_path`; no network calls; subprocess tests set `PYTHONPATH` to the worktree root.

## No Analog Found

| File | Role | Data Flow | Reason |
|------|------|-----------|--------|
| `MIGRATION_V1_8.md` | documentation | migration workflow | No standalone migration guide exists yet; use README's Obsidian docs pattern plus CLI/help/test phrases. |

## Metadata

**Analog search scope:** `graphify/`, `tests/`, `README.md`, `pyproject.toml`, Phase 36 planning artifacts  
**Project rules/skills:** No workspace `.cursor/rules/`, `.cursor/skills/`, or `.agents/skills/` were found.  
**Files scanned:** 14 directly read plus phase context/research/validation  
**Pattern extraction date:** 2026-04-29
