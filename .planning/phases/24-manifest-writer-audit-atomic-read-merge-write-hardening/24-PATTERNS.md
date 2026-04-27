# Phase 24: Manifest Writer Audit + Atomic Read-Merge-Write Hardening - Pattern Map

**Mapped:** 2026-04-27
**Files analyzed:** 5 (2 created, 3 modified)
**Analogs found:** 5 / 5

---

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|---|---|---|---|---|
| `graphify/routing_audit.py` | service / writer | file-I/O (atomic read-merge-write) | `graphify/vault_promote.py` `_load_manifest`/`_save_manifest` | role-match (same atomic + merge shape, different key) |
| `graphify/capability.py` | service / writer | file-I/O (atomic read-merge-write) | `graphify/vault_promote.py` `_load_manifest`/`_save_manifest` | role-match (same atomic + merge shape, different key) |
| `tests/test_routing_audit.py` | test | CRUD | `tests/test_routing_sidecar.py` | exact (same module, same `tmp_path` + `monkeypatch.chdir` conventions) |
| `tests/test_capability.py` | test (ADD function) | CRUD | `tests/test_vault_promote.py` `test_vault05_manifest_roundtrip` + `test_multi_run_*` | role-match (write-twice-assert-union shape) |
| `tests/test_vault_promote.py` | test (ADD function) | CRUD | `tests/test_vault_promote.py` `test_multi_run_drift_overwrite_self` | exact (same file, same two-sequential-promote pattern) |

---

## Pattern Assignments

### `graphify/routing_audit.py` — ADD read-merge step in `RoutingAudit.flush`

**Analog:** `graphify/vault_promote.py` — `_load_manifest` / `_save_manifest`

**Context:** `flush` already has `.tmp` + `os.replace` (atomic). The only change is inserting a read-merge step before building `payload`. Row identity key is the file path string (the dict key in `files: {path: routes}`). Last-write-wins on conflict.

**Current `flush` body** (`graphify/routing_audit.py:38-62`):
```python
def flush(self, out_dir: Path) -> Path:
    """Write ``routing.json`` under *out_dir* using atomic replace. D-07/D-08: same pattern as dedup."""
    out_dir = Path(out_dir).resolve()
    cwd = Path.cwd().resolve()
    try:
        out_dir.relative_to(cwd)
    except ValueError as e:
        raise ValueError(
            f"routing audit output path {out_dir} escapes working directory {cwd}"
        ) from e
    out_dir.mkdir(parents=True, exist_ok=True)
    payload = {"version": 1, "files": dict(sorted(self._files.items()))}
    dest = out_dir / "routing.json"
    tmp = dest.with_suffix(".json.tmp")
    try:
        tmp.write_text(
            json.dumps(payload, indent=2, ensure_ascii=False, sort_keys=True),
            encoding="utf-8",
        )
        os.replace(tmp, dest)
    except Exception:
        tmp.unlink(missing_ok=True)
        raise
    return dest
```

**Read-merge-write pattern to copy** (`graphify/vault_promote.py:650-682`):
```python
def _load_manifest(graphify_out: Path) -> dict[str, str]:
    """Load vault-manifest.json from graphify_out/, returning {} if missing or corrupt."""
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


def _save_manifest(manifest: dict[str, str], graphify_out: Path) -> None:
    """Write vault-manifest.json atomically with indent=2, sort_keys=True."""
    manifest_path = graphify_out / "vault-manifest.json"
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
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

**How to apply:** In `flush`, before building `payload`, read the existing `routing.json`
with a module-local `_read_existing_routing(dest)` helper that returns `{}` on missing/corrupt
(≤6 LOC, mirrors `_load_manifest`). Extract `existing_files = existing.get("files", {})`.
Then merge: `merged = {**existing_files, **self._files}`. Build `payload` with `merged`
instead of `self._files`. The `.tmp` + `os.replace` block is unchanged.

**Anchor comment style** (from `graphify/dedup.py:493`, Phase 23 precedent):
```python
# MANIFEST-09: read-merge-write keyed by file path — preserves sibling rows from prior runs.
```

---

### `graphify/capability.py` — ADD read-merge step in `write_manifest_atomic`

**Analog:** `graphify/vault_promote.py` — `_load_manifest` / `_save_manifest` (same pattern, key = tool name)

**Context:** `write_manifest_atomic` already has `.tmp` + `os.replace` (atomic). The change is
a read-merge step before the write. Row identity key is the tool `name` field inside
`data["CAPABILITY_TOOLS"]` (a list of dicts, each with a `"name"` field). Last-write-wins.

**Current `write_manifest_atomic` body** (`graphify/capability.py:225-241`):
```python
def write_manifest_atomic(out_dir: Path, data: dict[str, Any]) -> Path:
    """Write graphify-out/capability.json via .tmp + os.replace.

    Renamed from manifest.json in quick-260422-jdj to eliminate the path
    collision with detect.py's incremental mtime manifest at
    graphify-out/manifest.json. Atomic write semantics (``.tmp`` + os.replace)
    and schema shape are preserved.
    """
    out_dir.mkdir(parents=True, exist_ok=True)
    target = out_dir / "capability.json"
    tmp = target.with_suffix(".tmp")
    payload = json.dumps(data, indent=2, ensure_ascii=False, sort_keys=True) + "\n"
    tmp.write_text(payload, encoding="utf-8")
    os.replace(tmp, target)
    return target
```

**`build_manifest_dict` output shape** — the list the merge operates over (`graphify/capability.py:174-199`):
```python
return {
    "manifest_version": _MANIFEST_VERSION,
    "graphify_version": _graphify_version(),
    "CAPABILITY_TOOLS": [
        _tool_to_manifest_entry(t, meta_defaults, docstrings.get(t.name))
        for t in tools
    ],
}
```

**How to apply:** In `write_manifest_atomic`, before building `payload`:
1. Read existing `capability.json` with an inline `_read_existing_capability(target)`
   helper (≤6 LOC, mirrors `_load_manifest`, returns `{}` on missing/corrupt).
2. Extract `existing_tools_by_name = {t["name"]: t for t in existing.get("CAPABILITY_TOOLS", [])}`.
3. Extract `new_tools_by_name = {t["name"]: t for t in data.get("CAPABILITY_TOOLS", [])}`.
4. Merge: `merged = {**existing_tools_by_name, **new_tools_by_name}`.
5. Reconstruct `data["CAPABILITY_TOOLS"]` as `list(merged.values())` (preserving list shape).
6. Then build `payload` from the merged `data` — the `.tmp` + `os.replace` block is unchanged.

**Anchor comment style:**
```python
# MANIFEST-10: read-merge-write keyed by tool name — preserves sibling tools from prior runs.
```

**Seed mirror pattern** (`graphify/seed.py:96-131`) — additional reference for the `_read_existing`
helper shape when the on-disk value is a list (not a dict):
```python
def _load_seeds_manifest(graphify_out: Path) -> list[dict]:
    """Load seeds-manifest.json from graphify_out/seeds/, returning [] if missing or corrupt."""
    manifest_path = graphify_out / "seeds" / "seeds-manifest.json"
    if not manifest_path.exists():
        return []
    try:
        data = json.loads(manifest_path.read_text(encoding="utf-8"))
        if not isinstance(data, list):
            raise ValueError("manifest is not a list")
        return data
    except (json.JSONDecodeError, OSError, ValueError):
        print(
            "[graphify] seeds-manifest.json corrupted or unreadable — treating all seeds as new",
            file=sys.stderr,
        )
        return []
```

---

### `tests/test_routing_audit.py` — CREATE with `test_subpath_isolation_routing`

**Analog:** `tests/test_routing_sidecar.py` (nearest neighbor — same module, same conventions)

**Module header pattern** (`tests/test_routing_sidecar.py:1-9`):
```python
"""Tests for routing.json audit (ROUTE-05)."""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from graphify.routing_audit import RoutingAudit
```

**Existing test shape to copy** (`tests/test_routing_sidecar.py:11-24`):
```python
def test_atomic_write(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Temp + replace leaves valid JSON (interrupt mid-write does not corrupt final)."""
    monkeypatch.chdir(tmp_path)
    audit = RoutingAudit()
    audit.record(Path("a.py"), "simple", "m", "e", 0, 1.0)
    out = audit.flush(tmp_path / "graphify-out")
    assert out.name == "routing.json"
    data = json.loads(out.read_text(encoding="utf-8"))
    assert data["version"] == 1
    assert "a.py" in data["files"]
```

**New test to create** — `test_subpath_isolation_routing`:
- Use `monkeypatch.chdir(tmp_path)` (required by the path-escape guard in `flush`).
- Flush #1: one `RoutingAudit` with records for `sub_a/file1.py`.
- Flush #2: a new `RoutingAudit` with records for `sub_b/file2.py`, flushing to the same `out_dir`.
- Assert: after flush #2, `routing.json["files"]` contains both `sub_a/file1.py` and `sub_b/file2.py`.
- Assert: no key from flush #1 was erased.

**Full new file structure:**
```python
"""Tests for RoutingAudit read-merge-write contract (MANIFEST-09, Phase 24)."""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from graphify.routing_audit import RoutingAudit


def test_subpath_isolation_routing(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """MANIFEST-09: two sequential flushes on disjoint path sets produce union in routing.json."""
    monkeypatch.chdir(tmp_path)
    out_dir = tmp_path / "graphify-out"

    # First flush — sub_a paths
    audit1 = RoutingAudit()
    audit1.record(Path("sub_a/file1.py"), "simple", "m", "e", 10, 1.0)
    audit1.flush(out_dir)

    # Second flush — sub_b paths (disjoint)
    audit2 = RoutingAudit()
    audit2.record(Path("sub_b/file2.py"), "complex", "m2", "e2", 20, 2.0)
    audit2.flush(out_dir)

    data = json.loads((out_dir / "routing.json").read_text(encoding="utf-8"))
    files = data["files"]
    assert "sub_a/file1.py" in files, "sub_a row erased by second flush"
    assert "sub_b/file2.py" in files, "sub_b row missing after second flush"
```

---

### `tests/test_capability.py` — ADD `test_subpath_isolation_capability_manifest`

**Analog:** `tests/test_capability.py` `test_atomic_manifest_roundtrip` (lines in same file) +
`tests/test_vault_promote.py` `test_multi_run_drift_overwrite_self` (two-sequential-write-assert-union shape)

**Existing import block** (`tests/test_capability.py:1-15`):
```python
"""Phase 13 — capability manifest, registry alignment, CLI."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from graphify.capability import (
    build_manifest_dict,
    canonical_manifest_hash,
    validate_manifest,
    validate_cli,
    write_manifest_atomic,
)
```

**Existing roundtrip test to mirror** (`tests/test_capability.py` — `test_atomic_manifest_roundtrip`):
```python
def test_atomic_manifest_roundtrip(tmp_path: Path) -> None:
    m = build_manifest_dict()
    p = write_manifest_atomic(tmp_path, m)
    assert p.exists()
    roundtrip = json.loads(p.read_text(encoding="utf-8"))
    assert canonical_manifest_hash(roundtrip) == canonical_manifest_hash(m)
```

**New test to add** — `test_subpath_isolation_capability_manifest`:
- Write #1: a manifest dict with `CAPABILITY_TOOLS` containing only `{"name": "tool_a", ...}`.
- Write #2: a manifest dict with `CAPABILITY_TOOLS` containing only `{"name": "tool_b", ...}`.
- Assert: after write #2, `capability.json["CAPABILITY_TOOLS"]` contains both `tool_a` and `tool_b`.
- Use synthetic minimal dicts (not `build_manifest_dict()`) to avoid coupling to live tool registry.

**Sketch:**
```python
def test_subpath_isolation_capability_manifest(tmp_path: Path) -> None:
    """MANIFEST-10: two sequential write_manifest_atomic calls with disjoint tool sets produce union."""
    def _make_data(tool_name: str) -> dict:
        return {
            "manifest_version": "1",
            "graphify_version": "0.0.0-test",
            "CAPABILITY_TOOLS": [{"name": tool_name, "description": f"desc for {tool_name}"}],
        }

    # First write — tool_a only
    write_manifest_atomic(tmp_path, _make_data("tool_a"))

    # Second write — tool_b only (disjoint)
    write_manifest_atomic(tmp_path, _make_data("tool_b"))

    data = json.loads((tmp_path / "capability.json").read_text(encoding="utf-8"))
    names = {t["name"] for t in data["CAPABILITY_TOOLS"]}
    assert "tool_a" in names, "tool_a row erased by second write"
    assert "tool_b" in names, "tool_b row missing after second write"
```

---

### `tests/test_vault_promote.py` — ADD `test_subpath_isolation_vault_manifest`

**Analog:** `tests/test_vault_promote.py` `test_multi_run_drift_overwrite_self` (same file, two-sequential-call shape)

**Existing two-call pattern** (`tests/test_vault_promote.py:664-695`):
```python
def test_multi_run_drift_overwrite_self(tmp_path):
    """Second identical promote() reports all prior notes as overwritten; import-log has 2 Run blocks."""
    from graphify.vault_promote import promote

    graph_path = _make_graph_json_from_fixture(tmp_path)
    vault = tmp_path / "vault"
    vault.mkdir()

    # First run — all notes are written
    promote(graph_path=graph_path, vault_path=vault, threshold=1)

    # Second run — same graph, same threshold
    summary2 = promote(graph_path=graph_path, vault_path=vault, threshold=1)
    ...
```

**Existing `_load_manifest`/`_save_manifest` roundtrip test** (`tests/test_vault_promote.py:411-430`):
```python
def test_vault05_manifest_roundtrip(tmp_path):
    """_save_manifest then _load_manifest round-trips the dict with sort_keys."""
    from graphify.vault_promote import _save_manifest, _load_manifest

    graphify_out = tmp_path / "graphify-out"
    graphify_out.mkdir()

    manifest = {
        "Atlas/Dots/Things/Zeta.md": "abc123",
        "Atlas/Maps/community-0.md": "def456",
        "Atlas/Dots/Things/Alpha.md": "ghi789",
    }
    _save_manifest(manifest, graphify_out)
    loaded = _load_manifest(graphify_out)

    assert loaded == manifest, f"Round-trip mismatch: {loaded}"
```

**New test to add** — `test_subpath_isolation_vault_manifest` (locks existing contract):
- Uses `_save_manifest` / `_load_manifest` directly (no need for `promote()` orchestrator).
- Save #1: manifest with rows for `sub_a/Note.md`.
- Save #2: manifest with rows for `sub_b/Note.md`, merged on top of loaded state.
- Assert: loaded result contains both rows.
- This is a contract-lock test — it MUST pass before Phase 24 (already compliant writer). If it
  fails, it signals a regression in `vault_promote._save_manifest`.

**Sketch:**
```python
def test_subpath_isolation_vault_manifest(tmp_path):
    """Locks existing contract: _save_manifest merges rows keyed by path, no sibling erasure."""
    from graphify.vault_promote import _save_manifest, _load_manifest

    graphify_out = tmp_path / "graphify-out"
    graphify_out.mkdir()

    # First save — sub_a rows
    manifest_a = {"sub_a/NoteA.md": "hash_a1"}
    _save_manifest(manifest_a, graphify_out)

    # Simulate second subpath run: load, merge, save
    existing = _load_manifest(graphify_out)
    existing["sub_b/NoteB.md"] = "hash_b1"
    _save_manifest(existing, graphify_out)

    result = _load_manifest(graphify_out)
    assert "sub_a/NoteA.md" in result, "sub_a row erased by second save"
    assert "sub_b/NoteB.md" in result, "sub_b row missing after second save"
    assert result["sub_a/NoteA.md"] == "hash_a1"
    assert result["sub_b/NoteB.md"] == "hash_b1"
```

---

## Shared Patterns

### Atomic write (`.tmp` + `os.replace`)
**Source:** `graphify/vault_promote.py` `_save_manifest` (lines 665-682)
**Also used in:** `graphify/seed.py` `_save_seeds_manifest` (lines 114-131)
**Apply to:** All patched writers — `routing_audit.flush`, `write_manifest_atomic`

The full atomic pattern (both files use identical structure):
```python
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

Note: `routing_audit.flush` currently uses `tmp.write_text(...)` (no `fsync`) + bare `except Exception`.
The vault_promote pattern uses `os.fsync` and a narrowed `except OSError`. The planner should decide
whether to upgrade `routing_audit.flush` to match `vault_promote`'s stricter atomic pattern or keep
the lighter `write_text` + `except Exception` form. Both are functionally atomic for the merge contract.
`capability.write_manifest_atomic` also uses the lighter form (`tmp.write_text`).

### Read-merge-write helper shape
**Source:** `graphify/vault_promote.py` `_load_manifest` (lines 650-663)
**Apply to:** `routing_audit.flush` and `write_manifest_atomic` — inline `_read_existing_*` helpers

Canonical helper shape (≤6 LOC inline — no new module needed unless both writers end up identical):
```python
def _read_existing_routing(dest: Path) -> dict:
    if not dest.exists():
        return {}
    try:
        data = json.loads(dest.read_text(encoding="utf-8"))
        return data.get("files", {}) if isinstance(data, dict) else {}
    except (json.JSONDecodeError, OSError):
        return {}
```

```python
def _read_existing_capability(target: Path) -> dict:
    if not target.exists():
        return {}
    try:
        data = json.loads(target.read_text(encoding="utf-8"))
        return {t["name"]: t for t in data.get("CAPABILITY_TOOLS", []) if isinstance(t, dict) and "name" in t}
    except (json.JSONDecodeError, OSError):
        return {}
```

Decision per CONTEXT.md §"Claude's Discretion": inline if ≤6 LOC. The capability helper
exceeds 6 LOC when written safely (type-check on `t`). Planner may factor to a shared
`graphify/_manifest_io.py` if both helpers end up identical in shape, but is not required to.

### Test conventions
**Source:** `tests/test_routing_sidecar.py`, `tests/test_capability.py`, `tests/test_vault_promote.py`
**Apply to:** All new and modified test functions

- `from __future__ import annotations` as first import
- Module docstring referencing the requirement label(s) and phase
- Type-annotated signatures: `def test_*(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None`
- `monkeypatch.chdir(tmp_path)` required for any test exercising `routing_audit.flush`
  (the path-escape guard resolves against `Path.cwd()`)
- No network calls, no FS side effects outside `tmp_path`
- Assertion messages include the failing value: `assert "x" in result, f"x missing; got: {result}"`

---

## No Analog Found

All files have close analogs. No entries in this section.

---

## Metadata

**Analog search scope:** `graphify/` (writers), `tests/` (test shape)
**Files scanned:** `vault_promote.py`, `seed.py`, `routing_audit.py`, `capability.py`,
  `tests/test_routing_sidecar.py`, `tests/test_capability.py`, `tests/test_vault_promote.py`
**Pattern extraction date:** 2026-04-27
