# Deferred Items — Phase 22

## Pre-existing test failures (out of scope for plan 22-01)

Four CLI subprocess tests fail with `No module named graphify` due to a
pyenv/multi-worktree environment quirk. They predate plan 22-01 — confirmed
by `git stash` + rerun. Unrelated to Excalidraw / profile schema work:

- tests/test_delta.py::test_cli_snapshot_saves_file
- tests/test_delta.py::test_cli_snapshot_with_name
- tests/test_delta.py::test_cli_snapshot_from_to
- tests/test_enrich.py::test_cli_pass_choices

Triage owner: a future general-maintenance ticket (likely needs
`pip install -e .` in this worktree's venv or test-suite refactor away
from spawning `python -m graphify` subprocesses).
