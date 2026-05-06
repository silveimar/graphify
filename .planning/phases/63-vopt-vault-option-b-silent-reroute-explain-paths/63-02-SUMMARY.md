---
phase: 63
plan: 02
subsystem: cli
tags: [cli, introspection, paths, flag, vopt-03]
requires: [63-01]
provides: ["--explain-paths CLI flag", "5-row resolution introspection table"]
affects: ["graphify/__main__.py main()"]
tech-stack:
  added: []
  patterns:
    - "Manual-argv early-exit (mirrors --version)"
    - "contextlib.redirect_stderr for clean introspection stdout"
    - "Pin forwarding (--vault, GRAPHIFY_VAULT) to resolve_execution_paths"
key-files:
  created:
    - tests/test_explain_paths.py
  modified:
    - graphify/__main__.py
decisions:
  - "Treat ResolvedSource='cli-flag' as label 'flag-output' (cli-flag origin not preserved post-resolve; flag-obsidian-dir label is unreachable in this implementation)"
metrics:
  duration: "~10 min"
  completed: 2026-05-06
---

# Phase 63 Plan 02: --explain-paths CLI Flag Summary

VOPT-03 closed: `graphify --explain-paths` prints a 5-row key:value resolution table to stdout and exits 0 without invoking the pipeline. Manual-argv early-exit (after `--version`, before subcommand dispatch) preempts even `graphify run --explain-paths …`. Honors `--vault` and `GRAPHIFY_VAULT` pins (W4 mandatory). stderr suppressed during introspection so the table is grep-clean.

## What Shipped

- `_print_explain_paths_table(*, vault_cli, env_vault)` helper in `graphify/__main__.py` next to `_render_version_block`.
- Early-exit `if "--explain-paths" in sys.argv` placed right after the `--version` block in `main()`, after `_strip_leading_vault_global_argv` so `g_vault_exp` is already extracted.
- Source→label map: `cli-flag→flag-output`, `profile/vault-cli/vault-env/vault-list→profile`, `option-b→option-b (silent reroute)`, `default→default`.
- `try/except SystemExit` wrapper → `resolution: error (see stderr)` + `<unresolved>` path (T-63-07).
- Help text updated.
- 12 new subprocess tests (`tests/test_explain_paths.py`): exit code, no pipeline run, 5-row contract, default/option-b/profile labels, vault yes/no, profile <none>, absolute path ending `.graphify-out/obsidian`, stderr quiet, run-subcommand preemption (W5), `--vault` pin (W4), `GRAPHIFY_VAULT` pin (W4).

## Verification

- `pytest tests/test_explain_paths.py -q` → 12/12 pass.
- `pytest tests/test_explain_paths.py tests/test_output_path_matrix.py tests/test_vault_cwd.py tests/test_output.py tests/test_routing_audit.py -q` → 85/85 pass.
- Manual: `cd /tmp && python -m graphify --explain-paths` → 5 rows on stdout, exit 0, empty stderr.

## Commits

- `93e2a7d` test(63-02): RED — failing subprocess tests for --explain-paths flag (VOPT-03)
- `0aad27c` feat(63-02): GREEN — --explain-paths flag with 5-row resolution table + pin support (VOPT-03)

## Deviations from Plan

None — plan executed exactly as written.

## Known Limitations / Notes

- **`flag-obsidian-dir` label is unreachable.** D-03's enum lists 5 possible resolution values, but `ResolvedOutput.source == "cli-flag"` does not preserve whether the flag was `--output` or `--obsidian-dir`. Both collapse to `cli-flag` upstream. The map therefore emits `flag-output` for any cli-flag source. Disambiguation would require threading the flag origin into `ResolvedOutput` (out of scope for VOPT-03). Future phase can revisit if grep-on-`flag-obsidian-dir` becomes a stated need.

## TDD Gate Compliance

- RED gate: `93e2a7d` (test commit) ✓
- GREEN gate: `0aad27c` (feat commit) ✓
- REFACTOR gate: not needed (helper landed clean).

## Self-Check: PASSED

- `tests/test_explain_paths.py` exists ✓
- `_print_explain_paths_table` defined exactly once in `graphify/__main__.py` ✓
- 12 test functions, all GREEN ✓
- Both commits present in `git log` ✓
