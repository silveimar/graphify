# Phase 24: Manifest Writer Audit + Atomic Read-Merge-Write Hardening - Research

**Researched:** 2026-04-27
**Domain:** Python manifest file I/O — atomic read-merge-write patterns across graphify writers
**Confidence:** HIGH

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

- **D-01:** "The MCP `manifest.json`" in success criteria = `capability.json` (`graphify/capability.py:225`). Was renamed from `manifest.json` in quick-260422-jdj to eliminate collision with `detect.py`'s `graphify-out/manifest.json`.
- **D-02:** `RoutingAudit.flush` switches to read-merge-write keyed by **file path** (the dict key in `files:{path: routes}`), last-write-wins. Atomic commit (`.tmp` + `os.replace`) is already present; patch is the read-merge step only.
- **D-03:** Row identity keys (locked):
  - `vault-manifest.json` → `path` (note path)
  - `seeds-manifest.json` → `seed_id`
  - `routing.json` → file path (dict key in `files:{path: routes}`)
  - `capability.json` → tool name (entry `.name` field in `CAPABILITY_TOOLS` list)
- **D-04:** `write_manifest_atomic` in `capability.py` switches to read-merge-write keyed by **tool name**, last-write-wins. Atomic commit already present; patch is the read-merge step.
- **D-05:** `detect.save_manifest` (`graphify/detect.py:447`) is documented in AUDIT.md as DEFERRED (known-bad: blind overwrite, non-atomic). NOT patched — not reachable from any active CLI flow.
- **D-06:** AUDIT.md is a single table with columns: manifest filename, writer (file:function:line), invocation site, row identity key, pre-fix read?, pre-fix atomic?, post-fix read?, post-fix atomic?, Phase 24 action. ~1 page, 1-paragraph preamble. No landmine appendix.
- **D-07:** Three unit tests, pure `tmp_path`, no E2E:
  1. `tests/test_vault_promote.py` → `test_subpath_isolation_vault_manifest` (locks existing contract, no code change)
  2. `tests/test_routing_audit.py` → `test_subpath_isolation_routing` (new test file; no test file for routing_audit currently exists)
  3. `tests/test_capability.py` (exists) → `test_subpath_isolation_capability_manifest`
- **D-08:** No migration code. On first read after upgrade, writers treat on-disk state as authoritative. AUDIT.md documents recovery path (re-run on missing subpaths).
- **Already-compliant (DO NOT modify):** `graphify/vault_promote.py:665-682`, `graphify/merge.py:1085`, `graphify/seed.py:96-131`

### Claude's Discretion

- Whether the read-merge step lives inline or factors out to a `_read_existing(path) -> dict` helper. Default: inline if ≤6 LOC; factored if both writers end up with identical shape (shared `graphify/_manifest_io.py` acceptable, not required).
- Exact location of the new test file `tests/test_routing_audit.py` (confirmed absent; create under existing conventions).
- Whether AUDIT.md sits at `.planning/phases/24-.../AUDIT.md` (preferred) or repo root.
- Which existing vault-promote/merge test surface exercises the subpath isolation contract.
- One-line anchor comments at each patched write site referencing MANIFEST-09/10 (default: yes, terse, matching `dedup.py:494` style).

### Deferred Ideas (OUT OF SCOPE)

- Atomic + read-merge-write fix for `detect.save_manifest` / `graphify-out/manifest.json`
- `graphify manifest rebuild` CLI
- Stale-manifest detection + stderr warning
- Shared `graphify/_manifest_io.py` unless it falls out naturally
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| MANIFEST-09 | Running `graphify` on a subpath does not erase manifest entries belonging to siblings or previous runs on other subpaths | Addressed by patching `routing_audit.flush` and `write_manifest_atomic` to read-merge before write; existing `vault_promote._save_manifest` and `merge._save_manifest` already compliant |
| MANIFEST-10 | All on-disk manifest writers follow read-merge-write with atomic `.tmp` + `os.replace` commit, scoped by row identity | Two writers (`routing.json`, `capability.json`) need the read-merge step added; two already compliant (`vault-manifest.json`, `seeds-manifest.json`); one deferred (`detect`'s `manifest.json`) |
| MANIFEST-11 | Subpath isolation regression: two sequential runs on `vault/sub_a/` then `vault/sub_b/` yield a single manifest containing rows from both | Three pure unit tests with `tmp_path`: vault-manifest (lock), routing (new), capability (new) |
| MANIFEST-12 | AUDIT.md enumerates every manifest writer, pre-v1.6 policy, post-fix policy | AUDIT.md at `.planning/phases/24-.../AUDIT.md`; one table, all 5 writers, D-06 column shape |
</phase_requirements>

---

## Summary

Phase 24 is a precision hardening pass: two writers need a read-merge step inserted before their already-present atomic commit (`.tmp` + `os.replace`). No new abstractions, no migrations, no CLI changes. The code surface is small — roughly 6-8 new lines per writer — and the reference implementations are already in the codebase.

**`routing_audit.flush`** (`graphify/routing_audit.py:34-56`) currently builds `payload = {"version": 1, "files": dict(sorted(self._files.items()))}` and writes it blindly. The fix: before building `payload`, read the existing `routing.json` (if any), extract `existing.get("files", {})`, merge `self._files` on top (last-write-wins per file path), then write the merged dict. The atomic commit (lines 49-55) is untouched.

**`write_manifest_atomic`** (`graphify/capability.py:225-241`) currently receives a fully-built `data` dict and writes it blindly. The callers always pass the result of `build_manifest_dict()`, which produces a list under `CAPABILITY_TOOLS`. The fix: in `write_manifest_atomic`, read the existing `capability.json` (if any), build a `{tool_name: entry}` index from the on-disk list, overlay the incoming list (last-write-wins per tool name), rebuild the list, and write. The atomic commit (lines 239-240) is untouched.

The reference implementations for read-merge-write are `vault_promote._save_manifest` / `_load_manifest` and `seed._save_seeds_manifest` / `_load_seeds_manifest`. Both follow the same pattern: read + return `{}` on missing/corrupt, merge new rows on top keyed by row identity, write via `.tmp` + `os.replace`.

**Primary recommendation:** Patch inline (≤6 LOC each). The read shapes differ enough (dict-of-dicts for routing vs list-of-dicts for capability) that a shared helper would need to be parameterized and adds no net simplicity. Write `tests/test_routing_audit.py` as a new file; add `test_subpath_isolation_capability_manifest` to existing `tests/test_capability.py`; add `test_subpath_isolation_vault_manifest` to `tests/test_vault_promote.py`.

---

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Atomic file commit (`.tmp` + `os.replace`) | CLI / Library | — | All writers live in the Python library tier; no server, no DB |
| Read-merge-write for routing.json | CLI / Library (`routing_audit.py`) | — | Routing audit is populated by `pipeline.py` and flushed to `graphify-out/` |
| Read-merge-write for capability.json | CLI / Library (`capability.py`) | — | Capability manifest is written by `export.to_json` → `write_runtime_manifest` → `write_manifest_atomic` |
| Subpath isolation contract | Test tier | — | Three pure unit tests assert the union-of-rows invariant |
| AUDIT.md | Planning artifact | — | Lives in `.planning/phases/24-.../AUDIT.md` |

---

## Standard Stack

### Core (no new dependencies)

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| `json` (stdlib) | 3.10+ | Serialise / deserialise manifest JSON | Already used everywhere |
| `os.replace` (stdlib) | 3.10+ | Atomic file replace | Cross-platform atomic rename; used in all existing writers |
| `pathlib.Path` (stdlib) | 3.10+ | Path manipulation | Project-wide convention |
| `pytest` | project pin | Unit tests | Existing test framework |

No new packages. All changes are pure stdlib. [VERIFIED: codebase grep]

---

## Architecture Patterns

### System Architecture Diagram

```
graphify CLI run (subpath A)
  └── pipeline.py:run()
        ├── extract() → RoutingAudit.record(path, ...)
        │     └── routing_audit.flush(out_dir)
        │           READ routing.json → existing_files{}
        │           MERGE self._files ON TOP (last-write-wins by path)
        │           WRITE routing.json via .tmp + os.replace
        │
        └── export.to_json()
              └── write_runtime_manifest(out_dir)
                    └── write_manifest_atomic(out_dir, data)
                          READ capability.json → existing_tools{name: entry}
                          MERGE incoming CAPABILITY_TOOLS ON TOP (last-write-wins by tool name)
                          WRITE capability.json via .tmp + os.replace

graphify CLI run (subpath B) — same flow
  → routing.json now contains BOTH subpath A rows AND subpath B rows
  → capability.json now contains BOTH runs' tool entries (tool list is static; merge is idempotent)
```

### Recommended Project Structure (no changes)

```
graphify/
├── routing_audit.py    # patch: add read-merge step in flush()
├── capability.py       # patch: add read-merge step in write_manifest_atomic()
├── vault_promote.py    # NO CHANGE — already compliant
├── merge.py            # NO CHANGE — already compliant
├── seed.py             # NO CHANGE — already compliant
└── detect.py           # NO CHANGE — deferred (AUDIT.md only)

tests/
├── test_routing_audit.py   # NEW FILE — test_subpath_isolation_routing + existing atomic tests
├── test_capability.py      # ADD test_subpath_isolation_capability_manifest
└── test_vault_promote.py   # ADD test_subpath_isolation_vault_manifest
```

---

## Code Under Change — Verbatim Excerpts + Exact Line References

### Writer 1: `RoutingAudit.flush` — PATCHED

**File:** `graphify/routing_audit.py`
**Lines:** 34-56 [VERIFIED: codebase read]

```python
# CURRENT (routing_audit.py:34-56) — blind overwrite, atomic
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

**Post-fix shape (read-merge step inserted before payload construction):**

```python
# MANIFEST-09/10: read existing routing.json, merge new run's files on top (last-write-wins by path)
existing: dict[str, Any] = {}
if dest.exists():
    try:
        existing = json.loads(dest.read_text(encoding="utf-8")).get("files", {})
    except (json.JSONDecodeError, OSError):
        existing = {}
merged_files = {**existing, **self._files}  # last-write-wins on path key
payload = {"version": 1, "files": dict(sorted(merged_files.items()))}
```

This replaces the single `payload = ...` line (routing_audit.py:45). The `.tmp` + `os.replace` block below it is unchanged. The `dest` variable must be defined before the read step — move `dest = out_dir / "routing.json"` up before the merge block.

**Input dict shape:**
- `self._files`: `dict[str, dict[str, Any]]` — keys are `str(path)`, values are `{"class": str, "model": str, "endpoint": str, "tokens_used": int, "ms": float}`
- On-disk `routing.json`: `{"version": 1, "files": {str: dict}}`
- Merge key: file path string (dict key in `files`)
- Conflict policy: last-write-wins (current run's entry replaces on-disk entry for same path)

### Writer 2: `write_manifest_atomic` — PATCHED

**File:** `graphify/capability.py`
**Lines:** 225-241 [VERIFIED: codebase read]

```python
# CURRENT (capability.py:225-241) — blind overwrite, atomic
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

**Invocation chain:** `write_runtime_manifest(out_dir)` → `write_manifest_atomic(out_dir, build_manifest_dict())` ← called from `export.to_json()` at `export.py:304` [VERIFIED: codebase grep]

**`build_manifest_dict()` output shape [VERIFIED: live introspection]:**
```python
{
    "manifest_version": "1",
    "graphify_version": "...",
    "CAPABILITY_TOOLS": [
        {"name": "query_graph", "description": "...", "inputSchema": {...}, ...},
        # ... 24 tools total
    ]
}
```

**Post-fix shape (read-merge step inserted before payload construction):**

```python
# MANIFEST-09/10: read existing capability.json, merge by tool name, last-write-wins
target = out_dir / "capability.json"
tmp = target.with_suffix(".tmp")
existing_tools: dict[str, Any] = {}
if target.exists():
    try:
        existing_tools = {
            t["name"]: t
            for t in json.loads(target.read_text(encoding="utf-8")).get("CAPABILITY_TOOLS", [])
            if isinstance(t, dict) and "name" in t
        }
    except (json.JSONDecodeError, OSError, KeyError):
        existing_tools = {}
incoming_tools = {t["name"]: t for t in data.get("CAPABILITY_TOOLS", []) if isinstance(t, dict) and "name" in t}
merged_tools = {**existing_tools, **incoming_tools}  # last-write-wins on tool name
merged_data = {**data, "CAPABILITY_TOOLS": list(merged_tools.values())}
payload = json.dumps(merged_data, indent=2, ensure_ascii=False, sort_keys=True) + "\n"
```

- Merge key: `tool["name"]` (string) — confirmed as unique identifier [VERIFIED: live introspection, 24 unique tool names]
- Conflict policy: last-write-wins (incoming run's tool entry replaces on-disk entry for same tool name)
- Note: In practice, `CAPABILITY_TOOLS` is derived from the same introspected MCP registry on every run — the merge is always idempotent. The fix matters only when the tool set genuinely changes between runs (extension installed between two subpath runs).
- Top-level keys (`manifest_version`, `graphify_version`) are taken from `data` (incoming run), not merged with on-disk values.

---

## Reference Implementations (Already Compliant — DO NOT Modify)

### Reference 1: `vault_promote._load_manifest` / `_save_manifest`

**File:** `graphify/vault_promote.py`
**Lines:** 651-682 [VERIFIED: codebase read]

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

**Row identity:** `path` (dict key) — dict is `{note_path_str: sha256_hex}`
**Merge site:** Callers (`promote()`, `apply_merge_plan()`) pass in a freshly-built manifest already incorporating prior state — the writer itself does NOT read; reading is done upstream.
**Subpath isolation status:** Compliant — callers load existing manifest with `_load_manifest()` before building new state.

### Reference 2: `seed._load_seeds_manifest` / `_save_seeds_manifest`

**File:** `graphify/seed.py`
**Lines:** 96-131 [VERIFIED: codebase read]

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
        print("[graphify] seeds-manifest.json corrupted or unreadable — treating all seeds as new",
              file=sys.stderr)
        return []

def _save_seeds_manifest(entries: list[dict], graphify_out: Path) -> None:
    """Write seeds-manifest.json atomically as the FINAL step of build_all_seeds."""
    manifest_path = graphify_out / "seeds" / "seeds-manifest.json"
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    tmp = manifest_path.with_suffix(".json.tmp")
    try:
        with open(tmp, "w", encoding="utf-8") as fh:
            fh.write(json.dumps(entries, indent=2, ensure_ascii=False))
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

**Row identity:** `seed_id` — callers deduplicate by `seed_id` before calling `_save_seeds_manifest`
**Subpath isolation status:** Compliant

---

## AUDIT.md Content Specification

Location: `.planning/phases/24-manifest-writer-audit-atomic-read-merge-write-hardening/AUDIT.md`

**Required preamble (1 paragraph):** Explain that every on-disk manifest writer in graphify must follow the read-merge-write contract: (1) read existing file, returning `{}` or `[]` on missing/corrupt; (2) merge new-run rows on top of existing rows keyed by row identity, last-write-wins on conflict; (3) write to `.tmp` then `os.replace`. Document D-08 migration policy: pre-v1.6 manifests missing sibling rows are authoritative; users recover by re-running on the missing subpaths.

**Table (D-06 columns):**

| manifest filename | writer (file:function:line) | invocation site | row identity key | pre-fix read? | pre-fix atomic? | post-fix read? | post-fix atomic? | Phase 24 action |
|---|---|---|---|---|---|---|---|---|
| `vault-manifest.json` | `vault_promote.py:_save_manifest:665` | `vault_promote.promote()` + `merge.apply_merge_plan()` | `path` (note path, dict key) | YES (caller loads via `_load_manifest`) | YES (`.tmp` + `os.replace` + `fsync`) | YES | YES | LOCKED — already compliant |
| `seeds-manifest.json` | `seed.py:_save_seeds_manifest:114` | `seed.build_all_seeds()` | `seed_id` (caller deduplicates) | YES (caller loads via `_load_seeds_manifest`) | YES (`.tmp` + `os.replace` + `fsync`) | YES | YES | LOCKED — already compliant |
| `routing.json` | `routing_audit.py:RoutingAudit.flush:34` | `pipeline.py:run()` | file path (dict key in `files`) | NO (blind overwrite of `self._files`) | YES (`.tmp` + `os.replace`) | YES | YES | PATCHED — Phase 24 adds read-merge step |
| `capability.json` | `capability.py:write_manifest_atomic:225` | `export.py:to_json():304` via `write_runtime_manifest` | tool name (`entry["name"]`) | NO (blind overwrite) | YES (`.tmp` + `os.replace`) | YES | YES | PATCHED — Phase 24 adds read-merge step |
| `graphify-out/manifest.json` | `detect.py:save_manifest:447` | `detect.py:detect_incremental():467` (not wired to any active CLI) | file path (dict key) | NO | NO (direct `write_text`) | NO | NO | DEFERRED — unreachable; fix belongs in phase that wires `detect_incremental` to CLI |

---

## Test Surface — Exact Patterns

### Existing test infrastructure confirmed [VERIFIED: codebase read]

- `tests/test_routing_sidecar.py` — EXISTS, covers `RoutingAudit.flush` atomicity. Header: `"""Tests for routing.json audit (ROUTE-05)."""`. Uses `monkeypatch.chdir(tmp_path)` because `flush()` validates path relative to `cwd`.
- `tests/test_capability.py` — EXISTS, covers `write_manifest_atomic` and `write_runtime_manifest`. Uses `tmp_path` directly (no chdir needed).
- `tests/test_vault_promote.py` — EXISTS, covers `_save_manifest` / `_load_manifest` roundtrip at line 411 (`test_vault05_manifest_roundtrip`). Multi-run patterns at lines 664-760.
- `tests/test_routing_audit.py` — DOES NOT EXIST. Must be created. Will be the new home for subpath isolation test for `routing.json`.

### Test 1: `test_subpath_isolation_vault_manifest` (add to `tests/test_vault_promote.py`)

This test locks the **existing** contract — no code change to the writer. Pattern mirrors `test_vault05_manifest_roundtrip` but uses two sequential calls.

```python
def test_subpath_isolation_vault_manifest(tmp_path):
    """MANIFEST-11: two sequential _save_manifest calls with disjoint path sets preserve union."""
    from graphify.vault_promote import _save_manifest, _load_manifest

    graphify_out = tmp_path / "graphify-out"
    graphify_out.mkdir()

    # Simulate subpath A run: load existing (empty), merge new rows, save
    existing = _load_manifest(graphify_out)
    existing.update({"Atlas/Dots/sub_a/NoteA.md": "hash_a1"})
    _save_manifest(existing, graphify_out)

    # Simulate subpath B run: load existing (has sub_a rows), merge new rows, save
    existing2 = _load_manifest(graphify_out)
    existing2.update({"Atlas/Dots/sub_b/NoteB.md": "hash_b1"})
    _save_manifest(existing2, graphify_out)

    final = _load_manifest(graphify_out)
    assert "Atlas/Dots/sub_a/NoteA.md" in final, "sub_a row must survive sub_b write"
    assert "Atlas/Dots/sub_b/NoteB.md" in final, "sub_b row must be present"
```

### Test 2: `test_subpath_isolation_routing` (new file `tests/test_routing_audit.py`)

```python
"""Tests for routing.json atomic read-merge-write (MANIFEST-09/11)."""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from graphify.routing_audit import RoutingAudit


def test_subpath_isolation_routing(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """MANIFEST-11: two sequential flush() calls with disjoint file sets preserve union."""
    monkeypatch.chdir(tmp_path)
    out = tmp_path / "graphify-out"

    # Subpath A run
    audit_a = RoutingAudit()
    audit_a.record(Path("sub_a/file1.py"), "simple", "haiku", "ep", 100, 10.0)
    audit_a.flush(out)

    # Subpath B run — different RoutingAudit instance, disjoint file set
    audit_b = RoutingAudit()
    audit_b.record(Path("sub_b/file2.py"), "complex", "sonnet", "ep2", 500, 50.0)
    audit_b.flush(out)

    data = json.loads((out / "routing.json").read_text(encoding="utf-8"))
    assert "sub_a/file1.py" in data["files"], "sub_a row must survive sub_b flush"
    assert "sub_b/file2.py" in data["files"], "sub_b row must be present"
```

### Test 3: `test_subpath_isolation_capability_manifest` (add to `tests/test_capability.py`)

```python
def test_subpath_isolation_capability_manifest(tmp_path: Path) -> None:
    """MANIFEST-11: two sequential write_manifest_atomic() calls with disjoint tool sets preserve union."""
    from graphify.capability import write_manifest_atomic

    data_a = {
        "manifest_version": "1",
        "graphify_version": "test",
        "CAPABILITY_TOOLS": [{"name": "tool_alpha", "description": "a", "inputSchema": {}}],
    }
    data_b = {
        "manifest_version": "1",
        "graphify_version": "test",
        "CAPABILITY_TOOLS": [{"name": "tool_beta", "description": "b", "inputSchema": {}}],
    }
    write_manifest_atomic(tmp_path, data_a)
    write_manifest_atomic(tmp_path, data_b)

    result = json.loads((tmp_path / "capability.json").read_text(encoding="utf-8"))
    names = {t["name"] for t in result["CAPABILITY_TOOLS"]}
    assert "tool_alpha" in names, "tool_alpha (sub_a run) must survive sub_b write"
    assert "tool_beta" in names, "tool_beta (sub_b run) must be present"
```

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Atomic file write | Custom lock-file or rename chain | `os.replace()` already in codebase | `os.replace` is POSIX-atomic; already used consistently in all 4 writers |
| Corrupt-file recovery | Silent swallow or crash | Try/except returning `{}`/`[]` with stderr warning | Pattern already in `_load_manifest` and `_load_seeds_manifest`; consistent UX |
| Dict merge | Custom deep-merge | `{**existing, **incoming}` shallow merge | Row identity is top-level key; no nested merging needed for routing or vault-manifest; capability tools are flat entries |

---

## Common Pitfalls

### Pitfall 1: Defining `dest` after the merge block in `routing_audit.flush`
**What goes wrong:** The read-merge step needs `dest` to check if the file exists, but the current code defines `dest` inside the write block. If you insert the read step without moving `dest` up, you get a `NameError`.
**Prevention:** Move `dest = out_dir / "routing.json"` to immediately after `out_dir.mkdir(...)`.

### Pitfall 2: `tmp` suffix collision in `routing_audit.flush`
**What goes wrong:** The current code uses `dest.with_suffix(".json.tmp")`. If `dest` is `routing.json`, this produces `routing.json.tmp`. The read step opens `dest` (not `tmp`), so there is no collision. But if the read step is accidentally pointed at `tmp`, it silently reads stale state.
**Prevention:** Always read from `dest`, write to `tmp`, replace `dest` with `tmp` — same as current pattern.

### Pitfall 3: `CAPABILITY_TOOLS` ordering after merge
**What goes wrong:** After merging tool dicts, `list(merged_tools.values())` order is insertion order of `{**existing, **incoming}`. This may differ from the introspected order in `build_manifest_dict()`. `sort_keys=True` in `json.dumps` sorts the JSON object keys but NOT the `CAPABILITY_TOOLS` array order.
**Prevention:** This is acceptable per D-03 (last-write-wins, no ordering contract on the list). The schema validator (`validate_manifest`) does not assert list order. If ordering becomes a requirement, sort by `t["name"]` before serialising — but this is NOT required by Phase 24.

### Pitfall 4: `write_manifest_atomic` receives already-validated data; merge bypasses schema validation
**What goes wrong:** `write_runtime_manifest` calls `validate_manifest(data)` BEFORE calling `write_manifest_atomic`. After the merge step, `merged_data` is written without re-validation. An on-disk capability.json written by a previous graphify version with a different schema could introduce corrupt entries.
**Prevention:** Gracefully skip corrupt on-disk entries in the merge step (the `isinstance(t, dict) and "name" in t` guard in the comprehension handles this). Do not re-run `validate_manifest` on the merged dict inside `write_manifest_atomic` — that would break the existing test `test_atomic_manifest_roundtrip` which passes a minimal dict without all schema-required fields.

### Pitfall 5: `RoutingAudit.flush` path confinement check — `dest` must be defined before the check
**What goes wrong:** Current code does `out_dir.relative_to(cwd)` path confinement check early. The `dest` variable is only used after that check. Moving `dest` up (for the read step) before the confinement check is safe — `dest` is just a `Path` object, no I/O.
**Prevention:** Define `dest = out_dir / "routing.json"` after `out_dir.mkdir()` but before the read-merge block. The confinement check uses `out_dir`, not `dest`.

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| `manifest.json` as capability writer target | `capability.json` (renamed) | quick-260422-jdj (2026-04-22) | Eliminates path collision with `detect.py`'s incremental mtime manifest at `graphify-out/manifest.json` |
| Blind overwrite in `routing_audit.flush` | Read-merge-write (Phase 24) | Phase 24 | Subpath runs no longer erase prior routing records |
| Blind overwrite in `write_manifest_atomic` | Read-merge-write (Phase 24) | Phase 24 | Subpath runs no longer erase prior capability tool entries |
| `vault_promote._save_manifest` blind overwrite (pre-v1.0) | Read-merge at caller site (Phase 5+) | Phase 5 (v1.0) | Already compliant — merge happens before save |

**Deprecated/outdated:**
- Calling `write_manifest_atomic` with a blind overwrite assumption — callers do not need to change (merge now happens inside the writer).

---

## Environment Availability

Step 2.6: SKIPPED — no external dependencies. All changes are pure Python stdlib on an already-installed codebase.

---

## Validation Architecture

### Test Framework

| Property | Value |
|----------|-------|
| Framework | pytest (project-pinned) |
| Config file | none detected (pyproject.toml `[tool.pytest.ini_options]` absent) |
| Quick run command | `pytest tests/test_routing_audit.py tests/test_capability.py tests/test_vault_promote.py -q` |
| Full suite command | `pytest tests/ -q` |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| MANIFEST-09 | subpath run does not erase sibling rows | unit | `pytest tests/test_routing_audit.py::test_subpath_isolation_routing tests/test_capability.py::test_subpath_isolation_capability_manifest -x` | ❌ Wave 0 (routing_audit), test added to existing (capability) |
| MANIFEST-10 | all writers use read-merge-write + atomic | unit (code review) | `pytest tests/ -q` (all existing writer tests + new) | partial — existing atomic tests pass; read-merge tests new |
| MANIFEST-11 | two sequential subpath runs → union in manifest | unit | `pytest tests/test_routing_audit.py::test_subpath_isolation_routing tests/test_capability.py::test_subpath_isolation_capability_manifest tests/test_vault_promote.py::test_subpath_isolation_vault_manifest -x` | ❌ Wave 0 (all 3 new test functions) |
| MANIFEST-12 | AUDIT.md exists and enumerates all writers | manual inspection | n/a — artifact, not code | ❌ Wave 0 (file must be created) |

### Sampling Rate

- **Per task commit:** `pytest tests/test_routing_audit.py tests/test_capability.py tests/test_vault_promote.py -q`
- **Per wave merge:** `pytest tests/ -q`
- **Phase gate:** Full suite green before `/gsd-verify-work`

### Wave 0 Gaps

- [ ] `tests/test_routing_audit.py` — new file, covers MANIFEST-09/11 for routing.json
- [ ] `tests/test_capability.py::test_subpath_isolation_capability_manifest` — new function in existing file, covers MANIFEST-09/11 for capability.json
- [ ] `tests/test_vault_promote.py::test_subpath_isolation_vault_manifest` — new function in existing file, locks existing MANIFEST-11 contract
- [ ] `.planning/phases/24-.../AUDIT.md` — MANIFEST-12 artifact

---

## Security Domain

> `security_enforcement` not explicitly disabled; included per default.

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | no | — |
| V3 Session Management | no | — |
| V4 Access Control | no | — |
| V5 Input Validation | yes (path confinement) | `out_dir.relative_to(cwd)` check already in `routing_audit.flush`; `.tmp` path derived from `dest`, never from user input |
| V6 Cryptography | no | — |

### Known Threat Patterns for manifest I/O

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| Path traversal via `out_dir` | Tampering | Existing `out_dir.relative_to(cwd)` check in `routing_audit.flush` — no change needed |
| Corrupt on-disk manifest → crash | Denial of Service | Try/except returning `{}` on `JSONDecodeError` / `OSError` — mirrors `_load_manifest` pattern |
| `.tmp` file left behind on crash | Tampering | `except` block calls `tmp.unlink(missing_ok=True)` — already present in current writers |

No new security surface introduced. The read step reads only from `dest` (the exact path being written), which is already under path confinement.

---

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | `CAPABILITY_TOOLS` list order after merge is acceptable (no order contract) | Code Under Change — Writer 2 | If downstream tooling (e.g. MCP client) depends on stable list order, tests could pass but runtime behavior could differ. Low risk: schema validator does not assert order. | [ASSUMED] |
| A2 | `write_runtime_manifest` at `capability.py:245` is the only public entry point that calls `write_manifest_atomic` in production use | Code Under Change — Writer 2 | If other callers exist that pass non-standard `data` shapes, the merge step's `data.get("CAPABILITY_TOOLS", [])` access could produce an empty merge. Verified via grep: only `export.py:304` calls `write_runtime_manifest`. [VERIFIED: codebase grep] | — |

---

## Open Questions

1. **Should `os.fsync` be added to the routing and capability writers after the patch?**
   - What we know: `vault_promote._save_manifest` uses `fsync` for extra durability; `routing_audit.flush` and `write_manifest_atomic` currently do not.
   - What's unclear: Whether the project requires fsync consistency across all writers.
   - Recommendation: Do NOT add fsync to the patched writers — matching current behavior per writer, not the reference. If fsync consistency is required, that is a separate hardening task. Planner can add a discretionary note.

2. **Should `test_routing_audit.py` absorb the two existing tests from `test_routing_sidecar.py`?**
   - What we know: `test_routing_sidecar.py` already exists with 2 tests for `RoutingAudit.flush`. A new `test_routing_audit.py` is required per D-07.
   - What's unclear: Whether to move existing tests or add a second file.
   - Recommendation: Create `tests/test_routing_audit.py` as a NEW file with only the new `test_subpath_isolation_routing` test. Leave `test_routing_sidecar.py` untouched. Avoids moving tests and breaking any tooling.

---

## Sources

### Primary (HIGH confidence)
- `graphify/routing_audit.py:34-56` — verbatim read from codebase [VERIFIED: codebase read]
- `graphify/capability.py:225-241` — verbatim read from codebase [VERIFIED: codebase read]
- `graphify/vault_promote.py:651-682` — verbatim read from codebase [VERIFIED: codebase read]
- `graphify/seed.py:96-131` — verbatim read from codebase [VERIFIED: codebase read]
- `graphify/merge.py:1085-1100` — verbatim read from codebase [VERIFIED: codebase read]
- `graphify/detect.py:447-465` — verbatim read from codebase [VERIFIED: codebase read]
- `graphify/capability.py:174-200` — `build_manifest_dict()` shape [VERIFIED: codebase read + live introspection]
- Live introspection of `build_manifest_dict()` — 24 tools, top-level keys confirmed [VERIFIED: live Python execution]
- Live introspection of `RoutingAudit.flush` output — `files` dict key shape confirmed [VERIFIED: live Python execution]
- `.planning/phases/24-.../24-CONTEXT.md` — all locked decisions [VERIFIED: codebase read]
- `.planning/REQUIREMENTS.md` — MANIFEST-09/10/11/12 acceptance text [VERIFIED: codebase read]

### Secondary (MEDIUM confidence)
- `tests/test_routing_sidecar.py`, `tests/test_capability.py`, `tests/test_vault_promote.py` — test convention patterns [VERIFIED: codebase read]
- `tests/test_merge.py` header + function list — test naming conventions [VERIFIED: codebase read]

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — stdlib only, no new deps
- Architecture: HIGH — writers read directly, patterns confirmed from live code
- Code excerpts: HIGH — verbatim from codebase reads at exact cited lines
- Pitfalls: HIGH — derived from actual code reading, not training data
- Test patterns: HIGH — verified from existing test files

**Research date:** 2026-04-27
**Valid until:** 2026-05-27 (stable internal codebase; no external dependencies)
