---
phase: 29
slug: doctor-diagnostics-dry-run-preview
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-04-28
---

# Phase 29 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 7.x (already installed; `pyproject.toml` extras) |
| **Config file** | `pyproject.toml` `[tool.pytest.ini_options]` (none required for new tests) |
| **Quick run command** | `pytest tests/test_doctor.py tests/test_detect.py::test_detect_skip_reasons tests/test_main_flags.py -q` |
| **Full suite command** | `pytest tests/ -q` |
| **Estimated runtime** | ~3s quick / ~45s full suite (current baseline 1657 passed) |

---

## Sampling Rate

- **After every task commit:** Run quick run command (target: under 3s)
- **After every plan wave:** Run full suite command
- **Before `/gsd-verify-work`:** Full suite must be green (current baseline: 1657 passed + 1 xfailed)
- **Max feedback latency:** 5 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 29-01 | doctor.py module | 0 | VAULT-14 | — | `run_doctor()` reports vault detection status when `.obsidian/` present | unit | `pytest tests/test_doctor.py::test_run_doctor_vault_detected -q` | ❌ W0 | ⬜ pending |
| 29-01 | doctor.py module | 0 | VAULT-14 | — | `run_doctor()` reports profile validation errors when profile invalid | unit | `pytest tests/test_doctor.py::test_run_doctor_invalid_profile -q` | ❌ W0 | ⬜ pending |
| 29-01 | doctor.py module | 0 | VAULT-14 | — | `run_doctor()` populates `resolved_output` from `output.py:resolve_output` | unit | `pytest tests/test_doctor.py::test_run_doctor_resolved_output -q` | ❌ W0 | ⬜ pending |
| 29-01 | doctor.py module | 0 | VAULT-14 | — | `run_doctor()` returns `ignore_list` grouped by 4 sources (D-37) | unit | `pytest tests/test_doctor.py::test_run_doctor_ignore_list_sources -q` | ❌ W0 | ⬜ pending |
| 29-01 | doctor.py module | 0 | VAULT-14 | — | `run_doctor()` reads `output-manifest.json` and surfaces history | unit | `pytest tests/test_doctor.py::test_run_doctor_manifest_history -q` | ❌ W0 | ⬜ pending |
| 29-01 | doctor.py module | 0 | VAULT-14 | — | `run_doctor()` sets `would_self_ingest=True` when resolved dest under input scan | unit | `pytest tests/test_doctor.py::test_run_doctor_self_ingest_detected -q` | ❌ W0 | ⬜ pending |
| 29-01 | doctor.py module | 0 | VAULT-14 | — | `would_self_ingest=False` when `resolved.source == "default"` (D-12 backcompat) | unit | `pytest tests/test_doctor.py::test_run_doctor_default_paths_not_self_ingest -q` | ❌ W0 | ⬜ pending |
| 29-01 | doctor.py module | 0 | VAULT-14 | — | `format_report()` emits sections in fixed order (Vault / Profile / Output / Ignore-list / Fixes) | unit | `pytest tests/test_doctor.py::test_format_report_section_order -q` | ❌ W0 | ⬜ pending |
| 29-01 | doctor.py module | 0 | VAULT-14 | — | `format_report()` lines all `[graphify]`-prefixed | unit | `pytest tests/test_doctor.py::test_format_report_graphify_prefix -q` | ❌ W0 | ⬜ pending |
| 29-01 | doctor.py module | 0 | VAULT-14 | — | `_FIX_HINTS` mapping produces actionable fix line for each known error pattern | unit | `pytest tests/test_doctor.py::test_fix_hints_coverage -q` | ❌ W0 | ⬜ pending |
| 29-01 | doctor.py module | 0 | VAULT-14 | — | `format_report()` shows "No issues detected." when zero issues | unit | `pytest tests/test_doctor.py::test_format_report_no_issues -q` | ❌ W0 | ⬜ pending |
| 29-01 | doctor.py module | 0 | VAULT-14 | — | `run_doctor()` returns `DoctorReport` with no disk side-effects (idempotent reads only) | unit | `pytest tests/test_doctor.py::test_run_doctor_no_disk_writes -q` | ❌ W0 | ⬜ pending |
| 29-02 | detect skip-reasons | 0 | VAULT-15 | — | `detect()` returns `skipped: dict[str, list[str]]` with keys `nesting`/`exclude-glob`/`manifest`/`sensitive`/`noise-dir` | unit | `pytest tests/test_detect.py::test_detect_skip_reasons -q` | ❌ W0 | ⬜ pending |
| 29-02 | detect skip-reasons | 0 | VAULT-15 | — | Existing `detect()` callers unaffected (additive return key, ABI preserved) | unit | `pytest tests/test_detect.py -q` | ✅ | ⬜ pending |
| 29-03 | doctor preview | 0 | VAULT-15 | — | `run_doctor(dry_run=True)` includes `preview` section with bounded counts + sample paths | unit | `pytest tests/test_doctor.py::test_run_doctor_dry_run_preview -q` | ❌ W0 | ⬜ pending |
| 29-03 | doctor preview | 0 | VAULT-15 | — | Dry-run preview groups skips by reason with first 5 paths each (D-38) | unit | `pytest tests/test_doctor.py::test_dry_run_skip_grouping -q` | ❌ W0 | ⬜ pending |
| 29-03 | doctor preview | 0 | VAULT-15 | — | `run_doctor(dry_run=True)` writes nothing to disk (asserted via tmp_path inventory) | unit | `pytest tests/test_doctor.py::test_dry_run_no_disk_writes -q` | ❌ W0 | ⬜ pending |
| 29-04 | __main__ wiring | 0 | VAULT-14, VAULT-15 | — | `graphify doctor` exits 0 on clean config | integration | `pytest tests/test_main_flags.py::test_doctor_clean_exit_zero -q` | ❌ W0 | ⬜ pending |
| 29-04 | __main__ wiring | 0 | VAULT-14 | — | `graphify doctor` exits 1 on invalid profile / unresolvable dest / would-self-ingest (D-35) | integration | `pytest tests/test_main_flags.py::test_doctor_misconfig_exit_one -q` | ❌ W0 | ⬜ pending |
| 29-04 | __main__ wiring | 0 | VAULT-15 | — | `graphify doctor --dry-run` flag parses; preview section appears in output | integration | `pytest tests/test_main_flags.py::test_doctor_dry_run_flag -q` | ❌ W0 | ⬜ pending |
| 29-04 | __main__ wiring | 0 | VAULT-14 | — | `graphify doctor` listed in `--help` block | integration | `pytest tests/test_main_flags.py::test_doctor_in_help -q` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/test_doctor.py` — new file with 16 stubs covering VAULT-14 + VAULT-15 unit behaviors
- [ ] `tests/test_detect.py::test_detect_skip_reasons` — extend existing file with skip-reason surfacing assertion (VAULT-15)
- [ ] `tests/test_main_flags.py::test_doctor_*` — 4 new subprocess/CLI integration tests (or in `tests/test_main.py` if that's the existing surface — planner picks)
- [ ] `tests/conftest.py` — add fixture for synthetic vault dir (`.obsidian/` + `.graphify/profile.yaml`) if not present
- [ ] No new framework install — pytest already in `pyproject.toml` `[all]` extras

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Doctor report human-readability / scannability | VAULT-14 (S.C. #1) | Subjective — requires eyeball review for terminal alignment, section spacing, line wrapping at 80 cols | Run `graphify doctor` from a real Obsidian vault directory; verify each section header is grep-friendly and sample paths don't truncate readability |
| Recommended-fixes wording is actionable | VAULT-14 (S.C. #4) | Verb-first imperative quality is qualitative | Trigger each `_FIX_HINTS` pattern; manually confirm each fix line starts with an imperative verb and names a concrete next action |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references (3 new test files / additions)
- [ ] No watch-mode flags
- [ ] Feedback latency < 5s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
