---
phase: 63
slug: vopt-vault-option-b-silent-reroute-explain-paths
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-05-05
---

# Phase 63 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution. Derived from `63-RESEARCH.md ## Validation Architecture`.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest (Python 3.10+, CI matrix 3.10 / 3.12) |
| **Config file** | `pyproject.toml` (project section) — no separate pytest.ini |
| **Quick run command** | `pytest tests/test_output_path_matrix.py tests/test_explain_paths.py tests/test_vault_cwd.py -q` |
| **Full suite command** | `pytest tests/ -q` |
| **Estimated runtime** | ~3 s quick / ~60 s full |

---

## Sampling Rate

- **After every task commit:** `pytest tests/test_output_path_matrix.py tests/test_explain_paths.py tests/test_vault_cwd.py tests/test_output.py -q`
- **After every plan wave:** `pytest tests/ -q`
- **Before `/gsd-verify-work`:** Full suite must be green
- **Max feedback latency:** ~3 s for the per-task subset

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 63-01-RED | 01 | 0 | VOPT-01/02 | — | N/A | unit | `pytest tests/test_output_path_matrix.py -k option_b -q` | ❌ W0 | ⬜ pending |
| 63-01-* | 01 | 1 | VOPT-01 | — | strict trigger gate (no Option B when `--output` or `--obsidian-dir` is set) | unit | `pytest tests/test_output_path_matrix.py::test_option_b_vault_no_profile_reroutes_to_hidden -x` | ❌ W0 | ⬜ pending |
| 63-01-* | 01 | 1 | VOPT-01 | — | suppression by `--obsidian-dir` | unit | `pytest tests/test_output_path_matrix.py::test_option_b_suppressed_by_obsidian_dir -x` | ❌ W0 | ⬜ pending |
| 63-01-* | 01 | 1 | VOPT-01 | — | suppression by `--output` | unit | `pytest tests/test_output_path_matrix.py::test_option_b_suppressed_by_cli_output -x` | ❌ W0 | ⬜ pending |
| 63-01-* | 01 | 1 | — | — | non-vault regression | unit | `pytest tests/test_output.py::test_default_graphify_artifacts_dir_nonvault_uses_cwd_not_target_subdir -x` | ✅ | ⬜ pending |
| 63-01-* | 01 | 1 | VOPT-02 | — | two-line breadcrumb shape | unit (capsys) | `pytest tests/test_output_path_matrix.py::test_option_b_breadcrumb_shape -x` | ❌ W0 | ⬜ pending |
| 63-01-* | 01 | 1 | VOPT-02 | — | VCWD-03 gate harmonized — no double-emit | unit | `pytest tests/test_vault_cwd.py -k no_profile -q` | ✅ (assertions to update) | ⬜ pending |
| 63-02-* | 02 | 1 | VOPT-03 | — | `--explain-paths` exits 0, no pipeline | integration (subprocess) | `pytest tests/test_explain_paths.py -x` | ❌ W0 | ⬜ pending |
| 63-02-* | 02 | 1 | VOPT-03 | — | resolution label includes `option-b` | unit | `pytest tests/test_explain_paths.py::test_explain_paths_reports_option_b -x` | ❌ W0 | ⬜ pending |
| 63-03-* | 03 | 2 | VOPT-02 | — | third hint line on legacy `graphify-out/` detect | unit | `pytest tests/test_output_path_matrix.py::test_option_b_legacy_dir_emits_third_hint -x` | ❌ W0 | ⬜ pending |
| 63-03-* | 03 | 2 | — | — | routing-audit unchanged (Success #4) | unit | `pytest tests/test_routing_audit.py -x` | ✅ | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/test_explain_paths.py` — new file; covers VOPT-03 table format, exit 0, no pipeline run
- [ ] Append ~6 Option B cases to `tests/test_output_path_matrix.py` (existing file from Phase 70.1)
- [ ] Update assertions in `tests/test_vault_cwd.py` for the no-profile branch (was `exit 2` refusal, now `exit 0` + reroute) — VCWD-03 harmonization

*Existing infra — no new fixtures or framework installs required.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Visual sanity of `--explain-paths` table on a real vault | VOPT-03 | TUI/copy-paste readability | Run `graphify --explain-paths` from inside an Obsidian vault with `.obsidian/` and no profile; eyeball that the 5 rows align and the `resolution: option-b (silent reroute)` label is correct. |

*All other phase behaviors have automated verification.*

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 5 s
- [ ] `nyquist_compliant: true` set in frontmatter (after planner consumes this)

**Approval:** pending
