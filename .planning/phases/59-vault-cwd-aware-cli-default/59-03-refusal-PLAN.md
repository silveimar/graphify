---
phase: 59-vault-cwd-aware-cli-default
plan: 03
type: tdd
wave: 2
depends_on: [59-01, 59-02]
files_modified:
  - tests/test_vault_cwd.py
  - graphify/__main__.py
autonomous: true
requirements: [VCWD-03]
nyquist_compliant: true
must_haves:
  truths:
    - "From a profile-less Obsidian vault CWD with no explicit routing flags, every gated command exits with code 2."
    - "The stderr output is exactly two lines: `[graphify] error: refusing to write into Obsidian vault at <cwd> — no .graphify/profile.yaml found` and `  hint: create .graphify/profile.yaml to opt in, pass --output <path> to write outside the vault, or --write-into-vault to override`."
    - "<cwd> is the resolved absolute path, sanitized via security.py rules before interpolation."
  artifacts:
    - path: "graphify/__main__.py"
      provides: "_check_vault_cwd_gate raises _emit_vault_error(..., code=2) with sanitized cwd in the refusal branch"
      contains: "code=2"
  key_links:
    - from: "_check_vault_cwd_gate refusal branch"
      to: "graphify.output._emit_vault_error"
      via: "raise _emit_vault_error(msg, hint, code=2)"
      pattern: "_emit_vault_error.*code=2"
---

<objective>
VCWD-03 wiring: Plan 01 already inserted the `_emit_vault_error(..., code=2)` call. Plan 03 hardens the call site (sanitize `<cwd>` per security.py) and adds the verbatim-text + exit-code RED tests.

Purpose: Guarantee exit-code 2, exact two-line wording (CONTEXT D-04 locked verbatim), and `<cwd>` safe interpolation.
Output: 2 RED test rows + sanitization wiring confirming the message format.
</objective>

<execution_context>
@$HOME/.claude/get-shit-done/workflows/execute-plan.md
@$HOME/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/REQUIREMENTS.md
@.planning/phases/59-vault-cwd-aware-cli-default/59-CONTEXT.md
@.planning/phases/59-vault-cwd-aware-cli-default/59-RESEARCH.md
@.planning/phases/59-vault-cwd-aware-cli-default/59-VALIDATION.md
@.planning/phases/59-vault-cwd-aware-cli-default/59-01-SUMMARY.md
@graphify/output.py
@graphify/security.py
@graphify/__main__.py
@tests/test_vault_cwd.py

<interfaces>
From graphify/output.py (line 80):
```python
def _emit_vault_error(msg: str, hint: str, *, code: int = 1) -> SystemExit:
    """Emit two-line `[graphify] error: <msg>` + `  hint: <hint>` and raise SystemExit(code).
    Phase 58/61 contract — exact bytes asserted by tests."""
```

From graphify/security.py:
```python
# Verify at execution time which sanitizer is appropriate. Candidates:
#   - sanitize_label(s: str) -> str    # HTML-escape, control-char strip, length cap
#   - validate_path(p: Path) -> Path   # path confinement
# Use grep at execution: grep -n "^def " graphify/security.py
```
</interfaces>
</context>

<tasks>

<task type="tdd" tdd="true">
  <name>Task 1 (RED): Add VCWD-03 verbatim-text and exit-code tests</name>
  <files>tests/test_vault_cwd.py</files>
  <behavior>
    - test_refusal_exit_code_and_format may PASS partially (Plan 01 already raises with code=2) but the verbatim-text test surfaces wording drift if any.
    - test_refusal_message_text PASSES iff Plan 01 helper text matches CONTEXT D-04 verbatim. If Plan 01 used different wording, this test fails RED here.
  </behavior>
  <read_first>
    - tests/test_vault_cwd.py
    - .planning/phases/59-vault-cwd-aware-cli-default/59-CONTEXT.md (Decision 4 — verbatim)
  </read_first>
  <action>
Append to `tests/test_vault_cwd.py`:

```python
REFUSAL_MSG_PREFIX = "[graphify] error: refusing to write into Obsidian vault at "
REFUSAL_MSG_SUFFIX = " — no .graphify/profile.yaml found"
REFUSAL_HINT_LINE = "  hint: create .graphify/profile.yaml to opt in, pass --output <path> to write outside the vault, or --write-into-vault to override"


def test_refusal_exit_code_and_format(tmp_path):
    """VCWD-03: profile-less vault CWD → exit 2 + two-line stderr."""
    vault = _make_partial_vault(tmp_path, with_profile=False)
    proc = _graphify("run", cwd=str(vault))
    assert proc.returncode == 2, f"expected exit 2, got {proc.returncode}\nstderr:\n{proc.stderr}"
    # Two-line shape: error line + hint line. Allow trailing newline; reject extra non-empty lines.
    err_lines = [ln for ln in proc.stderr.splitlines() if ln.strip()]
    # The two VCWD-03 lines must appear consecutively.
    error_idx = next((i for i, ln in enumerate(err_lines) if ln.startswith(REFUSAL_MSG_PREFIX)), None)
    assert error_idx is not None, f"missing error line:\n{proc.stderr}"
    assert err_lines[error_idx + 1] == REFUSAL_HINT_LINE, (
        f"hint line mismatch.\n"
        f"  expected: {REFUSAL_HINT_LINE!r}\n"
        f"  actual:   {err_lines[error_idx + 1]!r}\n"
        f"full stderr:\n{proc.stderr}"
    )


def test_refusal_message_text(tmp_path):
    """VCWD-03: error line MUST match CONTEXT D-04 verbatim (prefix + suffix shape)."""
    vault = _make_partial_vault(tmp_path, with_profile=False)
    proc = _graphify("run", cwd=str(vault))
    error_line = next(
        (ln for ln in proc.stderr.splitlines() if ln.startswith(REFUSAL_MSG_PREFIX)),
        None,
    )
    assert error_line is not None
    assert error_line.endswith(REFUSAL_MSG_SUFFIX), f"suffix mismatch: {error_line!r}"
    # Path between prefix and suffix is the resolved cwd. It MUST be absolute.
    cwd_in_msg = error_line[len(REFUSAL_MSG_PREFIX):-len(REFUSAL_MSG_SUFFIX)]
    assert Path(cwd_in_msg).is_absolute(), f"cwd in msg must be absolute: {cwd_in_msg!r}"
    # Sanity check: the cwd in the message resolves to our test vault.
    assert Path(cwd_in_msg).resolve() == vault.resolve(), (
        f"cwd in msg {cwd_in_msg!r} should equal {vault!r}"
    )
```

Commit message: `test(59-03): RED — VCWD-03 exit 2 + verbatim two-line refusal text`
  </action>
  <acceptance_criteria>
    - 2 new tests added; collectable via `pytest tests/test_vault_cwd.py -k refusal --collect-only -q`.
    - `pytest tests/test_vault_cwd.py::test_refusal_message_text -x` exits non-zero IF Plan 01 wording drifted, else exits 0 (acceptable — the test is now LOCKED for regression).
    - Commit prefix `test(59-03): RED`.
  </acceptance_criteria>
  <verify>
    <automated>pytest tests/test_vault_cwd.py -k refusal --collect-only -q</automated>
  </verify>
  <done>2 RED tests added; verbatim text locked in test assertions.</done>
</task>

<task type="tdd" tdd="true">
  <name>Task 2 (GREEN): Sanitize <cwd> via security.py and confirm exit 2 + verbatim text</name>
  <files>graphify/__main__.py</files>
  <behavior>
    - Both VCWD-03 tests PASS.
    - `<cwd>` interpolated into the refusal message passes through `graphify/security.py` sanitization (label or path sanitizer; whichever exists at HEAD).
    - Exit code is 2 (not the default 1 of `_emit_vault_error`).
  </behavior>
  <read_first>
    - graphify/security.py — `grep -n "^def " graphify/security.py` to enumerate sanitizers (likely `sanitize_label`, `validate_path`, `_sanitize_path` or similar).
    - graphify/__main__.py — `_check_vault_cwd_gate` body (added in Plan 01).
  </read_first>
  <action>
**Step 1 — Pick the appropriate sanitizer.** Read `graphify/security.py` and identify the exposed function(s). The minimum requirement: strip control characters and HTML-dangerous bytes from the absolute path string before interpolation. If `security.py` exposes `sanitize_label(s: str) -> str`, use it. If only `validate_path` exists, supplement with a small inline `re.sub(r'[\x00-\x1f]', '', str(cwd))` filter.

**Step 2 — Update `_check_vault_cwd_gate` refusal branch:**

```python
# Replace the existing refusal raise with sanitized interpolation.
from graphify.security import sanitize_label  # if exposed; else use the alternative below
safe_cwd = sanitize_label(str(cwd))  # OR fallback:
# safe_cwd = "".join(ch for ch in str(cwd) if ch.isprintable())
raise _emit_vault_error(
    f"refusing to write into Obsidian vault at {safe_cwd} — no .graphify/profile.yaml found",
    "create .graphify/profile.yaml to opt in, pass --output <path> to write outside the vault, or --write-into-vault to override",
    code=2,
)
```

**Verbatim wording (locked in CONTEXT D-04):**
- Error message body (without `[graphify] error: ` prefix added by `_emit_vault_error`):
  `refusing to write into Obsidian vault at <cwd> — no .graphify/profile.yaml found`
- Hint body (without `  hint: ` prefix added by `_emit_vault_error`):
  `create .graphify/profile.yaml to opt in, pass --output <path> to write outside the vault, or --write-into-vault to override`

Note the em-dash `—` (U+2014), NOT a hyphen `-`. Tests assert this character exactly.

**Step 3 — Confirm `_emit_vault_error` formats lines as `[graphify] error: <msg>\n  hint: <hint>\n` and exits with the supplied code.** If you find any deviation in the helper, do NOT modify the helper (CONTEXT prior_decisions: signatures unchanged). Adjust the message body instead.

Commit message: `feat(59-03): GREEN — VCWD-03 refusal uses sanitized cwd, exit 2, verbatim two-line text`
  </action>
  <acceptance_criteria>
    - `pytest tests/test_vault_cwd.py -k refusal -x -q` PASSES.
    - `grep -v '^#' graphify/__main__.py | grep -c "code=2"` >= 1.
    - `grep -nE "(sanitize_label|isprintable)" graphify/__main__.py` shows at least 1 hit (sanitization wired).
    - The em-dash character `—` (U+2014) appears in the refusal message text in `graphify/__main__.py`: `python -c "print('—' in open('graphify/__main__.py').read())"` outputs `True`.
    - `pytest tests/ -q` exits 0; ≥ 2123 + 7 baseline (Plans 01–03 cumulative).
  </acceptance_criteria>
  <verify>
    <automated>pytest tests/test_vault_cwd.py -k refusal -x -q && python -c "assert '—' in open('graphify/__main__.py').read(), 'em-dash missing'" && pytest tests/ -q</automated>
  </verify>
  <done>VCWD-03 verbatim text + exit 2 + sanitized cwd confirmed; full suite green.</done>
</task>

</tasks>

<threat_model>
## Trust Boundaries

| Boundary | Description |
|----------|-------------|
| CWD path → stderr error message | Path string interpolated into user-visible error |

## STRIDE Threat Register

| Threat ID | Category | Component | Disposition | Mitigation Plan |
|-----------|----------|-----------|-------------|-----------------|
| T-59-06 | Information Disclosure | Adversarial control characters in CWD path leaking into terminal | mitigate | Sanitize via `graphify/security.py` (or printable-filter fallback) before interpolating into the `[graphify] error:` line. |
| T-59-07 | Tampering | Hint-line wording drift breaking downstream tooling that greps for it | mitigate | Tests assert the verbatim hint string; any future change to wording must update the locked test. |
</threat_model>

<verification>
- 2 VCWD-03 tests green.
- Em-dash present in source.
- Sanitizer wired (grep confirms).
- Full suite green.
</verification>

<success_criteria>
- ROADMAP success criterion 3: exit 2 + two-line `[graphify] error:` / `  hint:` (via `_emit_vault_error`) suggesting `--output <path>` or `--write-into-vault`.
</success_criteria>

<output>
After completion, create `.planning/phases/59-vault-cwd-aware-cli-default/59-03-SUMMARY.md` documenting:
- Sanitizer used (name + `security.py` line)
- Hint-text byte-exact verification (echo $hint | wc -c)
</output>
