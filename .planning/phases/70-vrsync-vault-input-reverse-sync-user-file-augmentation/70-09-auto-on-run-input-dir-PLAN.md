---
phase: 70-vrsync-vault-input-reverse-sync-user-file-augmentation
plan: 09
type: tdd
wave: 1
depends_on: []
files_modified:
  - graphify/__main__.py
  - tests/test_auto_on_run.py
autonomous: true
gap_closure: true
requirements: [VRSYNC-01, VPROF-03]
must_haves:
  truths:
    - "When `auto_on_run: true` and the user runs `graphify run`, vault user_only_folders files are copied into the user's pre-D-07 input directory (not the D-07-rewritten CWD)"
    - "D-07 (vault auto-adopt forces pipeline corpus to CWD) still applies to the pipeline `target` — only the auto_on_run hook receives the unrewritten path"
    - "UAT Test 5 scenario passes: vault-only Bob.md, auto_on_run=true, mode=always_copy, cwd=parent of vault — Bob.md ends up in the user's --input path"
  artifacts:
    - path: graphify/__main__.py
      provides: "auto_on_run hook in `run` cmd uses raw_target (pre-D-07) for input_dir_override"
      contains: "input_dir_override=Path(raw_target)"
    - path: tests/test_auto_on_run.py
      provides: "Regression tests for UAT Test 5 (input_dir_override binding) + unit test on raw_target wiring"
      contains: "test_auto_on_run_uses_raw_target"
  key_links:
    - from: "graphify/__main__.py (run cmd, ~line 3010)"
      to: "graphify.reverse_sync.run_reverse_sync"
      via: "input_dir_override=Path(raw_target).resolve() (NOT target)"
      pattern: "input_dir_override=Path\\(raw_target\\)"
---

<objective>
Close UAT Test 5 (severity: major, VRSYNC-01 + VPROF-03): the `auto_on_run`
hook inside `graphify run` currently passes the D-07-rewritten `target`
(forced to CWD) as `input_dir_override` to `run_reverse_sync`. As a result,
when the user runs from outside their input corpus directory, vault-only files
are compared against the wrong directory and never copied.

Fix: capture `raw_target` (the user's pre-D-07 input path, already present at
line 2976) and pass that into the auto_on_run hook. D-07 must continue to
govern the pipeline `target`; only the reverse-sync hook needs the unrewritten
path.

Purpose: Restore the documented `auto_on_run` user-file augmentation behavior
(VPROF-03 augmentation half).
Output: One-line fix in `graphify/__main__.py` plus regression tests.
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
@.planning/phases/70-vrsync-vault-input-reverse-sync-user-file-augmentation/70-05-auto-on-run-SUMMARY.md

<interfaces>
From graphify/__main__.py around line 2976:
  raw_target = rest[0] if rest else "."
  ...
  if resolved.vault_detected and resolved.source in _PROFILE_DRIVEN_SOURCES:
      target = Path.cwd().resolve()           # D-07 rewrite
  else:
      target = Path(raw_target).resolve()

Around line 3001-3027 (the auto_on_run hook in `run` cmd) currently passes:
  _run_reverse_sync(
      resolved.vault_path,
      input_dir_override=target,              # BUG — uses D-07'd path
      auto_on_run=True,
  )

The second hook site (line ~3412 inside `update-vault` cmd) is NOT affected by
this bug — it uses `Path(opts.input)` directly, bypassing D-07 entirely. Do
NOT modify that site.

`run_reverse_sync` signature (graphify/reverse_sync.py:314):
  def run_reverse_sync(
      vault_dir: Path,
      *,
      input_dir_override: Path | None = None,
      mode_override: str | None = None,
      yes: bool = False,
      auto_on_run: bool = False,
  ) -> dict
</interfaces>
</context>

<tasks>

<task type="tdd" tdd="true">
  <name>Task 1 (RED): Add failing tests for raw_target binding + UAT-5 scenario</name>
  <files>tests/test_auto_on_run.py</files>
  <read_first>
    - .planning/phases/70-vrsync-vault-input-reverse-sync-user-file-augmentation/70-UAT.md (Test 5 section: exact failing scenario, vault layout, expected post-state)
    - graphify/__main__.py (the `run` cmd block lines ~2960–3030 — raw_target capture, D-07 rewrite, auto_on_run hook)
    - graphify/reverse_sync.py (run_reverse_sync signature only)
    - tests/test_reverse_sync.py (existing fixture patterns: tmp_path vault + input dir, profile.yaml writing)
  </read_first>
  <behavior>
    - Test A (`test_auto_on_run_uses_raw_target_for_input_dir_override`,
      unit-level): monkeypatch `graphify.reverse_sync.run_reverse_sync` to
      capture call kwargs into a list. Build a temp vault with
      `.graphify/profile.yaml` containing `reverse_sync: {auto_on_run: true,
      mode: always_copy}` and `user_only_folders: [People]`. Invoke the `run`
      command (via `_main` / argv) with cwd=vault_path (D-07 will rewrite
      target to CWD) and an explicit input dir argument that is DIFFERENT from
      cwd. Assert that the captured `input_dir_override` kwarg equals the
      user-supplied input path (raw_target), NOT the vault CWD.
    - Test B (`test_auto_on_run_copies_vault_only_file_to_user_input_dir`,
      integration-level UAT-5 reproduction): build temp vault containing
      `People/Bob.md` (vault-only — input dir does not have it), profile with
      `auto_on_run: true`, `mode: always_copy`, `user_only_folders: [People]`.
      cwd = parent of vault. Invoke `graphify run <input_dir>` (input_dir is
      sibling of vault). After invocation assert
      `(input_dir / "People" / "Bob.md").exists()` is True and its bytes equal
      the vault file's bytes.
  </behavior>
  <action>
    Create new file tests/test_auto_on_run.py. Use pytest tmp_path, monkeypatch,
    capsys. Follow existing test patterns from tests/test_reverse_sync.py for
    profile.yaml construction. For invoking `graphify run`, drive
    `graphify.__main__._main` (or the equivalent entry point already used in
    other CLI tests) with patched `sys.argv`. The pipeline body of `run` may
    fail later (no real corpus) — that's fine. Use try/except or monkeypatch
    pipeline calls to no-ops so the test only exercises the hook. Both tests
    MUST fail at this point: Test A because `input_dir_override` is the D-07'd
    target, Test B because Bob.md never lands in input_dir.
  </action>
  <verify>
    <automated>pytest tests/test_auto_on_run.py -x 2>&1 | grep -E "FAILED|failed"</automated>
  </verify>
  <acceptance_criteria>
    - `test -f tests/test_auto_on_run.py && echo OK` prints OK
    - `grep -c "def test_auto_on_run_uses_raw_target_for_input_dir_override" tests/test_auto_on_run.py` returns 1
    - `grep -c "def test_auto_on_run_copies_vault_only_file_to_user_input_dir" tests/test_auto_on_run.py` returns 1
    - Both tests FAIL when run (RED state confirmed)
  </acceptance_criteria>
  <done>tests/test_auto_on_run.py exists with two failing tests. Commit: `test(70-09): add RED tests for auto_on_run input_dir_override raw_target binding`</done>
</task>

<task type="tdd" tdd="true">
  <name>Task 2 (GREEN): Pass raw_target (not D-07'd target) to auto_on_run hook</name>
  <files>graphify/__main__.py</files>
  <read_first>
    - graphify/__main__.py (lines ~2970–3030 — the exact block being edited)
  </read_first>
  <action>
    In graphify/__main__.py, locate the `run` cmd's auto_on_run hook block
    (approximately lines 3001–3027 — the one inside the `if cmd == "run":`
    branch, NOT the one near line 3412 inside update-vault). Change ONLY this
    line:

      input_dir_override=target,

    to:

      input_dir_override=Path(raw_target).resolve(),

    `raw_target` is already in scope (set at line 2976: `raw_target = rest[0]
    if rest else "."`). Do NOT modify the D-07 rewrite of `target` itself —
    the pipeline corpus must continue to use the rewritten `target`. Do NOT
    touch the second hook site near line 3412 (update-vault cmd) — it already
    uses `Path(opts.input)` and is correct.
  </action>
  <verify>
    <automated>pytest tests/test_auto_on_run.py tests/test_reverse_sync.py -q</automated>
  </verify>
  <acceptance_criteria>
    - `grep -n "input_dir_override=Path(raw_target).resolve()" graphify/__main__.py` returns exactly 1 match
    - `grep -n "input_dir_override=target," graphify/__main__.py` returns 0 matches (the buggy line is gone)
    - `grep -n "input_dir_override=Path(opts.input)" graphify/__main__.py` still returns 1 match (the update-vault site is untouched)
    - Both Task 1 tests now PASS
    - `pytest tests/ -q` passes (no regressions)
  </acceptance_criteria>
  <done>auto_on_run hook in `run` cmd uses raw_target; UAT-5 scenario reproduces fixed; full test suite green. Commit: `fix(70-09): auto_on_run hook uses raw_target (pre-D-07) for input_dir_override`</done>
</task>

</tasks>

<verification>
- New tests pass; existing tests unaffected
- `grep` invariants in acceptance_criteria all hold
- Manual UAT-5 smoke: vault with user_only_folders=[People] containing Bob.md,
  separate input dir, `auto_on_run: true`, `mode: always_copy`, run
  `graphify run <input_dir>` with cwd != input_dir → Bob.md appears in
  `<input_dir>/People/Bob.md`
</verification>

<success_criteria>
UAT Test 5 (VRSYNC-01 + VPROF-03 augmentation half) gap closed:
- auto_on_run hook in `graphify run` reverse-syncs into the user's actual
  input directory, not the D-07-rewritten CWD
- D-07 vault auto-adopt semantics for the pipeline corpus (`target`) unchanged
- update-vault auto_on_run hook (separate site) unchanged
</success_criteria>

<output>
Create `.planning/phases/70-vrsync-vault-input-reverse-sync-user-file-augmentation/70-09-auto-on-run-input-dir-SUMMARY.md`
</output>
