# Phase 63: VOPT — Vault Option B Silent Reroute & `--explain-paths` — Pattern Map

**Mapped:** 2026-05-05
**Files analyzed:** 5 (3 modify, 1 create, 1 modify-tests)
**Analogs found:** 5/5

## File Classification

| File | Created/Modified | Layer | Role | Closest Analog | Match Quality |
|------|------------------|-------|------|----------------|---------------|
| `graphify/output.py` | MODIFY | resolver | path-resolution + stderr emit | self (`_emit_vault_error`, `resolve_output` cli-flag branch) | exact (sibling extension) |
| `graphify/__main__.py` | MODIFY | cli | argv early-exit + gate harmonization | self (`--version` early-exit at L1571, `_check_vault_cwd_gate` L1517–1561) | exact |
| `tests/test_output_path_matrix.py` | MODIFY (append) | tests | unit (resolver matrix, capsys) | self (existing `test_cwd_in_vault_profile_dot_resolves_to_vault_root`) | exact |
| `tests/test_explain_paths.py` | CREATE | tests | integration (subprocess + key:value table) | `tests/test_vault_cwd.py` `_graphify(...)` subprocess helper | role-match |
| `tests/test_vault_cwd.py` | MODIFY (assertions) | tests | unit (subprocess gate behavior) | self (lines 346, 357, 374) | exact |

## Pattern Assignments

### `graphify/output.py` (resolver, request-response)

**Analog:** self — extend `ResolvedSource` Literal, add `_emit_vault_info()` sibling helper, insert Option B branch into `resolve_output()`.

**ResolvedSource Literal pattern** (output.py:34–43):
```python
ResolvedSource = Literal[
    "profile",
    "cli-flag",
    "default",
    "vault-cli",
    "vault-env",
    "vault-list",
]
```
Action: append `"option-b"` (and only that — schema unchanged).

**Two-line stderr helper pattern** (output.py:84–101) — the exact shape the new `_emit_vault_info` must mirror:
```python
def _emit_vault_error(msg: str, hint: str, *, code: int = EXIT_VAULT_REFUSAL) -> SystemExit:
    """Emit [graphify] error: + hint: lines to stderr and return SystemExit(code).

    VAUX-02: two-line format mirrors doctor.py _FIX_HINTS pattern (D-05).
    Callers: raise _emit_vault_error(msg, hint, code=...)
    """
    print(f"[graphify] error: {msg}", file=sys.stderr)
    print(f"  hint: {hint}", file=sys.stderr)
    return SystemExit(code)
```
Action: add a sibling `_emit_vault_info(msg, hint, *, extra_hint=None)` that mirrors this shape but uses `info:` and prints an optional third `  hint: {extra_hint}` line. No `SystemExit` — Option B is a continue, not a refuse.

**`is_obsidian_vault` reuse pattern** (output.py:68–70):
```python
def is_obsidian_vault(path: Path) -> bool:
    """Strict CWD-only detection (D-04). No parent-walking."""
    return (path / ".obsidian").is_dir()
```
Action: do NOT add a new vault detector; reuse this for Option B trigger.

**`resolve_output` dispatch + VAULT-08 emission pattern** (output.py:287 onward, cli-flag branch):
```python
def resolve_output(cwd: Path, *, cli_output: str | None = None) -> ResolvedOutput:
    cwd_resolved = cwd.resolve()
    is_vault = is_obsidian_vault(cwd_resolved)

    if cli_output is not None:
        cli_path = Path(cli_output)
        flag_path = (
            cli_path.resolve()
            if cli_path.is_absolute()
            else (cwd_resolved / cli_output).resolve()
        )
        if is_vault:
            ...
            print(
                f"[graphify] vault detected at {cwd_resolved} — "
                f"output: {flag_path} (source=cli-flag)",
                file=sys.stderr,
            )
```
Action: at the existing `vault + no-profile` branch (where `_refuse(...)` lives today, ~line 312–315), insert the Option B branch BEFORE the refuse. Suppress the VAULT-08 `vault detected at ...` line on this branch (Pitfall 2 — keeps breadcrumb count at one two-line cluster). Construct paths absolutely:
```python
notes_dir = (cwd_resolved / ".graphify-out" / "obsidian").resolve()
artifacts_dir = (cwd_resolved / ".graphify-out").resolve()
```
Plus add `obsidian_dir_override: bool = False` parameter so D-02 strict-trigger works (when True, keep the legacy `_refuse`).

**`default_graphify_artifacts_dir` invariant** (output.py:53–66):
```python
def default_graphify_artifacts_dir(target, *, resolved=None) -> Path:
    if resolved is not None and resolved.source == "default":
        return (Path.cwd() / resolved.artifacts_dir).resolve()
    return target / "graphify-out" if target.is_dir() else target.parent / "graphify-out"
```
Action: do NOT modify. Verify `source="option-b"` flows through the `else` arm at `__main__.py:3056` (uses `resolved.artifacts_dir` directly).

---

### `graphify/__main__.py` (cli, request-response)

**Analog:** self — `--version` early-exit + `_check_vault_cwd_gate` + `_resolve_cli_paths` precedence chain.

**Early-exit flag pattern** (__main__.py:1571 — the `--version` analog):
```python
argv_head = sys.argv[1:]
if len(argv_head) >= 1 and argv_head[0] in ("--version", "-V"):
    print(_render_version_block())
    raise SystemExit(0)
```
Action: insert `--explain-paths` early-exit immediately after this block (after vault-flag strip lines 1566–1567, before help dispatch line 1597). Use a manual `if "--explain-paths" in sys.argv: _print_explain_paths_table(); raise SystemExit(0)` (no argparse — matches existing manual-argv style).

**VCWD-03 gate landmine pattern** (__main__.py:1517–1561) — the gate that must downgrade:
```python
def _check_vault_cwd_gate(cmd: str, *, has_explicit_route: bool, write_into_vault: bool) -> str:
    cwd = Path.cwd().resolve()
    if not is_obsidian_vault(cwd):
        return "n/a"
    if has_explicit_route:
        return "n/a"
    has_profile = (cwd / ".graphify" / "profile.yaml").is_file()
    if has_profile:
        print(f"[graphify] auto-adopted vault at {cwd} ...", file=sys.stderr)
        return "auto-adopt"
    if write_into_vault:
        return "n/a"
    safe_cwd = sanitize_label(str(cwd))
    raise _emit_vault_error(
        f"refusing to write into Obsidian vault at {safe_cwd} — no .graphify/profile.yaml found",
        "create .graphify/profile.yaml ...",
        code=EXIT_VAULT_GATE,
    )
```
Action: the final `raise _emit_vault_error(...)` block must downgrade to `return "option-b"` (or `return "n/a"`) when `--obsidian-dir` and `--output` are both absent. Thread a new signal — either a new `cli_path_override: bool` parameter, or fold `user_passed_obsidian_dir` and `cli_output is not None` into `has_explicit_route` at every call site.

**Precedence chain integration pattern** (__main__.py:1869–1888 — the `--obsidian` post-resolve dispatch):
```python
# Precedence (D-08): --output > profile > --obsidian-dir > legacy default
_od_profile = None
if cli_output is not None:
    obsidian_dir = str(resolved.notes_dir)
elif resolved.vault_detected and resolved.source in _PROFILE_DRIVEN_SOURCES:
    obsidian_dir = str(resolved.notes_dir)
elif user_passed_obsidian_dir:
    _od = Path(obsidian_dir).resolve()
    obsidian_dir = str(_od)
    ...
# else: keep legacy default "graphify-out/obsidian" (D-12 backcompat)
```
Action: insert a new `elif resolved.source == "option-b":` arm BEFORE the `elif user_passed_obsidian_dir:` arm, that sets `obsidian_dir = str(resolved.notes_dir)` (which the resolver guarantees is `<vault>/.graphify-out/obsidian` already absolute via `.resolve()`). Update the help text on line 1597 to read `--output > profile > --obsidian-dir > option-b (vault) > default`.

**`--explain-paths` table helper pattern** (new — but stderr-suppression pattern exists at `resolve_vault_for_parity` output.py:236):
```python
def _print_explain_paths_table() -> None:
    import contextlib, io
    cwd = Path.cwd().resolve()
    profile_path = cwd / ".graphify" / "profile.yaml"
    captured = io.StringIO()
    try:
        with contextlib.redirect_stderr(captured):
            resolved = resolve_execution_paths(cwd)
        ...
    except SystemExit:
        ...
    print(f"cwd:           {cwd}")
    print(f"vault:         {'yes' if (cwd / '.obsidian').is_dir() else 'no'}  (.obsidian/ present)")
    print(f"profile:       {profile_path if profile_path.exists() else '<none>'}")
    print(f"resolved out:  {out}")
    print(f"resolution:    {resolution_label}")
```

---

### `tests/test_output_path_matrix.py` (tests, unit)

**Analog:** self — append cases at end of file using existing `_make_vault` and `_no_doubled_segment` helpers.

**Fixture builder pattern** (test_output_path_matrix.py:42–55):
```python
def _make_vault(tmp_path: Path, name: str = "uat70-vault") -> Path:
    vault = tmp_path / name
    vault.mkdir()
    (vault / ".obsidian").mkdir()
    (vault / ".graphify").mkdir()
    (vault / ".graphify" / "profile.yaml").write_text(_PROFILE_YAML, encoding="utf-8")
    return vault
```
Action for Option B tests: build a vault WITHOUT `.graphify/profile.yaml` (skip the profile.yaml write):
```python
def _make_vault_no_profile(tmp_path: Path, name: str = "vopt-vault") -> Path:
    vault = tmp_path / name
    vault.mkdir()
    (vault / ".obsidian").mkdir()
    return vault
```

**Existing test pattern** (test_output_path_matrix.py:67–76) — direct `resolve_output(vault)` call + `capsys.readouterr()` drain:
```python
def test_cwd_in_vault_profile_dot_resolves_to_vault_root(tmp_path, capsys):
    pytest.importorskip("yaml")
    vault = _make_vault(tmp_path)
    resolved = resolve_output(vault)
    capsys.readouterr()
    assert resolved.vault_detected is True
    assert resolved.source == "profile"
    assert resolved.notes_dir == vault.resolve()
    assert _no_doubled_segment(resolved.notes_dir, vault.name)
```
Action: append ~6 Option B cases following this exact shape — assert `resolved.source == "option-b"`, `resolved.notes_dir == (vault / ".graphify-out" / "obsidian").resolve()`, and capsys stderr contains the `info:` / `hint:` strings.

---

### `tests/test_explain_paths.py` (tests, integration — NEW)

**Analog:** `tests/test_vault_cwd.py` `_graphify(...)` subprocess helper pattern.

**Subprocess helper pattern** (test_vault_cwd.py — `_graphify` already used throughout):
```python
proc = _graphify("update-vault", "--input", str(tmp_path / "nonexistent"), cwd=str(tmp_path))
assert proc.returncode == 1
assert "expected text" in proc.stderr
```
Action: copy/import the `_graphify` helper or replicate the `subprocess.run([sys.executable, "-m", "graphify", ...], cwd=..., capture_output=True, text=True)` shape. Tests assert:
- `proc.returncode == 0`
- `proc.stdout` contains 5 rows: `cwd:`, `vault:`, `profile:`, `resolved out:`, `resolution:`
- pipeline did NOT run (no `graphify-out/` created in `tmp_path`)
- `resolution: option-b` appears when CWD is vault-no-profile
- `resolution: default` appears when CWD is plain dir

---

### `tests/test_vault_cwd.py` (tests, unit — MODIFY assertions)

**Analog:** self — these expectation strings flip from refusal to reroute.

**Existing refusal-expectation pattern** (test_vault_cwd.py:346, 357):
```python
assert "refuse" in s3, f"vault-no-profile → refuse expected; got: {s3!r}"
...
assert runtime.returncode == 2 and "refusing to write" in runtime.stderr, (
    f"doctor predicted refuse; runtime should refuse. runtime stderr:\n{runtime.stderr}"
)
```
Action: flip these assertions. The `vault-no-profile` doctor section should now predict `option-b` (or whatever label the doctor reports — coordinate with planner). Runtime `returncode` becomes `0` and stderr contains `info: vault CWD without .graphify/profile.yaml — Option B reroute active`.

Also flip the global-prefix line at 204:
```python
REFUSAL_MSG_PREFIX = "[graphify] error: refusing to write into Obsidian vault at "
```
This still exists for the `--obsidian-dir` strict-trigger refusal path (D-02), so KEEP it but ensure tests using it pass `--obsidian-dir` so refusal still fires.

---

## Shared Patterns

### Pattern S1 — `[graphify] info: / hint:` two-line stderr breadcrumb
**Source:** `graphify/output.py:84–101` (`_emit_vault_error`)
**Apply to:** Phase 63 emits ONE new sibling `_emit_vault_info(msg, hint, *, extra_hint=None)` in `output.py`. All Option B trigger sites call this exactly once. NEVER inline `print(... file=sys.stderr)` — the helper is the single regex anchor for Phase 64 AUDIT-A.

### Pattern S2 — Vault detection via `is_obsidian_vault(path)`
**Source:** `graphify/output.py:68–70`
**Apply to:** Option B trigger detection AND `--explain-paths` `vault: yes/no` row. Never write a custom `.obsidian` walker.

### Pattern S3 — Manual argv early-exit (no argparse for top-level flags)
**Source:** `graphify/__main__.py:1571` (`--version`)
**Apply to:** `--explain-paths` follows the same manual-argv detection shape, immediately after the vault-flag strip and before subcommand dispatch.

### Pattern S4 — `tmp_path`-only test fixtures, no chdir
**Source:** `tests/test_output_path_matrix.py` (entire file)
**Apply to:** All new Option B unit tests. Pass `cwd` directly to `resolve_output(cwd)`. No `monkeypatch.chdir`. Subprocess-style tests in `test_explain_paths.py` use `cwd=` kwarg of `subprocess.run`, never the test process's actual cwd.

### Pattern S5 — Resolver-level path absoluteness via `.resolve()`
**Source:** `graphify/output.py` (cli-flag branch, lines ~296–306)
**Apply to:** Option B branch must `.resolve()` both `notes_dir` and `artifacts_dir` at construction so the 70.1 nested-vault fix doesn't regress.

### Pattern S6 — `_PROFILE_DRIVEN_SOURCES` membership for downstream branching
**Source:** `graphify/__main__.py` (referenced at line ~1872)
**Apply to:** Decide whether `"option-b"` should be added to `_PROFILE_DRIVEN_SOURCES` set (the analog branch sets `obsidian_dir = str(resolved.notes_dir)`). Recommendation: add a separate `elif resolved.source == "option-b":` arm rather than expanding the set, since profile semantics differ (no profile loaded for Option B).

## No Analog Found

None — every file has an exact or close analog already in the codebase.

## Metadata

**Analog search scope:** `graphify/output.py`, `graphify/__main__.py`, `tests/test_output_path_matrix.py`, `tests/test_vault_cwd.py`, `tests/test_output.py`
**Files scanned:** 5
**Pattern extraction date:** 2026-05-05

## PATTERN MAPPING COMPLETE
