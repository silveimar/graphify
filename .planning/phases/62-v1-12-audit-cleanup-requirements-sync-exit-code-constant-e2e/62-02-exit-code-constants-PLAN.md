---
phase: 62-v1-12-audit-cleanup-requirements-sync-exit-code-constant-e2e
plan: 02
type: tdd
wave: 2
depends_on: [01]
files_modified:
  - graphify/output.py
  - graphify/__main__.py
  - tests/test_output.py
autonomous: true
requirements:
  - EXIT-CODE-CONST-01
must_haves:
  truths:
    - "graphify.output exports module-level constants EXIT_VAULT_REFUSAL=1 and EXIT_VAULT_GATE=2"
    - "_emit_vault_error default value is the named constant EXIT_VAULT_REFUSAL (still equals 1)"
    - "_ensure_vault_root explicitly passes code=EXIT_VAULT_REFUSAL at both raise sites"
    - "VCWD-03 site (_check_vault_cwd_gate in __main__.py) passes code=EXIT_VAULT_GATE in place of literal 2"
    - "HARN-FMT-01 site (import-harness vault-write guard in __main__.py) passes explicit code=EXIT_VAULT_REFUSAL"
    - "_emit_vault_error docstring references both constants by name"
    - "_check_vault_cwd_gate docstring references EXIT_VAULT_GATE instead of 'SystemExit(2)' literal"
    - "tests/test_vault_cwd.py and tests/test_harness_import.py remain unchanged and pass"
    - "tests/test_output.py contains a new test asserting both constant names and integer values"
  artifacts:
    - path: "graphify/output.py"
      provides: "Module-level exit-code constants with named-constant default in _emit_vault_error"
      contains: "EXIT_VAULT_REFUSAL"
    - path: "graphify/output.py"
      provides: "EXIT_VAULT_GATE constant"
      contains: "EXIT_VAULT_GATE"
    - path: "graphify/__main__.py"
      provides: "VCWD-03 and HARN-FMT-01 call sites wired to named constants"
      contains: "EXIT_VAULT_GATE"
    - path: "tests/test_output.py"
      provides: "Constant existence + value assertions"
      contains: "EXIT_VAULT_REFUSAL"
  key_links:
    - from: "graphify/__main__.py:1560 (VCWD-03 raise _emit_vault_error)"
      to: "graphify/output.py EXIT_VAULT_GATE"
      via: "from graphify.output import ... EXIT_VAULT_GATE; code=EXIT_VAULT_GATE"
      pattern: "code=EXIT_VAULT_GATE"
    - from: "graphify/__main__.py:2906 (HARN-FMT-01 raise _emit_vault_error)"
      to: "graphify/output.py EXIT_VAULT_REFUSAL"
      via: "from graphify.output import ... EXIT_VAULT_REFUSAL; code=EXIT_VAULT_REFUSAL"
      pattern: "code=EXIT_VAULT_REFUSAL"
---

<objective>
Close audit finding EXIT-CODE-CONST-01 (audit "WARNING 1"): introduce named exit-code constants in `graphify/output.py` and replace the magic numbers `1`/`2` at all four call sites. Behavior must NOT change — both wire values stay the same; only legibility improves.

Purpose: Eliminate un-grepable literal `2` at `__main__.py:1560` and make the divergence between vault-policy refusal (code 1) and vault-CWD gate refusal (code 2) explicit at the call site. Provide a stable importable symbol for downstream exit-code parsers.
Output: Two new constants exported from `graphify.output`, four call sites rewired, two docstrings updated, one new symbol-existence test in `tests/test_output.py`. Net behavior change: zero.
</objective>

<execution_context>
@$HOME/.claude/get-shit-done/workflows/execute-plan.md
@$HOME/.claude/get-shit-done/templates/summary.md
@$HOME/.claude/get-shit-done/references/tdd.md
</execution_context>

<context>
@.planning/PROJECT.md
@.planning/ROADMAP.md
@.planning/STATE.md
@.planning/phases/62-v1-12-audit-cleanup-requirements-sync-exit-code-constant-e2e/62-CONTEXT.md
@.planning/v1.12-MILESTONE-AUDIT.md
@.planning/phases/61-harness-vault-write-error-format-normalization/61-CONTEXT.md
@graphify/output.py
@graphify/__main__.py

<interfaces>
<!-- Existing _emit_vault_error signature (output.py:80) — preserved verbatim except for default literal. -->

```python
# Current (output.py:~80)
def _emit_vault_error(msg: str, hint: str, *, code: int = 1) -> SystemExit:
    """..."""
    print(f"[graphify] error: {msg}", file=sys.stderr)
    print(f"  hint: {hint}", file=sys.stderr)
    return SystemExit(code)
```

```python
# Target (additions above the function)
EXIT_VAULT_REFUSAL = 1   # vault-policy refusal (e.g. write into vault root, no profile)
EXIT_VAULT_GATE = 2      # VCWD-03 gate refusal (CWD is vault, no profile, no override)

def _emit_vault_error(msg: str, hint: str, *, code: int = EXIT_VAULT_REFUSAL) -> SystemExit:
    """..."""
```

<!-- Four call sites to update (all use `raise _emit_vault_error(...)` form): -->
<!-- 1. graphify/output.py:~95   _ensure_vault_root path-not-dir branch       -> add code=EXIT_VAULT_REFUSAL -->
<!-- 2. graphify/output.py:~100  _ensure_vault_root not-a-vault branch        -> add code=EXIT_VAULT_REFUSAL -->
<!-- 3. graphify/__main__.py:1560 _check_vault_cwd_gate VCWD-03 raise         -> change code=2 -> code=EXIT_VAULT_GATE -->
<!-- 4. graphify/__main__.py:2906 import-harness vault-write guard            -> add code=EXIT_VAULT_REFUSAL -->

<!-- Existing imports (extend, don't add new lines): -->
<!-- __main__.py:1535: from graphify.output import is_obsidian_vault, _emit_vault_error -->
<!-- __main__.py:2904: from graphify.output import is_obsidian_vault, _emit_vault_error -->
<!-- After change: each imports also EXIT_VAULT_GATE (line 1535) or EXIT_VAULT_REFUSAL (line 2904) -->

<!-- _check_vault_cwd_gate docstring excerpt (__main__.py:1525-1529) currently reads: -->
<!--   "or 'refuse' (never returned — raises SystemExit(2) via _emit_vault_error)." -->
<!--   "Raises SystemExit(2) via _emit_vault_error() when ..." -->
<!-- Target: replace `SystemExit(2)` with `SystemExit(EXIT_VAULT_GATE)` in both occurrences. -->
</interfaces>
</context>

<tasks>

<task type="tdd" tdd="true">
  <name>Task 1: RED — add constant-existence test in tests/test_output.py (D-11)</name>
  <files>tests/test_output.py</files>
  <behavior>
    - Test `test_emit_vault_error_exit_code_constants` imports `EXIT_VAULT_REFUSAL` and `EXIT_VAULT_GATE` from `graphify.output`.
    - Asserts `EXIT_VAULT_REFUSAL == 1`.
    - Asserts `EXIT_VAULT_GATE == 2`.
    - Asserts they are plain `int` instances (not str/Enum) so `SystemExit(code)` interprets them as POSIX exit codes.
    - Asserts the default `code` parameter of `_emit_vault_error` equals `EXIT_VAULT_REFUSAL` (use `inspect.signature` to introspect the default value and compare).
  </behavior>
  <action>Per D-11: add a new top-level test function `test_emit_vault_error_exit_code_constants` to `tests/test_output.py` (planner choice per "Claude's Discretion": top-level test, not extension of an existing one — keeps the symbol-contract test discoverable by name). Imports: `from graphify.output import EXIT_VAULT_REFUSAL, EXIT_VAULT_GATE, _emit_vault_error` and `import inspect`. Use four assertions as specified in `<behavior>`. Run pytest and confirm the test FAILS with `ImportError` (constants do not yet exist). Commit with message `test(62-02): RED — add EXIT_VAULT_REFUSAL/EXIT_VAULT_GATE constant-existence test`.</action>
  <verify>
    <automated>pytest tests/test_output.py::test_emit_vault_error_exit_code_constants -x 2>&amp;1 | grep -E "ImportError|cannot import name 'EXIT_VAULT_REFUSAL'"</automated>
  </verify>
  <done>The new test exists in tests/test_output.py and fails with ImportError on a fresh test run, locking the RED step.</done>
</task>

<task type="auto" tdd="true">
  <name>Task 2: GREEN — define constants + rewire 4 call sites + update 2 docstrings (D-03..D-10)</name>
  <files>graphify/output.py, graphify/__main__.py</files>
  <action>
Per D-03 / D-04: in `graphify/output.py`, directly above the existing `def _emit_vault_error(...)` (currently around line 80), add:

```python
EXIT_VAULT_REFUSAL = 1
EXIT_VAULT_GATE = 2
```

Per D-08: change the `_emit_vault_error` default from `code: int = 1` to `code: int = EXIT_VAULT_REFUSAL`. Wire value still equals 1.

Per D-09: extend the `_emit_vault_error` docstring (currently 4 lines) by adding a 2–3 line note that names both constants and explains the policy split: `EXIT_VAULT_REFUSAL` for vault-policy refusals (default), `EXIT_VAULT_GATE` for the VCWD-03 CWD gate refusal. Keep total docstring under ~8 lines.

Per D-07: update both `raise _emit_vault_error(...)` sites inside `_ensure_vault_root` (currently lines ~95 and ~100) to add an explicit `code=EXIT_VAULT_REFUSAL` keyword argument. The default already equals 1; this is a presentation change only.

Per D-05: in `graphify/__main__.py`, in `_check_vault_cwd_gate` (around line 1535), extend the existing local import to:
`from graphify.output import is_obsidian_vault, _emit_vault_error, EXIT_VAULT_GATE`
Then in the `raise _emit_vault_error(...)` call (currently around line 1560), change `code=2` → `code=EXIT_VAULT_GATE`. Wire value still equals 2.

Per D-10: in `_check_vault_cwd_gate`'s docstring (around lines 1525–1529), replace both occurrences of `SystemExit(2)` with `SystemExit(EXIT_VAULT_GATE)`. Two textual replacements; do not reflow the rest of the docstring.

Per D-06: in `graphify/__main__.py` (around line 2904), extend the existing local import to:
`from graphify.output import is_obsidian_vault, _emit_vault_error, EXIT_VAULT_REFUSAL`
In the `raise _emit_vault_error(...)` block immediately following (around line 2906), add an explicit `code=EXIT_VAULT_REFUSAL` keyword argument as the third argument. The default already equals 1; this makes the divergence between this site (refusal) and the VCWD-03 site (gate) visible.

Do NOT touch `tests/test_vault_cwd.py` or `tests/test_harness_import.py` — they are regression guards (D-12). Do NOT change message strings. Do NOT renumber requirements. Do NOT alter the wire values 1 and 2.

Run the new RED test and confirm it now passes (GREEN). Run the full suite and confirm nothing else regressed.

Commit with message `refactor(62-02): name vault-error exit codes via EXIT_VAULT_REFUSAL/EXIT_VAULT_GATE`.
  </action>
  <verify>
    <automated>pytest tests/test_output.py::test_emit_vault_error_exit_code_constants tests/test_vault_cwd.py tests/test_harness_import.py -x -q</automated>
  </verify>
  <done>
    - New test passes (constants exist with correct values and default).
    - tests/test_vault_cwd.py passes unchanged (VCWD-03 still exits 2).
    - tests/test_harness_import.py passes unchanged (HARN-FMT-01 still exits 1).
    - `grep -n "code=2" graphify/__main__.py` returns no production-code hits in the VCWD-03 site (lines around 1560).
    - `grep -n "EXIT_VAULT_GATE\|EXIT_VAULT_REFUSAL" graphify/output.py graphify/__main__.py` returns the expected 6+ usages (2 defs in output.py, 2 explicit code= passes in output.py _ensure_vault_root, 2 imports + 2 code= passes in __main__.py, 2 docstring mentions in __main__.py).
  </done>
</task>

<task type="auto">
  <name>Task 3: Full-suite regression sweep</name>
  <files>(no edits — verification only)</files>
  <action>Run `pytest tests/ -q` to confirm no regressions across the full suite. Phase 62 changes are presentation-only at the call sites and additive in graphify/output.py; the suite must stay green. If any test fails, STOP and triage before any further commits — a failure here means the constant wiring is wrong (per D-12).</action>
  <verify>
    <automated>pytest tests/ -q</automated>
  </verify>
  <done>Full pytest suite passes on Python 3.10 (CI parity). No regressions in test_vault_cwd.py, test_harness_import.py, test_output.py, or any other module.</done>
</task>

</tasks>

<verification>
- `grep -n "EXIT_VAULT_REFUSAL\|EXIT_VAULT_GATE" graphify/output.py | wc -l` returns ≥4 (2 definitions + 2 explicit code= in `_ensure_vault_root` + default value reference).
- `grep -n "EXIT_VAULT_GATE" graphify/__main__.py | wc -l` returns ≥3 (1 import + 1 code= + 2 docstring mentions).
- `grep -n "EXIT_VAULT_REFUSAL" graphify/__main__.py | wc -l` returns ≥2 (1 import + 1 code= at HARN-FMT-01).
- The literal `code=2` no longer appears in `graphify/__main__.py` production code.
- The wire exit codes from VCWD-03 (subprocess) remain `2`; from HARN-FMT-01 (subprocess) remain `1` (locked by existing tests).
- `pytest tests/ -q` is green.
</verification>

<success_criteria>
- Constants exist, are named per D-04, equal 1 and 2 respectively.
- `_emit_vault_error` default uses the constant; docstring names both constants.
- All four call sites use named constants (D-05, D-06, D-07, D-08 satisfied).
- `_check_vault_cwd_gate` docstring no longer says `SystemExit(2)` (D-10).
- `tests/test_output.py` contains the constant-existence test (D-11).
- `tests/test_vault_cwd.py` and `tests/test_harness_import.py` are byte-identical to their pre-phase versions and still pass (D-12).
- Full pytest suite green.
</success_criteria>

<risk_and_rollback>
- **Risk class**: low. Behavior-preserving rename of literals to module-level constants. Wire values unchanged.
- **Regression guards untouched**: `tests/test_vault_cwd.py` and `tests/test_harness_import.py` are NOT modified. Their continued passing is the primary signal that the rewiring is correct. Phase 61 D-03 contract (HARN-FMT-01 = code 1) is preserved by D-06 setting `code=EXIT_VAULT_REFUSAL` (= 1).
- **Wire-value lock**: D-04 fixes `EXIT_VAULT_REFUSAL = 1` and `EXIT_VAULT_GATE = 2`. The new test in `tests/test_output.py` locks both values, preventing accidental future drift.
- **Rollback**: revert the GREEN commit (Task 2). The RED test commit can stay or be reverted as a pair — without the constants it will fail, so it should be reverted together if rolling back.
</risk_and_rollback>

<output>
After completion, create `.planning/phases/62-v1-12-audit-cleanup-requirements-sync-exit-code-constant-e2e/62-02-SUMMARY.md` listing the four call sites updated, the two constant values, and the SHA of the GREEN commit (this SHA feeds plan 62-04).
</output>
