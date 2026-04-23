---
phase: 07-mcp-write-back-peer-modeling
plan: "02"
subsystem: serve
tags: [mcp, propose-vault-note, proposals, persistence, tdd]
dependency_graph:
  requires: ["07-01"]
  provides: ["propose_vault_note tool handler", "proposal staging pipeline"]
  affects: ["graphify/serve.py", "tests/test_serve.py"]
tech_stack:
  added: []
  patterns: ["uuid4 filename generation", "proposals/ staging directory", "sanitize_label at storage layer"]
key_files:
  created: []
  modified:
    - graphify/serve.py
    - tests/test_serve.py
decisions:
  - "Proposal filename is always server-generated uuid4 — never derived from agent-supplied title (T-07-08)"
  - "sanitize_label applied to all string fields at storage time, including each tag individually"
  - "_list_proposals sorts by timestamp ascending and silently skips corrupt JSON files"
  - "Tool description explicitly states 'Does NOT write to the vault — only to graphify-out/proposals/'"
metrics:
  duration: "~2 min"
  completed: "2026-04-13"
  tasks_completed: 1
  files_modified: 2
  tests_added: 11
  tests_total: 46
---

# Phase 07 Plan 02: propose_vault_note Staging Summary

**One-liner:** UUID4-named JSON proposal staging in `graphify-out/proposals/` via `_make_proposal_record` / `_save_proposal` / `_list_proposals`, with full D-08 field set and `sanitize_label` on every agent-supplied string.

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| RED | Failing tests for proposal helpers | 758a63b | tests/test_serve.py |
| GREEN | Implement proposal helpers + replace placeholder | c51e3d1 | graphify/serve.py |

## What Was Built

### New module-level functions (graphify/serve.py)

**`_make_proposal_record(arguments: dict, session_id: str) -> dict`**
Builds a complete D-08 proposal record:
- Extracts and sanitizes all string fields via `sanitize_label`: `title`, `note_type` (default `"note"`), `body_markdown`, `suggested_folder`, `rationale`
- Each tag in `tags` array sanitized individually
- `peer_id` defaults to `"anonymous"` if not supplied
- `record_id` is a fresh `uuid.uuid4()` — never from agent input
- `status` is always `"pending"`

**`_save_proposal(out_dir: Path, record: dict) -> None`**
Writes `graphify-out/proposals/{record_id}.json` (indented JSON). Creates the proposals directory with `mkdir(parents=True, exist_ok=True)`.

**`_list_proposals(out_dir: Path) -> list[dict]`**
Reads all `*.json` files from `graphify-out/proposals/`, skips corrupt files silently, returns list sorted by `timestamp` ascending. Returns `[]` if directory does not exist.

### Replaced placeholder (graphify/serve.py)

`_tool_propose_vault_note` was a stub returning `"Not implemented yet"`. Replaced with:
```python
def _tool_propose_vault_note(arguments: dict) -> str:
    record = _make_proposal_record(arguments, _session_id)
    _save_proposal(_out_dir, record)
    return json.dumps({"record_id": record["record_id"], "status": "pending"})
```

### Updated tool schema

`propose_vault_note` description updated to: `"Stage a proposed vault note for human approval. Does NOT write to the vault — only to graphify-out/proposals/."` — matching D-14 field set with `default` annotations on `note_type` and `peer_id`.

### Tests added (tests/test_serve.py): 11 new tests

- `test_make_proposal_record_fields` — all D-08 fields present
- `test_make_proposal_record_sanitizes` — control chars stripped from title
- `test_make_proposal_record_default_peer` — peer_id defaults to "anonymous"
- `test_make_proposal_record_status_pending` — status always "pending"
- `test_make_proposal_record_default_note_type` — note_type defaults to "note"
- `test_make_proposal_record_tags_sanitized` — each tag sanitized
- `test_save_proposal_creates_dir` — proposals/ dir created on first save
- `test_save_proposal_filename_is_uuid` — filename is record_id.json, not title
- `test_list_proposals_empty` — returns [] for missing dir
- `test_list_proposals_returns_records` — both proposals returned
- `test_list_proposals_skips_corrupt` — corrupt JSON file silently skipped

## Threat Mitigations Applied

| Threat | Mitigation |
|--------|-----------|
| T-07-07 path traversal in suggested_folder | `sanitize_label()` applied at storage time; `validate_vault_path()` deferred to Plan 03 approve step |
| T-07-08 proposal filename injection | Filename always `{uuid4}.json` — server-generated, title stored only inside JSON payload |
| T-07-09 agent writes vault without approval | Tool writes ONLY to `graphify-out/proposals/`; no vault path accepted as argument |
| T-07-10 control chars in body_markdown | `sanitize_label()` strips control chars from all string fields |

## Deviations from Plan

None — plan executed exactly as written.

## Known Stubs

None. `_tool_propose_vault_note` placeholder from Plan 01 has been fully replaced.

## Self-Check: PASSED

- `graphify/serve.py` contains `def _make_proposal_record`: confirmed
- `graphify/serve.py` contains `def _save_proposal`: confirmed
- `graphify/serve.py` contains `def _list_proposals`: confirmed
- `graphify/serve.py` contains `def _tool_propose_vault_note` (real implementation): confirmed
- `graphify/serve.py` has `validate_vault_path` count = 0: confirmed
- Tests RED commit 758a63b: confirmed
- Tests GREEN commit c51e3d1: confirmed
- `python -m pytest tests/test_serve.py -x -q` exits 0: 46 passed
- `python -m pytest tests/ -q` exits 0: 941 passed
