---
phase: 61-harness-vault-write-error-format-normalization
plan: 01
type: tdd
wave: 1
depends_on: []
files_modified:
  - graphify/__main__.py
  - tests/test_harness_import.py
autonomous: true
requirements: [HARN-FMT-01]
must_haves:
  truths:
    - "import-harness vault-write refusal emits two-line `[graphify] error:` + `  hint:` format (not the legacy one-line `[graphify] refusing to write harness import...`)"
    - "Refusal exit code is 1 (vault-policy-error), not 2 (argv-error)"
    - "tests/test_harness_import.py asserts the new two-line shape AND rejects the old one-line shape (regression guard)"
    - "Full pytest suite remains green after migration"
  artifacts:
    - path: "graphify/__main__.py"
      provides: "import-harness vault-write guard using `raise _emit_vault_error(...)`"
      contains: "raise _emit_vault_error"
    - path: "tests/test_harness_import.py"
      provides: "tightened assertions locking the two-line format"
      contains: "[graphify] error:"
  key_links:
    - from: "graphify/__main__.py (import-harness block ~line 2725)"
      to: "graphify.output._emit_vault_error"
      via: "import + raise"
      pattern: "from graphify\\.output import .*_emit_vault_error"
---

<objective>
Migrate the last surviving one-line `[graphify] refusing to write harness import...` stderr emission at `graphify/__main__.py:2727` to the canonical two-line `[graphify] error: <msg>` + `  hint: <fix>` format established by Phase 58 (VAUX-02), using the existing `_emit_vault_error()` helper from `graphify/output.py:80`. Tighten `tests/test_harness_import.py` to lock the new shape and prevent regression.

Purpose: Final cleanup of vault-error format inconsistency. Every other vault refusal already uses `_emit_vault_error`; this is the last hold-out, and reclassifies its exit code from 2 (argv-error) to 1 (vault-policy-error) for parity.

Output: Updated `__main__.py` call site, tightened test assertions, all suite tests green.
</objective>

<execution_context>
@$HOME/.claude/get-shit-done/workflows/execute-plan.md
@$HOME/.claude/get-shit-done/references/tdd.md
@$HOME/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/STATE.md
@.planning/ROADMAP.md
@.planning/REQUIREMENTS.md
@.planning/phases/61-harness-vault-write-error-format-normalization/61-CONTEXT.md

<interfaces>
<!-- Helper signature (graphify/output.py:80-89) -->
```python
def _emit_vault_error(msg: str, hint: str, code: int = 1) -> SystemExit:
    """Print two-line error to stderr and return SystemExit(code) for `raise`."""
    print(f"[graphify] error: {msg}", file=sys.stderr)
    print(f"  hint: {hint}", file=sys.stderr)
    return SystemExit(code)
```

<!-- Pattern template (graphify/output.py:91-104, _ensure_vault_root) -->
```python
if not is_obsidian_vault(p):
    raise _emit_vault_error(
        f"Not an Obsidian vault (missing .obsidian/ directory): {p}",
        "Pass the root of an Obsidian vault (must contain .obsidian/).",
    )
```

<!-- Current call site at __main__.py:2725-2731 (to be replaced) -->
```python
if not opts.allow_vault_write and is_obsidian_vault(artifacts):
    print(
        f"[graphify] refusing to write harness import under vault root {artifacts}; "
        "pass --allow-vault-write to override.",
        file=sys.stderr,
    )
    sys.exit(2)
```

<!-- Existing import line (extend it): -->
`from graphify.output import is_obsidian_vault`
</interfaces>
</context>

<tasks>

<task type="tdd" tdd="true">
  <name>Task 1: TDD migration of import-harness vault-write refusal to two-line format</name>
  <files>tests/test_harness_import.py, graphify/__main__.py</files>

  <read_first>
    - graphify/__main__.py (lines 2710-2750 — see surrounding import-harness block, current refusal at 2727)
    - graphify/output.py (lines 75-110 — `_emit_vault_error` definition + `_ensure_vault_root` exemplar)
    - tests/test_harness_import.py (lines 130-170 — `test_import_refuses_vault_without_flag` and `test_import_accepts_vault_with_explicit_flag`)
    - .planning/phases/61-harness-vault-write-error-format-normalization/61-CONTEXT.md (D-01 through D-08, NON-NEGOTIABLE)
  </read_first>

  <behavior>
    - When `import-harness` is invoked targeting an Obsidian vault WITHOUT `--allow-vault-write`:
      - stderr contains `[graphify] error: Refusing to write harness import under vault root <path>`
      - stderr contains `  hint: Pass --allow-vault-write to override.`
      - stderr does NOT contain the legacy `refusing to write harness import` (lowercase, one-line) text
      - stderr still mentions `--allow-vault-write` (preserved actionable flag name)
      - exit code is 1 (was 2 — deliberate reclassification per D-03)
    - When `import-harness` is invoked WITH `--allow-vault-write`: behavior unchanged (write proceeds).
  </behavior>

  <action>
    Execute the TDD gate sequence strictly. Do NOT migrate source until RED is captured.

    **=== RED gate ===**

    Edit `tests/test_harness_import.py`. In `test_import_refuses_vault_without_flag` (around line 144), KEEP the existing `assert "--allow-vault-write" in rc.stderr` (per D-07) and ADD these three assertions (per D-06):

    ```python
    assert "[graphify] error:" in rc.stderr
    assert "hint:" in rc.stderr
    assert "refusing to write harness import" not in rc.stderr
    ```

    (Discretion per CONTEXT.md: extending the existing test is preferred over a new dedicated test method — keeps the assertions co-located with the existing flag-name check.)

    Run RED check:
    ```bash
    pytest tests/test_harness_import.py::test_import_refuses_vault_without_flag -q
    ```
    MUST fail (production still emits one-line `[graphify] refusing to write harness import...`). Capture failure output as RED evidence.

    Commit:
    ```
    test(61-01): RED — tighten test_import_refuses_vault_without_flag for two-line format
    ```

    **=== GREEN gate ===**

    Edit `graphify/__main__.py`:

    1. Extend the existing import line (currently `from graphify.output import is_obsidian_vault`) to also import `_emit_vault_error`:
       ```python
       from graphify.output import _emit_vault_error, is_obsidian_vault
       ```
       (If the existing import is laid out differently, preserve its style and add `_emit_vault_error`.)

    2. Replace the block at `__main__.py:2725-2731` (the current `print(...); sys.exit(2)` block) VERBATIM with:
       ```python
       if not opts.allow_vault_write and is_obsidian_vault(artifacts):
           raise _emit_vault_error(
               f"Refusing to write harness import under vault root {artifacts}",
               "Pass --allow-vault-write to override.",
           )
       ```

       Note exact strings (D-04, D-05):
       - msg: `f"Refusing to write harness import under vault root {artifacts}"` (sentence-case "Refusing", interpolates `artifacts` Path resolved at line 2718)
       - hint: `"Pass --allow-vault-write to override."` (verbatim, sentence-case, trailing period)
       - code: omit (defaults to 1 per D-03)

    Per D-02, ONLY migrate the refusal at line 2727. Do NOT touch the adjacent `print(f"[graphify] {exc}", file=sys.stderr)` at ~line 2745 (different error class, out of scope).

    Run GREEN check:
    ```bash
    pytest tests/test_harness_import.py -q
    ```
    MUST pass.

    Then run full suite:
    ```bash
    pytest tests/ -q
    ```
    MUST pass (no unrelated regressions).

    Commit:
    ```
    feat(61-01): GREEN — migrate import-harness vault-write refusal to _emit_vault_error
    ```

    **=== REFACTOR gate ===**

    N/A. The `_emit_vault_error` helper already encapsulates the format; nothing further to clean up. Mark gate as skipped per TDD reference.
  </action>

  <verify>
    <automated>pytest tests/test_harness_import.py -q && pytest tests/ -q</automated>
  </verify>

  <acceptance_criteria>
    Run all of these (each must exit 0 / produce expected output):

    1. New format present in source:
       ```bash
       grep -n 'raise _emit_vault_error' graphify/__main__.py | grep -q 'Refusing to write harness import'
       ```

    2. Old one-line text fully removed from source (negative grep — exit code 1 expected from grep; wrap with `!`):
       ```bash
       ! grep -q 'refusing to write harness import' graphify/__main__.py
       ! grep -q '\[graphify\] refusing to write harness import' graphify/__main__.py
       ```

    3. Old `sys.exit(2)` at the migrated site removed (the surrounding `import-harness` function may still have other exits — this checks the specific refusal block is gone):
       ```bash
       ! grep -B1 -A4 'refusing to write harness import' graphify/__main__.py
       ```

    4. Import updated:
       ```bash
       grep -E 'from graphify\.output import .*_emit_vault_error' graphify/__main__.py
       ```

    5. Test assertions present (D-06 lines 1-3):
       ```bash
       grep -q '"\[graphify\] error:" in rc.stderr' tests/test_harness_import.py
       grep -q '"hint:" in rc.stderr' tests/test_harness_import.py
       grep -q '"refusing to write harness import" not in rc.stderr' tests/test_harness_import.py
       ```

    6. Existing flag-name assertion preserved (D-07):
       ```bash
       grep -q '"--allow-vault-write" in rc.stderr' tests/test_harness_import.py
       ```

    7. Targeted test passes:
       ```bash
       pytest tests/test_harness_import.py::test_import_refuses_vault_without_flag -q
       ```

    8. Full harness test file passes:
       ```bash
       pytest tests/test_harness_import.py -q
       ```

    9. Full suite green:
       ```bash
       pytest tests/ -q
       ```
  </acceptance_criteria>

  <done>
    - Two atomic commits exist: `test(61-01): RED ...` and `feat(61-01): GREEN ...`
    - All nine acceptance criteria above pass
    - `graphify/__main__.py` import-harness vault-write guard uses `raise _emit_vault_error(...)` with exact msg/hint strings from D-04/D-05
    - `_emit_vault_error` added to `from graphify.output import ...` line
    - Old `print(...); sys.exit(2)` block fully removed from the migrated site
    - Adjacent error printing at `__main__.py:~2745` left untouched (D-02)
    - `tests/test_harness_import.py` contains all three new assertions (D-06) plus preserved `--allow-vault-write` assertion (D-07)
  </done>
</task>

</tasks>

<threat_model>
## Trust Boundaries

No new trust boundaries introduced. The import-harness CLI invocation already crosses argv → process boundary; this phase changes only stderr text and exit code.

## STRIDE Threat Register

| Threat ID | Category | Component | Disposition | Mitigation Plan |
|-----------|----------|-----------|-------------|-----------------|
| T-61-01 | Information Disclosure | stderr message in `__main__.py:2727` | accept | New `msg` interpolates `<artifacts>` (resolved vault Path) — identical to legacy one-line; no additional sensitive data exposed. Path is user-supplied and already echoed under prior format. |

**Attack-surface delta: ZERO.** Stderr-format-only change. No new inputs accepted, no new code paths, no new external interaction. Vault-write guard's behavior (refuse-by-default unless `--allow-vault-write`) is unchanged. See `<security_threat_model>` in 61-CONTEXT planning input.
</threat_model>

<verification>
- `pytest tests/test_harness_import.py -q` exits 0
- `pytest tests/ -q` exits 0 (full suite green)
- `grep -q 'raise _emit_vault_error' graphify/__main__.py` (positive)
- `! grep -q 'refusing to write harness import' graphify/__main__.py` (negative — old text gone)
- `grep -q '"\[graphify\] error:" in rc.stderr' tests/test_harness_import.py` (positive)
- `grep -q '"hint:" in rc.stderr' tests/test_harness_import.py` (positive)
- `grep -q '"refusing to write harness import" not in rc.stderr' tests/test_harness_import.py` (positive — regression guard literal asserted in tests)
</verification>

<success_criteria>
- HARN-FMT-01 satisfied: import-harness vault-write refusal emits two-line `[graphify] error:` + `  hint:` format using `_emit_vault_error` helper
- Exit code is 1 (was 2)
- Legacy one-line `[graphify] refusing to write harness import...` literal fully removed from production code
- Test suite locks new shape via three new assertions and full pytest suite passes
- TDD evidence: two atomic commits (RED, GREEN) showing red→green progression
</success_criteria>

<output>
After completion, create `.planning/phases/61-harness-vault-write-error-format-normalization/61-01-SUMMARY.md` covering:
- Files modified (with diff summary)
- TDD gate evidence (RED failure output, GREEN pass output)
- Commit SHAs
- Verification check results
- Confirmation that exit code reclassification (2 → 1) is intentional per D-03
</output>
