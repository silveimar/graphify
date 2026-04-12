---
phase: 05-integration-cli
reviewed: 2026-04-11T00:00:00Z
depth: standard
files_reviewed: 2
files_reviewed_list:
  - graphify/__main__.py
  - tests/test_main_cli.py
findings:
  critical: 0
  warning: 2
  info: 6
  total: 8
status: issues_found
---

# Phase 05-06: Code Review Report

**Reviewed:** 2026-04-11
**Depth:** standard
**Files Reviewed:** 2
**Status:** issues_found

## Summary

Scope-limited review of the gap-closure branches added to `graphify/__main__.py`
(`--validate-profile` and `--obsidian`) and the new `tests/test_main_cli.py`
integration suite. The library layer (plans 05-01 through 05-05) is out of scope
and already covered by `05-REVIEW.md`.

**D-78 compliance: PASS.** The new CLI branches import only from
`graphify.profile`, `graphify.export`, `graphify.merge`, stdlib, and
`networkx.readwrite`. No imports from `graphify.extract`, `graphify.build`,
`graphify.cluster`, or `graphify.analyze`. The branches are thin
finished-graph-utility wrappers as the plan intends.

**Overall assessment:** The wiring is correct and the exit-code contract is
consistent. Tests cover the main happy paths and a good spread of error paths.
The findings below are minor: two warnings about CLI ergonomics / defensive
patterns, and a handful of info-level gaps in test coverage and code cleanliness.

No critical issues. No security issues. No source files were modified.

## Warnings

### WR-01: `--validate-profile` silently ignores extra positional args

**File:** `graphify/__main__.py:694-711`
**Issue:** The branch reads `sys.argv[2]` directly and never inspects
`sys.argv[3:]`. If the user runs `graphify --validate-profile /vault --extra`,
the `--extra` token is silently dropped and preflight runs against `/vault` as
if nothing were wrong. Every other branch in this file either (a) parses
remaining args in a `while` loop or (b) errors on unknown tokens (see
`--obsidian` at line 737). The inconsistency is a footgun: a user who mistypes
`graphify --validate-profile /vault --strict` will get a success exit and
believe `--strict` was honoured.

**Fix:** Reject extra positional arguments explicitly, matching the `--obsidian`
branch's error style:

```python
if cmd == "--validate-profile":
    if len(sys.argv) < 3:
        print("Usage: graphify --validate-profile <vault-path>", file=sys.stderr)
        sys.exit(2)
    if len(sys.argv) > 3:
        print(
            f"error: unknown --validate-profile option: {sys.argv[3]}",
            file=sys.stderr,
        )
        sys.exit(2)
    from graphify.profile import validate_profile_preflight
    result = validate_profile_preflight(Path(sys.argv[2]))
    ...
```

A regression test in `test_main_cli.py` would also catch this:

```python
def test_validate_profile_extra_arg_exits_2(tmp_path):
    result = _run_cli("--validate-profile", str(tmp_path), "--bogus")
    assert result.returncode == 2
    assert "unknown --validate-profile option" in result.stderr
```

### WR-02: Defensive `getattr` chain on a known-typed result is a code smell

**File:** `graphify/__main__.py:795-803`
**Issue:** After the `isinstance(result, MergePlan)` branch returns, the `else`
arm knows statically that `result` is a `MergeResult` (see
`graphify/export.py:453` annotation `MergeResult | MergePlan`). Yet the code
does:

```python
summary = getattr(getattr(result, "plan", None), "summary", {}) or {}
total = sum(summary.values()) if summary else 0
created = summary.get("CREATE", 0)
updated = summary.get("UPDATE", 0)
```

The chained `getattr` pattern hides two real risks:

1. If `to_obsidian` is ever refactored to return a different object without a
   `.plan.summary`, this code will silently print `"— 0 actions (0 CREATE, 0
   UPDATE)"` instead of failing loudly. The user will think the export
   succeeded with zero work, and the bug will only surface when they inspect
   the vault on disk.
2. The `MergeResult` dataclass is `frozen=True` (`merge.py:109`) with a
   declared `plan: MergePlan` field — `.plan.summary` is always present. The
   defensive fallbacks are dead defense.

**Fix:** Trust the type contract:

```python
else:
    # result is MergeResult (checked above)
    summary = result.plan.summary
    total = sum(summary.values())
    created = summary.get("CREATE", 0)
    updated = summary.get("UPDATE", 0)
    print(
        f"wrote obsidian vault at {Path(obsidian_dir).resolve()} "
        f"\u2014 {total} actions ({created} CREATE, {updated} UPDATE)"
    )
```

If the concern is future-proofing against `to_obsidian` returning a third
type, use an `else: raise TypeError(...)` clause instead of silent fallbacks.

## Info

### IN-01: Local `import json as _json` shadows the module-level import

**File:** `graphify/__main__.py:750`
**Issue:** `json` is already imported at module top (line 3). The function-local
`import json as _json` inside the `--obsidian` branch is redundant and slightly
confusing — readers wonder why the alias exists. The alias was presumably
introduced to avoid shadowing a loop variable or parameter named `json`, but
none exists in this scope.

**Fix:** Drop the alias and use the top-level import:

```python
try:
    from networkx.readwrite import json_graph
    _raw = json.loads(gp.read_text(encoding="utf-8"))
    ...
```

### IN-02: `--validate-profile` does not support `=`-form, but `--obsidian` does

**File:** `graphify/__main__.py:694, 726-733`
**Issue:** Minor UX inconsistency. `--obsidian` accepts both `--graph <path>`
and `--graph=<path>`, but `--validate-profile` only accepts the space-separated
positional form. Users habituated to `--key=value` will be surprised. This is
not a bug — `--validate-profile` treats the vault path as a positional
argument, which is defensible — but a one-line comment above the `argv[2]`
read would document the intent so a future maintainer does not "helpfully" add
`=`-parsing and accidentally break the current contract.

**Fix:** Add a comment, or accept both forms if symmetry with `--obsidian` is
preferred.

### IN-03: Empty-string `--graph=` silently resolves to cwd

**File:** `graphify/__main__.py:728-729, 741`
**Issue:** If the user passes `--graph=` (trailing empty value), `graph_path`
becomes the empty string, and `Path("").resolve()` evaluates to the current
working directory. The subsequent `gp.exists()` check is True (cwd always
exists), so the code progresses to `gp.suffix != ".json"` and errors with
"graph file must be a .json file" instead of the more accurate "graph file
not found". Not a correctness bug, but the error message misleads the user.

**Fix:** Validate non-empty after parsing:

```python
elif args[i].startswith("--graph="):
    graph_path = args[i].split("=", 1)[1]
    if not graph_path:
        print("error: --graph requires a non-empty path", file=sys.stderr)
        sys.exit(2)
    i += 1
```

### IN-04: Broad `except Exception` for `to_obsidian` hides root cause from logs

**File:** `graphify/__main__.py:787-789`
**Issue:** Catching `Exception` and printing only `f"error: to_obsidian failed:
{exc}"` loses the traceback. For end users this is usually fine, but when
`--obsidian` fails inside CI or a script, the shortened message (`"KeyError:
'labels'"` or similar) is often insufficient for debugging. Every other error
branch in this file follows the same pattern, so this is consistent — but
consider adding a `--debug` flag in a future iteration that re-raises or prints
`traceback.format_exc()` to stderr. Not blocking for this phase.

**Fix:** Optional — add traceback printing when a `--debug` or `GRAPHIFY_DEBUG`
environment variable is set. Accept as-is for now.

### IN-05: Unused import `MergePlan` is actually used for `isinstance` — verify

**File:** `graphify/__main__.py:779`
**Issue:** Double-checked — `MergePlan` is imported and used on line 791 for
the `isinstance(result, MergePlan)` dispatch. Not dead code. Flagging here only
because `format_merge_plan` and `MergePlan` are imported together on the same
line, and a reader might mistake the pattern. No action needed; this info item
exists to close the loop on the review.

**Fix:** None.

### IN-06: Test coverage gap — no happy-path test for `--validate-profile` with a real profile

**File:** `tests/test_main_cli.py`
**Issue:** `test_validate_profile_empty_vault_exits_0` only exercises the
short-circuit path (no `.graphify/` subdir, returns zero-counts). There is no
CLI-level test that constructs a minimal `.graphify/profile.yaml` and verifies:
1. `rule_count` is reported correctly in the `"profile ok — N rules, M
   templates validated"` line (the D-77a literal).
2. Warnings (not errors) are printed to stderr and do NOT trigger exit 1.

`profile.py` has unit tests for `validate_profile_preflight`, so the logic is
covered — but the CLI-to-library stdout/stderr wiring for the counts and
warnings is not exercised end-to-end. A broken f-string in line 707-710 would
slip past CI.

**Fix:** Add one test that writes a valid single-rule `profile.yaml` under
`tmp_path/.graphify/profile.yaml` and asserts:

```python
def test_validate_profile_with_real_profile_reports_counts(tmp_path):
    gdir = tmp_path / ".graphify"
    gdir.mkdir()
    (gdir / "profile.yaml").write_text(
        "version: 1\n"
        "mapping_rules:\n"
        "  - when: {file_type: code}\n"
        "    emit: {note_type: concept, folder: Atlas}\n",
        encoding="utf-8",
    )
    result = _run_cli("--validate-profile", str(tmp_path))
    assert result.returncode == 0, f"stderr={result.stderr}"
    assert "profile ok" in result.stdout
    assert "1 rules" in result.stdout
```

Also consider a warnings-path test (preflight returns warnings but zero errors
→ exits 0, warnings appear on stderr).

---

_Reviewed: 2026-04-11_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
_Scope: plan 05-06 gap-closure only (new `--validate-profile` and `--obsidian`
branches in `__main__.py` + new `tests/test_main_cli.py`)_
