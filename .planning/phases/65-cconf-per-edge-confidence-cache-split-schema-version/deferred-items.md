# Deferred items (Phase 65)

## Pre-existing test failure unrelated to Phase 65 scope

- `tests/test_migration.py::test_preview_expands_risky_action_rows` fails on `main` independent of any Phase 65 change. Verified by stashing 65-01 changes and re-running; failure persists. Risky action rows (Preserve/Conflict/Replace/Orphan) are no longer expanded in the compact migration preview. Out of scope for Phase 65 (CCONF) — track in a separate hygiene phase / migration owner.
