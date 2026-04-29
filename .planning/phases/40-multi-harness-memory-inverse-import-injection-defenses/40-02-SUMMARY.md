---
phase: 40-multi-harness-memory-inverse-import-injection-defenses
plan: "02"
---

## Done

- `security.py`: `MAX_HARNESS_IMPORT_BYTES`, `sanitize_harness_text`, `guard_harness_injection_patterns`.
- `graphify/harness_import.py`: `import_harness_path`, `import_harness_bytes`; JSON + Claude markdown parsers; path/size policy.
- Tests: `tests/test_harness_import.py` (library + strict/injection).

## Verified

`pytest tests/test_harness_import.py -q`
