---
phase: 49-add-version-flag-to-graphify-command-and-also-print-current
plan: "01"
subsystem: cli-version
requirements-completed:
  - CLI-VER-01
  - CLI-VER-02
completed: 2026-05-01
---

# Phase 49 Plan 01 — Summary

**Outcome:** `graphify.version.package_version()` as the single `graphifyy` metadata reader; `graphify --version` / `-V` early exit without skill sidecar noise; `_cli_exit` emits `[graphify] version` on successful CLI exits with suppression for install/uninstall/help; skill `.graphify_version` mismatch messaging refined (directional older/newer); readers migrated in `capability`, `harness_interchange`, `elicit`.

## Accomplishments

- **`graphify/version.py`** — `package_version()` with try/except → `"unknown"`.
- **`graphify/__main__.py`** — early `--version`/`-V`; `_suppress_success_version_footer`; `_cli_exit`; `_check_skill_version` tuple comparison for stamps.
- **Tests:** `tests/test_main_cli.py`, `tests/test_main_flags.py` cover `--version`, footer, suppressed paths.

## Verification

- `pytest tests/test_main_cli.py tests/test_main_flags.py tests/test_capability.py tests/test_harness_interchange.py -q` — 81 passed (2026-05-01).
- `pytest tests/ -q` — 1965 passed, 1 xfailed (2026-05-01).
