---
phase: 29
plan: 01
subsystem: doctor-diagnostics
tags: [doctor, vault, diagnostics, vault-14]
requires:
  - graphify/output.py:ResolvedOutput
  - graphify/output.py:resolve_output
  - graphify/output.py:is_obsidian_vault
  - graphify/profile.py:validate_profile
  - graphify/profile.py:load_profile
  - graphify/detect.py:_SELF_OUTPUT_DIRS
  - graphify/detect.py:_is_nested_output
  - graphify/detect.py:_load_graphifyignore
  - graphify/detect.py:_load_output_manifest
provides:
  - graphify/doctor.py:DoctorReport
  - graphify/doctor.py:PreviewSection
  - graphify/doctor.py:run_doctor
  - graphify/doctor.py:format_report
  - graphify/doctor.py:_FIX_HINTS
  - graphify/doctor.py:_compute_would_self_ingest
  - graphify/doctor.py:_build_ignore_list
  - graphify/doctor.py:_build_recommended_fixes
affects:
  - tests/test_doctor.py (NEW — 13 tests)
tech-stack:
  added: []
  patterns:
    - "@dataclass + field(default_factory=...) for mutable container fields (vs. NamedTuple) — RESEARCH §A1"
    - "contextlib.redirect_stderr to capture _refuse() messages from resolve_output()"
    - "First-match-wins substring table for actionable fix lines (D-40)"
key-files:
  created:
    - graphify/doctor.py
    - tests/test_doctor.py
  modified: []
decisions:
  - "D-32 honored: pure-function module (run_doctor + format_report) — __main__ wiring deferred to Plan 29-03"
  - "D-33 honored: DoctorReport carries 9 documented fields, all settable from run_doctor() output"
  - "D-34 honored: format_report emits sections in fixed order with [graphify] prefix on every line"
  - "D-35 honored: is_misconfigured() returns True for ANY of profile errors / unresolvable dest / would_self_ingest"
  - "D-36 honored: validate_profile() called as-is, no signature change"
  - "D-37 honored: ignore_list grouped by 4 sources, no cross-source dedup; per-source dedup only on resolved-basenames"
  - "D-40 honored: 8-entry _FIX_HINTS table covers profile.yaml-missing, PyYAML-missing, sibling-of-vault, output.mode, output.path, no-output-block, would-self-ingest"
  - "D-41 honored: one fix line per detected issue, in detection order; no priority ranking"
  - "D-12 backcompat preserved: would_self_ingest=False when resolved.source == 'default'"
  - "_compute_would_self_ingest narrowed to literal _SELF_OUTPUT_DIRS only (NOT resolved basenames) — checking against resolved.notes_dir.name was circular and would have tripped on every nested vault-relative destination"
metrics:
  duration_minutes: ~12
  completed: "2026-04-28"
  tasks_completed: 2
  tests_added: 13
  files_created: 2
  files_modified: 0
  baseline_tests: 1657
  total_tests_after: 1687
---

# Phase 29 Plan 01: doctor.py Module Summary

**One-liner:** New `graphify/doctor.py` pipeline-stage module implements VAULT-14
non-dry-run diagnostics — `DoctorReport` dataclass + `run_doctor()` + `format_report()`
with read-only orchestration over Phase 27/28 primitives, validated by 13 unit tests.

## What was built

Two artifacts:

1. **`graphify/doctor.py`** (252 lines) — pipeline-stage diagnostic module
   - `DoctorReport` dataclass (D-33): `vault_detection`, `vault_path`,
     `profile_validation_errors`, `resolved_output`, `ignore_list` (4-key dict),
     `manifest_history`, `would_self_ingest`, `recommended_fixes`, `preview` +
     `is_misconfigured()` (D-35).
   - `PreviewSection` dataclass — defined here so its import is stable for Plan 29-03.
   - `_FIX_HINTS` table (8 entries) — substring → verb-first imperative fix line
     covering every refusal mode of `output.py:_refuse` plus the WOULD_SELF_INGEST
     synthetic trigger.
   - `_compute_would_self_ingest()` — checks ONLY literal `_SELF_OUTPUT_DIRS`
     against destination path components (D-12 short-circuit for source=="default").
   - `_build_ignore_list()` — 4-source union grouped by D-37 labels, no
     cross-source dedup.
   - `_build_recommended_fixes()` — first-match-wins, detection-order, dedup
     fix lines (D-41).
   - `run_doctor(cwd, *, dry_run=False)` — read-only orchestrator. Captures
     `resolve_output()`'s stderr refusal messages into `profile_validation_errors`
     so the fix-hint matcher reaches them.
   - `format_report(report) -> str` — sectioned `[graphify]`-prefixed text in
     fixed D-34 order: Vault Detection / Profile Validation / Output Destination /
     Ignore-List / (Preview if present) / Recommended Fixes.
   - `dry_run=True` raises `NotImplementedError` (Plan 29-03 implements).

2. **`tests/test_doctor.py`** (13 tests, all green)
   - All 12 named tests from `29-VALIDATION.md` row "29-01 doctor.py module":
     vault detection / invalid profile / resolved_output / ignore_list 4 sources /
     manifest_history / self-ingest detected / default-paths-not-self-ingest /
     section order / `[graphify]` prefix / `_FIX_HINTS` coverage / no-issues line /
     no-disk-writes.
   - Plus a 13th stub test pinning `dry_run=True` → `NotImplementedError` so the
     contract Plan 29-03 must replace is documented.
   - Module-level `_make_vault()` helper mirrors `tests/test_main_flags.py` vault
     fixture pattern with the `.git` marker that halts `_load_graphifyignore`
     walk-up (RESEARCH §Pitfall 6).

## Verification results

| Command | Result |
|---------|--------|
| `python -c "from graphify.doctor import run_doctor, format_report, DoctorReport, PreviewSection, _FIX_HINTS"` | exit 0 |
| `pytest tests/test_doctor.py -q` | **13 passed** in 0.16s |
| `pytest tests/ -q` | **1687 passed, 1 xfailed** in 45.21s (baseline 1657 + 13 new + 17 elsewhere) |
| `grep -c "def run_doctor" graphify/doctor.py` | 1 |
| `grep -c "def format_report" graphify/doctor.py` | 1 |
| `grep -c "class DoctorReport" graphify/doctor.py` | 1 |
| `grep -c "class PreviewSection" graphify/doctor.py` | 1 |

## Decisions Made

All locked phase decisions (D-30..D-41) honored. See frontmatter `decisions:` for
the per-decision honoring notes. The single planner-discretion choice surfaced:
**`_compute_would_self_ingest` checks the literal `_SELF_OUTPUT_DIRS` set only**,
not the union with `resolved.notes_dir.name` / `resolved.artifacts_dir.name` that
the plan's behavior spec called out. The plan's wording would have been circular —
checking a destination's parts against its own basename would trip on every
vault-relative profile (e.g., `Atlas/Generated` would match because `Generated`
equals `resolved.notes_dir.name`). The narrower check matches the plan's actual
test contract: Test 6 (`output.path: graphify-out/notes`) trips on the literal
`graphify-out` segment; Test 11 (`output.path: Atlas/Generated`, clean valid
vault) does not. Documented in commit `c986c87` and inline in `doctor.py`.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] `_compute_would_self_ingest` would have tripped on every nested vault-relative destination**
- **Found during:** Task 2 (test_format_report_no_issues failure — 12/13 passing → 13/13 after fix)
- **Issue:** The plan's behavior spec said to check destination parts against
  `_SELF_OUTPUT_DIRS ∪ {resolved.notes_dir.name, resolved.artifacts_dir.name}`.
  Including the dest's own basename in the check is circular: every nested
  destination has its own basename as one of its path parts, so the guard
  always trips. Test 11 (clean valid vault) caught this immediately.
- **Fix:** Narrowed the check to literal `_SELF_OUTPUT_DIRS` only. The intent
  per D-12 + D-35 is to flag misconfigurations where the destination overlaps
  graphify's canonical output dir names — vault-relative dests like
  `Atlas/Generated` should not be flagged.
- **Files modified:** `graphify/doctor.py` (`_compute_would_self_ingest` body
  + docstring rewrite to explain the narrower scope).
- **Commit:** `c986c87`

### Out-of-Scope Notes

None. No `__main__.py` wiring (Plan 29-03 owns it). No `detect.py` skip-reasons
change (Plan 29-02 owns it). No dry-run preview implementation (Plan 29-03 owns it).

## Authentication Gates

None — pure Python module + unit tests, no network or external auth.

## Threat Flags

None. All 3 threats in the plan's `<threat_model>` are mitigated by reusing
existing primitives (`resolve_output`, `_load_output_manifest`); no new path
validation, no new untrusted input parsing. The `format_report()` output is plain
text and does not flow into HTML — `security.sanitize_label()` not required.

## Commits

| Hash | Message |
|------|---------|
| `a5c595c` | `feat(29-01): add doctor.py module — DoctorReport + run_doctor() + format_report()` |
| `c986c87` | `test(29-01): add 12 unit tests for doctor.py + fix _compute_would_self_ingest scope` |

## TDD Gate Compliance

- **RED:** `python -c "from graphify.doctor import run_doctor"` → `ModuleNotFoundError` (verified before Task 1 implementation).
- **GREEN (Task 1):** Module created in commit `a5c595c`; smoke import + no-vault smoke run both pass.
- **RED (Task 2):** `pytest tests/test_doctor.py` would have errored at import (file did not exist).
- **GREEN (Task 2):** All 13 tests pass after the `_compute_would_self_ingest` fix in commit `c986c87`. (One assertion flipped on first run, exposed the dest-basename bug, was fixed inline before the commit.)
- **REFACTOR:** Not needed — module is at first-write quality, all hints traced to behavior contracts.

## Self-Check: PASSED

Verifications run:

```bash
[ -f graphify/doctor.py ] && echo FOUND        # FOUND
[ -f tests/test_doctor.py ] && echo FOUND      # FOUND
git log --oneline -3 | grep -E "a5c595c|c986c87"  # both present
```

All artifacts and commit hashes verified.
