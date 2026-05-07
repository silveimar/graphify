# Deferred Items — Phase 70.2

Discovered during execution but out-of-scope for this phase per SCOPE BOUNDARY rule.

## Pre-existing test failures (unrelated to AUDIT-02)

Confirmed pre-existing on `main` before plan 70.2-01 changes — these failures
reproduce when the working tree is reverted via `git stash`.

1. `tests/test_capability.py::test_validate_cli_zero` — capability manifest
   content-hash drift. server.json `_meta.manifest_content_hash` does not match
   the rebuilt manifest. Root cause likely: `graphify_version` or tool count
   change since the last `python scripts/sync_mcp_server_json.py` run.
2. `tests/test_main_cli.py::test_validate_profile_empty_vault_exits_0` —
   downstream of the capability/server.json drift above.
3. `tests/test_migration.py::test_preview_expands_risky_action_rows` —
   `format_migration_preview` no longer emits per-file risky-row names
   (`Preserve.md`, `Conflict.md`, `Replace.md`, `Orphan.md`) in the compact
   preview — only the action-name headers and counts. D-13 contract regression
   that is independent of stderr work.

Recommend filing as separate plan(s) in a future phase.
