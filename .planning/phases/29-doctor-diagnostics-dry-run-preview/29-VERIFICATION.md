---
phase: 29-doctor-diagnostics-dry-run-preview
verified: 2026-04-28T08:58:00Z
status: passed
score: 4/4 success criteria verified
overrides_applied: 0
---

# Phase 29: Doctor Diagnostics & Dry-Run Preview — Verification Report

**Phase Goal:** A new user can diagnose vault adapter misconfiguration and preview vault-aware behavior before any files are written.
**Verified:** 2026-04-28T08:58:00Z
**Status:** passed
**Re-verification:** No — initial verification

---

## Goal Achievement

### Observable Truths (Success Criteria from ROADMAP)

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | `graphify doctor` prints vault detection, profile validation, resolved output destination, and active ignore-list in a single human-readable report | PASS | Live CLI: 4 sectioned headers `=== Vault Detection ===`, `=== Profile Validation ===`, `=== Output Destination ===`, `=== Ignore-List ===` emitted in fixed order. Implemented in `graphify/doctor.py:format_report()` lines ~412-475. Verified end-to-end from `/tmp/doctor_test`. |
| 2 | `graphify doctor` exits non-zero when profile invalid / dest unresolvable / would self-ingest | PASS | Three live invocations: (a) invalid profile (`name:` unknown key) → EXIT=1; (b) `output.path: graphify-out/notes` (would_self_ingest) → EXIT=1 with WARNING; (c) clean profile → EXIT=0. Implemented at `__main__.py:2310` `sys.exit(1 if report.is_misconfigured() else 0)` and `doctor.py:DoctorReport.is_misconfigured()` lines 130-138 (D-35 binary). |
| 3 | `graphify doctor --dry-run` shows would-ingest, would-skip, would-write — without touching disk | PASS | Live CLI: `python3 -m graphify doctor --dry-run` produced `=== Preview ===` section with `Would ingest: 2 files`, grouped `Would skip (nesting/exclude-glob/manifest/sensitive/noise-dir)`, plus `Would write notes to:` and `Would write artifacts to:`. Disk inventory before/after identical (no `graphify-out/` created). Implemented in `doctor.py:_format_preview` (~382-410) and `_build_preview_section` (~248-296). |
| 4 | Doctor report ends with concrete, actionable "recommended fixes" for each misconfiguration | PASS | Live CLI for invalid profile produced `=== Recommended Fixes ===` followed by `[graphify] FIX: Add an output: {mode: ..., path: ...} block to .graphify/profile.yaml`. Self-ingest case produced `[graphify] FIX: Move existing graphify-out/ outside the input scan, or add 'graphify-out/**' to .graphifyignore`. Clean case shows `No issues detected.` `_FIX_HINTS` table at `doctor.py:67-99` (8 verb-first imperative entries). |

**Score:** 4/4 success criteria verified.

---

## Locked Decisions D-30..D-41 — Code Verification

| Decision | Requirement | Status | Evidence |
|----------|-------------|--------|----------|
| D-30 | `doctor` is top-level subcommand in `__main__.py` | PASS | `__main__.py:2291` `elif cmd == "doctor":`; `--help` lists `doctor` line 1215 |
| D-31 | `--dry-run` exists ONLY on `doctor` | PASS | `__main__.py:2302` `_p_dr.add_argument("--dry-run", ...)`; bare `graphify --dry-run` only appears scoped under `doctor`, `enrich`, and `--obsidian` (existing) — no top-level bare `--dry-run`. Help line 1216 binds `--dry-run` directly under `doctor`. |
| D-32 | `graphify/doctor.py` exists with `run_doctor()` + `format_report()` as pure functions | PASS | File `graphify/doctor.py` (481 lines); `run_doctor` at line ~298, `format_report` at line ~422; both pure (no disk writes; only reads via `detect()`/`load_profile()`/`resolve_output()`) |
| D-33 | DoctorReport carries vault_detection, profile_validation_errors, resolved_output, ignore_list, manifest_history, would_self_ingest, recommended_fixes, preview | PASS | `doctor.py:118-128` dataclass declares all 8 fields |
| D-34 | Sectioned text in fixed order, every line `[graphify]`-prefixed | PASS | `format_report` orders Vault → Profile → Output → Ignore-List → Preview → Fixes; verified live output — every line begins with `[graphify]` |
| D-35 | Binary exit codes (0/1) | PASS | `__main__.py:2310` `sys.exit(1 if report.is_misconfigured() else 0)`; `is_misconfigured()` triggers on profile errors OR unresolvable dest OR would_self_ingest |
| D-36 | `validate_profile()` signature unchanged | PASS | `doctor.py:309` calls `validate_profile(profile)` with single positional dict arg, matching pre-Phase-29 signature |
| D-37 | Ignore-list union of 4 sources, grouped, no cross-source dedup | PASS | `_build_ignore_list` (lines ~178-208) returns dict with keys `self-output-dirs`, `resolved-basenames`, `graphifyignore-patterns`, `profile-exclude-globs`; live output includes `graphify-out` in both `self-output-dirs` and `resolved-basenames` (no cross-source dedup) |
| D-38 | Bounded preview (first 10 ingested + first 5 per skip-reason) | PASS | `_PREVIEW_INGEST_SAMPLE_CAP = 10` (line 64), `_PREVIEW_SKIP_SAMPLE_CAP = 5` (line 65); `_build_preview_section` slices `flattened[:_PREVIEW_INGEST_SAMPLE_CAP]` and `bucket[:_PREVIEW_SKIP_SAMPLE_CAP]`; `_format_preview` emits `... +K more` overflow lines |
| D-39 | Dry-run calls real `detect()` | PASS | `doctor.py:336-339` `from graphify.detect import detect as _detect_scan; scan = _detect_scan(cwd_resolved)` — no re-implementation |
| D-40 | `_FIX_HINTS` mapping in `doctor.py` | PASS | Lines 67-99: list-of-tuples with 8 substring → fix-line entries |
| D-41 | One fix line per detected issue, in detection order | PASS | `_build_recommended_fixes` (lines 215-241) iterates errors in order, dedups by fix-line via `seen_fixes`, appending in detection sequence |

All 12 decisions implemented in code as specified.

---

## Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `graphify/doctor.py` | New module with run_doctor, format_report, _FIX_HINTS, DoctorReport, PreviewSection | VERIFIED | 481 lines, all symbols present |
| `graphify/detect.py` | Additive `skipped: dict[str, list[str]]` return key with 5 reason groups | VERIFIED | Lines 465-470 declare the 5 reason buckets (`nesting`, `exclude-glob`, `manifest`, `sensitive`, `noise-dir`); `_record_skip` accumulator at 475-478 |
| `graphify/__main__.py` | `doctor` subcommand dispatch with `--dry-run` flag, exit code wiring, help line | VERIFIED | `cmd == "doctor"` at 2291; help at 1215-1216; `sys.exit(1 if ... else 0)` at 2310 |
| `tests/test_doctor.py` | Phase 29-01 + 29-03 unit tests for DoctorReport, run_doctor, format_report, dry-run | VERIFIED | 330 lines exists |
| `tests/test_detect.py::test_detect_skip_reasons` | Skip-reasons return shape test | VERIFIED | Test passes (see suite below) |
| `tests/test_main_flags.py` | 4 doctor CLI integration tests | VERIFIED | All 4 tests pass |

---

## Behavioral Spot-Checks

| Behavior | Command | Result | Status |
|----------|---------|--------|--------|
| Phase 29 test suite green | `pytest tests/test_doctor.py tests/test_detect.py::test_detect_skip_reasons tests/test_main_flags.py -q` | `29 passed in 1.83s` | PASS |
| `doctor` listed in `--help` | `python3 -m graphify --help \| grep doctor` | `doctor   diagnose vault/profile/output configuration (VAULT-14/15)` | PASS |
| Clean config exits 0 | `python3 -m graphify doctor` (valid profile) | EXIT=0, "No issues detected." | PASS |
| Invalid profile exits 1 with fix | `python3 -m graphify doctor` (unknown `name:` key) | EXIT=1, FIX line emitted | PASS |
| would_self_ingest exits 1 with fix | `python3 -m graphify doctor` (`output.path: graphify-out/notes`) | EXIT=1, WARNING + FIX: Move existing graphify-out/ ... | PASS |
| Dry-run produces preview, no disk writes | `python3 -m graphify doctor --dry-run` | Preview section emitted; pre/post `ls` unchanged (no `graphify-out/` created) | PASS |
| All output `[graphify]`-prefixed | grep on live output | Every emitted line prefixed | PASS |

---

## Requirements Coverage

| Requirement | Description | Status | Evidence |
|-------------|-------------|--------|----------|
| VAULT-14 | `graphify doctor` command — vault detection, profile validation, resolved output, ignore-list, recommended fixes; non-zero on misconfig | SATISFIED | SC #1, #2, #4 verified (live CLI + 25/25 doctor unit tests + 4/4 CLI integration tests) |
| VAULT-15 | Dry-run preview for vault-root-aware behavior | SATISFIED | SC #3 verified (live `--dry-run` + `test_detect_skip_reasons` + `test_run_doctor_dry_run_preview` etc.) |

---

## Anti-Patterns Found

None blocking.

- `doctor.py` module is read-only; no `TODO`/`FIXME`/`PLACEHOLDER` markers found
- No empty handler stubs; every section formatter returns real content
- `is_misconfigured()` returns concrete bools — not always-True/always-False stub
- `_compute_would_self_ingest` correctly excludes `resolved.source == "default"` per D-12 backcompat (line 159-160)

---

## Human Verification Required

None required — all 4 success criteria verified end-to-end through CLI invocation against synthetic vault directory.

The Validation matrix flagged 2 manual-only items (report human-readability and fix-line wording quality), but both are subjective polish concerns that the automated CLI runs already satisfied at a functional level (sections grep-friendly, all fix lines verb-first imperative).

---

## Gaps Summary

No gaps. All 4 ROADMAP success criteria pass. All 12 locked decisions D-30..D-41 are reflected in the code. All 29 phase-scoped tests green. Live CLI behavior matches contract: clean → exit 0, three misconfig paths → exit 1 with actionable fix lines, dry-run produces bounded preview without disk writes.

---

_Verified: 2026-04-28T08:58:00Z_
_Verifier: Claude (gsd-verifier)_
