---
phase: 70
slug: vrsync-vault-input-reverse-sync-user-file-augmentation
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-05-05
---

# Phase 70 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 7.x (existing) |
| **Config file** | pyproject.toml `[tool.pytest.ini_options]` |
| **Quick run command** | `pytest tests/test_reverse_sync.py tests/test_augment.py tests/test_profile.py -q` |
| **Full suite command** | `pytest tests/ -q` |
| **Estimated runtime** | ~6s quick, ~45s full |

---

## Sampling Rate

- **After every task commit:** Run quick command
- **After every plan wave:** Run full suite
- **Before `/gsd-verify-work`:** Full suite must be green
- **Max feedback latency:** 10 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 70-01-* | 01 | 1 | VPROF-03 (aug) | — | Frontmatter merge preserves user list order; never overwrites scalar; community key gated | unit + property | `pytest tests/test_augment.py -q` | ❌ W0 | ⬜ pending |
| 70-02-* | 02 | 1 | VRSYNC-01 (detect) | — | SHA256 raw-bytes change detection; markdown-only recursive scan; symmetric to user_only_folders | unit | `pytest tests/test_reverse_sync.py::test_detect -q` | ❌ W0 | ⬜ pending |
| 70-03-* | 03 | 2 | VRSYNC-01 (modes) | — | always_ask Y/n/d/A/Q; --yes overrides only always_ask not never_copy; non-TTY skips | unit | `pytest tests/test_reverse_sync.py::test_modes -q` | ❌ W0 | ⬜ pending |
| 70-04-* | 04 | 2 | VRSYNC-01 (log) | — | JSONL append-only; action enum recorded; vault_deleted logged not propagated | unit | `pytest tests/test_reverse_sync.py::test_jsonl -q` | ❌ W0 | ⬜ pending |
| 70-05-* | 05 | 3 | VRSYNC-01 (auto_on_run) | — | Hooks into run/update-vault; warn-and-continue on failure; non-blocking | integration | `pytest tests/test_main.py::test_auto_on_run -q` | ❌ W0 | ⬜ pending |
| 70-06-* | 06 | 3 | VPROF-03 + VRSYNC-01 | — | Doctor section non-blocking; pending-conflict count; profile schema additive defaults | integration | `pytest tests/test_doctor.py::test_reverse_sync_section -q` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/test_reverse_sync.py` — RED tests for VRSYNC-01 detection, modes, JSONL, auto_on_run, deletion-log-only
- [ ] `tests/test_augment.py` — RED tests for VPROF-03 augmentation: list-union (D-04), scalar-preserve (D-05), stateless re-add (D-06), byte-identical body property test (D-07), community gate (D-16)
- [ ] `tests/test_profile.py` — extend with reverse_sync.* and augment.* default-merge cases (additive schema)
- [ ] `tests/conftest.py` — shared fixture: dual-tree vault+input tmp_path setup, profile factory with user_only_folders preset

*Property test (D-07):** Use stdlib `random` (per RESEARCH A1; no Hypothesis dependency added). Generate 50 random markdown bodies (varied line endings, BOM, trailing whitespace, embedded `---`), augment frontmatter, assert body bytes unchanged.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| TTY prompt UX (color, line wrap, [d] re-prompt flow) | VRSYNC-01 (modes) | Subjective UX; hard to assert in unit tests beyond key-handling logic | Run `graphify reverse-sync` against a vault with 3+ conflicting files; verify Y/n/d/A/Q flow matches D-01..D-02 |
| auto_on_run integration in real `graphify run` | VRSYNC-01 (auto_on_run) | Full pipeline integration; covered by integration test but worth one manual smoke | Set `reverse_sync.auto_on_run: true` in profile; modify a vault user file; run `graphify run`; verify stderr warning + log entry without aborting |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 10s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
