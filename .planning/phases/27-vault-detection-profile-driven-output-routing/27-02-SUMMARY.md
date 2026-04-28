---
phase: 27-vault-detection-profile-driven-output-routing
plan: 02
subsystem: vault-adapter
tags: [vault-detection, output-resolution, resolved-output, vault-adapter]
requires: [PROF-01 load_profile, PROF-04 validate_profile, validate_vault_path]
provides:
  - graphify.output.ResolvedOutput
  - graphify.output.is_obsidian_vault
  - graphify.output.resolve_output
affects:
  - graphify/__main__.py (Plan 27-03 will consume resolve_output)
  - graphify/detect.py (Phase 28 will consume ResolvedOutput for self-ingest pruning)
  - graphify/doctor.py (Phase 29 will consume ResolvedOutput)
tech-stack:
  added: []
  patterns:
    - NamedTuple data carrier for cross-plan integration contract (D-13)
    - Function-local imports to avoid circular dependency output -> profile
    - Per-mode lazy imports for parallel-wave compatibility
key-files:
  created:
    - graphify/output.py
    - tests/test_output.py
  modified: []
decisions:
  - D-04 strict CWD-only vault detection (no parent walk)
  - D-05 vault + missing profile -> SystemExit
  - D-02 vault + profile without 'output:' block -> SystemExit
  - D-08 cli_output > profile.output > v1.0 default precedence
  - D-09 single-line stderr precedence message emitted exactly once
  - D-10 cli_output treated as literal CWD-relative or absolute path
  - D-11 artifacts always sibling-of-vault when vault detected
  - D-12 silent byte-identical backcompat when no vault and no flag
  - D-13 single ResolvedOutput integration carrier
metrics:
  duration: ~25 minutes
  completed: 2026-04-27
  tasks: 2
  files: 2
  tests_added: 21
  tests_passing_in_isolation: 14 (7 await Plan 27-01 landing)
---

# Phase 27 Plan 02: Vault Detection + Output Resolution Summary

`graphify/output.py` introduces the v1.7 vault-detection + output-resolution layer with a single `ResolvedOutput` NamedTuple, the strict CWD-only `is_obsidian_vault()` predicate (D-04), and the `resolve_output()` resolver that orchestrates vault detection, profile load, mode resolution, artifact placement, and the D-09 precedence stderr line.

## Public API

```python
from graphify.output import ResolvedOutput, is_obsidian_vault, resolve_output

ResolvedOutput(vault_detected, vault_path, notes_dir, artifacts_dir, source)
# source ∈ {"profile", "cli-flag", "default"}

is_obsidian_vault(path: Path) -> bool      # strict CWD-only (D-04)
resolve_output(cwd: Path, *, cli_output: str | None = None) -> ResolvedOutput
```

## Behavior matrix

| CWD has `.obsidian/` | profile.yaml | output: block | cli_output | source     | notes_dir                    | artifacts_dir                | stderr |
|----------------------|--------------|---------------|------------|------------|------------------------------|------------------------------|--------|
| no                   | —            | —             | None       | default    | `graphify-out/obsidian`      | `graphify-out`               | silent (D-12) |
| no                   | —            | —             | "X"        | cli-flag   | `<cwd>/X.resolve()`          | same as notes_dir            | silent |
| yes                  | absent       | —             | None       | (raises)   | —                            | —                            | D-05 refusal |
| yes                  | present      | absent        | None       | (raises)   | —                            | —                            | D-02 refusal |
| yes                  | present      | vault-relative| None       | profile    | `<vault>/<path>`             | `<vault>/../graphify-out`    | VAULT-08 detection |
| yes                  | present      | absolute      | None       | profile    | `Path(p).resolve()`          | `<vault>/../graphify-out`    | VAULT-08 detection |
| yes                  | present      | sibling-of-vault | None    | profile    | `<vault>/../<path>`          | `<vault>/../graphify-out`    | VAULT-08 detection |
| yes                  | any          | any           | "X"        | cli-flag   | `<cwd>/X.resolve()`          | `<vault>/../graphify-out`    | VAULT-08 + D-09 override line (exactly once) |

## Threats mitigated

- T-27-06 — `.obsidian` file-not-dir spoofing → `is_dir()` check + dedicated test
- T-27-07 — profile-driven path tampering → all modes flow through validators (`validate_vault_path`, `validate_sibling_path`, `Path.is_absolute()` re-check)
- T-27-08 — `..` in sibling-of-vault path → `validate_sibling_path` raises ValueError; covered by `test_resolve_output_sibling_of_vault_traversal_in_path_refuses`
- T-27-09 — silent auto-adopt to default vault path → D-02 refusal; no source-path mirroring fallback
- T-27-10 — silent PyYAML-missing failure → distinct error mentioning `pip install graphifyy[obsidian]`
- T-27-11 — duplicate D-09 stderr line → single emission inside `resolve_output()`; `count(...) == 1` asserted
- T-27-12 — sibling at filesystem root → defended by `validate_sibling_path` (Plan 27-01); covered by POSIX-conditional test

## Tasks executed

| # | Name | Commit | Files |
|---|------|--------|-------|
| 1 | Create `graphify/output.py` | `d825cc5` (feat) + `b3e02fc` (fix) | graphify/output.py |
| 2 | Create `tests/test_output.py` | `f0661b4` | tests/test_output.py |

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 — Blocking issue] Lazy per-mode profile imports**

- **Found during:** Task 2 verification (`pytest tests/test_output.py`)
- **Issue:** The plan's <action> for Task 1 placed `from graphify.profile import load_profile, validate_sibling_path, validate_vault_path` immediately after the PyYAML check. This made every vault-detected branch fail with `ImportError` in this worktree because Plan 27-01 (parallel wave) ships `validate_sibling_path` and has not yet landed. Tests like `test_resolve_output_vault_profile_no_output_block_refuses` failed before they could exercise the no-output-block refusal path.
- **Fix:** Moved `validate_sibling_path` import inside the `sibling-of-vault` branch and `validate_vault_path` inside the `vault-relative` branch. Top of the vault-detected block now imports only `load_profile` (which already exists in this worktree). This is consistent with the plan's stated invariant ("function-local imports avoid circular dependency"); the change extends the per-function scope to per-mode scope so non-sibling tests can run before 27-01 lands.
- **Files modified:** `graphify/output.py`
- **Commit:** `b3e02fc`

### Deferred Issues (pre-existing, out of scope)

- `tests/test_detect.py::test_detect_skips_dotfiles` and `tests/test_extract.py::test_collect_files_from_dir` fail in this worktree because the path includes `.claude/worktrees/...` (a dotdir component). Logged in `deferred-items.md`. Not caused by 27-02.

## Test results in this worktree (Plan 27-01 not yet merged)

```
$ pytest tests/test_output.py -q
14 passed, 7 failed in 0.16s
```

Passing (14):
- `test_is_obsidian_vault_true_when_dir_present`
- `test_is_obsidian_vault_false_when_file_not_dir`
- `test_is_obsidian_vault_false_when_absent`
- `test_is_obsidian_vault_no_parent_walk`
- `test_resolve_output_no_vault_default_paths`
- `test_resolve_output_vault_no_profile_refuses`
- `test_resolve_output_vault_profile_no_output_block_refuses`
- `test_resolve_output_cli_flag_in_vault_without_profile_output_emits_fallback_label`
- `test_resolve_output_cli_flag_no_vault_silent`
- `test_resolve_output_cli_flag_absolute_path`
- `test_resolve_output_pyyaml_missing_distinct_message`
- `test_resolved_output_namedtuple_field_order`
- `test_resolved_output_is_immutable`
- `test_resolved_output_unpacks_to_tuple`

Awaiting Plan 27-01 (7) — all rely on `validate_sibling_path` or on `_VALID_TOP_LEVEL_KEYS` accepting an `output:` block in `profile.yaml`:
- `test_resolve_output_vault_relative_resolves`
- `test_resolve_output_absolute_mode`
- `test_resolve_output_sibling_of_vault_mode`
- `test_resolve_output_artifacts_always_sibling_when_vault`
- `test_resolve_output_cli_flag_overrides_profile_emits_stderr`
- `test_resolve_output_sibling_of_vault_traversal_in_path_refuses`
- `test_resolve_output_sibling_at_filesystem_root_refuses`

This is explicit parallel-wave behavior accepted by the plan: see `<sequencing>` section. Once both worktrees merge into the integration branch, all 21 tests should pass.

## Integration contract for downstream consumers

- **Plan 27-03 (`graphify/__main__.py`)** — call `resolve_output(Path.cwd(), cli_output=args.output)` once at the top of `run` and `--obsidian` paths. Use `result.notes_dir` for Obsidian notes and `result.artifacts_dir` for graph/cache/report. Do NOT re-emit any of the stderr lines that `resolve_output` already prints (Pitfall 5).
- **Phase 28 (`graphify/detect.py`)** — receive `ResolvedOutput` to prune both `notes_dir` and `artifacts_dir` from the input scan when `vault_detected` is True.
- **Phase 29 (`graphify/doctor.py`)** — call `resolve_output()` to produce the diagnostic report.

## Requirements addressed

- VAULT-08 — vault detection + report (`is_obsidian_vault`, `[graphify] vault detected at ...` stderr)
- VAULT-09 — auto-adopt Option C (refuse loudly when profile or output block missing; honor profile.output otherwise)

## Self-Check

**Files exist:**

```
$ [ -f graphify/output.py ] && echo FOUND
FOUND
$ [ -f tests/test_output.py ] && echo FOUND
FOUND
```

**Commits exist:**

```
$ git log --oneline b5bb41a..HEAD
f0661b4 test(27-02): add tests/test_output.py ...
b3e02fc fix(27-02): defer profile validator imports per-mode ...
d825cc5 feat(27-02): add output.py with vault detection and resolution
```

## Self-Check: PASSED
