---
phase: 40-multi-harness-memory-inverse-import-injection-defenses
plan: "04"
---

## Done

- MCP: `import_harness`, `export_harness_interchange` in `mcp_tool_registry.py`; `_tool_*` handlers in `serve.py` delegating to library code only.
- `capability_tool_meta.yaml` entries for both tools.
- `server.json` regenerated via `scripts/sync_mcp_server_json.py`.
- `SECURITY.md` harness import/export subsection + PORT/SEC traceability.
- Tests: `tests/test_mcp_harness_io.py`.

## Verified

`pytest tests/test_mcp_harness_io.py tests/test_capability.py -q`
