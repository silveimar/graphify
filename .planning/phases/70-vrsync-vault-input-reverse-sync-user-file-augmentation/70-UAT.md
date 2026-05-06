---
status: partial
phase: 70-vrsync-vault-input-reverse-sync-user-file-augmentation
source:
  - 70-01-augment-SUMMARY.md
  - 70-02-reverse-sync-detect-SUMMARY.md
  - 70-03-reverse-sync-cmd-SUMMARY.md
  - 70-04-jsonl-log-SUMMARY.md
  - 70-05-auto-on-run-SUMMARY.md
  - 70-06-doctor-and-schema-SUMMARY.md
  - 70-07-augmentation-chokepoint-wiring-SUMMARY.md
started: 2026-05-06T01:19:01Z
updated: 2026-05-06T01:19:30Z
---

## Current Test

[testing complete]

## Tests

### 1. Cold Start Smoke Test
expected: From a fresh checkout (no graphify-out/, no cached state), run `graphify --help` and a basic `graphify run` against a tiny corpus. CLI loads without import errors, the pipeline completes, and graphify-out/ artifacts are produced.
result: pass

### 2. Augmentation Adds Allowlist Frontmatter Without Touching Body
expected: Take a user-authored vault note with a body and partial frontmatter. Trigger augmentation (via vault-promote into a user_only_folder). Allowlist keys (tags, related_to, up, references, comments, analysis, type) get added/merged into frontmatter; body bytes are byte-identical pre/post; existing scalar values are not overwritten. Re-running yields zero diff.
result: blocked
blocked_by: third-party
reason: "graphify run did not emit graph.json from a tiny markdown corpus (likely needs LLM/API key for doc extraction); could not reach the vault-promote augmentation chokepoint manually. Contract is covered by 12 unit tests in tests/test_augment.py + 4 integration tests in tests/test_vault_promote.py (all green)."

### 3. reverse-sync CLI Subcommand
expected: Run `graphify reverse-sync --vault <vault> --input <input>` with a vault containing user-authored notes in user_only_folders that don't exist in --input. CLI prompts Y/n/d/A/Q (or honors --mode/--yes), copies confirmed files into the input corpus via atomic path-confined writes, and reports a per-file summary.
result: issue
reported: "File copy succeeded (Alice.md landed in uat70-input/People/) but CLI printed no per-file summary or any output to stdout/stderr — silent success."
severity: minor

### 4. JSONL Audit Log on reverse-sync
expected: After a reverse-sync run with at least one new/update/vault_deleted decision, an audit JSONL file exists with one line per non-skip decision and the fixed 7-key schema (timestamp, kind, vault_path, input_path, sha256, mode, decision).
result: pass

### 5. auto_on_run Hook Fires on graphify run / update-vault
expected: With `profile.reverse_sync.auto_on_run: true` in the vault profile, running `graphify run` or `graphify update-vault` triggers reverse-sync detection BEFORE the main pipeline. With it false/absent, the hook is silent. Failures or skipped conflicts warn-and-continue without blocking the parent command.
result: issue
reported: "Set auto_on_run: true and mode: always_copy in vault profile, added Bob.md to uat70-vault/People/ only, ran 'graphify run uat70-input --vault uat70-vault'. No reverse-sync output and Bob.md did NOT appear in uat70-input/People/. Likely root cause: __main__.py forces target=Path.cwd() under D-07 vault auto-adopt, then passes that target as input_dir_override to the reverse-sync hook — so the hook compares against the wrong input directory."
severity: major

### 6. doctor Reverse-Sync Section
expected: `graphify doctor` (against a vault) prints a non-blocking `=== Reverse-Sync ===` section reporting profile config (mode, auto_on_run, user_only_folders) and a count of pending changes, without erroring or blocking on missing config.
result: pass
notes: "Section present, shows log path and pending conflicts count, non-blocking. Doesn't list mode/auto_on_run/user_only_folders config inline — operational status only. Acceptable."

### 7. vault-promote Routes user_only_folders Through Augmentation (Not Refusal)
expected: Running `graphify vault-promote` against a graph with nodes mapped into a `user_only_folders` directory where user files already exist no longer hard-refuses. Allowlist-only frontmatter deltas merge into the existing user file (body untouched); non-allowlist or body-modifying writes are still refused per the user-namespace invariant.
result: blocked
blocked_by: third-party
reason: "Same upstream blocker as Test 2: vault-promote needs graph.json from a real graphify run (LLM doc extraction + path resolution friction in user's sandbox). Chokepoint contract is covered by 4 integration tests in tests/test_vault_promote.py (70-07 RED→GREEN suite, all green) plus 12 augmentation unit tests."

## Summary

total: 7
passed: 3
issues: 2
pending: 0
skipped: 0
blocked: 2

## Gaps

- truth: "reverse-sync CLI reports a per-file summary"
  status: failed
  reason: "User reported: File copy succeeded but CLI printed no per-file summary or any output to stdout/stderr — silent success."
  severity: minor
  test: 3
  artifacts: []
  missing: []

- truth: "auto_on_run hook in graphify run pulls user-only vault files into the input corpus before pipeline executes"
  status: failed
  reason: "Bob.md created only in uat70-vault/People/ was not copied to uat70-input/People/ when running 'graphify run uat70-input --vault uat70-vault' with auto_on_run: true and mode: always_copy. Hypothesis: __main__.py forces target=Path.cwd() under D-07 vault auto-adopt, then the auto_on_run hook passes that forced target as input_dir_override to run_reverse_sync — comparing vault against CWD instead of the user's input dir. Either (a) the hook should use the original raw_target, not the D-07-rewritten target, or (b) D-07 should not apply to reverse-sync's input_dir_override."
  severity: major
  test: 5
  artifacts:
    - graphify/__main__.py:2995-3015 (D-07 target rewrite + auto_on_run hook)
    - graphify/reverse_sync.py:314-345 (run_reverse_sync input_path resolution)
  missing: []
