# Phase 28: Self-Ingestion Hardening - Pattern Map

**Mapped:** 2026-04-27
**Files analyzed:** 9 (5 modified, 4 test files — 3 existing + 1 new wave)
**Analogs found:** 9 / 9

---

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|-------------------|------|-----------|----------------|---------------|
| `graphify/detect.py` | utility (file-scan) | batch | self (extend existing) | exact — same file |
| `graphify/output.py` | utility (NamedTuple) | request-response | self (extend existing) | exact — same file |
| `graphify/profile.py` | utility (schema validation) | request-response | self (extend existing) | exact — same file |
| `graphify/pipeline.py` | service (orchestration) | request-response | self (extend existing) | exact — same file |
| `graphify/__main__.py` | controller (CLI) | request-response | self (extend existing) | exact — same file |
| `tests/test_detect.py` | test | batch | `tests/test_detect.py` lines 241–305 | exact |
| `tests/test_profile.py` | test | request-response | `tests/test_profile.py` lines 1223–1295 | exact |
| `tests/test_output.py` | test | request-response | `tests/test_output.py` lines 218–245 | exact |

---

## Pattern Assignments

### `graphify/detect.py` — extensions (utility, batch)

**Analog:** self — extend existing patterns at lines 252–430

#### Imports pattern (lines 1–8):
```python
# file discovery, type classification, and corpus health checks
from __future__ import annotations
import fnmatch
import json
import os
import re
from enum import Enum
from pathlib import Path
```

**Phase 28 additions to imports block** — add after `from pathlib import Path`:
```python
import sys
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from graphify.output import ResolvedOutput
```
`sys` is already used in `__main__.py`; `TYPE_CHECKING` guard is the project-established pattern for avoiding circular imports (see `extract.py` lines 12–17 for the canonical example).

#### Core pattern 1 — `_SELF_OUTPUT_DIRS` constant (line 252):
```python
# graphify's own output directory — always pruned by default to prevent
# self-ingestion loops …
_SELF_OUTPUT_DIRS = {"graphify-out", "graphify_out"}
```
Phase 28 adds a new predicate alongside (not replacing) `_is_noise_dir`:
```python
def _is_nested_output(part: str, resolved_basenames: frozenset[str]) -> bool:
    """Return True if dirname matches any known graphify output location (D-18)."""
    if part in _SELF_OUTPUT_DIRS:
        return True
    if part in resolved_basenames:
        return True
    return False
```
`resolved_basenames` is computed once before `os.walk`:
```python
resolved_basenames: frozenset[str] = frozenset()
if resolved is not None:
    resolved_basenames = frozenset({
        resolved.notes_dir.name,
        resolved.artifacts_dir.name,
    }) - _SELF_OUTPUT_DIRS
```

#### Core pattern 2 — `_is_noise_dir` (lines 261–274):
```python
def _is_noise_dir(part: str) -> bool:
    """Return True if this directory name looks like a venv, cache, or dep dir."""
    if part in _SKIP_DIRS:
        return True
    if part in _SELF_OUTPUT_DIRS:
        return True
    if part.endswith("_venv") or part.endswith("_env"):
        return True
    if part.endswith(".egg-info"):
        return True
    return False
```
**Do not modify this function.** Phase 28 calls the new `_is_nested_output` predicate alongside it (see `detect()` walk loop below).

#### Core pattern 3 — `_is_ignored` fnmatch matcher (lines 307–337):
```python
def _is_ignored(path: Path, root: Path, patterns: list[str]) -> bool:
    """Return True if path matches any .graphifyignore pattern."""
    if not patterns:
        return False
    try:
        rel = str(path.relative_to(root))
    except ValueError:
        return False
    rel = rel.replace(os.sep, "/")
    parts = rel.split("/")
    for pattern in patterns:
        p = pattern.strip("/")
        if not p:
            continue
        if fnmatch.fnmatch(rel, p):
            return True
        if fnmatch.fnmatch(path.name, p):
            return True
        for i, part in enumerate(parts):
            if fnmatch.fnmatch(part, p):
                return True
            if fnmatch.fnmatch("/".join(parts[:i + 1]), p):
                return True
    return False
```
Phase 28 reuses this **unmodified** for `output.exclude` globs (D-16). In the per-file loop, add:
```python
exclude_globs: list[str] = list(resolved.exclude_globs) if resolved else []
# … per-file loop …
if exclude_globs and _is_ignored(p, root, exclude_globs):
    continue
```

#### Core pattern 4 — `detect()` signature extension (line 338):
```python
# Current:
def detect(root: Path, *, follow_symlinks: bool = False) -> dict:

# Phase 28 minimal diff:
def detect(
    root: Path,
    *,
    follow_symlinks: bool = False,
    resolved: "ResolvedOutput | None" = None,  # Phase 28 (D-14..D-21, D-25..D-27)
) -> dict:
```
All 5 existing call sites pass no second argument — `resolved=None` activates the unchanged code path.

#### Core pattern 5 — `dirnames[:]` walk filter (lines 393–400, current form):
```python
dirnames[:] = [
    d for d in dirnames
    if not d.startswith(".")
    and not _is_noise_dir(d)
    and not _is_ignored(dp / d, root, ignore_patterns)
]
```
Phase 28 refactors this to accumulate nesting paths for the D-20 summary warning:
```python
nested_paths: list[str] = []
# … before the walk …

# inside the os.walk loop, replace the dirnames[:] comprehension:
pruned: set[str] = set()
for d in dirnames:
    if d.startswith(".") or _is_noise_dir(d) or _is_ignored(dp / d, root, ignore_patterns):
        pruned.add(d)
    elif _is_nested_output(d, resolved_basenames):
        nested_paths.append(str(dp / d))
        pruned.add(d)
dirnames[:] = [d for d in dirnames if d not in pruned]
```
After the walk loop, emit the D-20 single summary warning:
```python
if nested_paths:
    deepest = max(nested_paths, key=lambda p: p.count(os.sep))
    print(
        f"[graphify] WARNING: skipped {len(nested_paths)} nested output path(s) "
        f"(deepest: {deepest})",
        file=sys.stderr,
    )
```

#### Core pattern 6 — `_load_output_manifest` / `_save_output_manifest` helpers:

These are **new** functions. Copy the structure from `vault_promote.py:_load_manifest` (line 648) and `vault_promote.py:_save_manifest` (line 661) with the VAULT-13 schema additions:

**`_load_output_manifest`** — mirrors `vault_promote.py:_load_manifest` (lines 648–660):
```python
_OUTPUT_MANIFEST_NAME = "output-manifest.json"
_OUTPUT_MANIFEST_VERSION = 1
_OUTPUT_MANIFEST_MAX_RUNS = 5

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

**`_save_output_manifest`** — mirrors `vault_promote.py:_save_manifest` (lines 661–693) + adds FIFO trim and GC:
```python
def _save_output_manifest(
    artifacts_dir: Path,
    notes_dir: Path,
    written_files: list[str],
    run_id: str | None = None,
) -> None:
    """Append run entry and write output-manifest.json atomically (D-29)."""
    import hashlib
    import datetime
    manifest_path = artifacts_dir / _OUTPUT_MANIFEST_NAME
    manifest_path.parent.mkdir(parents=True, exist_ok=True)

    existing = _load_output_manifest(artifacts_dir)
    ts = datetime.datetime.now(datetime.timezone.utc).isoformat()
    if run_id is None:
        h = hashlib.sha256(f"{notes_dir}{ts}".encode()).hexdigest()[:8]
        run_id = f"{ts}-{h}"

    new_run = {
        "run_id": run_id,
        "timestamp": ts,
        "notes_dir": str(notes_dir.resolve()),
        "artifacts_dir": str(artifacts_dir.resolve()),
        "files": [str(Path(f).resolve()) for f in written_files],
    }

    runs: list[dict] = existing.get("runs", [])
    # D-28: GC stale file entries from prior runs
    for run in runs:
        run["files"] = [f for f in run.get("files", []) if Path(f).exists()]
    # Append and FIFO-trim to N=5 (D-24)
    runs.append(new_run)
    runs = runs[-_OUTPUT_MANIFEST_MAX_RUNS:]

    manifest = {"version": _OUTPUT_MANIFEST_VERSION, "runs": runs}

    # Atomic write: tmp + os.replace (D-29) — mirrors merge.py:_write_atomic
    tmp = manifest_path.with_suffix(".json.tmp")
    try:
        with open(tmp, "w", encoding="utf-8") as fh:
            fh.write(json.dumps(manifest, indent=2, sort_keys=True))
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

#### Core pattern 7 — prior-file prune in `detect()`:
```python
# Before the os.walk loop, after loading ignore_patterns:
prior_files: set[str] = set()
if resolved is not None:
    manifest_data = _load_output_manifest(resolved.artifacts_dir)
    for run in manifest_data.get("runs", []):
        prior_files.update(run.get("files", []))

# In the per-file loop, before ftype classification:
if prior_files and str(p.resolve()) in prior_files:
    continue
```

#### Error handling pattern — `[graphify]`-prefixed stderr (from `build.py`, `cluster.py`):
```python
print("[graphify] WARNING: ...", file=sys.stderr)
```
All warn-and-skip paths in Phase 28 follow this pattern. Never `raise SystemExit` on nesting detection (D-19).

#### `detect_incremental()` deleted-files GC pattern (lines 503–505):
```python
# Files in manifest that no longer exist - their cached nodes are now ghost nodes
current_files = {f for flist in full["files"].values() for f in flist}
deleted_files = [f for f in manifest if f not in current_files]
```
Phase 28 D-28 mirrors this: for each prior run in the output manifest, GC `files` entries where `Path(f).exists()` is False.

---

### `graphify/output.py` — `ResolvedOutput` extension (utility, request-response)

**Analog:** self — extend `ResolvedOutput` NamedTuple at lines 24–30

#### Current `ResolvedOutput` (lines 24–30):
```python
class ResolvedOutput(NamedTuple):
    vault_detected: bool
    vault_path: Path | None
    notes_dir: Path
    artifacts_dir: Path
    source: Literal["profile", "cli-flag", "default"]
```

#### Phase 28 minimal diff — add 6th field with default:
```python
class ResolvedOutput(NamedTuple):
    vault_detected: bool
    vault_path: Path | None
    notes_dir: Path
    artifacts_dir: Path
    source: Literal["profile", "cli-flag", "default"]
    exclude_globs: tuple[str, ...] = ()   # Phase 28 D-14
```
NamedTuple trailing default fields are valid on Python 3.6.1+ (confirmed target: 3.10+).

#### `resolve_output()` population pattern — vault+profile branch (lines ~133–172):
```python
# After profile is loaded and output_block is confirmed valid:
# Current return (vault + profile path):
return ResolvedOutput(True, cwd_resolved, notes_dir, artifacts_dir, "profile")

# Phase 28: populate exclude_globs from profile
_raw_exclude = profile.get("output", {}).get("exclude", [])
_exclude_globs: tuple[str, ...] = tuple(_raw_exclude) if isinstance(_raw_exclude, list) else ()
return ResolvedOutput(True, cwd_resolved, notes_dir, artifacts_dir, "profile", _exclude_globs)
```
The other two resolution branches (cli-flag, default) continue to return `exclude_globs=()` — the 6th field default handles this transparently.

#### Function-local import pattern (lines 118–127, used for `profile.py`):
```python
# Function-local imports avoid circular dependency (output -> profile, never reverse)
try:
    import yaml  # noqa: F401
except ImportError:
    raise _refuse(...)

from graphify.profile import load_profile
```
Phase 28 does **not** add any new imports to `output.py`; `exclude_globs` is populated from the already-loaded `profile` dict.

---

### `graphify/profile.py` — `validate_profile()` `output:` branch extension (utility, request-response)

**Analog:** self — extend the `output:` branch at lines 422–451

#### Current `output:` schema branch (lines 422–451):
```python
output = profile.get("output")
if output is not None:
    if not isinstance(output, dict):
        errors.append("'output' must be a mapping (dict)")
    else:
        mode = output.get("mode")
        if mode is None:
            errors.append("'output' requires a 'mode' key")
        elif mode not in _VALID_OUTPUT_MODES:
            errors.append(
                f"output.mode {mode!r} invalid — valid modes are: "
                f"{sorted(_VALID_OUTPUT_MODES)}"
            )
        path_val = output.get("path")
        if path_val is None:
            errors.append("'output' requires a 'path' key")
        elif not isinstance(path_val, str) or not path_val.strip():
            errors.append("output.path must be a non-empty string")
        elif mode == "vault-relative":
            if Path(path_val).is_absolute():
                errors.append("output.path must be relative when mode=vault-relative")
            elif path_val.startswith("~"):
                errors.append("output.path must not start with '~' when mode=vault-relative")
            elif ".." in Path(path_val).parts:
                errors.append("output.path must not contain '..' when mode=vault-relative")
        elif mode == "absolute":
            if not Path(path_val).is_absolute():
                errors.append("output.path must be absolute when mode=absolute")
        # mode == "sibling-of-vault": deferred to validate_sibling_path() at use-time
```

#### Phase 28 addition — append after existing mode/path validation, inside the `else:` block:
```python
        # Phase 28 D-17: validate output.exclude list
        exclude = output.get("exclude")
        if exclude is not None:
            if not isinstance(exclude, list):
                errors.append("output.exclude must be a list")
            else:
                for i, item in enumerate(exclude):
                    if not isinstance(item, str):
                        errors.append(
                            f"output.exclude[{i}] must be a string "
                            f"(got {type(item).__name__})"
                        )
                    elif not item.strip():
                        errors.append(
                            f"output.exclude[{i}] must not be empty or whitespace-only"
                        )
                    elif Path(item).is_absolute():
                        errors.append(
                            f"output.exclude[{i}] must not be an absolute path"
                        )
                    elif ".." in Path(item.lstrip("/")).parts:
                        errors.append(
                            f"output.exclude[{i}] must not contain '..' (path traversal)"
                        )
```

#### Traversal-rejection pattern — mirrors `folder_mapping` validation (lines 284–299):
```python
# Existing folder_mapping traversal rejection (lines 284-292):
elif path_val.startswith("..") or "/.." in path_val or "\\.." in path_val:
    errors.append(f"folder_mapping.{name} must not traverse above root (contains '..')")
elif path_val.startswith("/") or (len(path_val) > 1 and path_val[1] == ":"):
    errors.append(f"folder_mapping.{name} must not be an absolute path")
```
Phase 28 uses `".." in Path(item.lstrip("/")).parts` which is consistent with the existing `vault-relative` path check at line 447.

#### Error accumulator pattern — `validate_profile()` signature (line 209):
```python
def validate_profile(profile: dict) -> list[str]:
    """Return a list of validation errors; empty list = valid."""
    errors: list[str] = []
    ...
    return errors
```
Phase 28 appends to `errors` in the same pattern — no signature change, no raising inside the validator.

---

### `graphify/pipeline.py` — `run_corpus()` signature extension (service, request-response)

**Analog:** self — minimal keyword parameter addition

#### Current signature (line 7):
```python
def run_corpus(target: Path, *, use_router: bool, out_dir: Path | None = None) -> dict:
```

#### Phase 28 minimal diff:
```python
def run_corpus(
    target: Path,
    *,
    use_router: bool,
    out_dir: Path | None = None,
    resolved: "ResolvedOutput | None" = None,  # Phase 28 D-14..D-21
) -> dict:
```
Add `TYPE_CHECKING` guard at top of `pipeline.py` (mirrors `extract.py` lines 12–17):
```python
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from graphify.output import ResolvedOutput
```
Thread `resolved` to `detect`:
```python
det = detect(target, resolved=resolved)
```

---

### `graphify/__main__.py` — manifest write wire-points (controller, request-response)

**Analog:** existing `resolve_output` call sites at lines 1326–1327 (`--obsidian` branch) and 2120–2142 (`run` branch)

#### `--obsidian` branch wire-point (after `result = to_obsidian(...)`, ~line 1388):
```python
# Phase 28 (D-29): write output manifest after successful export
if not isinstance(result, MergePlan) and resolved is not None:
    from graphify.detect import _save_output_manifest
    written = getattr(getattr(result, "plan", None), "written_files", None) or []
    _save_output_manifest(resolved.artifacts_dir, resolved.notes_dir, written)
```

#### `run` branch wire-point (after `run_corpus(...)`, ~line 2162):
```python
# Phase 28 (D-29): write output manifest after successful export
if resolved is not None:
    from graphify.detect import _save_output_manifest
    _save_output_manifest(
        resolved.artifacts_dir,
        resolved.notes_dir,
        written_files=[],  # roots only; full file list via --obsidian path
    )
```

#### Pattern: function-local import (established in `output.py`, `pipeline.py`, `__main__.py`):
```python
from graphify.detect import _save_output_manifest
```
Import is placed inside the `if` guard, not at module level, consistent with the lazy-import convention throughout `__main__.py`.

#### Pattern: `resolved is not None` guard (established at lines 1331–1333):
```python
if cli_output is not None:
    obsidian_dir = str(resolved.notes_dir)
elif resolved.vault_detected and resolved.source == "profile":
    obsidian_dir = str(resolved.notes_dir)
```
Phase 28 guards its manifest write with `resolved is not None` — same style.

---

## Shared Patterns

### Atomic write (merge.py lines 1152–1174 — canonical reference)
**Apply to:** `_save_output_manifest()` in `detect.py`
```python
def _write_atomic(target: Path, content: str) -> None:
    tmp = target.with_suffix(target.suffix + ".tmp")
    target.parent.mkdir(parents=True, exist_ok=True)
    try:
        with open(tmp, "w", encoding="utf-8") as fh:
            fh.write(content)
            fh.flush()
            os.fsync(fh.fileno())
        os.replace(tmp, target)
    except OSError:
        if tmp.exists():
            try:
                tmp.unlink()
            except OSError:
                pass
        raise
```
For `.json` files, `target.with_suffix(target.suffix + ".tmp")` produces `.json.tmp`. Identical pattern is also in `vault_promote.py:_write_atomic` (line 627) and `enrich.py:_commit_pass` (line 448).

### Warn-on-corrupt manifest + silent-on-missing (vault_promote.py lines 648–660)
**Apply to:** `_load_output_manifest()` in `detect.py`
```python
def _load_manifest(graphify_out: Path) -> dict[str, str]:
    manifest_path = graphify_out / "vault-manifest.json"
    if not manifest_path.exists():
        return {}
    try:
        return json.loads(manifest_path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        print(
            "[graphify] vault-manifest.json corrupted or unreadable — treating all notes as new",
            file=sys.stderr,
        )
        return {}
```
Phase 28 variant returns `{"version": 1, "runs": []}` instead of `{}` to maintain schema shape.

### `[graphify]`-prefixed stderr (build.py, cluster.py, output.py)
**Apply to:** all warnings in `detect.py` Phase 28 additions
```python
print("[graphify] WARNING: ...", file=sys.stderr)
```

### `TYPE_CHECKING` guard for circular-import-safe type hints (extract.py lines 12–17)
**Apply to:** `detect.py` (for `ResolvedOutput`), `pipeline.py` (for `ResolvedOutput`)
```python
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from graphify.output import ResolvedOutput
```

### `errors.append(...)` accumulator without early return (profile.py lines 209–451)
**Apply to:** `validate_profile()` `exclude` extension
All errors are collected into a list; function always returns the complete list.

---

## Test Pattern Assignments

### `tests/test_detect.py` — nesting guard + manifest + exclude_globs tests

**Analog:** `tests/test_detect.py` lines 241–305 (existing `test_detect_skips_graphify_out_*` suite)

#### Fixture pattern (lines 241–252):
```python
def test_detect_skips_graphify_out_subtree(tmp_path):
    """detect() must NOT re-ingest its own graphify-out/ output."""
    out_dir = tmp_path / "graphify-out" / "obsidian"
    out_dir.mkdir(parents=True)
    (out_dir / "foo.md").write_text("# Some prior export\n\nA simple note.\n")
    (tmp_path / "main.py").write_text("x = 1")

    result = detect(tmp_path)
    for ftype, file_list in result["files"].items():
        for f in file_list:
            assert "/graphify-out/obsidian" not in f
    assert any("main.py" in f for f in result["files"]["code"])
```
Phase 28 adds analogous tests that construct a `ResolvedOutput` with `notes_dir` pointing to a custom path and verify `detect(tmp_path, resolved=resolved)` prunes it.

#### Warning emission test pattern — use `capsys`:
```python
def test_detect_warns_nesting_once(tmp_path, capsys):
    """D-20: a single summary warning, not per-file."""
    ...
    result = detect(tmp_path, resolved=resolved)
    captured = capsys.readouterr()
    warning_lines = [l for l in captured.err.splitlines() if "WARNING: skipped" in l]
    assert len(warning_lines) == 1
    assert "nested output path" in warning_lines[0]
```

#### Manifest round-trip pattern — `tmp_path` only, no network:
```python
def test_save_and_load_output_manifest(tmp_path):
    from graphify.detect import _save_output_manifest, _load_output_manifest
    artifacts_dir = tmp_path / "artifacts"
    notes_dir = tmp_path / "notes"
    artifacts_dir.mkdir(); notes_dir.mkdir()
    f = notes_dir / "note.md"
    f.write_text("x")
    _save_output_manifest(artifacts_dir, notes_dir, [str(f)])
    data = _load_output_manifest(artifacts_dir)
    assert len(data["runs"]) == 1
    assert str(f.resolve()) in data["runs"][0]["files"]
```

### `tests/test_profile.py` — `output.exclude` validation tests

**Analog:** `tests/test_profile.py` lines 1229–1295 (Phase 27 `output:` block tests)

#### Pattern — one assertion per error scenario:
```python
def test_validate_profile_output_exclude_valid_glob():
    assert validate_profile({"output": {
        "mode": "vault-relative", "path": "Atlas",
        "exclude": ["**/cache/**", "*.tmp"]
    }}) == []

def test_validate_profile_output_exclude_not_a_list():
    errs = validate_profile({"output": {
        "mode": "vault-relative", "path": "Atlas",
        "exclude": "*.tmp"
    }})
    assert any("must be a list" in e for e in errs)

def test_validate_profile_output_exclude_empty_string_rejected():
    errs = validate_profile({"output": {
        "mode": "vault-relative", "path": "Atlas",
        "exclude": [""]
    }})
    assert any("must not be empty" in e for e in errs)

def test_validate_profile_output_exclude_absolute_path_rejected():
    errs = validate_profile({"output": {
        "mode": "vault-relative", "path": "Atlas",
        "exclude": ["/etc/*"]
    }})
    assert any("must not be an absolute path" in e for e in errs)

def test_validate_profile_output_exclude_traversal_rejected():
    errs = validate_profile({"output": {
        "mode": "vault-relative", "path": "Atlas",
        "exclude": ["../../etc/*"]
    }})
    assert any("'..' (path traversal)" in e for e in errs)
```

### `tests/test_output.py` — `exclude_globs` field tests

**Analog:** `tests/test_output.py` lines 218–245 (NamedTuple field order + unpacking tests)

#### Field order test — update to 6 fields:
```python
def test_resolved_output_namedtuple_field_order():
    assert ResolvedOutput._fields == (
        "vault_detected",
        "vault_path",
        "notes_dir",
        "artifacts_dir",
        "source",
        "exclude_globs",  # Phase 28 D-14
    )
```

#### Unpacking test — update to 6 variables:
```python
def test_resolved_output_unpacks_to_tuple():
    r = ResolvedOutput(True, Path("/v"), Path("/v/n"), Path("/g"), "profile", ("*.tmp",))
    vault_detected, vault_path, notes_dir, artifacts_dir, source, exclude_globs = r
    assert exclude_globs == ("*.tmp",)
```

#### Default value test:
```python
def test_resolved_output_exclude_globs_defaults_to_empty_tuple():
    r = ResolvedOutput(False, None, Path("a"), Path("b"), "default")
    assert r.exclude_globs == ()
```

---

## No Analog Found

All files in Phase 28 are extensions of existing files — no entirely new modules are introduced. The `output-manifest.json` data structure is new, but its read/write helpers live in `detect.py` and follow existing `vault_promote.py:_load_manifest` / `_save_manifest` patterns exactly.

---

## Metadata

**Analog search scope:** `graphify/` (detect.py, output.py, profile.py, pipeline.py, merge.py, vault_promote.py, enrich.py, extract.py), `tests/` (test_detect.py, test_output.py, test_profile.py)
**Files scanned:** 11 source files, 3 test files
**Pattern extraction date:** 2026-04-27
