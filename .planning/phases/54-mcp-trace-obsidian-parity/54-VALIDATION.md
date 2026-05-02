---
phase: 54
slug: mcp-trace-obsidian-parity
status: approved
nyquist_compliant: true
wave_0_complete: true
created: 2026-05-02
reconstructed_from: [54-01-PLAN.md, 54-02-PLAN.md, 54-03-PLAN.md, 54-04-PLAN.md, 54-05-PLAN.md, 54-VERIFICATION.md, 54-RESEARCH.md]
---

# Phase 54 — Validation Strategy

> Per-phase validation contract. Reconstructed retroactively from completed phase artifacts. All CGRAPH-03 / CGRAPH-04 sub-requirements have automated coverage; phase is Nyquist-compliant.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 7.x (CI on Python 3.10 and 3.12) |
| **Config file** | `pyproject.toml` (no separate `pytest.ini`) |
| **Quick run command** | `pytest tests/test_concept_code_mcp.py tests/test_concept_code_obsidian.py tests/test_serve.py tests/test_capability.py -q` |
| **Full suite command** | `pytest tests/ -q` |
| **Estimated runtime** | ~5s quick / ~30s full (1995 passed at phase close, +16 net new vs Phase 53 baseline) |

---

## Sampling Rate

- **After every task commit:** Quick run command above
- **After every plan wave:** `pytest tests/ -q`
- **Before `/gsd-verify-work`:** Full suite must be green
- **Max feedback latency:** ~5s (quick) / ~30s (full)

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 54-01-01 | 01 | 1 | CGRAPH-03, CGRAPH-04 | — | RED test scaffolds for MCP + Obsidian + entity_trace + capability | unit | `pytest tests/test_concept_code_mcp.py tests/test_concept_code_obsidian.py tests/test_serve.py tests/test_capability.py -q` | ✅ | ✅ green |
| 54-02-01 | 02 | 2 | CGRAPH-03 | — | `concept_code_hops` accepts `relations` list w/ default `["implements"]`; structured-error rejection; payload shim | unit | `pytest tests/test_concept_code_mcp.py -q` | ✅ | ✅ green |
| 54-03-01 | 03 | 2 | CGRAPH-03 | — | `entity_trace.include_concept_code` (default `false`, byte-identical to Phase 11) | unit | `pytest tests/test_serve.py -k entity_trace -q` | ✅ | ✅ green |
| 54-04-01 | 04 | 3 | CGRAPH-04 | — | Forward + inverse per-relation sections (5 relations × 2 directions = 10 H2 sections); parity, idempotence, dedupe vs connections callout | unit | `pytest tests/test_concept_code_obsidian.py -q` | ✅ | ✅ green |
| 54-05-01 | 05 | 4 | CGRAPH-03, CGRAPH-04 | — | `docs/RELATIONS.md` MCP traversal section; `server.json` manifest hash sync; `54-VERIFICATION.md` produced | doc-spot-check | `grep -E "MCP traversal\|concept_code_hops\|entity_trace.include_concept_code" docs/RELATIONS.md && python scripts/sync_mcp_server_json.py --check` | ✅ | ✅ green |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

### Test → Requirement Index

**CGRAPH-03 — MCP exposes typed concept↔code traversal**

| Test | Behavior |
|------|----------|
| `tests/test_concept_code_mcp.py::test_concept_code_hops_default_relations` | `relations` defaults to `["implements"]` |
| `…::test_concept_code_hops_unknown_relation_errors` | Unknown relation → structured error (via `_validate_relations_arg`) |
| `…::test_concept_code_hops_empty_relations_errors` | Empty `relations` → structured error |
| `…::test_concept_code_hops_multi_relation_traversal` | `relations=["documents","tests"]` walks both |
| `…::test_concept_code_hops_payload_steps_by_relation` | Payload exposes `traversal_steps` + `steps_by_relation` |
| `…::test_concept_code_hops_backward_compat_implements_steps_key` | implements-only emits Phase 47 `implements_traversal_steps` shim |
| `tests/test_serve.py::test_entity_trace_default_excludes_concept_code` | `include_concept_code=False` is byte-identical to Phase 11 baseline |
| `tests/test_serve.py::test_entity_trace_includes_concept_code_when_requested` | `include_concept_code=True` merges hops into envelope |
| `tests/test_capability.py::test_concept_code_hops_schema_includes_relations_and_entity_trace_includes_concept_code` | Tool registry inputSchema declares both new params; manifest hash rotates |

**CGRAPH-04 — Obsidian export single-source-of-truth parity**

| Test | Behavior |
|------|----------|
| `tests/test_concept_code_obsidian.py::test_code_note_per_relation_sections_canonical_order` | CODE notes emit forward H2 sections in canonical order |
| `…::test_concept_moc_inverse_sections_canonical_order` | Inverse sections emit in canonical order (per A1 ADOPTED) |
| `…::test_empty_relation_section_suppressed` | Empty section is suppressed |
| `…::test_forward_parity_edges_to_wikilinks` | Every graph edge appears as `[[Label]]` under matching forward H2 |
| `…::test_backward_parity_wikilinks_to_edges` | Every wikilink under any of the 10 H2 sections maps to a graph edge with matching relation |
| `…::test_per_relation_count_parity` | `forward_count == inverse_count == graph_edge_count` per relation |
| `…::test_round_trip_per_relation_sections_idempotent` | Sentinel block byte-identical across two consecutive `to_obsidian` runs (proves no double-rendering vs connections callout) |

---

## Wave 0 Requirements

Plan 01 served as Wave 0 (RED test scaffold). All scaffolds landed in commit history before any GREEN logic — verification via VERIFICATION.md confirms this sequence.

- ✅ `tests/test_concept_code_mcp.py` extended with 6 RED tests (Plan 01)
- ✅ `tests/test_concept_code_obsidian.py` created with 7 RED tests (Plan 01)
- ✅ `tests/test_serve.py` extended with 2 `entity_trace` RED tests (Plan 01)
- ✅ `tests/test_capability.py` extended with schema-includes-params test (Plan 01)

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| `/trace` slash workflow surfacing of concept↔code edges in user-visible output | CGRAPH-03 (deferred per D-54.05) | D-54.05 explicitly deferred slash-workflow widening; `entity_trace.include_concept_code` is the data-path satisfier. No automated test for the slash command body itself. | If a future phase widens `/trace`, exercise the slash command end-to-end and assert concept↔code hops appear inline. Until then, this is intentionally not validated. |

All other behaviors have automated verification.

---

## Validation Sign-Off

- [x] All tasks have `<automated>` verify or Wave 0 dependencies
- [x] Sampling continuity: no 3 consecutive tasks without automated verify
- [x] Wave 0 covers all MISSING references (Plan 01 RED scaffolds)
- [x] No watch-mode flags
- [x] Feedback latency < 30s (full) / < 5s (quick)
- [x] `nyquist_compliant: true` set in frontmatter

**Approval:** approved 2026-05-02 (retroactive — phase shipped 2026-05-01 via gsd-executor, `83aabf2` close-out).

## Validation Audit 2026-05-02

| Metric | Count |
|--------|-------|
| Gaps found | 0 |
| Resolved | 0 |
| Escalated | 1 (D-54.05 `/trace` slash workflow body — intentionally deferred, manual-only) |
| Sub-requirements verified (from 54-VERIFICATION.md) | CGRAPH-03 ✓ + CGRAPH-04 ✓ (full mapping tables) |
| Full suite at phase close | 1995 passed, 1 xfailed, 0 failed (+16 net new vs Phase 53 baseline of 1979) |
