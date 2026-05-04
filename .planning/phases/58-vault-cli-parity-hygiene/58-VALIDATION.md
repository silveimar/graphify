---
phase: 58
slug: vault-cli-parity-hygiene
status: approved
nyquist_compliant: true
wave_0_complete: true
created: 2026-05-03
post_execution_audit: 2026-05-03 (v1.11-MILESTONE-AUDIT) — full suite green at 2105 passed, 1 xfailed
---

# Phase 58 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 7.x (existing) |
| **Config file** | `pyproject.toml` (no separate pytest config) |
| **Quick run command** | `pytest tests/test_vault_parity.py tests/test_vault_cli.py tests/test_doctor.py tests/test_detect.py -q` |
| **Full suite command** | `pytest tests/ -q` |
| **Estimated runtime** | quick ~10s · full ~80s |

---

## Sampling Rate

- **After every task commit:** Run quick command (focused on touched test files)
- **After every plan wave:** Run full suite command
- **Before `/gsd-verify-work`:** Full suite must be green
- **Max feedback latency:** 10 seconds (quick) / 80 seconds (full)

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 58-01-01 | 01 | 1 | VAUX-01 | — | Parity helper returns identical dict for CLI dispatch and doctor surfaces | unit (tdd) | `pytest tests/test_vault_parity.py -q` | ❌ W0 | ⬜ pending |
| 58-01-02 | 01 | 1 | VAUX-01 | — | All 4 dimensions agree (path, source label, profile/mode, warnings) across multiple resolution scenarios | unit (tdd) | `pytest tests/test_vault_parity.py -q -k dimensions` | ❌ W0 | ⬜ pending |
| 58-02-01 | 02 | 1 | VAUX-02 | — | `_emit_vault_error()` companion to `_refuse()` emits `[graphify] error:` + `  hint:` lines and exits non-zero | unit (tdd) | `pytest tests/test_vault_cli.py -q -k emit_vault_error` | ❌ W0 | ⬜ pending |
| 58-02-02 | 02 | 1 | VAUX-02 | — | "Unknown vault" — 3 sub-cases (path doesn't exist, no .obsidian/, file not dir) all emit hint and exit non-zero | unit (tdd) | `pytest tests/test_vault_cli.py -q -k unknown_vault` | ❌ W0 | ⬜ pending |
| 58-02-03 | 02 | 1 | VAUX-02 | — | "Ambiguous selection" — `--vault-list` with 2+ matches exits 2 with clear hint | unit (tdd) | `pytest tests/test_vault_cli.py -q -k ambiguous` | ❌ W0 | ⬜ pending |
| 58-02-04 | 02 | 1 | VAUX-02 | — | Existing precedence warnings (global vs per-command, env vs flag) present and worded clearly — NOT promoted to errors | unit | `pytest tests/test_vault_cli.py -q -k precedence_warning` | ❌ W0 | ⬜ pending |
| 58-02-05 | 02 | 2 | VAUX-02 | — | "Dry-run mismatch" — `doctor --dry-run` resolution agrees with `run` resolution via parity helper | unit (tdd) | `pytest tests/test_vault_parity.py -q -k dry_run` | ❌ W0 | ⬜ pending |
| 58-03-01 | 03 | 1 | HYG-01 | — | `_SELF_OUTPUT_DIRS` constant in `corpus_prune` excludes `graphify-out` and `graphify_out` | unit | `pytest tests/test_detect.py -q -k self_output_dirs_constant` | ✅ existing module | ⬜ pending |
| 58-03-02 | 03 | 1 | HYG-01 | — | `58-VERIFICATION.md` cites `260427-rc7-SUMMARY.md` and quick-task commit | doc | `grep -F '260427-rc7-fix-detect-self-ingestion' .planning/phases/58-vault-cli-parity-hygiene/58-VERIFICATION.md` | N/A (verifier writes) | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/test_vault_parity.py` — new module hosting VAUX-01 + VAUX-02 dry-run-mismatch tests
- [ ] `tests/test_vault_cli.py` — extend with `_emit_vault_error` shape tests and 3 actionable-error categories (unknown vault, ambiguous, precedence warnings)
- [ ] `tests/test_detect.py` — append `test_self_output_dirs_constant` (named regression-lock guard for HYG-01)
- [ ] No new fixture infrastructure — reuse `tests/test_doctor.py:_make_vault()` pattern via import

*Existing infrastructure (pytest, tmp_path, _make_vault helper) covers all phase needs.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| `58-VERIFICATION.md` HYG-01 evidence narrative | HYG-01 | Verification doc is human-curated; pytest only checks file presence and citation grep | Reviewer reads `58-VERIFICATION.md` and confirms quick-task SUMMARY + commit hash are cited with non-empty rationale |

*All other phase behaviors have automated pytest verification.*

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 80s (full suite)
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
