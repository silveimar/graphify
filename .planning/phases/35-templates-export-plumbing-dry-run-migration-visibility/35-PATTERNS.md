# Phase 35: Templates, Export Plumbing & Dry-Run/Migration Visibility - Pattern Map

**Mapped:** 2026-04-29
**Files analyzed:** 11 new/modified files
**Analogs found:** 11 / 11

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|-------------------|------|-----------|----------------|---------------|
| `graphify/__main__.py` | route | request-response | `graphify/__main__.py` `run`, `doctor`, `vault-promote` command blocks | exact |
| `graphify/migration.py` | service/utility | file-I/O, batch | `graphify/merge.py`, `graphify/detect.py`, `graphify/output.py` | role-match |
| `graphify/export.py` | exporter/service | transform, file-I/O | `graphify/export.py::to_obsidian` | exact |
| `graphify/merge.py` | service | file-I/O, transform | `graphify/merge.py::compute_merge_plan`, `apply_merge_plan`, `format_merge_plan` | exact |
| `graphify/templates.py` | renderer/utility | transform | `graphify/templates.py::render_note`, `_build_frontmatter_fields` | exact |
| `graphify/output.py` | config/utility | request-response, file-I/O | `graphify/output.py::resolve_output` | exact |
| `graphify/detect.py` | utility | file-I/O, batch | `graphify/detect.py::_save_output_manifest`, `detect` | role-match |
| `tests/test_migration.py` | test | file-I/O, batch | `tests/test_merge.py`, `tests/test_main_flags.py` | role-match |
| `tests/test_main_flags.py` | test | request-response | `tests/test_main_flags.py` CLI subprocess tests | exact |
| `tests/test_export.py` | test | transform, file-I/O | `tests/test_export.py` Obsidian export tests | exact |
| `tests/test_merge.py` | test | file-I/O, transform | `tests/test_merge.py` merge plan/apply tests | exact |

## Pattern Assignments

### `graphify/__main__.py` (route, request-response)

**Analog:** `graphify/__main__.py` command dispatch blocks.

**Imports pattern:** keep top-level imports stdlib-only and import feature modules inside command branches.

```python
from __future__ import annotations
import json
import platform
import re
import shutil
import sys
from pathlib import Path
```

**Argument extraction pattern** (lines 49-71):

```python
def _extract_repo_identity_arg(args: list[str]) -> tuple[str | None, list[str]]:
    """Remove --repo-identity from argv and return its value."""
    repo_identity: str | None = None
    filtered: list[str] = []
    i = 0
    while i < len(args):
        arg = args[i]
        if arg == "--repo-identity":
            if i + 1 >= len(args) or args[i + 1].startswith("--"):
                print("error: --repo-identity requires a value", file=sys.stderr)
                sys.exit(2)
            repo_identity = args[i + 1]
            i += 2
        elif arg.startswith("--repo-identity="):
            repo_identity = arg.split("=", 1)[1]
            if not repo_identity:
                print("error: --repo-identity requires a value", file=sys.stderr)
                sys.exit(2)
            i += 1
        else:
            filtered.append(arg)
            i += 1
    return repo_identity, filtered
```

**Core command pattern** (lines 2223-2256):

```python
elif cmd == "run":
    # graphify run [path] [--router] [--output <path>]
    from graphify.pipeline import run_corpus
    from graphify.output import resolve_output

    rest = list(sys.argv[2:])
    cli_repo_identity, rest = _extract_repo_identity_arg(rest)
    use_router = "--router" in rest
    rest = [a for a in rest if a != "--router"]

    # Parse --output / --output=<path> (D-08 unified override flag)
    cli_output: str | None = None
    filtered: list[str] = []
    i = 0
    while i < len(rest):
        if rest[i] == "--output" and i + 1 < len(rest):
            cli_output = rest[i + 1]; i += 2
        elif rest[i].startswith("--output="):
            cli_output = rest[i].split("=", 1)[1]; i += 1
        else:
            filtered.append(rest[i]); i += 1
    rest = filtered
    raw_target = rest[0] if rest else "."
```

**Pipeline/output integration pattern** (lines 2268-2285):

```python
if resolved.source == "default":
    out_dir = target / "graphify-out" if target.is_dir() else target.parent / "graphify-out"
else:
    out_dir = resolved.artifacts_dir

lock_fd = _foreground_acquire_enrichment_lock(out_dir, timeout_seconds=30.0)
try:
    run_corpus(target, use_router=use_router, out_dir=out_dir, resolved=resolved)
    if resolved is not None:
        from graphify.detect import _save_output_manifest
        _save_output_manifest(
            resolved.artifacts_dir,
            resolved.notes_dir,
            written_files=[],
        )
finally:
    _foreground_release_enrichment_lock(lock_fd)
```

**Argparse subcommand pattern** (lines 2397-2416):

```python
elif cmd == "doctor":
    # graphify doctor [--dry-run]
    import argparse as _ap

    _p_dr = _ap.ArgumentParser(
        prog="graphify doctor",
        description="Diagnose vault detection / profile / output destination / ignore-list (VAULT-14/15)",
    )
    _p_dr.add_argument(
        "--dry-run",
        action="store_true",
        help="Preview which files would be ingested/skipped without writing",
    )
    opts = _p_dr.parse_args(sys.argv[2:])
    from graphify.doctor import run_doctor, format_report
    report = run_doctor(Path.cwd(), dry_run=opts.dry_run)
    print(format_report(report))
    sys.exit(1 if report.is_misconfigured() else 0)
```

**Apply to Phase 35:** add `elif cmd == "update-vault":` near `run`/`doctor`; parse with `argparse`; require `--input` and `--vault`; default to preview; reject `--apply` without `--plan-id` with exit 2; import `graphify.migration` inside the branch.

---

### `graphify/migration.py` (service/utility, file-I/O + batch)

**Analog:** combine pure dataclasses/formatters from `merge.py`, atomic sidecar writes from `detect.py`, and path resolution style from `output.py`.

**Data structure pattern** (lines 82-115 in `graphify/merge.py`):

```python
@dataclass(frozen=True)
class MergeAction:
    """One row in a MergePlan — decision for a single file path."""
    path: Path
    action: Literal["CREATE", "UPDATE", "SKIP_PRESERVE", "SKIP_CONFLICT", "REPLACE", "ORPHAN"]
    reason: str
    changed_fields: list[str] = field(default_factory=list)
    changed_blocks: list[str] = field(default_factory=list)
    conflict_kind: str | None = None
    user_modified: bool = False
    has_user_blocks: bool = False
    source: str = "graphify"

@dataclass(frozen=True)
class MergePlan:
    """Pure data structure produced by compute_merge_plan (Plan 04)."""
    actions: list[MergeAction]
    orphans: list[Path]
    summary: dict[str, int]
```

**Atomic JSON artifact pattern** (lines 385-439 in `graphify/detect.py`):

```python
def _save_output_manifest(
    artifacts_dir: Path,
    notes_dir: Path,
    written_files: list[str],
    run_id: str | None = None,
) -> None:
    """Append a run entry and write output-manifest.json atomically (D-29)."""
    manifest_path = artifacts_dir / _OUTPUT_MANIFEST_NAME
    manifest_path.parent.mkdir(parents=True, exist_ok=True)

    existing = _load_output_manifest(artifacts_dir)
    ts = datetime.datetime.now(datetime.timezone.utc).isoformat()
    if run_id is None:
        h = hashlib.sha256(f"{notes_dir}{ts}".encode()).hexdigest()[:8]
        run_id = f"{ts}-{h}"
    # ...
    tmp = manifest_path.with_suffix(".json.tmp")
    try:
        with open(tmp, "w", encoding="utf-8") as fh:
            fh.write(json.dumps(manifest, indent=2, sort_keys=True))
            fh.write("\n")
            fh.flush()
            os.fsync(fh.fileno())
        os.replace(tmp, manifest_path)
    except OSError:
        if tmp.exists():
            try:
                tmp.unlink()
            except OSError:
                pass
        raise
```

**Path resolution/refusal pattern** (lines 38-49 in `graphify/output.py`):

```python
def _refuse(msg: str) -> SystemExit:
    """Print actionable error to stderr and prepare SystemExit(1)."""
    print(f"[graphify] {msg}", file=sys.stderr)
    return SystemExit(1)

def resolve_output(cwd: Path, *, cli_output: str | None = None) -> ResolvedOutput:
    """Resolve final output destination per D-06..D-13."""
```

**Legacy scan pattern** (lines 511-536 in `graphify/detect.py`):

```python
for scan_root in scan_paths:
    in_memory_tree = memory_dir.exists() and str(scan_root).startswith(str(memory_dir))
    for dirpath, dirnames, filenames in os.walk(scan_root, followlinks=follow_symlinks):
        dp = Path(dirpath)
        if follow_symlinks and os.path.islink(dirpath):
            real = os.path.realpath(dirpath)
            parent_real = os.path.realpath(os.path.dirname(dirpath))
            if parent_real == real or parent_real.startswith(real + os.sep):
                dirnames.clear()
                continue
        if not in_memory_tree:
            pruned: set[str] = set()
            for d in dirnames:
                if d.startswith(".") or _is_noise_dir(d):
                    _record_skip("noise-dir", str(dp / d))
                    pruned.add(d)
                elif _is_ignored(dp / d, root, all_ignore_patterns):
                    _record_skip("exclude-glob", str(dp / d))
                    pruned.add(d)
                elif _is_nested_output(d, resolved_basenames):
                    nested_paths.append(str(dp / d))
                    _record_skip("nesting", str(dp / d))
                    pruned.add(d)
            dirnames[:] = [d for d in dirnames if d not in pruned]
```

**Apply to Phase 35:** new `migration.py` should expose small pure helpers such as `build_migration_preview`, `write_migration_artifacts`, `load_migration_plan`, `validate_plan_matches_request`, and `scan_legacy_notes`. Use frozen dataclasses or plain dicts; write JSON/Markdown artifacts atomically; keep vault note writes delegated to `apply_merge_plan()`.

---

### `graphify/export.py` (exporter/service, transform + file-I/O)

**Analog:** `to_obsidian()`.

**Imports pattern** (lines 1-16):

```python
from __future__ import annotations
import html as _html
import json
import math
import os
import re
import sys
from collections import Counter
from pathlib import Path
from typing import Callable
import networkx as nx
from networkx.readwrite import json_graph
from graphify.security import sanitize_label
from graphify.analyze import _node_community_map, _fmt_source_file
from graphify.profile import safe_filename, safe_frontmatter_value, safe_tag
```

**Repo identity sidecar pattern** (lines 26-50):

```python
def _write_repo_identity_sidecar(artifacts_dir: Path, resolved_repo_identity) -> None:
    """Write resolved repo identity as a generated artifact sidecar."""
    sidecar_path = artifacts_dir / "repo-identity.json"
    sidecar_path.parent.mkdir(parents=True, exist_ok=True)
    tmp = sidecar_path.with_suffix(".json.tmp")
    payload = {
        "identity": resolved_repo_identity.identity,
        "raw_value": resolved_repo_identity.raw_value,
        "source": resolved_repo_identity.source,
        "warnings": list(resolved_repo_identity.warnings),
    }
    try:
        with open(tmp, "w", encoding="utf-8") as fh:
            fh.write(json.dumps(payload, indent=2, sort_keys=True))
            fh.write("\n")
            fh.flush()
            os.fsync(fh.fileno())
        os.replace(tmp, sidecar_path)
    except OSError:
        if tmp.exists():
            try:
                tmp.unlink()
            except OSError:
                pass
        raise
```

**Dry-run return pattern** (lines 826-838):

```python
plan = compute_merge_plan(
    out, rendered_notes, profile,
    skipped_node_ids=skipped,
    manifest=manifest,
    force=force,
)
if dry_run:
    return plan
return apply_merge_plan(
    plan, out, rendered_notes, profile,
    manifest_path=manifest_path,
    old_manifest=manifest,
)
```

**CODE filename identity pattern** (lines 698-719):

```python
code_candidates: list[dict] = []
for node_id, ctx in per_node.items():
    if ctx.get("note_type") != "code" or node_id not in G:
        continue
    node = G.nodes[node_id]
    code_candidates.append(
        {
            "node_id": node_id,
            "label": node.get("label", node_id),
            "source_file": node.get("source_file", ""),
        }
    )
code_filename_stems = build_code_filename_stems(
    code_candidates,
    resolved_repo_identity.identity,
)
for node_id, stem_info in code_filename_stems.items():
    if node_id not in per_node:
        continue
    ctx = dict(per_node[node_id])
    ctx.update(stem_info)
    per_node[node_id] = ctx
```

**Apply to Phase 35:** keep `to_obsidian(dry_run=True)` as the preview source of truth. If repo identity must reach template rendering, enrich per-node CODE contexts before `render_note()` rather than recomputing filenames or rendering notes in `migration.py`.

---

### `graphify/merge.py` (service, file-I/O + transform)

**Analog:** existing merge engine.

**Action vocabulary pattern** (lines 21-43):

```python
_VALID_ACTIONS: frozenset[str] = frozenset({
    "CREATE",
    "UPDATE",
    "SKIP_PRESERVE",
    "SKIP_CONFLICT",
    "REPLACE",
    "ORPHAN",
})

_VALID_CONFLICT_KINDS: frozenset[str] = frozenset({
    "unmanaged_file",
    "malformed_sentinel",
    "malformed_frontmatter",
})
```

**Path confinement pattern** (lines 627-652):

```python
def _validate_target(candidate: Path, vault_dir: Path) -> Path:
    """Gate every candidate path through profile.validate_vault_path."""
    from graphify.profile import validate_vault_path
    if candidate.is_absolute():
        resolved_vault = vault_dir.resolve()
        resolved_candidate = candidate.resolve()
        try:
            rel = resolved_candidate.relative_to(resolved_vault)
        except ValueError as exc:
            raise ValueError(
                f"{candidate!r} escapes vault directory {vault_dir}"
            ) from exc
    else:
        rel = candidate
    return validate_vault_path(rel, vault_dir)
```

**Pure preview pattern** (lines 863-884):

```python
def compute_merge_plan(
    vault_dir: Path,
    rendered_notes: dict[str, RenderedNote],
    profile: dict,
    *,
    skipped_node_ids: set[str] | None = None,
    previously_managed_paths: set[Path] | None = None,
    manifest: dict[str, dict] | None = None,
    force: bool = False,
) -> MergePlan:
    """Pure reconciliation of rendered notes against a vault on disk.

    Produces a MergePlan listing per-file MergeAction decisions. Never writes.
    """
```

**User-modified skip pattern** (lines 919-937):

```python
if manifest and not force:
    rel_key = str(target_path.relative_to(vault_dir))
    entry = manifest.get(rel_key)
    if entry and "content_hash" in entry:
        current_hash = _content_hash(target_path)
        if current_hash != entry["content_hash"]:
            actions.append(MergeAction(
                path=target_path,
                action="SKIP_PRESERVE",
                reason="user-modified since last merge",
                user_modified=True,
                has_user_blocks=entry.get("has_user_blocks", False),
                source="user",
            ))
            continue
```

**Apply safety pattern** (lines 1248-1274):

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
    """
```

**Formatter pattern** (lines 1364-1428):

```python
def format_merge_plan(plan: MergePlan) -> str:
    """Render a MergePlan as the grouped human-readable summary."""
    total = len(plan.actions)
    lines: list[str] = []
    lines.append(f"Merge Plan — {total} actions")
    lines.append("=" * 24)
    # ...
    for key in _ACTION_DISPLAY_ORDER:
        count = summary.get(key, 0)
        lines.append(f"  {key + ':':<15}{count:>3}")
    lines.append("")
    # ...
    return "\n".join(lines) + "\n"
```

**Apply to Phase 35:** add any repo-drift conflict kind conservatively, keeping defaults backward compatible. Do not turn `ORPHAN` into cleanup. If manifest entries gain repo metadata, missing repo must mean unknown, not conflict.

---

### `graphify/templates.py` (renderer/utility, transform)

**Analog:** `render_note()` and `_build_frontmatter_fields()`.

**Imports/sanitizer pattern** (lines 24-31):

```python
from graphify.profile import (
    _DEFAULT_PROFILE,
    _dump_frontmatter,
    safe_filename,
    safe_frontmatter_value,
    safe_tag,
    validate_vault_path,
)
```

**Frontmatter builder pattern** (lines 693-738):

```python
def _build_frontmatter_fields(
    *,
    up: list[str],
    related: list[str],
    collections: list[str],
    tags: list[str],
    note_type: str,
    file_type: str | None,
    source_file: str | None,
    source_location: str | None,
    community: str | None,
    created: datetime.date,
    cohesion: float | None = None,
) -> dict:
    """Build the ordered dict of frontmatter fields."""
    fields: dict = {}
    if up:
        fields["up"] = up
    if related:
        fields["related"] = related
    if collections:
        fields["collections"] = collections
    fields["created"] = created
    if tags:
        fields["tags"] = tags
    fields["type"] = note_type
    if file_type:
        fields["file_type"] = file_type
    if source_file:
        fields["source_file"] = source_file
    if source_location:
        fields["source_location"] = source_location
    if community:
        fields["community"] = community
    if cohesion is not None and note_type in ("moc", "community"):
        fields["cohesion"] = cohesion
    return fields
```

**CODE/non-MOC tag pattern** (lines 1101-1126):

```python
tag_list: list[str] = []
if community_tag:
    # safe_tag ensures no spaces, uppercase, or special chars in the tag
    # component (WR-04). community_tag from ctx may not be pre-slugified.
    tag_list.append(f"community/{safe_tag(community_tag)}")
tag_list.append(f"graphify/{safe_tag(file_type or 'note')}")

frontmatter_fields = _build_frontmatter_fields(
    up=up_list,
    related=related_list,
    collections=[],
    tags=tag_list,
    note_type=note_type,
    file_type=file_type,
    source_file=source_file,
    source_location=source_location,
    community=community_name,
    created=created if created is not None else datetime.date.today(),
)
```

**Apply to Phase 35:** pass repo identity through classification context for CODE notes, add `repo` to CODE frontmatter only, and append `repo/{safe_tag(repo_identity)}` to CODE tags. If `repo` is added to frontmatter, mirror it in merge field policy/order.

---

### `graphify/output.py` (config/utility, request-response + file-I/O)

**Analog:** `resolve_output()`.

**Resolved output shape** (lines 24-30):

```python
class ResolvedOutput(NamedTuple):
    vault_detected: bool
    vault_path: Path | None
    notes_dir: Path
    artifacts_dir: Path
    source: Literal["profile", "cli-flag", "default"]
    exclude_globs: tuple[str, ...] = ()   # Phase 28 D-14
```

**CLI flag precedence pattern** (lines 53-99):

```python
if cli_output is not None:
    cli_path = Path(cli_output)
    flag_path = (
        cli_path.resolve()
        if cli_path.is_absolute()
        else (cwd_resolved / cli_output).resolve()
    )
    if is_vault:
        artifacts_dir = (
            (cwd_resolved.parent / "graphify-out").resolve()
            if cwd_resolved.parent != cwd_resolved
            else flag_path
        )
        print(
            f"[graphify] vault detected at {cwd_resolved} — "
            f"output: {flag_path} (source=cli-flag)",
            file=sys.stderr,
        )
        return ResolvedOutput(True, cwd_resolved, flag_path, artifacts_dir, "cli-flag")
    return ResolvedOutput(False, None, flag_path, flag_path, "cli-flag")
```

**Profile path validation pattern** (lines 141-158):

```python
if mode == "vault-relative":
    from graphify.profile import validate_vault_path
    notes_dir = validate_vault_path(path_val, cwd_resolved)
elif mode == "absolute":
    if not isinstance(path_val, str) or not Path(path_val).is_absolute():
        raise _refuse(
            f"profile output.path must be absolute when mode=absolute (got {path_val!r})"
        )
    notes_dir = Path(path_val).resolve()
elif mode == "sibling-of-vault":
    from graphify.profile import validate_sibling_path
    notes_dir = validate_sibling_path(path_val, cwd_resolved)
else:
    raise _refuse(f"profile output.mode {mode!r} invalid")
```

**Apply to Phase 35:** either reuse `ResolvedOutput` or create a small migration-specific resolver for `--input` and `--vault`. The target vault must be resolved as an existing vault path, while artifacts should remain outside vault note paths to avoid self-ingestion.

---

### `graphify/detect.py` (utility, file-I/O + batch)

**Analog:** output manifest writer and bounded corpus scan.

**Manifest constants pattern** (lines 261-265):

```python
# Phase 28 (VAULT-13): output-manifest constants
_OUTPUT_MANIFEST_NAME = "output-manifest.json"
_OUTPUT_MANIFEST_VERSION = 1
_OUTPUT_MANIFEST_MAX_RUNS = 5
```

**Load warning pattern** (lines 363-382):

```python
def _load_output_manifest(artifacts_dir: Path) -> dict:
    """Load output-manifest.json; return empty envelope on any failure (D-25)."""
    manifest_path = artifacts_dir / _OUTPUT_MANIFEST_NAME
    if not manifest_path.exists():
        return {"version": _OUTPUT_MANIFEST_VERSION, "runs": []}
    try:
        data = json.loads(manifest_path.read_text(encoding="utf-8"))
        if not isinstance(data, dict) or "runs" not in data:
            raise ValueError("unexpected shape")
        return data
    except Exception:
        print(
            "[graphify] WARNING: output-manifest.json unreadable, ignoring history",
            file=sys.stderr,
        )
        return {"version": _OUTPUT_MANIFEST_VERSION, "runs": []}
```

**Apply to Phase 35:** mirror this for `migration-plan-<id>.json` loading, but apply should be stricter than history loading: unreadable or mismatched plan artifact should exit nonzero rather than silently preview/apply.

---

### `tests/test_migration.py` (test, file-I/O + batch)

**Analog:** `tests/test_merge.py` for pure preview/apply and manifest behavior.

**Fixture copy pattern** (lines 401-409):

```python
def _copy_vault_fixture(name: str, tmp_path) -> Path:
    """Copy a checked-in vault fixture into tmp_path and return its root."""
    src = Path(__file__).parent / "fixtures" / "vaults" / name
    dst = tmp_path / name
    shutil.copytree(src, dst)
    return dst
```

**Pure preview test pattern** (lines 650-659):

```python
def test_compute_is_pure_no_mtime_change(tmp_path):
    from graphify.merge import compute_merge_plan
    import os
    vault = _copy_vault_fixture("pristine_graphify", tmp_path)
    target_file = vault / "Atlas/Dots/Things/Transformer.md"
    mtime_before = os.path.getmtime(target_file)
    rn = _rendered_note_matching_pristine(vault)
    compute_merge_plan(vault, {"transformer": rn}, {})
    mtime_after = os.path.getmtime(target_file)
    assert mtime_before == mtime_after, "compute_merge_plan must not modify any file (purity violation)"
```

**ORPHAN non-delete test pattern** (lines 893-908):

```python
def test_apply_orphan_never_deleted(tmp_path):
    from graphify.merge import compute_merge_plan, apply_merge_plan
    vault = _copy_vault_fixture("pristine_graphify", tmp_path)
    orphan_path = Path("Atlas/Dots/Things/Transformer.md")
    plan = compute_merge_plan(
        vault, {}, {},
        previously_managed_paths={(vault / orphan_path).resolve()},
    )
    assert any(a.action == "ORPHAN" for a in plan.actions)
    result = apply_merge_plan(plan, vault, {}, {})
    assert (vault / orphan_path).exists()
    assert (vault / orphan_path).resolve() not in result.succeeded
```

**Apply to Phase 35:** build temporary vaults under `tmp_path`, seed legacy `_COMMUNITY_*` files and `vault-manifest.json`, assert preview artifacts are written but vault notes/manifests are unchanged, and assert apply leaves legacy files intact.

---

### `tests/test_main_flags.py` (test, request-response)

**Analog:** current CLI subprocess tests.

**Subprocess helper pattern** (lines 12-36):

```python
def _graphify(args: list[str], cwd: Path, env: dict | None = None) -> subprocess.CompletedProcess:
    """Invoke `python -m graphify <args>` in cwd, return CompletedProcess."""
    full_env = os.environ.copy()
    worktree_root = Path(__file__).resolve().parent.parent
    existing_pp = full_env.get("PYTHONPATH", "")
    full_env["PYTHONPATH"] = (
        f"{worktree_root}{os.pathsep}{existing_pp}" if existing_pp else str(worktree_root)
    )
    if env:
        full_env.update(env)
    return subprocess.run(
        [sys.executable, "-m", "graphify", *args],
        cwd=str(cwd),
        env=full_env,
        capture_output=True,
        text=True,
        timeout=60,
    )
```

**Missing value exit-code pattern** (lines 302-313):

```python
def test_run_repo_identity_missing_value_exits_two(tmp_path):
    result = _graphify(["run", "--repo-identity"], cwd=tmp_path)

    assert result.returncode == 2
    assert "error: --repo-identity requires a value" in result.stderr
```

**Dry-run no-write pattern** (lines 376-392):

```python
def test_doctor_dry_run_flag(tmp_path):
    pytest.importorskip("yaml")
    vault = _make_doctor_vault(tmp_path, profile_text=_DOCTOR_VALID_PROFILE)
    (vault / "alpha.py").write_text("def a(): return 1\n")

    def _snapshot(p: Path) -> set[Path]:
        return {q for q in p.rglob("*") if q.is_file()}

    before = _snapshot(tmp_path)
    result = _graphify(["doctor", "--dry-run"], cwd=vault)
    after = _snapshot(tmp_path)
    assert "Would ingest:" in result.stdout
    assert "Would write notes to:" in result.stdout
    new_files = after - before
    assert new_files == set(), f"doctor --dry-run wrote files: {sorted(new_files)}"
```

**Apply to Phase 35:** add tests for `update-vault --input raw --vault vault` preview default, `--apply` without `--plan-id` exit 2, and `--help` containing `update-vault`.

---

### `tests/test_export.py` (test, transform + file-I/O)

**Analog:** Obsidian export repo identity and dry-run tests.

**Graph fixture pattern** (lines 233-263):

```python
def _phase33_graph():
    G = nx.Graph()
    G.add_node(
        "n_auth_session",
        label="Auth Session",
        file_type="code",
        source_file="auth/session.py",
        source_location="L10",
        community=0,
    )
    # ...
    G.add_edges_from([
        ("n_auth_session", "n_refresh_token"),
        ("n_auth_session", "n_login_flow"),
    ])
    return G, {0: ["n_auth_session", "n_refresh_token", "n_login_flow"]}
```

**Dry-run sidecar no-write pattern** (lines 295-314):

```python
def test_to_obsidian_dry_run_does_not_write_naming_sidecar(tmp_path):
    from graphify.export import to_obsidian
    from graphify.profile import _DEFAULT_PROFILE

    G, communities = _phase33_graph()
    out_root = tmp_path / "graphify-out"
    obsidian_dir = out_root / "obsidian"
    profile = json.loads(json.dumps(_DEFAULT_PROFILE))
    profile["naming"]["concept_names"]["budget"] = 1.0

    to_obsidian(
        G,
        communities,
        output_dir=str(obsidian_dir),
        profile=profile,
        concept_namer=lambda _payload: "Authentication Session Flow",
        dry_run=True,
    )

    assert not (out_root / "concept-names.json").exists()
```

**Repo identity assertion pattern** (lines 317-339):

```python
def test_to_obsidian_profile_repo_identity_records_sidecar(tmp_path):
    from graphify.export import to_obsidian

    G, communities = _phase33_graph()
    out_root = tmp_path / "graphify-out"
    obsidian_dir = out_root / "obsidian"
    profile = {
        "repo": {"identity": "profile-repo"},
        "naming": {"concept_names": {"enabled": False}},
    }

    to_obsidian(
        G,
        communities,
        output_dir=str(obsidian_dir),
        profile=profile,
    )

    payload = json.loads((out_root / "repo-identity.json").read_text(encoding="utf-8"))
    assert payload["identity"] == "profile-repo"
```

**Apply to Phase 35:** add assertions that CODE note frontmatter contains `repo: graphify`, tags contain `repo/graphify`, manifest entries contain per-note repo identity, and run metadata records resolved repo identity.

---

### `tests/test_merge.py` (test, file-I/O + transform)

**Analog:** merge dataclass, manifest, conflict, formatter tests.

**Vocabulary test pattern** (lines 40-44):

```python
def test_valid_actions_set_contains_exact_vocabulary(self):
    from graphify.merge import _VALID_ACTIONS
    assert _VALID_ACTIONS == frozenset({
        "CREATE", "UPDATE", "SKIP_PRESERVE", "SKIP_CONFLICT", "REPLACE", "ORPHAN"
    })
```

**Manifest shape pattern** (lines 1507-1523):

```python
def test_save_load_roundtrip(self, tmp_path):
    from graphify.merge import _save_manifest, _load_manifest
    manifest_path = tmp_path / "vault-manifest.json"
    data = {
        "Atlas/Note.md": {
            "content_hash": "abc123",
            "last_merged": "2026-04-12T10:00:00+00:00",
            "target_path": "Atlas/Note.md",
            "node_id": "note",
            "note_type": "thing",
            "community_id": 0,
            "has_user_blocks": False,
        }
    }
    _save_manifest(manifest_path, data)
    loaded = _load_manifest(manifest_path)
    assert loaded == data
```

**Formatter conflict pattern** (lines 1384-1397):

```python
def test_format_merge_plan_skip_conflict_suffix():
    plan = _mk_plan([
        MergeAction(
            path=Path("x.md"), action="SKIP_CONFLICT",
            reason="conflict", conflict_kind="unmanaged_file",
        ),
        MergeAction(
            path=Path("y.md"), action="SKIP_CONFLICT",
            reason="conflict", conflict_kind=None,
        ),
    ])
    out = format_merge_plan(plan)
    assert "[unmanaged_file]" in out
    assert "[unknown]" in out
```

**Apply to Phase 35:** extend tests only if `MergeAction` or manifest schema changes. Ensure defaults keep old construction valid, and add tests that missing repo metadata is tolerated while concrete mismatched repo emits `SKIP_CONFLICT`.

## Shared Patterns

### Preview First, Apply Through Merge

**Source:** `graphify/export.py` and `graphify/merge.py`
**Apply to:** `graphify/__main__.py`, `graphify/migration.py`, `tests/test_migration.py`

```python
if dry_run:
    return plan
return apply_merge_plan(
    plan, out, rendered_notes, profile,
    manifest_path=manifest_path,
    old_manifest=manifest,
)
```

Phase 35 preview may write migration artifacts, but vault notes and `vault-manifest.json` must remain unchanged until `--apply --plan-id <id>` succeeds.

### Explicit Safety Actions

**Source:** `graphify/merge.py`
**Apply to:** merge extensions, migration preview rows, terminal/Markdown/JSON artifacts

```python
_ACTION_DISPLAY_ORDER: tuple[str, ...] = (
    "CREATE", "UPDATE", "SKIP_PRESERVE", "SKIP_CONFLICT", "REPLACE", "ORPHAN",
)
```

Use the existing action vocabulary in every artifact. Expand `SKIP_CONFLICT`, `SKIP_PRESERVE`, `ORPHAN`, and `REPLACE` rows in human output.

### Repo Identity Resolution

**Source:** `graphify/naming.py`
**Apply to:** CLI banner, CODE note metadata, manifest metadata, repo drift checks

```python
def resolve_repo_identity(
    cwd: Path,
    *,
    cli_identity: str | None = None,
    profile: dict | None = None,
) -> ResolvedRepoIdentity:
    """Resolve repo identity with CLI > profile > git remote > directory precedence."""
```

Do not add a new repo slug function. Use `resolve_repo_identity()` / `normalize_repo_identity()` and `safe_tag()` for the repo tag.

### Atomic Artifact Writes

**Source:** `graphify/detect.py`, `graphify/export.py`, `graphify/merge.py`
**Apply to:** migration JSON/Markdown artifacts and any metadata sidecars

```python
tmp = manifest_path.with_suffix(".json.tmp")
try:
    with open(tmp, "w", encoding="utf-8") as fh:
        fh.write(json.dumps(manifest, indent=2, sort_keys=True))
        fh.write("\n")
        fh.flush()
        os.fsync(fh.fileno())
    os.replace(tmp, manifest_path)
except OSError:
    if tmp.exists():
        try:
            tmp.unlink()
        except OSError:
            pass
    raise
```

### Path Confinement

**Source:** `graphify/merge.py::_validate_target`, `graphify/profile.py::validate_vault_path`
**Apply to:** legacy scan candidates, migration artifact plan paths, apply validation

```python
if candidate.is_absolute():
    resolved_vault = vault_dir.resolve()
    resolved_candidate = candidate.resolve()
    try:
        rel = resolved_candidate.relative_to(resolved_vault)
    except ValueError as exc:
        raise ValueError(
            f"{candidate!r} escapes vault directory {vault_dir}"
        ) from exc
else:
    rel = candidate
return validate_vault_path(rel, vault_dir)
```

### Test Style

**Source:** `tests/test_main_flags.py`, `tests/test_merge.py`, `tests/test_export.py`
**Apply to:** all Phase 35 tests

Use pure `tmp_path` fixtures, subprocess CLI helper for command behavior, and direct unit tests for pure migration helpers. No network calls and no filesystem side effects outside `tmp_path`.

## No Analog Found

All Phase 35 files have usable analogs. The only new concept is persistent migration plan artifacts with apply-by-plan-id, but its implementation should compose existing manifest, merge plan, and CLI patterns rather than introduce a new architecture.

## Metadata

**Analog search scope:** `graphify/__main__.py`, `graphify/export.py`, `graphify/merge.py`, `graphify/templates.py`, `graphify/output.py`, `graphify/detect.py`, `graphify/naming.py`, `tests/test_main_flags.py`, `tests/test_export.py`, `tests/test_merge.py`, `tests/test_templates.py`
**Files scanned:** 12
**Pattern extraction date:** 2026-04-29
