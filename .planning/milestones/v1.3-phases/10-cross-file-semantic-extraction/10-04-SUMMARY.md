---
phase: 10-cross-file-semantic-extraction
plan: "04"
subsystem: cli-integration
tags: [cli, skill, dedup, batch, yaml-config, phase-10]
dependency_graph:
  requires:
    - 10-cross-file-semantic-extraction/02  # batch.py
    - 10-cross-file-semantic-extraction/03  # dedup.py
  provides:
    - CLI surface for --dedup family of flags
    - YAML config layering (.graphify/dedup.yaml)
    - Per-cluster semantic dispatch in all 9 skill variants
  affects:
    - graphify/__main__.py
    - graphify/skill.md + 8 platform variants
    - tests/test_main_cli.py
tech_stack:
  added: []
  patterns:
    - yaml.safe_load with graceful ImportError fallback (Pitfall 7)
    - CLI flag override over YAML config (D-17)
    - Subprocess PYTHONPATH injection in tests for cwd isolation
key_files:
  created: []
  modified:
    - graphify/__main__.py
    - graphify/skill.md
    - graphify/skill-codex.md
    - graphify/skill-opencode.md
    - graphify/skill-aider.md
    - graphify/skill-claw.md
    - graphify/skill-droid.md
    - graphify/skill-trae.md
    - graphify/skill-windows.md
    - graphify/skill-copilot.md
    - tests/test_main_cli.py
decisions:
  - "_load_dedup_yaml_config placed as module-level helper before main() — matches existing helper function pattern (_format_proposal_summary, _check_skill_version)"
  - "Test helper _run_cli_in injects PYTHONPATH from project root so subprocess uses local package, not stale site-packages install — prevents false failures in cwd-isolated tests"
  - "yaml.load detection regex changed from \\byaml\\.load\\b to \\byaml\\.load\\( — excludes docstring references like 'never yaml.load' while still catching actual call sites"
  - "Windows skill variant uses PowerShell backtick line continuation in dedup block to match platform convention"
  - "Copilot variant uses graphify-out/ path prefix in B0.5 clustering block to match its existing path convention"
metrics:
  duration_minutes: 35
  completed_date: "2026-04-16"
  tasks_completed: 2
  files_modified: 11
---

# Phase 10 Plan 04: CLI + Skill Integration Summary

Wire dedup and batch-clustering into the CLI surface and all 9 skill file variants — `--dedup` command with YAML config layering in `__main__.py`, per-cluster semantic dispatch replacing per-file chunking in every skill.

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 | Add --dedup CLI command + YAML config loader | e396f62 | graphify/__main__.py, tests/test_main_cli.py |
| 2 | Update skill.md + 8 platform variants for per-cluster dispatch | bb2affe | 9 skill files |

## What Was Built

### Task 1: `graphify/__main__.py` CLI surface

**Insertion locations:**
- `_load_dedup_yaml_config` helper: lines 884-919 (before `main()`, after `_format_proposal_summary`)
- Help text addition: after `--obsidian` block (lines 917-924)
- `--dedup` command handler: lines 1122-1218 (after `--obsidian` block, before `snapshot`)

**Six new CLI flags:**

| Flag | Form | Default | Source |
|------|------|---------|--------|
| `--dedup` (command) | — | off | D-14 |
| `--dedup-fuzzy-threshold` | `--flag F` and `--flag=F` | 0.90 | D-02 |
| `--dedup-embed-threshold` | `--flag F` and `--flag=F` | 0.85 | D-02 |
| `--dedup-cross-type` | boolean flag | False | D-13 |
| `--batch-token-budget` | `--flag N` and `--flag=N` | 50000 | D-07 |
| `--graph` | `--flag P` and `--flag=P` | graphify-out/extraction.json | — |
| `--out-dir` | `--flag P` and `--flag=P` | graphify-out/ | — |

**YAML config precedence chain (D-17):**
```
CLI flags  >  .graphify/dedup.yaml  >  hardcoded defaults
```
Example: if `dedup.yaml` has `fuzzy_threshold: 0.95` and CLI passes `--dedup-fuzzy-threshold 0.92`, the effective value is `0.92`.

**PyYAML graceful degradation (Pitfall 7):**
When PyYAML is not installed and `.graphify/dedup.yaml` exists, prints:
```
[graphify] warning: PyYAML not installed, skipping .graphify/dedup.yaml
```
and continues with CLI-only config. Never crashes.

**T-10-04 enforcement:** `yaml.safe_load` is the only YAML loader call in `__main__.py`. The `yaml.load(` regex scan in tests confirms zero unsafe calls.

### Task 2: All 9 skill files updated

**Step B0.5 inserted** in each skill after the Part B0 cache check ("Only dispatch subagents..." line), before the original "Step B1 - Split into chunks":

- Runs `cluster_files()` on the uncached file list
- Writes `graphify_clusters.json` (or `graphify-out/.graphify_clusters.json` for copilot variant)
- Replaces "Split into chunks of 20-25 files" with "Dispatch one subagent per cluster"

**Step C.5 inserted** in each skill after Part C merge extract (before "### Step 4"), documenting the optional `graphify --dedup` post-step.

**Platform-specific adaptations:**
- `skill-windows.md`: PowerShell backtick continuation in dedup block; `python` not `$(cat .graphify_python)`
- `skill-copilot.md`: `graphify-out/` prefix in all paths (matches its existing convention)
- All other 7 variants: relative paths (`.graphify_uncached.txt`, `.graphify_clusters.json`)

**Consistency verified:**
```
graphify/skill.md: batch=1 dedup=2
graphify/skill-codex.md: batch=1 dedup=2
graphify/skill-opencode.md: batch=1 dedup=2
graphify/skill-aider.md: batch=1 dedup=2
graphify/skill-claw.md: batch=1 dedup=2
graphify/skill-droid.md: batch=1 dedup=2
graphify/skill-trae.md: batch=1 dedup=2
graphify/skill-windows.md: batch=1 dedup=2
graphify/skill-copilot.md: batch=1 dedup=2
```

## CLI Tests Added (tests/test_main_cli.py)

6 new test functions appended after existing tests:

| Test | Exercises |
|------|-----------|
| `test_help_lists_dedup_flags` | `--dedup`, `--dedup-fuzzy-threshold`, `--dedup-embed-threshold`, `--dedup-cross-type`, `--batch-token-budget` in help output |
| `test_dedup_missing_source_errors_cleanly` | Exit code 1 + "no extraction.json or graph.json found" error message |
| `test_dedup_unknown_flag_exits_2` | Exit code 2 + "unknown --dedup option" for bad flag |
| `test_dedup_reads_empty_extraction` | Exit code 0, writes dedup_report.json with merges=0 |
| `test_dedup_yaml_config_respected` | YAML thresholds echoed in stderr; requires PyYAML (skipped if absent) |
| `test_dedup_yaml_safe_load_only` | Regex scan: `yaml.load(` not present in `__main__.py` |
| `test_no_unsafe_yaml_load_in_any_module` | Scans both `graphify/dedup.py` and `graphify/__main__.py` |

Total: 17 tests pass (11 existing + 6 new). The helper `_run_cli_in` injects `PYTHONPATH` to the project root so subprocess invocations use the local package regardless of cwd.

## Deviations from Plan

None — plan executed exactly as written.

The `yaml.load` regex detection in tests was adjusted from `\byaml\.load\b(?!_all\b)` to `\byaml\.load\(` (Rule 1 auto-fix): the plan's regex matched docstring text ("never yaml.load") which is not an unsafe call. The tighter regex correctly targets actual call sites only — same security intent, better precision.

## Known Stubs

None. The `--dedup` command fully wires to real `dedup()` and `write_dedup_reports()` implementations from plan 10-03.

## Threat Flags

None. No new network endpoints, auth paths, file access patterns beyond what is already in the plan's threat model. The YAML loading is gated behind `yaml.safe_load` with the static scan enforced by tests.

## Self-Check: PASSED

- graphify/__main__.py: FOUND
- graphify/skill.md: FOUND
- tests/test_main_cli.py: FOUND
- .planning/phases/10-cross-file-semantic-extraction/10-04-SUMMARY.md: FOUND
- Commit e396f62 (Task 1): FOUND
- Commit bb2affe (Task 2): FOUND
- 17 tests pass, 0 regressions introduced
