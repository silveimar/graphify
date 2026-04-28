# Phase 29: Doctor Diagnostics & Dry-Run Preview - Pattern Map

**Mapped:** 2026-04-28
**Files analyzed:** 6 (2 NEW, 4 MODIFY)
**Analogs found:** 6 / 6

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|-------------------|------|-----------|----------------|---------------|
| `graphify/doctor.py` (NEW) | pipeline-stage module (diagnostic) | request-response (read state → build report → format) | `graphify/output.py` (NamedTuple + pure functions + `_refuse` stderr-and-exit pattern); secondary: `graphify/report.py` (renderer pattern) | exact (composite) |
| `graphify/detect.py` (MODIFY — add `skipped` return key) | scanner | additive return-shape extension | self — extend existing `nested_paths` / `skipped_sensitive` accumulator pattern (lines ~471, 488, 590) | exact (self-extension) |
| `graphify/__main__.py` (MODIFY — `doctor` dispatch branch) | CLI dispatch | request-response | `vault-promote` branch (lines 2289–2323) — argparse + `sys.exit` pattern; secondary: `--obsidian` branch (lines 1291–1326) for the `--dry-run` manual flag loop | exact |
| `tests/test_doctor.py` (NEW) | unit tests | tmp_path fixture | `tests/test_output.py` (pure unit tests against module functions) | exact |
| `tests/test_detect.py` (MODIFY — `test_detect_skip_reasons`) | unit tests | tmp_path fixture | self — existing `detect()` assertion patterns at lines 41–53 | exact (self-extension) |
| `tests/test_main_flags.py` (MODIFY — 4 doctor CLI tests) | integration tests (subprocess) | request-response | self — `_graphify()` helper at lines 12–25; vault fixture pattern at lines 53–63 | exact (self-extension) |

## Pattern Assignments

### `graphify/doctor.py` (NEW — pure-function module)

**Primary analog:** `graphify/output.py` (172 lines — most direct stylistic precedent)
**Secondary analog:** `graphify/report.py` (renderer separation)

**Module header pattern** (`graphify/output.py` lines 1–22):
```python
"""Vault detection and output destination resolution (Phase 27).

Resolves the (vault, notes_dir, artifacts_dir, source) tuple consumed by
the run/--obsidian commands, Phase 28 self-ingest pruning, and Phase 29
doctor diagnostics.

Decisions implemented:
  - D-04: strict CWD-only `.obsidian/` detection (no parent walk)
  ...
"""
from __future__ import annotations

import sys
from pathlib import Path
from typing import Literal, NamedTuple
```
→ Mirror: `"""Doctor diagnostics — read-only orchestration over Phase 27/28 primitives.\n\nDecisions implemented:\n  - D-30..D-41 ..."""`. Use `from __future__ import annotations`. Stdlib imports only.

**Container shape pattern** (`graphify/output.py` lines 25–31 — `NamedTuple`):
```python
class ResolvedOutput(NamedTuple):
    vault_detected: bool
    vault_path: Path | None
    notes_dir: Path
    artifacts_dir: Path
    source: Literal["profile", "cli-flag", "default"]
    exclude_globs: tuple[str, ...] = ()   # Phase 28 D-14
```
→ For `DoctorReport` and `PreviewSection`, RESEARCH §A1 recommends `dataclass(frozen=False)` over NamedTuple because of mutable list/dict fields with `field(default_factory=list)`. Either matches house style — RESEARCH calls this LOW risk. Pick one and stay consistent.

**Stderr-and-fail pattern** (`graphify/output.py` lines 38–41):
```python
def _refuse(msg: str) -> SystemExit:
    """Print actionable error to stderr and prepare SystemExit(1)."""
    print(f"[graphify] {msg}", file=sys.stderr)
    return SystemExit(1)
```
→ Doctor itself does NOT raise; it accumulates errors. But it MUST catch `SystemExit` from `resolve_output()` (which uses `_refuse`). Pattern: `try: resolved = resolve_output(cwd); except SystemExit: resolved = None`.

**Renderer pattern** (`graphify/report.py` lines 70–86 — `generate()` builds `lines: list[str]` then `"\n".join(lines)`):
```python
def generate(G, communities, cohesion_scores, community_labels, ...) -> str:
    today = date.today().isoformat()
    lines = [
        f"# Graph Analysis - {root}  ({today})",
        "",
        "> Multi-perspective analysis ...",
    ]
    # ... append more sections via lines += [...]
    return "\n".join(lines)
```
→ Mirror in `format_report(report: DoctorReport) -> str`: build `lines: list[str]`, append fixed-order sections per D-34 (Vault Detection / Profile Validation / Output Destination / Ignore-List / Preview / Recommended Fixes), prefix every emitted info line with `[graphify]` per D-34 + CLAUDE.md convention, return `"\n".join(lines)`.

**Pure-function module signature pattern** (`graphify/output.py:resolve_output` line 44):
```python
def resolve_output(cwd: Path, *, cli_output: str | None = None) -> ResolvedOutput:
```
→ Mirror exactly per D-32: `def run_doctor(cwd: Path, *, dry_run: bool = False) -> DoctorReport:` and `def format_report(report: DoctorReport) -> str:`. Keyword-only kwargs. Type hints on every parameter and return.

---

### `graphify/detect.py` (MODIFY — add `skipped: dict[str, list[str]]` return key)

**Analog:** self — existing accumulator pattern in `detect()` itself.

**Existing accumulator pattern** (`graphify/detect.py` lines 471, 488, 503):
```python
skipped_sensitive: list[str] = []          # line 471
ignore_patterns = _load_graphifyignore(root)
...
nested_paths: list[str] = []               # line 488
...
prior_files: set[str] = set()              # line 503 (Phase 28)
```
→ Mirror by adding 4 more list accumulators OR a single `skipped: dict[str, list[str]] = {"nesting": [], "exclude-glob": [], "manifest": [], "sensitive": [], "noise-dir": []}`. RESEARCH §"Approach A" recommends the dict. Five existing pruning sites need an `.append()` added (lines 506–558 region).

**Existing return shape pattern** (`graphify/detect.py` end of `detect()` ~line 595):
```python
return {
    "files": {k.value: v for k, v in files.items()},
    "total_files": total_files,
    "total_words": total_words,
    "needs_graph": needs_graph,
    "warning": warning,
    "skipped_sensitive": skipped_sensitive,
    "graphifyignore_patterns": len(ignore_patterns),
}
```
→ Additive change ONLY: add `"skipped": skipped` key. Preserve all existing keys (RESEARCH §"Open Questions" #3: keep `skipped_sensitive` AND add `skipped["sensitive"]` as a copy — zero-cost backcompat).

**Pruning sites to instrument** (currently silent `continue` statements):
- Noise/hidden dir pruning (line ~509–518): add to `skipped["noise-dir"]` and `skipped["exclude-glob"]` per branch.
- `_is_nested_output` pruning (line ~519): already accumulates to `nested_paths` — copy into `skipped["nesting"]`.
- File-level `_is_ignored` (line ~559): add to `skipped["exclude-glob"]`.
- File-level `prior_files` manifest skip (line ~562): add to `skipped["manifest"]`.
- `_is_sensitive` accumulator (line ~565): already in `skipped_sensitive` — copy into `skipped["sensitive"]`.

**Existing `[graphify] WARNING:` stderr pattern** (`graphify/detect.py` lines 482–488 — D-20 nesting summary):
```python
if nested_paths:
    deepest = max(nested_paths, key=lambda p: p.count(os.sep))
    print(
        f"[graphify] WARNING: skipped {len(nested_paths)} nested output path(s) "
        f"(deepest: {deepest})",
        file=sys.stderr,
    )
```
→ No new stderr lines needed for the additive `skipped` key. Doctor consumes `skipped` directly.

---

### `graphify/__main__.py` (MODIFY — `doctor` dispatch branch + help line)

**Primary analog:** `vault-promote` branch (`graphify/__main__.py` lines 2289–2323).
**Secondary analog:** `--obsidian` branch (lines 1291–1326) for manual `--dry-run` flag handling precedent.

**Dispatch + argparse pattern** (`graphify/__main__.py` lines 2289–2323):
```python
elif cmd == "vault-promote":
    # graphify vault-promote --vault PATH [--threshold N] [--graph PATH]
    import argparse as _ap

    _p_vp = _ap.ArgumentParser(
        prog="graphify vault-promote",
        description="Promote knowledge graph nodes into an Obsidian vault (VAULT-01/05/06)",
    )
    _p_vp.add_argument("--vault", required=True, help="...")
    _p_vp.add_argument("--threshold", type=int, default=3, help="...")
    opts = _p_vp.parse_args(sys.argv[2:])
    from graphify.vault_promote import promote
    summary = promote(...)
    print(f"[graphify] vault-promote complete: ...")
    sys.exit(0)
```
→ Mirror for `doctor`:
```python
elif cmd == "doctor":
    import argparse as _ap
    _p_dr = _ap.ArgumentParser(
        prog="graphify doctor",
        description="Diagnose vault detection / profile / output destination / ignore-list (VAULT-14/15)",
    )
    _p_dr.add_argument("--dry-run", action="store_true",
                       help="Preview which files would be ingested/skipped without writing")
    opts = _p_dr.parse_args(sys.argv[2:])
    from graphify.doctor import run_doctor, format_report
    report = run_doctor(Path.cwd(), dry_run=opts.dry_run)
    print(format_report(report))
    sys.exit(1 if report.is_misconfigured() else 0)
```
RESEARCH §"Don't Hand-Roll" suggests manual `if "--dry-run" in sys.argv[2:]` to match `--obsidian` style. Either is fine; argparse is cleaner for the help text. Vault-promote sets the precedent at this size.

**Help-block pattern** (`graphify/__main__.py` lines 1170–1228 — every command gets a single line + indented options):
```python
print("  vault-promote         promote graph nodes into an Obsidian vault (VAULT-01/05/06)")
print("    --vault <path>          target vault directory (required)")
print("    --threshold N           minimum node degree (default: 3)")
```
→ Add at the appropriate alphabetic position (next to other vault verbs):
```python
print("  doctor                  diagnose vault/profile/output configuration (VAULT-14/15)")
print("    --dry-run               preview which files would be ingested/skipped, no writes")
```

---

### `tests/test_doctor.py` (NEW — pure unit tests)

**Analog:** `tests/test_output.py` (lines 1–40 are the closest stylistic precedent).

**Imports + fixture pattern** (`tests/test_output.py` lines 1–13):
```python
"""Unit tests for graphify/output.py — Phase 27 vault detection + resolution."""
from __future__ import annotations

from pathlib import Path

import pytest

from graphify.output import ResolvedOutput, is_obsidian_vault, resolve_output


def test_is_obsidian_vault_true_when_dir_present(tmp_path):
    (tmp_path / ".obsidian").mkdir()
    assert is_obsidian_vault(tmp_path) is True
```
→ Mirror header: `"""Unit tests for graphify/doctor.py — Phase 29 diagnostics + dry-run."""`, then `from graphify.doctor import run_doctor, format_report, DoctorReport, PreviewSection`. All tests take `tmp_path`.

**Vault fixture pattern** (from `tests/test_main_flags.py` lines 55–63 — applies to doctor unit tests too):
```python
vault = tmp_path / "vault"
vault.mkdir()
(vault / ".obsidian").mkdir()
(vault / ".graphify").mkdir()
(vault / ".graphify" / "profile.yaml").write_text(
    "output:\n  mode: vault-relative\n  path: Atlas/Generated\n"
)
```
→ Reuse verbatim. RESEARCH §Pitfall 6: also `(tmp_path / ".git").mkdir()` to halt `_load_graphifyignore` walk-up.

**`pytest.importorskip` for PyYAML guard pattern** (`tests/test_main_flags.py` line 54):
```python
def test_run_in_vault_emits_detection_report(tmp_path):
    pytest.importorskip("yaml")
```
→ Apply to any doctor test that exercises `resolve_output()` against a vault-with-profile (PyYAML required for `load_profile`).

---

### `tests/test_detect.py` (MODIFY — `test_detect_skip_reasons`)

**Analog:** self — existing patterns.

**Existing detect-assertion pattern** (`tests/test_detect.py` lines 41–53):
```python
def test_detect_finds_fixtures():
    result = detect(FIXTURES)
    assert result["total_files"] >= 2
    assert "code" in result["files"]
    assert "document" in result["files"]
```
→ Mirror for skip-reason surfacing:
```python
def test_detect_surfaces_skip_reasons(tmp_path):
    (tmp_path / ".git").mkdir()
    (tmp_path / "node_modules").mkdir()
    (tmp_path / "node_modules" / "x.js").write_text("x")
    (tmp_path / "main.py").write_text("x = 1\n")
    result = detect(tmp_path)
    assert "skipped" in result
    assert isinstance(result["skipped"], dict)
    assert set(result["skipped"].keys()) >= {"nesting", "exclude-glob", "manifest", "sensitive", "noise-dir"}
    assert any("node_modules" in p for p in result["skipped"]["noise-dir"])

def test_detect_return_shape_backcompat(tmp_path):
    """Existing keys must remain unchanged after additive 'skipped' addition."""
    (tmp_path / ".git").mkdir()
    (tmp_path / "main.py").write_text("x = 1\n")
    result = detect(tmp_path)
    for key in ("files", "total_files", "total_words", "needs_graph",
                "warning", "skipped_sensitive", "graphifyignore_patterns"):
        assert key in result
```

---

### `tests/test_main_flags.py` (MODIFY — 4 doctor CLI integration tests)

**Analog:** self — `_graphify()` helper + vault fixture pattern.

**Subprocess helper pattern** (`tests/test_main_flags.py` lines 12–25):
```python
def _graphify(args: list[str], cwd: Path, env: dict | None = None) -> subprocess.CompletedProcess:
    """Invoke `python -m graphify <args>` in cwd, return CompletedProcess."""
    full_env = os.environ.copy()
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
→ Reuse as-is. New tests call `_graphify(["doctor"], cwd=vault)` and `_graphify(["doctor", "--dry-run"], cwd=vault)`.

**Refusal-assertion pattern** (`tests/test_main_flags.py` lines 73–80):
```python
def test_run_in_vault_no_profile_refuses(tmp_path):
    vault = tmp_path / "vault"
    vault.mkdir()
    (vault / ".obsidian").mkdir()
    result = _graphify(["run", "--router"], cwd=vault)
    assert result.returncode != 0
    assert "no .graphify/profile.yaml found" in result.stderr
```
→ Mirror for `test_doctor_invalid_profile_exits_1`, `test_doctor_unresolvable_dest_exits_1`. Use substring assertions, not equality (per RESEARCH §Pitfall 1: `[graphify] vault detected at ...` lines from `output.py:88` will appear in stderr — match on substrings).

**Required new tests** (per RESEARCH "Phase Requirements → Test Map"):
1. `test_doctor_valid_exits_0` — vault with valid profile → exit 0, all 5 sections in stdout, "No issues detected" line.
2. `test_doctor_invalid_profile_exits_1` — vault with malformed `output:` → exit 1, error substring + recommended-fix line in stdout/stderr.
3. `test_doctor_unresolvable_dest_exits_1` — vault with no profile → exit 1.
4. `test_doctor_dry_run_no_writes` — `doctor --dry-run` produces preview + creates no files in `tmp_path` (assert directory tree unchanged after invocation, modulo `.git` marker).

---

## Shared Patterns

### `[graphify]`-prefixed stderr lines
**Source:** `graphify/output.py` line 40, `graphify/detect.py` lines 484, 376, multiple sites in `__main__.py`.
**Apply to:** All `format_report()` info lines; doctor refusal and recommended-fix lines.
```python
print(f"[graphify] {msg}", file=sys.stderr)
```
Per CLAUDE.md "[graphify]-prefixed stderr" convention and D-34. Note: `format_report()` returns a string; the `print()` happens in `__main__.py`. The prefix lives in the formatted lines themselves.

### `from __future__ import annotations` first
**Source:** Every module in `graphify/` — verified at `output.py:18`, `detect.py:1` region, `report.py:2`, `analyze.py:2`.
**Apply to:** `doctor.py` and `tests/test_doctor.py`.
Per CLAUDE.md "Type hints" + "Use `from __future__ import annotations` for forward compatibility (present in all modules)".

### Pure-function modules with no shared mutable state
**Source:** Every module in `graphify/` (CLAUDE.md "Architecture": "Each stage is a single function in its own module... no shared state, no side effects outside `graphify-out/`").
**Apply to:** `doctor.py` — `run_doctor()` reads filesystem, returns dataclass, never writes. `format_report()` is pure (str → str).

### Lazy/function-local imports for optional/circular deps
**Source:** `graphify/output.py` lines 73–80, 117–119, 137 (`from graphify.profile import load_profile` inside the function body).
**Apply to:** `doctor.py` should import `from graphify.detect import _SELF_OUTPUT_DIRS, _is_nested_output, _load_graphifyignore, _load_output_manifest, detect` at module top (no circular concern), but PyYAML probing should be `try: import yaml` inside `run_doctor()` per RESEARCH §Pitfall 2.

### Validators return `list[str]`, never raise
**Source:** `graphify/profile.py:validate_profile()` line 209 (returns `list[str]`).
**Apply to:** D-36 locks this — `doctor.py` must call `validate_profile()` and accumulate the returned list into `report.profile_validation_errors`. Never wrap it in try/except.

### Catch-`SystemExit` for `resolve_output()` failure modes
**Source:** `graphify/output.py:_refuse` (line 38) raises `SystemExit(1)` for missing profile / missing PyYAML / malformed mode / sibling validators. RESEARCH §Pattern 2.
**Apply to:** `doctor.py:run_doctor()`:
```python
try:
    resolved = resolve_output(cwd, cli_output=None)
except SystemExit:
    resolved = None  # report as "unresolvable" → exit 1 per D-35
```
Note: `resolve_output()` writes to stderr BEFORE refusing (RESEARCH §Pitfall 1) — tests must use substring assertions, not stderr equality.

### Subprocess CLI tests with `tmp_path`, `capture_output=True, text=True, timeout=60`
**Source:** `tests/test_main_flags.py` lines 17–24, `tests/test_main_cli.py` lines 32–40.
**Apply to:** All 4 new `tests/test_main_flags.py` doctor tests.

### Test fixture: `.git` marker to halt `_load_graphifyignore` walk-up
**Source:** RESEARCH §Pitfall 6 — `_load_graphifyignore(root)` (`detect.py:300`) walks up to filesystem root.
**Apply to:** Every new test that exercises ignore-list. Place `(tmp_path / ".git").mkdir()` at fixture setup.

---

## No Analog Found

None. Every file in this phase has a clear in-repo precedent. Phase 29 is purely a composition exercise per RESEARCH §"Don't Hand-Roll" key insight: "Every primitive exists; the new code is a 200-line module that reads them, builds a dataclass, and renders text."

---

## Metadata

**Analog search scope:**
- `graphify/output.py` (172 lines, full read) — primary stylistic precedent
- `graphify/detect.py` (lines 250–595) — `_SELF_OUTPUT_DIRS`, `_is_nested_output`, `_is_noise_dir`, `_load_graphifyignore`, `_is_ignored`, `_load_output_manifest`, `detect()` body
- `graphify/__main__.py` (lines 1160–1228 help block, 1291–1326 `--obsidian` branch, 2120–2170 `run` branch, 2289–2323 `vault-promote` branch)
- `graphify/report.py` (lines 1–40, 300–409) — renderer pattern
- `graphify/analyze.py` (lines 1–30) — pure-function module header style
- `tests/test_main_flags.py` (lines 1–80) — `_graphify` helper + vault fixture pattern
- `tests/test_main_cli.py` (lines 1–60) — `_run_cli` alternate helper
- `tests/test_detect.py` (lines 1–80) — detect-assertion patterns
- `tests/test_output.py` (lines 1–40) — pure-unit-test stylistic precedent
- `tests/test_profile.py` (lines 1–50) — validator-test stylistic precedent

**Files scanned:** 10
**Pattern extraction date:** 2026-04-28
