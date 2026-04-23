---
phase: 12-heterogeneous-extraction-routing
plan: "02"
subsystem: cache
tags: [ROUTE-04, sha256, cache-key]

requires: []
provides:
  - file_hash(path, model_id) with ROUTE-04 string format; sanitized model_id
affects: [extract, semantic cache]

tech-stack:
  added: []
  patterns: ["legacy 64-char hex when model_id empty", "hashed filename when key contains ':'"]

key-files:
  created: []
  modified: ["graphify/cache.py", "tests/test_cache.py"]

key-decisions:
  - "Reject model_id with path segments or '..' (T-12-02)"

patterns-established:
  - "Cache key = inner SHA256 + optional ':model_id'; filesystem-safe JSON basename via secondary hash when needed"

requirements-completed: [ROUTE-04]

duration: —
completed: 2026-04-17
---

# Phase 12 — Plan 02 Summary

**Per-model cache isolation via `file_hash(..., model_id)` and threaded semantic cache helpers without breaking default `model_id=""` behavior.**

## Accomplishments

- `load_cached` / `save_cached` / `cached_files` aligned with new key format.
- `save_semantic_cache` / `check_semantic_cache` accept optional `model_id`.

## Self-Check: PASSED

`pytest tests/test_cache.py -q`; full suite `1257 passed`.
