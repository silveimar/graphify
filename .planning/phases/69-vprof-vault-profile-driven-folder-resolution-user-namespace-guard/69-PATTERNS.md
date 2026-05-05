# Phase 69: VPROF — Vault Profile-Driven Folder Resolution & User-Namespace Guard - Pattern Map

**Mapped:** 2026-05-05
**Files analyzed:** 6
**Analogs found:** 6 / 6

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|-------------------|------|-----------|----------------|---------------|
| `graphify/profile.py` | service/config | CRUD (schema migration) | `graphify/profile.py` itself (extend) | self |
| `graphify/vault_promote.py` | service | request-response / file-I/O | `graphify/vault_promote.py` itself (refactor) | self |
| `graphify/__main__.py` | controller | request-response | existing `update-vault` + `doctor` wiring in `__main__.py` | exact |
| `graphify/doctor.py` | utility | request-response | existing `format_report()` in `graphify/doctor.py` | exact |
| `tests/test_profile.py` | test | CRUD | `tests/test_profile.py` itself (extend) | self |
| `tests/test_vault_promote.py` | test | request-response | `tests/test_vault_promote.py` itself (extend) | exact |

---

## Pattern Assignments

### `graphify/profile.py` — add migrator + new schema v2 keys

**Analog:** `graphify/profile.py` existing patterns

**Imports pattern** (lines 1-10 of profile.py):
```python
from __future__ import annotations

"""Profile loading, validation, deep merge, and safety helpers for Obsidian export."""

import os
import sys
from copy import deepcopy
from pathlib import Path
from typing import TYPE_CHECKING, NamedTuple
```

**_DEFAULT_PROFILE extension pattern** — add new top-level keys under existing dict (lines 65-170):
```python
_DEFAULT_PROFILE: dict = {
    # ... existing keys ...
    # Phase 69 new keys — schema v2 placeholders
    "graphify_folder_mapping": {
        "things":     "Atlas/Dots/Things",
        "questions":  "Atlas/Dots/Questions",
        "statements": "Atlas/Dots/Statements",
        "people":     "Atlas/Dots/People",
        "quotes":     "Atlas/Dots/Quotes",
        "maps":       "Atlas/Maps",
        "sources":    "Atlas/Sources/Clippings",
    },
    "user_only_folders": [],
    "augment": {
        "allow_community": True,
    },
    "reverse_sync": {},  # Phase 70 placeholder — not consumed in Phase 69
}
```

**_VALID_TOP_LEVEL_KEYS extension pattern** (lines ~175):
```python
_VALID_TOP_LEVEL_KEYS = {
    # ... existing keys ...
    "graphify_folder_mapping",  # Phase 69 (VPROF-01)
    "user_only_folders",         # Phase 69 (VPROF-02)
    "augment",                   # Phase 69 (VPROF-03)
    "reverse_sync",              # Phase 70 placeholder
}
```

**Atomic YAML write pattern for migrator** — copy exactly from `profile.py` lines 1547-1557:
```python
# Write .bak before overwrite — idempotent: skip if .bak already exists
bak_path = profile_path.with_suffix(".yaml.bak")
if not bak_path.exists():
    bak_path.write_bytes(profile_path.read_bytes())

tmp = profile_path.with_suffix(".yaml.tmp")
tmp.write_text(
    yaml.dump(updated, allow_unicode=True, sort_keys=True),
    encoding="utf-8",
)
os.replace(tmp, profile_path)
```

**stderr warning pattern** (consistent with all profile.py warnings):
```python
print(
    "[graphify] profile: migrated legacy keys → graphify_folder_mapping "
    "(backup at .graphify/profile.yaml.bak)",
    file=sys.stderr,
)
```

**Migrator function signature pattern** — follow `_apply_taxonomy_folder_mapping` style (lines 344-360):
```python
def migrate_profile_v1_to_v2(profile_path: Path, vault_dir: Path) -> str:
    """Migrate a v1 profile.yaml to v2 in-place, writing .bak first.

    Returns "migrated" | "already_v2" | "skipped_no_yaml".
    Idempotent: if graphify_folder_mapping already present, returns "already_v2".
    """
```

---

### `graphify/vault_promote.py` — profile-driven folder resolution

**Analog:** `graphify/vault_promote.py` existing patterns

**Imports — no new imports needed** (lines 38-46):
```python
from graphify.profile import (
    _DEFAULT_PROFILE,
    _deep_merge,
    _dump_frontmatter,
    safe_filename,
    safe_frontmatter_value,
    safe_tag,
    validate_vault_path,
)
```

**_FOLDER_PATH_PREFIX dict to REMOVE** (lines 872-880) — replace dict lookup with profile read:
```python
# REMOVE this dict entirely in Phase 69:
_FOLDER_PATH_PREFIX: dict[str, str] = {
    "things":     "Atlas/Dots/Things",
    "questions":  "Atlas/Dots/Questions",
    "statements": "Atlas/Dots/Statements",
    "people":     "Atlas/Dots/People",
    "quotes":     "Atlas/Dots/Quotes",
    "maps":       "Atlas/Maps",
    "sources":    "Atlas/Sources/Clippings",
}
```

**Profile-driven folder resolution pattern** — read from `graphify_folder_mapping` key in merged profile (replace `_FOLDER_PATH_PREFIX[bucket_key]` at line 958):
```python
def _resolve_folder_prefix(bucket_key: str, merged_profile: dict) -> str:
    """Return vault-relative folder prefix for *bucket_key* from merged profile.

    Falls back to _DEFAULT_PROFILE["graphify_folder_mapping"][bucket_key] when
    the user profile omits the key, preserving backward compatibility.
    """
    mapping = merged_profile.get("graphify_folder_mapping") or {}
    default_mapping = _DEFAULT_PROFILE["graphify_folder_mapping"]
    raw = mapping.get(bucket_key) or default_mapping[bucket_key]
    # Normalize: strip trailing slash (rel_path construction adds it)
    return raw.rstrip("/")
```

**`_assert_under_pinned_subtree` guard pattern** — follow `validate_vault_path` style (lines 1480-1494):
```python
def _assert_under_pinned_subtree(rel_path: str, graphify_folder_mapping: dict) -> None:
    """Raise ValueError if rel_path is not under any graphify-owned folder.

    Prevents writes into user-only folders defined outside graphify_folder_mapping.
    """
    pinned_prefixes = tuple(
        v.rstrip("/") + "/"
        for v in graphify_folder_mapping.values()
        if isinstance(v, str)
    )
    if not any(rel_path.startswith(p) for p in pinned_prefixes):
        raise ValueError(
            f"Target path {rel_path!r} is not under any graphify-owned folder. "
            "Check graphify_folder_mapping in .graphify/profile.yaml."
        )
```

**`_write_record` chokepoint pattern** — wrap `write_note` to enforce the guard before each write:
```python
def _write_record(
    vault_dir: Path,
    rel_path: str,
    content: str,
    manifest: dict[str, str],
    graphify_folder_mapping: dict,
) -> str:
    """Single chokepoint for all vault writes in promote(). Enforces namespace guard."""
    _assert_under_pinned_subtree(rel_path, graphify_folder_mapping)
    return write_note(vault_dir, rel_path, content, manifest)
```

**Pre-flight pass pattern** — iterate profile mapping values and call `validate_vault_path` before any writes (follow existing step structure in `promote()` lines 920-935):
```python
# Pre-flight: validate all profile-derived paths before any I/O
folder_mapping = merged_profile.get("graphify_folder_mapping", _DEFAULT_PROFILE["graphify_folder_mapping"])
for bucket_key, folder_prefix in folder_mapping.items():
    try:
        validate_vault_path(vault_dir / folder_prefix.rstrip("/"), vault_dir)
    except ValueError as exc:
        raise ValueError(
            f"graphify_folder_mapping[{bucket_key!r}] is invalid: {exc}"
        ) from exc
```

**Legacy artifact detection pattern** — scan vault for notes under old hardcoded paths:
```python
_LEGACY_GRAPHIFY_FOLDERS: tuple[str, ...] = (
    "Atlas/Dots/Things",
    "Atlas/Dots/Questions",
    "Atlas/Dots/Statements",
    "Atlas/Dots/People",
    "Atlas/Dots/Quotes",
    "Atlas/Maps",
    "Atlas/Sources/Clippings",
)

def detect_legacy_artifacts(vault_dir: Path) -> list[str]:
    """Return vault-relative paths of notes under legacy graphify-owned folders.

    Called by doctor and --migrate-legacy pre-flight.
    """
    found: list[str] = []
    for folder in _LEGACY_GRAPHIFY_FOLDERS:
        folder_path = vault_dir / folder
        if folder_path.is_dir():
            for md in folder_path.rglob("*.md"):
                found.append(md.relative_to(vault_dir).as_posix())
    return found
```

---

### `graphify/__main__.py` — wire `--migrate-legacy` flag into `vault-promote`

**Analog:** existing `vault-promote` argparse block (lines 3370-3410)

**Add flag to existing `_p_vp` ArgumentParser pattern** — follow `--threshold` style (line ~3385):
```python
_p_vp.add_argument(
    "--migrate-legacy",
    action="store_true",
    help="Detect and move legacy Atlas/Dots/… notes to profile-mapped folders before promoting",
)
```

**Dispatch after `opts = _p_vp.parse_args(...)` pattern** — follow `opts.apply and not opts.plan_id` guard style:
```python
if opts.migrate_legacy:
    from graphify.vault_promote import migrate_legacy_artifacts
    legacy_result = migrate_legacy_artifacts(
        vault_path=Path(_vp_vault),
        graph_path=Path(opts.graph),
        dry_run=False,
    )
    moved = legacy_result.get("moved", 0)
    print(f"[graphify] migrate-legacy: moved {moved} note(s) to profile-mapped folders")
```

**Doctor `--migrate-legacy` section pattern** — follows the existing `opts.dot_graphify_track` branch (lines 3195-3230):
```python
if opts.migrate_legacy:
    from graphify.vault_promote import detect_legacy_artifacts
    _dr_vault = report.vault_path or Path.cwd()
    legacy = detect_legacy_artifacts(_dr_vault)
    if legacy:
        print(f"[graphify] legacy artifacts ({len(legacy)}):")
        for p in legacy[:10]:
            print(f"[graphify]   {p}")
        if len(legacy) > 10:
            print(f"[graphify]   ... +{len(legacy) - 10} more")
    else:
        print("[graphify] no legacy graphify artifacts detected")
    _cli_exit(0)
```

---

### `graphify/doctor.py` — add legacy artifact detection section

**Analog:** `format_report()` section pattern (lines 545-620)

**New section appended to `format_report()` after `=== Recommended Fixes ===`**:
```python
# --- Legacy Artifacts (Phase 69, VPROF) -----------------------------------
lines.append("[graphify] === Legacy Artifacts ===")
if hasattr(report, "legacy_artifact_paths") and report.legacy_artifact_paths:
    lines.append(
        f"[graphify] {len(report.legacy_artifact_paths)} legacy graphify note(s) "
        "under hardcoded Atlas/Dots/… paths detected"
    )
    for p in report.legacy_artifact_paths[:5]:
        lines.append(f"[graphify]   {p}")
    overflow = len(report.legacy_artifact_paths) - 5
    if overflow > 0:
        lines.append(f"[graphify]   ... +{overflow} more")
    lines.append(
        "[graphify] FIX: Run 'graphify vault-promote --migrate-legacy' to move notes "
        "to profile-mapped folders"
    )
else:
    lines.append("[graphify] no legacy graphify artifacts detected")
```

**DoctorReport dataclass extension pattern** — follow existing `@dataclass` field additions (lines 155-175):
```python
@dataclass
class DoctorReport:
    # ... existing fields ...
    legacy_artifact_paths: list[str] = field(default_factory=list)  # Phase 69 (VPROF)
```

**run_doctor() population pattern** — follow `_build_preview_section` call style (line ~471):
```python
# Phase 69: detect legacy artifacts when vault is known
if report.vault_path and report.vault_path.is_dir():
    from graphify.vault_promote import detect_legacy_artifacts
    report.legacy_artifact_paths = detect_legacy_artifacts(report.vault_path)
```

---

### `tests/test_profile.py` — migrator tests

**Analog:** `tests/test_profile.py` existing test patterns (lines 1-55)

**Imports pattern** (lines 1-22 of test_profile.py):
```python
from __future__ import annotations
import sys
from pathlib import Path
from unittest import mock
import pytest
from graphify.profile import (
    _DEFAULT_PROFILE,
    load_profile,
    # add: migrate_profile_v1_to_v2
)
```

**tmp_path + yaml fixture pattern** — consistent with all profile tests:
```python
def _write_profile(tmp_path: Path, content: dict) -> Path:
    """Write a YAML profile to tmp_path/.graphify/profile.yaml."""
    import yaml
    profile_dir = tmp_path / ".graphify"
    profile_dir.mkdir(parents=True, exist_ok=True)
    profile_path = profile_dir / "profile.yaml"
    profile_path.write_text(yaml.dump(content, allow_unicode=True))
    return profile_path
```

**Idempotency test pattern** — test function returns "already_v2" on second call:
```python
def test_migrate_profile_v1_to_v2_idempotent(tmp_path):
    """Second call must return 'already_v2' without rewriting .bak."""
    pytest.importorskip("yaml")
    from graphify.profile import migrate_profile_v1_to_v2

    profile_path = _write_profile(tmp_path, {"taxonomy": {"version": "v1.8", ...}})
    migrate_profile_v1_to_v2(profile_path, tmp_path)
    bak_mtime = (tmp_path / ".graphify" / "profile.yaml.bak").stat().st_mtime

    result = migrate_profile_v1_to_v2(profile_path, tmp_path)
    assert result == "already_v2"
    # .bak must not be rewritten on second call
    assert (tmp_path / ".graphify" / "profile.yaml.bak").stat().st_mtime == bak_mtime
```

**`.bak` creation test pattern**:
```python
def test_migrate_profile_v1_to_v2_writes_bak(tmp_path):
    """Migrator must write .bak before touching profile.yaml."""
    pytest.importorskip("yaml")
    from graphify.profile import migrate_profile_v1_to_v2

    profile_path = _write_profile(tmp_path, {"taxonomy": {"version": "v1.8", ...}})
    original_bytes = profile_path.read_bytes()

    migrate_profile_v1_to_v2(profile_path, tmp_path)

    bak = tmp_path / ".graphify" / "profile.yaml.bak"
    assert bak.exists(), ".bak must be created"
    assert bak.read_bytes() == original_bytes, ".bak must be unmodified copy of original"
```

**`pytest.importorskip("yaml")` guard** — used consistently in all profile tests that need PyYAML:
```python
def test_migrate_profile_v1_to_v2_skipped_no_yaml(tmp_path):
    """Returns 'skipped_no_yaml' when profile.yaml does not exist."""
    from graphify.profile import migrate_profile_v1_to_v2
    result = migrate_profile_v1_to_v2(tmp_path / ".graphify" / "profile.yaml", tmp_path)
    assert result == "skipped_no_yaml"
```

---

### `tests/test_vault_promote.py` — new tests for profile-driven folder routing

**Analog:** `tests/test_vault_promote.py` existing patterns (lines 1-160)

**Graph-building helper pattern** (lines 9-24) — reuse `_make_graph_with_nodes` and `_make_communities`:
```python
from tests.test_vault_promote import _make_graph_with_nodes, _make_communities
# OR redefine inline — both patterns present in codebase
```

**`classify_nodes` test isolation pattern** (lines 33-55):
```python
def test_vprof_folder_routing_from_profile(tmp_path):
    """classify_nodes must use profile graphify_folder_mapping for folder field."""
    from graphify.vault_promote import classify_nodes

    G = _make_graph_with_nodes([
        {"id": "t1", "label": "Thing1", "file_type": "document", "source_file": "a.md", "community": 0},
    ])
    # Add edges to exceed threshold
    for i in range(4):
        G.add_node(f"p{i}", label=f"P{i}", file_type="document", source_file="b.md", community=0)
        G.add_edge("t1", f"p{i}", relation="references", confidence="EXTRACTED", source_file="a.md")

    communities = _make_communities(G, {0: ["t1"] + [f"p{i}" for i in range(4)]})
    profile = {
        "graphify_folder_mapping": {
            "things": "MyVault/Graph/Things",
            # ... other keys omitted → fall back to default
        }
    }

    result = classify_nodes(G, communities, profile, threshold=2)

    thing_folders = [r["folder"] for r in result["things"]]
    assert all("MyVault/Graph/Things" in f for f in thing_folders), \
        "Things must use profile-mapped folder, not hardcoded Atlas/Dots/Things"
```

**Namespace guard test pattern** — follow `write_note` test style with `pytest.raises`:
```python
def test_vprof_write_record_rejects_user_folder(tmp_path):
    """_write_record must raise ValueError for paths outside graphify_folder_mapping."""
    from graphify.vault_promote import _write_record

    vault = tmp_path / "vault"
    vault.mkdir()
    graphify_folder_mapping = {"things": "Atlas/Dots/Things"}
    with pytest.raises(ValueError, match="not under any graphify-owned folder"):
        _write_record(vault, "UserNotes/MyNote.md", "content", {}, graphify_folder_mapping)
```

**End-to-end `promote()` test update pattern** — existing `test_end_to_end_all_seven_folders` must pass a profile with `graphify_folder_mapping` and assert output paths use profile values:
```python
# In test_end_to_end_all_seven_folders — add profile fixture
profile_dir = vault / ".graphify"
profile_dir.mkdir()
import yaml
(profile_dir / "profile.yaml").write_text(yaml.dump({
    "taxonomy": {"version": "v1.8", "root": "Atlas/Sources/Graphify",
                 "folders": {"moc": "MOCs", "thing": "Things", ...}},
    "mapping": {"min_community_size": 3},
    "graphify_folder_mapping": {
        "things":     "Atlas/Dots/Things",
        "questions":  "Atlas/Dots/Questions",
        "statements": "Atlas/Dots/Statements",
        "people":     "Atlas/Dots/People",
        "quotes":     "Atlas/Dots/Quotes",
        "maps":       "Atlas/Maps",
        "sources":    "Atlas/Sources/Clippings",
    },
}))
```

---

## Shared Patterns

### Atomic write (no data loss on crash)
**Source:** `graphify/vault_promote.py` `_write_atomic()` (lines 641-660) — copied from `merge.py`
**Apply to:** `profile.py` migrator, any new file write in `vault_promote.py`
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

### Path security guard
**Source:** `graphify/profile.py` `validate_vault_path()` (lines 1480-1494)
**Apply to:** All new path construction in `vault_promote.py`, `_assert_under_pinned_subtree`
```python
def validate_vault_path(candidate: str | Path, vault_dir: str | Path) -> Path:
    vault_base = Path(vault_dir).resolve()
    resolved = (vault_base / candidate).resolve()
    try:
        resolved.relative_to(vault_base)
    except ValueError:
        raise ValueError(
            f"Profile-derived path {candidate!r} would escape vault directory {vault_base}. "
            "Check folder_mapping values for path traversal sequences."
        )
    return resolved
```

### stderr warning prefix
**Source:** throughout `profile.py` and `vault_promote.py`
**Apply to:** all new diagnostic prints
```python
print("[graphify] <message>", file=sys.stderr)
```

### `[graphify]-prefixed` doctor output lines
**Source:** `graphify/doctor.py` `format_report()` (lines 545-620)
**Apply to:** all new `format_report()` section additions in `doctor.py`
```python
lines.append("[graphify] === Section Name ===")
lines.append(f"[graphify] key: {value}")
lines.append("[graphify] FIX: imperative action sentence")
```

### Test PyYAML guard
**Source:** `tests/test_profile.py` — all tests touching YAML files
**Apply to:** all new migrator tests in `test_profile.py`
```python
pytest.importorskip("yaml")
```

### Test tmp_path isolation
**Source:** `tests/test_vault_promote.py` every test function (line 33+)
**Apply to:** all new tests — use `tmp_path` fixture, never touch real filesystem
```python
def test_<name>(tmp_path):
    vault = tmp_path / "vault"
    vault.mkdir()
    # all operations relative to vault or tmp_path
```

---

## No Analog Found

All files have close analogs in the existing codebase. No file requires a purely greenfield pattern.

---

## Metadata

**Analog search scope:** `graphify/vault_promote.py`, `graphify/profile.py`, `graphify/__main__.py`, `graphify/doctor.py`, `tests/test_vault_promote.py`, `tests/test_profile.py`
**Files scanned:** 6 source files, 2 test files
**Pattern extraction date:** 2026-05-05
