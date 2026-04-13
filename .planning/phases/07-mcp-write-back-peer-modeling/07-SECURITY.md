# Security Audit — Phase 07: MCP Write-Back & Peer Modeling

**Phase:** 07 — mcp-write-back-peer-modeling
**ASVS Level:** 1
**Audit Date:** 2026-04-12
**Auditor:** gsd-security-auditor
**Plans Audited:** 07-01, 07-02, 07-03

---

## Threat Verification

| Threat ID | Category | Disposition | Evidence | Status |
|-----------|----------|-------------|----------|--------|
| T-07-01 | Tampering | mitigate | `graphify/serve.py:77-116` — `sanitize_label()` called on all string inputs in `_make_annotate_record`, `_make_flag_record`, `_make_edge_record` | CLOSED |
| T-07-02 | Information Disclosure | mitigate | `graphify/serve.py` — grep for `os.environ` returns 0 matches; `peer_id` defaults to literal `"anonymous"` at lines 613, 623, 637 | CLOSED |
| T-07-03 | Tampering | mitigate | `graphify/serve.py:632-641` — `_tool_add_edge` calls `_save_agent_edges` only; no `G.add_edge()` call found in any tool handler | CLOSED |
| T-07-04 | Denial of Service | mitigate | `graphify/serve.py:337` — `_compact_annotations(_out_dir / "annotations.jsonl")` called at `serve()` startup before `_session_id` assignment | CLOSED |
| T-07-05 | Information Disclosure | mitigate | `graphify/serve.py:339` — `_session_id = str(uuid.uuid4())`; grep for `uuid.uuid1` returns 0 matches | CLOSED |
| T-07-06 | Tampering | accept | Corrupt JSONL lines skipped via `json.JSONDecodeError` catch in `_compact_annotations` (line 41); data loss bounded to one record per crash. Accepted by design. | CLOSED |
| T-07-07 | Tampering | mitigate | `graphify/serve.py:124` — `suggested_folder = sanitize_label(arguments.get("suggested_folder", ""))` in `_make_proposal_record`; `validate_vault_path` applied at approval time (Plan 03, line 806 in `__main__.py`) | CLOSED |
| T-07-08 | Tampering | mitigate | `graphify/serve.py:128` — `record_id = str(uuid.uuid4())`; `_save_proposal` uses `proposals_dir / f"{record['record_id']}.json"` (line 149) — filename is server-generated, never from agent title | CLOSED |
| T-07-09 | Spoofing | mitigate | `graphify/serve.py:643-647` — `_tool_propose_vault_note` calls only `_save_proposal(_out_dir, record)` which writes to `graphify-out/proposals/`; no vault path accepted as argument | CLOSED |
| T-07-10 | Injection | mitigate | `graphify/serve.py:119-142` — `sanitize_label()` applied to `body_markdown` (line 123) and all other string fields in `_make_proposal_record` | CLOSED |
| T-07-11 | Tampering | mitigate | `graphify/__main__.py:806` — `_validate_vault_path_for_approve(suggested_folder, vault_path)` called in `_approve_and_write_proposal` before merge engine executes; delegates to `graphify.profile.validate_vault_path` | CLOSED |
| T-07-12 | Elevation of Privilege | mitigate | `graphify/__main__.py:1230,1247` — two explicit `--vault is required for approve operations` guards with `sys.exit(2)` covering both single-approve and batch-approve paths | CLOSED |
| T-07-13 | Tampering | accept | Proposals stored in `graphify-out/proposals/` which is user-controlled. User-editable by design — this is the human-in-the-loop review feature, not a vulnerability. Accepted. | CLOSED |

---

## Accepted Risks Log

| Threat ID | Risk Description | Rationale |
|-----------|-----------------|-----------|
| T-07-06 | Corrupt JSONL line from mid-write crash is silently skipped during startup compaction | Data loss is bounded to at most one annotation record. Single-server assumption prevents concurrent writers. Acceptable for annotation sidecars which are supplementary, not authoritative. |
| T-07-13 | Proposal JSON files in `graphify-out/proposals/` can be edited by the user before approval | Intentional: this is the human-review surface. Users owning their `graphify-out/` directory is a design invariant of the tool. Editing proposals before approving is a documented feature. |

---

## Unregistered Flags

None. SUMMARY.md `## Threat Flags` for all three plans (07-01, 07-02, 07-03) report no new threat flags.

---

## Implementation Deviations with Security Impact

The executor auto-corrected two plan bugs that had indirect security relevance:

1. **`validate_vault_path` module location** (07-03): Plan specified `graphify.security` but the function lives in `graphify.profile`. Executor corrected to `from graphify.profile import validate_vault_path`. Mitigation for T-07-11 is intact — the function is called at the correct point.

2. **`RenderedNote` field names** (07-03): Plan used `content`/`frontmatter` but TypedDict defines `body`/`frontmatter_fields`. Corrected by executor. No security impact.

Neither deviation weakens any declared mitigation.
