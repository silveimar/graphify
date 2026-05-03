# Phase 58: Vault CLI parity & hygiene - Pattern Map

**Mapped:** 2026-05-03
**Files analyzed:** 4 (2 new, 2 modified)
**Analogs found:** 4 / 4

---

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|-------------------|------|-----------|----------------|---------------|
| `graphify/output.py` (modify — add 2 functions) | utility / resolver | request-response | `graphify/output.py` itself (`_refuse`, `resolve_execution_paths`) | exact (same file) |
| `tests/test_vault_parity.py` (new) | test | request-response | `tests/test_doctor.py` | exact (same role, same vault-fixture pattern) |
| `tests/test_vault_cli.py` (modify — add subprocess tests) | test | request-response | `tests/test_vault_cli.py` itself | exact (same file) |
| `tests/test_detect.py` (modify — add 1 regression-lock test) | test | transform | `tests/test_detect.py` itself (lines 280-340, existing HYG-01 behavioral tests) | exact (same file, same constant-assertion style) |

---

## Pattern Assignments

### `graphify/output.py` — add `resolve_vault_for_parity()` and `_emit_vault_error()`

**Analog:** `graphify/output.py` existing functions `_refuse()` (lines 67-69) and `resolve_execution_paths()` (lines 151-190).

**Imports pattern** (lines 1-11 — already present, no new imports needed at module level):
```python
from __future__ import annotations

import sys
from pathlib import Path
from typing import Literal, NamedTuple
```
Note: `io` and `contextlib` must be imported inside `resolve_vault_for_parity()` as local imports (same pattern used by `run_doctor()` in `doctor.py` which also does `import io, contextlib` at function scope via module-level `import contextlib; import io`). Since `doctor.py` imports them at module level, the planner should add `import contextlib` and `import io` to `output.py`'s module-level imports.

**Existing `_refuse()` pattern** (lines 67-69 — companion to new `_emit_vault_error()`):
```python
def _refuse(msg: str) -> SystemExit:
    """Print actionable error to stderr and prepare SystemExit(1)."""
    print(f"[graphify] {msg}", file=sys.stderr)
    return SystemExit(1)
```
`_emit_vault_error()` follows the same return-a-SystemExit convention (caller does `raise _emit_vault_error(...)`). Do NOT change `_refuse()` — existing callers stay unchanged.

**New `_emit_vault_error()` pattern** (add immediately after `_refuse()` at line 70):
```python
def _emit_vault_error(msg: str, hint: str, *, code: int = 1) -> SystemExit:
    """Emit [graphify] error: + hint: lines to stderr and return SystemExit(code).

    VAUX-02: two-line format mirrors doctor.py _FIX_HINTS pattern (D-05).
    Callers: raise _emit_vault_error(msg, hint, code=...)
    """
    print(f"[graphify] error: {msg}", file=sys.stderr)
    print(f"  hint: {hint}", file=sys.stderr)
    return SystemExit(code)
```

**New `resolve_vault_for_parity()` pattern** (add after `resolve_execution_paths()`, around line 195):
```python
def resolve_vault_for_parity(
    cwd: Path,
    *,
    explicit_vault: Path | None = None,
    env_vault: str | None = None,
    vault_list_file: Path | None = None,
) -> dict:
    """Return structured parity dict for VAUX-01 test assertions.

    Dict shape:
      {
        "vault_path": Path | None,       # resolved.vault_path
        "source": str,                   # resolved.source
        "profile_path": Path | None,     # vault/.graphify/profile.yaml or None
        "profile_mode": str | None,      # output.mode from profile, or None
        "warnings": list[str],           # stderr lines emitted during resolution
      }
    Calls resolve_execution_paths() — never duplicates resolution logic.
    """
    import contextlib
    import io

    captured = io.StringIO()
    try:
        with contextlib.redirect_stderr(captured):
            resolved = resolve_execution_paths(
                cwd,
                explicit_vault=explicit_vault,
                env_vault=env_vault,
                vault_list_file=vault_list_file,
            )
    except SystemExit:
        raise

    warnings = [
        ln.strip() for ln in captured.getvalue().splitlines() if ln.strip()
    ]

    profile_path: Path | None = None
    profile_mode: str | None = None
    if resolved.vault_path is not None:
        pp = resolved.vault_path / ".graphify" / "profile.yaml"
        if pp.exists():
            profile_path = pp
            try:
                import yaml  # noqa: F401
                from graphify.profile import load_profile
                prof = load_profile(resolved.vault_path)
                out_block = prof.get("output") if isinstance(prof, dict) else None
                if isinstance(out_block, dict):
                    profile_mode = out_block.get("mode")
            except Exception:
                pass

    return {
        "vault_path": resolved.vault_path,
        "source": resolved.source,
        "profile_path": profile_path,
        "profile_mode": profile_mode,
        "warnings": warnings,
    }
```

**Stderr-capture model** (from `graphify/doctor.py` lines 417-430 — copy this pattern exactly into `resolve_vault_for_parity()`):
```python
captured = io.StringIO()
try:
    with contextlib.redirect_stderr(captured):
        report.resolved_output = resolve_output(cwd_resolved)
except SystemExit:
    report.resolved_output = None
    for line in captured.getvalue().splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        if stripped.startswith("[graphify] "):
            stripped = stripped[len("[graphify] "):]
        report.profile_validation_errors.append(stripped)
```

**Call sites for `_emit_vault_error()`** — replace `raise _refuse(...)` in these three D-07 failure locations:
- `_ensure_vault_root()` line ~75: `not p.is_dir()` → unknown vault (file or nonexistent)
- `_ensure_vault_root()` line ~78: `not is_obsidian_vault(p)` → no `.obsidian/` marker
- `_pick_vault_from_list_file()` ambiguous multi-root non-TTY path → exits 2 (already uses `raise SystemExit(2)`, not `_refuse`)

Hint strings (one per failure category, inline per D-05/D-06):
- No `.obsidian/` marker: `hint: "Pass the root of an Obsidian vault (must contain .obsidian/)."`
- Not a directory / nonexistent: `hint: "Check the path exists and is a directory, not a file."`
- Ambiguous vault-list: the existing multi-line stderr block already printed before `raise SystemExit(2)` — add a `hint:` line printed immediately before the `raise`.

---

### `tests/test_vault_parity.py` (new module)

**Analog:** `tests/test_doctor.py` (imports, `_make_vault`, `_VALID_PROFILE`, `pytest.importorskip`, `run_doctor` call with `resolved_output` param).
**Secondary analog:** `tests/test_vault_cli.py` (subprocess pattern for VAUX-02 CLI error tests).

**Imports pattern** (copy from `tests/test_doctor.py` lines 1-16, adapt for parity):
```python
"""Unit + integration tests for VAUX-01 parity and VAUX-02 error format (Phase 58)."""
from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import pytest

from graphify.doctor import run_doctor
from graphify.output import ResolvedOutput, resolve_vault_for_parity
```

**`_make_vault()` fixture** (copy verbatim from `tests/test_doctor.py` lines 20-35 — do NOT import it, replicate per D-08):
```python
def _make_vault(tmp_path: Path, *, profile_text: str | None = None) -> Path:
    """Create a synthetic Obsidian vault under tmp_path/vault.

    - .obsidian/  marks it as a vault (D-04)
    - .git/       halts _load_graphifyignore walk-up
    - .graphify/  for profile.yaml when profile_text is provided
    """
    vault = tmp_path / "vault"
    vault.mkdir()
    (vault / ".obsidian").mkdir()
    (vault / ".git").mkdir()
    (vault / ".graphify").mkdir()
    if profile_text is not None:
        (vault / ".graphify" / "profile.yaml").write_text(profile_text)
    return vault
```

**`_VALID_PROFILE` constant** (copy from `tests/test_doctor.py` lines 37-57 — same text):
```python
_VALID_PROFILE = (
    "taxonomy:\n"
    "  version: v1.8\n"
    "  root: Atlas/Sources/Graphify\n"
    "  folders:\n"
    "    moc: MOCs\n"
    "    thing: Things\n"
    "    statement: Statements\n"
    "    person: People\n"
    "    source: Sources\n"
    "    default: Things\n"
    "    unclassified: MOCs\n"
    "mapping:\n"
    "  min_community_size: 3\n"
    "output:\n"
    "  mode: vault-relative\n"
    "  path: Atlas/Generated\n"
)
```

**VAUX-01 parity test pattern** (modeled on `test_run_doctor_preflight_uses_pinned_vault_not_cwd` in `test_doctor.py` lines 154-175 — constructs `ResolvedOutput` explicitly and passes to `run_doctor(resolved_output=...)`):
```python
def test_parity_vault_cli_matches_doctor(tmp_path):
    """VAUX-01: resolve_vault_for_parity and run_doctor agree on vault_path + source."""
    pytest.importorskip("yaml")
    vault = _make_vault(tmp_path, profile_text=_VALID_PROFILE)
    parity = resolve_vault_for_parity(tmp_path, explicit_vault=vault)
    # Build the same ResolvedOutput and ask doctor to validate it
    resolved = ResolvedOutput(
        True,
        parity["vault_path"],
        parity["vault_path"] / "Atlas" / "Generated",
        parity["vault_path"].parent / "graphify-out",
        parity["source"],
        (),
    )
    report = run_doctor(tmp_path, resolved_output=resolved)
    assert report.resolved_output is not None
    assert report.resolved_output.vault_path == parity["vault_path"]
    assert report.resolved_output.source == parity["source"]
```

**VAUX-02 subprocess error test pattern** (copy from `tests/test_vault_cli.py` lines 40-62):
```python
def test_unknown_vault_nonexistent_path_error(tmp_path):
    """VAUX-02: --vault /nonexistent emits error+hint lines and exits non-zero."""
    r = subprocess.run(
        [sys.executable, "-m", "graphify", "--vault", str(tmp_path / "no-such-dir"), "doctor"],
        cwd=str(tmp_path),
        capture_output=True,
        text=True,
        timeout=60,
    )
    assert r.returncode != 0
    assert "[graphify] error:" in r.stderr
    assert "  hint:" in r.stderr
```

**VAUX-02 ambiguous vault-list exit-2 pattern** (copy from `tests/test_vault_cli.py` lines 63-80):
```python
def test_ambiguous_vault_list_exit2(tmp_path):
    pytest.importorskip("yaml")
    v1 = _make_vault(tmp_path / "a", "v1")  # note: _make_vault signature here uses parent
    # ...build list file with two valid vaults...
    r = subprocess.run(
        [sys.executable, "-m", "graphify", "--vault-list", str(lst), "doctor"],
        cwd=str(tmp_path),
        capture_output=True,
        text=True,
        timeout=60,
    )
    assert r.returncode == 2
    assert "  hint:" in r.stderr
```
Note: `test_vault_cli.py`'s `_make_vault(parent, name)` has a different signature from `test_doctor.py`'s `_make_vault(tmp_path, *, profile_text=...)`. For `test_vault_parity.py` use the `test_doctor.py` variant. To make multi-vault fixtures, call `_make_vault()` twice with different `tmp_path` subdirectories (e.g., `tmp_path / "a"` and `tmp_path / "b"`, passing each as `tmp_path` arg).

**Override-warning test pattern** (in-process, no subprocess — tests `_merge_vault_pins` via `graphify.__main__._resolve_cli_paths` or by comparing the warning string in parity dict):
```python
def test_global_local_override_warning(tmp_path, capsys):
    """VAUX-02: global --vault + per-command --vault produces override warning."""
    pytest.importorskip("yaml")
    vault = _make_vault(tmp_path, profile_text=_VALID_PROFILE)
    # Verify the warning string is emitted via subprocess (CLI surface only)
    r = subprocess.run(
        [
            sys.executable, "-m", "graphify",
            "--vault", str(vault),       # global pin
            "doctor",
            "--vault", str(vault),       # per-command pin (same path)
        ],
        cwd=str(tmp_path),
        capture_output=True,
        text=True,
        timeout=60,
    )
    # Assert the existing override warning text is present
    assert "[graphify] command --vault / --vault-list overrides global pin" in r.stderr
```

---

### `tests/test_vault_cli.py` — add VAUX-02 subprocess tests (if planner places them here)

**Decision note:** CONTEXT.md D-04 / Claude's Discretion says conflict tests may live in either `test_vault_parity.py` or `test_vault_cli.py`. The pattern below applies to both. Recommend `test_vault_parity.py` to keep existing `test_vault_cli.py` untouched.

**Existing subprocess pattern** (lines 40-62 — copy for any new tests added here):
```python
r = subprocess.run(
    [sys.executable, "-m", "graphify", "--vault", str(vault), "doctor"],
    cwd=str(repo),
    capture_output=True,
    text=True,
    timeout=60,
)
assert r.returncode == 0, r.stderr
assert "source: vault-cli" in r.stdout
```

---

### `tests/test_detect.py` — add HYG-01 regression-lock test

**Analog:** `tests/test_detect.py` lines 280-340 (the four HYG-01 behavioral tests already present). The new test is a **constant-membership guard**, not a behavioral file-scan test — it is simpler and shorter.

**Import to add** (at top of file, alongside existing `from graphify.detect import ...`):
```python
from graphify.corpus_prune import _SELF_OUTPUT_DIRS
```
Or use a local import inside the test function (same pattern as some late imports in the existing test file, e.g., line 245 `from graphify.detect import FileType`).

**New test function** (append after the last existing `_SELF_OUTPUT_DIRS`-touching test, around line 345):
```python
def test_self_ingestion_dirs_constant_excludes_both_spellings():
    """HYG-01 regression-lock: _SELF_OUTPUT_DIRS must always contain both spellings.

    Named intentional guard — survives future refactors of _is_noise_dir that
    might accidentally drop a spelling. Unlike the behavioral detect() tests
    above, this asserts the constant directly so any rename/removal is caught
    immediately regardless of file-scan behavior.

    Cite: .planning/quick/260427-rc7-fix-detect-self-ingestion/260427-rc7-SUMMARY.md
    Commit: 59d8b2f
    """
    from graphify.corpus_prune import _SELF_OUTPUT_DIRS as _CORPUS_SELF
    from graphify.detect import _SELF_OUTPUT_DIRS as _DETECT_SELF
    assert "graphify-out" in _CORPUS_SELF
    assert "graphify_out" in _CORPUS_SELF
    # Catch future divergence between the two intentionally-mirrored copies
    assert _CORPUS_SELF == _DETECT_SELF
```

**Rationale for dual-import:** `_SELF_OUTPUT_DIRS` exists in BOTH `corpus_prune.py:31` and `detect.py:257` (intentionally mirrored per corpus_prune module docstring to avoid import cycles). Testing both in one guard catches future divergence. The authoritative one used by `_is_noise_dir` is in `corpus_prune.py`.

---

## Shared Patterns

### Error-with-hint format
**Source:** `graphify/doctor.py` `_FIX_HINTS` (lines 62-110) and `format_report()` (which emits `[graphify] error:` prefixed lines).
**Apply to:** `_emit_vault_error()` in `graphify/output.py` (VAUX-02); all VAUX-02 test assertions.
```python
# Two-line format — both lines required per D-05
print(f"[graphify] error: {msg}", file=sys.stderr)
print(f"  hint: {hint}", file=sys.stderr)
```
Test assertion shape:
```python
assert "[graphify] error:" in r.stderr
assert "  hint:" in r.stderr
assert r.returncode != 0
```

### `_refuse()` caller convention
**Source:** `graphify/output.py` lines 67-69, and its callers at lines 75-80, 104-107.
**Apply to:** `_emit_vault_error()` usage — callers must `raise _emit_vault_error(...)` (same pattern: function returns `SystemExit`, caller raises it).
```python
# Caller pattern (same as _refuse):
raise _emit_vault_error(
    f"Vault path is not a directory: {p}",
    "Check the path exists and is a directory, not a file.",
)
```

### `pytest.importorskip("yaml")` guard
**Source:** `tests/test_doctor.py` line 62, `tests/test_vault_cli.py` line 45 — every test that touches vault profile resolution gates on PyYAML being installed.
**Apply to:** All `test_vault_parity.py` tests that call `_make_vault(..., profile_text=...)` or `resolve_vault_for_parity()` followed by profile inspection.
```python
def test_parity_vault_cli_matches_doctor(tmp_path):
    pytest.importorskip("yaml")
    ...
```

### Subprocess CLI invocation
**Source:** `tests/test_vault_cli.py` lines 40-62 — `subprocess.run([sys.executable, "-m", "graphify", ...], capture_output=True, text=True, timeout=60)`.
**Apply to:** All VAUX-02 failure-scenario tests in `test_vault_parity.py` (D-07 three categories test the full CLI error surface, not in-process functions).

### `run_doctor(cwd, resolved_output=resolved)` pattern
**Source:** `tests/test_doctor.py` lines 154-175 — constructs `ResolvedOutput` explicitly, passes as `resolved_output` kwarg. Doctor skips inner resolution and uses the supplied value.
**Apply to:** VAUX-01 dry-run mismatch test and all parity tests that need doctor to see the same resolved vault as the parity helper.
```python
resolved = ResolvedOutput(
    True,
    parity["vault_path"],
    parity["vault_path"] / "Atlas" / "Generated",
    parity["vault_path"].parent / "graphify-out",
    parity["source"],
    (),
)
report = run_doctor(cwd, resolved_output=resolved)
```

---

## No Analog Found

All files in this phase have clear analogs in the codebase. No new patterns without precedent.

| File | Role | Data Flow | Notes |
|------|------|-----------|-------|
| — | — | — | All files fully covered by analogs above |

---

## Key Anti-Patterns (from RESEARCH.md)

These must be communicated to the planner:

1. **Do NOT import `_SELF_OUTPUT_DIRS` from `detect.py` only** — import from `corpus_prune.py` too (authoritative source for `_is_noise_dir`). The regression test should assert both copies are equal.
2. **Do NOT call `resolve_output()` or resolution logic inside `resolve_vault_for_parity()`** — must delegate to `resolve_execution_paths()` exclusively.
3. **Do NOT use `contextlib.redirect_stderr` across `_merge_vault_pins` warnings** — `_merge_vault_pins` is in `__main__.py`; calling it from `output.py` would create a circular import. The parity helper's "warnings" dimension covers only what `resolve_execution_paths()` emits.
4. **Do NOT modify `_refuse()`** — add `_emit_vault_error()` alongside it. All existing `_refuse()` callers stay unchanged except the three D-07 failure sites.
5. **Do NOT use golden-text snapshot assertions** (D-01) — assert dict field equality: `assert parity["vault_path"] == report.resolved_output.vault_path`.
6. **Do NOT introduce new `_make_vault` fixture infrastructure** — replicate `test_doctor.py`'s `_make_vault` body at the top of `test_vault_parity.py` (D-08).

---

## Metadata

**Analog search scope:** `graphify/output.py`, `graphify/doctor.py`, `graphify/corpus_prune.py`, `graphify/detect.py`, `tests/test_doctor.py`, `tests/test_vault_cli.py`, `tests/test_detect.py`
**Files scanned:** 7
**Pattern extraction date:** 2026-05-03
