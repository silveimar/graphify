---
phase: 27
slug: vault-detection-profile-driven-output-routing
status: draft
nyquist_compliant: true
wave_0_complete: true
created: 2026-04-27
---

# Phase 27 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest (existing — no install needed) |
| **Config file** | `pyproject.toml` (test discovery via `tests/` dir) |
| **Quick run command** | `pytest tests/test_profile.py tests/test_output.py tests/test_main_flags.py -q` |
| **Full suite command** | `pytest tests/ -q` |
| **Estimated runtime** | ~25 seconds (full suite ~1597 tests already in repo) |

---

## Sampling Rate

- **After every task commit:** Run quick command (`pytest tests/test_profile.py tests/test_output.py tests/test_main_flags.py -q`)
- **After every plan wave:** Run full suite (`pytest tests/ -q`)
- **Before `/gsd-verify-work`:** Full suite must be green
- **Max feedback latency:** ~5 seconds for quick, ~25 seconds for full

---

## Per-Task Verification Map

> Plans are TBD; this skeleton is filled by the planner. The planner MUST add a row per task and verify each row maps to one of VAULT-08, VAULT-09, VAULT-10.

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 27-XX-XX | TBD | 0 | REQ-VAULT-{08\|09\|10} | — | TBD | unit | `pytest tests/test_*.py::test_* -q` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/test_output.py` — new file: `ResolvedOutput` resolution under all branches (vault+profile, vault+flag, no-vault default, refusal cases)
- [ ] `tests/test_profile.py` — append cases for `output:` schema validation (3 modes × valid/invalid), `validate_sibling_path()` edge cases
- [ ] `tests/test_main_flags.py` — new file (or append to existing CLI test): `--output <path>` flag override, single-line stderr precedence message, vault-detection report
- [ ] No new framework install — pytest already present.

*If none: not applicable — three new/extended test modules required.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| End-to-end vault adoption from a real Obsidian vault on disk | VAULT-08, VAULT-09 | Verifies `Path('.obsidian').is_dir()` against a non-tmp_path real vault structure with `.graphify/profile.yaml` | 1. `cd /tmp/fake-vault` (with `.obsidian/`, `.graphify/profile.yaml output: { mode: vault-relative, path: "Atlas/Generated/graphify" }`); 2. Run `graphify`; 3. Verify stderr reports vault detection; 4. Verify rendered notes land at `/tmp/fake-vault/Atlas/Generated/graphify/`; 5. Verify build artifacts land at `/tmp/fake-vault/../graphify-out/` |

*If none: "All phase behaviors have automated verification."*

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references (`tests/test_output.py`, extensions to `test_profile.py`, `tests/test_main_flags.py`)
- [ ] No watch-mode flags
- [ ] Feedback latency < 30s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
