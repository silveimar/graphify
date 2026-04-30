# Phase 49 — Pattern Map

## PATTERN MAPPING COMPLETE

| New / touched | Role | Closest analog |
|---------------|------|----------------|
| `graphify/version.py` | tiny stdlib metadata reader | `harness_interchange._package_version` (to be inlined then removed) |
| CLI flags in `__main__.py` | argv dispatch | `tests/test_main_cli.py::_run_cli`, `--validate-profile` branch |
| stderr diagnostics | user messaging | `_check_skill_version` existing `warning:` lines |
