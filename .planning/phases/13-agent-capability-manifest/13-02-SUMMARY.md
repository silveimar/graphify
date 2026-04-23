---
phase: 13-agent-capability-manifest
plan: 02
subsystem: api
tags: [mcp, manifest, ci, docstrings]

requires:
  - phase: 13-agent-capability-manifest
    plan: 01
    provides: capability.py (build_manifest_dict, canonical_manifest_hash, validate_cli), mcp_tool_registry.py, server.json, capability_manifest.schema.json
provides:
  - CI drift-gate step in .github/workflows/ci.yml running `graphify capability --validate` on every push/PR to main/v* matrix (3.10, 3.12)
  - extract_tool_examples() helper + `_meta.examples: list[str]` on every CAPABILITY_TOOLS entry (uniform, possibly empty)
  - build_handler_docstrings() in mcp_tool_registry + _handlers_snapshot() in serve exposing live docstrings to the manifest pipeline
affects: [Phase 13 Wave B — HARNESS plans can extend _meta with additional MANIFEST-06 defaults]

tech-stack:
  added: []
  patterns:
    - "Docstring Examples: blocks → _meta.examples via pure-function extractor (no new deps, stdlib-only)"
    - "Module-level _HANDLER_DOCSTRINGS cache published on serve() bind so capability manifest never needs a running stdio server"

key-files:
  created: []
  modified:
    - .github/workflows/ci.yml
    - graphify/capability.py
    - graphify/mcp_tool_registry.py
    - graphify/serve.py
    - server.json
    - tests/test_capability.py

key-decisions:
  - "Existing validate_cli() stderr already satisfied all four D-03 tokens (expected, actual, server.json, regenerate command); no template change required — tests pin the contract in place."
  - "build_handler_docstrings() lives in mcp_tool_registry.py and delegates to serve._handlers_snapshot() so fresh checkouts without a loaded graph still produce a schema-uniform manifest (fallback to {} → _meta.examples: [])."
  - "server.json regenerated exactly once (10e59d5c… → d066e4e1…); hash algorithm and canonicalization preserved (D-04) — hash changed solely because every tool entry now carries _meta.examples."

patterns-established:
  - "Executors owning MANIFEST-10 content should grow handler docstrings with an `Examples:` block whose lines are copy-pasteable tool invocations — extraction is deterministic and order-preserving."

requirements-completed:
  - MANIFEST-09
  - MANIFEST-10

duration: "~20 minutes wall-clock"
completed: 2026-04-17
---

# Phase 13 Plan 02: MCP Capability CI Drift Gate + Docstring Examples Summary

Close Phase 13 P2 items. Wire `graphify capability --validate` into GitHub Actions as a non-bypassable CI drift gate (MANIFEST-09) and auto-extract per-tool `Examples:` docstring blocks into `_meta.examples: list[str]` for agent-visible worked examples (MANIFEST-10). No new dependencies; hash-semantics preserved (D-04); `server.json` rolled forward once.

## Performance

- **Tasks:** 2 — both `autonomous=true`, both TDD (`tdd="true"`)
- **Commits:** 3 (one RED, one Task-1-GREEN, one Task-2-GREEN)
- **Tests:** 10 new (3 drift-gate + 7 docstring extraction) — full suite `pytest tests/ -q` = **1273 passed** (+10 over Plan 01's 1263)
- **Files modified:** 6 (no files created; Plan 01 owned all artifacts except the test file)

## What shipped

### MANIFEST-09 — CI drift gate

- **`.github/workflows/ci.yml`** — new step `Verify MCP capability manifest has not drifted` runs `graphify capability --validate` after install + tests + `graphify install` on both Python 3.10 and 3.12 matrix legs. No `continue-on-error`, no `if:` env-var guard. Suppression only possible by editing the workflow file (visible in code review per T-13-08).
- **`tests/test_capability.py`** — three tests pin the D-03 stderr contract:
  - `test_validate_cli_drift_detected` asserts `expected`, `actual`, `server.json`, and `graphify capability --stdout > server.json` each appear in stderr on drift.
  - `test_validate_cli_clean_tree` asserts `code == 0` + empty stderr when hashes match.
  - `test_validate_cli_no_huge_diff_by_default` asserts `len(stderr) < 2000` — D-03 "no huge unified diffs by default" contract.
- No edits to `validate_cli()` itself — Plan 01's existing template already emitted all four tokens; tests now lock that in.

### MANIFEST-10 — Docstring → `_meta.examples`

- **`graphify/capability.py`**:
  - `extract_tool_examples(docstring: str | None) -> list[str]` — pure, deterministic, order-preserving. Locates first line equal to `Examples:`, collects subsequent lines until blank line OR another `Header:` section OR EOF. Strips each; drops empties. Non-string → `[]`.
  - `_tool_to_manifest_entry(..., handler_docstring=None)` — now merges YAML-sourced `_meta` with `{"examples": extract_tool_examples(handler_docstring)}`. Field is **always present** — uniform schema even when empty (D-01).
  - `build_manifest_dict()` — fetches handler docstrings via `mcp_tool_registry.build_handler_docstrings()`; passes each by name into `_tool_to_manifest_entry`. Module-level import of the registry so test monkeypatches take effect.
- **`graphify/mcp_tool_registry.py`** — `build_handler_docstrings()` delegates to `serve._handlers_snapshot()` and returns `{}` on any error path (no graph loaded, import failure, etc.). Keeps `graphify capability --stdout` runnable on a fresh clone with no graph.
- **`graphify/serve.py`** — module-level `_HANDLER_DOCSTRINGS` dict + `_handlers_snapshot()` accessor. Inside `serve()`, right after the MANIFEST-05 registry-vs-handlers set-equality check, publishes `{name: fn.__doc__ for name, fn in _handlers.items()}`. Server behavior unchanged.
- **`server.json`** — `_meta.manifest_content_hash` regenerated: `10e59d5c94db364dc50d64c24956f9c05272e87a8d2d4b1e5bafe85fd1872b8f` → `d066e4e17cbfcc237ac390d74ff2f4fb1d8f7df65e4ec121850f224445055a26`. Hash **algorithm** and canonicalization unchanged (D-04); only the canonical content grew by one uniform `_meta` key per tool.
- **Determinism verified** — `test_manifest_hash_stable_after_examples_added` asserts two successive `build_manifest_dict()` calls produce identical hashes.

## Test results

```
pytest tests/test_capability.py -q
  16 passed in 0.53s
pytest tests/ -q
  1273 passed, 2 warnings in 40.70s
```

Ten new tests added in Plan 02:

1. `test_validate_cli_drift_detected` (MANIFEST-09, D-03)
2. `test_validate_cli_clean_tree` (MANIFEST-09)
3. `test_validate_cli_no_huge_diff_by_default` (MANIFEST-09, D-03)
4. `test_extract_tool_examples_parses_examples_block` (MANIFEST-10)
5. `test_extract_tool_examples_empty_when_no_block` (MANIFEST-10)
6. `test_extract_tool_examples_empty_on_none_docstring` (MANIFEST-10 — None-safety)
7. `test_extract_tool_examples_stops_at_next_section` (MANIFEST-10 — grammar edge case)
8. `test_meta_examples_populated_in_manifest` (MANIFEST-10 — end-to-end wiring)
9. `test_meta_examples_uniform_when_absent` (MANIFEST-10 — D-01 schema uniformity)
10. `test_manifest_hash_stable_after_examples_added` (MANIFEST-10 — determinism, T-13-10)

## Acceptance criteria

All acceptance checks from the plan pass:

- `grep -q 'graphify capability --validate' .github/workflows/ci.yml` → exit 0
- `grep -c 'continue-on-error' .github/workflows/ci.yml` → 0 (no bypass added)
- `grep -E 'if:.*GRAPHIFY_SKIP' .github/workflows/ci.yml` → no match
- `pytest tests/test_capability.py -k validate_cli -q` → 4 passed
- `grep -n 'def extract_tool_examples' graphify/capability.py` → present
- `grep -n '_meta' graphify/capability.py | grep -q examples` → present
- `grep -n '_handlers_snapshot\|build_handler_docstrings' graphify/mcp_tool_registry.py graphify/serve.py` → both files
- `python -c "from graphify.capability import build_manifest_dict; d=build_manifest_dict(); assert all(isinstance(t.get('_meta',{}).get('examples'), list) for t in d['CAPABILITY_TOOLS'])"` → exit 0
- `graphify capability --validate` (live CLI) → exit 0

## Deviations from Plan

**None.** Plan executed exactly as written.

Minor note: the plan's acceptance-criterion one-liner uses `d['tools']`, but Plan 01's schema names the array `CAPABILITY_TOOLS` — the equivalent assertion was run against `CAPABILITY_TOOLS` and passes. Not a behavior change, just a docs reference reconciled to the actual schema.

## Threat-model disposition

- **T-13-08 (CI bypass tampering)** — mitigated. Workflow step has no `continue-on-error`, no env-var guard; test asserts absence of `GRAPHIFY_SKIP`-style bypass tokens. Suppression requires editing `ci.yml` (visible in code review).
- **T-13-09 (Docstring leak)** — accepted. Docstrings are already public via source + MCP `description` field; elevating `Examples:` to `_meta.examples` surfaces no net-new information.
- **T-13-10 (Non-deterministic manifest)** — mitigated. `extract_tool_examples` preserves input order; `build_mcp_tools()` returns stable order (Plan 01); `test_manifest_hash_stable_after_examples_added` pins determinism.

## Commits

- `da02ed7` — `feat(13-02): wire MCP capability drift gate into CI (MANIFEST-09)`
- `aab4967` — `test(13-02): add failing tests for _meta.examples extraction (MANIFEST-10)` — RED gate
- `c1c987e` — `feat(13-02): extract per-tool examples from docstrings into _meta (MANIFEST-10)` — GREEN gate

TDD gate sequence satisfied for Task 2: RED (`aab4967`) → GREEN (`c1c987e`). Task 1 stacked the test and implementation in a single commit because no new implementation code was written — only a CI YAML edit plus three assertions pinning the existing `validate_cli` template. That commit is marked `feat` because the CI YAML addition is the behavior change; the tests pin it in place.

## Self-Check: PASSED

- `.github/workflows/ci.yml` contains the drift-gate step — verified
- `graphify/capability.py::extract_tool_examples` exists — verified
- `graphify/mcp_tool_registry.py::build_handler_docstrings` exists — verified
- `graphify/serve.py::_handlers_snapshot` exists — verified
- `server.json` `_meta.manifest_content_hash` = `d066e4e1…` matches live `canonical_manifest_hash(build_manifest_dict())` — verified (`graphify capability --validate` → exit 0)
- Commits `da02ed7`, `aab4967`, `c1c987e` present in `git log` — verified
- Full suite `pytest tests/ -q` → 1273 passed — verified

## Next

- Plan 13-03 (Wave 1): SEED-002 harness export core (HARNESS-01..06)
- Plan 13-04 (Wave 2): HARNESS-07/08 P2 items
