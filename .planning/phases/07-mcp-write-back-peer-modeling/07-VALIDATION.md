---
phase: 7
slug: mcp-write-back-peer-modeling
status: draft
nyquist_compliant: false
wave_0_complete: false
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
| 07-01-01 | 01 | 1 | MCP-04 | — | JSONL append-only writes | unit | `pytest tests/test_serve.py::test_annotation_append_only -x` | No — W0 | ⬜ pending |
| 07-01-02 | 01 | 1 | MCP-05 | T-07-03 | peer_id defaults "anonymous", never from env | unit | `pytest tests/test_serve.py::test_record_provenance_fields -x` | No — W0 | ⬜ pending |
| 07-01-03 | 01 | 1 | MCP-05 | T-07-03 | peer_id never derived from environment | unit | `pytest tests/test_serve.py::test_peer_id_no_env_leak -x` | No — W0 | ⬜ pending |
| 07-01-04 | 01 | 1 | MCP-01 | — | annotate_node persists across restarts | unit | `pytest tests/test_serve.py::test_annotate_node_persists -x` | No — W0 | ⬜ pending |
| 07-01-05 | 01 | 1 | MCP-02 | — | flag_node persists importance levels | unit | `pytest tests/test_serve.py::test_flag_node_persists -x` | No — W0 | ⬜ pending |
| 07-02-01 | 02 | 1 | MCP-03 | T-07-01 | add_edge writes to sidecar, not graph.json | unit | `pytest tests/test_serve.py::test_add_edge_sidecar_only -x` | No — W0 | ⬜ pending |
| 07-02-02 | 02 | 1 | MCP-10 | T-07-01 | graph.json byte-identical after mutations | unit | `pytest tests/test_serve.py::test_graph_json_never_mutated -x` | No — W0 | ⬜ pending |
| 07-02-03 | 02 | 1 | MCP-08 | — | get_annotations filters by peer_id | unit | `pytest tests/test_serve.py::test_get_annotations_peer_filter -x` | No — W0 | ⬜ pending |
| 07-02-04 | 02 | 1 | MCP-08 | — | get_annotations filters by session_id | unit | `pytest tests/test_serve.py::test_get_annotations_session_filter -x` | No — W0 | ⬜ pending |
| 07-02-05 | 02 | 1 | MCP-08 | — | get_annotations filters by time_range | unit | `pytest tests/test_serve.py::test_get_annotations_time_filter -x` | No — W0 | ⬜ pending |
| 07-02-06 | 02 | 1 | MCP-09 | — | Session-scoped view returns current session only | unit | `pytest tests/test_serve.py::test_session_scoped_view -x` | No — W0 | ⬜ pending |
| 07-03-01 | 03 | 2 | MCP-06 | T-07-05 | propose_vault_note writes to proposals/ only | unit | `pytest tests/test_serve.py::test_propose_writes_to_staging_only -x` | No — W0 | ⬜ pending |
| 07-03-02 | 03 | 2 | MCP-07 | T-07-04 | approve <id> applies merge engine | unit | `pytest tests/test_main_cli.py::test_approve_applies_merge_engine -x` | No — W0 | ⬜ pending |
| 07-03-03 | 03 | 2 | MCP-07 | — | approve --reject <id> marks rejected | unit | `pytest tests/test_main_cli.py::test_approve_reject_id -x` | No — W0 | ⬜ pending |
| 07-04-01 | 04 | 3 | MCP-13 | — | mtime check reloads graph on change | unit | `pytest tests/test_serve.py::test_reload_if_stale -x` | No — W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] New test functions in `tests/test_serve.py` — stubs for MCP-01 through MCP-06, MCP-08 through MCP-10
- [ ] New test functions in `tests/test_main_cli.py` — stubs for MCP-07 (`graphify approve` CLI)
- [ ] `tests/test_serve.py` already exists — append new test functions (do not create new file)

*All new tests are additions to existing test files — no new test infrastructure needed.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| MCP tool appears in Claude agent tool list | MCP-01/02/03/06 | Requires live MCP connection | Start server, connect agent, verify tools listed |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 15s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
