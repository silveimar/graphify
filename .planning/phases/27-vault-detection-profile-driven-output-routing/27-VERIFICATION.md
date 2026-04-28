---
phase: 27-vault-detection-profile-driven-output-routing
verified: 2026-04-27T22:25:00Z
status: passed
score: 4/4 must-haves verified
overrides_applied: 0
---

# Phase 27: Vault Detection & Profile-Driven Output Routing — Verification Report

**Phase Goal:** When graphify runs from inside an Obsidian vault, it recognizes the vault and routes output to a profile-declared destination instead of dumping `graphify-out/` into the vault root.
**Verified:** 2026-04-27T22:25:00Z
**Status:** passed
**Re-verification:** No — initial verification

## Goal Achievement

### Observable Truths

| # | Truth (ROADMAP Success Criterion) | Status | Evidence |
|---|-----------------------------------|--------|----------|
| 1 | Running `graphify` from a directory containing `.obsidian/` is detected as a vault and reported in CLI output | VERIFIED | `is_obsidian_vault()` at `graphify/output.py:32-34` (strict CWD-only `.is_dir()` check, D-04). `resolve_output()` emits VAULT-08 stderr line `[graphify] vault detected at <path> — output: <path> (source=...)` (output.py:86-90, 165-169). Tested by `tests/test_main_flags.py::test_run_in_vault_emits_detection_report` and `tests/test_output.py::test_is_obsidian_vault_*` (4 cases). |
| 2 | When the vault has `.graphify/profile.yaml`, graphify auto-adopts profile-driven placement (Option C) — CWD is treated as both input corpus and output target without an explicit flag | VERIFIED | `__main__.py:1336-1340` (run branch) implements D-07: `if resolved.vault_detected and resolved.source == "profile": target = Path.cwd().resolve()`. Refusal path for missing profile / missing `output:` block at `output.py:108-122`. Tested via `test_run_in_vault_no_profile_refuses` and `test_run_in_vault_profile_no_output_block_refuses`. |
| 3 | The profile's output destination field (vault-relative path, absolute path, or sibling-of-vault) determines where notes are written | VERIFIED | Profile schema validated at `profile.py:421-451` for all 3 modes via `_VALID_OUTPUT_MODES = {"vault-relative", "absolute", "sibling-of-vault"}` (line 115). `validate_sibling_path()` (profile.py:477-518) authorizes the deliberate one-parent escape. `resolve_output()` dispatches per mode at `output.py:138-156`. Tested by `tests/test_profile.py` (20 new tests) and `tests/test_output.py` (`test_resolve_output_vault_relative_resolves`, `test_resolve_output_absolute_mode`, `test_resolve_output_sibling_of_vault_mode`). |
| 4 | The CLI `--output` flag overrides the profile's declared destination and the precedence is shown in stderr when both are present | VERIFIED | CLI parses `--output`/`--output=` in both `run` (~line 2120-2138) and `--obsidian` (~line 1311-1325) branches. `output.py:53-99` short-circuits with `cli-flag` source and emits exactly one D-09 line: `[graphify] --output=<path> overrides profile output (mode=<m>, path=<resolved>)`. Tested by `test_run_output_flag_overrides_profile_emits_d09_line` (asserts count=1) and `test_obsidian_output_flag_takes_precedence_over_obsidian_dir`. |

**Score:** 4/4 truths verified

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `graphify/profile.py` | `_VALID_OUTPUT_MODES`, `output:` schema branch, `validate_sibling_path()` | VERIFIED | Line 115 (constant), 421-451 (validate_profile output branch), 477-518 (validate_sibling_path with 5+ rejection classes incl. filesystem-root corner). |
| `graphify/output.py` | New module: `ResolvedOutput`, `is_obsidian_vault`, `resolve_output` | VERIFIED | 7130 bytes; `ResolvedOutput` NamedTuple (line 24), `is_obsidian_vault` (line 32), `resolve_output` (line 43). All wired and used (2 call sites in __main__.py). |
| `graphify/__main__.py` | `--output` flag wired into `run` and `--obsidian` branches; `resolve_output(Path.cwd(), cli_output=...)` called twice | VERIFIED | Line 1327 (--obsidian branch) and line 2142 (run branch). 2 occurrences of `resolve_output(Path.cwd()` confirmed. |
| `graphify/pipeline.py` | `run_corpus(target, *, use_router, out_dir=None)` additive kwarg | VERIFIED | Line 7 signature; line 18-19 default preserves D-12 backcompat; line 31 uses out_dir for `audit.flush`. |
| `tests/test_main_flags.py` | 9 new integration tests | VERIFIED | 9 `test_*` functions present, all passing. |
| `tests/test_output.py` | Module unit tests (21 cases) | VERIFIED | All 21 pass post-merge. |
| `tests/test_profile.py` | 20 new tests for output schema + validate_sibling_path | VERIFIED | 158 passing (was 138). |

### Key Link Verification

| From | To | Via | Status | Details |
|------|----|----|--------|---------|
| `__main__.py` (run) | `output.resolve_output` | `from graphify.output import resolve_output; resolve_output(Path.cwd(), cli_output=cli_output)` | WIRED | Line 2120-2142; result threaded into `out_dir` for `run_corpus` (line 2161). |
| `__main__.py` (--obsidian) | `output.resolve_output` | `from graphify.output import resolve_output; resolve_output(...)` | WIRED | Line 1326-1338; `resolved.notes_dir` populates `obsidian_dir`. |
| `output.resolve_output` | `profile.load_profile` | function-local import inside vault branch | WIRED | output.py:130 — lazy to avoid circular import. |
| `output.resolve_output` | `profile.validate_sibling_path` | per-mode lazy import | WIRED | output.py:153-154 — D-13 contract honored. |
| `output.resolve_output` | `profile.validate_vault_path` | per-mode lazy import | WIRED | output.py:140-141. |
| `pipeline.run_corpus` | `audit.flush(out_dir)` | additive kwarg | WIRED | pipeline.py:31. |

### Data-Flow Trace (Level 4)

| Artifact | Data Variable | Source | Produces Real Data | Status |
|----------|---------------|--------|---------------------|--------|
| `__main__.py run branch` | `out_dir` | `resolved.artifacts_dir` from `resolve_output()` | Yes — Path object computed from CWD/vault parent | FLOWING |
| `__main__.py --obsidian branch` | `obsidian_dir` | `resolved.notes_dir` (or legacy fallback) | Yes — Path resolved from profile or CLI flag | FLOWING |
| `ResolvedOutput` consumers (Phase 28/29) | `notes_dir`, `artifacts_dir` | NamedTuple immutable | Yes — `test_resolved_output_unpacks_to_tuple` confirms shape | FLOWING (contract for downstream phases) |

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
|----------|---------|--------|--------|
| Full test suite passes | `pytest tests/ -q` | 1647 passed, 1 xfailed (pre-existing) | PASS |
| Phase 27 tests pass | `pytest tests/test_main_flags.py tests/test_output.py tests/test_profile.py -q` | 188 passed, 1 xfailed | PASS |
| `validate_sibling_path` exported | `grep "^def validate_sibling_path" graphify/profile.py` | 1 match line 477 | PASS |
| `ResolvedOutput` defined | `grep "^class ResolvedOutput" graphify/output.py` | 1 match line 24 | PASS |
| `resolve_output(Path.cwd()` ≥2x in __main__.py | `grep -c` | 2 matches (lines 1327, 2142) | PASS |
| 9 tests in test_main_flags.py | `grep -c "^def test_"` | 9 | PASS |

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|-------------|-------------|--------|----------|
| VAULT-08 | 27-02, 27-03 | graphify detects when CWD is itself an Obsidian vault | SATISFIED | `is_obsidian_vault()` + stderr report line; tested by `test_run_in_vault_emits_detection_report`. |
| VAULT-09 | 27-02, 27-03 | Auto-adopt Option C — CWD is both input corpus and output target | SATISFIED | D-07 input forcing + D-05/D-02 refusal paths; tested by `test_run_in_vault_no_profile_refuses` + `test_run_in_vault_profile_no_output_block_refuses`. |
| VAULT-10 | 27-01, 27-03 | Profile output destination + CLI `--output` override | SATISFIED | `output:` schema in profile.py + `--output` flag in __main__.py + D-09 stderr line; tested by `test_run_output_flag_overrides_profile_emits_d09_line`. |

### Anti-Patterns Found

None. Spot-checked all 3 modified files for TODO/FIXME/PLACEHOLDER/empty-implementation patterns — all returns produce real Path objects, no stub fallthroughs. The `pass` statement at __main__.py:1334 is a deliberate D-08 precedence ladder (`elif user_passed_obsidian_dir: pass # honor explicit --obsidian-dir`), not a stub.

### D-12 Backcompat Verification

- Pre-existing test suite (1638 prior tests) passes unchanged — no test was modified to compensate for behavior changes.
- `output.py:101-107` returns byte-identical v1.0 paths (`Path("graphify-out/obsidian")`, `Path("graphify-out")`) when no vault and no flag.
- `pipeline.py:18-19` defaults `out_dir = target / "graphify-out"` when kwarg is None — preserving the v1.0 contract.
- Confirmed by `test_run_no_vault_no_output_no_stderr_noise` and `test_obsidian_no_vault_no_output_no_stderr_noise` (both assert empty stderr).

### D-13 Integration Contract (Phase 28 + Phase 29 readiness)

- `ResolvedOutput` NamedTuple has the 5 declared fields: `vault_detected: bool`, `vault_path: Path | None`, `notes_dir: Path`, `artifacts_dir: Path`, `source: Literal["profile", "cli-flag", "default"]`.
- Immutability verified by `test_resolved_output_is_immutable`; field order verified by `test_resolved_output_namedtuple_field_order`.
- Single import surface: `from graphify.output import ResolvedOutput, is_obsidian_vault, resolve_output` — consumable by Phase 28 (`detect.py` for self-ingest pruning) and Phase 29 (`doctor.py`).

### Human Verification Required

None. All 4 success criteria are programmatically verified via the existing test suite. No visual / real-time / external-service behavior in scope for this phase.

### Gaps Summary

No gaps. All 4 ROADMAP success criteria, all 3 requirements (VAULT-08/09/10), all artifacts, all key links, and all decisions (D-01..D-13) are present in the codebase with passing tests. The phase goal — vault recognition + profile-driven routing instead of dumping `graphify-out/` into vault root — is achieved.

---

## VERIFICATION PASSED

_Verified: 2026-04-27T22:25:00Z_
_Verifier: Claude (gsd-verifier)_
