# Deferred Items — Phase 70

Items discovered during plan execution that are out of scope.

## From Plan 70-08 (reverse-sync CLI summary)

Pre-existing test failures observed when running full `pytest tests/ -q`,
unrelated to reverse_sync.py changes. Confirmed pre-existing by re-running
with the plan-08 working tree stashed (parent commit `3f29bde`).

- `tests/test_detect.py::test_detect_skips_dotfiles` — AssertionError on
  unexpected dotfile inclusion.
- `tests/test_extract.py::test_collect_files_skips_hidden` — `assert not True`
  (hidden file collection regression).
- `tests/test_migration.py::test_preview_expands_risky_action_rows` — preview
  output missing `Preserve.md` row.

These should be triaged in their own plans — they touch
`detect.py`/`extract.py`/`migration.py`, none of which plan 70-08 modifies.
