---
phase: 15-async-background-enrichment
plan: 04
subsystem: mcp-serve-overlay
tags: [mcp, overlay, serve, reload-if-stale, mtime, enrichment, read-time-merge, augmentation, alias-read]
wave: 3
requirements_completed:
  - ENRICH-08
  - ENRICH-09
  - ENRICH-12
depends_on: [15-02, 15-03]
dependency_graph:
  requires:
    - graphify/enrich.py::_validate_enrichment_envelope  # shape guard (Plan 01/03)
    - graphify/enrich.py::PASS_NAMES                      # pass-key vocabulary (Plan 01)
    - graphify/serve.py::_load_dedup_report                # D-16 alias_map source
    - graphify/serve.py::_load_graph                       # unchanged; overlay runs AFTER
  provides:
    - graphify/serve.py::_load_enrichment_overlay          # NEW in-place merge helper
    - graphify/serve.py::_reload_if_stale                  # extended with _enrichment_mtime watch
  affects:
    - all MCP tool handlers that read G.nodes[*] attributes  # now transparently see
                                                            # enriched_description /
                                                            # community_summary /
                                                            # staleness_override
tech-stack:
  added: []
  patterns:
    - "read-side alias resolve via alias_map.get(nid, nid) before G.nodes[...] lookup (D-16 read-side)"
    - "augmentation-not-replacement attribute naming (enriched_* / *_override) to preserve base fields (D-06)"
    - "dual-mtime watcher pattern in _reload_if_stale (graph.json + enrichment.json tracked independently)"
    - "in-memory overlay merge — graph.json on disk byte-identical before/after (T-15-02 mitigation)"
key-files:
  created: []
  modified:
    - graphify/serve.py        # +98/-2: _load_enrichment_overlay + _reload_if_stale extension + startup wiring
    - tests/test_serve.py      # +178: 5 new tests for overlay merge / mtime / alias / no-op
decisions:
  - "Overlay is applied in-memory on G only; serve.py never imports to_json/_write_graph_json (T-15-02)"
  - "D-06 attribute naming: overlay writes enriched_description / community_summary / staleness_override; base description / staleness are never mutated"
  - "D-16 read-side: every node_id key from enrichment.json threaded through _load_dedup_report alias_map before G.nodes lookup; unknown ids silently dropped (no phantom nodes)"
  - "enrich._validate_enrichment_envelope reused as the read-side shape guard — malformed envelopes no-op"
  - "Missing enrichment.json is a no-op (not an error) — existing tests that mock _load_graph keep passing without fixture changes"
  - "patterns pass resolves each pattern.nodes list through alias_map too (consistency with per-node passes)"
metrics:
  duration_min: ~18
  tasks_completed: 2
  files_created: 0
  files_modified: 2
  lines_added: 276
  tests_added: 5
  completed_date: 2026-04-22
---

# Phase 15 Plan 04: Serve Overlay Merge-on-Read Summary

Wired `enrichment.json` as an in-memory overlay on the NetworkX graph served by the MCP layer so every `G`-consuming handler (`get_node`, `graph_context`, `entity_trace`, etc.) transparently surfaces LLM-derived content without mutating `graph.json` on disk.

## What shipped

### `_load_enrichment_overlay(G, out_dir)` (module-level in `graphify/serve.py`)

Reads `<out_dir>/enrichment.json` and applies the four passes onto `G` in-place:

| Pass            | Overlay write target                      | Base field preserved |
|-----------------|-------------------------------------------|----------------------|
| `description`   | `G.nodes[nid]["enriched_description"]`    | `description`        |
| `community`     | `G.nodes[nid]["community_summary"]` (fanned to every node whose `community` matches) | — |
| `staleness`     | `G.nodes[nid]["staleness_override"]`      | `staleness`          |
| `patterns`      | `G.graph["patterns"]` (graph-level list; per-pattern `nodes` also alias-resolved) | — |

**Invariants enforced:**
- Missing file → no-op (keeps Phase 1-10 mocked-`_load_graph` tests unchanged).
- Malformed envelope → `_validate_enrichment_envelope` rejects → no-op with stderr trace.
- Every `node_id` key → `alias_map.get(nid, nid)` → `G.nodes` membership check before write; phantom ids silently skipped.
- Idempotent: repeated calls with the same `enrichment.json` produce identical `G` state.

### `_reload_if_stale()` extension

Now tracks `_enrichment_mtime` alongside `_graph_mtime`. Branches:
1. `graph.json` mtime changed → reload `G` + re-apply overlay + refresh both mtimes.
2. `graph.json` unchanged, `enrichment.json` mtime changed → re-apply overlay only (ENRICH-09).
3. Neither changed → return immediately (unchanged fast-path).

### `serve()` startup wiring

Immediately after `G = _load_graph(graph_path)` and the existing `_alias_map` load, `_load_enrichment_overlay(G, _out_dir)` runs once, and `_enrichment_mtime` is initialized from disk (0.0 when absent).

## D-06 Augmentation Rule Table

| Attribute               | Source                              | Overwrites base? | Read by handler as                                   |
|-------------------------|-------------------------------------|------------------|------------------------------------------------------|
| `description`           | `_load_graph` (base graph.json)     | —                | `G.nodes[n]["description"]`                          |
| `enriched_description`  | overlay (`passes.description`)      | **No**           | prefer `nattrs.get("enriched_description") or nattrs.get("description")` |
| `staleness`             | `_load_graph` / delta pipeline      | —                | `G.nodes[n]["staleness"]`                            |
| `staleness_override`    | overlay (`passes.staleness`)        | **No**           | prefer `nattrs.get("staleness_override") or nattrs.get("staleness")` |
| `community_summary`     | overlay (`passes.community`, fanned)| N/A (new attr)   | `G.nodes[n]["community_summary"]`                    |
| `patterns` (graph-level)| overlay (`passes.patterns`)         | N/A (new attr)   | `G.graph.get("patterns", [])`                        |

Plan 05 foreground lock and Plan 06 dry-run + invariant tests inherit this naming.

## Tests added (5)

All in `tests/test_serve.py`, appended after the existing focus tests:

- `test_load_enrichment_overlay` — base `description` preserved; `enriched_description` set; nodes without base description get overlay-only attribute.
- `test_overlay_augments_not_overwrites` — `staleness`/`staleness_override` coexist; `community_summary` fanned across nodes by community id; `G.graph["patterns"]` set from graph-level list.
- `test_reload_if_stale_enrichment` — overlay re-applied on mtime bump; `os.stat(graph_path).st_mtime` asserted unchanged before/after (T-15-02 invariant proof).
- `test_overlay_alias_redirect_on_read` — D-16/ENRICH-12: overlay entry keyed by alias redirects to canonical node; overlay entry for phantom id silently skipped; no new nodes added to `G`.
- `test_overlay_missing_file_noop` — no `enrichment.json` on disk → `G` unchanged; preserves backward compatibility of all existing mocked-`_load_graph` tests.

## Threat-model outcomes

| Threat ID | Disposition after plan |
|-----------|-------------------------|
| T-15-01 (torn read of enrichment.json) | mitigated — `_validate_enrichment_envelope` rejects partial/malformed envelopes; writer side (Plan 02) atomically flips via `os.replace` so readers only ever see a fully-committed snapshot |
| T-15-02 (graph.json mutation via overlay) | **mitigated and test-enforced** — `test_reload_if_stale_enrichment` asserts `os.stat(gp).st_mtime` is unchanged across overlay refresh; no new `to_json` / `_write_graph_json` import added to serve.py |
| T-15-03 (HTML-injected overlay text) | mitigated — sanitation remains on the write side (Plan 02 `_sanitize_pass_output`); read side simply trusts the shape-validated envelope |
| T-15-05 (phantom-node injection via crafted `node_id`) | mitigated — `test_overlay_alias_redirect_on_read` asserts unknown ids do not create phantom `G.nodes` entries |

## Commits

| Task | Type | Hash     | Message                                                    |
|------|------|----------|------------------------------------------------------------|
| 1    | test | 59db742  | test(15-04): add failing tests for _load_enrichment_overlay|
| 2    | feat | c8c0bea  | feat(15-04): wire enrichment.json overlay into MCP serve layer |

## Acceptance criteria verification

- `grep -c "_load_enrichment_overlay" graphify/serve.py` → **4** (def + startup + 2 × `_reload_if_stale`)
- `grep -c "_enrichment_mtime" graphify/serve.py` → **7**
- `from graphify.enrich import _validate_enrichment_envelope` imported inline in helper (OK)
- `alias_map.get(` present (D-16 read-side proof)
- `python -c "from graphify.serve import _load_enrichment_overlay"` → OK
- `pytest tests/test_serve.py -q` → **175 passed**
- `pytest tests/ -q` → **1352 passed, 2 warnings** (no regression)

## Open items (forwarded)

### For Plan 05 (foreground lock + watch.py trigger)
- `__main__.py` `enrich` CLI subcommand must acquire the `_acquire_lock` on enrichment PID file; this plan does not gate the writer from the reader — reader already torn-read-safe via validator + atomic replace (Plan 02).
- `watch.py` needs to avoid spuriously rebuilding on `enrichment.json` / `enrichment.tmp` / `enrichment.pid` churn; serve already handles that branch via `_reload_if_stale`.

### For Plan 06 (polish + invariants)
- Byte-equality CI test: hash `graph.json` before/after a full enrichment cycle + serve overlay refresh — must be identical (T-15-02 tightened to whole-run scope).
- `grep` guard in CI: `graphify/serve.py` must never contain a call to `to_json(` or `_write_graph_json(`.
- MCP `get_node` handler polish: explicit `nattrs.get("enriched_description") or nattrs.get("description")` preference in the response envelope (deferred to keep Plan 04 behavior-only).
- Dry-run envelope: `graphify enrich --dry-run` should print per-pass counts and exit without invoking LLM — reuses overlay validation in `--dry-run` verify mode.

## Self-Check: PASSED

- File `graphify/serve.py` exists — VERIFIED (contains `_load_enrichment_overlay` + `_enrichment_mtime`).
- File `tests/test_serve.py` exists — VERIFIED (5 new test symbols).
- Commit `59db742` (test) FOUND in `git log --oneline -5`.
- Commit `c8c0bea` (feat) FOUND in `git log --oneline -5`.
- Full suite passes (1352/1352).
