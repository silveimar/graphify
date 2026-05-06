---
phase: 64-audit-a-stderr-format-snapshot-lock-sweep
plan: "01"
title: "AUDIT-02 stderr Snapshot Lock — Golden Fixture + Test (TDD)"
one-liner: "TDD golden snapshot locks [graphify] error:/info: two-line stderr contract via byte-exact fixture and strict D-04 prefix whitelist"
subsystem: testing
tags: [audit, stderr, snapshot, tdd, contract]
dependency-graph:
  requires: []
  provides: [stderr-contract-fixture, test-stderr-contract]
  affects: [graphify/output.py (contract surface)]
tech-stack:
  added: []
  patterns: [pytest capsys, golden fixture, snapshot testing]
key-files:
  created:
    - tests/fixtures/stderr_contract.txt
    - tests/test_stderr_contract.py
  modified: []
decisions:
  - "D-01: Golden fixture at tests/fixtures/stderr_contract.txt — three blank-line-separated sections (error, info, option_b)"
  - "D-04: Strict prefix whitelist enforced in test_strict_prefix_whitelist — only [graphify] error:, [graphify] info:, [graphify] hint:, and   hint: allowed"
  - "Option B fixture section uses /private/tmp/vault/.graphify-out/ (macOS realpath of /tmp/vault) — path is hard-coded fixture, not real data"
metrics:
  duration: "~10 minutes"
  completed: "2026-05-06"
  tasks_completed: 2
  tasks_total: 2
  files_created: 2
  files_modified: 0
requirements: [AUDIT-02]
---

# Phase 64 Plan 01: AUDIT-02 stderr Snapshot Lock — Golden Fixture + Test (TDD) Summary

## One-liner

TDD golden snapshot locks `[graphify] error:/info:` two-line stderr contract via byte-exact fixture and strict D-04 prefix whitelist.

## What Was Built

A pytest snapshot test module (`tests/test_stderr_contract.py`) with 4 tests that drive existing emitters in `graphify/output.py` and assert byte-exact stderr output against a golden fixture file (`tests/fixtures/stderr_contract.txt`).

The fixture contains three blank-line-separated sections:
1. `_emit_vault_error("vault refused: profile invalid", "fix profile.yaml")` output
2. `_emit_vault_info("vault routing", "see docs")` output
3. `emit_option_b_breadcrumb(Path("/tmp/vault"))` output

The `test_strict_prefix_whitelist` test enforces D-04 — every non-empty fixture line must match `^(\[graphify\] (error|info|hint): |  hint: )`. Any future emitter drift or new prefix added without updating the contract will fail CI.

## TDD Gate Compliance

- RED gate: commit `18f1f8b` — `test(64-01): RED snapshot test for stderr contract (AUDIT-02)` — empty fixture causes all 4 tests to FAIL
- GREEN gate: commit `48a6d6c` — `test(64-01): GREEN -- lock stderr contract snapshot (AUDIT-02)` — populated fixture, all 4 tests PASS
- REFACTOR gate: not needed (no implementation code written, test-only plan)

## Deviations from Plan

None - plan executed exactly as written.

Minor: the docstring escape sequence warning (`\[`) was fixed during RED gate creation (changed to raw string style) — this was a correctness fix on the test file itself before committing.

## Self-Check: PASSED

- tests/fixtures/stderr_contract.txt: EXISTS
- tests/test_stderr_contract.py: EXISTS
- commit 18f1f8b: EXISTS (RED gate)
- commit 48a6d6c: EXISTS (GREEN gate)
- pytest tests/test_stderr_contract.py exits 0: VERIFIED
- grep -c "^\[graphify\] " tests/fixtures/stderr_contract.txt returns 3: VERIFIED
- No emitter source files modified: VERIFIED (git diff --name-only graphify/ is empty for this plan)
