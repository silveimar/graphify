# Phase 58: Vault CLI parity & hygiene - Research

**Researched:** 2026-05-03
**Domain:** Python CLI vault resolution, graphify doctor parity, error formatting, test fixture reuse
**Confidence:** HIGH

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
- **D-01:** Parity strategy = structured parity helper. A small `resolve_vault_for_parity(args, env, cwd) -> dict` that both CLI dispatch and `graphify/doctor.py` call. Tests assert both surfaces produce identical dicts for the same inputs. NOT golden-text snapshots.
- **D-02:** Four parity dimensions asserted: resolved vault path, precedence source label, profile path & mode, diagnostic warnings.
- **D-03:** CLI dispatch and `doctor` must share a warning-emission path (today the global-vs-per-command override note at `__main__.py:1299` is CLI-only). Surface via a single helper rather than duplicating print sites.
- **D-04:** Parity helper lives in `graphify/output.py` or a new `graphify/vault_resolution.py`. Tests in new `tests/test_vault_parity.py`. Existing `test_doctor.py` and `test_vault_cli.py` stay untouched.
- **D-05:** Error format = stderr text + fix hint mirroring `_FIX_HINTS`. Two lines: `[graphify] error: <what failed>` then `  hint: <what to do>`. Tests assert both lines present and non-empty.
- **D-06:** Exit code = single non-zero (whatever graphify already emits for argparse/config errors). No per-category exit codes. No JSON flag.
- **D-07:** Three failure scenarios defined (unknown vault 3 sub-cases, ambiguous selection with existing-warning preservation, dry-run mismatch via parity helper).
- **D-08:** Test fixtures reuse `tests/test_doctor.py`'s `_make_vault(tmp_path, *, profile_text=...)` helper. Do NOT introduce new fixture infrastructure.
- **D-09:** Observation-only for existing precedence — no breaking changes to `--vault / GRAPHIFY_VAULT / --vault-list` conflict behavior (they remain warnings, not errors).
- **D-10:** HYG-01 closure = cite SUMMARY + add named regression-lock test in `tests/test_detect.py`.
- **D-11:** Regression-lock test asserts `_is_noise_dir` returns `True` for `"graphify-out"` and `"graphify_out"`. Named intentional guard, not a re-fix.

### Claude's Discretion
- Exact module location of parity helper (`graphify/output.py` extension vs new `graphify/vault_resolution.py`) — planner picks based on existing module size and cohesion.
- Specific name of the parity helper function and the dict schema — researcher proposes (see below); locked in PLAN.
- Whether regression-lock test name is `test_self_ingestion_dirs_excluded` or similar — planner picks.
- Whether global-vs-per-command and env-vs-flag conflict tests live in `test_vault_parity.py` or `test_vault_cli.py` — planner picks.

### Deferred Ideas (OUT OF SCOPE)
- Per-category exit codes for vault errors.
- `--error-format=json` flag.
- Hard error on global-vs-per-command `--vault` conflict.
- Hard error on `GRAPHIFY_VAULT` vs `--vault` flag conflict.
- Hard error only when conflicting values genuinely differ.
- Dry-run preview vs actual write-path mismatch tests (broader scope).
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| VAUX-01 | `--vault` / vault discovery and `graphify doctor` agree on resolution outcomes for same inputs — 4 dimensions: resolved vault path, precedence source label, profile path & mode, diagnostic warnings | Parity helper wraps `resolve_execution_paths()` — both surfaces already share this function. Helper extracts the 4 dimensions from `ResolvedOutput` + emitted warnings into a comparable dict. |
| VAUX-02 | Vault CLI failures emit `[graphify] error: <msg>` + `  hint: <fix>` stderr, single non-zero exit code, for three failure categories. Asserted by pytest. | `_FIX_HINTS` in `doctor.py` already defines the error+hint pattern. The three failure categories align with existing `_refuse()` / `SystemExit(2)` surfaces. New thin wrapper needed to emit the 2-line format uniformly. |
| HYG-01 | Quick-task `260427-rc7-fix-detect-self-ingestion` (shipped 2026-04-27) closed in VERIFICATION.md by citing its SUMMARY + adding a named regression-lock test in `tests/test_detect.py`. | `_SELF_OUTPUT_DIRS` lives in `graphify/corpus_prune.py` (mirrored in `detect.py`). `_is_noise_dir` in `corpus_prune.py` checks it. Test asserts constant membership — no new logic needed. |
</phase_requirements>

---

## Summary

Phase 58 is a **lock-down-and-verify** phase — it adds no new behavior, only asserts that existing behavior is consistent, well-documented in tests, and error surfaces are actionable. Three requirements: VAUX-01 (parity between `--vault` CLI resolution and `graphify doctor`), VAUX-02 (actionable error formatting for three failure categories), and HYG-01 (closure evidence for a shipped quick-task).

The key implementation insight: both the CLI run path and `graphify doctor` already call the same underlying function — `resolve_execution_paths()` in `graphify/output.py:151`. The parity gap is therefore not in the resolution logic itself but in (a) exposing the 4 dimensions as a comparable dict, and (b) ensuring warning emission (`_merge_vault_pins`'s print at `__main__.py:~1299`) flows through a shared path that `doctor` can also access.

For VAUX-02, the existing `_refuse()` function in `output.py:67` emits `[graphify] <msg>` and raises `SystemExit(1)`, but does NOT emit a `hint:` line. The fix is a thin `_emit_error_with_hint()` helper that prints both lines and sets exit code, with the hint sourced from `_FIX_HINTS`-style lookup or inline per failure category. For HYG-01, the four regression tests that shipped with the fix are already in `tests/test_detect.py` (lines 280-340), but they are behavioral tests. D-11 calls for one additional **named intentional guard** asserting `_SELF_OUTPUT_DIRS` constant membership directly — a sentinel that survives future refactors of `_is_noise_dir`.

**Primary recommendation:** Add `resolve_vault_for_parity()` to `graphify/output.py` (module is 321 lines, still a reasonable size); add `_emit_vault_error()` as a shared error-emitter near `_refuse()`; add the HYG-01 named guard to `tests/test_detect.py`; all new parity tests go in `tests/test_vault_parity.py`.

---

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Vault resolution (path + source label) | Backend library (`graphify/output.py`) | CLI dispatch (`__main__.py`) | `resolve_execution_paths()` is the single resolver; CLI passes args, doctor passes `resolved_output` |
| Warning emission (override conflicts) | CLI dispatch (`__main__.py:_merge_vault_pins`) | — | Today CLI-only; D-03 says move to shared path |
| Error formatting (2-line error+hint) | Backend library (`graphify/doctor.py` pattern) | CLI dispatch | `_FIX_HINTS` lives in `doctor.py`; new emitter near `_refuse()` in `output.py` |
| Doctor dry-run resolution | Doctor module (`graphify/doctor.py`) | `graphify/output.py` | `run_doctor()` delegates to `resolve_execution_paths()` via `resolved_output` param |
| HYG-01 regression guard | Test module (`tests/test_detect.py`) | `graphify/corpus_prune.py` | `_SELF_OUTPUT_DIRS` constant lives in `corpus_prune.py`; asserted directly in test |
| Parity assertion | Test module (`tests/test_vault_parity.py`) | `graphify/output.py` | New helper + new test module |

---

## Standard Stack

### Core (all [VERIFIED: direct file read])

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| Python stdlib `pathlib` | 3.10+ | Path manipulation throughout | Existing codebase standard |
| Python stdlib `sys` | 3.10+ | stderr emission, exit codes | Existing codebase standard |
| `pytest` | existing | Test runner for all new tests | CI convention, `tests/` directory |
| `graphify.output.ResolvedOutput` | project | 6-field NamedTuple for resolution result | Phase 41 established contract |
| `graphify.output.resolve_execution_paths` | project | Single vault resolution hub | Both CLI and doctor call this |
| `graphify.doctor._FIX_HINTS` | project | Error-to-hint substring table | Pattern to mirror for VAUX-02 |

No new third-party dependencies required for this phase.

---

## Architecture Patterns

### System Architecture Diagram

```
Test (test_vault_parity.py)
    |
    |-- calls --> resolve_vault_for_parity(args, env, cwd) [output.py NEW]
    |                  |
    |                  +-- resolve_execution_paths(cwd, explicit_vault=..., env_vault=..., vault_list_file=...)
    |                  |         [output.py:151 — EXISTING, unchanged]
    |                  |
    |                  +-- captures emitted warnings via _emit_warnings_for_parity() [output.py NEW]
    |                  |
    |                  +-- returns dict: {vault_path, source, profile_path, profile_mode, warnings}
    |
    |-- calls --> run_doctor(cwd, resolved_output=parity_resolved) [doctor.py — EXISTING]
    |                  |
    |                  +-- also calls resolve_execution_paths internally (when resolved_output=None)
    |                  +-- returns DoctorReport with .resolved_output, .profile_validation_warnings
    |
    |-- asserts dict_from_parity_helper == dict_from_doctor_report [VAUX-01]

CLI (graphify run / doctor)
    |-- _resolve_cli_paths() [__main__.py:~1315]
    |       |-- _merge_vault_pins() [__main__.py — emits override warning TODAY]
    |       |-- resolve_execution_paths() [output.py]
    |
    |-- On vault failure: _emit_vault_error(msg, hint) [output.py NEW]
    |       |-- prints "[graphify] error: <msg>"
    |       |-- prints "  hint: <fix>"
    |       |-- raises SystemExit(1 or 2)
    |
    |-- [VAUX-02] test_vault_parity.py asserts stderr contains both lines

detect.py / corpus_prune.py
    |-- _SELF_OUTPUT_DIRS = {"graphify-out", "graphify_out"} [corpus_prune.py:31]
    |-- _is_noise_dir(part) checks _SELF_OUTPUT_DIRS [corpus_prune.py:45]
    |-- [HYG-01] tests/test_detect.py NEW test asserts constant membership directly
```

### Recommended Project Structure (changes only)

```
graphify/
├── output.py              # ADD: resolve_vault_for_parity(), _emit_vault_error()
│                          # MODIFY: _refuse() optionally extended or companion added
tests/
├── test_vault_parity.py   # NEW: VAUX-01 parity tests + VAUX-02 error-format tests
├── test_detect.py         # MODIFY: ADD one named HYG-01 regression-lock test
```

### Pattern 1: Parity Helper Function

**What:** A thin wrapper around `resolve_execution_paths()` that returns a structured dict capturing all 4 parity dimensions. Captures warnings emitted to stderr during resolution.

**When to use:** In parity tests — called once for the "CLI path" (with vault pins passed directly) and once in a way that mirrors what doctor does (constructing a `resolved_output` from the same call), then asserted equal.

**Proposed signature and return shape:**

```python
# Source: graphify/output.py (to be added)
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
        "vault_path": Path | None,        # resolved.vault_path
        "source": str,                    # resolved.source (e.g. "vault-cli", "vault-env", ...)
        "profile_path": Path | None,      # <vault_path>/.graphify/profile.yaml or None
        "profile_mode": str | None,       # output.mode from profile, or None
        "warnings": list[str],            # stderr lines emitted during resolution (stripped)
      }
    """
    import io, contextlib
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
                import yaml
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

[VERIFIED: function signatures confirmed by reading `graphify/output.py` lines 1-321]

### Pattern 2: VAUX-02 Error Emitter

**What:** A two-line stderr emission helper that produces `[graphify] error: <msg>` + `  hint: <fix>`, then raises `SystemExit`.

**Current state:** `_refuse()` in `output.py:67` emits only ONE line (`[graphify] <msg>`) and returns (not raises) `SystemExit(1)`. There is no hint line. VAUX-02 requires both lines.

**Proposed approach:** Add a companion `_emit_vault_error(msg: str, hint: str, *, code: int = 1) -> SystemExit` to `output.py` near `_refuse()`:

```python
# Source: graphify/output.py (to be added — VAUX-02)
def _emit_vault_error(msg: str, hint: str, *, code: int = 1) -> SystemExit:
    """Emit [graphify] error: + hint: lines to stderr and return SystemExit(code)."""
    print(f"[graphify] error: {msg}", file=sys.stderr)
    print(f"  hint: {hint}", file=sys.stderr)
    return SystemExit(code)
```

Callers: `_ensure_vault_root()` (currently raises `_refuse(...)`) and `_pick_vault_from_list_file()` (currently raises `_refuse(...)` or `SystemExit(2)`) would be updated to `raise _emit_vault_error(msg, hint, code=...)` for the three D-07 categories. [ASSUMED: planner confirms which specific call sites to update vs. which to leave as `_refuse()`.]

### Pattern 3: HYG-01 Regression-Lock Test

**What:** A named, intentional constant-membership guard in `tests/test_detect.py` that asserts both spellings are in `_SELF_OUTPUT_DIRS`. Unlike the four behavioral tests shipped with the fix, this one reads the constant directly — surviving any future `_is_noise_dir` refactor.

**Exact assertion shape (pure unit test, no fixtures):**

```python
# Source: tests/test_detect.py (new test to add — HYG-01 D-10/D-11)
# Import: from graphify.corpus_prune import _SELF_OUTPUT_DIRS
def test_self_ingestion_dirs_constant_excludes_both_spellings():
    """HYG-01 regression-lock: _SELF_OUTPUT_DIRS must always contain both spellings.

    Guards against future refactors silently dropping the self-ingestion exclusion.
    Cite: .planning/quick/260427-rc7-fix-detect-self-ingestion/260427-rc7-SUMMARY.md
    Commit: 59d8b2f
    """
    assert "graphify-out" in _SELF_OUTPUT_DIRS
    assert "graphify_out" in _SELF_OUTPUT_DIRS
```

**Import note:** `_SELF_OUTPUT_DIRS` is defined in `graphify/corpus_prune.py:31` as `{"graphify-out", "graphify_out"}` — it is a separate copy from the one in `detect.py:257`. The `doctor.py` imports it from `detect.py`. For the regression test, import from `graphify.corpus_prune` (the authoritative source, also checked by `corpus_prune._is_noise_dir`). [VERIFIED: both files contain identical sets, read directly]

### Pattern 4: Existing Exit Code Convention

**What the codebase does today:**

- `sys.exit(1)` — generic operational error, config error, resolution failure [VERIFIED: `__main__.py` lines 319, 330, 371, 1562, 1630, 1633, etc.]
- `sys.exit(2)` — ambiguous vault selection (non-TTY multi-vault `--vault-list`), argparse usage errors [VERIFIED: `__main__.py` lines 100, 107, 1478, 1728, etc.; `output.py` `_pick_vault_from_list_file` raises `SystemExit(2)`]
- `SystemExit(0)` — success via `_cli_exit(0)` which also prints version footer [VERIFIED: `__main__.py:65`]
- `_refuse()` returns `SystemExit(1)` (caller must `raise` it) [VERIFIED: `output.py:67-69`]

**VAUX-02 alignment:** D-06 says "single non-zero" — the existing convention already separates 1 (config errors) vs 2 (ambiguity / usage). VAUX-02 should preserve this: unknown vault = exit 1, ambiguous selection = exit 2, dry-run mismatch = exit 1. Tests should assert `returncode != 0`, not a specific code, unless the scenario is unambiguously exit-2 (ambiguous vault-list).

### Anti-Patterns to Avoid

- **Duplicating resolution logic in `run_doctor()`:** The doctor already accepts `resolved_output` from the CLI. The parity helper must call `resolve_execution_paths()` — never re-implement resolution.
- **Golden-text snapshot tests (D-01 rejection):** Tests must assert dict field equality, not captured stdout strings.
- **Breaking `_refuse()` callers:** VAUX-02 adds a new emitter (`_emit_vault_error`) rather than changing `_refuse()` in-place — existing callers in `resolve_output()` and `resolve_execution_paths()` continue unchanged.
- **Importing `_SELF_OUTPUT_DIRS` from `detect.py` in the regression test:** `detect.py` has its own copy but the authoritative one used by `_is_noise_dir` is in `corpus_prune.py`. Import from `corpus_prune`.
- **Using subprocess in `test_vault_parity.py`:** The parity helper is importable — pure in-process tests are faster and more debuggable. Subprocess is already used in `test_vault_cli.py` for integration. Keep `test_vault_parity.py` as pure unit tests.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Vault path resolution | Custom resolution logic in parity helper | `resolve_execution_paths()` from `output.py` | Single source of truth; already handles all precedence cases |
| Warning capture | Custom sys.stderr redirect | `contextlib.redirect_stderr(io.StringIO())` | stdlib, already used in `doctor.py:run_doctor()` lines ~310-325 |
| Vault fixture creation | New fixture infrastructure | `_make_vault()` from `tests/test_doctor.py` (D-08) | Battle-tested, handles `.obsidian/` + `.git/` + optional profile |
| Error-hint lookup | New table in VAUX-02 error emitter | Inline hint strings per failure category (3 total) OR extend `_FIX_HINTS` | Only 3 new cases; `_FIX_HINTS` is a substring-match table so extension is trivial |

**Key insight:** The resolution logic already exists and is shared. Phase 58's job is to expose the internals as a structured dict (VAUX-01), audit the error emission path for the 2-line format (VAUX-02), and add a named constant guard (HYG-01).

---

## Runtime State Inventory

> This is not a rename/refactor phase. No runtime state inventory needed.

None — Phase 58 adds tests and a thin helper. No database records, service configurations, OS registrations, or secrets are involved.

---

## Common Pitfalls

### Pitfall 1: _SELF_OUTPUT_DIRS Duplication

**What goes wrong:** `_SELF_OUTPUT_DIRS` exists in TWO files: `graphify/detect.py:257` and `graphify/corpus_prune.py:31`. They are intentionally mirrored to avoid import cycles (see `corpus_prune.py` module docstring: "duplicate intentionally to avoid import cycles"). A test that asserts one but not the other could miss a future divergence.

**Why it happens:** The module docstring says "Keep pruning helpers aligned with detect.py — duplicate intentionally." This is a deliberate architecture decision.

**How to avoid:** The regression-lock test (D-10/D-11) should import from `corpus_prune` (where `_is_noise_dir` actually lives and uses the set). Optionally add a second assertion line checking `detect._SELF_OUTPUT_DIRS` equals `corpus_prune._SELF_OUTPUT_DIRS` to catch divergence — but this is planner's discretion.

**Warning signs:** `grep -rn '_SELF_OUTPUT_DIRS' graphify/` shows two definitions.

### Pitfall 2: _merge_vault_pins Warning Emission Path (D-03)

**What goes wrong:** The warning `"[graphify] command --vault / --vault-list overrides global pin"` is printed inside `_merge_vault_pins()` in `__main__.py` (around line 1299). `run_doctor()` calls `_resolve_cli_paths()` which calls `_merge_vault_pins()` — so the warning already does flow through both paths today. However, the VAUX-01 parity helper (living in `output.py`) calls `resolve_execution_paths()` which does NOT call `_merge_vault_pins()` — that merging step is in `__main__.py`.

**Why it happens:** `_merge_vault_pins()` is a CLI dispatch helper in `__main__.py`, not in `output.py`. The parity helper would need to either (a) call `_merge_vault_pins` too (but that creates a circular import `output.py` → `__main__.py`), or (b) accept already-merged vault pins as parameters (callers pre-merge, same as `resolve_execution_paths` does today), or (c) the "warnings" dimension of VAUX-01 excludes the merge-conflict warning and only covers the warnings emitted by `resolve_execution_paths` itself.

**How to avoid:** The cleanest design: `resolve_vault_for_parity()` accepts pre-merged `explicit_vault` / `vault_list_file` params (same signature as `resolve_execution_paths`). The merge-conflict warning test lives in `test_vault_parity.py` but tests `_merge_vault_pins()` directly OR uses the `_resolve_cli_paths()` function from `__main__.py`. This avoids circular imports. [ASSUMED: Planner confirms the "warnings" dimension scope — whether it covers merge-conflict warnings or only resolution warnings from `resolve_execution_paths`.]

### Pitfall 3: doctor's resolved_output bypass

**What goes wrong:** When `run_doctor()` is called with `resolved_output` already set (as CLI does in the doctor dispatch), it skips the inner `resolve_output(cwd_resolved)` call entirely. This means the "warnings" captured by the parity helper's stderr redirect might differ from what doctor captured during its construction if the caller does both operations independently.

**Why it happens:** `run_doctor()` lines ~332-352 show: "if resolved_output is not None → skip inner resolution." Doctor relies on the caller having already done resolution (and emitted any warnings during that step).

**How to avoid:** In parity tests, call `resolve_vault_for_parity()` first (captures warnings), then construct the `ResolvedOutput` and pass it to `run_doctor()`. Assert that `report.resolved_output` matches the dict from the parity helper. The test contract is: "same inputs produce same resolved values" — warnings comparison must be designed carefully (the test captures warnings during `resolve_vault_for_parity()` only, not during `run_doctor()` since doctor doesn't re-resolve).

### Pitfall 4: SystemExit propagation in parity tests

**What goes wrong:** Failure-scenario tests (VAUX-02) must capture both the stderr output AND the exit code. Using `pytest.raises(SystemExit)` with a `capsys` fixture to check stderr is the correct pattern — but the order matters: `capsys.readouterr()` must be called after the `SystemExit` is caught.

**Why it happens:** pytest `capsys` works fine with `SystemExit`, but if the code uses `sys.exit()` vs `raise SystemExit()` the behavior differs in some pytest versions.

**How to avoid:** Use `subprocess.run()` for the 3 VAUX-02 failure-mode tests (following `test_vault_cli.py` pattern) since they test the full CLI error surface. Use in-process calls with `pytest.raises(SystemExit)` + `capsys` only for unit-level assertion of `_emit_vault_error`.

---

## Code Examples

### Existing `_make_vault` fixture from `tests/test_doctor.py`

```python
# Source: tests/test_doctor.py (verified by direct read)
def _make_vault(tmp_path: Path, *, profile_text: str | None = None) -> Path:
    """Create a synthetic Obsidian vault under tmp_path/vault.

    - .obsidian/  marks it as a vault (D-04)
    - .git/       halts _load_graphifyignore walk-up (RESEARCH Pitfall 6)
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

Note: `test_vault_cli.py` has its own `_make_vault(parent, name)` with a slightly different signature. Do NOT confuse them. D-08 says reuse the `test_doctor.py` pattern — replicate the function at the top of `test_vault_parity.py` (same body, no import needed).

### Existing _refuse() in output.py

```python
# Source: graphify/output.py:67-69 (verified by direct read)
def _refuse(msg: str) -> SystemExit:
    """Print actionable error to stderr and prepare SystemExit(1)."""
    print(f"[graphify] {msg}", file=sys.stderr)
    return SystemExit(1)
```

VAUX-02 adds `_emit_vault_error()` alongside this — does NOT replace `_refuse()`.

### Existing _merge_vault_pins warning in __main__.py

```python
# Source: graphify/__main__.py _merge_vault_pins() (verified by direct read)
def _merge_vault_pins(g_exp, g_list, l_exp, l_list):
    """Local --vault / --vault-list override global leading flags (41-RESEARCH)."""
    used_local = l_exp is not None or l_list is not None
    used_global = g_exp is not None or g_list is not None
    if used_local and used_global:
        print(
            "[graphify] command --vault / --vault-list overrides global pin",
            file=sys.stderr,
        )
    exp = l_exp if l_exp is not None else g_exp
    vlf = l_list if l_list is not None else g_list
    return exp, vlf
```

This warning is already shared: `_resolve_cli_paths()` calls `_merge_vault_pins()` and is called by both `run` and `doctor` dispatch. The parity helper in `output.py` cannot call this (circular import). Tests for this warning dimension use `_resolve_cli_paths()` directly or subprocess.

### ResolvedOutput NamedTuple

```python
# Source: graphify/output.py:35-42 (verified by direct read)
class ResolvedOutput(NamedTuple):
    vault_detected: bool
    vault_path: Path | None
    notes_dir: Path
    artifacts_dir: Path
    source: ResolvedSource  # Literal["profile","cli-flag","default","vault-cli","vault-env","vault-list"]
    exclude_globs: tuple[str, ...] = ()
```

The `source` field is the "precedence source label" dimension of VAUX-01.

### Doctor warning-emission path (stderr capture in run_doctor)

```python
# Source: graphify/doctor.py lines ~310-330 (verified by direct read)
if resolved_output is None and not report.profile_validation_errors:
    captured = io.StringIO()
    try:
        with contextlib.redirect_stderr(captured):
            report.resolved_output = resolve_output(cwd_resolved)
    except SystemExit:
        report.resolved_output = None
        for line in captured.getvalue().splitlines():
            stripped = line.strip()
            if stripped.startswith("[graphify] "):
                stripped = stripped[len("[graphify] "):]
            report.profile_validation_errors.append(stripped)
```

This pattern is the exact model for the parity helper's warning capture.

---

## Module Location Decision (Claude's Discretion — Researcher Recommendation)

**Recommendation: extend `graphify/output.py`.**

Rationale:
- `output.py` is 321 lines — still well within a manageable single-purpose module.
- `resolve_execution_paths()` is already in `output.py`. Adding `resolve_vault_for_parity()` keeps the complete resolution API in one place.
- `_refuse()` is already in `output.py`. Adding `_emit_vault_error()` alongside it is cohesive.
- Creating `graphify/vault_resolution.py` would be a thin new file that mostly re-exports from `output.py` — unnecessary indirection for 2 small functions.
- Planner may override to `vault_resolution.py` if they judge `output.py` is getting crowded after Phase 57 additions. [ASSUMED: output.py line count is based on reading 321 lines — verify against actual post-Phase-57 state before planning.]

---

## Dry-Run Mismatch Test Design

The VAUX-01 parity helper is also the detection vehicle for the dry-run mismatch scenario (D-07). The test design:

1. Create a vault with valid profile using `_make_vault()`.
2. Call `resolve_vault_for_parity(vault, explicit_vault=vault)` — this runs the "run path" resolution.
3. Call `run_doctor(vault, dry_run=True, resolved_output=<same ResolvedOutput>)` — this runs the "doctor path" resolution.
4. Extract the relevant fields from `DoctorReport.resolved_output` and compare to the parity dict.
5. Assert they agree (this is the "no mismatch" positive case).
6. The "mismatch" scenario would require injecting a corrupted `resolved_output` into `run_doctor` while the parity helper resolves differently — but since both use the same `resolve_execution_paths()`, a true mismatch cannot occur unless the inputs differ. This means the dry-run mismatch test is effectively: assert that `resolve_vault_for_parity()` and `run_doctor(resolved_output=...)` with the same root produce identical vault_path and source.

**No subprocess needed** for the dry-run mismatch test — it is fully in-process. [VERIFIED: `run_doctor()` accepts `resolved_output` param; `resolve_execution_paths()` is importable]

---

## Environment Availability

Step 2.6: SKIPPED — Phase 58 is purely code and test additions. No external tools, databases, or services beyond the existing Python 3.10+/pytest environment.

Verified: `pytest` is available (project CI convention), PyYAML available (used in existing `test_doctor.py` via `pytest.importorskip("yaml")`).

---

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | `output.py` is still ~321 lines post-Phase-57; adding 2 functions keeps it cohesive | Module Location Decision | If Phase 57 added significantly more code, planner should use `vault_resolution.py` instead |
| A2 | The "warnings" dimension of VAUX-01 covers only warnings emitted by `resolve_execution_paths()` (not the `_merge_vault_pins` override note) | Pitfall 2, Architecture Patterns | If override warning must be in scope, parity helper needs a different architecture to avoid circular import |
| A3 | VAUX-02 failure tests for the 3 D-07 categories use subprocess (following `test_vault_cli.py` pattern) | Common Pitfalls §4 | If planner prefers in-process `pytest.raises`, the test approach changes but outcome is equivalent |
| A4 | `_emit_vault_error()` replaces `raise _refuse(...)` only in the three D-07 failure sites, leaving all other `_refuse()` callers unchanged | Pattern 2 | If other callsites also need the hint line, scope expands |

---

## Open Questions

1. **Which specific call sites in `output.py` emit VAUX-02 errors?**
   - What we know: `_ensure_vault_root()` calls `_refuse()` for non-directory and non-vault cases (2 of 3 D-07 "unknown vault" sub-cases). `_pick_vault_from_list_file()` calls `_refuse()` for not-found and uses `SystemExit(2)` for ambiguous (1 of 2 ambiguous sub-cases). The third sub-case (`--vault README.md`) hits `_ensure_vault_root` "not a directory" check.
   - What's unclear: The exact `_refuse()` messages used today — are they already actionable enough, or do they need hint augmentation?
   - Recommendation: Planner reads the exact `_refuse()` messages in `_ensure_vault_root()` and `_pick_vault_from_list_file()` and decides: add hints inline (preferred — D-05) or leave message and add generic hint.

2. **Parity dict: profile_path field when profile doesn't exist**
   - What we know: `run_doctor()` checks `profile_yaml.exists()` before calling `validate_profile_preflight()`. When missing, errors are captured differently.
   - What's unclear: Should parity dict `profile_path` be `None` (file absent) or the expected path (absent but typed)?
   - Recommendation: `None` when file does not exist — matches doctor behavior which also gates on existence.

---

## Validation Architecture

### Test Framework

| Property | Value |
|----------|-------|
| Framework | pytest (existing, no version pin) |
| Config file | none — `pyproject.toml` [tool.pytest.ini_options] |
| Quick run command | `pytest tests/test_vault_parity.py tests/test_detect.py -q` |
| Full suite command | `pytest tests/ -q` |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| VAUX-01 | `resolve_vault_for_parity()` returns same 4-dimension dict as `run_doctor().resolved_output` for same inputs | unit | `pytest tests/test_vault_parity.py::test_parity_vault_cli_matches_doctor -x` | ❌ Wave 0 |
| VAUX-01 | Parity holds for `vault-env` pin (GRAPHIFY_VAULT) | unit | `pytest tests/test_vault_parity.py::test_parity_vault_env_matches_doctor -x` | ❌ Wave 0 |
| VAUX-01 | Parity holds for `vault-list` single-entry pin | unit | `pytest tests/test_vault_parity.py::test_parity_vault_list_matches_doctor -x` | ❌ Wave 0 |
| VAUX-01 | Dry-run doctor resolution agrees with run-path resolution for same inputs | unit | `pytest tests/test_vault_parity.py::test_dry_run_matches_run_path -x` | ❌ Wave 0 |
| VAUX-02 | `--vault /nonexistent` emits `[graphify] error:` + `  hint:` + exits nonzero | integration | `pytest tests/test_vault_parity.py::test_unknown_vault_nonexistent_path_error -x` | ❌ Wave 0 |
| VAUX-02 | `--vault /dir-without-obsidian` emits error+hint | integration | `pytest tests/test_vault_parity.py::test_unknown_vault_no_obsidian_marker_error -x` | ❌ Wave 0 |
| VAUX-02 | `--vault README.md` (file not dir) emits error+hint | integration | `pytest tests/test_vault_parity.py::test_unknown_vault_file_not_dir_error -x` | ❌ Wave 0 |
| VAUX-02 | `--vault-list` with 2+ valid vaults (non-TTY) exits 2 with useful message | integration | `pytest tests/test_vault_parity.py::test_ambiguous_vault_list_exit2 -x` | ❌ Wave 0 |
| VAUX-02 | Global `--vault` + per-command `--vault` conflict emits existing override warning | unit | `pytest tests/test_vault_parity.py::test_global_local_override_warning -x` | ❌ Wave 0 |
| VAUX-02 | `GRAPHIFY_VAULT` env + `--vault` flag conflict emits existing override warning | unit | `pytest tests/test_vault_parity.py::test_env_flag_override_warning -x` | ❌ Wave 0 |
| HYG-01 | `_SELF_OUTPUT_DIRS` constant contains both `"graphify-out"` and `"graphify_out"` | unit | `pytest tests/test_detect.py::test_self_ingestion_dirs_constant_excludes_both_spellings -x` | ❌ Wave 0 |

### Sampling Rate
- **Per task commit:** `pytest tests/test_vault_parity.py tests/test_detect.py -q`
- **Per wave merge:** `pytest tests/ -q`
- **Phase gate:** Full suite green before `/gsd-verify-work`

### Wave 0 Gaps
- [ ] `tests/test_vault_parity.py` — new module, create before implementation tasks (VAUX-01 + VAUX-02 tests)
- [ ] `tests/test_detect.py` — add 1 test function (`test_self_ingestion_dirs_constant_excludes_both_spellings`)
- [ ] `graphify/output.py` — add `resolve_vault_for_parity()` and `_emit_vault_error()` stubs

---

## Security Domain

VAUX-01, VAUX-02, and HYG-01 do not introduce new input surfaces. The ASVS categories that apply to vault path handling already apply to the unchanged `resolve_execution_paths()` and `_ensure_vault_root()` — those functions pass through `graphify/security.py` conventions (path confinement to `graphify-out/`). No new attack surface is introduced.

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V5 Input Validation | Inherited (not new) | `_ensure_vault_root()` validates path is dir + has `.obsidian/` |
| V4 Access Control | No | Read-only operations |
| V2 Authentication | No | No auth surfaces |
| V6 Cryptography | No | No crypto |

---

## Sources

### Primary (HIGH confidence)

- `graphify/output.py` (direct read, lines 1-321) — `ResolvedOutput`, `resolve_execution_paths`, `_refuse`, `_ensure_vault_root`, `_pick_vault_from_list_file`, full resolution logic
- `graphify/doctor.py` (direct read, full file) — `DoctorReport`, `_FIX_HINTS`, `run_doctor`, `format_report`, `_build_recommended_fixes`, stderr capture pattern
- `graphify/__main__.py` lines 1237-1420 (direct read) — `_strip_leading_vault_global_argv`, `_strip_vault_flags_from_tokens`, `_merge_vault_pins`, `_resolve_cli_paths`, doctor dispatch
- `graphify/__main__.py` lines 2807-2911 (direct read) — doctor command dispatch implementation
- `graphify/corpus_prune.py` lines 1-80 (direct read) — `_SELF_OUTPUT_DIRS`, `_is_noise_dir`, `dir_prune_reason`
- `tests/test_doctor.py` (direct read) — `_make_vault` helper signature and usage, `_VALID_PROFILE` pattern, existing test patterns
- `tests/test_vault_cli.py` (direct read, full file) — subprocess integration test pattern, `_make_vault` variant
- `tests/test_detect.py` lines 280-345 (direct read) — four HYG-01 behavioral tests already shipped
- `.planning/quick/260427-rc7-fix-detect-self-ingestion/260427-rc7-SUMMARY.md` (direct read) — full HYG-01 fix evidence, commit hashes `6584eff` and `59d8b2f`
- `.planning/phases/58-vault-cli-parity-hygiene/58-CONTEXT.md` (direct read, full file) — locked decisions D-01 through D-11

### Secondary (MEDIUM confidence)
- `graphify/detect.py` lines 257, 482-510 (grep + direct read) — `_SELF_OUTPUT_DIRS` mirrored copy, `dir_prune_reason` call site

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — no new dependencies; all existing
- Architecture: HIGH — read all relevant code directly; proposals grounded in actual signatures
- Pitfalls: HIGH — discovered by reading actual code (two `_SELF_OUTPUT_DIRS` copies, circular import risk, `_refuse()` one-line limitation)
- Test map: HIGH — all test functions named with proposed names matching D-07 categories

**Research date:** 2026-05-03
**Valid until:** 2026-06-03 (stable codebase, changes only from same phase work)
