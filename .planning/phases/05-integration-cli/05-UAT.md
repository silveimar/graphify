---
status: complete
phase: 05-integration-cli
source:
  - 05-01-SUMMARY.md
  - 05-02-SUMMARY.md
  - 05-03-SUMMARY.md
  - 05-04-SUMMARY.md
  - 05-05-SUMMARY.md
  - 05-06-SUMMARY.md
started: 2026-04-11T22:15:00Z
updated: 2026-04-11T22:19:55Z
mode: automated
notes: "User invoked '/gsd-verify-work 05 and run all validation commands' — ran the VERIFICATION.md spot-checks directly instead of the conversational checkpoint loop."
---

## Current Test

[testing complete]

## Tests

### 1. Full test suite green

expected: |
  `pytest tests/ -q` exits 0 with no failures. Must still be 872 tests after the
  WR-01/WR-02 fixes landed on top of the gap-closure commits.
command: pytest tests/ -q
result: pass
evidence: "872 passed in 3.42s"

### 2. `--validate-profile` on a vault with no .graphify/ directory

expected: |
  `graphify --validate-profile <empty-dir>` runs the four-layer preflight, prints
  a pass line ("profile ok — 0 rules, 0 templates validated" per D-77a early
  return), exits 0, and writes no files anywhere.
command: python -m graphify --validate-profile /tmp
result: pass
evidence: "profile ok — 0 rules, 0 templates validated (exit=0)"

### 3. `--validate-profile` on a vault with a broken profile

expected: |
  When `.graphify/profile.yaml` contains schema errors, the preflight prints each
  error to stderr, still emits warnings about Windows-path-length budget, and
  exits 1 without writing any files.
command: python -m graphify --validate-profile <tmpdir-with-broken-profile>
result: pass
evidence: |
  "error: Unknown profile key 'schema_version'" + similar schema errors printed
  to stderr. Windows-path-length warnings printed. Exit code 1. No files written.

### 4. `--obsidian --dry-run` end-to-end against a fixture graph

expected: |
  `graphify --obsidian --graph <path>.json --obsidian-dir <out> --dry-run` loads
  the graph, calls `to_obsidian(..., dry_run=True)`, prints the merge plan via
  `format_merge_plan`, exits 0, and writes ZERO files under the out directory.
command: python -m graphify --obsidian --graph /tmp/graphify_graph.XXX.json --obsidian-dir /tmp/tmp.XXX --dry-run
result: pass
evidence: |
  Merge Plan — 4 actions
    CREATE: 4, UPDATE: 0, SKIP_PRESERVE: 0, SKIP_CONFLICT: 0, REPLACE: 0, ORPHAN: 0
  4 CREATE rows for Atlas/Dots/Things/{Attention,Layernorm,Transformer}.md and Atlas/Maps/Uncategorized.md.
  Exit code 0. `find $TMPOUT -type f` returned empty — dry-run wrote nothing.

### 5. Backward-compat: default profile produces Atlas/ layout

expected: |
  When no vault profile exists, `to_obsidian()` falls back to `_DEFAULT_PROFILE`
  and produces Atlas/Dots/Things/ and Atlas/Maps/ layout (MRG-05). Existing
  `test_integration.py::test_to_obsidian_default_profile_writes_atlas_layout`
  and `test_to_obsidian_default_profile_returns_merge_result` must still pass.
command: pytest tests/test_integration.py -q
result: pass
evidence: |
  Covered by Test 1 (full suite green, 872 passed). Dry-run output in Test 4
  confirms the Atlas/Dots/Things/ and Atlas/Maps/ layout at runtime.

### 6. `graphify/__main__.py` has CLI handlers for the gap-closure flags

expected: |
  Verification gap #1 (PROF-05) and gap #2 (MRG-03) both required CLI handlers
  in `__main__.py`. Grep must show `--validate-profile` and `--obsidian`
  branches in `main()`, and the help text must mention them.
command: grep -n 'validate-profile\|--obsidian\|--dry-run' graphify/__main__.py
result: pass
evidence: |
  L653: "  --validate-profile <vault-path>"
  L656: "  --obsidian  export an already-built graphify-out/graph.json ..."
  L659: "    --dry-run  print the merge plan via format_merge_plan without writing files"
  L691-712: --validate-profile dispatch branch
  L713-740: --obsidian [--graph ...] [--obsidian-dir ...] [--dry-run] dispatch branch

### 7. Code review warnings (WR-01, WR-02) no longer present

expected: |
  `to_obsidian()` must no longer silently swallow render failures (WR-01) and
  must guard against non-directory output_dir (WR-02). Both were fixed by
  commits 39476f3 and 606cb81 before this UAT run.
command: git log --oneline graphify/export.py | head -5
result: pass
evidence: |
  39476f3 fix(05): WR-01 log to_obsidian render skips to stderr
  606cb81 fix(05): WR-02 guard non-directory output_dir and broaden to_obsidian except
  Manual inspection of export.py confirms stderr logging inside the exception
  handler and the non-directory guard before the render loop.

## Summary

total: 7
passed: 7
issues: 0
pending: 0
skipped: 0

## Gaps

[none — all 7 verification commands passed]

## Environment Notes

- The `graphify` shim at `/Users/silveimar/.pyenv/shims/graphify` is bound to an
  older installed build (package 0.4.1 without the new handlers), so running
  the bare `graphify --validate-profile` command uses the stale build and
  reports "unknown command". Running via `python -m graphify` from the repo
  picks up the local editable code (0.3.29 per pyproject.toml) and works.
- Follow-up: user should run `pip install -e ".[all]"` (or equivalent) to
  re-register the console-script entry point against the current repo code.
  This is an install-env issue, not a code issue — the CLI wiring itself is
  correct and all tests pass.

- The hardcoded `dry_run = False  # replace with True if --dry-run was passed`
  at graphify/skill.md:547 remains by design (documented as a Warning, not a
  Blocker, in 05-VERIFICATION.md). D-73: CLI is utilities-only; skill is the
  pipeline driver. The skill-side comment instructs the agent how to flip the
  value when a `--dry-run` flag is passed to `/graphify`.
