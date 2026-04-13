---
phase: 7
slug: mcp-write-back-peer-modeling
status: draft
nyquist_compliant: true
wave_0_complete: true
created: 2026-04-12
---

# Phase 7 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest (existing) |
| **Config file** | none — discovered by default |
| **Quick run command** | `pytest tests/test_serve.py -q` |
| **Full suite command** | `pytest tests/ -q` |
| **Estimated runtime** | ~15 seconds |

---

## Sampling Rate

- **After every task commit:** Run `pytest tests/test_serve.py -q`
- **After every plan wave:** Run `pytest tests/ -q`
- **Before `/gsd-verify-work`:** Full suite must be green
- **Max feedback latency:** 15 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 07-01-01 | 01 | 1 | MCP-04 | — | JSONL append-only writes | unit | `pytest tests/test_serve.py::test_append_annotation_creates_file -x` | TDD in-task | ⬜ pending |
| 07-01-02 | 01 | 1 | MCP-04 | — | Compaction deduplicates by key | unit | `pytest tests/test_serve.py::test_compact_annotations_dedup -x` | TDD in-task | ⬜ pending |
| 07-01-03 | 01 | 1 | MCP-03 | — | Agent edges load/save atomically | unit | `pytest tests/test_serve.py::test_save_agent_edges_atomic -x` | TDD in-task | ⬜ pending |
| 07-01-04 | 01 | 1 | MCP-05 | T-07-02 | peer_id defaults "anonymous", never from env | unit | `pytest tests/test_serve.py::test_make_annotate_record_defaults -x` | TDD in-task | ⬜ pending |
| 07-01-05 | 01 | 1 | MCP-05 | T-07-02 | peer_id never derived from environment | unit | `pytest tests/test_serve.py::test_peer_id_never_from_env -x` | TDD in-task | ⬜ pending |
| 07-01-06 | 01 | 1 | MCP-01 | T-07-01 | annotate_node sanitizes input | unit | `pytest tests/test_serve.py::test_make_annotate_record_sanitizes -x` | TDD in-task | ⬜ pending |
| 07-01-07 | 01 | 1 | MCP-02 | — | flag_node validates importance values | unit | `pytest tests/test_serve.py::test_make_flag_record_valid -x` | TDD in-task | ⬜ pending |
| 07-01-08 | 01 | 1 | MCP-10 | T-07-03 | add_edge never modifies graph object | unit | `pytest tests/test_serve.py::test_make_edge_record_never_modifies_graph -x` | TDD in-task | ⬜ pending |
| 07-01-09 | 01 | 1 | MCP-08 | — | get_annotations filters by peer_id | unit | `pytest tests/test_serve.py::test_filter_annotations_by_peer -x` | TDD in-task | ⬜ pending |
| 07-01-10 | 01 | 1 | MCP-08 | — | get_annotations filters by session_id | unit | `pytest tests/test_serve.py::test_filter_annotations_by_session -x` | TDD in-task | ⬜ pending |
| 07-01-11 | 01 | 1 | MCP-08 | — | get_annotations filters by time_range | unit | `pytest tests/test_serve.py::test_filter_annotations_by_time_range -x` | TDD in-task | ⬜ pending |
| 07-01-12 | 01 | 1 | MCP-09 | — | Session-scoped view returns filtered | unit | `pytest tests/test_serve.py::test_filter_annotations_no_filter -x` | TDD in-task | ⬜ pending |
| 07-02-01 | 02 | 2 | MCP-06 | T-07-08 | propose_vault_note creates proposal in proposals/ | unit | `pytest tests/test_serve.py::test_save_proposal_creates_dir -x` | TDD in-task | ⬜ pending |
| 07-02-02 | 02 | 2 | MCP-06 | T-07-08 | Proposal filename is UUID, not title | unit | `pytest tests/test_serve.py::test_save_proposal_filename_is_uuid -x` | TDD in-task | ⬜ pending |
| 07-02-03 | 02 | 2 | MCP-06 | T-07-10 | All proposal strings sanitized | unit | `pytest tests/test_serve.py::test_make_proposal_record_sanitizes -x` | TDD in-task | ⬜ pending |
| 07-02-04 | 02 | 2 | MCP-06 | — | Proposal status always "pending" | unit | `pytest tests/test_serve.py::test_make_proposal_record_status_pending -x` | TDD in-task | ⬜ pending |
| 07-03-01 | 03 | 3 | MCP-07 | — | List pending proposals, filter by status | unit | `pytest tests/test_approve.py::test_list_pending_proposals_filters_status -x` | TDD in-task | ⬜ pending |
| 07-03-02 | 03 | 3 | MCP-07 | T-07-11 | approve <id> calls merge engine | unit | `pytest tests/test_approve.py::test_approve_and_write_proposal_calls_merge -x` | TDD in-task | ⬜ pending |
| 07-03-03 | 03 | 3 | MCP-07 | — | reject <id> marks proposal rejected | unit | `pytest tests/test_approve.py::test_reject_proposal -x` | TDD in-task | ⬜ pending |
| 07-03-04 | 03 | 3 | MCP-07 | T-07-12 | --vault required for approve ops | unit | `pytest tests/test_approve.py::test_cli_approve_no_vault_exits_2 -x` | TDD in-task | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

Tests are written in-task via TDD pattern — each plan task creates its own tests as part of the implementation. No separate Wave 0 plan needed.

*Existing infrastructure covers all phase requirements.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| MCP tool appears in Claude agent tool list | MCP-01/02/03/06 | Requires live MCP connection | Start server, connect agent, verify tools listed |

---

## Validation Sign-Off

- [x] All tasks have `<automated>` verify or Wave 0 dependencies
- [x] Sampling continuity: no 3 consecutive tasks without automated verify
- [x] Wave 0 covers all MISSING references
- [x] No watch-mode flags
- [x] Feedback latency < 15s
- [x] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
