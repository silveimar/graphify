# Deferred Items — Phase 62

## Pre-existing test failure (out of scope for plan 62-03)

`tests/test_migration.py::test_preview_expands_risky_action_rows` fails on
clean main (verified by `git stash` round-trip during 62-03 execution on
2026-05-04). Failure is unrelated to plan 62-03 (pure test addition); should
be triaged via `/gsd-debug` in a follow-up phase.
