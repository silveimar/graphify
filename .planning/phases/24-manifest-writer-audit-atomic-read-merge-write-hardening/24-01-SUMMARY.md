---
phase: 24-manifest-writer-audit-atomic-read-merge-write-hardening
plan: "01"
subsystem: manifest-writers
tags: [manifest, atomic, read-merge-write, subpath-isolation, tdd]
dependency_graph:
  requires: []
  provides: [routing-audit-read-merge-write, capability-read-merge-write, subpath-isolation-tests]
  affects: [graphify/routing_audit.py, graphify/capability.py]
tech_stack:
  added: []
  patterns: [read-merge-write keyed by row identity, try/except-on-corrupt-json, last-write-wins merge]
key_files:
  created:
    - tests/test_routing_audit.py
  modified:
    - graphify/routing_audit.py
    - graphify/capability.py
    - tests/test_capability.py
    - tests/test_vault_promote.py
decisions:
  - "D-02: routing.json merge key is file path (str); self._files always wins on collision"
  - "D-04: capability.json merge key is tool name; incoming data always wins on collision"
  - "D-08: anchor comments referencing MANIFEST-09/10 added at each patched write site"
  - "No validate_manifest() call inside write_manifest_atomic (Pitfall 4 — would break test_atomic_manifest_roundtrip which passes minimal dicts)"
  - "Corrupt/missing on-disk JSON treated as empty via try/except (json.JSONDecodeError, OSError) — no crash"
metrics:
  duration_seconds: 259
  completed_date: "2026-04-27"
  tasks_completed: 3
  files_modified: 5
requirements_completed: [MANIFEST-09, MANIFEST-10, MANIFEST-11]
---

# Phase 24 Plan 01: Manifest Writer Audit + Atomic Read-Merge-Write Hardening Summary

**One-liner:** Patched `RoutingAudit.flush` and `write_manifest_atomic` to perform read-merge-write keyed by row identity (file path / tool name) before atomic `.tmp + os.replace` commit, preventing subpath-scoped runs from erasing sibling manifest rows.

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 | Wave 0 RED — three subpath-isolation tests | 580595d | tests/test_routing_audit.py (new), tests/test_capability.py, tests/test_vault_promote.py |
| 2 | Patch RoutingAudit.flush (GREEN routing) | a78ed90 | graphify/routing_audit.py |
| 3 | Patch write_manifest_atomic (GREEN capability + full suite) | 2e83f3f | graphify/capability.py |

## TDD Gate Compliance

- RED gate: `test(24-01)` commit `580595d` — two tests failing before implementation
- GREEN gate: `fix(24-01)` commits `a78ed90` and `2e83f3f` — all three subpath tests pass after patches
- REFACTOR: none needed

## Changes Made

### graphify/routing_audit.py — RoutingAudit.flush

Before: `payload = {"version": 1, "files": dict(sorted(self._files.items()))}` — blind overwrite.

After: `dest` defined before merge block; existing `routing.json` read and `files` dict extracted; merged with `{**existing, **self._files}` (last-write-wins by path); corrupt/missing JSON treated as empty via `try/except (json.JSONDecodeError, OSError)`.

### graphify/capability.py — write_manifest_atomic

Before: `payload = json.dumps(data, ...)` — blind overwrite.

After: existing `capability.json` read; `CAPABILITY_TOOLS` list indexed by `tool["name"]`; incoming tools overlaid with `{**existing_tools, **incoming_tools}` (last-write-wins by tool name); per-entry `isinstance(t, dict) and "name" in t` guard skips malformed entries; corrupt/missing JSON treated as empty. Top-level keys (`manifest_version`, `graphify_version`) taken from incoming `data`.

### tests/test_routing_audit.py (new file)

One test: `test_subpath_isolation_routing` — two sequential `flush()` calls with disjoint file sets; asserts union is preserved.

### tests/test_capability.py (appended)

One test: `test_subpath_isolation_capability_manifest` — two sequential `write_manifest_atomic()` calls with disjoint tool sets; asserts union is preserved.

### tests/test_vault_promote.py (appended)

One test: `test_subpath_isolation_vault_manifest` — two `_load_manifest`/`_save_manifest` round-trips; locks existing compliant contract in vault_promote.

## Verification

- `pytest tests/test_routing_audit.py tests/test_capability.py tests/test_vault_promote.py -q` — 55 passed
- `pytest tests/ -q` — 1581 passed, 1 xfailed
- Three subpath isolation tests collected and passing: `test_subpath_isolation_routing`, `test_subpath_isolation_capability_manifest`, `test_subpath_isolation_vault_manifest`
- MANIFEST-09/10 anchor comments present in both patched writers (confirmed via grep)

## Policy Alignment

Both patched writers now match `vault_promote._save_manifest` reference semantics:
- Read existing on-disk manifest (if any)
- Merge incoming rows on top (last-write-wins)
- Atomic commit via `.tmp + os.replace`
- Corrupt on-disk JSON treated as empty, never crashes pipeline

## Deviations from Plan

None — plan executed exactly as written.

## Self-Check: PASSED

Files confirmed present:
- `tests/test_routing_audit.py` — EXISTS
- `graphify/routing_audit.py` — EXISTS (modified)
- `graphify/capability.py` — EXISTS (modified)

Commits confirmed present:
- `580595d` (test RED) — FOUND
- `a78ed90` (routing GREEN) — FOUND
- `2e83f3f` (capability GREEN + full suite) — FOUND
