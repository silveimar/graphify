---
phase: 05-integration-cli
verified: 2026-04-11T00:00:00Z
status: gaps_found
score: 2/3 must-haves verified
overrides_applied: 0
gaps:
  - truth: "Running `graphify --validate-profile <vault-path>` prints pass/fail with actionable messages and exits without writing any files"
    status: failed
    reason: "__main__.py has no argparse handling for --validate-profile. The command exits with 'error: unknown command' instead of running the preflight validator."
    artifacts:
      - path: "graphify/__main__.py"
        issue: "No case/branch for '--validate-profile' in the main() dispatch. The library function validate_profile_preflight exists and is tested, but is not wired to the graphify CLI."
    missing:
      - "Add '--validate-profile <vault-path>' handling in graphify/__main__.py main() that calls validate_profile_preflight(vault_dir), prints errors/warnings, and sys.exit(1 if errors else 0)"
  - truth: "Running `graphify --obsidian --dry-run` prints the full plan of files to create or update without writing any files"
    status: failed
    reason: "__main__.py has no argparse handling for --obsidian or --dry-run. Both commands exit with 'error: unknown command'."
    artifacts:
      - path: "graphify/__main__.py"
        issue: "No case/branch for '--obsidian' or '--dry-run' flags. The library to_obsidian(dry_run=True) works and is tested, but is not wired to the graphify CLI."
    missing:
      - "Add '--obsidian [--obsidian-dir <path>] [--dry-run]' handling in graphify/__main__.py that loads graph JSON, calls to_obsidian(..., dry_run=True), and prints format_merge_plan(result)"
---

# Phase 5: Integration & CLI Verification Report

**Phase Goal:** All four modules are wired into a refactored `to_obsidian()` that passes existing tests; `--dry-run` and `--validate-profile` are available from the CLI.
**Verified:** 2026-04-11
**Status:** gaps_found
**Re-verification:** No — initial verification

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | Running `graphify --validate-profile <vault-path>` prints pass/fail and exits without writing files | FAILED | `graphify --validate-profile /tmp` → "error: unknown command '--validate-profile'". `__main__.py` has no handler for this flag. |
| 2 | Running `graphify --obsidian --dry-run` prints the full plan without writing any files | FAILED | `graphify --obsidian --dry-run` → "error: unknown command '--obsidian'". `__main__.py` has no handler for `--obsidian` or `--dry-run`. |
| 3 | Running `graphify --obsidian` against a vault with no `.graphify/` directory produces backward-compatible output and all existing tests pass | VERIFIED | `pytest tests/ -q` → 862 passed in 2.93s. `to_obsidian()` with default profile produces Atlas/-shaped layout (test_integration.py confirms). |

**Score:** 1/3 truths verified (truths 1 and 2 failed; truth 3 passes)

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `graphify/merge.py` | `format_merge_plan` public helper | VERIFIED | Present at L1036; `_ACTION_DISPLAY_ORDER` tuple at L35 |
| `graphify/merge.py` | `split_rendered_note` public helper | VERIFIED | Present at L1098 |
| `graphify/profile.py` | `validate_profile_preflight` function + `PreflightResult` NamedTuple | VERIFIED | Both present; `PreflightResult` is a NamedTuple with `errors`, `warnings`, `rule_count`, `template_count` |
| `graphify/export.py` | Refactored `to_obsidian()` with `profile` and `dry_run` kwargs | VERIFIED | Signature confirmed: `['G', 'communities', 'output_dir', 'profile', 'community_labels', 'cohesion', 'dry_run']` |
| `graphify/__init__.py` | Lazy imports for `format_merge_plan`, `split_rendered_note`, `validate_profile_preflight`, `PreflightResult` | VERIFIED | All four entries present in `_map` dict |
| `graphify/__main__.py` | CLI handlers for `--validate-profile` and `--obsidian --dry-run` | MISSING | No argument handling for these flags; `graphify --validate-profile /tmp` and `graphify --obsidian --dry-run` both produce "error: unknown command" |
| `graphify/skill.md` | `validate_profile_preflight`, `format_merge_plan`, `dry_run=`, `profile ok —` patterns | VERIFIED | All markers present; Step 6a section exists |
| `graphify/skill-{aider,claw,codex,copilot,droid,opencode,trae,windows}.md` | All 8 platform variants updated with same patterns | VERIFIED | Each variant has ≥2 matches for `format_merge_plan`, `validate_profile_preflight`, `dry_run`, `result.rule_count`, `profile ok —` |
| `tests/test_integration.py` | Integration tests for dry-run, default-profile, FIX-01/02/03 regression | VERIFIED | File exists; tests for MergeResult return, Atlas layout, dry-run writes zero files, FIX-01/02/03 |
| `tests/test_merge.py` | format_merge_plan and split_rendered_note unit tests | VERIFIED | 15 test functions matching `def test_format_merge_plan` or `def test_split_rendered_note` |

### Key Link Verification

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| `export.py::to_obsidian` | `profile.py::load_profile` | function-local import | WIRED | `from graphify.profile import load_profile` present inside `to_obsidian` |
| `export.py::to_obsidian` | `mapping.py::classify` | direct call | WIRED | `classify(G, communities, profile, cohesion=cohesion)` at L485 |
| `export.py::to_obsidian` | `templates.py::render_note` | per-node loop | WIRED | `render_note(...)` called in per-node loop |
| `export.py::to_obsidian` | `templates.py::render_moc` | per-community loop | WIRED | `render_moc(...)` called in per-community loop |
| `export.py::to_obsidian` | `merge.py::compute_merge_plan` | after render loop | WIRED | `compute_merge_plan(out, rendered_notes, ...)` at L556 |
| `export.py::to_obsidian` | `merge.py::apply_merge_plan` | non-dry-run path | WIRED | `apply_merge_plan(plan, out, rendered_notes, profile)` at L562 |
| `export.py::to_obsidian` | `merge.py::split_rendered_note` | public wrapper | WIRED | `split_rendered_note(rendered_text)` called twice inside to_obsidian |
| `skill.md::Step 6` | `export.py::to_obsidian` | Python inline block | WIRED | `to_obsidian(..., dry_run=dry_run)` present |
| `skill.md::Step 6a` | `profile.py::validate_profile_preflight` | Python inline block | WIRED | `validate_profile_preflight(vault)` with `result.rule_count` / `result.template_count` |
| `__main__.py` | `validate_profile_preflight` | argparse handler | NOT_WIRED | No handler in `__main__.py` main() dispatch |
| `__main__.py` | `to_obsidian(dry_run=True)` | argparse handler | NOT_WIRED | No handler in `__main__.py` main() dispatch |

### Data-Flow Trace (Level 4)

| Artifact | Data Variable | Source | Produces Real Data | Status |
|----------|---------------|--------|-------------------|--------|
| `to_obsidian()` | `MergeResult` | `apply_merge_plan` → `compute_merge_plan` → rendered_notes from classify+render | Yes — 862 tests pass confirming real pipeline | FLOWING |
| `to_obsidian(dry_run=True)` | `MergePlan` | `compute_merge_plan` without applying | Yes — `test_to_obsidian_dry_run_returns_plan` confirms plan.summary.CREATE > 0 | FLOWING |

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
|----------|---------|--------|--------|
| `graphify --validate-profile <path>` works from CLI | `graphify --validate-profile /tmp` | "error: unknown command '--validate-profile'" | FAIL |
| `graphify --obsidian --dry-run` works from CLI | `graphify --obsidian --dry-run` | "error: unknown command '--obsidian'" | FAIL |
| Library `to_obsidian(dry_run=True)` returns MergePlan | `pytest tests/test_integration.py::test_to_obsidian_dry_run_returns_plan` (covered by full suite) | 862 passed | PASS |
| Full test suite green | `pytest tests/ -q` | 862 passed in 2.93s | PASS |

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|------------|-------------|--------|----------|
| PROF-05 | 05-02, 05-05 | User can run `graphify --validate-profile <vault-path>` to check profile validity without generating output | BLOCKED | `validate_profile_preflight()` exists in `profile.py` and is exported via `__init__.py`, but `__main__.py` has no CLI handler. The skill covers agent-invoked use, but `graphify --validate-profile` as a direct CLI command does not work. |
| MRG-03 | 05-01, 05-03, 05-05 | User can run `graphify --obsidian --dry-run` to preview all changes without writing any files | BLOCKED | `to_obsidian(dry_run=True)` works at library level and is tested, and `format_merge_plan` exists. But `__main__.py` has no `--obsidian` or `--dry-run` CLI flag handling. |
| MRG-05 | 05-03, 05-04, 05-05 | When no vault profile exists, output is backward-compatible with current `to_obsidian()` behavior | SATISFIED | `test_to_obsidian_default_profile_returns_merge_result` and `test_to_obsidian_default_profile_writes_atlas_layout` both pass. Default profile falls back to `_DEFAULT_PROFILE` producing Atlas/ layout. |

### Anti-Patterns Found

| File | Pattern | Severity | Impact |
|------|---------|----------|--------|
| `graphify/__main__.py` | No `--obsidian`, `--dry-run`, or `--validate-profile` arg dispatch | BLOCKER | Success criteria 1 and 2 require these as CLI commands; they are not present |
| `graphify/skill.md` | `dry_run = False  # replace with True if --dry-run was passed` | Warning | The skill has a hardcoded `False` with a comment. The agent consuming the skill must interpret `--dry-run` and substitute `True` — there is no automated mechanism for passing CLI flags into the embedded Python block. This is a known architectural limitation (D-73: CLI is utilities-only; skill is the pipeline driver). |

### Human Verification Required

None — gaps are fully deterministic (CLI flag not implemented).

### Gaps Summary

**Root cause: `graphify/__main__.py` has no handlers for the `--obsidian`, `--dry-run`, or `--validate-profile` flags.**

The library layer is complete and fully tested:
- `to_obsidian(dry_run=True)` returns a `MergePlan` without writing files (verified by test suite)
- `validate_profile_preflight()` runs the four-layer preflight and returns a `PreflightResult` (verified by test suite)
- `format_merge_plan()` produces the human-readable dry-run summary (verified by test suite)
- All lazy imports are registered in `__init__.py`
- All 9 skill files are updated with the correct code patterns

The CLI layer is missing:
- `graphify --validate-profile <vault-path>` → "error: unknown command"
- `graphify --obsidian --dry-run` → "error: unknown command"

Both success criteria 1 and 2 use the literal phrasing "Running `graphify --validate-profile`" and "Running `graphify --obsidian --dry-run`", referring to the binary CLI. The phase goal also states "available from the CLI". The implementation is library-level only.

**Both gaps share the same root cause** and can be addressed in a single plan that adds argument handling to `__main__.py`.

---

_Verified: 2026-04-11_
_Verifier: Claude (gsd-verifier)_
