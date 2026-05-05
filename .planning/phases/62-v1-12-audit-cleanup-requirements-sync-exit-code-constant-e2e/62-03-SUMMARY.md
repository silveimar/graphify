---
phase: 62-v1-12-audit-cleanup-requirements-sync-exit-code-constant-e2e
plan: 03
subsystem: testing
tags: [e2e, vault-cwd, auto-adopt, apply-det-01, audit-closure]
requires: [56636ce, cfe3884]   # Phase 62.1 argparse fix + regression locks
provides:
  - "E2E coverage for update-vault auto-adopt path through preview→apply"
  - "Determinism lock (APPLY-DET-01) under auto-adopt routing"
affects:
  - tests/test_e2e_integration.py
tech-stack:
  added: []
  patterns: ["subprocess E2E", "TDD-by-spec (RED→GREEN single-step)"]
key-files:
  created: []
  modified:
    - tests/test_e2e_integration.py
decisions:
  - "TDD-by-spec: production fix already on main from Phase 62.1; new test acts as both RED and GREEN by locking shipped behavior."
  - "Did NOT extend _run_update_vault_preview_then_apply helper — it passes --vault explicitly, defeating the auto-adopt path. Inlined two subprocess calls instead per CONTEXT note."
  - "Preview 2 deletes the migration JSON between previews to force re-generation and prove plan_id determinism (APPLY-DET-01) survives auto-adopt."
metrics:
  duration: "~3 min"
  completed: 2026-05-04
---

# Phase 62 Plan 03: E2E Test for Vault-CWD Auto-Adopt Summary

One-liner: Added `test_e2e_update_vault_auto_adopts_vault_cwd` to lock the Phase 62.1 argparse `--vault required=False` fix end-to-end and prove APPLY-DET-01 determinism survives auto-adopt routing.

## What was built

A single new test function appended to `tests/test_e2e_integration.py` that exercises the auto-adopt path the existing helpers never covered (the existing helper always passes `--vault` explicitly).

### New test signature

```python
def test_e2e_update_vault_auto_adopts_vault_cwd(tmp_path: Path) -> None: ...
```

### Subprocess call signatures (auto-adopt — NO `--vault` flag)

```python
# Preview 1 (auto-adopt)
_graphify(["update-vault", "--input", str(corpus)], cwd=vault)

# Preview 2 (determinism check after deleting migration JSON)
_graphify(["update-vault", "--input", str(corpus)], cwd=vault)

# Apply (auto-adopt)
_graphify(["update-vault", "--input", str(corpus), "--apply", "--plan-id", plan_id_1], cwd=vault)
```

### Behavior locked

1. Preview 1 from `cwd=<vault>` exits 0 and emits `"auto-adopted vault at"` exactly once.
2. Migration plan JSON is produced under `<vault>.parent/graphify-out/migrations/`.
3. Preview 2 (after deleting plan JSON) regenerates the same `plan_id` (APPLY-DET-01).
4. Apply with the captured plan_id from `cwd=<vault>` (still no `--vault`) exits 0.
5. Notes are materialized as `*.md` under `<vault>.parent/graphify-out/`.
6. No `[graphify] error:` line appears in any stderr (proves auto-adopt branch, not VCWD-03 refusal).

## Test results

```
pytest tests/test_e2e_integration.py::test_e2e_update_vault_auto_adopts_vault_cwd -x -q
1 passed in 22.17s

pytest tests/test_e2e_integration.py tests/test_vault_cwd.py tests/test_harness_import.py -q
33 passed in 56.53s

pytest tests/ -q
1 failed, 2144 passed, 1 xfailed, 8 warnings in 133.85s
```

## Deviations from Plan

### Pre-existing failure (out of scope)

`tests/test_migration.py::test_preview_expands_risky_action_rows` fails on the full suite. Verified pre-existing via `git stash` round-trip on clean main — unrelated to plan 62-03 (test-only addition cannot affect a migration unit test). Logged in `.planning/phases/62-v1-12-…/deferred-items.md` for triage in a follow-up phase. Per executor scope-boundary rules this is out of scope.

### Resolution of stale BLOCKED file

`62-03-BLOCKED.md` (from a prior blocked attempt before Phase 62.1 shipped the argparse fix) was renamed to `62-03-BLOCKED-RESOLVED.md` with a resolution section appended pointing at commits `56636ce` (fix) and `cfe3884` (regression lock).

### Auth gates

None.

## Commits

| Commit | Message |
|--------|---------|
| `522e290` | test(62-03): add E2E coverage for update-vault auto-adopt from vault CWD |

## TDD Gate Compliance

This plan was declared `type: tdd` with a single TDD task. Per the plan's own
`<action>` block: "If [the test] passes, the RED→GREEN cycle is satisfied as
a single TDD step (test added, behavior already correct, test locks the
behavior)." This is TDD-by-spec — the production fix shipped in Phase 62.1
(commit `56636ce`), so the new test passes on first run. A single `test(62-03):`
commit was created. No separate `feat(...)` GREEN commit exists because no
production code change was needed in this plan; the corresponding GREEN
commit lives in Phase 62.1 history.

## Self-Check: PASSED

- File `tests/test_e2e_integration.py` exists and contains exactly one
  `def test_e2e_update_vault_auto_adopts_vault_cwd` (verified: `grep -c` → 1).
- Commit `522e290` exists in `git log` on `main`.
- `tests/test_vault_cwd.py` and `tests/test_harness_import.py` are byte-identical
  to pre-phase versions (no diff).
- `.planning/REQUIREMENTS.md` is unchanged by this plan (D-16 enforced).
