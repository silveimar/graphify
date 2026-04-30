# Phase 40 — Verification

**Phase:** 40-multi-harness-memory-inverse-import-injection-defenses  
**Requirements:** PORT-01 — PORT-05, SEC-01 — SEC-04 (`.planning/REQUIREMENTS.md`)

## Goal

Harness interchange, import/export, MCP parity, sanitization, and round-trip tests ship with documented security posture — per plans **`40-01` … `40-05`** and **`40-SECURITY.md`**.

## Requirement coverage

| REQ-ID | Summary | Evidence |
|--------|---------|----------|
| **PORT-01** | Additional export targets / interchange | `graphify/harness_interchange.py`, export wiring; **`tests/test_harness_interchange.py`**, **`tests/test_harness_export.py`**; **`40-01-SUMMARY.md`** |
| **PORT-02** | Canonical schemas under VCS | `graphify/harness_schemas/`; referenced by import/export; **`40-01-SUMMARY.md`** |
| **PORT-03** | `import-harness` → validated extraction | `graphify/harness_import.py`, **`graphify/__main__.py`** branch; **`tests/test_harness_import.py`** |
| **PORT-04** | Export→import round-trip (limits documented) | **`tests/test_harness_import.py`** + interchange tests; **`40-05-SUMMARY.md`** |
| **PORT-05** | Path confinement / caps | `validate_graph_path`, byte caps in **`graphify/harness_import.py`** / **`security.py`**; **`tests/test_harness_import.py`**; **`40-SECURITY.md`** |
| **SEC-01** | Sanitization of imported content | `sanitize_harness_text`, `guard_harness_injection_patterns`; **`tests/test_harness_import.py`**; **`40-SECURITY.md`** |
| **SEC-02** | Provenance on exports | Interchange v1 metadata fields; **`graphify/harness_interchange.py`**; **`40-01-SUMMARY.md`** |
| **SEC-03** | MCP uses same validation as CLI | **`tests/test_mcp_harness_io.py`**; MCP tools call shared library paths (`serve.py`); **`40-04-SUMMARY.md`** |
| **SEC-04** | SECURITY.md documents threats | Root **`SECURITY.md`** § harness / MCP rows; detailed register **`40-SECURITY.md`** |

## Nyquist / VALIDATION

- Phase **`40-VALIDATION.md`** already captures structured Nyquist-style validation — **do not duplicate**; treat it as the detailed checklist.
- UAT: **`40-UAT.md`** (complete).

## Automated verification

```bash
pytest tests/test_harness_interchange.py tests/test_harness_export.py tests/test_harness_import.py tests/test_mcp_harness_io.py -q
pytest tests/ -q
```

## Status

**passed** — PORT and SEC criteria are backed by the harness modules and test modules listed; checkbox rows in **`REQUIREMENTS.md`** remain the documentation reconciliation surface for milestone bookkeeping.
