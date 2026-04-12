# Phase 3 Deferred Items

## Pre-existing worktree-path test failures (out of scope)

**Discovered:** Plan 03-01 execution, 2026-04-11

Two tests fail when run in a path containing `.claude/` (e.g. the worktree
directory `.claude/worktrees/agent-aedf90f6/`):

- `tests/test_detect.py::test_detect_skips_dotfiles` — asserts `'/.' not in f`,
  but every fixture path contains `.claude/` in the worktree.
- `tests/test_extract.py::test_collect_files_from_dir` — depends on
  `collect_files(FIXTURES)` returning non-empty, but `collect_files` filters
  out any path containing a dot-directory, which now includes every worktree
  file.

**Root cause:** Tests assume the repo is never checked out at a path containing
a dot-directory. This is a legacy environment assumption, not a regression
from Plan 03-01.

**Action:** Deferred. Fix is unrelated to Phase 3 and belongs in a separate
cleanup pass (either relax the dotfile filter when the fixture root itself
contains a dot, or mark the tests xfail when running inside `.claude/`).
