# Deferred Items (Phase 27)


## 2026-04-27 (plan 27-02 worktree)

- `tests/test_detect.py::test_detect_skips_dotfiles` and `tests/test_extract.py::test_collect_files_from_dir` fail in this worktree because the path includes `.claude/worktrees/...` (a dotdir component). Pre-existing fixture-detection assumption; not caused by 27-02. Out of scope for this plan.
