---
phase: 70.1-vfix-nested-vault-folder-bug-and-output-obsidian-dir-profile
verified: 2026-05-05T23:12:00Z
status: passed
score: 7/7 must-haves verified
overrides_applied: 0
---

# Phase 70.1: VFIX Nested-Vault-Folder + Output/Obsidian-Dir Profile — Verification Report

**Phase Goal:** Close VFIX-01 (nested-vault-folder bug in `--obsidian-dir` path resolution) and VFIX-02 (document + annotate the precedence chain `--output > profile > --obsidian-dir > legacy default` across all user-visible surfaces).

**Verified:** 2026-05-05T23:12:00Z
**Status:** passed
**Re-verification:** No — initial verification

## Goal Achievement

### Observable Truths

| #   | Truth                                                                                                                                          | Status     | Evidence                                                                                                          |
| --- | ---------------------------------------------------------------------------------------------------------------------------------------------- | ---------- | ----------------------------------------------------------------------------------------------------------------- |
| 1   | RED regression matrix exists locking VFIX-01 invariants                                                                                        | ✓ VERIFIED | `tests/test_output_path_matrix.py` exists with 7 tests; pytest reports `7 passed in 0.22s`                        |
| 2   | Doubled-`<vault>/<vault>` segment bug fixed in `to_obsidian` (relative `--obsidian-dir <vault>` from parent cwd)                               | ✓ VERIFIED | `graphify/export.py:599` resolves `out = Path(output_dir)` early; Test 7 (the dedicated UAT70 reproducer) passes  |
| 3   | `--obsidian` dispatch (`__main__.py`) resolves relative `obsidian_dir` to absolute and conditionally loads its profile preserving D-08         | ✓ VERIFIED | `graphify/__main__.py:1875–1885` shows `user_passed_obsidian_dir` branch with `Path(obsidian_dir).resolve()`      |
| 4   | Precedence chain documented in README with "Nested vault folder" pitfall callout                                                               | ✓ VERIFIED | `README.md` contains canonical phrase `--output > profile > --obsidian-dir`                                       |
| 5   | CLI `--help` references precedence chain in both per-flag and global notes blocks                                                              | ✓ VERIFIED | `python -m graphify --help` emits 3 precedence-related lines including "avoid nested-vault pitfall"               |
| 6   | All 7 platform skill files (`skill.md`, `skill-codex.md`, `-opencode`, `-claw`, `-droid`, `-trae`, `-windows`) carry the canonical paragraph   | ✓ VERIFIED | `grep -lF '--output > profile > --obsidian-dir'` matches all 7 skill files + README (8 total)                     |
| 7   | Profile examples annotated with precedence + pitfall guidance                                                                                  | ✓ VERIFIED | Both `profile-example.yaml` and `profile-example-complete.yaml` contain "Output destination precedence" + "Common pitfall" markers |

**Score:** 7/7 truths verified

### Required Artifacts

| Artifact                            | Expected                                                       | Status      | Details                                                       |
| ----------------------------------- | -------------------------------------------------------------- | ----------- | ------------------------------------------------------------- |
| `tests/test_output_path_matrix.py`  | 7 RED→GREEN tests covering cwd × --obsidian-dir × profile      | ✓ VERIFIED  | All 7 pass                                                    |
| `graphify/export.py`                | `to_obsidian` resolves relative `output_dir` early             | ✓ VERIFIED  | Line 599 `out = Path(output_dir)` (per plan-02 fix)           |
| `graphify/__main__.py`              | dispatch resolves relative `--obsidian-dir` + profile fallback | ✓ VERIFIED  | Lines 1875–1885 implement `user_passed_obsidian_dir` branch   |
| `README.md`                         | precedence section + nested-vault callout                      | ✓ VERIFIED  | Canonical phrase present                                      |
| `graphify/skill*.md` (×7)           | canonical paragraph mirrored                                   | ✓ VERIFIED  | All 7 files match                                             |
| `profile-example.yaml`              | output: block + precedence comment                             | ✓ VERIFIED  | Contains both markers; valid YAML                             |
| `profile-example-complete.yaml`     | precedence comment above existing output: stub                 | ✓ VERIFIED  | Contains both markers; valid YAML                             |

### Key Link Verification

| From                              | To                                | Via                                              | Status   |
| --------------------------------- | --------------------------------- | ------------------------------------------------ | -------- |
| `__main__.py` --obsidian dispatch | `to_obsidian` (export.py)         | resolved absolute `obsidian_dir` forwarded       | ✓ WIRED  |
| `to_obsidian` `out` path          | `_validate_target(target, vault)` | absolute path prevents doubled-segment join      | ✓ WIRED  |
| README §Output destination prec.  | profile-example*.yaml comments    | cross-reference text "See README §..."           | ✓ WIRED  |

### Behavioral Spot-Checks

| Behavior                                | Command                                              | Result            | Status   |
| --------------------------------------- | ---------------------------------------------------- | ----------------- | -------- |
| Output-path matrix tests pass           | `pytest tests/test_output_path_matrix.py -q`         | `7 passed`        | ✓ PASS   |
| CLI emits precedence in help            | `python -m graphify --help \| grep -i precedence`    | 3 matching lines  | ✓ PASS   |
| Profile examples are valid YAML         | `python -c "yaml.safe_load(open(...))"`              | exit 0            | ✓ PASS   |
| Canonical phrase appears in 8 surfaces  | `grep -lF '--output > profile > --obsidian-dir'`     | README + 7 skills | ✓ PASS   |

### Anti-Patterns Found

None. No TODO/FIXME/placeholder/stub markers introduced in the modified files for this phase scope.

### Human Verification Required

None — all goal artifacts are programmatically verifiable (test pass/fail, grep markers, YAML parse, CLI help output).

### Gaps Summary

No gaps. Both VFIX-01 (path-resolution bug) and VFIX-02 (documentation + profile-example annotation of the precedence chain) are fully delivered:

- VFIX-01: Closed by Plan 70.1-01 (RED matrix) + Plan 70.1-02 (GREEN fix in `export.py` + `__main__.py`); the dedicated UAT70 reproducer (Test 7) flips RED→GREEN.
- VFIX-02: Closed by Plan 70.1-03 (README + CLI --help + 7 skill files) + Plan 70.1-04 (both profile-example YAMLs annotated).

A pre-existing failure in `tests/test_migration.py::test_preview_expands_risky_action_rows` is documented as out-of-scope (verified independent of this phase via `git stash` per plan-02 summary).

---

_Verified: 2026-05-05T23:12:00Z_
_Verifier: Claude (gsd-verifier)_
