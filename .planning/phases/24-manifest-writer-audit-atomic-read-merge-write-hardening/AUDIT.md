# Manifest Writer Audit (Phase 24)

**Phase:** 24 — Manifest Writer Audit + Atomic Read-Merge-Write Hardening
**Closes:** MANIFEST-12
**Date:** 2026-04-27

## Contract

Every on-disk manifest writer in graphify MUST follow the read-merge-write contract: (1) **read** the existing file, returning `{}` or `[]` on missing/corrupt (catch `json.JSONDecodeError` and `OSError`, log to stderr if intent is to surface the recovery to users); (2) **merge** new-run rows on top of existing rows keyed by **row identity** (path / id / tool name), last-write-wins on conflict; (3) **write** to `<dest>.tmp` then `os.replace(<dest>.tmp, <dest>)` for crash-safe atomic commit. The reference implementation lives in `graphify/vault_promote.py:_save_manifest` (lines 665-682). Phase 24 brings `routing.json` and `capability.json` into compliance; `vault-manifest.json` and `seeds-manifest.json` were already compliant; `graphify-out/manifest.json` (detect.py) is documented here as DEFERRED because it is unreachable from any active CLI flow today.

**Migration policy (D-08):** No migration code. On first read after the v1.6 upgrade, the patched writers treat whatever's on disk as authoritative and merge the new run's rows on top. Users with pre-v1.6 manifests missing sibling-subpath rows recover by **re-running on the missing subpaths**; the union accumulates after each run. There is no `graphify manifest rebuild` CLI and no auto-detection / stderr warning for stale state — both are deferred as new capabilities.

## Writer Inventory

| manifest filename | writer (file:function:line) | invocation site | row identity key | pre-fix read? | pre-fix atomic? | post-fix read? | post-fix atomic? | Phase 24 action |
|---|---|---|---|---|---|---|---|---|
| `vault-manifest.json` | `graphify/vault_promote.py:_save_manifest:665` (also `graphify/merge.py:_save_manifest:1085`) | `vault_promote.promote()` and `merge.apply_merge_plan()` | `path` (note path; dict key) | YES (caller loads via `_load_manifest`) | YES (`.tmp` + `os.replace` + `fsync`) | YES (unchanged) | YES (unchanged) | LOCKED — already compliant; regression test added (`tests/test_vault_promote.py::test_subpath_isolation_vault_manifest`) |
| `seeds-manifest.json` | `graphify/seed.py:_save_seeds_manifest:114` | `seed.build_all_seeds()` | `seed_id` (caller deduplicates before save) | YES (caller loads via `_load_seeds_manifest`) | YES (`.tmp` + `os.replace` + `fsync`) | YES (unchanged) | YES (unchanged) | LOCKED — already compliant; documented for completeness |
| `routing.json` | `graphify/routing_audit.py:RoutingAudit.flush:34` | `pipeline.py:run()` (after extract phase) | file path string (dict key in `files`) | NO (blind overwrite of `self._files`) | YES (`.tmp` + `os.replace`) | YES (read existing, merge by file path, last-write-wins) | YES (unchanged) | PATCHED — Phase 24 Plan 01 inserted read-merge step before payload construction |
| `capability.json` | `graphify/capability.py:write_manifest_atomic:227` | `export.py:to_json():304` via `capability.write_runtime_manifest:245` | tool name (`entry["name"]` in `CAPABILITY_TOOLS`) | NO (blind overwrite) | YES (`.tmp` + `os.replace`) | YES (read existing, index by tool name, layer incoming, last-write-wins) | YES (unchanged) | PATCHED — Phase 24 Plan 01 inserted read-merge step before payload construction. This is "the MCP `manifest.json`" in ROADMAP success criterion #2 (renamed from `manifest.json` in `quick-260422-jdj`, per D-01) |
| `graphify-out/manifest.json` | `graphify/detect.py:save_manifest:447` | `graphify/detect.py:detect_incremental:460` (NOT WIRED — not invoked from any active CLI flow) | file path string (dict key) | NO | NO (direct `Path.write_text`, no `.tmp`, no `os.replace`) | NO (unchanged in Phase 24) | NO (unchanged in Phase 24) | DEFERRED — known-bad writer (blind overwrite + non-atomic). Fix is REQUIRED scope of whichever future phase wires `detect_incremental` to an active CLI flow (e.g., a `--update` mode or watch-mode hookup). DO NOT ship that wiring without first bringing this writer into the contract. |

## Test Coverage (MANIFEST-11)

| Writer | Test | File:Function |
|---|---|---|
| `vault-manifest.json` | locks existing contract | `tests/test_vault_promote.py::test_subpath_isolation_vault_manifest` |
| `routing.json` | exercises new read-merge-write | `tests/test_routing_audit.py::test_subpath_isolation_routing` |
| `capability.json` | exercises new read-merge-write | `tests/test_capability.py::test_subpath_isolation_capability_manifest` |

`seeds-manifest.json` and `graphify-out/manifest.json` (detect) are not covered by Phase 24 tests — the former is already locked by Phase 14 tests, the latter is unreachable from CLI today (and will be tested when re-wired in a future phase).
