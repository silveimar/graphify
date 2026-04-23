---
phase: 19
plan: "03"
subsystem: vault-promote
tags: [vault, obsidian, cli, manifest, atomic-write, profile-writeback]
dependency_graph:
  requires: [19-01, 19-02]
  provides: [promote, write_note, _writeback_profile, vault-manifest.json, import-log.md, vault-promote-cli]
  affects: [graphify/vault_promote.py, graphify/__main__.py, tests/test_vault_promote.py]
tech_stack:
  added: [hashlib.sha256, os.replace, tempfile-pattern, yaml.dump]
  patterns: [atomic-write-tmp-replace, d13-decision-table, d15-latest-first-log, d16-atomic-everywhere]
key_files:
  created: []
  modified:
    - graphify/vault_promote.py
    - graphify/__main__.py
    - tests/test_vault_promote.py
decisions:
  - "D-13 decision table enforced exactly: written/overwritten/skipped_foreign/skipped_user_modified"
  - "validate_vault_path imported from graphify.profile (NOT security) per Pitfall 3"
  - "PyYAML guard in _writeback_profile: ImportError → stderr warning + return skipped_no_yaml"
  - "promote() returns summary dict {promoted, skipped, writeback} for test assertion and CLI output"
  - "_hash_bytes(path: Path) takes a Path object (not bytes) — test initially passed bytes, fixed"
  - "Maps filename = safe_filename('Community N') = 'Community N.md' not 'community-N.md'"
metrics:
  duration: "6 minutes"
  tasks_completed: 2
  files_changed: 3
  completed_date: "2026-04-23"
requirements: [VAULT-01, VAULT-05, VAULT-06]
---

# Phase 19 Plan 03: Vault Promotion Write Pipeline Summary

**One-liner:** Atomic note writer with SHA-256 manifest, D-13 overwrite-self-skip-foreign policy, append-first import-log, and PyYAML-optional profile write-back wired to `graphify vault-promote` CLI.

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 3.1 | Atomic writer + manifest decision table + import-log | 5a671ed | vault_promote.py, test_vault_promote.py |
| 3.2 | promote() orchestrator + profile write-back + CLI | 0b9d65c | vault_promote.py, __main__.py, test_vault_promote.py |

## What Was Built

### Task 3.1: Write Infrastructure

Added to `graphify/vault_promote.py`:

- `_hash_bytes(path: Path) -> str` — SHA-256 of raw file bytes (matches merge.py::_content_hash idiom)
- `_write_atomic(target, content)` — lifted verbatim from merge.py with fsync; tempfile + os.replace
- `_load_manifest(graphify_out)` / `_save_manifest(manifest, graphify_out)` — JSON round-trip with `indent=2, sort_keys=True`, atomic write
- `write_note(vault_dir, rel_path, content, manifest) -> str` — implements D-13 decision table exactly; calls `validate_vault_path` before any I/O
- `_append_import_log(graphify_out, run_block)` — prepends new run block after title header (latest-first per D-15)
- `_format_run_block(run_meta, counts_by_type, skipped_entries) -> str` — emits exact D-15 block shape

Added imports: `hashlib`, `os`, `sys`, `validate_vault_path` (from `graphify.profile`).

### Task 3.2: Orchestrator + CLI

Added to `graphify/vault_promote.py`:

- `_writeback_profile(vault_dir, detected_tags) -> str` — union-merge detected tech tags into `.graphify/profile.yaml`; PyYAML optional guard; atomic write; validate_vault_path before write; returns "written" | "disabled" | "skipped_no_yaml"
- `promote(graph_path, vault_path, threshold) -> dict` — full pipeline: load → load_profile → resolve_taxonomy → validate_vault → classify → render+write → save_manifest → append_import_log → _writeback_profile; respects `profile_sync.auto_update`

Added to `graphify/__main__.py`:

- `elif cmd == "vault-promote":` branch with argparse (`--vault REQUIRED`, `--threshold INT=3`, `--graph STR`)
- Dispatches to `from graphify.vault_promote import promote`

## Test Results

```
tests/test_vault_promote.py: 20 passed, 0 failed, 0 skipped
tests/: 1469 passed, 0 failed
```

Tests added in this plan:
- `test_vault01_write_decision_table` — all 4 D-13 cases
- `test_vault01_write_note_path_traversal` — path escape raises ValueError
- `test_vault05_import_log_written` — log file created with Run block
- `test_vault05_import_log_append_latest_first` — second block before first in file
- `test_vault05_manifest_roundtrip` — sort_keys=True preserved
- `test_promote_smoke` — end-to-end: manifest + log + summary
- `test_promote_idempotent` — second run: no foreign skips, 2 Run blocks in log
- `test_vault01_cli_does_not_overwrite_foreign` — pre-placed file unchanged, foreign in summary + log
- `test_vault06_profile_writeback_union_merge` — .graphify/profile.yaml gains tech/python
- `test_vault06_profile_writeback_opt_out` — byte-identical when auto_update=False
- `test_cli_subcommand_help_works` — subprocess exit 0 with --vault in stdout

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Test used `_hash_bytes(path.read_bytes())` — wrong type**
- **Found during:** Task 3.1 GREEN phase (first test run)
- **Issue:** Test passed bytes to `_hash_bytes()` which expects `Path`
- **Fix:** Changed test to `_hash_bytes(disk_path)` (pass Path, not bytes)
- **Files modified:** tests/test_vault_promote.py
- **Commit:** 5a671ed (fixed inline before commit)

**2. [Rule 1 - Bug] Foreign-file test used wrong Maps filename**
- **Found during:** Task 3.2 GREEN phase (one test failure)
- **Issue:** Test pre-placed `community-0.md` but `render_note()` uses `safe_filename("Community 0")` = `"Community 0.md"`
- **Fix:** Changed pre-placed filename to `"Community 0.md"` to match actual render output
- **Files modified:** tests/test_vault_promote.py
- **Commit:** 0b9d65c (fixed inline before commit)

## Known Stubs

None. All functions are fully wired. Profile write-back is gated by `profile_sync.auto_update` (tested both on/off).

## Threat Flags

None. All T-19-03-0x threats from the plan's threat register are mitigated:
- T-19-03-01/02: Path traversal / symlink escape — `validate_vault_path` called before every vault write
- T-19-03-03: User-edited note overwrite — D-13 hash check enforced
- T-19-03-04: Foreign file overwrite — `skipped_foreign` path enforced
- T-19-03-05: YAML injection — values flow through closed `_TECH_EXT_MAP`; `yaml.dump` never takes string-concat input

## Self-Check

### Files exist:

- `graphify/vault_promote.py` — contains `promote`, `_writeback_profile`, `write_note`, `_hash_bytes`, `_write_atomic`, `_load_manifest`, `_save_manifest`, `_append_import_log`, `_format_run_block`
- `graphify/__main__.py` — contains `elif cmd == "vault-promote":`
- `tests/test_vault_promote.py` — 20 tests, all passing

### Commits exist:
- 5a671ed — Task 3.1
- 0b9d65c — Task 3.2

## Self-Check: PASSED
