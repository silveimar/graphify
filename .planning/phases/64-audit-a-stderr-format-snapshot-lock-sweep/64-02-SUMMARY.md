---
phase: 64
plan: 02
subsystem: stderr-format-audit
tags: [stderr, audit, prefix-whitelist, invariant-test, AUDIT-02]
dependency_graph:
  requires: [64-01]
  provides: [zero-outlier-stderr-codebase, grep-invariant-test]
  affects: [graphify/__main__.py, graphify/serve.py, graphify/profile.py, graphify/naming.py, graphify/vault_promote.py, graphify/watch.py, graphify/seed.py, graphify/dedup.py, graphify/harness_export.py, graphify/extract.py]
tech_stack:
  added: []
  patterns: [D-04 strict prefix whitelist enforcement, grep-based CI invariant test]
key_files:
  created:
    - tests/test_stderr_contract.py (brought from 64-01 wave 1 + new invariant test appended)
    - tests/fixtures/stderr_contract.txt (brought from 64-01 wave 1)
  modified:
    - graphify/__main__.py (50+ stderr call sites migrated)
    - graphify/serve.py (3 sites: warning->info, serve:->info:, bare error:)
    - graphify/profile.py (2 sites: profile error: -> error: profile:)
    - graphify/naming.py (2 sites: repo identity warning -> info:)
    - graphify/vault_promote.py (1 site: migrate-legacy failed -> error:)
    - graphify/watch.py (2 sites: watch: triggered -> info:, failed -> error:)
    - graphify/seed.py (1 site: diagram-seeds -> info:)
    - graphify/dedup.py (1 site: Loading embedding model -> info:)
    - graphify/harness_export.py (3 sites: error: + hint: shape)
    - graphify/extract.py (1 site: Usage -> error: usage:)
    - tests/test_main_cli.py (1 assertion: Usage -> case-insensitive)
    - tests/test_profile.py (1 assertion: profile error: -> error: profile:)
    - tests/test_profile_composition.py (3 assertions: same)
    - tests/test_vault_cwd.py (2 assertions: auto-adopted -> info: auto-adopted)
    - tests/test_vault_parity.py (1 assertion: overrides global pin -> info: overrides)
decisions:
  - "warning: prefix folded into info: per D-04 (only 3 allowed prefixes: error/info/hint)"
  - "namespace prefixes like serve:, watch:, migrate-legacy: preserved as part of message body after compliant error:/info: prefix"
  - "test_migration.py::test_preview_expands_risky_action_rows is a pre-existing failure unrelated to this plan"
metrics:
  duration: ~35 minutes
  completed: 2026-05-06T18:08:00Z
  tasks_completed: 2
  files_modified: 15
---

# Phase 64 Plan 02: AUDIT-02 stderr Outlier Sweep Summary

One-liner: Migrated all 60+ non-compliant `print(..., file=sys.stderr)` call sites across 10 graphify modules to `[graphify] (error|info): ` / `  hint: ` D-04 whitelist format; added grep-invariant test that fails CI on future regressions.

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 | Enumerate and migrate every non-compliant stderr call site | a0b6743 | __main__.py, serve.py, profile.py, naming.py, vault_promote.py, watch.py, seed.py, dedup.py, harness_export.py, extract.py, test_stderr_contract.py, fixtures/stderr_contract.txt |
| 2 (TDD) | Add grep-invariant test that fails CI on new outliers | 9f246a5 | tests/test_stderr_contract.py |
| Rule 1 fix | Update test assertions to match migrated prefix format | 922ba3b | 5 test files |

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Test assertions used old non-compliant prefix strings**
- **Found during:** Task 2 (pytest full suite run)
- **Issue:** 8 tests checked for `"[graphify] profile error:"`, `"[graphify] auto-adopted vault at"`, `"[graphify] command --vault"` — all migrated during Task 1
- **Fix:** Updated assertions to match new compliant prefixes
- **Files modified:** test_main_cli.py, test_profile.py, test_profile_composition.py, test_vault_cwd.py, test_vault_parity.py
- **Commit:** 922ba3b

**2. [Rule 3 - Missing dependency] test_stderr_contract.py + fixture not on main branch**
- **Found during:** Task 1 verification
- **Issue:** Plan 64-01 created these files in a worktree branch that was not merged into main; this worktree (agent-a100ebd1b4fe5039d) works on main directly
- **Fix:** Cherry-picked the file contents from worktree-agent-a5970374d2e6623c1 commits 18f1f8b and 48a6d6c using `git show`
- **Files added:** tests/test_stderr_contract.py, tests/fixtures/stderr_contract.txt
- **Commit:** a0b6743 (included in migration commit)

**3. [Out-of-scope] Pre-existing failure: test_migration.py::test_preview_expands_risky_action_rows**
- Confirmed pre-existing by git stash verification — unrelated to this plan's changes
- Logged to deferred-items; not fixed

### harness_export.py (extra file not in plan)
- **Reason:** Grep revealed non-compliant `"error: graph.json not found..."` + bare hint lines in `graphify/harness_export.py` — not listed in plan's `files_modified`
- **Action:** Rule 2 auto-fix — migrated to `[graphify] error:` + `  hint:` shape
- **Commit:** a0b6743

## Verification Results

- `grep -rEn 'print\([^)]*file=sys\.stderr' graphify/ --include='*.py' | grep -v output.py | grep -vE '\[graphify\] (error|info):|"  hint:'` → **0 lines**
- `pytest tests/test_stderr_contract.py -v` → **5 passed** (4 snapshot + 1 invariant)
- `pytest tests/ -q` → **2274 passed, 1 xfailed, 1 pre-existing failure** (test_migration.py::test_preview_expands_risky_action_rows — unrelated)

## Self-Check: PASSED

- tests/test_stderr_contract.py: FOUND
- tests/fixtures/stderr_contract.txt: FOUND
- commit a0b6743: FOUND
- commit 9f246a5: FOUND
- commit 922ba3b: FOUND
- Zero non-compliant prefixes confirmed by invariant test

## Known Stubs

None — all migrated sites are production stderr emitters, none are stubs.

## Threat Flags

None — pure source migration, no new external input surface introduced.
