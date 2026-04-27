# Deferred Items — Phase 23

## Pre-existing test failures (out of scope for DEDUP fix)

Discovered during 23-01-03 full-suite sweep on 2026-04-27. Both fail
identically before and after the dedup patch — unrelated to phase 23.

- `tests/test_detect.py::test_detect_skips_dotfiles` — AssertionError on dotfile detection
- `tests/test_extract.py::test_collect_files_from_dir` — `assert 0 > 0` (no files collected)

These should be triaged in a separate phase. Do NOT block phase 23 close.
