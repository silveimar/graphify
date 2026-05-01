---
status: passed
phase: 49
phase_name: CLI version, footer, skill/package validation
verified: 2026-05-01
---

# Phase 49 — Verification

## Must-haves (from plans + CONTEXT)

| Item | Evidence |
|------|----------|
| CLI-VER-01 — `--version`/`-V`, `package_version()` | `graphify/version.py`; `__main__.py` early argv; `pytest tests/test_main_flags.py` / `test_main_cli.py` |
| CLI-VER-02 — success footer, skill stamp warnings | `_cli_exit`, `_suppress_success_version_footer`, `_check_skill_version`; tests above |
| D-49.06 — missing stamp silent + CLAUDE.md | `CLAUDE.md` skill install stamp paragraph; `_check_skill_version` behavior |

## Automated

- `pytest tests/ -q` — **1965 passed**, 1 xfailed (2026-05-01).

## Gaps

- None blocking.

## human_verification

None.
