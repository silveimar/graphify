---
phase: 08
slug: obsidian-round-trip-awareness
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-04-12
---

# Phase 08 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest |
| **Config file** | pyproject.toml (`[tool.pytest.ini_options]`) |
| **Quick run command** | `pytest tests/test_merge.py -q` |
| **Full suite command** | `pytest tests/ -q` |
| **Estimated runtime** | ~0.2 seconds |

---

## Sampling Rate

- **After every task commit:** Run `pytest tests/test_merge.py -q`
- **After every plan wave:** Run `pytest tests/ -q`
- **Before `/gsd-verify-work`:** Full suite must be green
- **Max feedback latency:** 1 second

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 08-01-01 | 01 | 0 | TRIP-01 | — | N/A | unit | `pytest tests/test_merge.py -q -k "manifest"` | ❌ W0 | ⬜ pending |
| 08-01-02 | 01 | 0 | TRIP-01 | — | N/A | unit | `pytest tests/test_merge.py -q -k "manifest_atomic"` | ❌ W0 | ⬜ pending |
| 08-01-03 | 01 | 0 | TRIP-01 | — | N/A | unit | `pytest tests/test_merge.py -q -k "manifest_none"` | ❌ W0 | ⬜ pending |
| 08-01-04 | 01 | 1 | TRIP-02 | — | N/A | unit | `pytest tests/test_merge.py -q -k "user_modified"` | ❌ W0 | ⬜ pending |
| 08-01-05 | 01 | 1 | TRIP-02 | — | N/A | unit | `pytest tests/test_merge.py -q -k "hash_match"` | ❌ W0 | ⬜ pending |
| 08-01-06 | 01 | 1 | TRIP-02 | — | N/A | unit | `pytest tests/test_merge.py -q -k "missing_manifest"` | ❌ W0 | ⬜ pending |
| 08-01-07 | 01 | 1 | TRIP-02 | V5 | `_load_manifest()` falls back to `{}` on corrupt JSON | unit | `pytest tests/test_merge.py -q -k "corrupt_manifest"` | ❌ W0 | ⬜ pending |
| 08-02-01 | 02 | 1 | TRIP-03 | — | N/A | unit | `pytest tests/test_merge.py -q -k "skip_preserve_user"` | ❌ W0 | ⬜ pending |
| 08-02-02 | 02 | 1 | TRIP-04 | — | N/A | unit | `pytest tests/test_merge.py -q -k "user_sentinel"` | ❌ W0 | ⬜ pending |
| 08-02-03 | 02 | 1 | TRIP-04 | — | N/A | unit | `pytest tests/test_merge.py -q -k "user_sentinel_malformed"` | ❌ W0 | ⬜ pending |
| 08-02-04 | 02 | 1 | TRIP-04 | — | N/A | unit | `pytest tests/test_merge.py -q -k "user_sentinel_multiple"` | ❌ W0 | ⬜ pending |
| 08-02-05 | 02 | 1 | TRIP-06 | — | N/A | unit | `pytest tests/test_merge.py -q -k "sentinel_preserve_replace"` | ❌ W0 | ⬜ pending |
| 08-02-06 | 02 | 1 | TRIP-06 | — | N/A | unit | `pytest tests/test_merge.py -q -k "sentinel_preserve_update"` | ❌ W0 | ⬜ pending |
| 08-03-01 | 03 | 2 | TRIP-05 | — | N/A | unit | `pytest tests/test_merge.py -q -k "format_preamble"` | ❌ W0 | ⬜ pending |
| 08-03-02 | 03 | 2 | TRIP-05 | — | N/A | unit | `pytest tests/test_merge.py -q -k "format_source"` | ❌ W0 | ⬜ pending |
| 08-03-03 | 03 | 2 | TRIP-07 | — | N/A | unit | `pytest tests/test_merge.py -q -k "merge_action_source"` | ❌ W0 | ⬜ pending |
| 08-03-04 | 03 | 2 | TRIP-07 | — | N/A | unit | `pytest tests/test_merge.py -q -k "source_both"` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `TestVaultManifest` class in `tests/test_merge.py` — stubs for TRIP-01
- [ ] `TestUserModifiedDetection` class in `tests/test_merge.py` — stubs for TRIP-02, TRIP-03
- [ ] `TestUserSentinelParser` class in `tests/test_merge.py` — stubs for TRIP-04
- [ ] `TestFormatMergePlanRoundTrip` class in `tests/test_merge.py` — stubs for TRIP-05, TRIP-07
- [ ] `TestUserSentinelPreservation` class in `tests/test_merge.py` — stubs for TRIP-06

*Existing tests (110 passing) must remain green — new tests are additive.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| `--dry-run` output is human-readable | TRIP-05 | Visual inspection | Run `graphify --obsidian --dry-run` on vault with user-modified notes; verify table + summary line |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 1s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
