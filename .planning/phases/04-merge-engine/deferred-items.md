# Deferred Items — Phase 04 Merge Engine

Out-of-scope issues discovered during plan execution. Not fixed inline because
they are unrelated to the plan's task boundary.

## Plan 04-02 (2026-04-11)

### Pre-existing unrelated test failures

- `tests/test_detect.py::test_detect_skips_dotfiles`
- `tests/test_extract.py::test_collect_files_from_dir` — `assert 0 > 0 (where 0 = len(files))`

Both failures reproduce on `HEAD` before any 04-02 changes are applied (verified
via `git stash && pytest -q`). They appear to be environment/fixture-related
(empty file collection) in detect + extract test suites. Unrelated to
`graphify/profile.py` and the Phase 4 merge configuration surface this plan
extends.

Action: route to a dedicated fix plan (not 04-02 scope).
