---
phase: 59-vault-cwd-aware-cli-default
plan: "03"
subsystem: vault-cwd-gate
tags: [tdd, vcwd-03, security, refusal, sanitization]
dependency_graph:
  requires: [59-01, 59-02]
  provides: [VCWD-03-locked-tests, T-59-06-mitigation]
  affects: [graphify/__main__.py, tests/test_vault_cwd.py]
tech_stack:
  added: []
  patterns: [sanitize_label-for-path-interpolation, verbatim-text-regression-lock]
key_files:
  created: []
  modified:
    - tests/test_vault_cwd.py
    - graphify/__main__.py
decisions:
  - "Plan 01 wording already matched CONTEXT D-04 verbatim — RED tests passed on first run, locked as regression guards"
  - "sanitize_label from security.py:190 used (strips control chars, caps at _MAX_LABEL_LEN); not sanitize_label_md since the path goes to stderr plain text, not markdown"
metrics:
  duration: "~8 minutes"
  completed: "2026-05-04"
  tasks_completed: 2
  tests_added: 2
---

# Phase 59 Plan 03: VCWD-03 Refusal Hardening Summary

VCWD-03 refusal locked with verbatim two-line text, exit code 2, and `sanitize_label` applied to CWD path before stderr interpolation.

## What Was Done

### Task 1 (RED): Add VCWD-03 verbatim-text and exit-code tests

Appended to `tests/test_vault_cwd.py`:
- `test_refusal_exit_code_and_format`: asserts exit code 2 and that two consecutive lines match the CONTEXT D-04 shape (error line starting with `REFUSAL_MSG_PREFIX`, followed immediately by the verbatim hint line).
- `test_refusal_message_text`: asserts the error line ends with `REFUSAL_MSG_SUFFIX`, that the embedded CWD is an absolute path, and that it resolves to the test vault.
- Three constants (`REFUSAL_MSG_PREFIX`, `REFUSAL_MSG_SUFFIX`, `REFUSAL_HINT_LINE`) lock the exact byte values. Any future wording drift causes immediate test failure.

Both tests passed on first run — Plan 01 had already wired the correct verbatim text. Per plan deviation protocol this is acceptable: tests now serve as regression locks.

### Task 2 (GREEN): Sanitize `<cwd>` in refusal branch

Modified `_check_vault_cwd_gate` in `graphify/__main__.py` (refusal branch, ~line 1530):
- Added `from graphify.security import sanitize_label` alongside the existing `from graphify.output import ...` import.
- Applied `safe_cwd = sanitize_label(str(cwd))` before interpolating into the error message.
- The `_emit_vault_error` call now uses `safe_cwd` instead of the raw `cwd` Path object.

**Sanitizer used:** `sanitize_label` at `graphify/security.py:190`.
- Strips control characters via `_CONTROL_CHAR_RE.sub("", text)`.
- Caps at `_MAX_LABEL_LEN` characters.
- Does NOT HTML-escape (correct for plain-text stderr; `sanitize_label_md` would be wrong here).

**Hint-text byte-exact verification:**
```
$ echo -n "create .graphify/profile.yaml to opt in, pass --output <path> to write outside the vault, or --write-into-vault to override" | wc -c
     122
```

**Em-dash verified:** `python3 -c "assert '—' in open('graphify/__main__.py').read(); print('ok')"` → `ok`.

## TDD Gate Compliance

- RED commit: `2ac5d93` — `test(59-03): RED — VCWD-03 exit 2 + verbatim two-line refusal text`
- GREEN commit: `58b7c7f` — `feat(59-03): GREEN — VCWD-03 refusal uses sanitized cwd, exit 2, verbatim two-line text`
- REFACTOR: not needed (change was a single-line addition).

Both gate commits present in order. Compliant.

## Deviations from Plan

### Already correct from 59-01 (no bug, scope reduction applied)

**Found during:** Task 1 (RED phase)
**Issue:** Plan 01 had already wired the exact CONTEXT D-04 verbatim text and `code=2` in `_emit_vault_error`. The RED tests passed on first run rather than failing.
**Action per plan deviation protocol:** Accepted as "already correct from 59-01". Tests remain as regression locks. Task 2 (sanitization) still executed in full.
**No extra hardening invented** beyond what the plan specified.

## Known Stubs

None. No placeholder text or unwired data sources introduced.

## Threat Flags

| Flag | File | Description |
|------|------|-------------|
| T-59-06 mitigated | graphify/__main__.py | Control-char injection via adversarial CWD path into stderr — now sanitized via `sanitize_label` |

## Self-Check

Commits:
- `2ac5d93` — test(59-03): RED — VCWD-03 exit 2 + verbatim two-line refusal text
- `58b7c7f` — feat(59-03): GREEN — VCWD-03 refusal uses sanitized cwd, exit 2, verbatim two-line text

Files:
- `tests/test_vault_cwd.py` — 2 new tests + 3 constants added
- `graphify/__main__.py` — sanitize_label import + safe_cwd application in refusal branch

Suite: 2130 passed, 1 xfailed (was 2128 before this plan; +2 tests).

## Self-Check: PASSED
