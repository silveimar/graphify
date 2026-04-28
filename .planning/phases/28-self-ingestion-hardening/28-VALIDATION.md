---
phase: 28
slug: self-ingestion-hardening
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-04-27
---

# Phase 28 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest (already installed, all 1647 tests passing) |
| **Config file** | pyproject.toml (pytest section) |
| **Quick run command** | `pytest tests/test_detect.py tests/test_profile.py tests/test_output.py -q` |
| **Full suite command** | `pytest tests/ -q` |
| **Estimated runtime** | ~3s quick / ~25s full |

---

## Sampling Rate

- **After every task commit:** Run `pytest tests/test_detect.py tests/test_profile.py tests/test_output.py -q`
- **After every plan wave:** Run `pytest tests/ -q`
- **Before `/gsd-verify-work`:** Full suite must be green
- **Max feedback latency:** ~3s (quick run)

---

## Per-Task Verification Map

> Task IDs and Wave numbers are placeholders pending PLAN.md authoring. Planner backfills `Task ID` / `Plan` / `Wave` columns; the `Requirement → Test` mapping below is locked.

| Requirement | Secure Behavior | Test Type | Automated Command | File Exists |
|-------------|-----------------|-----------|-------------------|-------------|
| VAULT-11 | `output.exclude` accepted in profile schema | unit | `pytest tests/test_profile.py -k "exclude" -x` | ❌ Wave 0 |
| VAULT-11 | Traversal/empty/non-string exclude entries rejected | unit | `pytest tests/test_profile.py -k "exclude" -x` | ❌ Wave 0 |
| VAULT-11 | `exclude_globs` populated in `ResolvedOutput` from profile | unit | `pytest tests/test_output.py -k "exclude_globs" -x` | ❌ Wave 0 |
| VAULT-11 | `detect()` prunes files matching `exclude_globs` | unit | `pytest tests/test_detect.py -k "exclude_globs" -x` | ❌ Wave 0 |
| VAULT-11 | `exclude_globs` applied even when `--output` overrides destination | unit | `pytest tests/test_detect.py -k "exclude_globs_with_cli_flag" -x` | ❌ Wave 0 |
| VAULT-12 | Paths matching `resolved.notes_dir.name` pruned from scan | unit | `pytest tests/test_detect.py -k "nesting_guard_resolved" -x` | ❌ Wave 0 |
| VAULT-12 | Paths matching `resolved.artifacts_dir.name` pruned from scan | unit | `pytest tests/test_detect.py -k "nesting_guard_resolved" -x` | ❌ Wave 0 |
| VAULT-12 | Single summary warning emitted (not per-file) | unit | `pytest tests/test_detect.py -k "nesting_guard_summary" -x` | ❌ Wave 0 |
| VAULT-12 | Guard applies with `resolved=None` (no-vault case) | unit | `pytest tests/test_detect.py -k "test_detect_skips_graphify_out" -x` | ✅ existing |
| VAULT-13 | `output-manifest.json` written atomically after export | unit | `pytest tests/test_detect.py -k "output_manifest" -x` | ❌ Wave 0 |
| VAULT-13 | Missing manifest → silent empty (no crash) | unit | `pytest tests/test_detect.py -k "output_manifest_missing" -x` | ❌ Wave 0 |
| VAULT-13 | Malformed manifest → warn-once + empty | unit | `pytest tests/test_detect.py -k "output_manifest_malformed" -x` | ❌ Wave 0 |
| VAULT-13 | Rolling N=5 cap enforced on write | unit | `pytest tests/test_detect.py -k "output_manifest_fifo" -x` | ❌ Wave 0 |
| VAULT-13 | GC of stale file entries on write | unit | `pytest tests/test_detect.py -k "output_manifest_gc" -x` | ❌ Wave 0 |
| VAULT-13 | Prior-run files excluded from scan (renamed notes_dir recovery) | unit | `pytest tests/test_detect.py -k "output_manifest_renamed_notes" -x` | ❌ Wave 0 |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/test_detect.py` — new test functions covering VAULT-12 / VAULT-13 (append to existing file, do not replace)
- [ ] `tests/test_profile.py` — new test functions covering VAULT-11 `output.exclude` validation (append after Phase 27 block ~line 1292)
- [ ] `tests/test_output.py` — update `test_resolved_output_unpacks_to_tuple` and `test_resolved_output_namedtuple_field_order` for 6th field (`exclude_globs`); add `test_resolve_output_exclude_globs_populated_from_profile`
- [ ] No new framework or fixture install required — existing `tmp_path` fixtures from Phase 27 are reusable

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| End-to-end self-ingestion regression repro | VAULT-11/12/13 (composite) | Multi-step user-flow scenario; covered by integration test but worth one manual pass | `cd /tmp/repro-vault && touch .obsidian/.empty && cat > .graphify/profile.yaml <<EOF\noutput:\n  mode: vault-relative\n  path: knowledge-graph\n  exclude:\n    - "**/cache/**"\nEOF` then run `graphify --obsidian` twice; second run must NOT nest `knowledge-graph/.../knowledge-graph/...` |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 5s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
