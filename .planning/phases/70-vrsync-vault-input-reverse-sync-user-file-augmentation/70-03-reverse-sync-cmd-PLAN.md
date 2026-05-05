---
phase: 70
plan: 03
type: tdd
wave: 2
depends_on: [70-02]
files_modified:
  - graphify/reverse_sync.py
  - graphify/__main__.py
  - tests/test_reverse_sync.py
autonomous: true
requirements: [VRSYNC-01]
must_haves:
  truths:
    - "always_ask mode prompts Y/n/d/A/Q per file (D-01, D-02)"
    - "always_copy mirrors without prompting (Success Criterion 3)"
    - "never_copy logs only and never writes (Success Criterion 3)"
    - "--yes overrides always_ask only; never_copy is unaffected (D-12)"
    - "Non-TTY under always_ask skips conflicts as skipped_conflict (D-13)"
    - "graphify reverse-sync subcommand is registered in CLI dispatch"
  artifacts:
    - path: "graphify/reverse_sync.py"
      provides: "run_reverse_sync(), prompt_per_file(), apply_change()"
      exports: ["run_reverse_sync"]
    - path: "graphify/__main__.py"
      provides: "elif cmd == 'reverse-sync' subcommand block"
      contains: "reverse-sync"
  key_links:
    - from: "graphify/__main__.py"
      to: "graphify/reverse_sync.py"
      via: "from graphify.reverse_sync import run_reverse_sync"
      pattern: "run_reverse_sync"
    - from: "graphify/reverse_sync.py"
      to: "sys.stdin.isatty"
      via: "TTY gate before input()"
      pattern: "isatty"
---

<objective>
Wire mode dispatch (always_ask / always_copy / never_copy), the Y/n/d/A/Q prompt with TTY gating, the file-copy step (atomic + path-confined), and the `graphify reverse-sync --vault --input --mode --yes` CLI subcommand. JSONL logging is wired in Plan 04.
</objective>

<execution_context>
@$HOME/.claude/get-shit-done/workflows/execute-plan.md
@$HOME/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/phases/70-vrsync-vault-input-reverse-sync-user-file-augmentation/70-CONTEXT.md
@.planning/phases/70-vrsync-vault-input-reverse-sync-user-file-augmentation/70-RESEARCH.md
@.planning/phases/70-vrsync-vault-input-reverse-sync-user-file-augmentation/70-02-reverse-sync-detect-PLAN.md
@graphify/reverse_sync.py
@graphify/__main__.py

<interfaces>
- ChangeRecord from Plan 02 — already typed.
- Modes (D-01..D-03, D-12, D-13): "always_ask" (default) | "always_copy" | "never_copy".
- Prompt key set: Y/n/d/A/Q. `[d]` re-prompts (D-02). `[A]` sets all-yes flag for the rest of the run. `[Q]` aborts cleanly.
- CLI flags: `--vault PATH` (default cwd), `--input PATH` (override profile.input_path), `--mode {always_ask,always_copy,never_copy}` (override profile.reverse_sync.mode), `--yes` (override always_ask only — D-12).
- Result dict: `{"copied": int, "skipped_user": int, "skipped_conflict": int, "skipped_never_copy": int, "vault_deleted": int, "failed": bool, "conflicts_skipped": int}`.
</interfaces>
</context>

<tasks>

<task type="tdd" tdd="true">
  <name>Task 1 (RED): Tests for mode dispatch + prompt + CLI registration</name>
  <files>tests/test_reverse_sync.py</files>
  <read_first>
    - .planning/phases/70-vrsync-vault-input-reverse-sync-user-file-augmentation/70-CONTEXT.md (D-01..D-03, D-12, D-13)
    - .planning/phases/70-vrsync-vault-input-reverse-sync-user-file-augmentation/70-RESEARCH.md (Pattern 1 CLI block, prompt code example, Pitfall 6)
    - graphify/__main__.py (lines 3296-3360 — Phase 69-04 --migrate-legacy precedent)
    - graphify/reverse_sync.py (Plan 02 output)
  </read_first>
  <behavior>
    - test_mode_always_copy_writes_without_prompt: mock input() to raise (proves not called); files copied; result["copied"] == N
    - test_mode_never_copy_logs_only: target files NOT created; result["skipped_never_copy"] == N (D-12 confirmation: --yes does not change this)
    - test_mode_always_ask_yes_response: monkeypatch input → "y"; file copied
    - test_mode_always_ask_no_response: input → "n"; file NOT copied; result["skipped_user"] == 1
    - test_prompt_diff_then_yes: input → ["d", "y"] sequence; diff written to stdout; file then copied (D-02 re-prompt)
    - test_prompt_all_response: input → "A"; subsequent files auto-yes without further input() calls
    - test_prompt_quit_response: input → "Q" mid-run; remaining files untouched; result["failed"] == False (clean abort)
    - test_yes_flag_overrides_always_ask: profile mode=always_ask, yes=True, input mocked to raise → still copies (proves input not called)
    - test_yes_does_NOT_override_never_copy: profile mode=never_copy, yes=True → still no writes (D-12)
    - test_non_tty_skips_conflicts: monkeypatch sys.stdin.isatty=False; mode=always_ask → result["skipped_conflict"] == N; no writes (D-13)
    - test_atomic_copy: copy uses .tmp + os.replace; verify by checking inode/mtime
    - test_path_confinement: vault file with rel_path "../escape.md" rejected with stderr warning
    - test_cli_subcommand_dispatch: invoke graphify/__main__.py main with argv=["graphify","reverse-sync","--vault",str(vd),"--mode","always_copy"]; subprocess returns 0; files copied
  </behavior>
  <action>
    Append 13 test functions to tests/test_reverse_sync.py. Use `monkeypatch.setattr("builtins.input", iter(["y","n",...]).__next__)` for prompt scripting. Use `monkeypatch.setattr("sys.stdin.isatty", lambda: False)` for D-13. For CLI dispatch test, invoke `graphify.__main__.main()` directly with `monkeypatch.setattr("sys.argv", [...])` and capture via capsys. Run pytest — new tests must FAIL.
  </action>
  <verify>
    <automated>pytest tests/test_reverse_sync.py -q -k 'mode or prompt or yes or tty or cli or atomic'</automated>
  </verify>
  <done>13 new tests added; all fail (NameError run_reverse_sync, or AttributeError, or argparse SystemExit).</done>
</task>

<task type="tdd" tdd="true">
  <name>Task 2 (GREEN): Implement run_reverse_sync + prompt_per_file + apply_change</name>
  <files>graphify/reverse_sync.py</files>
  <read_first>
    - tests/test_reverse_sync.py (just extended)
    - .planning/phases/70-vrsync-vault-input-reverse-sync-user-file-augmentation/70-RESEARCH.md (Code Examples section: prompt_per_file, diff_summary)
    - graphify/profile.py (load_profile signature)
  </read_first>
  <action>
    Extend graphify/reverse_sync.py with:
    1. `def _diff_summary(a: bytes, b: bytes) -> str` — verbatim from RESEARCH Code Examples (D-03 stats string).
    2. `def prompt_per_file(rel: str, vault_text: str, input_text: str | None) -> str` — returns "yes"/"no"/"all"/"quit"/"skip". Implementation per RESEARCH Code Examples: TTY-gate via `sys.stdin.isatty() and sys.stdout.isatty()`; non-TTY → "skip" (D-13). Loop input() with `[Y/n/d/A/Q]`; `[d]` → write `difflib.unified_diff(input_text, vault_text)` to stdout, then `continue` (D-02); empty/y/yes → "yes"; n/no → "no"; a/all → "all"; q/quit → "quit"; unknown → re-prompt.
    3. `def _atomic_copy(src: Path, dst: Path) -> None` — `dst.parent.mkdir(parents=True, exist_ok=True); tmp = dst.with_suffix(dst.suffix+".tmp"); tmp.write_bytes(src.read_bytes()); os.replace(tmp, dst)`.
    4. `def _validate_input_path(input_dir: Path, target: Path) -> bool` — resolve both; require `target.resolve()` to be inside `input_dir.resolve()`; mirror merge.py:629 `_validate_target` pattern.
    5. `def run_reverse_sync(vault_dir: Path, *, input_dir_override: Path | None = None, mode_override: str | None = None, yes: bool = False, auto_on_run: bool = False) -> dict`:
       - Load profile: `from graphify.profile import load_profile; profile = load_profile(vault_dir)`.
       - Resolve mode: mode_override > profile["reverse_sync"].get("mode", "always_ask").
       - Resolve input_dir: input_dir_override > profile["input_path"].
       - changes = compute_change_set(profile_with_overrides).
       - Initialize counters dict and `all_yes = yes and mode == "always_ask"`. (D-12: yes only flips always_ask.)
       - For each ChangeRecord:
           * kind == "skip" → continue (no log, no count)
           * kind == "vault_deleted" → counters["vault_deleted"] += 1, no write (D-10), JSONL logged in Plan 04
           * mode == "never_copy" → counters["skipped_never_copy"] += 1, no write (D-12: yes does NOT override)
           * mode == "always_copy" → _atomic_copy + counters["copied"] += 1
           * mode == "always_ask":
                - if all_yes → copy directly
                - else → resp = prompt_per_file(rel, vault_text, input_text)
                    - "yes" → copy, counters["copied"] += 1
                    - "no" → counters["skipped_user"] += 1
                    - "all" → all_yes = True; copy this file too
                    - "quit" → break the loop; remaining files untouched
                    - "skip" (non-TTY) → counters["skipped_conflict"] += 1 (D-13)
       - Path-confinement: every copy validated with _validate_input_path; reject with stderr `[graphify] reverse-sync: refusing target outside input_path: {rel}` (security V4).
       - Set `result["conflicts_skipped"] = counters["skipped_conflict"]` for Plan 05's stderr summary.
       - `result["failed"] = False` always for now (errors handled per-file; future hardening).
       - Return result.
    6. Register CLI subcommand in graphify/__main__.py — INSERT a new block right after the `cmd == "update-vault"` block (search for `elif cmd == "update-vault"` near `:3283`; place new block immediately after that elif/else closes). Use the exact pattern from RESEARCH Pattern 1:
       ```python
       elif cmd == "reverse-sync":
           import argparse as _ap
           _p_rs = _ap.ArgumentParser(prog="graphify reverse-sync")
           _p_rs.add_argument("--vault", default=None)
           _p_rs.add_argument("--input", default=None)
           _p_rs.add_argument("--yes", action="store_true",
               help="Override always_ask mode (does NOT override never_copy per D-12)")
           _p_rs.add_argument("--mode",
               choices=["always_ask", "always_copy", "never_copy"], default=None)
           opts = _p_rs.parse_args(sys.argv[2:])
           from graphify.reverse_sync import run_reverse_sync
           result = run_reverse_sync(
               vault_dir=Path(opts.vault) if opts.vault else Path.cwd(),
               input_dir_override=Path(opts.input) if opts.input else None,
               mode_override=opts.mode,
               yes=opts.yes,
           )
           sys.exit(0 if not result["failed"] else 1)
       ```
       Also register "reverse-sync" in the help-text command list / argparse choices wherever __main__.py enumerates commands (grep for "update-vault" string literals to find sibling registration sites).
  </action>
  <verify>
    <automated>pytest tests/test_reverse_sync.py -q && python3 -m graphify reverse-sync --help 2>&1 | grep -q 'always_ask'</automated>
  </verify>
  <done>All 22 reverse_sync tests pass; CLI help shows the subcommand; grep shows --yes help text mentions D-12 invariant; non-TTY path verified.</done>
</task>

</tasks>

<verification>
- `pytest tests/test_reverse_sync.py -q` all green
- `python3 -m graphify reverse-sync --help` lists --vault --input --mode --yes
- grep -n "elif cmd == .reverse-sync" graphify/__main__.py returns exactly one match
</verification>

<success_criteria>
- All three modes dispatch correctly per Success Criterion 3
- --yes overrides only always_ask (D-12 verified by test)
- Non-TTY skips under always_ask (D-13)
- Y/n/d/A/Q prompt with [d] re-prompt works (D-01, D-02)
- CLI subcommand `graphify reverse-sync` registered
</success_criteria>

<output>
Create `.planning/phases/70-vrsync-vault-input-reverse-sync-user-file-augmentation/70-03-reverse-sync-cmd-SUMMARY.md` after completion.
</output>
