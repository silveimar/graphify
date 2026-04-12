---
phase: 05-integration-cli
verified: 2026-04-11T00:00:00Z
reverified: 2026-04-11T22:19:55Z
status: passed
score: 3/3 must-haves verified
overrides_applied: 0
gaps_closed_by:
  - plan: 05-06
    commits:
      - 9cced12
      - 185ef71
      - 967da30
  - plan: code-review-fix
    commits:
      - 39476f3
      - 606cb81
gaps: []
---

# Phase 5: Integration & CLI Verification Report

**Phase Goal:** All four modules are wired into a refactored `to_obsidian()` that passes existing tests; `--dry-run` and `--validate-profile` are available from the CLI.
**Verified:** 2026-04-11 (initial)
**Re-verified:** 2026-04-11T22:19:55Z (via /gsd-verify-work 05 — see 05-UAT.md)
**Status:** passed
**Re-verification:** Yes — gaps closed by plan 05-06 + WR-01/WR-02 code-review fixes

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | Running `graphify --validate-profile <vault-path>` prints pass/fail and exits without writing files | VERIFIED | `python -m graphify --validate-profile /tmp` → "profile ok — 0 rules, 0 templates validated" (exit 0). Broken-profile fixture → schema errors to stderr, exit 1, no files written. `__main__.py:691-712` dispatch branch added by plan 05-06 (commits 9cced12, 185ef71). |
| 2 | Running `graphify --obsidian --dry-run` prints the full plan without writing any files | VERIFIED | `python -m graphify --obsidian --graph <fixture>.json --obsidian-dir <tmp> --dry-run` → "Merge Plan — 4 actions" with CREATE:4 for Atlas/Dots/Things/{Attention,Layernorm,Transformer}.md + Atlas/Maps/Uncategorized.md. Exit 0. `find $TMPOUT -type f` empty — zero files written. `__main__.py:713-740` dispatch branch added by plan 05-06. |
| 3 | Running `graphify --obsidian` against a vault with no `.graphify/` directory produces backward-compatible output and all existing tests pass | VERIFIED | `pytest tests/ -q` → 872 passed in 3.42s (was 862 at initial verification; +10 from gap-closure tests). `to_obsidian()` with default profile produces Atlas/Dots/Things/ + Atlas/Maps/ layout (confirmed both by test_integration and by Truth 2's live dry-run). |

**Score:** 3/3 truths verified

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `graphify/merge.py` | `format_merge_plan` public helper | VERIFIED | Present at L1036; `_ACTION_DISPLAY_ORDER` tuple at L35 |
| `graphify/merge.py` | `split_rendered_note` public helper | VERIFIED | Present at L1098 |
| `graphify/profile.py` | `validate_profile_preflight` function + `PreflightResult` NamedTuple | VERIFIED | Both present; `PreflightResult` is a NamedTuple with `errors`, `warnings`, `rule_count`, `template_count` |
| `graphify/export.py` | Refactored `to_obsidian()` with `profile` and `dry_run` kwargs | VERIFIED | Signature confirmed: `['G', 'communities', 'output_dir', 'profile', 'community_labels', 'cohesion', 'dry_run']` |
| `graphify/__init__.py` | Lazy imports for `format_merge_plan`, `split_rendered_note`, `validate_profile_preflight`, `PreflightResult` | VERIFIED | All four entries present in `_map` dict |
| `graphify/__main__.py` | CLI handlers for `--validate-profile` and `--obsidian --dry-run` | VERIFIED | `--validate-profile` dispatch at L691-712; `--obsidian [--graph] [--obsidian-dir] [--dry-run]` dispatch at L713-740. Help text at L653-659. Wired by plan 05-06. |
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
| `__main__.py` | `validate_profile_preflight` | argparse handler | WIRED | `cmd == "--validate-profile"` branch at L694 calls `validate_profile_preflight(vault_dir)`, prints errors/warnings, `sys.exit(1 if errors else 0)` |
| `__main__.py` | `to_obsidian(dry_run=True)` | argparse handler | WIRED | `cmd == "--obsidian"` branch at L719 parses `--graph`, `--obsidian-dir`, `--dry-run`, calls `to_obsidian(..., dry_run=dry_run)`, prints `format_merge_plan(result)` |

### Data-Flow Trace (Level 4)

| Artifact | Data Variable | Source | Produces Real Data | Status |
|----------|---------------|--------|-------------------|--------|
| `to_obsidian()` | `MergeResult` | `apply_merge_plan` → `compute_merge_plan` → rendered_notes from classify+render | Yes — 872 tests pass confirming real pipeline | FLOWING |
| `to_obsidian(dry_run=True)` | `MergePlan` | `compute_merge_plan` without applying | Yes — `test_to_obsidian_dry_run_returns_plan` confirms plan.summary.CREATE > 0, plus live CLI dry-run emits 4 CREATE rows with zero files written | FLOWING |

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
|----------|---------|--------|--------|
| `--validate-profile` happy path (no `.graphify/`) | `python -m graphify --validate-profile /tmp` | "profile ok — 0 rules, 0 templates validated" (exit 0) | PASS |
| `--validate-profile` error path (broken profile) | `python -m graphify --validate-profile <bad>` | Schema errors + Windows-path warnings to stderr, exit 1, no files written | PASS |
| `--obsidian --dry-run` end-to-end | `python -m graphify --obsidian --graph <fx>.json --obsidian-dir <tmp> --dry-run` | "Merge Plan — 4 actions", CREATE:4 for Atlas/ layout, exit 0, `find $TMPOUT -type f` empty | PASS |
| Library `to_obsidian(dry_run=True)` returns MergePlan | `pytest tests/test_integration.py::test_to_obsidian_dry_run_returns_plan` (covered by full suite) | 872 passed | PASS |
| Full test suite green | `pytest tests/ -q` | 872 passed in 3.42s (was 862 at initial; +10 from 05-06 and regression coverage) | PASS |

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|------------|-------------|--------|----------|
| PROF-05 | 05-02, 05-05, 05-06 | User can run `graphify --validate-profile <vault-path>` to check profile validity without generating output | SATISFIED | `__main__.py:691-712` dispatches to `validate_profile_preflight(vault_dir)`, prints `profile ok — N rules, M templates validated` or per-error lines to stderr, and `sys.exit(1 if errors else 0)`. Verified live against both happy and error paths. |
| MRG-03 | 05-01, 05-03, 05-05, 05-06 | User can run `graphify --obsidian --dry-run` to preview all changes without writing any files | SATISFIED | `__main__.py:713-740` loads `--graph <path>.json`, calls `to_obsidian(..., dry_run=True)`, prints `format_merge_plan(result)`. Verified live: 4 CREATE rows printed, zero files written to `--obsidian-dir`. |
| MRG-05 | 05-03, 05-04, 05-05 | When no vault profile exists, output is backward-compatible with current `to_obsidian()` behavior | SATISFIED | `test_to_obsidian_default_profile_returns_merge_result` and `test_to_obsidian_default_profile_writes_atlas_layout` both pass. Default profile produces Atlas/Dots/Things/ + Atlas/Maps/ layout — confirmed independently by live dry-run against a 3-node graph fixture. |

### Anti-Patterns Found

| File | Pattern | Severity | Impact |
|------|---------|----------|--------|
| `graphify/skill.md` | `dry_run = False  # replace with True if --dry-run was passed` | Warning (by design) | D-73: CLI is utilities-only; skill is the pipeline driver. The skill embeds a Python block whose `dry_run` variable is a placeholder the invoking agent flips based on its own `--dry-run` parsing. No runtime substitution mechanism. Accepted as documented tech debt. |
| `graphify/export.py::to_obsidian` (historical) | Silent `except ValueError: continue` per-node and per-community render loops | Warning (fixed) | Closed by commit 39476f3 (WR-01) — now logs `[graphify] to_obsidian: skipping ...: <exc>` to stderr and catches `(ValueError, FileNotFoundError)`. |
| `graphify/export.py::to_obsidian` (historical) | Late `FileNotFoundError` when `output_dir` exists as a non-directory | Warning (fixed) | Closed by commit 606cb81 (WR-02) — upfront `ValueError` guard raises before the render loop. |

### Human Verification Required

None — all gaps closed deterministically by plan 05-06 and the WR-01/WR-02 code-review fixes.

### Gaps Summary

**Both gaps closed.**

Original root cause: `graphify/__main__.py` had no handlers for `--obsidian`, `--dry-run`, or `--validate-profile`. The library layer was complete and tested, but the CLI dispatcher lacked the glue branches.

Resolution:
- **Plan 05-06** (commits 9cced12, 185ef71, 967da30) added the two dispatch branches in `__main__.py` and integration tests.
- **Code-review fixes** (commits 39476f3, 606cb81) hardened the `to_obsidian()` error path (WR-01, WR-02) that was flagged after the gap-closure landed.

Re-verification evidence lives in `05-UAT.md` (7/7 verification commands pass).

### Environment Caveat (non-blocking)

The `graphify` console-script shim on this machine points to a stale `graphifyy` 0.4.1 wheel that predates the new handlers — running the bare `graphify --validate-profile /tmp` hits the stale binary and reports "unknown command". Running via `python -m graphify` from the repo picks up the editable local code (0.3.29 in pyproject.toml, which includes the new handlers) and all verification commands succeed. This is an install-environment skew, not a defect in the code delivered by Phase 5. Recommend `pip install -e ".[all]"` to re-bind the console-script entry point.

---

_Verified: 2026-04-11 (initial, gaps_found)_
_Re-verified: 2026-04-11T22:19:55Z (passed, via /gsd-verify-work 05)_
_Verifier: Claude (gsd-verifier + inline re-verification)_
