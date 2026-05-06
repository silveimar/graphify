---
phase: 63
plan: 03
subsystem: vault-option-b
tags: [vault, breadcrumb, legacy-detection, ignore-rules, vopt-02]
requires: [63-01]
provides:
  - "Third hint line in Option B breadcrumb when legacy graphify-out/ exists at vault root"
  - "Project-shipped .graphifyignore preventing graphify self-ingest of .graphify-out/ and graphify-out/"
  - "W7 behavior test that exercises real detect() discovery API to verify ignore rule wiring"
affects: [graphify/output.py, .graphifyignore, tests/test_output_path_matrix.py, tests/test_detect.py]
tech-stack:
  added: []
  patterns:
    - "Two-/three-line stderr breadcrumb via _emit_vault_info(extra_hint=...) (S1)"
    - "gitignore-style project-level ignore via .graphifyignore (parsed by graphify/detect.py:_load_graphifyignore)"
key-files:
  created:
    - .graphifyignore
  modified:
    - graphify/output.py
    - tests/test_output_path_matrix.py
    - tests/test_detect.py
decisions:
  - "D-01 third hint: '  hint: legacy graphify-out/ detected — run `graphify doctor` to review' fires only when (vault/'graphify-out').is_dir()"
  - "D-04 detect-only confirmed: legacy dir contents untouched (test asserts iterdir() == [] post-resolve)"
  - "Pitfall 5 / A4 mitigation shipped via .graphifyignore (.graphify-out/ + graphify-out/)"
metrics:
  duration_minutes: ~6
  completed: 2026-05-06
  tasks_completed: 2
  files_changed: 4
  commits: 3
---

# Phase 63 Plan 03: VOPT-02 third hint line + .graphifyignore self-ingest guard Summary

VOPT-02 closed: legacy `graphify-out/` detection wired into the Option B breadcrumb as a third advisory hint, and graphify's own outputs (`.graphify-out/`, legacy `graphify-out/`) added to a project-shipped `.graphifyignore` so the next run does not re-ingest its own emitted notes.

## What landed

1. **`graphify/output.py` — `emit_option_b_breadcrumb` extended** (one ~7-line change): before calling `_emit_vault_info`, check `(vault_cwd / "graphify-out").is_dir()`. When True, set `extra = "legacy graphify-out/ detected — run \`graphify doctor\` to review"` and pass `extra_hint=extra`. Detect-only — no move, no delete, no migration (D-04).

2. **`.graphifyignore` (new, force-added)** — project-level ignore file with `.graphify-out/` and `graphify-out/` rules, plus a Phase 63 (VOPT-02) traceability comment. Force-added because the user's global gitignore (`~/.gitignore:35`) excludes `.graphify*`; the file is intentionally project-scoped.

3. **`tests/test_output_path_matrix.py` — 3 new tests** appended:
   - `test_option_b_legacy_dir_emits_third_hint`: asserts 3-line breadcrumb + detect-only contract (legacy dir still empty post-resolve).
   - `test_option_b_no_legacy_dir_two_line_breadcrumb`: regression-locks 2-line shape when legacy dir absent.
   - `test_option_b_graphify_out_in_ignore_default`: static-asset lock on shipped `.graphifyignore` content.

4. **`tests/test_detect.py` — `test_graphify_out_ignored_in_vault_cwd`** (W7): exercises real `detect()` discovery API with a vault containing `.graphify-out/obsidian/Generated.md` plus a vault-root `.graphifyignore`, asserts `doc.md` is discovered and no `.graphify-out` paths leak into the corpus.

## `.graphify` prefix audit (Pitfall 5 / A4)

**Result: clean — no tightening needed.**

`grep -n "\.graphify" graphify/detect.py graphify/security.py` shows all prefix matches use a trailing slash (`.graphify/` at detect.py:419 and detect.py:563), so they cannot over-match `.graphify-out/`. No code change required; A4 confirmed.

## ROADMAP acceptance walk-through (criteria 1–4)

| # | Criterion | Status | Evidence |
|---|-----------|--------|----------|
| 1 | Vault CWD with `.obsidian/` + no profile → outputs under `<vault>/.graphify-out/` | PASS | Plan 01 + 03; `test_option_b_vault_no_profile_reroutes_to_hidden`, `test_option_b_paths_are_absolute` |
| 2 | Exactly one breadcrumb (2 lines without legacy, 3 lines with legacy) | PASS | `test_option_b_breadcrumb_shape` (2-line), `test_option_b_legacy_dir_emits_third_hint` (3-line), `test_option_b_idempotent_across_calls` (single emission) |
| 3 | `--explain-paths` prints table, exits 0, no pipeline run | PASS | Plan 02 — `tests/test_explain_paths.py` |
| 4 | Non-vault CWDs continue to use `default_graphify_artifacts_dir()` | PASS | `pytest tests/test_routing_audit.py tests/test_output.py -q` → 38 passed |

## Verification

- `pytest tests/test_output_path_matrix.py -k option_b -q` → 9 passed
- `pytest tests/test_output_path_matrix.py::test_option_b_graphify_out_in_ignore_default tests/test_detect.py::test_graphify_out_ignored_in_vault_cwd -q` → 2 passed
- `pytest tests/test_routing_audit.py tests/test_output.py -q` → 38 passed (Success Criterion #4 regression canary clean)
- `pytest tests/ -q --ignore=tests/test_migration.py` → 2259 passed, 1 xfailed (test_migration.py excluded per pre-existing unrelated failure noted in project memory 5920)
- `grep -n "legacy graphify-out/ detected" graphify/output.py` → 1 match (line 152)
- `grep -c ".graphify-out/" .graphifyignore` → 1; `grep -c "graphify-out/" .graphifyignore` → 2 (covers both)
- `grep -c "test_graphify_out_ignored_in_vault_cwd" tests/test_detect.py` → 1

## Commits

| Hash | Subject |
|------|---------|
| `fd429c0` | test(63-03): RED — failing legacy graphify-out/ detection tests |
| `f63c0bd` | feat(63-03): GREEN — legacy graphify-out/ detection emits third hint line (VOPT-02) |
| `7c4d036` | chore(63-03): add .graphify-out/ to .graphifyignore + final Phase 63 regression sweep |

## Deviations from Plan

**1. [Rule 3 - Blocking]** `.graphifyignore` is excluded by the user's global gitignore (`/Users/silveimar/.gitignore:35: .graphify*`). Used `git add -f` to force-add the project-shipped file, since the plan requires it to ship in the repo. Documented in the commit message. No code change needed; user's global config is unchanged.

Otherwise: plan executed exactly as written.

## Forward pointer

**Phase 64 (AUDIT-A) stderr snapshot lock:** The future audit test that snapshots breadcrumb prefixes will need to widen its valid-prefix list from `error:` only to **`error: | info:`** so the new `_emit_vault_info` two-/three-line shape is included. With Plan 03 landed, both 2-line and 3-line `info:` variants are now valid emissions and must be in scope for the snapshot.

## TDD Gate Compliance

- RED gate: `fd429c0` (`test(63-03): RED ...`) — test_option_b_legacy_dir_emits_third_hint observed failing before implementation.
- GREEN gate: `f63c0bd` (`feat(63-03): GREEN ...`) — both new tests pass after implementation.
- REFACTOR: not needed — minimal patch site, no cleanup.

## Self-Check: PASSED

- FOUND: graphify/output.py (line 152: legacy graphify-out/ detected)
- FOUND: .graphifyignore (.graphify-out/ + graphify-out/)
- FOUND: tests/test_output_path_matrix.py (3 new tests)
- FOUND: tests/test_detect.py (test_graphify_out_ignored_in_vault_cwd)
- FOUND: commit fd429c0
- FOUND: commit f63c0bd
- FOUND: commit 7c4d036
