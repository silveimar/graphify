---
phase: 23
plan: 01
subsystem: dedup
tags: [dedup, bugfix, source-file-shape, edge-merge, hardening, issue-4]
requirements-completed: [DEDUP-01, DEDUP-02, DEDUP-03]
dependency-graph:
  requires:
    - graphify.analyze._iter_sources (canonical str|list[str]|None -> list[str] flattener)
    - graphify.dedup._merge_extraction (edges-merge loop)
  provides:
    - dedup.py edge merge accepting list[str] source_file without TypeError
    - sorted-unique union shape contract preserved verbatim per DEDUP-02
  affects:
    - graphify.dedup (only the edges-merge block at former line 493 + one new import)
tech-stack:
  added: []
  patterns:
    - reuse _iter_sources (D-01) — single canonical source_file flattener
    - mirror v1.3 IN-06 node-path set fold (dedup.py:445-459) for edges path
key-files:
  created:
    - .planning/phases/23-dedup-source-file-list-handling-fix/23-01-SUMMARY.md
    - .planning/phases/23-dedup-source-file-list-handling-fix/deferred-items.md
  modified:
    - graphify/dedup.py (+11/-1: one import + 6-line set-fold replacement)
    - tests/test_dedup.py (+65/-0: two regression tests appended)
decisions:
  - D-01 honored: reused graphify.analyze._iter_sources, no new _sf_flatten helper
  - D-02 honored: node-merge block at dedup.py:445-459 untouched (byte-identical)
  - D-03 honored: replaced set comprehension with flatten-then-fold via _iter_sources
  - D-04 honored: shape contract preserved (sorted list >=2, scalar ==1, "" for 0)
  - D-05 honored: two tests added — DEDUP-03 spec case + idempotency facet
  - D-06 honored: no export-consumer smoke test added
  - D-07 honored: no mixed scalar+list fixture beyond Test 1's implicit mix
metrics:
  duration: ~12 minutes (3 commits)
  completed: 2026-04-27
---

# Phase 23 Plan 01: Dedup `source_file` List-Handling Fix Summary

Routed `_merge_extraction`'s edges-path `source_file` set fold through `graphify.analyze._iter_sources` so list-shaped inputs (the natural output of a prior dedup pass — Issue #4) no longer crash with `TypeError: unhashable type: 'list'`.

## Tasks Executed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 | Add failing regression tests (RED) | 8b7f4dc | tests/test_dedup.py |
| 2 | Patch dedup.py edge-merge via _iter_sources (GREEN) | 8c67e1f | graphify/dedup.py |
| 3 | Full-suite regression sweep + commit (this SUMMARY commit) | (pending) | (docs only) |

## Test Results

| Stage | Command | Result |
|-------|---------|--------|
| Pre-fix (Task 1) | `pytest tests/test_dedup.py -q` | 1 failed (`test_cross_type_merges_list_shaped_source_file`), 23 passed |
| Pre-fix bug evidence | — | `TypeError: unhashable type: 'list'` at `dedup.py:493` (verbatim) |
| Post-fix (Task 2) | `pytest tests/test_dedup.py -q` | 24 passed, 0 failed |
| Phase gate (Task 3) | `pytest tests/ -q` | 1576 passed, 1 xfailed, 2 pre-existing failures unrelated to phase 23 (see Deferred Issues) |

### Notes on RED Step

- `test_cross_type_merges_list_shaped_source_file` failed RED with the exact `TypeError` (bug reproduced).
- `test_dedup_is_idempotent_on_source_file_shape` did NOT fail RED — investigated and confirmed the test fixture's pass2 produces a single-edge group (`len(group) == 1` short-circuit at `dedup.py:483`), so the buggy comprehension is never reached on the second pass for this fixture. The test still validates the idempotency contract correctly (no crash, shape-preserved). This is acceptable per the plan's stated intent (locks the shape contract) and is documented for transparency.

## Code Changes

### `graphify/dedup.py` (+11/-1)

1. **Import added** (line 35, alphabetical within local imports block):
   ```python
   from graphify.analyze import _iter_sources
   ```

2. **Edge-merge fix** (former line 493): replaced the unhashable-list-prone set comprehension with a flatten-then-fold loop, plus an explicit `else: ""` branch mirroring the node-path contract at line 459:
   ```python
   sf_set: set[str] = set()
   for e in group:
       sf_set.update(_iter_sources(e.get("source_file")))
   if len(sf_set) > 1:
       merged["source_file"] = sorted(sf_set)
   elif sf_set:
       merged["source_file"] = next(iter(sf_set))
   else:
       merged["source_file"] = ""
   ```

### `tests/test_dedup.py` (+65/-0)

- `test_cross_type_merges_list_shaped_source_file` — DEDUP-03 spec case
- `test_dedup_is_idempotent_on_source_file_shape` — idempotency facet

## Decision Compliance (D-01..D-07)

All seven locked decisions from `23-CONTEXT.md` were honored:

- **D-01**: Reused `_iter_sources` — no new `_sf_flatten` helper introduced.
- **D-02**: Node-merge block at `dedup.py:445-459` is byte-identical to pre-patch (verified via `grep` and visual diff).
- **D-03**: Patch is exactly the flatten-then-set construction prescribed.
- **D-04**: Output shape contract preserved verbatim (sorted list ≥2 / scalar ==1 / `""` ==0).
- **D-05**: Exactly two tests added; both use `_forced_merge_encoder` and `cross_type=True, embed_threshold=0.85`.
- **D-06**: No export-consumer smoke test added.
- **D-07**: No mixed scalar+list fixture beyond Test 1's implicit mix.

## Threat Mitigations

- **T-23-01 (Denial of Service via crafted list-shaped `source_file`):** mitigated. `_iter_sources` returns `[]` for `None`/empty/unknown types — fail-soft.
- **T-23-02 (Tampering of merged `source_file` reaching exporters):** unchanged (already mitigated outside this phase via `_fmt_source_file` → `sanitize_label`).

## Deviations from Plan

**Auto-fixed:**

1. **[Rule 3 — Blocking issue] Worktree branch base reset.** The worktree was initially created from an old `v3` ancestor commit (3711115) which predated the existence of `graphify/dedup.py` and the phase 23 plan files. Reset the worktree branch to `main` (HEAD: `a517c8d`) so the plan files and target source files were available. No source code change — pure environment fix.

Otherwise the plan executed exactly as written.

## Deferred Issues

Two test failures pre-existed on `main` (verified via `git stash` round-trip — both failed identically before any dedup change). Logged in `.planning/phases/23-dedup-source-file-list-handling-fix/deferred-items.md`:

- `tests/test_detect.py::test_detect_skips_dotfiles`
- `tests/test_extract.py::test_collect_files_from_dir`

These are out of scope per SCOPE BOUNDARY rule and should be triaged separately.

## Self-Check: PASSED

Verified post-write:

- File exists: `graphify/dedup.py` — FOUND
- File exists: `tests/test_dedup.py` — FOUND
- File exists: `.planning/phases/23-dedup-source-file-list-handling-fix/23-01-SUMMARY.md` — (this file, will exist after Write)
- Commit 8b7f4dc — FOUND (test add, RED)
- Commit 8c67e1f — FOUND (dedup.py fix, GREEN)
- Bug comprehension absent: `grep -nF '{e["source_file"] for e in group' graphify/dedup.py` — 0 matches
- New import present: `grep -n "from graphify.analyze import _iter_sources" graphify/dedup.py` — 1 match
- Two new tests present in `tests/test_dedup.py` — both grep matches
- Diff scope: exactly 2 files changed across HEAD~2..HEAD (graphify/dedup.py, tests/test_dedup.py)

## TDD Gate Compliance

- RED gate: `test(23-01): ...` commit 8b7f4dc — present
- GREEN gate: `fix(23-01): ...` commit 8c67e1f — present
- REFACTOR gate: not needed (patch was already minimal)
