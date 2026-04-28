# Phase 29: Doctor Diagnostics & Dry-Run Preview - Research

**Researched:** 2026-04-28
**Domain:** CLI diagnostics — read-only orchestration over Phase 27 (`output.py`) + Phase 28 (`detect.py` manifest/nesting/exclude) primitives
**Confidence:** HIGH

## Summary

Phase 29 ships a single new pure-Python module (`graphify/doctor.py`) plus a CLI dispatch branch in `graphify/__main__.py`. Every primitive it needs already exists: `is_obsidian_vault()` and `resolve_output()` (Phase 27, `output.py`); `validate_profile()` returning `list[str]` (`profile.py:209`); `_load_output_manifest()`, `_is_nested_output()`, `_is_ignored()`, `_load_graphifyignore()`, `_SELF_OUTPUT_DIRS`, and `detect()` itself (Phase 28, `detect.py`). The architectural work is therefore (a) defining the `DoctorReport` dataclass shape; (b) deciding how `detect()` surfaces per-path skip reasons for the dry-run preview; (c) wiring `_FIX_HINTS` against the inventory of error strings the validators actually emit; (d) computing `would_self_ingest` as a forward-looking nesting check against the resolved destinations.

The only non-trivial implementation choice is item (b). Three viable approaches exist; the recommended one (extend `detect()` return shape with a new `skipped: dict[str, list[str]]` field) is the lowest-risk because it preserves all current callers (existing keys are untouched) and keeps the "single source of truth for skip decisions" invariant from D-39.

**Primary recommendation:** Plan three plans — `29-01` (`doctor.py` + `tests/test_doctor.py`), `29-02` (extend `detect()` to surface skip reasons), `29-03` (`__main__.py` `doctor` subcommand wiring + integration tests via `subprocess.run` matching `tests/test_main_flags.py` pattern).

## User Constraints (from CONTEXT.md)

### Locked Decisions

- **D-30:** New top-level `graphify doctor` subcommand in `__main__.py` dispatch.
- **D-31:** `--dry-run` lives ONLY on `graphify doctor --dry-run`. No top-level `graphify --dry-run`. Existing `--dry-run` flags on `--obsidian` (MRG-05), `vault-promote`, `enrich` (ENRICH-10) keep semantics unchanged.
- **D-32:** New `graphify/doctor.py` module — pure functions `run_doctor(cwd: Path, *, dry_run: bool = False) -> DoctorReport` and `format_report(report: DoctorReport) -> str`.
- **D-33:** `DoctorReport` shape (planner picks dataclass vs NamedTuple) carries: `vault_detection`, `profile_validation_errors: list[str]`, `resolved_output: ResolvedOutput | None`, `ignore_list: list[str]` (union surface — see D-37), `manifest_history: list[dict] | None`, `would_self_ingest: bool`, `recommended_fixes: list[str]`, plus `preview: PreviewSection` when `dry_run=True`.
- **D-34:** Sectioned plain text only in v1.7. Fixed section order: Vault Detection / Profile Validation / Output Destination / Ignore-List / (Preview) / Recommended Fixes. `[graphify]`-prefixed lines.
- **D-35:** Binary exit codes — 0 OK, 1 misconfig (any of: profile validation errors, output destination unresolvable, `would_self_ingest=True`).
- **D-36:** `validate_profile()` ABI unchanged — `(profile: dict) -> list[str]`.
- **D-37:** Ignore-list shown as union of 4 sources, grouped by source — no dedup across sources:
  1. `_SELF_OUTPUT_DIRS` literal set
  2. Resolved-basename additions (notes_dir.name, artifacts_dir.name when distinct)
  3. `.graphifyignore` patterns (`_load_graphifyignore()`)
  4. Profile `output.exclude` globs (`resolved.exclude_globs`)
- **D-38:** Counts + bounded sample (first 10 ingested + first 5 per skip-reason group).
- **D-39:** Dry-run calls real `detect()` — preview ≡ actual scan. Planner picks how `detect()` surfaces skip reasons (constraint: single source of truth for skip decisions).
- **D-40:** `_FIX_HINTS` hardcoded mapping in `doctor.py` — pattern-keyed (substring or regex) → fix line.
- **D-41:** One fix line per detected issue, no priority ranking.

### Claude's Discretion

- Exact `DoctorReport` form (dataclass vs NamedTuple) — must be importable from tests.
- How `detect()` surfaces skip reasons — extend return shape vs predicate instrumentation vs `explain` flag.
- TTY-aware colorization — only if trivially free.
- Exact wording of `_FIX_HINTS` entries beyond the three CONTEXT examples — verb-first imperative.
- MCP exposure via `serve.py` — defer to v1.8 unless trivially free.

### Deferred Ideas (OUT OF SCOPE)

- `graphify doctor --json` machine-readable output (revisit when scripting demand emerges).
- Distinct exit codes per failure class.
- Top-level `graphify --dry-run` aliasing.
- MCP exposure of `doctor`.
- Auto-fix mode (`graphify doctor --fix`) — doctor is read-only by design.
- Color/TTY-aware formatting beyond plain `[graphify]`-prefixed text.
- Per-fix priority/severity ranking.

## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| VAULT-14 | `graphify doctor` command — prints vault detection, profile validation, resolved destination, ignore-list, recommended fixes; non-zero exit on misconfig | §"Existing primitives" maps each section to a one-call source; §"Fix-hint inventory" provides `_FIX_HINTS` table; §"`would_self_ingest`" defines the third exit-1 trigger |
| VAULT-15 | Dry-run preview — `graphify doctor --dry-run` shows what files would be ingested, skipped (grouped), and where output would land — without writing | §"Skip-reason surfacing" recommends extending `detect()` return shape; §"Bounded sample formatting" handles D-38 |

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|--------------|----------------|-----------|
| CLI argv parsing for `doctor` / `doctor --dry-run` | `__main__.py` dispatch | — | Joins existing `if cmd == ...` chain (D-30); manual flag loop pattern matches `--obsidian`, `run`, `vault-promote` |
| Diagnostic logic (read state, build report) | `graphify/doctor.py` `run_doctor()` | — | Per-stage-module convention (D-32); pure function |
| Report rendering (text formatting) | `graphify/doctor.py` `format_report()` | — | Separable from logic for unit testing |
| Vault detection | `graphify/output.py:is_obsidian_vault` | — | Phase 27 contract; doctor is a read-only consumer |
| Output destination resolution | `graphify/output.py:resolve_output` | — | Phase 27 contract; doctor calls unchanged (must catch SystemExit for missing-profile / sibling-validation refusals) |
| Profile validation | `graphify/profile.py:validate_profile` | — | Phase 27/28 ABI unchanged (D-36); doctor maps return list to fix hints |
| Ignore-list union | `graphify/doctor.py` (composes 4 sources) | `detect.py` helpers | New aggregation; sources are already-stable primitives |
| Manifest history read | `graphify/detect.py:_load_output_manifest` | — | Phase 28 helper already returns empty envelope on failure (D-25); doctor reuses |
| Dry-run file scan | `graphify/detect.py:detect()` | — | Single source of truth (D-39); planner extends return shape with skip reasons |
| `would_self_ingest` predicate | `graphify/doctor.py` (composes `_is_nested_output` + `resolved.notes_dir`/`artifacts_dir`) | `detect.py:_is_nested_output` | New forward-looking check; reuses Phase 28 predicate |
| `_FIX_HINTS` table | `graphify/doctor.py` (module-level constant) | — | D-40 — single edit surface |

## Standard Stack

### Core

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| Python stdlib `pathlib` | 3.10+ | Path manipulation throughout | Already used everywhere `[VERIFIED: detect.py, output.py]` |
| Python stdlib `dataclasses` (or `typing.NamedTuple`) | 3.10+ | `DoctorReport` shape | `ResolvedOutput` uses `NamedTuple` `[VERIFIED: output.py:25]`; either works for D-33 |
| Python stdlib `sys` | 3.10+ | stderr/stdout/argv/exit | Already used in `__main__.py`, `output.py` |
| Python stdlib `json` | 3.10+ | Read manifest history | Already used in `detect.py:_load_output_manifest` |

### Supporting

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| Python stdlib `re` | 3.10+ | `_FIX_HINTS` regex pattern matching | Only if regex chosen over substring; substring `in` is sufficient for the 5–10 known patterns |
| Python stdlib `fnmatch` | 3.10+ | (Already used by `_is_ignored`) | Doctor consumes via `_is_ignored`; no direct use |

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| `dataclass(frozen=True)` for `DoctorReport` | `NamedTuple` | NamedTuple matches `ResolvedOutput` precedent; dataclass gives nicer default-factory for `list` fields. Recommend dataclass for the lists. `[ASSUMED: stylistic]` |
| Hardcoded `_FIX_HINTS` dict | Map error strings programmatically per validator | D-40 explicitly locks hardcoded — no decision needed `[CITED: 29-CONTEXT.md D-40]` |
| Subprocess-based CLI tests | In-process `main()` invocation | `tests/test_main_flags.py` and `tests/test_main_cli.py` both use subprocess `[VERIFIED: tests/test_main_flags.py:18, tests/test_main_cli.py:32]` — match the established pattern |

**Installation:** None — stdlib only.

**Version verification:** N/A (stdlib).

## Architecture Patterns

### System Architecture Diagram

```
                                        ┌─────────────────────────────┐
   sys.argv ───► __main__.py:main()  ───┤  cmd == "doctor"            │
                                        │  parse --dry-run flag       │
                                        └────────────┬────────────────┘
                                                     │
                                                     ▼
                                        ┌─────────────────────────────┐
                                        │  doctor.run_doctor(         │
                                        │    cwd=Path.cwd(),          │
                                        │    dry_run=<bool>,          │
                                        │  )                          │
                                        └────────────┬────────────────┘
                                                     │
        ┌────────────────────────┬───────────────────┼────────────────────┬─────────────────────┐
        ▼                        ▼                   ▼                    ▼                     ▼
  is_obsidian_vault()    load_profile()       resolve_output()     _load_output_      _load_graphifyignore()
  (output.py)            validate_profile()    (output.py)          manifest()          (detect.py)
                         (profile.py)          → may SystemExit     (detect.py)
                                                  catch as
                                                  "unresolvable"
        │                        │                   │                    │                     │
        └─────────────┬──────────┴────────┬──────────┴──────────┬─────────┴─────────┬───────────┘
                      ▼                   ▼                     ▼                   ▼
                ┌─────────────────────────────────────────────────────────────────────┐
                │  Build DoctorReport                                                  │
                │   • vault_detection                                                  │
                │   • profile_validation_errors                                        │
                │   • resolved_output (or None)                                        │
                │   • ignore_list (4-source union, grouped)                            │
                │   • manifest_history                                                 │
                │   • would_self_ingest = _check_self_ingest(resolved, scan_root)      │
                │   • recommended_fixes (mapped via _FIX_HINTS)                        │
                │   • preview (only if dry_run=True)                                   │
                └────────────────────────────┬────────────────────────────────────────┘
                                             │
                                  if dry_run │
                                             ▼
                                  ┌─────────────────────────────┐
                                  │  detect(scan_root,           │
                                  │         resolved=resolved)   │
                                  │  ─ extended return shape ─   │
                                  │  files: dict[type, list]     │
                                  │  skipped: dict[reason, list] │ ◄── NEW (29-02)
                                  └────────────┬────────────────┘
                                               ▼
                                       PreviewSection
                                       (counts + bounded sample,
                                        first 10 ingested,
                                        first 5 per skip group)
                                             │
                                             ▼
                          format_report(report) ──► stdout (sectioned text)
                                             │
                                             ▼
                          sys.exit(1 if any_misconfig else 0)
```

### Recommended Project Structure

```
graphify/
├── doctor.py                    # NEW (29-01) — run_doctor + format_report + DoctorReport + _FIX_HINTS
├── detect.py                    # MODIFIED (29-02) — detect() return shape gains "skipped: dict[str, list[str]]"
├── __main__.py                  # MODIFIED (29-03) — new "doctor" dispatch branch + --help line
├── output.py                    # READ-ONLY consumer
└── profile.py                   # READ-ONLY consumer

tests/
├── test_doctor.py               # NEW (29-01) — unit tests for run_doctor, format_report, _FIX_HINTS mapping, would_self_ingest
├── test_detect.py               # EXTENDED (29-02) — skip-reason surfacing tests
└── test_main_flags.py           # EXTENDED (29-03) — subprocess tests for `doctor` and `doctor --dry-run` exit codes + stdout
```

### Pattern 1: Pure-function module with dataclass return + formatter pair

**What:** `run_X(...) -> XReport` does all I/O + computation; `format_report(report) -> str` is pure formatting. Mirrors the `analyze.py` / `report.py` separation the codebase already uses.

**When to use:** Any CLI subcommand that produces structured human output AND must be unit-testable without parsing strings.

**Example:**
```python
# Source: graphify/output.py (precedent for NamedTuple), graphify/analyze.py (precedent for pure-function module)
from __future__ import annotations
from dataclasses import dataclass, field
from pathlib import Path
from graphify.output import ResolvedOutput

@dataclass
class PreviewSection:
    would_ingest: list[str]
    would_skip: dict[str, list[str]]   # reason -> sample paths
    notes_dir: Path
    artifacts_dir: Path
    total_ingest: int
    total_skip: int

@dataclass
class DoctorReport:
    vault_detection: dict                    # {"detected": bool, "cwd": Path, "vault_path": Path | None}
    profile_validation_errors: list[str] = field(default_factory=list)
    resolved_output: ResolvedOutput | None = None
    ignore_list: dict[str, list[str]] = field(default_factory=dict)   # source -> entries (D-37 grouping)
    manifest_history: list[dict] | None = None
    would_self_ingest: bool = False
    recommended_fixes: list[str] = field(default_factory=list)
    preview: PreviewSection | None = None

    def is_misconfigured(self) -> bool:
        return (
            bool(self.profile_validation_errors)
            or self.resolved_output is None
            or self.would_self_ingest
        )
```

### Pattern 2: Catch-SystemExit for `resolve_output()` failure modes

**What:** `output.py:_refuse()` raises `SystemExit(1)` for missing profile (D-05), missing `output:` block (D-02), missing PyYAML, malformed `mode`, sibling-of-vault validator failures.
**When to use:** Doctor must convert these refusals into report state, not propagate them.

**Example:**
```python
# Source: graphify/output.py:38 (_refuse helper)
try:
    resolved = resolve_output(cwd, cli_output=None)
except SystemExit:
    resolved = None   # report it as "unresolvable" → exit 1 per D-35
```

Caveat: `resolve_output()` ALSO writes detection lines to stderr (`output.py:88`, `:165`) before refusing. The doctor invocation will emit those lines too — acceptable per D-34 (`[graphify]`-prefixed convention) but worth noting in the test setup (`capsys.readouterr().err` will see them).

### Pattern 3: Subprocess-based CLI integration tests

**What:** Use `subprocess.run([sys.executable, "-m", "graphify", *args], cwd=tmp_path, capture_output=True, text=True)`.
**Source:** `tests/test_main_flags.py:18`, `tests/test_main_cli.py:32`.

```python
def _graphify(args: list[str], cwd: Path) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, "-m", "graphify", *args],
        cwd=str(cwd), capture_output=True, text=True, timeout=60,
    )
```

### Anti-Patterns to Avoid

- **Re-implementing scan logic in `doctor.py`** — D-39 explicitly forbids; preview must call `detect()`.
- **Mutating any of `output.py`, `profile.py`, `detect.py:detect()` signatures beyond the additive `skipped` return-key** — D-36 locks `validate_profile()`; CONTEXT D-39's "single source of truth" implies additive-only changes to `detect()`.
- **Raising on profile errors** — `validate_profile()` returns `list[str]`; doctor follows the same accumulator pattern (CONTEXT "Validate-first, fail-loudly" applies to validator emission, not to doctor's collection step).
- **Inferring fix hints by re-parsing English error strings outside `_FIX_HINTS`** — D-40 says single hardcoded table.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| File scanning for dry-run preview | A lighter parallel scanner | `graphify.detect.detect(scan_root, resolved=resolved)` | D-39 — preview ≡ actual scan; any divergence is a v1.6-style bug |
| Glob matching for ignore-list display | `re` patterns | `fnmatch` via `_is_ignored` | Already in production for `.graphifyignore` (`detect.py:332`) |
| Manifest reading | `json.loads()` + custom error handling | `_load_output_manifest()` | Already returns empty envelope on failure (D-25); single source of truth |
| Vault basename detection | `_SELF_OUTPUT_DIRS` re-listed | Import the constant | Single source: `detect.py:259` |
| Sibling-of-vault validation | Re-derive | Catch `SystemExit` from `resolve_output` | All refusals already centralized in `_refuse()` (`output.py:38`) |
| Argparse for `doctor --dry-run` | `argparse.ArgumentParser` | Manual `if "--dry-run" in sys.argv[2:]` | Codebase convention (`__main__.py` `--obsidian` branch ~line 1304); only one flag, no value parsing needed |

**Key insight:** Phase 29 is almost entirely a composition exercise. Every primitive exists; the new code is a 200-line module that reads them, builds a dataclass, and renders text. Resist the urge to reach beyond `doctor.py` + a single additive change to `detect()`.

## Skip-Reason Surfacing — Three Approaches

This is the ONE open implementation question. CONTEXT D-39 leaves it to the planner.

### Recommended: Approach A — Extend `detect()` return shape (additive)

Add a new top-level key to `detect()`'s return dict:

```python
# in detect.py, alongside existing return:
return {
    "files": {...},                       # unchanged
    "total_files": ...,                   # unchanged
    ...                                   # all existing keys unchanged
    "skipped": {                          # NEW (29-02)
        "nesting": [...],                 # already accumulated as `nested_paths`
        "exclude-glob": [...],            # currently dropped by _is_ignored before entering files[]
        "manifest": [...],                # currently dropped by `if str(p.resolve()) in prior_files: continue`
        "sensitive": [...],               # already accumulated as `skipped_sensitive` (rename for grouping)
        "noise-dir": [...],               # currently dropped silently in dirnames pruning loop
    },
}
```

**Implementation:** Change five `continue` / pruning sites in `detect.py:detect()` (lines 506–558) to also `append` to the appropriate skipped list. No public ABI break — additive only.

**Pros:**
- Single source of truth (D-39).
- Zero impact on existing callers — `result["files"]`, `result["total_files"]`, etc., remain unchanged.
- Test surface: existing `test_detect.py` tests still pass; new tests assert on `result["skipped"]`.
- Doctor consumes `result["skipped"]` directly to build `PreviewSection.would_skip`.

**Cons:**
- Memory overhead on huge corpora (10k+ skipped paths). Mitigation: doctor only displays the bounded sample (D-38), but `detect()` itself accumulates all paths. Acceptable in v1.7 — no caller is memory-pressured today.

**Confidence: HIGH** — matches the codebase pattern (return dict with named keys; `nested_paths` and `skipped_sensitive` already accumulate).

### Approach B — `explain: bool = False` flag

```python
def detect(root: Path, *, follow_symlinks=False, resolved=None, explain: bool = False) -> dict:
    ...
    if explain:
        result["skipped"] = {...}
    return result
```

**Pros:** Memory-zero for production callers (no accumulation when `explain=False`).
**Cons:** Branch noise inside the hot loop; doctor must request explain mode. Two code paths to maintain. Higher test surface (must verify both modes return same `files` keys).

### Approach C — Predicate instrumentation from doctor.py

Doctor wraps `_is_nested_output`, `_is_ignored`, etc., with logging predicates and re-runs `os.walk` itself.

**Pros:** No detect.py changes.
**Cons:** Re-implements scan logic — violates D-39. Predicate ABI is module-private. Reject.

### Recommendation

**Approach A.** Approach B's memory savings are theoretical (no callers report memory issues today) and the dual code path adds maintenance cost. Approach C is disqualified by D-39.

If the planner is concerned about memory on huge corpora, the trivial mitigation is to cap `skipped` lists at `MAX_SKIPPED_PER_REASON = 1000` inside `detect()` — far above the 5-per-reason display cap.

## `would_self_ingest` Computation

Success criterion #2 requires exit-1 when configuration would cause self-ingestion. The predicate:

```python
# in doctor.py
from graphify.detect import _is_nested_output, _SELF_OUTPUT_DIRS

def _would_self_ingest(resolved: "ResolvedOutput | None", scan_root: Path) -> bool:
    """True if any of the resolved output dirs sits under the input scan root.

    Combines two failure modes:
      1. notes_dir or artifacts_dir is INSIDE scan_root (nesting) → next run re-ingests.
      2. notes_dir or artifacts_dir basename matches _SELF_OUTPUT_DIRS but lives at
         a depth where the nesting guard would catch them (Phase 28 D-18 path).
    """
    if resolved is None:
        return False
    scan_root = scan_root.resolve()
    for candidate in (resolved.notes_dir, resolved.artifacts_dir):
        try:
            candidate.resolve().relative_to(scan_root)
        except ValueError:
            continue   # outside scan root — safe
        # Inside scan root: would the nesting guard catch any path component?
        # Walk path components to detect a match.
        rel = candidate.resolve().relative_to(scan_root)
        resolved_basenames = frozenset({resolved.notes_dir.name, resolved.artifacts_dir.name}) - _SELF_OUTPUT_DIRS
        for part in rel.parts:
            if _is_nested_output(part, resolved_basenames):
                return True
        # Even if no part matches the nesting guard, an output dir living
        # under the scan root is still self-ingestion (the scan will walk into it
        # unless _is_noise_dir / exclude-glob catches it). Be conservative:
        return True
    return False
```

**Test scenarios:**
- `scan_root=/tmp/vault`, `notes_dir=/tmp/vault/Notes` → True (sibling-violation; should be sibling-of-vault per D-11).
- `scan_root=/tmp/vault`, `notes_dir=/tmp/notes`, `artifacts_dir=/tmp/graphify-out` → False (both outside).
- `scan_root=/tmp/proj`, `notes_dir=/tmp/proj/graphify-out/obsidian` → True (default v1.0 layout — only flagged when vault detected? Open question; conservative answer is "always True if inside scan_root").

**Open design point:** When `resolved.source == "default"` (the v1.0 backcompat case, D-12), `notes_dir = "graphify-out/obsidian"` is BY DESIGN inside `scan_root`. This must NOT trigger `would_self_ingest=True` or every legacy invocation breaks. Recommendation: skip the check when `resolved.source == "default"` — the nesting guard (Phase 28 D-18) and `_SELF_OUTPUT_DIRS` already protect this case at scan time.

```python
if resolved.source == "default":
    return False   # v1.0 backcompat — Phase 28 nesting guard handles it
```

## Fix-Hint Inventory (`_FIX_HINTS`)

Inventory of every error string each validator emits, with proposed fix-line wording (D-40 / D-41):

### From `validate_profile()` (`profile.py:209` — `output:` branch)

| Error substring (validator output) | Recommended fix line |
|------------------------------------|----------------------|
| `'output' must be a mapping` | `Replace 'output:' with a mapping: 'output: {mode: ..., path: ...}'` |
| `'output' requires a 'mode' key` | `Add 'mode:' under 'output:' — one of: vault-relative, absolute, sibling-of-vault` |
| `output.mode ... invalid` | `Set output.mode to one of: vault-relative, absolute, sibling-of-vault` |
| `'output' requires a 'path' key` | `Add 'path:' under 'output:' (e.g., path: Knowledge/Graph)` |
| `output.path must be a non-empty string` | `Set output.path to a non-empty string (e.g., path: Knowledge/Graph)` |
| `output.path must be relative when mode=vault-relative` | `Use a relative path under 'path:' (no leading /) when mode=vault-relative` |
| `output.path must not start with '~'` | `Replace '~' with an explicit path; '~' is not expanded` |
| `output.path must not contain '..'` | `Remove '..' segments from output.path — path traversal is blocked` |
| `output.path must be absolute when mode=absolute` | `Use an absolute path (starting with /) under 'path:' when mode=absolute` |
| `output.exclude must be a list` | `Make output.exclude a YAML list of glob strings (e.g., ['private/**', '*.tmp'])` |
| `output.exclude[N] must be a string` | `Each output.exclude entry must be a string glob, not a number/dict/list` |
| `output.exclude[N] must not be empty` | `Remove empty/whitespace-only entries from output.exclude` |
| `output.exclude[N] must not be an absolute path` | `Use relative globs in output.exclude (e.g., 'private/**' not '/private/**')` |
| `output.exclude[N] must not contain '..'` | `Remove '..' segments from output.exclude entries — path traversal is blocked` |

### From `resolve_output()` SystemExit refusals (`output.py:_refuse`)

| Refusal substring | Recommended fix line |
|-------------------|----------------------|
| `CWD is an Obsidian vault ... but no .graphify/profile.yaml found` | `Create .graphify/profile.yaml at the vault root (see docs/vault-adapter.md), or pass --output <path>` |
| `CWD is an Obsidian vault ... but PyYAML is not installed` | `Install PyYAML: pip install graphifyy[obsidian]` |
| `CWD is an Obsidian vault ... but profile.yaml has no 'output:' block` | `Add an 'output: {mode: ..., path: ...}' block to .graphify/profile.yaml` |
| `profile output.path must be absolute when mode=absolute` | (same as validator) |
| `profile output.mode ... invalid` | (same as validator) |

### From `validate_sibling_path()` (`profile.py:502`)

| Refusal substring | Recommended fix line |
|-------------------|----------------------|
| `output.path must be a non-empty string for mode=sibling-of-vault` | `Set output.path to a relative directory name (e.g., 'graphify-knowledge') for mode=sibling-of-vault` |
| `output.path must not start with '~'` | (same) |
| `output.path must be relative for mode=sibling-of-vault` | `Use a relative path for sibling-of-vault; switch mode=absolute if you need an absolute path` |
| `output.path must not contain '..' segments for mode=sibling-of-vault` | `Remove '..' segments — sibling-of-vault already escapes one level` |
| `vault ... has no parent directory` | `Move the vault out of the filesystem root, or switch to mode=absolute` |
| `output.path ... escapes vault parent` | `Choose a path that resolves under the vault's parent directory` |

### From `validate_vault_path()` (`profile.py:485`)

| Refusal substring | Recommended fix line |
|-------------------|----------------------|
| `would escape vault directory` | `Remove '..' segments from output.path (vault-relative paths must stay inside the vault)` |

### Doctor-internal triggers (no upstream validator)

| Condition | Recommended fix line |
|-----------|----------------------|
| `would_self_ingest=True` | `Move existing graphify output outside the input scan, or add 'graphify-out/**' to .graphifyignore` |
| Manifest history shows ≥3 distinct `notes_dir` paths in last 5 runs (renamed-output indicator) | `Resolved notes_dir has changed across recent runs — check 'output.path' stability in profile.yaml` (informational; not necessarily exit-1) |

**Implementation form:**
```python
# doctor.py
_FIX_HINTS: list[tuple[str, str]] = [
    ("'output' must be a mapping",
     "Replace 'output:' with a mapping: 'output: {mode: ..., path: ...}'"),
    ("'output' requires a 'mode' key",
     "Add 'mode:' under 'output:' — one of: vault-relative, absolute, sibling-of-vault"),
    # ... ~25 entries
    ("would_self_ingest",
     "Move existing graphify output outside the input scan, "
     "or add 'graphify-out/**' to .graphifyignore"),
]

def _map_to_fix(error_msg: str) -> str | None:
    """Return the first matching fix line for error_msg, or None if no pattern matches."""
    for needle, fix in _FIX_HINTS:
        if needle in error_msg:
            return fix
    return None
```

Substring matching keeps it stdlib-only and avoids regex DoS on user-controlled YAML error messages. Patterns are maintained in declaration order — the first match wins (D-41: one fix per issue, no priority).

## Common Pitfalls

### Pitfall 1: `resolve_output()` writes to stderr before raising

**What goes wrong:** Tests assert `result.stderr == ""` for the success path; doctor tests will see `[graphify] vault detected at ...` lines from `output.py:88`.
**Why it happens:** D-09 / VAULT-08 require that line for ALL invocations that go through `resolve_output()`.
**How to avoid:** Doctor tests use substring assertions (`"vault detected" in result.stderr`), not equality. Match the `tests/test_main_flags.py` style.

### Pitfall 2: PyYAML missing — graceful degradation

**What goes wrong:** `output.py:124` refuses with `SystemExit` if PyYAML is absent and a vault is detected. Doctor must convert this to a fix-hint, not propagate.
**How to avoid:** Wrap `resolve_output()` in `try/except SystemExit`; record that the destination is unresolvable; map the stderr message via `_FIX_HINTS`.
**Detection:** Doctor can probe `import yaml` upfront and surface a single "PyYAML not installed — vault diagnostics limited" line if it's missing AND `is_obsidian_vault(cwd)` is True.

### Pitfall 3: Detect rewrites overwhelm the report

**What goes wrong:** A 10k-file vault → 10k entries in `result["skipped"]["sensitive"]` → format_report renders MB of text.
**How to avoid:** D-38 caps display at first 5/10 per group. `format_report` does the slicing — `run_doctor`/`detect` accumulate everything (or detect caps internally per Approach A mitigation).

### Pitfall 4: `Path.resolve()` against non-existent paths

**What goes wrong:** `would_self_ingest` calls `.resolve()` on `notes_dir` which may not exist yet on first run.
**How to avoid:** `Path.resolve()` is safe on non-existent paths in Python 3.10+ (returns the lexically-resolved path). `[VERIFIED: Python stdlib pathlib docs — strict=False default]`. Confirmed by `output.py:60` which already calls `.resolve()` on user-typed `--output` flag values that may not exist.

### Pitfall 5: Test fixtures need `.obsidian/` AND `.graphify/profile.yaml` AND parent dir for sibling-of-vault

**What goes wrong:** Sibling-of-vault tests require `vault.parent != vault` — `tmp_path / "vault"` has `tmp_path` as parent, which works. But `tmp_path` itself can't be a vault (no parent for sibling tests).
**How to avoid:** Always nest the vault: `vault = tmp_path / "vault"; vault.mkdir(); (vault / ".obsidian").mkdir()`. Pattern from `tests/test_main_flags.py:55`.

### Pitfall 6: `_load_graphifyignore` walks UP from `root`

**What goes wrong:** `_load_graphifyignore(root)` (`detect.py:300`) walks toward the filesystem root collecting `.graphifyignore` files until it hits `.git`. In a `tmp_path` test, it may reach `.graphifyignore` files in the parent project directory.
**How to avoid:** Test fixtures place a `.git` marker at the test root: `(tmp_path / ".git").mkdir()`. Halts the walk. Pattern: not enforced today; will need to be added for any new doctor test that exercises ignore-list. Sanity-check by inspecting `result["graphifyignore_patterns"]` count.

## Code Examples

### Reading the four ignore-list sources and grouping per D-37

```python
# Source: composes graphify/detect.py:_SELF_OUTPUT_DIRS, _load_graphifyignore + ResolvedOutput
from graphify.detect import _SELF_OUTPUT_DIRS, _load_graphifyignore
from graphify.output import ResolvedOutput

def _build_ignore_list(scan_root: Path, resolved: ResolvedOutput | None) -> dict[str, list[str]]:
    sources: dict[str, list[str]] = {}

    # Source 1: literal _SELF_OUTPUT_DIRS
    sources["self-output-dirs (built-in)"] = sorted(_SELF_OUTPUT_DIRS)

    # Source 2: resolved-basename additions
    if resolved:
        basenames = sorted({resolved.notes_dir.name, resolved.artifacts_dir.name} - _SELF_OUTPUT_DIRS)
        if basenames:
            sources["resolved-basenames (from --output / profile)"] = basenames

    # Source 3: .graphifyignore patterns
    sources[".graphifyignore patterns"] = _load_graphifyignore(scan_root)

    # Source 4: profile output.exclude
    if resolved and resolved.exclude_globs:
        sources["profile output.exclude"] = list(resolved.exclude_globs)

    return sources
```

### Subprocess test pattern for the new `doctor` command

```python
# Source: extends tests/test_main_flags.py:_graphify pattern
def test_doctor_in_vault_emits_resolved_destination(tmp_path):
    vault = tmp_path / "vault"
    vault.mkdir()
    (vault / ".obsidian").mkdir()
    (vault / ".graphify").mkdir()
    (vault / ".graphify" / "profile.yaml").write_text(
        "output:\n  mode: vault-relative\n  path: Knowledge/Graph\n"
    )
    (tmp_path / ".git").mkdir()  # halt _load_graphifyignore walk

    result = subprocess.run(
        [sys.executable, "-m", "graphify", "doctor"],
        cwd=str(vault), capture_output=True, text=True, timeout=60,
    )
    assert result.returncode == 0
    assert "Vault Detection" in result.stdout
    assert "Profile Validation" in result.stdout
    assert "Output Destination" in result.stdout
    assert "Knowledge/Graph" in result.stdout
    assert "Recommended Fixes" in result.stdout
    assert "No issues detected" in result.stdout

def test_doctor_invalid_profile_exits_1(tmp_path):
    vault = tmp_path / "vault"
    vault.mkdir()
    (vault / ".obsidian").mkdir()
    (vault / ".graphify").mkdir()
    (vault / ".graphify" / "profile.yaml").write_text("output: not-a-dict\n")
    (tmp_path / ".git").mkdir()

    result = subprocess.run(
        [sys.executable, "-m", "graphify", "doctor"],
        cwd=str(vault), capture_output=True, text=True, timeout=60,
    )
    assert result.returncode == 1
    assert "must be a mapping" in result.stdout or "must be a mapping" in result.stderr
```

### Pure unit test on `run_doctor()` return shape

```python
# Source: matches tests/test_detect.py pure unit pattern
from graphify.doctor import run_doctor, DoctorReport

def test_run_doctor_no_vault_returns_default_resolved(tmp_path):
    (tmp_path / ".git").mkdir()
    (tmp_path / "main.py").write_text("x = 1\n")

    report = run_doctor(tmp_path, dry_run=False)

    assert isinstance(report, DoctorReport)
    assert report.vault_detection["detected"] is False
    assert report.profile_validation_errors == []
    assert report.resolved_output is not None
    assert report.resolved_output.source == "default"
    assert report.would_self_ingest is False
    assert report.is_misconfigured() is False

def test_run_doctor_dry_run_includes_preview(tmp_path):
    (tmp_path / ".git").mkdir()
    (tmp_path / "main.py").write_text("x = 1\n")

    report = run_doctor(tmp_path, dry_run=True)

    assert report.preview is not None
    assert report.preview.total_ingest >= 1
    assert "main.py" in str(report.preview.would_ingest)
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Manual user inspection of `_SELF_OUTPUT_DIRS` + `.graphify/profile.yaml` to debug self-ingestion | `graphify doctor` single-call diagnostic | Phase 29 (this) | Closes the v1.6 self-ingestion-loop debugging gap that motivated the entire v1.7 milestone |
| Run-then-observe to see what `detect()` would skip | `graphify doctor --dry-run` | Phase 29 (this) | Eliminates destructive trial-and-error for new vault adapters |

**Deprecated/outdated:** None — Phase 29 is purely additive.

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | `dataclass` is preferred over `NamedTuple` for `DoctorReport` because of mutable list fields | Standard Stack §Alternatives | Low — both work; planner can override with NamedTuple if preferred |
| A2 | Substring matching is sufficient for `_FIX_HINTS` (no regex needed) | Fix-Hint Inventory | Low — covers all 25-ish patterns inventoried; can switch to regex if a future error message has variable substrings that need capturing |
| A3 | When `resolved.source == "default"`, `would_self_ingest` should be False (skip the check) to preserve v1.0 backcompat (D-12) | `would_self_ingest` Computation | MEDIUM — needs user/planner confirmation. Alternative: ALWAYS compute, accept that legacy `graphify run` from a non-vault dir will exit 1 from doctor. Conservative recommendation: skip for `source="default"` |
| A4 | The 4-source ignore-list display is a `dict[str, list[str]]` keyed by source label, not a flat `list[str]` | Pattern 1 example, `_build_ignore_list` | Low — D-37 says "grouped by source"; dict-of-lists is the natural shape. Planner may prefer a list of `(source, entry)` tuples for ordered display |
| A5 | `_load_graphifyignore` walking up to filesystem root requires test fixtures to place a `.git` halt marker | Pitfall 6 | Low — empirically required by reading `detect.py:323` |

## Open Questions (RESOLVED)

> RESOLVED: Each numbered question below carries an inline `RESOLVED:` marker pointing to the CONTEXT.md decision and/or plan must_have where the recommendation was locked.

1. **Should `would_self_ingest` apply when `resolved.source == "default"`?**
   - What we know: D-12 mandates v1.0 backcompat with `notes_dir=graphify-out/obsidian` inside scan_root.
   - What's unclear: Whether doctor should flag this as a "would self-ingest" issue (telling users to migrate to vault layout) or treat it as backcompat-OK.
   - Recommendation: Treat as backcompat-OK (skip the check when `source="default"`). The Phase 28 nesting guard handles the actual scan-time self-ingestion safely.

2. **Does the `output-manifest.json` history section warrant its own report section, or fold into "Output Destination"?**
   - What we know: D-34 lists 5 fixed sections; manifest history is not one of them.
   - What's unclear: Where in the report `manifest_history` surfaces.
   - Recommendation: Fold into "Output Destination" as a sub-list ("Recent runs: <run_id> @ <timestamp>"). Keeps the section count at 5/6.

3. **`detect()`'s current `skipped_sensitive` key — keep parallel, or fold into new `skipped["sensitive"]`?**
   - What we know: `detect()` already returns `skipped_sensitive: list[str]` (`detect.py:592`).
   - What's unclear: Whether to keep the legacy key for backcompat OR rename.
   - Recommendation: Keep `skipped_sensitive` for backcompat AND add `skipped["sensitive"]` as a copy. Zero-cost, zero-risk.

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| Python stdlib (`pathlib`, `dataclasses`, `json`, `sys`, `re`) | All doctor.py logic | ✓ | 3.10+ | — |
| PyYAML | Reading `.graphify/profile.yaml` (via `load_profile`) | ✓ (optional dep, project-level) | per pyproject.toml `[obsidian]` extra | Doctor degrades gracefully — emits "PyYAML not installed" recommended fix when vault detected without PyYAML |
| `graphify.output.ResolvedOutput`, `is_obsidian_vault`, `resolve_output` | Phase 27 contract consumed by doctor | ✓ | shipped Phase 27 | — |
| `graphify.detect._load_output_manifest`, `_is_nested_output`, `_is_ignored`, `_SELF_OUTPUT_DIRS`, `_load_graphifyignore` | Phase 28 contract consumed by doctor | ✓ | shipped Phase 28 | — |
| `graphify.profile.validate_profile`, `load_profile` | Profile validation surface | ✓ | stable since v1.0 | — |

**Missing dependencies with no fallback:** None.

**Missing dependencies with fallback:** PyYAML — if the user has installed graphify without the `[obsidian]` extra AND CWD is a vault, doctor reports the missing-PyYAML refusal as a recommended fix. Doctor itself does not import PyYAML directly.

## Validation Architecture

### Test Framework

| Property | Value |
|----------|-------|
| Framework | pytest 8.x (per `pyproject.toml`; verified by `tests/conftest.py` and `pytest tests/ -q` from CLAUDE.md) |
| Config file | `pyproject.toml` (no separate pytest.ini) |
| Quick run command | `pytest tests/test_doctor.py -q` |
| Full suite command | `pytest tests/ -q` |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| VAULT-14 | `graphify doctor` prints all 5 report sections | unit | `pytest tests/test_doctor.py::test_format_report_includes_all_sections -x` | ❌ Wave 0 (new file) |
| VAULT-14 | `graphify doctor` exits 0 on valid configuration | integration (subprocess) | `pytest tests/test_main_flags.py::test_doctor_valid_exits_0 -x` | ❌ Wave 0 (extend existing) |
| VAULT-14 | `graphify doctor` exits 1 when profile invalid | integration | `pytest tests/test_main_flags.py::test_doctor_invalid_profile_exits_1 -x` | ❌ Wave 0 |
| VAULT-14 | `graphify doctor` exits 1 when output destination unresolvable (missing profile in vault) | integration | `pytest tests/test_main_flags.py::test_doctor_unresolvable_dest_exits_1 -x` | ❌ Wave 0 |
| VAULT-14 | `graphify doctor` exits 1 when `would_self_ingest` is True | unit | `pytest tests/test_doctor.py::test_run_doctor_self_ingest_flagged -x` | ❌ Wave 0 |
| VAULT-14 | Ignore-list section shows union of 4 sources, grouped | unit | `pytest tests/test_doctor.py::test_ignore_list_grouped_by_source -x` | ❌ Wave 0 |
| VAULT-14 | Recommended Fixes section emits `_FIX_HINTS` lines for each issue | unit | `pytest tests/test_doctor.py::test_fix_hints_mapping -x` | ❌ Wave 0 |
| VAULT-14 | Recommended Fixes prints "No issues detected" when clean | unit | `pytest tests/test_doctor.py::test_no_issues_message -x` | ❌ Wave 0 |
| VAULT-15 | `--dry-run` shows would-ingest count + first 10 sample | unit | `pytest tests/test_doctor.py::test_dry_run_preview_bounded -x` | ❌ Wave 0 |
| VAULT-15 | `--dry-run` shows would-skip grouped by 5 reasons (`nesting`, `exclude-glob`, `manifest`, `sensitive`, `noise-dir`), first 5 each | unit | `pytest tests/test_doctor.py::test_dry_run_skip_groups -x` | ❌ Wave 0 |
| VAULT-15 | `--dry-run` writes nothing to disk | integration | `pytest tests/test_main_flags.py::test_doctor_dry_run_no_writes -x` | ❌ Wave 0 |
| VAULT-15 | `--dry-run` calls real `detect()` (preview ≡ actual scan) | unit | `pytest tests/test_doctor.py::test_dry_run_uses_real_detect -x` | ❌ Wave 0 |
| VAULT-15 | `detect()` return shape includes `skipped: dict[str, list[str]]` keyed by 5 reason labels | unit | `pytest tests/test_detect.py::test_detect_surfaces_skip_reasons -x` | ❌ Wave 0 (extend existing test_detect.py) |
| VAULT-15 | `detect()` skip-reason backcompat: existing `files`, `total_files`, `skipped_sensitive` keys unchanged | unit | `pytest tests/test_detect.py::test_detect_return_shape_backcompat -x` | ❌ Wave 0 |

### Sampling Rate

- **Per task commit:** `pytest tests/test_doctor.py tests/test_detect.py tests/test_main_flags.py -q`
- **Per wave merge:** `pytest tests/ -q`
- **Phase gate:** Full suite green before `/gsd-verify-work`.

### Wave 0 Gaps

- [ ] `tests/test_doctor.py` — covers VAULT-14, VAULT-15 unit tests (new file, ~12 tests)
- [ ] `tests/test_detect.py` — extend with skip-reason surfacing tests (2 new tests)
- [ ] `tests/test_main_flags.py` — extend with `doctor` subcommand subprocess tests (4 new tests)
- [ ] No new framework install needed — pytest already installed.

## Project Constraints (from CLAUDE.md)

- **Python 3.10+** on CI 3.10 and 3.12 — `from __future__ import annotations` first import; `dict[K,V]` not `Dict`; `str | None` not `Optional[str]`.
- **No new required dependencies** — stdlib only. PyYAML stays optional under `[obsidian]` extra; doctor degrades gracefully.
- **All file paths confined to output directory per `security.py` patterns** — doctor reads-only; no path writes; `would_self_ingest` predicate uses `Path.resolve().relative_to()` defensively.
- **Pure unit tests — no network, no filesystem side effects outside `tmp_path`** — all `tests/test_doctor.py` cases use `tmp_path` exclusively.
- **`[graphify]`-prefixed stderr** for warnings/info (build.py, cluster.py convention) — `format_report` lines per D-34 follow this prefix.
- **Validators return `list[str]` of errors, not raised exceptions** — `validate_profile()` ABI unchanged per D-36; doctor accumulates errors the same way.
- **One test file per module** — `tests/test_doctor.py` pairs with `graphify/doctor.py`.
- **No linter/formatter** — match existing 4-space indent and module docstring style.

## Sources

### Primary (HIGH confidence)
- `graphify/output.py` (lines 1–172) — full module read; `ResolvedOutput` shape, `is_obsidian_vault`, `resolve_output`, `_refuse` SystemExit pattern.
- `graphify/profile.py` (lines 200–550 read) — `validate_profile()` ABI, `output:` schema branch (lines 422–480), `validate_vault_path` and `validate_sibling_path` failure messages.
- `graphify/detect.py` (lines 1–595 read) — `_SELF_OUTPUT_DIRS`, `_is_nested_output`, `_is_noise_dir`, `_load_graphifyignore`, `_is_ignored`, `_load_output_manifest`, `_save_output_manifest`, `detect()` return shape and pruning sites.
- `graphify/__main__.py` (lines 1162–2329 mapped) — `main()` dispatch, `--obsidian` branch (line 1291), `run` branch (line 2120), `vault-promote` branch (line 2289), `--help` block (line 1170).
- `tests/test_main_flags.py` (lines 1–155) — subprocess CLI test pattern.
- `tests/test_main_cli.py` (lines 1–60) — `_run_cli` helper pattern.
- `tests/test_detect.py` (lines 1–110) — `tmp_path` fixture patterns, `detect()` assertions.
- `.planning/phases/29-doctor-diagnostics-dry-run-preview/29-CONTEXT.md` — D-30 through D-41 locked decisions.
- `.planning/phases/27-vault-detection-profile-driven-output-routing/27-CONTEXT.md` — `ResolvedOutput` integration contract D-13.
- `.planning/phases/28-self-ingestion-hardening/28-CONTEXT.md` — output-manifest schema D-22, D-23, D-24, D-25, nesting guard D-18.
- `.planning/REQUIREMENTS.md` — VAULT-14, VAULT-15 verbatim.
- `./CLAUDE.md` — project constraints.

### Secondary (MEDIUM confidence)
- Python 3.10 stdlib `pathlib.Path.resolve(strict=False)` semantics — confirmed by parallel use in `output.py:60`.

### Tertiary (LOW confidence)
- None — all claims grounded in repo source or locked CONTEXT.

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — stdlib only; every primitive verified in source.
- Architecture: HIGH — single new module + one additive `detect()` change + one dispatch branch; pattern matches `analyze.py`/`report.py`.
- Pitfalls: HIGH — derived from reading `output.py:_refuse` flow, `_load_graphifyignore` walk-up logic, and existing test fixture patterns.
- Skip-reason surfacing approach: HIGH — Approach A (extend return shape) is the lowest-risk option and matches existing `nested_paths`/`skipped_sensitive` accumulator pattern in `detect()`.
- Fix-hint inventory: HIGH — exhaustively walked validator source; ~25 patterns mapped.
- `would_self_ingest` definition: MEDIUM — open question on `resolved.source == "default"` behavior (A3) needs planner/user confirmation.

**Research date:** 2026-04-28
**Valid until:** 2026-05-28 (stable surface — Phase 27/28 contracts locked)
