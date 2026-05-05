# Plan 62-03 — BLOCKED on auto-adopt argparse defect

**Date:** 2026-05-04
**Status:** Halted per CONTEXT D-17 stop-condition.

## What happened

Plan 62-03 added `tests/test_e2e_integration.py::test_e2e_update_vault_auto_adopts_vault_cwd` per D-13/D-14/D-15. The new test was expected to PASS on shipped main (auto-adopt + APPLY-DET-01 already wired). It does not.

## The bug

`update-vault` is gated at `graphify/__main__.py:3286` — `_check_vault_cwd_gate` fires correctly and emits the auto-adopt stderr notice. But the argparse parser at `graphify/__main__.py:3358` still declares:

```python
_p_vp.add_argument("--vault", required=True, ...)
```

So from `cwd=<vault>` with no `--vault`:

```
[graphify] auto-adopted vault at <cwd> (profile: .graphify/profile.yaml)
graphify update-vault: error: the following arguments are required: --vault
```

Gate runs, prints notice, sets `lv_vault = Path.cwd()` for the dispatch layer — then argparse rejects exit 2 because `--vault` is still `required=True`. Auto-adopt is half-implemented at the CLI surface for `update-vault`.

## Likely scope

Every gated command whose argparse declares `--vault required=True` is affected. `_check_vault_cwd_gate` has 14 gated call sites; only those with required=True argparse `--vault` exhibit this defect. `update-vault` is the one this E2E covers; others may also be broken.

## Working-tree state

- New test stashed at `stash@{0}: On main: phase-62-03-blocked-on-auto-adopt-bug`. Restore with `git stash pop` once the bug is fixed.
- No production code touched.
- Plans 62-01 and 62-02 committed cleanly through `53fead9`.

## How to resume

1. `/gsd-debug` to characterize the gate↔argparse handoff defect, identify all affected gated commands, design a fix (likely either: gate injects `--vault <cwd>` into argv before argparse parses; OR argparse `--vault` declared `required=False` for gated commands and the resolution layer raises if both gate and explicit are absent).
2. Ship the fix as its own phase (cleanup phases must not fix-forward — D-17).
3. Reopen the v1.12 audit to record the WARNING 2 → defect upgrade.
4. `git stash pop` and re-run plan 62-03 once auto-adopt actually works end-to-end.
5. After 62-03 passes, run plan 62-04 (audit closure) — WARNING 2 closure section can then truthfully cite the fix-phase commits AND the 62-03 SHA.

## Plans 62-04 status

Not started. Cannot run while 62-03 is unresolved — the audit closure section would falsely claim WARNING 2 is closed.

---

## RESOLUTION (2026-05-04)

The `--vault required=True` argparse defect was fixed in Phase 62.1 (commit
`56636ce`: "fix(62.1-01): GREEN — flip --vault to required=False with
friendly-error guard for update-vault + vault-promote"), and locked by
Phase 62.1 regression tests (commit `cfe3884`).

Plan 62-03 was re-run on shipped main and its single new test
`test_e2e_update_vault_auto_adopts_vault_cwd` passes:

```
pytest tests/test_e2e_integration.py::test_e2e_update_vault_auto_adopts_vault_cwd -x -q
1 passed in 22.17s
```

Audit WARNING 2 (E2E-AUTO-ADOPT-01) is now closed.
