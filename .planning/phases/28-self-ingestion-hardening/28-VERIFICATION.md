---
phase: 28-self-ingestion-hardening
verified: 2026-04-27T23:59:00Z
status: passed
score: 4/4
overrides_applied: 0
re_verification: false
---

# Phase 28: Self-Ingestion Hardening — Verification Report

**Phase Goal:** Re-running graphify inside a vault never re-ingests its own previous output, even across profile changes or unconventional output paths.
**Verified:** 2026-04-27T23:59:00Z
**Status:** PASSED
**Re-verification:** No — initial verification

---

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | `detect.py` prunes the profile's resolved output destination plus any declared exclusion globs from the input scan | VERIFIED | `detect.py:461-469` builds `resolved_basenames` from `resolved.notes_dir.name` + `resolved.artifacts_dir.name`; `exclude_globs` merged into `all_ignore_patterns` at line 469; `_is_ignored()` called at line 508 and 544 |
| 2 | Paths matching `**/graphify-out/**` at any nesting depth are refused as ingestion candidates and prior nesting is reported as a warning | VERIFIED | `_is_nested_output()` at `detect.py:273-283` checks `_SELF_OUTPUT_DIRS = {"graphify-out","graphify_out"}` AND resolved basenames; scan loop at `detect.py:510-512` appends to `nested_paths` and prunes; single-line warning at `detect.py:523-529` |
| 3 | The current run's manifest records every output path it wrote, and a subsequent run reads that manifest and skips those paths even when the profile output destination has changed | VERIFIED | `_save_output_manifest()` at `detect.py:385-439` writes atomic `output-manifest.json`; `_load_output_manifest()` at `detect.py:363-382` reads it; `detect()` at `detect.py:477-480` loads all prior `files` into `prior_files`; line 547 silently skips any file whose resolved path is in `prior_files` |
| 4 | A user who renames their output directory in `profile.yaml` between two runs does not see the previous run's notes re-ingested as "documents" | VERIFIED | D-26: manifest anchored to stable `artifacts_dir` (sibling-of-vault per D-11); D-27: old `files:` entries from prior run (different `notes_dir`) are in `prior_files` and silently skipped; exercised by `test_detect_renamed_notes_dir_no_re_ingest` at `tests/test_detect.py:593-617` |

**Score:** 4/4 truths verified

---

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `graphify/detect.py` | nesting guard + exclude_globs + manifest read/write | VERIFIED | 659 lines; all Phase 28 logic present: `_is_nested_output()` L273, `_load_output_manifest()` L363, `_save_output_manifest()` L385, manifest-aware `detect()` L442 |
| `graphify/output.py` | `ResolvedOutput.exclude_globs` field | VERIFIED | `ResolvedOutput` NamedTuple at L24-30; `exclude_globs: tuple[str, ...] = ()` at L30; populated at L170-171 from `profile.output.exclude` |
| `graphify/profile.py` | `output.exclude` schema validation (D-17) | VERIFIED | Lines 453-475: validates `exclude` is a list of non-empty, non-absolute, non-traversal strings |
| `graphify/__main__.py` | `_save_output_manifest()` called after export | VERIFIED | `--obsidian` branch: L1407-1409; `run` branch: L2172-2175 |
| `tests/test_detect.py` | Phase 28 test coverage | VERIFIED | Lines 304-630+: 17 dedicated tests for VAULT-11, VAULT-12, VAULT-13 |

---

### Key Link Verification

| From | To | Via | Status | Details |
|------|-----|-----|--------|---------|
| `output.py:ResolvedOutput` | `detect.py:detect()` | `resolved` kwarg | WIRED | `detect()` signature at L442 accepts `resolved: ResolvedOutput | None`; TYPE_CHECKING import at L14 |
| `output.py:ResolvedOutput.exclude_globs` | `detect.py:_is_ignored()` | `all_ignore_patterns` merge at L469 | WIRED | `exclude_globs: list[str] = list(resolved.exclude_globs) if resolved else []` then appended to ignore patterns |
| `detect.py:_is_nested_output()` | scan loop | called at L510 | WIRED | `elif _is_nested_output(d, resolved_basenames): nested_paths.append(...); pruned.add(d)` |
| `detect.py:_load_output_manifest()` | `detect()` prior_files | called at L478 | WIRED | `manifest_data = _load_output_manifest(resolved.artifacts_dir)` feeds `prior_files` set |
| `detect.py:prior_files` | file inclusion check | L547 | WIRED | `if prior_files and str(p.resolve()) in prior_files: continue` |
| `__main__.py` | `_save_output_manifest()` | post-export call | WIRED | Both `--obsidian` and `run` branches call `_save_output_manifest(resolved.artifacts_dir, resolved.notes_dir, written)` |
| `profile.py:validate_profile()` | `output.exclude` schema | L453-475 | WIRED | D-17 strict validation integrated into existing validate-first pattern |

---

### Data-Flow Trace (Level 4)

| Artifact | Data Variable | Source | Produces Real Data | Status |
|----------|---------------|--------|-------------------|--------|
| `detect.py:detect()` | `prior_files` | `_load_output_manifest(resolved.artifacts_dir)` reading `output-manifest.json` | Yes — real file paths written by prior runs | FLOWING |
| `detect.py:detect()` | `exclude_globs` | `resolved.exclude_globs` from `output.py:resolve_output()` reading `profile.yaml` | Yes — profile-declared glob strings | FLOWING |
| `detect.py:detect()` | `resolved_basenames` | `resolved.notes_dir.name`, `resolved.artifacts_dir.name` | Yes — derived from real resolved paths | FLOWING |

---

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
|----------|---------|--------|--------|
| exclude_globs prunes matching files | `pytest tests/test_detect.py::test_detect_exclude_globs_prunes_files -q` | 1 passed | PASS |
| nesting guard emits single warning | `pytest tests/test_detect.py::test_detect_nesting_guard_summary_emits_once -q` | 1 passed | PASS |
| manifest round-trip | `pytest tests/test_detect.py::test_save_and_load_output_manifest_round_trip -q` | 1 passed | PASS |
| renamed notes_dir no re-ingest | `pytest tests/test_detect.py::test_detect_renamed_notes_dir_no_re_ingest -q` | 1 passed | PASS |
| FIFO cap at N=5 | `pytest tests/test_detect.py::test_save_output_manifest_fifo_caps_at_5 -q` | 1 passed | PASS |
| atomic write + OSError cleanup | `pytest tests/test_detect.py::test_save_output_manifest_atomic_no_partial_on_oserror -q` | 1 passed | PASS |

---

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|-------------|-------------|--------|---------|
| VAULT-11 | 28-01-PLAN.md | Profile-aware exclusions: `detect.py` prunes output destination + declared globs | SATISFIED | `ResolvedOutput.exclude_globs` (output.py L30), profile schema D-17 (profile.py L453-475), `detect()` L461-469 applying globs |
| VAULT-12 | 28-02-PLAN.md | Recursive nesting guard at any depth, warn user | SATISFIED | `_is_nested_output()` detect.py L273-283, nesting loop detect.py L503-513, single warning detect.py L523-529 |
| VAULT-13 | 28-03-PLAN.md | Manifest records output paths; subsequent run skips them regardless of profile changes | SATISFIED | `_save_output_manifest()` detect.py L385-439, `_load_output_manifest()` detect.py L363-382, `prior_files` skip at detect.py L547 |

---

### D-14..D-29 Decision Trace

| Decision | Description | Implementation | Status |
|----------|-------------|----------------|--------|
| D-14 | `exclude_globs: tuple[str, ...]` in `ResolvedOutput`, co-located under `output:` block | `output.py:30` — `exclude_globs: tuple[str, ...] = ()`; populated at L170-171 | TRACED |
| D-15 | Exclusions apply regardless of `--output` CLI flag override | `detect.py:468` — `exclude_globs` applied whenever `resolved is not None`; not gated on `resolved.source` | TRACED |
| D-16 | Reuse existing `fnmatch`-based `_is_ignored()` for glob matching | `detect.py:468-469` — `exclude_globs` appended to `all_ignore_patterns`; `_is_ignored()` called at L508, L544 | TRACED |
| D-17 | Strict validation: reject empty strings, non-string types, absolute paths, traversal | `profile.py:453-475` — all four cases validated with distinct error messages | TRACED |
| D-18 | Guard matches `_SELF_OUTPUT_DIRS` UNION resolved basenames | `detect.py:273-283` `_is_nested_output()` checks both sets; `detect.py:461-466` builds `resolved_basenames` | TRACED |
| D-19 | Warn-and-skip, not fatal, when nesting detected | `detect.py:503-513` — prunes from scan and continues; `detect.py:523-529` — warning only, no `sys.exit` | TRACED |
| D-20 | One summary warning line per run (not per-file) | `detect.py:471,510-512,523-529` — accumulate `nested_paths`, emit single line with count + deepest | TRACED |
| D-21 | Guard applies with or without vault | `detect.py:501` — `if not in_memory_tree:` applies to all scan roots; `resolved_basenames` gracefully empty when `resolved=None` | TRACED |
| D-22 | New dedicated `output-manifest.json` in `artifacts_dir`, separate from incremental `manifest.json` | `detect.py:262` — `_OUTPUT_MANIFEST_NAME = "output-manifest.json"`; stored at `artifacts_dir / _OUTPUT_MANIFEST_NAME` | TRACED |
| D-23 | Schema: `version`, `runs[]` with `run_id`, `timestamp`, `notes_dir`, `artifacts_dir`, `files` | `detect.py:407-413` — `new_run` dict with all 5 fields; L423 wraps in `{"version": ..., "runs": ...}` | TRACED |
| D-24 | Rolling N=5 FIFO cap | `detect.py:263` — `_OUTPUT_MANIFEST_MAX_RUNS = 5`; L421 — `runs = runs[-_OUTPUT_MANIFEST_MAX_RUNS:]` | TRACED |
| D-25 | Missing manifest → silent; malformed JSON → one warning to stderr + empty envelope | `detect.py:371` — missing returns `{"version": 1, "runs": []}`; L378-382 — malformed prints warning, returns empty | TRACED |
| D-26 | Stable anchor: always read from `resolved.artifacts_dir` (sibling-of-vault, stable across `notes_dir` renames) | `detect.py:478` — `_load_output_manifest(resolved.artifacts_dir)` | TRACED |
| D-27 | Silent skip of files from prior run's `files:` array (no warning on rename) | `detect.py:546-548` — `if prior_files and str(p.resolve()) in prior_files: continue` | TRACED |
| D-28 | GC stale file entries on manifest write | `detect.py:416-418` — `run["files"] = [f for f in run.get("files", []) if Path(f).exists()]` | TRACED |
| D-29 | Atomic write: tmp + fsync + os.replace; cleanup .tmp on OSError; called only after successful export | `detect.py:426-438` — tmp path, fsync, `os.replace`; OSError cleanup L433-438; `__main__.py:1407-1409` and `L2172-2175` — post-export only | TRACED |

---

### Anti-Patterns Found

| File | Pattern | Severity | Impact |
|------|---------|----------|--------|
| `__main__.py:2175` | `written_files=[]` in `run` branch | Info | By design — the `run` command does corpus extraction only (no Obsidian export); written files are recorded by the `--obsidian` path. D-29 note in code comments confirms this is intentional. |

No blockers found. The `written_files=[]` in the `run` branch is explicitly documented in the surrounding comment (`# roots only; full file list recorded via --obsidian path`).

---

### Human Verification Required

None. All success criteria are verifiable programmatically. The nesting warning (`[graphify] WARNING: ...`) is exercised by `test_detect_nesting_guard_summary_emits_once` via `capsys`.

---

## Summary

Phase 28 goal is achieved. All four success criteria are VERIFIED with line-number evidence:

1. **SC-1 (VAULT-11):** `detect.py:461-469` builds `resolved_basenames` + merges `exclude_globs` into `all_ignore_patterns`. Profile schema validation in `profile.py:453-475` enforces D-17. Exercised by 3 `test_detect_exclude_globs_*` tests.

2. **SC-2 (VAULT-12):** `_is_nested_output()` at `detect.py:273-283` checks `_SELF_OUTPUT_DIRS` union resolved basenames at any scan depth; accumulated in `nested_paths`; single summary warning at `detect.py:523-529`. Exercised by 4 `test_detect_nesting_guard_*` tests plus the pre-existing `test_detect_skips_graphify_out_at_any_depth`.

3. **SC-3 (VAULT-13):** `_save_output_manifest()` writes atomic `output-manifest.json` with all exported file paths; `detect()` loads it via `_load_output_manifest()` and builds `prior_files` set; line 547 skips any file in `prior_files`. Exercised by 8 `output-manifest` tests.

4. **SC-4 (VAULT-13 + D-26/D-27):** Stable `artifacts_dir` anchor means the manifest survives `notes_dir` renames in `profile.yaml`; prior `files:` entries are silently skipped regardless of which `notes_dir` the current run uses. Directly exercised by `test_detect_renamed_notes_dir_no_re_ingest`.

All 16 decisions (D-14..D-29) are fully traced in code. Full test suite: **1674 passed, 1 xfailed, 8 warnings**.

---

_Verified: 2026-04-27T23:59:00Z_
_Verifier: Claude (gsd-verifier)_
