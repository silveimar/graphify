# Phase 25 — Deferred Items

Items discovered during Phase 25 execution that are out-of-scope for this phase.

## Pre-existing test failures unrelated to skill-file persistence

Both failures reproduce on base commit `24810ec` (before any Phase 25 changes), so they are not caused by this phase's markdown-only edits. Per Rule 4 (Scope Boundary), they are not auto-fixed here.

| Test                                  | File                       | Notes                                                                 |
| ------------------------------------- | -------------------------- | --------------------------------------------------------------------- |
| `test_detect_skips_dotfiles`          | `tests/test_detect.py`     | AssertionError; appears unrelated to skill-file or `_PLATFORM_CONFIG`. |
| `test_collect_files_from_dir`         | `tests/test_extract.py`    | `assert 0 > 0` — likely fixture or working-directory setup issue.     |

Recommend triage in a follow-up phase or `/gsd-debug` session.
