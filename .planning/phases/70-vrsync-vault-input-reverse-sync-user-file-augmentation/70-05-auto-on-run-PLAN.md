---
phase: 70
plan: 05
type: execute
wave: 3
depends_on: [70-03, 70-04]
files_modified:
  - graphify/__main__.py
  - tests/test_auto_on_run.py
autonomous: true
requirements: [VRSYNC-01]
must_haves:
  truths:
    - "profile.reverse_sync.auto_on_run=true triggers reverse-sync at start of `graphify run` (Success Criterion 4)"
    - "Same hook runs at start of `graphify update-vault` (Success Criterion 4)"
    - "auto_on_run=false (default) leaves both commands untouched (Success Criterion 4)"
    - "Reverse-sync errors during auto_on_run warn-and-continue; never block parent command (D-11)"
    - "Stderr summary printed when conflicts skipped: '[graphify] reverse-sync: N conflicts skipped — run graphify reverse-sync to resolve' (D-11)"
  artifacts:
    - path: "graphify/__main__.py"
      provides: "auto_on_run hook calls before run_corpus and update_vault"
      contains: "auto_on_run"
    - path: "tests/test_auto_on_run.py"
      provides: "Integration tests for hook firing + warn-and-continue"
  key_links:
    - from: "graphify/__main__.py:2936 (cmd=='run')"
      to: "graphify.reverse_sync.run_reverse_sync"
      via: "early-stage call gated on profile.reverse_sync.auto_on_run"
      pattern: "auto_on_run"
    - from: "graphify/__main__.py:3283 (cmd=='update-vault')"
      to: "graphify.reverse_sync.run_reverse_sync"
      via: "early-stage call gated on profile.reverse_sync.auto_on_run"
      pattern: "auto_on_run"
---

<objective>
Wire the auto_on_run hook into the two parent commands (`graphify run` and `graphify update-vault`). Hook fires after profile load, before pipeline starts. Failures or skipped conflicts warn-and-continue per D-11 — never block parent command.

This plan is `type: execute` because the work is glue/wiring with no new business logic; mode dispatch and JSONL logic already TDD'd in Plans 03/04.
</objective>

<execution_context>
@$HOME/.claude/get-shit-done/workflows/execute-plan.md
@$HOME/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/phases/70-vrsync-vault-input-reverse-sync-user-file-augmentation/70-CONTEXT.md
@.planning/phases/70-vrsync-vault-input-reverse-sync-user-file-augmentation/70-RESEARCH.md
@graphify/__main__.py

<interfaces>
- Hook insertion points (RESEARCH Pattern 2): `__main__.py:2936` (cmd=="run") and `:3283` (cmd=="update-vault"). Insert AFTER profile load resolves and BEFORE the main pipeline call.
- run_reverse_sync(... , auto_on_run=True) — already accepts the flag (Plan 03).
- Pitfall 5: no recursion possible because reverse_sync does not invoke run/update-vault.
</interfaces>
</context>

<tasks>

<task type="auto" tdd="true">
  <name>Task 1: Write integration tests for auto_on_run hook</name>
  <files>tests/test_auto_on_run.py</files>
  <read_first>
    - .planning/phases/70-vrsync-vault-input-reverse-sync-user-file-augmentation/70-CONTEXT.md (D-11)
    - .planning/phases/70-vrsync-vault-input-reverse-sync-user-file-augmentation/70-RESEARCH.md (Pattern 2, Pitfall 5)
    - graphify/__main__.py:2936-3300 (cmd dispatch blocks)
    - tests/test_commands.py or tests/test_main.py (existing pytest patterns for invoking main)
  </read_first>
  <behavior>
    - test_run_with_auto_on_run_true_fires_hook: profile auto_on_run=true; new vault file present; invoke `graphify run` via main(); reverse-sync log shows the file copied; run pipeline still proceeds (mock or skip the heavy extraction)
    - test_run_with_auto_on_run_false_skips_hook: auto_on_run=false (default); no log file created; pipeline proceeds normally
    - test_update_vault_with_auto_on_run_true_fires_hook: same as above but for cmd=="update-vault"
    - test_auto_on_run_failure_warn_continue: monkeypatch run_reverse_sync to raise; invoke `graphify run`; assert no exception bubbles out; stderr captures `[graphify] reverse-sync: skipped due to error`; parent command exits 0 (D-11)
    - test_auto_on_run_conflicts_skipped_summary: run_reverse_sync returns conflicts_skipped=3; stderr matches `reverse-sync: 3 conflicts skipped — run 'graphify reverse-sync' to resolve` (D-11 wording)
    - test_no_recursion: log file shows exactly N entries for N changes (not 2N) — proves reverse-sync is not re-invoking run (Pitfall 5 guard)
    Use `monkeypatch.setattr("graphify.run.run_corpus", lambda *a, **kw: None)` (or equivalent stub) to avoid heavy pipeline invocation. Use `monkeypatch.setattr("sys.argv", ["graphify", "run", "--vault", str(vd)])` and `graphify.__main__.main()` direct invocation. Capture stderr via `capsys`.
  </behavior>
  <action>
    Create tests/test_auto_on_run.py with the 6 tests above. Build minimal vault+input dual-tree fixtures. For run_corpus stub, search graphify/__main__.py for the function called when cmd=="run" (likely `run_corpus` from `graphify.run`) and stub it. Run pytest — tests must FAIL until hook is wired in Task 2.
  </action>
  <verify>
    <automated>pytest tests/test_auto_on_run.py -q 2>&1 | grep -E "(error|failed)"</automated>
  </verify>
  <done>6 integration tests added and failing.</done>
</task>

<task type="auto">
  <name>Task 2: Insert auto_on_run hook in `run` and `update-vault` dispatch</name>
  <files>graphify/__main__.py</files>
  <read_first>
    - .planning/phases/70-vrsync-vault-input-reverse-sync-user-file-augmentation/70-RESEARCH.md (Pattern 2 verbatim pseudocode)
    - graphify/__main__.py:2936-3000 (cmd=="run" block) and :3283-3350 (cmd=="update-vault" block)
    - tests/test_auto_on_run.py (just written)
  </read_first>
  <action>
    For BOTH cmd=="run" (~line 2936) and cmd=="update-vault" (~line 3283) blocks:
    1. Locate the line where `profile = load_profile(...)` (or equivalent) resolves the active profile.
    2. Immediately after, BEFORE the main pipeline call (`run_corpus(...)` / `update_vault(...)`), insert:
    ```python
    if profile.get("reverse_sync", {}).get("auto_on_run", False):
        try:
            from graphify.reverse_sync import run_reverse_sync
            _rs_result = run_reverse_sync(vault_dir, auto_on_run=True)
            _rs_skipped = _rs_result.get("conflicts_skipped", 0)
            if _rs_skipped:
                print(
                    f"[graphify] reverse-sync: {_rs_skipped} conflicts skipped — "
                    f"run 'graphify reverse-sync' to resolve",
                    file=sys.stderr,
                )
        except Exception as exc:  # D-11: warn-and-continue
            print(f"[graphify] reverse-sync: skipped due to error: {exc}", file=sys.stderr)
    ```
    3. Confirm the variable name matches the local profile/vault_dir variables in each block (might be `vault_dir`, `_vault_dir`, or `cwd`); adjust accordingly.
    4. NO other changes in those blocks — pipeline call sites remain identical so the existing CI test_commands.py tests stay green.
    5. Make sure the import is local (`from graphify.reverse_sync import run_reverse_sync` inside the if-block) to avoid loading reverse_sync at module init (matches lazy-load convention in __init__.py).
  </action>
  <verify>
    <automated>pytest tests/test_auto_on_run.py tests/test_commands.py tests/test_reverse_sync.py -q</automated>
  </verify>
  <done>All 6 auto_on_run tests pass; existing test_commands.py untouched/passing; grep -c "auto_on_run" graphify/__main__.py >= 2 (one per command block).</done>
</task>

</tasks>

<verification>
- `pytest tests/test_auto_on_run.py -q` green
- `pytest tests/ -q` no regressions
- grep -n "reverse-sync: .* conflicts skipped" graphify/__main__.py shows D-11 message in both insertion sites (or once if shared helper extracted)
</verification>

<success_criteria>
- Success Criterion 4 delivered: hook fires when auto_on_run=true; silent when false
- D-11 warn-and-continue: errors don't crash parent
- Pitfall 5 no-recursion invariant verified by test_no_recursion
</success_criteria>

<output>
Create `.planning/phases/70-vrsync-vault-input-reverse-sync-user-file-augmentation/70-05-auto-on-run-SUMMARY.md` after completion.
</output>
