---
phase: 59
slug: vault-cwd-aware-cli-default
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-05-04
---

# Phase 59 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest >= 7 (per `pyproject.toml [test]` extra) |
| **Config file** | `pyproject.toml` (no separate pytest.ini) |
| **Quick run command** | `pytest tests/test_vault_cwd.py -x -q` |
| **Full suite command** | `pytest tests/ -q` |
| **Estimated runtime** | ~25 seconds (full suite ~120s) |

---

## Sampling Rate

- **After every task commit:** Run `pytest tests/test_vault_cwd.py -x -q`
- **After every plan wave:** Run `pytest tests/test_vault_cwd.py tests/test_vault_cli.py tests/test_doctor.py tests/test_main_flags.py tests/test_e2e_integration.py -q`
- **Before `/gsd-verify-work`:** Full suite must be green (≥ 2123 baseline + delta from new VCWD coverage)
- **Max feedback latency:** 30 seconds for quick run

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 59-01-W0 | 01 | 0 | — (infra) | — | tmp_path-confined fixtures | infra | `pytest tests/test_vault_cwd.py -x -q --collect-only` | ❌ W0 | ⬜ pending |
| 59-01-01 | 01 | 1 | VCWD-01 | — | Detect `.obsidian/` only via `is_obsidian_vault()` | unit | `pytest tests/test_vault_cwd.py::test_gate_runs_for_each_gated_cmd -x` | ❌ W0 | ⬜ pending |
| 59-01-02 | 01 | 1 | VCWD-01 | — | Skip detection on read-only commands | integration | `pytest tests/test_vault_cwd.py::test_gate_skipped_for_readonly_cmds -x` | ❌ W0 | ⬜ pending |
| 59-02-01 | 02 | 1 | VCWD-02 | — | Auto-route via `_resolve_output_target` with `Path.cwd()` | unit | `pytest tests/test_vault_cwd.py::test_auto_adopt_matches_explicit_vault -x` | ❌ W0 | ⬜ pending |
| 59-02-02 | 02 | 1 | VCWD-02 | — | Single stderr notice line | integration | `pytest tests/test_vault_cwd.py::test_auto_adopt_notice_emitted_once -x` | ❌ W0 | ⬜ pending |
| 59-02-03 | 02 | 1 | VCWD-02 | — | Explicit `--vault $CWD` no notice | integration | `pytest tests/test_vault_cwd.py::test_explicit_vault_no_auto_adopt_notice -x` | ❌ W0 | ⬜ pending |
| 59-03-01 | 03 | 2 | VCWD-03 | — | Exit 2 + two-line stderr via `_emit_vault_error` | integration | `pytest tests/test_vault_cwd.py::test_refusal_exit_code_and_format -x` | ❌ W0 | ⬜ pending |
| 59-03-02 | 03 | 2 | VCWD-03 | — | Refusal text matches CONTEXT Decision 4 verbatim; `<cwd>` sanitized | integration | `pytest tests/test_vault_cwd.py::test_refusal_message_text -x` | ❌ W0 | ⬜ pending |
| 59-04-01 | 04 | 2 | VCWD-04 | — | Per-command flag suppresses refusal | integration | `pytest tests/test_vault_cwd.py::test_write_into_vault_suppresses_refusal -x` | ❌ W0 | ⬜ pending |
| 59-04-02 | 04 | 2 | VCWD-04 | — | Global leading flag suppresses refusal | integration | `pytest tests/test_vault_cwd.py::test_global_write_into_vault_suppresses_refusal -x` | ❌ W0 | ⬜ pending |
| 59-04-03 | 04 | 2 | VCWD-04 | — | Silent precedence vs `--vault`/`--output` | integration | `pytest tests/test_vault_cwd.py::test_write_into_vault_silent_precedence -x` | ❌ W0 | ⬜ pending |
| 59-04-04 | 04 | 2 | VCWD-04 | — | Does NOT suppress VCWD-02 auto-adopt | integration | `pytest tests/test_vault_cwd.py::test_write_into_vault_yields_to_profile -x` | ❌ W0 | ⬜ pending |
| 59-05-01 | 05 | 3 | VCWD-05 | — | `[vault-cwd]` section always shown | integration | `pytest tests/test_vault_cwd.py::test_doctor_vault_cwd_section_always_shown -x` | ❌ W0 | ⬜ pending |
| 59-05-02 | 05 | 3 | VCWD-05 | — | Parity: doctor outcome == runtime gate | integration | `pytest tests/test_vault_cwd.py::test_doctor_runtime_parity -x` | ❌ W0 | ⬜ pending |
| 59-05-03 | 05 | 3 | VCWD-05 | — | All three outcomes reachable | integration | `pytest tests/test_vault_cwd.py::test_doctor_three_outcomes -x` | ❌ W0 | ⬜ pending |
| 59-X-01 | cross | 3 | VCWD-01..04 | — | `GRAPHIFY_VAULT` env pin treated as explicit route | integration | `pytest tests/test_vault_cwd.py::test_env_pin_disables_gate -x` | ❌ W0 | ⬜ pending |
| 59-X-02 | cross | 3 | VCWD-01..04 | — | `--vault-list` treated as explicit route | integration | `pytest tests/test_vault_cwd.py::test_vault_list_disables_gate -x` | ❌ W0 | ⬜ pending |
| 59-R-01 | regr | 3 | — | — | Phase 41 vault CLI tests still green | regression | `pytest tests/test_vault_cli.py -q` | ✅ exists | ⬜ pending |
| 59-R-02 | regr | 3 | — | — | Phase 60 E2E still green | regression | `pytest tests/test_e2e_integration.py -q` | ✅ exists | ⬜ pending |
| 59-R-03 | regr | 3 | — | — | Full suite green; ≥ 2123 baseline | regression | `pytest tests/ -q` | ✅ | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/test_vault_cwd.py` — new file housing all 17 VCWD test rows above
- [ ] `_make_partial_vault(parent, *, with_profile: bool)` fixture (mirrors `tests/test_vault_cli.py::_make_vault` and `tests/test_e2e_integration.py::_write_vault`)
- [ ] No-vault fixture for VCWD-05 `n/a` outcome (parent dir without `.obsidian/`)
- [ ] `pytest.importorskip("yaml")` only in tests that actually load profiles (VCWD-02 with-profile cases)

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| (none) | — | All VCWD behaviors are subprocess-testable via stderr/exit-code/stdout assertions | — |

*All phase behaviors have automated verification.*

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references (`tests/test_vault_cwd.py` + fixtures)
- [ ] No watch-mode flags (subprocess tests are deterministic)
- [ ] Feedback latency < 30s on quick run
- [ ] `nyquist_compliant: true` set in frontmatter after planner pass

**Approval:** pending
