---
phase: 40-multi-harness-memory-inverse-import-injection-defenses
plan: "03"
---

## Done

- CLI `graphify import-harness PATH [--format auto|json|claude] [--strict] [--output]` writes `harness_import.json` under resolved artifacts dir.
- Stdin/URL rejected with clear message.

## Verified

`pytest tests/test_harness_import.py::test_cli_import_harness_smoke -q`
