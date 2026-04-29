---
phase: 40-multi-harness-memory-inverse-import-injection-defenses
plan: "01"
---

## Done

- Added `graphify/harness_schemas/interchange_v1.schema.json` and `graphify/harness_interchange.py` (`export_interchange_v1`, `graph_data_to_extraction`).
- Extended `export_claude_harness(..., memory_format=markdown|interchange|both)`; CLI `graphify harness export --format`.
- Tests: `tests/test_harness_interchange.py`.

## Verified

`pytest tests/test_harness_interchange.py tests/test_harness_export.py -q`
