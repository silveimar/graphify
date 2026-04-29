---
phase: 40-multi-harness-memory-inverse-import-injection-defenses
plan: "05"
---

## Done

- `tests/test_harness_interchange.py::test_export_import_semantic_ids_labels_relations` — interchange export → import preserves node ids, labels, and edge relations for fixture graph (PORT-04 semantic round-trip; not byte-identical requirement).

## Verified

`pytest tests/test_harness_interchange.py::test_export_import_semantic_ids_labels_relations -q`
