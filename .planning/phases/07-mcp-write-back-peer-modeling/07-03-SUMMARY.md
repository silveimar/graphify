---
phase: 07-mcp-write-back-peer-modeling
plan: "03"
subsystem: cli
tags: [cli, approve, proposals, merge-engine, human-in-the-loop, tdd]
dependency_graph:
  requires: ["07-02"]
  provides:
    - graphify/__main__.py::_list_pending_proposals
    - graphify/__main__.py::_reject_proposal
    - graphify/__main__.py::_approve_and_write_proposal
    - graphify/__main__.py::_format_proposal_summary
    - graphify/__main__.py::approve subcommand
  affects:
    - graphify-out/proposals/*.json (status updates)
    - vault directory (via merge engine on approval)
tech_stack:
  added: []
  patterns:
    - Module-level helper functions with indirection wrappers for testability
    - Atomic JSON rewrite via os.replace() for status updates
    - validate_vault_path called at approval time (T-07-11)
    - TDD with monkeypatched merge engine for approve-and-write test
key_files:
  created:
    - tests/test_approve.py
  modified:
    - graphify/__main__.py
decisions:
  - "validate_vault_path is in graphify.profile, not graphify.security (plan referenced wrong module — corrected)"
  - "RenderedNote TypedDict uses frontmatter_fields/body, not frontmatter/content (plan had wrong field names — corrected)"
  - "Indirection helpers (_load_profile_for_approve, _validate_vault_path_for_approve, etc.) added for monkeypatching in tests without MCP server"
  - "Python 3.10 f-string backslash restriction: use variable _hr instead of backslash Unicode escape inside f-string"
  - "--vault is required for all approve operations that write to vault (D-11, T-07-12)"
metrics:
  duration: ~4 min
  completed: "2026-04-13"
  tasks_completed: 2
  files_changed: 2
  tests_added: 11
  tests_total: 952
---

# Phase 07 Plan 03: graphify approve CLI Subcommand Summary

**One-liner:** `graphify approve` CLI subcommand with list/single-approve/reject/batch operations, path-confined via `validate_vault_path`, writing approved proposals through the `compute_merge_plan` + `apply_merge_plan` merge engine.

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 RED | Failing tests for approve helper functions | 570ab01 | tests/test_approve.py |
| 1 GREEN | Implement approve helper functions | 1b93d4d | graphify/__main__.py |
| 2 RED | Failing CLI integration tests for approve subcommand | 760b73a | tests/test_approve.py |
| 2 GREEN | Wire approve subcommand into CLI main() | e6cd402 | graphify/__main__.py |

## What Was Built

### Module-Level Helper Functions (graphify/__main__.py)

**`_list_pending_proposals(out_dir: Path) -> list[dict]`**
Reads all `.json` files from `out_dir/proposals/`, filters to `status == "pending"`, returns sorted by `timestamp` ascending. Returns `[]` when directory does not exist. Silently skips corrupt JSON files.

**`_reject_proposal(proposals_dir: Path, record_id: str) -> dict`**
Reads proposal, sets `status = "rejected"`, rewrites atomically via `os.replace()`. Raises `FileNotFoundError` for missing proposals.

**`_approve_and_write_proposal(proposals_dir: Path, record_id: str, vault_path: Path) -> dict`**
Reads proposal, calls `validate_vault_path` on `suggested_folder` (T-07-11), loads vault profile via `load_profile`, constructs `RenderedNote` dict, calls `compute_merge_plan` + `apply_merge_plan`, sets `status = "approved"`, rewrites atomically.

**`_format_proposal_summary(proposal: dict) -> str`**
Returns one-line tabular summary with `record_id[:8]`, title (40 chars), note_type (12 chars), peer_id (12 chars), timestamp (25 chars).

**Indirection helpers** (`_load_profile_for_approve`, `_validate_vault_path_for_approve`, `_compute_merge_plan_for_approve`, `_apply_merge_plan_for_approve`): module-level delegating functions that call the real imports, making them monkeypatchable in tests without starting an MCP server.

### CLI Subcommand (graphify/__main__.py `main()`)

`if cmd == "approve":` block with manual `sys.argv` parsing following the `snapshot` subcommand pattern:

| Usage | Behavior |
|-------|----------|
| `graphify approve` | Lists all pending proposals in tabular format |
| `graphify approve <id> --vault <path>` | Approves and writes single proposal to vault |
| `graphify approve --reject <id>` | Rejects single proposal |
| `graphify approve --all --vault <path>` | Batch approves all pending proposals |
| `graphify approve --reject-all` | Batch rejects all pending proposals |
| `graphify approve <id>` (no `--vault`) | Prints error and exits 2 (D-11, T-07-12) |

### Tests (tests/test_approve.py): 11 new tests

**Helper unit tests:**
- `test_list_pending_proposals_empty` — empty dir returns `[]`
- `test_list_pending_proposals_filters_status` — only pending returned
- `test_list_pending_proposals_sorted_by_timestamp` — ascending order
- `test_reject_proposal` — status updated on disk
- `test_reject_proposal_missing` — raises FileNotFoundError
- `test_format_proposal_summary` — contains id prefix and title
- `test_approve_and_write_proposal_calls_merge` — mocked merge engine; status set to "approved"

**CLI integration tests:**
- `test_cli_approve_list` — proposal IDs appear in list output
- `test_cli_approve_no_vault_exits_2` — exits 2 without `--vault`
- `test_cli_approve_reject` — `--reject` sets status on disk
- `test_cli_approve_reject_all` — `--reject-all` rejects all pending

## Security Invariants Verified

| Threat | Status |
|--------|--------|
| T-07-11: suggested_folder path traversal at approval | MITIGATED — `validate_vault_path()` called in `_approve_and_write_proposal` before merge engine runs |
| T-07-12: approve without --vault writes to CWD | MITIGATED — `--vault` required for all vault-write operations; exits 2 if missing |
| T-07-13: proposal JSON tampering | ACCEPTED — user-editable by design (proposals in graphify-out/) |

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Wrong module for `validate_vault_path`**
- **Found during:** Task 1 implementation
- **Issue:** Plan specified `from graphify.security import validate_vault_path` but `validate_vault_path` lives in `graphify.profile`, not `graphify.security`
- **Fix:** Used `from graphify.profile import validate_vault_path` in `_validate_vault_path_for_approve`
- **Files modified:** graphify/__main__.py

**2. [Rule 1 - Bug] Wrong `RenderedNote` field names**
- **Found during:** Task 1 implementation
- **Issue:** Plan specified `content=` and `frontmatter=` but `RenderedNote` TypedDict defines `body` and `frontmatter_fields`
- **Fix:** Used correct field names `body` and `frontmatter_fields` when constructing RenderedNote
- **Files modified:** graphify/__main__.py

**3. [Rule 1 - Bug] Python 3.10 f-string backslash restriction**
- **Found during:** Task 2 GREEN
- **Issue:** `f"  {'\u2500'*8}  ..."` is a SyntaxError on Python 3.10 (backslash escapes not allowed inside f-string expressions in 3.10)
- **Fix:** Assigned `_hr = "\u2500"` as a local variable and used `f"  {_hr*8}  ..."` instead
- **Files modified:** graphify/__main__.py
- **Commit:** e6cd402

## Known Stubs

None. All approve operations fully implemented.

## Threat Flags

None. No new network endpoints or trust boundaries introduced. `graphify approve` reads from `graphify-out/` (user-controlled) and writes to vault (user-controlled local path).

## Self-Check: PASSED

- `graphify/__main__.py` contains `def _list_pending_proposals`: confirmed
- `graphify/__main__.py` contains `def _reject_proposal`: confirmed
- `graphify/__main__.py` contains `def _approve_and_write_proposal`: confirmed
- `graphify/__main__.py` contains `def _format_proposal_summary`: confirmed
- `graphify/__main__.py` contains `if cmd == "approve":`: confirmed
- `graphify/__main__.py` contains `--vault is required for approve operations`: confirmed
- `graphify/__main__.py` contains `validate_vault_path`: confirmed
- `tests/test_approve.py` contains `test_list_pending_proposals_empty`: confirmed
- `tests/test_approve.py` contains `test_reject_proposal`: confirmed
- `tests/test_approve.py` contains `test_format_proposal_summary`: confirmed
- `tests/test_approve.py` contains `test_cli_approve_list`: confirmed
- `tests/test_approve.py` contains `test_cli_approve_no_vault_exits_2`: confirmed
- `tests/test_approve.py` contains `test_cli_approve_reject`: confirmed
- RED commit 570ab01: confirmed (test-only, ImportError)
- RED commit 760b73a: confirmed (CLI tests, unknown command error)
- GREEN commit 1b93d4d: confirmed (7 helper tests pass)
- GREEN commit e6cd402: confirmed (11 tests pass)
- `python -m pytest tests/test_approve.py -x -q` exits 0: 11 passed
- `python -m pytest tests/ -q` exits 0: 952 passed
