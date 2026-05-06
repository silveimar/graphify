---
phase: 66-cfed-cross-repo-concept-federation-federate-py
plan: 02
subsystem: federate
tags: [federation, pipeline-wiring, atomic-write, vault-aware, tdd, cfed]
requires:
  - graphify/federate.py::federate
  - graphify/federate.py::build_manifest
  - graphify/output.py::default_graphify_artifacts_dir
provides:
  - graphify/build.py::build_from_json (federation-aware)
  - graphify/federate.py::write_manifest
affects:
  - graphify/build.py
tech_stack:
  added: []
  patterns: [lazy-import, atomic-temp-replace, default-off-invariant, vault-aware-routing]
key_files:
  created: []
  modified:
    - graphify/build.py
    - graphify/federate.py
    - tests/test_federate.py
    - tests/test_build.py
decisions: [D-66.1, D-66.4, D-66.5, D-66.7]
metrics:
  duration: ~5m
  tasks: 2
  tests_added: 5
  date: 2026-05-06
requirements: [CFED-01, CFED-04]
---

# Phase 66 Plan 02: build.py wiring + atomic vault-aware manifest writer — Summary

Federation engine from Plan 01 wired into `build_from_json` with strict
default-off invariant, plus `write_manifest()` writing
`federation-manifest.json` atomically through the Phase-27/63 vault-aware
output resolver.

## Tasks Completed

| Task | Name                                                     | Commit  |
| ---- | -------------------------------------------------------- | ------- |
| 1    | RED — pipeline + manifest tests (5 new)                  | f3e87ec |
| 2    | GREEN — wire federate + atomic vault-aware write_manifest | d940464 |

## Behaviors Locked by Tests

- **CFED-01 default-off (`test_build_from_json_default_off`):** without the
  `peers` kwarg, node/edge counts on the canonical fixture remain 4/4 — no
  federation code path executes.
- **CFED-04 placement (`test_pipeline_invokes_federate`):** `build_from_json`
  calls `federate()` exactly once when `peers` is non-empty, with the spy
  proving the call site fires after `_normalize_concept_code_edges` and
  before `validate_extraction` (line-order check: L228 → L235 → L247).
- **Phase 53 normalization preserved
  (`test_pipeline_preserves_concept_code_normalization`):** duplicate
  concept↔code edges still collapse to one when `peers=[]`.
- **Vault-aware path (`test_manifest_vault_aware`):** `write_manifest`
  resolves through `default_graphify_artifacts_dir(target)` — never
  hardcodes `graphify-out/`. With `monkeypatch.chdir(tmp_path)` the manifest
  lands at `<resolved>/federation-manifest.json`.
- **Atomic write (`test_manifest_atomic`):** failure-injected `os.replace`
  raises through the caller; no partial `federation-manifest.json` exists,
  no orphaned `*.tmp` siblings remain.

## Public API

```python
from graphify.build import build_from_json
from graphify.federate import write_manifest

# Default-off (existing callers unaffected)
G = build_from_json(extraction)

# Federation enabled
G = build_from_json(
    extraction,
    peers=[Path("../other_repo/graphify-out/graph.json")],
    local_repo="thisrepo",
    target_dir=Path.cwd(),          # vault-aware via default_graphify_artifacts_dir
    resolved_output=resolved,        # optional Phase 27 ResolvedOutput
)

# Standalone manifest write
out_path = write_manifest(entries, Path.cwd(), resolved=None)
```

## Pipeline Placement (CFED-04)

```python
# graphify/build.py — build_from_json
nodes_for_norm = [n for n in extraction["nodes"] if isinstance(n, dict)]
_normalize_concept_code_edges(nodes_for_norm, extraction["edges"])  # L228

if peers:                                                            # L235
    from .federate import federate, build_manifest, write_manifest
    merged_extraction, merges = federate(extraction, peers, local_repo=local_repo)
    extraction["nodes"] = list(merged_extraction.get("nodes", []))
    extraction["edges"] = [dict(e) for e in merged_extraction.get("edges", [])]
    manifest = build_manifest(merges)
    write_manifest(manifest, target_dir or Path.cwd(), resolved=resolved_output)

errors = validate_extraction(extraction)                             # L247
```

Lazy import inside the `if peers:` block keeps `graphify.federate` (and any
transitive imports it grows in future plans) out of the default import
graph.

## Atomic Writer (Phase 64 sidecar pattern, mirrored)

`write_manifest` follows `export.py::_write_repo_identity_sidecar`:
write to `<final>.tmp`, fsync, `os.replace`, and `unlink` the tmp on
`OSError`. JSON serialised with `indent=2, sort_keys=True,
separators=(",", ": ")` so re-runs produce byte-identical manifests.

## Verification

- `pytest tests/test_federate.py tests/test_build.py -x` → **22 passed**
- `pytest tests/ -q` → **2334 passed**, 1 xfailed, 1 pre-existing failure
  (`tests/test_migration.py::test_preview_expands_risky_action_rows` —
  documented out of scope per Plan 01 SUMMARY / Phase 65 deferred-items)
- `grep -n "if peers:" graphify/build.py` → matches L235 (between L228 and L247) ✓
- `grep -c "def write_manifest" graphify/federate.py` → 1 ✓
- `grep -c "default_graphify_artifacts_dir" graphify/federate.py` → 3 ✓
- `grep -c "os.replace" graphify/federate.py` → 2 ✓

## Deviations from Plan

**[Rule 2 — Test allow-list adjustment]** `tests/test_federate.py::test_no_new_deps`
allow-list extended with `"graphify.output"`. The plan did not call this
out, but `write_manifest` necessarily imports `default_graphify_artifacts_dir`
to satisfy the vault-aware criterion. This is not a new pip dependency —
`graphify.output` is an existing internal module. The allow-list spirit
(no new external deps) is preserved; entry added for transparency.

## Cross-Plan Handoff

Plan 03 (`__main__.py` CLI surface) consumes:
- `build_from_json(..., peers=[...], local_repo=..., resolved_output=...)`
  for the `--federate-with` runtime path.
- `FederationCollisionError` for two-line stderr handling.

Plan 04 (report rendering) reads the `federation-manifest.json` produced
here (path: `default_graphify_artifacts_dir(...) / "federation-manifest.json"`).

## Self-Check: PASSED

- `graphify/build.py` (modified — federation block at L235) — FOUND
- `graphify/federate.py::write_manifest` — FOUND (line: `def write_manifest`)
- `tests/test_federate.py` (4 new tests + allow-list update) — FOUND
- `tests/test_build.py::test_build_from_json_default_off` — FOUND
- Commit f3e87ec — FOUND
- Commit d940464 — FOUND

## TDD Gate Compliance

- **RED gate:** `test(66-02): add failing tests for federation pipeline integration + atomic manifest` (f3e87ec) — confirmed RED via `AttributeError: module 'graphify.federate' has no attribute 'write_manifest'` and `ImportError: cannot import name 'write_manifest'` before implementation.
- **GREEN gate:** `feat(66-02): wire federation into build pipeline + atomic vault-aware manifest writer` (d940464) — all 22 plan-scoped tests pass; full suite 2334 passed.
- **REFACTOR gate:** not needed; implementation landed clean on first iteration.
