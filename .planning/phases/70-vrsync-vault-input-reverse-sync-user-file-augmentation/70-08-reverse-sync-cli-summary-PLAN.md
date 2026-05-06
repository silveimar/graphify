---
phase: 70-vrsync-vault-input-reverse-sync-user-file-augmentation
plan: 08
type: tdd
wave: 1
depends_on: []
files_modified:
  - graphify/reverse_sync.py
  - tests/test_reverse_sync.py
autonomous: true
gap_closure: true
requirements: [VRSYNC-01]
must_haves:
  truths:
    - "Running `graphify reverse-sync` with copy/skip outcomes prints one line per non-skip outcome to stdout"
    - "Running `graphify reverse-sync` prints a final totals line summarizing all counters"
    - "Outcome lines are NOT emitted for kind='skip' (unchanged-file no-ops)"
  artifacts:
    - path: graphify/reverse_sync.py
      provides: "run_reverse_sync emits per-file + totals stdout summary"
      contains: "reverse-sync:"
    - path: tests/test_reverse_sync.py
      provides: "Regression tests for stdout summary (UAT Test 3 closure)"
      contains: "test_run_reverse_sync_emits"
  key_links:
    - from: "graphify/reverse_sync.py::run_reverse_sync"
      to: "stdout"
      via: "print() inside per-record loop and after loop completes"
      pattern: "print\\(.*reverse-sync"
---

<objective>
Close UAT Test 3 (severity: minor, VRSYNC-01): `graphify reverse-sync` currently
runs to completion but emits NOTHING on stdout when changes are applied. Add a
per-file outcome line and a final totals line so the operator can see what the
command did.

Purpose: Operator visibility — silent success is indistinguishable from a no-op.
Output: Modified `graphify/reverse_sync.py` plus regression tests.
</objective>

<execution_context>
@$HOME/.claude/get-shit-done/workflows/execute-plan.md
@$HOME/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@CLAUDE.md
@.planning/STATE.md
@.planning/ROADMAP.md
@.planning/phases/70-vrsync-vault-input-reverse-sync-user-file-augmentation/70-UAT.md
@.planning/phases/70-vrsync-vault-input-reverse-sync-user-file-augmentation/70-CONTEXT.md
@.planning/phases/70-vrsync-vault-input-reverse-sync-user-file-augmentation/70-03-reverse-sync-cmd-SUMMARY.md

<interfaces>
From graphify/reverse_sync.py — `run_reverse_sync(...)` already maintains a
`counters` dict with these exact keys:
  - copied
  - skipped_user
  - skipped_conflict
  - skipped_never_copy
  - vault_deleted
And the per-record loop has access to `outcome` (str) and `rec.rel_path` (str
relative path inside the vault). The function returns `result = dict(counters)`
plus `conflicts_skipped`, `failed`, `log_path`. DO NOT change the return shape.

Per-record outcomes that should emit a line (everything EXCEPT "skip" and "quit"):
  copied, skipped_user, skipped_conflict, skipped_never_copy, vault_deleted

Outcome "skip" (kind=="skip", unchanged file) MUST remain silent (D-14: not a
sync event).

Outcome "quit" breaks the loop and MUST NOT emit a per-file line.
</interfaces>
</context>

<tasks>

<task type="tdd" tdd="true">
  <name>Task 1 (RED): Add failing tests asserting stdout summary</name>
  <files>tests/test_reverse_sync.py</files>
  <read_first>
    - tests/test_reverse_sync.py (read entirety to follow existing fixture/mocking patterns — pytest tmp_path, capsys, profile dict construction)
    - graphify/reverse_sync.py (the run_reverse_sync function around lines 314–410 — counter keys, outcome strings, ChangeRecord shape)
    - .planning/phases/70-vrsync-vault-input-reverse-sync-user-file-augmentation/70-UAT.md (Test 3 section for the exact failing scenario)
  </read_first>
  <behavior>
    - Test A (`test_run_reverse_sync_emits_per_file_copied_line`): vault has one
      user-only file `People/Alice.md`, profile mode=always_copy, run
      `run_reverse_sync` and capture stdout via capsys; assert stdout contains
      the substring `[graphify] reverse-sync: copied People/Alice.md`.
    - Test B (`test_run_reverse_sync_emits_totals_line`): same scenario; assert
      stdout contains a totals line with substring
      `reverse-sync: totals copied=1 skipped_user=0 skipped_conflict=0 skipped_never_copy=0 vault_deleted=0`.
    - Test C (`test_run_reverse_sync_silent_on_unchanged`): vault and input both
      contain identical `People/Alice.md` (so compute_change_set yields kind=="skip"
      OR no record); run with mode=always_copy; assert stdout does NOT contain
      the substring `copied` (only the totals line is allowed, and that is
      always emitted; assert totals line shows `copied=0`).
    - Test D (`test_run_reverse_sync_emits_skipped_never_copy_line`): vault-only
      file with mode=never_copy; assert stdout contains
      `[graphify] reverse-sync: skipped_never_copy People/Alice.md`.
  </behavior>
  <action>
    Append four new tests to tests/test_reverse_sync.py, modeled after existing
    tests in that file (use tmp_path to build vault_dir + input_dir, write
    `.graphify/profile.yaml` or pass profile dict directly per existing
    convention, call `run_reverse_sync(vault_dir=..., input_dir_override=...,
    mode_override="always_copy")`, capture stdout with the `capsys` fixture).
    The substrings are exact and case-sensitive. Tests MUST fail at this point
    because run_reverse_sync emits nothing on success today.
  </action>
  <verify>
    <automated>pytest tests/test_reverse_sync.py::test_run_reverse_sync_emits_per_file_copied_line tests/test_reverse_sync.py::test_run_reverse_sync_emits_totals_line tests/test_reverse_sync.py::test_run_reverse_sync_silent_on_unchanged tests/test_reverse_sync.py::test_run_reverse_sync_emits_skipped_never_copy_line -x 2>&1 | grep -E "FAILED|failed"</automated>
  </verify>
  <acceptance_criteria>
    - `grep -c "def test_run_reverse_sync_emits_per_file_copied_line" tests/test_reverse_sync.py` returns 1
    - `grep -c "def test_run_reverse_sync_emits_totals_line" tests/test_reverse_sync.py` returns 1
    - `grep -c "def test_run_reverse_sync_silent_on_unchanged" tests/test_reverse_sync.py` returns 1
    - `grep -c "def test_run_reverse_sync_emits_skipped_never_copy_line" tests/test_reverse_sync.py` returns 1
    - All four tests FAIL when run (RED state confirmed)
  </acceptance_criteria>
  <done>Four new tests exist, all fail with assertion errors about missing stdout substrings. Commit: `test(70-08): add RED tests for reverse-sync stdout summary`</done>
</task>

<task type="tdd" tdd="true">
  <name>Task 2 (GREEN): Emit per-file + totals lines in run_reverse_sync</name>
  <files>graphify/reverse_sync.py</files>
  <read_first>
    - graphify/reverse_sync.py (the full run_reverse_sync function around lines 314–410, plus apply_change above it for the outcome string list)
  </read_first>
  <action>
    Inside the existing `for rec in changes:` loop in `run_reverse_sync` (after
    the `if outcome == "skip": continue` and `if outcome == "quit": break`
    guards, BEFORE the JSONL log append), add:

      if outcome in ("copied", "skipped_user", "skipped_conflict",
                     "skipped_never_copy", "vault_deleted"):
          print(f"[graphify] reverse-sync: {outcome} {rec.rel_path}")

    After the loop completes (right before `result = dict(counters)`), add the
    totals line:

      print(
          f"[graphify] reverse-sync: totals "
          f"copied={counters['copied']} "
          f"skipped_user={counters['skipped_user']} "
          f"skipped_conflict={counters['skipped_conflict']} "
          f"skipped_never_copy={counters['skipped_never_copy']} "
          f"vault_deleted={counters['vault_deleted']}"
      )

    Use plain `print()` (stdout, no `file=sys.stderr`). Do NOT alter return
    shape, exit codes, JSONL logging, or any other behavior. Do NOT add a
    `--quiet` flag (out of scope; no precedent in cmd_reverse_sync arg parser).
  </action>
  <verify>
    <automated>pytest tests/test_reverse_sync.py -x -q</automated>
  </verify>
  <acceptance_criteria>
    - `grep -c 'reverse-sync: totals copied=' graphify/reverse_sync.py` returns 1
    - `grep -E 'print\(f"\[graphify\] reverse-sync: \{outcome\} \{rec.rel_path\}"\)' graphify/reverse_sync.py` returns a match
    - All four Task 1 tests now PASS
    - Full `pytest tests/test_reverse_sync.py -q` passes (no regressions)
    - Full `pytest tests/ -q` passes
  </acceptance_criteria>
  <done>All reverse-sync tests pass; full test suite green. Commit: `feat(70-08): emit per-file + totals stdout summary in reverse-sync`</done>
</task>

</tasks>

<verification>
- All tests in tests/test_reverse_sync.py pass
- Full test suite (`pytest tests/ -q`) passes
- Manual smoke: `graphify reverse-sync --vault /tmp/uat-vault --input /tmp/uat-input --mode always_copy` prints at least one `[graphify] reverse-sync: ...` line and a totals line on stdout
</verification>

<success_criteria>
UAT Test 3 (VRSYNC-01) gap closed:
- Per-file outcome lines visible on stdout for copied / skipped_user / skipped_conflict / skipped_never_copy / vault_deleted
- Totals line always emitted at end of run
- Unchanged files (kind=="skip") remain silent (D-14)
- No change to exit codes or JSONL log format
</success_criteria>

<output>
Create `.planning/phases/70-vrsync-vault-input-reverse-sync-user-file-augmentation/70-08-reverse-sync-cli-summary-SUMMARY.md`
</output>
