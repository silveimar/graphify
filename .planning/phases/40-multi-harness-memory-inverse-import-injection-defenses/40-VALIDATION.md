---
phase: 40
slug: multi-harness-memory-inverse-import-injection-defenses
status: approved
nyquist_compliant: true
wave_0_complete: true
created: 2026-04-29
---

# Phase 40 — Validation Strategy

> Per-phase validation contract: requirement coverage via automated tests (Nyquist).

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest |
| **Config file** | `pyproject.toml` (project metadata; no `pytest.ini`) |
| **Quick run command** | `pytest tests/test_harness_interchange.py tests/test_harness_import.py tests/test_mcp_harness_io.py tests/test_harness_export.py -q` |
| **Full suite command** | `pytest tests/ -q` |
| **Estimated runtime** | ~60–90 s (full suite) |

---

## Sampling Rate

- **After every task commit:** Run targeted harness tests above.
- **After every plan wave:** Run full `pytest tests/ -q`.
- **Before `/gsd-verify-work`:** Full suite must be green.

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 01-01 | 01 | 1 | PORT-01, PORT-02, SEC-02 | T-40-01, T-40-02 | Interchange JSON + provenance; extraction validates | unit | `pytest tests/test_harness_interchange.py -q` | ✅ | ✅ green |
| 01-02 | 01 | 1 | PORT-01 | T-40-01 | CLI `--format` writes confined interchange file | unit | `pytest tests/test_harness_interchange.py::test_cli_harness_export_format_interchange -q` | ✅ | ✅ green |
| 02-01 | 02 | 2 | PORT-03, PORT-05, SEC-01 | T-40-03–05 | Import sanitizes; path/size enforced | unit | `pytest tests/test_harness_import.py -q` | ✅ | ✅ green |
| 02-02 | 02 | 2 | PORT-03 | — | Module docstring documents limits / elicitation | unit | `pytest tests/test_harness_import.py::test_module_docstring_mentions_elicitation -q` | ✅ | ✅ green |
| 03-01 | 03 | 3 | PORT-03, PORT-05 | T-40-06 | `import-harness` subcommand | unit | `pytest tests/test_harness_import.py::test_cli_import_harness_smoke -q` | ✅ | ✅ green |
| 04-01 | 04 | 3 | SEC-03, SEC-04 | T-40-08–10 | MCP tools + handlers delegate to library | unit | `pytest tests/test_mcp_harness_io.py -q` | ✅ | ✅ green |
| 04-02 | 04 | 3 | SEC-04 | — | SECURITY.md harness subsection + traceability | unit | `pytest tests/test_mcp_harness_io.py::test_security_md_phase40_harness_traceability -q` | ✅ | ✅ green |
| 05-01 | 05 | 4 | PORT-04 | T-40-RT | Export→import semantic preservation | unit | `pytest tests/test_harness_interchange.py::test_export_import_semantic_ids_labels_relations -q` | ✅ | ✅ green |

*Status: ✅ green*

---

## Wave 0 Requirements

Existing infrastructure covers all phase requirements — no Wave 0 stubs required.

---

## Manual-Only Verifications

All phase behaviors targeted by plans have automated verification.

---

## Validation Sign-Off

- [x] All tasks have automated verify coverage
- [x] No watch-mode-only gates
- [x] `nyquist_compliant: true` set in frontmatter

**Approval:** approved 2026-04-29

---

## Validation Audit 2026-04-29

| Metric | Count |
|--------|-------|
| Gaps found | 1 |
| Resolved | 1 |
| Escalated | 0 |

Gap addressed: SEC-04 SECURITY.md traceability previously relied on ad-hoc `python -c`; added `test_security_md_phase40_harness_traceability`.
