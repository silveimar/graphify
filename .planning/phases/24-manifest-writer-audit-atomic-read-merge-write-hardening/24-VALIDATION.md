---
phase: 24
slug: manifest-writer-audit-atomic-read-merge-write-hardening
status: validated
nyquist_compliant: true
wave_0_complete: true
created: 2026-04-27
last_audited: 2026-04-27
---

# Phase 24 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest (project-pinned, configured via pyproject.toml) |
| **Config file** | none detected (`[tool.pytest.ini_options]` absent in pyproject.toml — pytest defaults apply) |
| **Quick run command** | `pytest tests/test_routing_audit.py tests/test_capability.py tests/test_vault_promote.py -q` |
| **Full suite command** | `pytest tests/ -q` |
| **Estimated runtime** | ~3 seconds quick run; ~30 seconds full suite |

---

## Sampling Rate

- **After every task commit:** Run `pytest tests/test_routing_audit.py tests/test_capability.py tests/test_vault_promote.py -q`
- **After every plan wave:** Run `pytest tests/ -q`
- **Before `/gsd-verify-work`:** Full suite must be green
- **Max feedback latency:** ~30 seconds (full suite); ~3 seconds (quick run)

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 24-01-W0a | 01 | 0 | MANIFEST-11 | — | N/A | unit | `pytest tests/test_routing_audit.py::test_subpath_isolation_routing -x` | ✅ tests/test_routing_audit.py:12 | ✅ green |
| 24-01-W0b | 01 | 0 | MANIFEST-11 | — | N/A | unit | `pytest tests/test_capability.py::test_subpath_isolation_capability_manifest -x` | ✅ tests/test_capability.py:409 | ✅ green |
| 24-01-W0c | 01 | 0 | MANIFEST-11 | — | N/A | unit | `pytest tests/test_vault_promote.py::test_subpath_isolation_vault_manifest -x` | ✅ tests/test_vault_promote.py:824 | ✅ green |
| 24-01-01 | 01 | 1 | MANIFEST-09, MANIFEST-10 | T-24-01: corrupt manifest → DoS | try/except → `{}` on `JSONDecodeError` / `OSError`; preserves availability | unit | `pytest tests/test_routing_audit.py -q` | ✅ existing | ✅ green |
| 24-01-02 | 01 | 1 | MANIFEST-09, MANIFEST-10 | T-24-02: `.tmp` left behind on crash | `except` calls `tmp.unlink(missing_ok=True)` | unit | `pytest tests/test_capability.py -q` | ✅ existing | ✅ green |
| 24-01-03 | 01 | 1 | MANIFEST-11 | — | N/A (locks existing contract) | unit | `pytest tests/test_vault_promote.py -q` | ✅ existing | ✅ green |
| 24-02-01 | 02 | 2 | MANIFEST-12 | — | N/A (artifact only) | manual | inspect `.planning/phases/24-*/AUDIT.md` matches policy diff schema | ✅ AUDIT.md present | ✅ green |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

*Note: Task IDs are illustrative — final IDs assigned by the planner. The verification map covers the three new subpath-isolation tests (Wave 0 stubs in Wave 0; full red→green transitions in Wave 1) plus the AUDIT.md artifact (Wave 2). Each row maps to a phase requirement and an automated or manual verification command.*

---

## Wave 0 Requirements

- [x] `tests/test_routing_audit.py` — new file, covers MANIFEST-09 / MANIFEST-11 for routing.json (`test_subpath_isolation_routing` at line 12)
- [x] `tests/test_capability.py::test_subpath_isolation_capability_manifest` — function added at line 409
- [x] `tests/test_vault_promote.py::test_subpath_isolation_vault_manifest` — function added at line 824
- [x] `.planning/phases/24-manifest-writer-audit-atomic-read-merge-write-hardening/AUDIT.md` — MANIFEST-12 artifact present (5-row policy-diff table)

*Existing infrastructure: pytest is already in place. No framework install required. tmp_path fixture already used across tests/ — no conftest.py changes needed.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| AUDIT.md schema correctness | MANIFEST-12 | Document content review — table columns, writer enumeration, policy diff accuracy | Open `.planning/phases/24-*/AUDIT.md`. Verify single table with columns: manifest filename, writer (file:function:line), invocation site, row identity key, pre-fix read?, pre-fix atomic?, post-fix read?, post-fix atomic?, Phase 24 action. Verify rows for: vault-manifest.json (LOCKED), seeds-manifest.json (LOCKED), routing.json (PATCHED), capability.json (PATCHED), graphify-out/manifest.json (DEFERRED). Verify ~1 page total. |

---

## Validation Sign-Off

- [x] All tasks have `<automated>` verify or Wave 0 dependencies
- [x] Sampling continuity: no 3 consecutive tasks without automated verify
- [x] Wave 0 covers all MISSING references (3 new test functions + AUDIT.md artifact)
- [x] No watch-mode flags
- [x] Feedback latency < 30s (full suite); < 3s (quick run — actual: 0.96s for 55 tests)
- [x] `nyquist_compliant: true` set in frontmatter

**Approval:** validated 2026-04-27 by `/gsd-validate-phase 24`

---

## Validation Audit 2026-04-27

| Metric | Count |
|--------|-------|
| Gaps found | 0 |
| Resolved | 0 |
| Escalated | 0 |
| Bookkeeping fixes | 7 statuses ⬜→✅, frontmatter draft→validated, Wave 0 + Sign-Off ticked |

All 7 Per-Task Map entries (24-01-W0a/b/c, 24-01-01/02/03, 24-02-01) classify as **COVERED**. The three new subpath-isolation tests landed in their respective files (verified by line-number grep) and the MANIFEST-12 AUDIT.md artifact exists at the prescribed path. Quick-run re-confirmed live: `pytest tests/test_routing_audit.py tests/test_capability.py tests/test_vault_promote.py -q` → **55 passed in 0.96s**. No auditor agent spawned — bookkeeping-only.
