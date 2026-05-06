---
phase: 66-cfed-cross-repo-concept-federation-federate-py
plan: 03
subsystem: federate
tags: [cli, federation, stderr-contract, tdd, cfed]
requires:
  - graphify/build.py::build_from_json (peers kwarg)
  - graphify/federate.py::FederationCollisionError
  - graphify/output.py::_emit_vault_error
  - graphify/pipeline.py::run_corpus
provides:
  - graphify/__main__.py::_build_federate_parser
  - graphify/__main__.py::_cmd_federate
  - cli: graphify federate --federate-with PATH [--federate-with PATH ...]
affects:
  - graphify/__main__.py
tech_stack:
  added: []
  patterns: [argparse-action-append, two-line-stderr-breadcrumb, fail-fast-preflight, default-off-invariant]
key_files:
  created: []
  modified:
    - graphify/__main__.py
    - tests/test_federate.py
    - tests/test_stderr_contract.py
decisions: [D-66.1, D-66.3]
metrics:
  duration: ~6m
  tasks: 1
  tests_added: 5
  date: 2026-05-06
requirements: [CFED-01]
---

# Phase 66 Plan 03: `graphify federate` CLI subcommand — Summary

CFED-01 user-facing opt-in surface. New `graphify federate` subcommand wraps
the engine from Plan 01 and the pipeline wiring from Plan 02 with repeatable
`--federate-with PATH` and Phase-64-conformant two-line stderr breadcrumbs
on both error paths.

## Tasks Completed

| Task | Name                                                            | Commit  |
| ---- | --------------------------------------------------------------- | ------- |
| 1a   | RED — failing CLI parser + missing-peer + collision tests       | f407efb |
| 1b   | GREEN — register subcommand, pre-flight validation, engine wire | bdea137 |

## Public CLI

```
graphify federate --federate-with PATH [--federate-with PATH ...] [target]
```

- `--federate-with PATH` (repeatable via argparse `action="append"`) — each
  `PATH` is a peer repo's `graphify-out/` directory (or a `graph.json` file
  directly).
- `target` positional (default `.`) — local corpus path.
- Exit codes: `0` on success; `2` on missing-peer or basename-collision
  (matches Phase 64's `EXIT_VAULT_GATE` policy).

## Behaviors Locked by Tests

- **`test_cli_repeatable`** — `_build_federate_parser()` accepts two
  `--federate-with` flags; `args.federate_with == [path1, path2]`.
- **`test_cli_missing_peer`** — invoking `python -m graphify federate
  --federate-with <nonexistent>` exits non-zero and emits exactly:
  ```
  [graphify] error: peer export not found at <path>/graph.json
    hint: run `graphify run` in the peer repo first
  ```
- **`test_cli_collision`** — two `--federate-with` paths whose parents share
  basename `repo` (D-66.3) emit:
  ```
  [graphify] error: duplicate peer repo basename 'repo'
    hint: rename one peer directory or use distinct paths
  ```
- **`test_federation_missing_peer_breadcrumb` /
  `test_federation_collision_breadcrumb`** (in `test_stderr_contract.py`) —
  pin the exact wording and confirm both lines satisfy the D-04 strict
  prefix whitelist (`^(\[graphify\] (error|info|hint): |  hint: )`).

## Implementation

`graphify/__main__.py` adds:

1. **`_build_federate_parser()`** at module scope — argparse parser with
   `add_argument("--federate-with", action="append", default=[])` and a
   single positional `path` (default `.`). Exposed for direct test
   introspection.
2. **`_cmd_federate(argv)`** — handler:
   - Pre-flight #1: each `--federate-with PATH` resolves to
     `<PATH>/graph.json` (or `<PATH>` itself if it's already a file). Missing
     → `_emit_vault_error("peer export not found at …", "run `graphify run`
     in the peer repo first", code=2)`.
   - Pre-flight #2: repo-basename collision detection mirroring
     `federate.py::_repo_label_for_peer` (label = `parent.parent.name` when
     `parent.name == "graphify-out"`, else `parent.name`). Duplicate → same
     `_emit_vault_error` with the collision message.
   - Engine: `extraction = run_corpus(target, use_router=False)` then
     `build_from_json(extraction, peers=peer_paths, local_repo=target.name,
     target_dir=Path.cwd())`. The federation block in `build.py` (Plan 02
     L235) writes the vault-aware `federation-manifest.json`.
   - `FederationCollisionError` from inside `build_from_json` (e.g.,
     local-repo basename clashes with a peer's) is re-emitted in two-line
     form.
3. **Dispatch**: `elif cmd == "federate": _cmd_federate(sys.argv[2:])`
   inserted directly above the unknown-command `else:` branch — no other
   commands touched. The acceptance grep `grep -c 'cmd == "run"'` still
   returns `1`, proving CFED-01 default-off plumbing.

Both error paths use `graphify.output._emit_vault_error`, which is the Phase
64 sole sanctioned two-line emitter. The plan's note on the existing helper
(`RESEARCH mentioned _emit_vault_error shape`) was honored — no new ad-hoc
print statements were introduced.

## Acceptance Criteria

- [x] `python -m graphify federate --help` exits 0 and stdout contains
      `--federate-with` ✓
- [x] `grep -c 'action="append"' graphify/__main__.py` → 3 (≥1) ✓
- [x] `grep -c 'cmd == "federate"' graphify/__main__.py` → 1 ✓
- [x] `python -m graphify federate --federate-with /tmp/__definitely_missing__/graphify-out`
      stderr line 1 starts with `[graphify] error:` and line 2 with `  hint:` ✓
- [x] `pytest tests/test_stderr_contract.py -x` exits 0 (10 tests) ✓
- [x] `grep -c 'cmd == "run"' graphify/__main__.py` → 1 (unchanged) ✓
- [x] Commit message starts with `feat(66-03):` ✓

The original plan's acceptance check `grep -c "..." | grep -q .` (a no-op
because `grep -c` always emits a numeric line) was replaced with the
deterministic `grep -c '…' > 0` form above per the executor's
execution_contract directive.

## Verification

- `pytest tests/test_federate.py tests/test_stderr_contract.py -q` →
  **25 passed** (5 new + 20 pre-existing)
- `pytest tests/ -q` → **2339 passed**, 1 xfailed, 1 pre-existing failure
  (`tests/test_migration.py::test_preview_expands_risky_action_rows` —
  out of scope per Phase 65 `deferred-items.md`)
- Manual: `python -m graphify federate --help` and the missing-peer
  smoke test both produce the expected exit codes and breadcrumbs.

## Deviations from Plan

**[Rule 1 — Acceptance grep correctness]** The plan listed
`grep -c "action=\"append\"" graphify/__main__.py | grep -q .` as an
acceptance check, but `grep -c` always emits a numeric line so the
`grep -q .` follow-up is a no-op (the executor's contract called this
out explicitly). Replaced with the meaningful
`[ "$(grep -c 'action="append"' graphify/__main__.py)" -gt 0 ]` form
documented above and verified manually (returns 3).

**[Rule 2 — Duplicate-peer error wording]** The plan's `<behavior>` block
referenced "FederationCollisionError" generically; the engine in Plan 01
emits the message `--federate-with paths share repo basename 'X'`, while
the executor's `<execution_contract>` mandated the user-facing wording
`[graphify] error: duplicate peer repo basename '<name>'`. Honored the
contract: the CLI pre-flight emits the contract wording, and the
`FederationCollisionError` raised inside `build_from_json` (only for
local-repo-vs-peer collisions, which the pre-flight cannot detect) is
caught and re-emitted in the same wording for consistency.

## Cross-Plan Handoff

Plan 04 (`report.py` Federation section) is unaffected by this plan:
the report renderer still reads `federation-manifest.json` produced by
Plan 02. The CLI now exercises the full Plan 02 write path end-to-end.

## Self-Check: PASSED

- `graphify/__main__.py::_build_federate_parser` — FOUND (line:
  `def _build_federate_parser`)
- `graphify/__main__.py::_cmd_federate` — FOUND (line: `def _cmd_federate`)
- `graphify/__main__.py` dispatch `elif cmd == "federate":` — FOUND
- `tests/test_federate.py::test_cli_repeatable` — FOUND
- `tests/test_federate.py::test_cli_missing_peer` — FOUND
- `tests/test_federate.py::test_cli_collision` — FOUND
- `tests/test_stderr_contract.py::test_federation_missing_peer_breadcrumb` — FOUND
- `tests/test_stderr_contract.py::test_federation_collision_breadcrumb` — FOUND
- Commit f407efb (RED) — FOUND
- Commit bdea137 (GREEN) — FOUND

## TDD Gate Compliance

- **RED gate:** `test(66-03): add failing CLI federate subcommand + stderr
  breadcrumb tests` (f407efb) — confirmed RED via
  `ImportError: cannot import name '_build_federate_parser' from
  'graphify.__main__'` before implementation.
- **GREEN gate:** `feat(66-03): add graphify federate subcommand with Phase
  64 stderr contract` (bdea137) — all 5 new tests pass; full plan-scoped
  suite 25 passed; full repo suite 2339 passed.
- **REFACTOR gate:** not needed; implementation landed clean on first
  iteration.
