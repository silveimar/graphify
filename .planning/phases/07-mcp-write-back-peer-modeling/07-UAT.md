---
status: complete
phase: 07-mcp-write-back-peer-modeling
source: 07-01-SUMMARY.md, 07-02-SUMMARY.md, 07-03-SUMMARY.md
started: 2026-04-13T03:11:00Z
updated: 2026-04-13T03:12:00Z
---

## Current Test

[testing complete]

## Tests

### 1. Test Suite: serve.py (Plans 01 + 02)
expected: All 46 tests in tests/test_serve.py pass — sidecar helpers, record constructors, proposal staging, mutation tools
result: pass
verified: `python -m pytest tests/test_serve.py -x -q` → 46 passed in 0.18s

### 2. Test Suite: approve (Plan 03)
expected: All 11 tests in tests/test_approve.py pass — list/reject/approve helpers, CLI integration
result: pass
verified: `python -m pytest tests/test_approve.py -x -q` → 11 passed in 0.04s

### 3. Full Test Suite Regression
expected: All 952 tests pass with no regressions from phase 07 changes
result: pass
verified: `python -m pytest tests/ -q` → 952 passed in 14.38s

### 4. Import Verification: serve.py helpers
expected: All 11 module-level helpers importable without MCP server (_append_annotation, _compact_annotations, _load_agent_edges, _save_agent_edges, _make_annotate_record, _make_flag_record, _make_edge_record, _filter_annotations, _make_proposal_record, _save_proposal, _list_proposals)
result: pass
verified: direct Python import of all 11 functions succeeds

### 5. Import Verification: approve helpers
expected: All 4 approve helpers importable from __main__.py (_list_pending_proposals, _reject_proposal, _approve_and_write_proposal, _format_proposal_summary)
result: pass
verified: direct Python import of all 4 functions succeeds

### 6. JSONL Sidecar Persistence
expected: _append_annotation writes JSONL lines, _compact_annotations deduplicates by (node_id, type, peer_id), keeping last entry
result: pass
verified: 2 lines compacted to 1 line; round-trip confirmed

### 7. Agent-Edges Atomic Write
expected: _save_agent_edges writes JSON atomically via os.replace(), _load_agent_edges reads it back identically
result: pass
verified: round-trip write/read of 1 edge with relation="calls"

### 8. Record Constructors: Sanitization
expected: All _make_*_record functions strip control characters from string inputs via sanitize_label
result: pass
verified: control chars (\x00, \x01, \x02) stripped from node_id, text, session_id, title, tags

### 9. Record Constructors: Validation
expected: _make_flag_record raises ValueError for invalid importance values; only accepts high/medium/low
result: pass
verified: ValueError raised for 'invalid_importance'; 'high' accepted

### 10. Record Constructors: Defaults
expected: peer_id defaults to "anonymous", note_type defaults to "note", status always "pending", confidence always "INFERRED" for edges
result: pass
verified: proposal peer_id="anonymous", note_type="note", status="pending"; edge confidence="INFERRED"

### 11. Proposal Staging Pipeline
expected: _save_proposal writes UUID4-named JSON to proposals/, _list_proposals reads and sorts by timestamp, returns [] for missing dir
result: pass
verified: proposal saved, listed with correct title/status, sorted by timestamp

### 12. CLI: graphify approve (list mode)
expected: `graphify approve` with no args lists pending proposals in tabular format or shows "No pending proposals"
result: pass
verified: `python -m graphify approve` → "No pending proposals."

### 13. CLI: graphify approve helpers
expected: _list_pending_proposals filters by status=pending; _reject_proposal updates status on disk; _format_proposal_summary shows id[:8] + title
result: pass
verified: 2 pending listed, 1 rejected → 1 remaining, status="rejected" on disk

### 14. Annotation Filtering
expected: _filter_annotations correctly filters by peer_id, session_id, time range; returns all when no filters
result: pass
verified: peer_id filter → 2/3, session_id filter → 1/3, no filter → 3/3

### 15. Security: T-07-02 peer_id never from environment
expected: Zero occurrences of os.environ in graphify/serve.py
result: pass
verified: `grep -c "os.environ" graphify/serve.py` → 0

### 16. Security: T-07-05 UUID4 only
expected: Zero occurrences of uuid.uuid1 in graphify/serve.py
result: pass
verified: `grep -c "uuid.uuid1" graphify/serve.py` → 0

### 17. Security: T-07-03 G never mutated
expected: No G.add_edge() or G.add_node() calls in mutation tool handlers
result: pass
verified: grep for G.add_edge/G.add_node in serve.py → none found

### 18. Security: CR-01 path traversal in record_id
expected: _reject_proposal raises ValueError for path traversal attempts (e.g., "../../../etc/passwd")
result: pass
verified: ValueError raised: "Invalid proposal ID: ../../../etc/passwd"

### 19. Security: WR-01 session_id sanitization
expected: session_id with control characters is sanitized in record constructors
result: pass
verified: 'sess\x00id' → 'sessid' (null byte stripped)

### 20. Security: validate_vault_path at approval time
expected: _approve_and_write_proposal calls validate_vault_path on suggested_folder before running merge engine (T-07-11)
result: pass
verified: graphify/__main__.py:814 calls _validate_vault_path_for_approve which imports and calls validate_vault_path from graphify.profile

### 21. CLI: approve not in --help
expected: `graphify approve` listed in `graphify --help` output
result: issue
reported: "approve subcommand works but is not listed in graphify --help output"
severity: minor

## Summary

total: 21
passed: 20
issues: 1
pending: 0
skipped: 0
blocked: 0

## Gaps

- truth: "`graphify approve` listed in `graphify --help` output"
  status: failed
  reason: "User reported: approve subcommand works but is not listed in graphify --help output"
  severity: minor
  test: 21
  root_cause: "approve subcommand was added to the if/elif dispatch in main() but the help text string at the top of main() was not updated to include it"
  artifacts:
    - path: "graphify/__main__.py"
      issue: "help text missing approve subcommand"
  missing:
    - "Add approve usage lines to the help text in main()"
  debug_session: ""
