---
phase: 08
slug: obsidian-round-trip-awareness
status: verified
nyquist_compliant: true
wave_0_complete: true
created: 2026-04-12
updated: 2026-04-12
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
| **Estimated runtime** | ~0.07 seconds (phase tests) |

---

## Sampling Rate

- **After every task commit:** Run `pytest tests/test_merge.py -q`
- **After every plan wave:** Run `pytest tests/ -q`
- **Before `/gsd-verify-work`:** Full suite must be green
- **Max feedback latency:** 1 second

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Class / -k Filter | Test Count | Status |
|---------|------|------|-------------|----------------------|------------|--------|
| 08-01-01 | 01 | 0 | TRIP-01 | `TestVaultManifest` | 8 | ✅ green |
| 08-01-02 | 01 | 0 | TRIP-01 | `test_save_atomic_no_partial` | 1 | ✅ green |
| 08-01-03 | 01 | 0 | TRIP-01 | `test_load_missing_returns_empty` | 1 | ✅ green |
| 08-01-04 | 01 | 1 | TRIP-02 | `TestUserModifiedDetection` | 6 | ✅ green |
| 08-01-05 | 01 | 1 | TRIP-02 | `test_hash_match_proceeds_normally` | 1 | ✅ green |
| 08-01-06 | 01 | 1 | TRIP-02 | `test_missing_manifest_normal_behavior` | 1 | ✅ green |
| 08-01-07 | 01 | 1 | TRIP-02 | `test_corrupt_entry_no_content_hash` | 1 | ✅ green |
| 08-02-01 | 02 | 1 | TRIP-03 | `test_user_modified_gets_skip_preserve` | 1 | ✅ green |
| 08-02-02 | 02 | 1 | TRIP-04 | `TestUserSentinelParser` | 6 | ✅ green |
| 08-02-03 | 02 | 1 | TRIP-04 | `test_malformed_start_no_end` | 1 | ✅ green |
| 08-02-04 | 02 | 1 | TRIP-04 | `test_multiple_pairs` | 1 | ✅ green |
| 08-02-05 | 02 | 1 | TRIP-06 | `test_replace_preserves_user_blocks` | 1 | ✅ green |
| 08-02-06 | 02 | 1 | TRIP-06 | `test_update_preserves_user_blocks` | 1 | ✅ green |
| 08-03-01 | 03 | 2 | TRIP-05 | `test_format_preamble_with_user_modified` | 1 | ✅ green |
| 08-03-02 | 03 | 2 | TRIP-05 | `test_format_source_user_annotation` | 1 | ✅ green |
| 08-03-03 | 03 | 2 | TRIP-07 | `test_source_both_when_has_user_blocks` | 1 | ✅ green |
| 08-03-04 | 03 | 2 | TRIP-07 | `test_format_source_both_annotation` | 1 | ✅ green |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

**Total:** 33 phase-specific tests, all green.

---

## Requirements Coverage

| Requirement | Test Class(es) | Test Count | Status |
|-------------|----------------|------------|--------|
| TRIP-01 | TestVaultManifest | 8 | COVERED |
| TRIP-02 | TestUserModifiedDetection | 6 | COVERED |
| TRIP-03 | TestUserModifiedDetection::test_user_modified_gets_skip_preserve | 1 | COVERED |
| TRIP-04 | TestUserSentinelParser | 6 | COVERED |
| TRIP-05 | TestFormatMergePlanRoundTrip | 7 | COVERED |
| TRIP-06 | TestUserSentinelPreservation | 6 | COVERED |
| TRIP-07 | TestFormatMergePlanRoundTrip (source annotations) + TestUserModifiedDetection::test_source_both | 4 | COVERED |

All 7 requirements have automated verification. No MISSING or PARTIAL gaps.

---

## Wave 0 Requirements

- [x] `TestVaultManifest` class in `tests/test_merge.py` — 8 tests for TRIP-01
- [x] `TestUserModifiedDetection` class in `tests/test_merge.py` — 6 tests for TRIP-02, TRIP-03
- [x] `TestUserSentinelParser` class in `tests/test_merge.py` — 6 tests for TRIP-04
- [x] `TestFormatMergePlanRoundTrip` class in `tests/test_merge.py` — 7 tests for TRIP-05, TRIP-07
- [x] `TestUserSentinelPreservation` class in `tests/test_merge.py` — 6 tests for TRIP-06

*Existing tests (110 pre-phase) remain green — 33 new tests are additive. Full suite: 143 pass.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| `--dry-run` output is human-readable | TRIP-05 | Visual inspection | Run `graphify --obsidian --dry-run` on vault with user-modified notes; verify table + summary line |
| End-to-end note edit + re-run preservation | TRIP-02, TRIP-03 | Requires real vault | Edit a graphify note in Obsidian, re-run `--obsidian`, verify note unchanged |
| Sentinel preservation with `--force` | TRIP-04, TRIP-06 | Requires real file editing | Add sentinel blocks, run `--obsidian --force`, verify sentinels survive |

---

## Validation Sign-Off

- [x] All tasks have automated verify commands
- [x] Sampling continuity: no 3 consecutive tasks without automated verify
- [x] Wave 0 covers all requirements
- [x] No watch-mode flags
- [x] Feedback latency < 0.1s
- [x] `nyquist_compliant: true` set in frontmatter

**Approval:** verified

---

## Validation Audit 2026-04-12

| Metric | Count |
|--------|-------|
| Gaps found | 0 |
| Resolved | 0 |
| Escalated | 0 |
| Tests verified green | 33 |
| Requirements covered | 7/7 |

*Note: Original VALIDATION.md was created pre-execution with predicted `-k` filter patterns. This audit updated the map to match actual test names after execution.*
