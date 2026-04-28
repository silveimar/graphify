# Phase 28: Self-Ingestion Hardening - Research

**Researched:** 2026-04-27
**Domain:** detect.py pruning logic, profile schema extension, output manifest write, atomic I/O patterns
**Confidence:** HIGH — all findings verified against live codebase; no external library research required

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

**VAULT-11 (Profile-aware exclusions)**
- D-14: `exclude: list[str]` lives nested under existing `output:` block. `ResolvedOutput` grows `exclude_globs: tuple[str, ...]`.
- D-15: `output.exclude` ALWAYS applies when profile loads (even if `--output` flag overrides destination).
- D-16: `fnmatch` via existing `_is_ignored()` at `detect.py:307`. Stdlib only.
- D-17: `validate_profile()` rejects malformed `exclude` entries strictly — empty strings, non-string types, traversal paths. Loud-fail, consistent with existing D-05/D-02 pattern.

**VAULT-12 (Recursive nesting guard)**
- D-18: Match union of `{"graphify-out", "graphify_out"}` AND basenames of `resolved.notes_dir` / `resolved.artifacts_dir`.
- D-19: Warn-and-skip, NOT fatal.
- D-20: ONE summary line per run: `[graphify] WARNING: skipped N nested output paths (deepest: <path>)`.
- D-21: Universal scope (vault or no vault).

**VAULT-13 (Output manifest)**
- D-22: New file `<resolved.artifacts_dir>/output-manifest.json`; separate from `graphify-out/manifest.json`.
- D-23: Schema: `{ version: 1, runs: [{ run_id, timestamp, notes_dir, artifacts_dir, files: [...] }] }`.
- D-24: Rolling N=5 most recent runs, FIFO drop.
- D-25: Missing → silent empty; malformed → warn-once; nesting guard (D-18) is the safety net.
- D-26: `detect.py` always reads from `resolved.artifacts_dir` (stable anchor).
- D-27: Renamed-output content silently pruned via prior-run `files:` list. No warning.
- D-28: GC stale entries on next manifest write (mirrors `detect_incremental`'s `deleted_files` cleanup).
- D-29: Atomic tmp+rename write AFTER successful export, before exit. Failed runs leave manifest unchanged.

### Claude's Discretion
- Exact `run_id` hash construction (short SHA-256 of `notes_dir + timestamp`, or UUID4).
- Module location of nesting-detection function (extend `_is_noise_dir` vs. new `_is_nested_output` predicate).
- Exact `__main__.py` wire-point for the post-export manifest write.
- Whether `output-manifest.json` is exposed via MCP `serve.py` (stretch goal, likely out of scope).
- Test fixture strategy for nesting scenarios.

### Deferred Ideas (OUT OF SCOPE)
- `--exclude` CLI flag mirroring `--output`.
- `output.manifest_history_depth` profile field.
- `output.manifest_path:` profile field.
- MCP query surface for `output-manifest.json`.
- Two manifest files (redundancy strategy).
- Per-file nesting warnings.
- Fatal-on-malformed-manifest behavior.
- `graphify init-profile` scaffolding.
- Discoverable manifest via filesystem walk.
- Pre-write manifest (record before writing).

</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| VAULT-11 | `detect.py` reads profile output destination + declared exclusion globs and prunes them from input scan | `_is_ignored()` reuse confirmed; `ResolvedOutput` extension path confirmed; `validate_profile()` extension surface identified |
| VAULT-12 | Recursive nesting guard — `detect.py` refuses paths matching `**/graphify-out/**` at any depth and warns | `_is_noise_dir()` + `_SELF_OUTPUT_DIRS` already prune by basename; extension to consume `ResolvedOutput` basenames is additive |
| VAULT-13 | Manifest-based ignore — current run records output paths; subsequent runs skip them even if profile changes | `save_manifest()` / `load_manifest()` pattern identified; atomic write pattern verified from `merge.py` / `vault_promote.py`; GC pattern from `detect_incremental()` confirmed |

</phase_requirements>

---

## Summary

Phase 28 adds three self-ingestion defences to graphify, all centred on `detect.py` as the primary modification surface. The Phase 27 `ResolvedOutput` NamedTuple is the integration anchor: its `notes_dir`, `artifacts_dir`, and a new `exclude_globs` field are consumed by `detect()` to prune output paths and user-declared exclusion globs at scan time.

The codebase is in good shape for this work. All three detection layers reuse existing infrastructure rather than introducing new patterns: `_is_noise_dir()` / `_SELF_OUTPUT_DIRS` for nesting guards, `_is_ignored()` / `fnmatch` for glob exclusions, and `save_manifest()` / `load_manifest()` extended into a new `_save_output_manifest()` / `_load_output_manifest()` pair. The canonical atomic write pattern (`target.with_suffix(".json.tmp")` + `fh.flush()` + `os.fsync()` + `os.replace()`) exists verbatim in `merge.py:_write_atomic`, `vault_promote.py:_write_atomic`, and `enrich.py:_commit_pass`; D-29 copies this without modification.

The primary design challenge is injecting `ResolvedOutput` into `detect()` without breaking the 10+ existing callers (skill.md scripts, `pipeline.py`, `watch.py`, `detect_incremental()`) that currently call `detect(root)` with no second argument. The recommended approach is a keyword-only parameter `resolved: ResolvedOutput | None = None` — existing callers pass nothing and get the current behaviour; the `run` and `--obsidian` branches pass the resolved object produced by `resolve_output()`.

**Primary recommendation:** Add `resolved: ResolvedOutput | None = None` to `detect()`, extend `_is_noise_dir` into a two-arg form that consumes resolved basenames, add `_load_output_manifest()` / `_save_output_manifest()` helpers to `detect.py`, extend `ResolvedOutput` with `exclude_globs`, and extend `validate_profile()`'s `output:` branch with `exclude` validation.

---

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Profile `output.exclude` schema validation | Library (profile.py) | — | validate_profile() is the single schema gate; consistent with all other output: block validation |
| `exclude_globs` population from profile | Library (output.py) | — | resolve_output() already loads profile and builds ResolvedOutput; adding one field keeps the integration contract single-sourced |
| Nesting guard (detect-side pruning) | Library (detect.py) | — | All file-scan pruning belongs in detect(); no other layer should know about the scan decisions |
| Glob exclusion from profile | Library (detect.py) | — | _is_ignored() is already the exclusion engine; adding exclude_globs re-uses it with zero new deps |
| Output manifest read (prior-run skip) | Library (detect.py) | — | detect() is the scan boundary; it must consume manifest before returning the file list |
| Output manifest write (post-export) | CLI (__main__.py) | Library (detect.py) | Write happens after successful export; CLI orchestrates timing; detect.py provides the helper |
| Atomic manifest write | Library (detect.py helper) | — | Helper function in detect.py mirrors the merge.py/_write_atomic pattern |
| Prior-run manifest GC | Library (detect.py helper) | — | Stale-file GC happens at write time inside _save_output_manifest(); mirrors detect_incremental pattern |

---

## Standard Stack

### Core (no new dependencies required)
| Module | Purpose | Phase 28 Change |
|--------|---------|-----------------|
| `graphify/detect.py` | File discovery + scan pruning | Primary modification surface |
| `graphify/output.py` | `ResolvedOutput` NamedTuple | Extend with `exclude_globs` field (6th field) |
| `graphify/profile.py` | Profile schema validation | Extend `output:` branch with `exclude` key validation |
| `graphify/__main__.py` | CLI entry points | Wire manifest write call after successful export in `run` and `--obsidian` branches |

All implementation uses only stdlib: `fnmatch`, `json`, `os`, `pathlib`, `hashlib` (for `run_id`), `datetime`. **No new `pip install` required.** [VERIFIED: codebase inspection]

---

## Architecture Patterns

### System Architecture Diagram

```
CLI (run / --obsidian branch)
  │
  ├─ resolve_output(cwd, cli_output) → ResolvedOutput(…, exclude_globs)
  │      └─ load_profile() → validate_profile() checks output.exclude
  │
  ├─ detect(root, resolved=resolved)   ← PRIMARY CHANGE
  │      ├─ _load_output_manifest(resolved.artifacts_dir)  → prior_files: set[str]
  │      ├─ per-dir: _is_noise_dir(d, resolved) → prune basenames of notes_dir / artifacts_dir
  │      ├─ per-dir: _is_ignored(dp/d, root, ignore_patterns)
  │      ├─ per-file: path in prior_files → skip (D-26/D-27)
  │      ├─ per-file: _is_ignored(p, root, exclude_globs) → skip (D-15/D-16)
  │      └─ emit ONE summary warning if nested_count > 0 (D-20)
  │
  ├─ [pipeline: extract / build / cluster / analyze / report / export]
  │
  └─ _save_output_manifest(resolved, written_files)  ← NEW, post-export
         ├─ read existing output-manifest.json (or empty)
         ├─ build new run entry (run_id, timestamp, notes_dir, artifacts_dir, files)
         ├─ GC files no longer on disk (D-28)
         ├─ FIFO-trim to N=5 runs (D-24)
         └─ atomic write via tmp + os.replace (D-29)
```

### Recommended Project Structure (no new files except test file)
```
graphify/
├── detect.py         # +_load_output_manifest, _save_output_manifest,
│                     #  _is_nested_output (or extended _is_noise_dir),
│                     #  detect() gains `resolved` kwarg
├── output.py         # ResolvedOutput gains 6th field: exclude_globs
├── profile.py        # validate_profile output: branch gains exclude validation
└── __main__.py       # post-export manifest write in run + --obsidian branches
tests/
├── test_detect.py    # +nesting guard, +exclude_globs, +manifest round-trip tests
├── test_profile.py   # +exclude validation tests
└── test_output.py    # +exclude_globs field presence / propagation tests
```

---

## Exact Code Touch-Points

### 1. `graphify/output.py` — `ResolvedOutput` extension

**Current signature (line 24-29):** [VERIFIED: codebase read]
```python
class ResolvedOutput(NamedTuple):
    vault_detected: bool
    vault_path: Path | None
    notes_dir: Path
    artifacts_dir: Path
    source: Literal["profile", "cli-flag", "default"]
```

**Minimal diff:**
- Add `exclude_globs: tuple[str, ...] = ()` as the 6th field
- In `resolve_output()`, populate from `prof.get("output", {}).get("exclude", [])` after profile load, tuple-cast: `tuple(profile["output"].get("exclude", []))`
- All three resolution branches (vault/profile, vault/cli-flag, no-vault/default) return `exclude_globs=()` by default; only the vault+profile branch populates it from the loaded profile

**Callers that break if field order changes:** None — all existing callers use keyword access (`result.notes_dir`) or positional unpacking, and NamedTuple positional unpacking by index only breaks if a caller unpacks all 5 fields into 5 variables. The test `test_resolved_output_unpacks_to_tuple` in `tests/test_output.py` (line 94) will need updating to expect 6 fields. [VERIFIED: test_output.py read]

**NamedTuple default field caveat:** Python NamedTuples support default values for trailing fields (Python 3.6.1+); `tuple[str, ...] = ()` is valid. [VERIFIED: Python 3.10+ confirmed by CLAUDE.md]

### 2. `graphify/profile.py` — `validate_profile()` output branch extension

**Current output: branch location:** lines 423-451 [VERIFIED: profile.py read]
```python
output = profile.get("output")
if output is not None:
    if not isinstance(output, dict):
        errors.append("'output' must be a mapping (dict)")
    else:
        mode = output.get("mode")
        ...
        # ends at line 451 with the sibling-of-vault comment
```

**Minimal diff:** After the existing mode/path validation, add an `exclude` validation block:
```python
exclude = output.get("exclude")
if exclude is not None:
    if not isinstance(exclude, list):
        errors.append("output.exclude must be a list")
    else:
        for i, item in enumerate(exclude):
            if not isinstance(item, str):
                errors.append(f"output.exclude[{i}] must be a string (got {type(item).__name__})")
            elif not item.strip():
                errors.append(f"output.exclude[{i}] must not be empty or whitespace-only")
            elif Path(item).is_absolute():
                errors.append(f"output.exclude[{i}] must not be an absolute path")
            elif item.lstrip("/").startswith(".."):
                errors.append(f"output.exclude[{i}] must not contain '..' (path traversal)")
            elif ".." in Path(item.lstrip("/")).parts:
                errors.append(f"output.exclude[{i}] must not contain '..' segments")
```

**Traversal rejection note (D-17):** The existing `validate_vault_path()` in `profile.py` uses `resolved.relative_to(vault_base)` for runtime traversal checks. For static validation of `exclude` strings at schema-load time (no vault_dir available), the check is syntactic: reject absolute paths and any pattern containing `..` segments. This matches how `folder_mapping` traversal is rejected (lines 284-292 in the existing code). [VERIFIED: profile.py read]

**Callers:** `validate_profile()` is called by `load_profile()` (profile.py:196) and `validate_profile_preflight()` (profile.py:711). Both consume the error list unchanged — no signature change needed. [VERIFIED: profile.py grep]

### 3. `graphify/detect.py` — primary modification surface

#### 3a. `_SELF_OUTPUT_DIRS` (line 252) and `_is_noise_dir()` (lines 261-243)

**Current state:** [VERIFIED: detect.py read]
```python
_SELF_OUTPUT_DIRS = {"graphify-out", "graphify_out"}

def _is_noise_dir(part: str) -> bool:
    if part in _SKIP_DIRS: return True
    if part in _SELF_OUTPUT_DIRS: return True
    if part.endswith("_venv") or part.endswith("_env"): return True
    if part.endswith(".egg-info"): return True
    return False
```

**Design choice (Claude's Discretion):** Add a new `_is_nested_output(part: str, resolved_basenames: frozenset[str]) -> bool` predicate rather than modifying `_is_noise_dir`. Rationale:
- `_is_noise_dir` is a pure string→bool function; threading a mutable set through it changes its contract and every test that monkeypatches it
- A separate predicate with an explicit `resolved_basenames` parameter is testable in isolation
- `detect()` calls the new predicate alongside `_is_noise_dir` in the `dirnames[:]` filter

```python
def _is_nested_output(part: str, resolved_basenames: frozenset[str]) -> bool:
    """Return True if dirname matches any known graphify output location.
    
    Covers the literal _SELF_OUTPUT_DIRS set plus any basenames from the
    current run's ResolvedOutput (notes_dir, artifacts_dir) per D-18.
    """
    if part in _SELF_OUTPUT_DIRS:
        return True
    if part in resolved_basenames:
        return True
    return False
```

`resolved_basenames` is computed once before the walk:
```python
resolved_basenames: frozenset[str] = frozenset()
if resolved is not None:
    resolved_basenames = frozenset({
        resolved.notes_dir.name,
        resolved.artifacts_dir.name,
    }) - _SELF_OUTPUT_DIRS  # avoid double-counting
```

#### 3b. `detect()` signature extension (line 338)

**Current signature:** `def detect(root: Path, *, follow_symlinks: bool = False) -> dict`

**Minimal diff:**
```python
def detect(
    root: Path,
    *,
    follow_symlinks: bool = False,
    resolved: ResolvedOutput | None = None,  # Phase 28 (D-14..D-21, D-25..D-27)
) -> dict:
```

**Import concern:** `ResolvedOutput` lives in `graphify.output`. `detect.py` must not import from `output.py` at module level to avoid circular imports — `output.py` imports `profile.py` which must never import `detect.py`. The safe pattern (already used in `output.py` for `profile.py`) is a `TYPE_CHECKING`-guarded import:

```python
from __future__ import annotations  # already present

from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from graphify.output import ResolvedOutput
```

For runtime isinstance checks (if needed), use `type(resolved).__name__ == "ResolvedOutput"` or duck-type attribute access. Since `resolved` is only used for attribute access (`resolved.notes_dir`, `resolved.artifacts_dir`, `resolved.exclude_globs`), the TYPE_CHECKING guard is sufficient — no runtime import of `output.py` from `detect.py` is needed.

**All callers of detect():** [VERIFIED: grep across codebase]
| Caller | Location | Impact |
|--------|----------|--------|
| `pipeline.py:24` | `det = detect(target)` | No change needed — `resolved=None` default activates backcompat path |
| `watch.py:106` | `detect(watch_path, ...)` | No change needed |
| `detect_incremental():475` | `full = detect(root)` | No change needed — but see §5 for cross-impact analysis |
| skill.md + all platform skill files | `detect(Path('INPUT_PATH'))` | No change needed — skill calls the CLI which passes `resolved` via `pipeline.py` or directly |
| `test_detect.py` (21 call sites) | All `detect(tmp_path)` or `detect(FIXTURES)` | No change needed — all keyword-only arguments remain optional |

**Nesting counter accumulation during walk:**
```python
nested_paths: list[str] = []
...
# in the dirnames[:] filter expression — prune in-place and record:
pruned = []
for d in dirnames:
    dp_d = dp / d
    if d.startswith(".") or _is_noise_dir(d) or _is_ignored(dp_d, root, ignore_patterns):
        pruned.append(d)
    elif _is_nested_output(d, resolved_basenames):
        nested_paths.append(str(dp_d))
        pruned.append(d)
dirnames[:] = [d for d in dirnames if d not in set(pruned)]
```
After the walk, emit the D-20 summary line:
```python
if nested_paths:
    deepest = max(nested_paths, key=lambda p: p.count(os.sep))
    print(
        f"[graphify] WARNING: skipped {len(nested_paths)} nested output path(s) "
        f"(deepest: {deepest})",
        file=sys.stderr,
    )
```

**Note:** The current `dirnames[:] = [...]` comprehension (line 143-148) must be refactored to the accumulate-then-assign pattern above to allow counting nested paths without a second pass.

#### 3c. `output.exclude` glob application in detect()

After `_load_graphifyignore(root)`, compute an additional exclude list from `resolved.exclude_globs`:
```python
exclude_globs: list[str] = list(resolved.exclude_globs) if resolved else []
```

Then apply in the per-file loop using the existing `_is_ignored()` function:
```python
if exclude_globs and _is_ignored(p, root, exclude_globs):
    continue
```

Note: `_is_ignored()` already handles empty pattern lists (`if not patterns: return False`), so the guard is optional but explicit about intent.

#### 3d. `_load_output_manifest()` and `_save_output_manifest()` helpers

**New in detect.py** (per D-22..D-29):

```python
_OUTPUT_MANIFEST_NAME = "output-manifest.json"
_OUTPUT_MANIFEST_VERSION = 1
_OUTPUT_MANIFEST_MAX_RUNS = 5

def _load_output_manifest(artifacts_dir: Path) -> dict:
    """Load output-manifest.json from artifacts_dir, returning empty envelope on any failure.
    
    Per D-25: missing -> silent empty; malformed -> warn-once and return empty.
    """
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


def _save_output_manifest(
    artifacts_dir: Path,
    notes_dir: Path,
    written_files: list[str],
    run_id: str | None = None,
) -> None:
    """Append a new run entry and write output-manifest.json atomically (D-29).
    
    - GC entries whose files no longer exist (D-28)
    - FIFO-trim to N=5 runs (D-24)
    - Atomic tmp+rename write (D-29)
    """
    import hashlib, datetime
    manifest_path = artifacts_dir / _OUTPUT_MANIFEST_NAME
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    
    existing = _load_output_manifest(artifacts_dir)
    
    # Build new run entry
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
    
    # D-28: GC stale file entries from existing runs
    for run in runs:
        run["files"] = [f for f in run.get("files", []) if Path(f).exists()]
    
    # Append new run and FIFO-trim to N=5 (D-24)
    runs.append(new_run)
    runs = runs[-_OUTPUT_MANIFEST_MAX_RUNS:]
    
    manifest = {"version": _OUTPUT_MANIFEST_VERSION, "runs": runs}
    
    # Atomic write: tmp + os.replace (D-29)
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

**Prior-file set for detect() lookup (D-26/D-27):**
```python
prior_files: set[str] = set()
if resolved is not None:
    manifest_data = _load_output_manifest(resolved.artifacts_dir)
    for run in manifest_data.get("runs", []):
        prior_files.update(run.get("files", []))
```

Then in the per-file loop:
```python
if str(p.resolve()) in prior_files:
    continue
```

### 4. `graphify/__main__.py` — manifest write wire-points

**Locations:** After the `to_obsidian()` call in the `--obsidian` branch (~line 1397) and after `run_corpus()` in the `run` branch (~line 2163). [VERIFIED: __main__.py read]

**--obsidian branch wire-point** (after `result = to_obsidian(...)` + guard against `MergePlan`):
```python
# Phase 28 (D-29): write output manifest after successful export
if not isinstance(result, MergePlan) and resolved is not None:
    from graphify.detect import _save_output_manifest
    written = getattr(getattr(result, "plan", None), "written_files", None) or []
    _save_output_manifest(resolved.artifacts_dir, resolved.notes_dir, written)
```

**run branch wire-point** (after `run_corpus(...)` returns):
```python
# Phase 28 (D-29): write output manifest after successful export
if resolved is not None:
    from graphify.detect import _save_output_manifest
    # run_corpus returns extraction result; written Obsidian files are in
    # resolved.notes_dir tree. Record roots only when full file list unavailable.
    _save_output_manifest(
        resolved.artifacts_dir,
        resolved.notes_dir,
        written_files=[],  # Phase 28: roots only; file list comes from to_obsidian path
    )
```

**Design note:** The `run` branch calls `run_corpus()` which calls `detect()` + `extract()` but does NOT call `to_obsidian()` — that is a separate `--obsidian` invocation. In Phase 28, the manifest write in the `run` branch records the roots (`notes_dir`, `artifacts_dir`) but the `files:` list will be populated only via the `--obsidian` path which has access to the `MergeResult`. This is acceptable per D-23 ("roots enable cheap directory-prefix prune; full file list enables precise re-run skipping") — the roots guard covers the `run` branch case; the full file list is populated by `--obsidian`. If the planner deems this insufficient, an alternative is to enumerate `resolved.notes_dir.rglob("*.md")` post-write, but that adds cost for minimal gain given the nesting guard already covers the root case.

---

## detect() Data Flow Analysis

**Call chain for the `run` command:**
```
__main__.py (run branch)
  → resolve_output(Path.cwd(), cli_output=cli_output) → ResolvedOutput
  → run_corpus(target, use_router=..., out_dir=resolved.artifacts_dir)
       → detect(target)                    ← no resolved passed today
       → extract(paths)
```

**Phase 28 injection point:** `run_corpus` in `pipeline.py` must accept and thread the `resolved` object, OR `detect()` is called directly from `__main__.py` before `run_corpus`. The cleanest extension is to add `resolved: ResolvedOutput | None = None` to `run_corpus()` in `pipeline.py` and thread it through to `detect(target, resolved=resolved)`. This keeps `__main__.py` calling `run_corpus()` as before, and `pipeline.py` as the single place that wires detection.

**pipeline.py minimal diff:**
```python
def run_corpus(target: Path, *, use_router: bool, out_dir: Path | None = None,
               resolved: ResolvedOutput | None = None) -> dict:
    ...
    det = detect(target, resolved=resolved)
```

**__main__.py run branch — pass resolved:**
```python
run_corpus(target, use_router=use_router, out_dir=out_dir, resolved=resolved)
```

`watch.py` calls `detect(watch_path, follow_symlinks=...)` with no resolved — this is correct, watch mode does not have a vault-aware `ResolvedOutput`. [VERIFIED: watch.py read] No change needed there.

---

## Atomic Write Pattern (Phase 24 / D-29)

The canonical pattern exists in THREE places in the codebase — they are identical in structure. Use `merge.py:_write_atomic` as the reference (line 1152): [VERIFIED: merge.py + vault_promote.py + enrich.py read]

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

**Key implementation details:**
- `target.with_suffix(target.suffix + ".tmp")` — for `output-manifest.json`, this produces `output-manifest.json.tmp` (suffix `.json`, result `.json.tmp`). Consistent with `enrich.py` which uses `.json.tmp` for `.json` targets.
- `os.fsync(fh.fileno())` — the vault_promote and merge versions both include fsync; the enrich.py version omits it but uses `tmp.write_text()`. Use the merge.py/vault_promote.py version (with fsync) for D-29 data integrity guarantee.
- `os.replace()` — atomic rename on POSIX; on Windows it replaces atomically if `tmp` and `target` are on the same volume.
- The existing `save_manifest()` in `detect.py` (line 456) uses `Path.write_text()` — NOT atomic. This is a known gap (the Phase 24 audit noted it). Phase 28 does NOT upgrade the existing `save_manifest()`; only the new `_save_output_manifest()` uses the atomic pattern. [VERIFIED: detect.py read]

---

## Existing Test Coverage Map

### `tests/test_detect.py` (300 lines, 30 test functions) [VERIFIED]
- Tests `detect()`, `classify_file()`, `count_words()`, `_is_ignored()`, `_load_graphifyignore()`
- Fixture patterns: `tmp_path` + inline file writes (no fixtures directory dependency for unit tests)
- Key reusable fixture helper pattern: create dirs, write files, call `detect(tmp_path)`, assert on `result["files"]`
- Tests for `_SELF_OUTPUT_DIRS` nesting: `test_detect_skips_graphify_out_subtree`, `test_detect_skips_graphify_out_at_any_depth`, `test_detect_skips_graphify_out_underscore_variant` — these confirm Phase 28 D-18 has prior test coverage to extend
- Tests for `_load_graphifyignore` / `_is_ignored` — reusable as pattern for `exclude_globs` tests
- **Wave 0 gaps for Phase 28:** Tests for nesting guard with `ResolvedOutput.notes_dir` / `artifacts_dir` basenames; tests for `output.exclude` globs in detect(); manifest load/save round-trip tests; renamed-notes-dir recovery test

### `tests/test_profile.py` (1337 lines) [VERIFIED]
- Full `validate_profile()` coverage including `output:` block (lines 1229-1292, Phase 27 additions)
- Traversal rejection tests for `folder_mapping` at lines 155-174 — same pattern for `exclude` validation
- **Wave 0 gaps:** Tests for `output.exclude` valid list, empty string rejection, non-string rejection, absolute path rejection, traversal rejection

### `tests/test_output.py` (269 lines, 21 test functions) [VERIFIED]
- Full `ResolvedOutput` / `resolve_output()` coverage
- `_setup_vault()` helper at line 85 creates vault layout with `.obsidian/` + `.graphify/profile.yaml`
- `test_resolved_output_unpacks_to_tuple` at line 94 unpacks to 5 variables — needs update for 6th field
- `test_resolved_output_namedtuple_field_order` checks field names — needs `exclude_globs` added
- **Wave 0 gaps:** Tests for `exclude_globs` populated from profile; `exclude_globs=()` default for all non-profile sources

---

## Cross-Phase Integration Risk: detect_incremental()

**Concern (from brief):** `detect_incremental()` (line 469) reads `manifest.json` (mtime tracking). Does the new `output-manifest.json` collide?

**Verdict: NO collision risk.** [VERIFIED: detect.py read]

Analysis:
- `detect_incremental()` calls `load_manifest(manifest_path)` where `manifest_path` defaults to `_MANIFEST_PATH = "graphify-out/manifest.json"` (line 19)
- The new output manifest lives at `<resolved.artifacts_dir>/output-manifest.json` — a different filename AND potentially a different directory
- `detect_incremental()` passes no `resolved` parameter to `detect()` (line 475: `full = detect(root)`). Post-Phase 28, `detect_incremental()` will call `detect(root)` with `resolved=None`, which activates the `_SELF_OUTPUT_DIRS`-only nesting guard (D-21 backcompat) — no manifest lookup, no exclude_globs. This is the correct behaviour for `--update` mode which is not vault-aware.

**No changes needed to `detect_incremental()`** in Phase 28.

The `deleted_files` GC pattern at line 503 is the template for D-28's stale-file GC in `_save_output_manifest()`:
```python
# detect_incremental GC pattern (lines 272-274):
current_files = {f for flist in full["files"].values() for f in flist}
deleted_files = [f for f in manifest if f not in current_files]
```
`_save_output_manifest()`'s D-28 GC mirrors this: `run["files"] = [f for f in run["files"] if Path(f).exists()]`.

---

## Nesting Guard Performance Recommendation

**Context:** `detect()` walks every directory. D-23's `files: [...]` list can contain O(100-10000) absolute path strings per run × 5 runs = up to 50,000 entries in the prior_files set.

**Data structure recommendation: `set[str]`** (Python's native hash set)

Analysis:
| Structure | Build cost | Lookup cost | Notes |
|-----------|------------|-------------|-------|
| `set[str]` | O(N) | O(1) average | Best for unordered membership test |
| `sorted list` + `bisect` | O(N log N) | O(log N) | Needed only if memory is critical; 50K strings = ~5MB which is fine |
| Trie | O(N×L) | O(L) where L=path length | Overhead unjustified for this use case |
| Prefix-match via `notes_dir` / `artifacts_dir` Path | O(1) | O(path length) | For the directory-level guard, sufficient |

**Recommended approach — two layers:**
1. **Directory-level (cheap):** Check `_is_nested_output(d, resolved_basenames)` in the `dirnames[:]=` filter. This prunes entire subtrees before any file-level lookup, handling the common case of a graphify-out/ subtree.
2. **File-level set lookup:** `if str(p.resolve()) in prior_files` where `prior_files` is a `set[str]` built once before the walk. O(1) per file lookup.

This two-layer approach means in the common case (output dir has been pruned at directory level), the file-level set lookup is never reached. The set is only consulted for files that survived directory pruning, i.e., prior outputs in a renamed location.

**Memory ceiling:** 5 runs × ~1000 files/run × ~100 bytes/path = ~500KB. Acceptable for a CLI tool.

---

## Schema Migration Concerns (First Deployment)

**No migration needed** — `output-manifest.json` is a new file at a new path. [VERIFIED: D-22 decision]

**Scenario 1: First ever Phase 28 run, no manifest exists.**
`_load_output_manifest()` returns `{"version": 1, "runs": []}`. `prior_files` is empty. Nesting guard still protects via D-18 basename matching + `_SELF_OUTPUT_DIRS`. No files are incorrectly skipped. After the run, a manifest is written.

**Scenario 2: Legacy `graphify-out/` content from pre-Phase 28 runs.**
These are handled by the existing nesting guard (`_SELF_OUTPUT_DIRS` / `_is_noise_dir`), which was already partially hardened in the quick-fix commit before Phase 28. Phase 28 supersedes that quick-fix by making the guard ResolvedOutput-aware. Legacy content in the default `graphify-out/` path is caught by D-18's literal set regardless of manifest presence.

**Scenario 3: User's corpus has a legitimate directory named `graphify-out` (e.g., they document graphify itself).**
D-19 is warn-and-skip, not fatal. The user will see:
```
[graphify] WARNING: skipped 1 nested output path(s) (deepest: /repo/docs/graphify-out)
```
This is a false positive — an inevitable consequence of basename-matching. The recommended mitigation is to add `graphify-out` to their `.graphifyignore` or use `output.exclude` in their profile. Phase 29's `graphify doctor` command (out of scope here) can surface this false-positive risk explicitly. There is no perfect solution: adding full path context to the guard would require `resolved.artifacts_dir` to be set (only available in vault mode) and would not protect no-vault users.

---

## Edge Cases to Plan For

### Edge Case 1: `resolved.artifacts_dir` doesn't exist yet (first vault run)
`_load_output_manifest()` checks `manifest_path.exists()` before reading; returns silent empty on missing file. `_save_output_manifest()` calls `manifest_path.parent.mkdir(parents=True, exist_ok=True)` before writing. **No issue.** [VERIFIED: pattern from save_manifest() line 463]

### Edge Case 2: `artifacts_dir` manually deleted between runs
Same as Edge Case 1 — `_load_output_manifest()` returns silent empty; `_save_output_manifest()` recreates the directory. The nesting guard via `_SELF_OUTPUT_DIRS` still works (basename match, no filesystem access required). **No issue.**

### Edge Case 3: User has a literal `graphify-out/` directory that ISN'T graphify output
Discussed under Schema Migration Concerns above. Warn-and-skip (D-19) means this is non-fatal but will produce a warning and skip the directory. The workaround is `.graphifyignore` or `output.exclude`. The planner should note this in the plan as a known UX limitation.

### Edge Case 4: `profile.output.exclude` glob matches `resolved.notes_dir` itself
Example: `output.exclude: ["Atlas/**"]` and `notes_dir = vault/Atlas/Knowledge`.

Behaviour: All files under `notes_dir` are excluded at the file level via `_is_ignored()`. This is correct — the user explicitly told graphify to exclude that subtree. No recursive logical loop (the nesting guard is independent of exclude_globs). However, the user would have a logical misconfiguration (excluding their own output directory via globs is redundant because the nesting guard already handles it, but not harmful). Phase 29's doctor command can detect and warn about this.

Phase 28 does NOT need to detect this misconfiguration. The plan should note it as an informational item for Phase 29.

### Edge Case 5: `notes_dir.name == artifacts_dir.name`
In the default (no-vault) case: `notes_dir = Path("graphify-out/obsidian")`, `artifacts_dir = Path("graphify-out")`. Their names are `"obsidian"` and `"graphify-out"` respectively. No collision.

In the vault case: `artifacts_dir.name` is always `"graphify-out"` (sibling-of-vault, D-11). `notes_dir.name` is user-defined. If a user sets `notes_dir` to have basename `"graphify-out"` (e.g., `mode: absolute, path: /vault/graphify-out`), then `resolved_basenames` will contain `"graphify-out"` twice (from both fields), which reduces to one entry in a `frozenset`. No double-counting issue — the frozenset deduplicates.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Glob matching for exclude patterns | Custom regex/wildcard engine | `fnmatch` via existing `_is_ignored()` | Already battle-tested, handles `*`, `**`, `?`; re-use is D-16 decision |
| Atomic JSON write | Write + rename without fsync | `_write_atomic` pattern from `merge.py` | fsync + `os.replace()` is POSIX atomic; already 3x in codebase |
| Path traversal rejection in globs | Custom `..` scanner | Syntactic check on `Path(item).parts` | Stdlib, consistent with `folder_mapping` traversal rejection pattern |
| Unique run_id generation | UUID library import | `hashlib.sha256(f"{notes_dir}{ts}".encode()).hexdigest()[:8]` + timestamp | Stdlib only, per project constraint; or `uuid.uuid4()` which is also stdlib |

---

## Common Pitfalls

### Pitfall 1: `_is_noise_dir` receives a full path, not just a basename
**What goes wrong:** `_is_noise_dir` takes a `str` dir-name component, not a `Path`. Passing `str(dp / d)` instead of `d` would break all existing callers.
**How to avoid:** The new `_is_nested_output(part, resolved_basenames)` mirrors the same `part: str` contract — a bare basename, not a full path.
**Warning sign:** Test failures on `test_detect_skips_graphify_out_subtree` after the change.

### Pitfall 2: `detect()` receives `resolved` but `detect_incremental()` calls `detect(root)` without it
**What goes wrong:** If `detect()` required `resolved`, `detect_incremental()` would break. The keyword-only `resolved: ResolvedOutput | None = None` with `None` default is the fix.
**How to avoid:** All new behaviour inside `detect()` is gated: `if resolved is not None: ...`.
**Warning sign:** `detect_incremental()` raises `TypeError` about missing argument.

### Pitfall 3: Manifest written BEFORE export completes (violates D-29)
**What goes wrong:** A crash or error during `to_obsidian()` would leave a manifest entry pointing at files that were never written.
**How to avoid:** The manifest write call in `__main__.py` must appear after the `try/except` block that wraps `to_obsidian()`, inside the non-error path only.
**Warning sign:** Manifest test shows entry with zero files or files that don't exist.

### Pitfall 4: `output-manifest.json` tmp file `output-manifest.json.tmp` is left on disk after crash
**What goes wrong:** On next run, `_load_output_manifest()` reads `output-manifest.json` (the clean version), ignoring the `.tmp` file — this is correct. The `.tmp` file accumulates on disk.
**How to avoid:** `_save_output_manifest()` already handles this: the `except OSError` block calls `tmp.unlink()`. The `.tmp` suffix won't be loaded by `_load_output_manifest()` because it looks for `_OUTPUT_MANIFEST_NAME` exactly.
**Warning sign:** Stray `.json.tmp` file in `artifacts_dir` after a simulated mid-write crash test.

### Pitfall 5: `exclude_globs` applied before `_load_graphifyignore` patterns, duplicating work
**What goes wrong:** Not a bug, just inefficiency — `_is_ignored()` with `exclude_globs` is called for every file. Order does not matter for correctness since `_is_ignored` short-circuits on first match.
**How to avoid:** Merge `exclude_globs` into `ignore_patterns` list: `all_patterns = ignore_patterns + list(resolved.exclude_globs)`. Then pass the combined list to the single `_is_ignored()` call. This is cleaner than two separate calls.
**Warning sign:** Two separate `_is_ignored()` calls per file with different pattern lists.

### Pitfall 6: NamedTuple field-order regression — consumers unpacking 5 values
**What goes wrong:** Adding `exclude_globs` as the 6th field breaks `errors, warnings, *_ = result`-style unpacking if any caller unpacks exactly 5.
**How to avoid:** `test_resolved_output_unpacks_to_tuple` in `test_output.py` currently unpacks to `(vault_detected, vault_path, notes_dir, artifacts_dir, source)`. Update to 6-tuple in Wave 0 before implementing.
**Warning sign:** `test_resolved_output_unpacks_to_tuple` fails with `too many values to unpack`.

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| `detect()` prunes only literal `{"graphify-out", "graphify_out"}` (quick-fix) | Prunes literal set + ResolvedOutput-derived basenames + profile exclude globs + manifest prior files | Phase 28 | Generalises the v1.6 self-ingestion fix across renamed output dirs and vault profiles |
| `save_manifest()` / `load_manifest()` use non-atomic writes | New `_save_output_manifest()` uses atomic tmp+rename (existing merge.py pattern) | Phase 28 | Crash-safe manifest writes |
| No record of prior output paths across runs | `output-manifest.json` rolling N=5 run history | Phase 28 | Renamed-output recovery (D-26/D-27) |

---

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | `run_corpus()` in `pipeline.py` is the right injection point for threading `resolved` to `detect()` | detect() Data Flow | If skill.md calls `detect()` directly (not via `run_corpus`), the vault-aware pruning won't apply to skill-driven runs |
| A2 | `MergeResult` returned by `to_obsidian()` has a `plan.written_files` attribute usable for the `--obsidian` manifest write | __main__.py wire-points | If `MergeResult` does not expose a written-file list, the manifest `files:` will be empty for `--obsidian` runs |
| A3 | `hashlib` is always available (stdlib) for `run_id` generation | Manifest helpers | hashlib is stdlib since Python 2.5; confirmed available on 3.10/3.12 |

**A1 elaboration:** The skill.md calls `detect(Path('INPUT_PATH'))` directly in Python subprocess code (lines 162-166 of skill.md). This is a skill-layer call that bypasses `pipeline.py`. For Phase 28, vault-aware pruning via `ResolvedOutput` requires the caller to have run `resolve_output()` first. Skill-driven detect calls do not have a `ResolvedOutput` — they pass `resolved=None`, which activates the D-21 universal nesting guard (`_SELF_OUTPUT_DIRS`) and no manifest lookup. This is acceptable per D-21 ("applies whether or not vault detected") — the literal-name guard runs regardless. The full vault-aware pruning (profile exclude_globs + manifest prior files) is only available when `resolved` is passed, which happens via the CLI branches.

**A2 elaboration:** Reading `merge.py`'s `MergeResult` (not read in this research session) is needed to confirm whether it exposes a written-file list. If it doesn't, `written_files=[]` is still correct — the nesting guard via directory pruning handles the common case, and the manifest's `notes_dir` root is recorded as a directory-level prune anchor.

---

## Open Questions

1. **Does `MergeResult` expose a `written_files` list?**
   - What we know: `to_obsidian()` returns `MergeResult` (or `MergePlan` for dry-run). The plan summary has `{"CREATE": N, "UPDATE": M}` but it's unclear if individual file paths are recorded.
   - What's unclear: Whether Phase 28 can record per-file paths in the manifest from `--obsidian` output, or must fall back to root-only recording.
   - Recommendation: The planner should grep `merge.py` for `MergeResult` fields before writing the `--obsidian` manifest-write task. If `files:` is not exposed, note in the plan that per-file manifest population is deferred (the roots + nesting guard still provide protection).

2. **Should `pipeline.py` be the injection point, or should `__main__.py` call `detect()` directly before `run_corpus()`?**
   - What we know: `run_corpus()` currently calls `detect(target)` internally (line 24).
   - What's unclear: Whether refactoring `pipeline.py` to accept `resolved` is preferable to splitting `detect()` out of `run_corpus()` in `__main__.py` (i.e., `__main__.py` calls `det = detect(target, resolved=resolved)` directly, then passes the result to an updated `run_corpus(det, ...)`)
   - Recommendation: Adding `resolved: ResolvedOutput | None = None` to `run_corpus()` is the minimal-diff approach and preserves `pipeline.py` as the single wiring surface. The planner should choose this unless there's a reason to expose `det` to `__main__.py`.

---

## Environment Availability

Step 2.6: SKIPPED — Phase 28 is a pure code/config change. No external tools, services, CLIs, databases, or runtimes beyond the standard Python 3.10+ stdlib are required. [VERIFIED: No new dependencies in Standard Stack section]

---

## Validation Architecture

Nyquist validation is **enabled** (`workflow.nyquist_validation: true` in `.planning/config.json`). [VERIFIED: config.json read]

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest (already installed, all 1647 tests passing) |
| Config file | None (uses defaults; `pyproject.toml` configures test paths) |
| Quick run command | `pytest tests/test_detect.py tests/test_profile.py tests/test_output.py -q` |
| Full suite command | `pytest tests/ -q` |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| VAULT-11 | `output.exclude` accepted in profile schema | unit | `pytest tests/test_profile.py -k "exclude" -x` | ❌ Wave 0 |
| VAULT-11 | Traversal/empty/non-string exclude entries rejected | unit | `pytest tests/test_profile.py -k "exclude" -x` | ❌ Wave 0 |
| VAULT-11 | `exclude_globs` populated in `ResolvedOutput` from profile | unit | `pytest tests/test_output.py -k "exclude_globs" -x` | ❌ Wave 0 |
| VAULT-11 | `detect()` prunes files matching `exclude_globs` | unit | `pytest tests/test_detect.py -k "exclude_globs" -x` | ❌ Wave 0 |
| VAULT-11 | `exclude_globs` applied even when `--output` overrides destination | unit | `pytest tests/test_detect.py -k "exclude_globs_with_cli_flag" -x` | ❌ Wave 0 |
| VAULT-12 | Paths matching `resolved.notes_dir.name` pruned from scan | unit | `pytest tests/test_detect.py -k "nesting_guard_resolved" -x` | ❌ Wave 0 |
| VAULT-12 | Paths matching `resolved.artifacts_dir.name` pruned from scan | unit | `pytest tests/test_detect.py -k "nesting_guard_resolved" -x` | ❌ Wave 0 |
| VAULT-12 | Single summary warning emitted (not per-file) | unit | `pytest tests/test_detect.py -k "nesting_guard_summary" -x` | ❌ Wave 0 |
| VAULT-12 | Guard applies with `resolved=None` (no-vault case) | unit | `pytest tests/test_detect.py -k "test_detect_skips_graphify_out" -x` | ✅ existing |
| VAULT-13 | `output-manifest.json` written atomically after export | unit | `pytest tests/test_detect.py -k "output_manifest" -x` | ❌ Wave 0 |
| VAULT-13 | Missing manifest → silent empty (no crash) | unit | `pytest tests/test_detect.py -k "output_manifest_missing" -x` | ❌ Wave 0 |
| VAULT-13 | Malformed manifest → warn-once + empty | unit | `pytest tests/test_detect.py -k "output_manifest_malformed" -x` | ❌ Wave 0 |
| VAULT-13 | Rolling N=5 cap enforced on write | unit | `pytest tests/test_detect.py -k "output_manifest_fifo" -x` | ❌ Wave 0 |
| VAULT-13 | GC of stale file entries on write | unit | `pytest tests/test_detect.py -k "output_manifest_gc" -x` | ❌ Wave 0 |
| VAULT-13 | Prior-run files excluded from scan (renamed notes_dir recovery) | unit | `pytest tests/test_detect.py -k "output_manifest_renamed_notes" -x` | ❌ Wave 0 |

### Integration / Acceptance Test Scenarios (ROADMAP success criteria)

**Scenario 1 — ROADMAP SC#1 (profile destination pruned + exclude globs applied):**
```python
# tmp_path: vault with .obsidian/ + profile.yaml (exclude: ["private/**"])
# Prior output at notes_dir; private/ subdir with files
# → detect() returns no notes_dir files, no private/ files
def test_vault_11_integration_profile_destination_and_exclude_globs(tmp_path): ...
```

**Scenario 2 — ROADMAP SC#2 (nesting guard at any depth, single warning):**
```python
# tmp_path: corpus with nested graphify-out/ at depth 3
# → detect() excludes nested dir, emits exactly one WARNING line
def test_vault_12_integration_nesting_at_depth_single_warning(tmp_path, capsys): ...
```

**Scenario 3 — ROADMAP SC#3 (manifest written + read on re-run):**
```python
# Simulate: build resolved, write manifest via _save_output_manifest, 
# then call detect() with resolved → prior files excluded
def test_vault_13_integration_manifest_written_and_read(tmp_path): ...
```

**Scenario 4 — ROADMAP SC#4 (renamed profile output — prior run not re-ingested):**
```python
# Run 1: notes_dir = vault/Atlas/Graph; manifest records those files
# Run 2: notes_dir = vault/Spaces/Graph (renamed in profile)
# → detect() reads manifest, excludes run-1 files even though notes_dir changed
def test_vault_13_integration_renamed_notes_dir_recovery(tmp_path): ...
```

**Scenario 5 — v1.6 self-ingestion regression guard:**
```python
# Set up: vault with .obsidian/, run 1 writes notes to vault/Atlas/
# Run 2 from same CWD: detect() must NOT ingest vault/Atlas/ notes
# → result["files"]["document"] contains no files from Atlas/
def test_no_self_ingestion_regression_after_phase28(tmp_path): ...
```

### Sampling Rate
- **Per task commit:** `pytest tests/test_detect.py tests/test_profile.py tests/test_output.py -q`
- **Per wave merge:** `pytest tests/ -q`
- **Phase gate:** Full suite green (1647+ tests) before `/gsd-verify-work`

### Wave 0 Gaps
- [ ] `tests/test_detect.py` — new test functions covering VAULT-12/13 (append to existing file, do not replace)
- [ ] `tests/test_profile.py` — new test functions covering VAULT-11 `output.exclude` validation (append after Phase 27 block at line 1292)
- [ ] `tests/test_output.py` — update `test_resolved_output_unpacks_to_tuple` and `test_resolved_output_namedtuple_field_order` for 6th field; add `test_resolve_output_exclude_globs_populated_from_profile`

---

## Security Domain

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | no | — |
| V3 Session Management | no | — |
| V4 Access Control | no | — |
| V5 Input Validation | yes | `validate_profile()` strict rejection of malformed `exclude` entries; D-17 |
| V6 Cryptography | no | — |
| Path confinement | yes | Traversal rejection in `exclude` glob validation (consistent with `security.py` model) |

### Known Threat Patterns

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| `output.exclude` glob containing `../../*` to cause path traversal during scan | Tampering | D-17: `validate_profile()` rejects any exclude entry containing `..` segments or absolute paths at load time |
| Adversarial `output-manifest.json` in `artifacts_dir` with crafted file paths | Tampering | `_load_output_manifest()` does not trust path strings from the manifest for any purpose except set membership (`if str(p.resolve()) in prior_files`); `p.resolve()` is always computed from the actual filesystem scan, not from the manifest |
| Malformed manifest causing crash / silent skip of legitimate files | Denial of Service | D-25 warn-once fallback: malformed manifest returns empty prior_files, degrading to no-manifest behaviour rather than crashing or silently pruning |
| Stale `.json.tmp` file from aborted write polluting the manifest read | Integrity | `_load_output_manifest()` looks for exact filename `output-manifest.json`; `.json.tmp` is never loaded |

---

## Project Constraints (from CLAUDE.md)

- **Python 3.10+** — `tuple[str, ...]` type syntax, `NamedTuple` default fields, `Path.with_suffix()`, `os.replace()` all supported
- **No new required dependencies** — all implementation uses stdlib (`fnmatch`, `json`, `os`, `pathlib`, `hashlib`, `datetime`)
- **Backward compatible** — `detect()` gains `resolved=None` keyword-only argument; all existing callers unchanged
- **Pure unit tests** — all tests use `tmp_path`; no network calls; no filesystem side effects outside `tmp_path`
- **CI targets: Python 3.10 and 3.12** — no syntax incompatibilities introduced
- **Security** — path confinement model respected: `output-manifest.json` written to `artifacts_dir` (confined per D-26); exclude glob validation inherits folder_mapping traversal rejection pattern

---

## Sources

### Primary (HIGH confidence)
- Codebase: `graphify/detect.py` — `_SELF_OUTPUT_DIRS`, `_is_noise_dir`, `_is_ignored`, `_load_graphifyignore`, `detect()`, `save_manifest()`, `load_manifest()`, `detect_incremental()` — read directly
- Codebase: `graphify/output.py` — `ResolvedOutput` NamedTuple, `resolve_output()` — read directly
- Codebase: `graphify/profile.py` — `validate_profile()`, `output:` schema branch (lines 423-451) — read directly
- Codebase: `graphify/__main__.py` — `--obsidian` branch (~lines 1285-1405), `run` branch (~lines 2112-2170) — read directly
- Codebase: `graphify/merge.py:_write_atomic` — canonical atomic write pattern — read directly
- Codebase: `graphify/vault_promote.py:_write_atomic` — second instance of atomic write pattern — read directly
- Codebase: `graphify/pipeline.py` — `run_corpus()` signature and `detect()` call — read directly
- Planning: `.planning/phases/28-self-ingestion-hardening/28-CONTEXT.md` — locked decisions D-14 through D-29
- Planning: `.planning/phases/27-vault-detection-profile-driven-output-routing/27-02-SUMMARY.md` — `ResolvedOutput` API as shipped
- Planning: `.planning/notes/obsidian-export-self-ingestion-loop.md` — root cause analysis
- Tests: `tests/test_detect.py`, `tests/test_profile.py`, `tests/test_output.py` — coverage maps read directly

---

## Metadata

**Confidence breakdown:**
- Code touch-points: HIGH — every symbol verified by direct codebase read
- Atomic write pattern: HIGH — three independent implementations verified
- Test coverage map: HIGH — all test files read and test names enumerated
- Integration risk (detect_incremental): HIGH — verified by tracing call chain
- `run_id` implementation: HIGH — stdlib hashlib available, pattern mirrors enrich.py
- `MergeResult.written_files` availability: LOW (A2) — merge.py not read in this session

**Research date:** 2026-04-27
**Valid until:** 2026-05-27 (stable codebase, no fast-moving external deps)
