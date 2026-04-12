---
phase: 04
slug: merge-engine
status: verified
threats_open: 0
asvs_level: 1
created: 2026-04-11
---

# Phase 04 — Security

> Per-phase security contract: threat register, accepted risks, and audit trail.

---

## Trust Boundaries

| Boundary | Description | Data Crossing |
|----------|-------------|---------------|
| rendered-note → sentinel grammar | `templates.py` emits graphify-owned blocks inside user notes; malformed output becomes a Phase 04 merge bug | Node labels, edge metadata |
| user-written `profile.yaml` → `_deep_merge` → runtime profile dict | PyYAML `safe_load` parses untrusted YAML before `validate_profile` gates it | Field policy mode, preserved keys |
| note-file-on-disk → `_parse_frontmatter` / `_parse_sentinel_blocks` | Adversarial YAML or sentinel-lookalike prose in user-edited notes | Frontmatter dict, sentinel block dict |
| `rendered_notes[target_path]` → filesystem | Every target path is gated through `_validate_target` before any `read_text` or `write` | Absolute file paths |
| vault_dir walking (`_cleanup_stale_tmp`, `rglob`) | Symlinks inside vault could escape confinement if followed | Path traversal |
| `.tmp` → `os.replace` atomic publish | Crash safety depends on filesystem ordering guarantees (ext4/btrfs/NTFS honor `os.replace`) | Final note content |
| test fixtures → `tmp_path` via `shutil.copytree` | Fixtures are version-controlled and never mutated in-place | Test vault snapshots |

---

## Threat Register

| Threat ID | Category | Component | Disposition | Mitigation | Status |
|-----------|----------|-----------|-------------|------------|--------|
| T-04-01 | Tampering | `templates.py` sentinel builders — adversarial node label containing `<!-- graphify:*:end -->` | mitigate | `_wrap_sentinel` emits fixed literal markers; `name` is the only interpolation. Regression tests: `tests/test_templates.py::test_sentinel_pairing_survives_adversarial_connections_label`, `tests/test_merge.py::test_malicious_label_does_not_break_sentinel_pairing`. Evidence: `graphify/templates.py:62-77`. | closed |
| T-04-02 | Information Disclosure | Empty section builder inadvertently emitting start marker | accept | `_wrap_sentinel` short-circuits on empty content (`graphify/templates.py:73-74`). Behavior tested in `test_render_note_omits_connections_sentinel_when_no_edges`, `test_render_moc_omits_members_sentinel_when_empty`, `test_render_moc_omits_sub_communities_sentinel_when_empty`. | closed |
| T-04-03 | Denial of Service | Extremely long section content producing massive sentinel block | accept | Sentinel overhead is ~60 bytes/block — orthogonal to upstream size caps enforced by `safe_frontmatter_value`. | closed |
| T-04-04 | Tampering | `merge.field_policies` colliding with a graphify-owned frontmatter key | accept | User-local config trust equivalent to CLI flags. Documented at `graphify/merge.py:341-345` (`_resolve_field_policy` docstring). | closed |
| T-04-05 | Elevation of Privilege | Unknown field policy mode silently interpreted as `preserve` | mitigate | `validate_profile` rejects invalid modes via `_VALID_FIELD_POLICY_MODES`. `load_profile` falls back to defaults on validation errors. Evidence: `graphify/profile.py:60, 203-208, 131`. Test: `tests/test_profile.py::test_validate_profile_rejects_invalid_field_policy_mode`. | closed |
| T-04-06 | Information Disclosure | Non-string `field_policies` key crashing downstream dispatcher | mitigate | `validate_profile` rejects non-string keys before the profile is returned. Evidence: `graphify/profile.py:197-202`. Test: `tests/test_profile.py::test_validate_profile_rejects_non_string_field_policy_key`. | closed |
| T-04-07 | Denial of Service | Enormous `field_policies` dict (e.g., 10k entries) | accept | Dispatch is O(1) hash lookup per frontmatter key. Not a realistic DoS vector at user-intended profile sizes. | closed |
| T-04-08 | Tampering | YAML tag injection (`!!python/object/apply:os.system`) in frontmatter | mitigate | Zero PyYAML imports in `graphify/merge.py`. Hand-rolled regex parser at `graphify/merge.py:184-236` (`_FM_SCALAR_RE`, `_FM_LIST_ITEM_RE`, `_coerce_scalar`). Test: `tests/test_merge.py::test_parse_frontmatter_rejects_yaml_tags_as_literal`. | closed |
| T-04-09 | Tampering | Sentinel-lookalike comments embedded in user prose | accept | Documented in `_MalformedSentinel` docstring at `graphify/merge.py:250-259`. Dual-signal defense: `compute_merge_plan` requires BOTH frontmatter `graphify_managed: true` and sentinel presence via `_has_fingerprint` at `graphify/merge.py:778`. | closed |
| T-04-10 | Tampering | Nested or duplicate sentinel blocks smuggling content | mitigate | `_parse_sentinel_blocks` raises `_MalformedSentinel` on duplicate (L315-318), nested same-name (L290-301), mismatched (L309-313), and unpaired (L304-308) markers. Evidence: `graphify/merge.py:262-323`. Test: `tests/test_merge.py::test_parse_sentinel_blocks_nested_same_name_raises_malformed`. | closed |
| T-04-11 | Information Disclosure | `_parse_frontmatter` returning `None` vs `{}` ambiguity | mitigate | Return contract documented at `graphify/merge.py:184-194`. Call site at `graphify/merge.py:754-765` explicitly branches on `parsed_fm is None` → SKIP_CONFLICT/malformed_frontmatter. | closed |
| T-04-12 | Elevation of Privilege | Profile freezing `graphify_managed` key via `field_policies` | accept | User-local config equivalent trust to CLI flags. Documented in `_resolve_field_policy` docstring at `graphify/merge.py:341-345`. | closed |
| T-04-13 | Tampering | Wikilink strings in union-mode list fields | accept | Union treats list items as opaque strings. Emission defense is `safe_frontmatter_value` in `graphify/profile.py:322+`. No new attack surface vs Phase 1. | closed |
| T-04-14 | Tampering | `RenderedNote.target_path` containing `../../etc/passwd` | mitigate | `_validate_target` gates every candidate at `graphify/merge.py:469-494`. Called from `compute_merge_plan` at L733 before any file I/O; traversal → SKIP_CONFLICT. Test: `tests/test_merge.py::test_compute_action_paths_are_absolute_and_inside_vault`. | closed |
| T-04-15 | Tampering | Symlink inside `vault_dir` pointing outside (e.g., to `/etc/`) | mitigate | `validate_vault_path` at `graphify/profile.py:301-315` calls `.resolve()` on both vault_base and candidate, then `relative_to`. Symlink escape raises `ValueError`. `_validate_target` additionally resolves absolute candidates at `merge.py:483-491`. | closed |
| T-04-16 | Denial of Service | Enormous fingerprinted file (e.g., 10 GB) loaded by `read_text()` | accept | Vault files are user-controlled. Size caps are a Phase 5 concern. Flagged in summary. | closed |
| T-04-17 | Information Disclosure | `compute_merge_plan` leaking file contents in `MergeAction.reason` | mitigate | Reason strings at `compute_merge_plan` L748, L762, L773, L782, L792, L799, L812, L836 contain only control information (`"new file"`, `"malformed frontmatter"`, `"malformed sentinel: {exc}"`, `"no fingerprint"`, `"idempotent re-render"`). No file contents interpolated. | closed |
| T-04-18 | TOCTOU | File passes fingerprint check in `compute_merge_plan`, then mutates before `apply_merge_plan` writes | transfer | Transferred to Plan 05 (`apply_merge_plan`). Atomic `.tmp + os.replace` pattern implemented at `graphify/merge.py:859-879`. Transfer tracked jointly with T-04-20. | closed |
| T-04-19 | Tampering | Adversarial fixture content accidentally committed | mitigate | Seven fixtures under `tests/fixtures/vaults/` reviewed and version-controlled. Test helper `_copy_vault_fixture` at `tests/test_merge.py:404-409` guarantees read-only use. | closed |
| T-04-20 | TOCTOU | Stale content between compute and apply | mitigate | Atomic write at `graphify/merge.py:859-879`: `.tmp` path (L865), `mkdir parents` (L866), `fh.flush()` + `os.fsync()` (L870-871), `os.replace` (L872), `.tmp` cleanup on OSError (L874-878). Test: `tests/test_merge.py::test_apply_atomic_no_partial_file_on_error`. | closed |
| T-04-21 | Tampering | Symlink escape in `apply_merge_plan` path crafted to write through | mitigate | `_validate_target` called at `graphify/merge.py:978` (inside `apply_merge_plan` before any write) and L969 for rendered-note index. Path escape → `MergeResult.failed` list. Test: `tests/test_merge.py::test_apply_path_escape_recorded_as_failed`. | closed |
| T-04-22 | Tampering | Malicious stale `.tmp` symlink target outside vault | mitigate | `_cleanup_stale_tmp` at `graphify/merge.py:882-893` uses `tmp.unlink()` (L891). `pathlib.Path.unlink()` unlinks the symlink itself, not the target (Python stdlib contract). Test: `tests/test_merge.py::test_apply_cleanup_stale_tmp`. | closed |
| T-04-23 | Denial of Service | `_cleanup_stale_tmp` walking a huge vault (100k files) | accept | Single-pass `rglob` at `graphify/merge.py:889` is O(n). Phase 5 may scope if needed. | closed |
| T-04-24 | Elevation of Privilege | `target.parent.mkdir(parents=True)` creating directories outside `vault_dir` | mitigate | `_validate_target` invoked at `apply_merge_plan` L978 strictly before `_write_atomic` (L1014), which owns the `mkdir` call (L866). Order verified — no `mkdir` path reachable without prior vault confinement. | closed |
| T-04-25 | Information Disclosure | `MergeResult.failed` leaking filesystem paths or OS errors | accept | Error strings (`merge.py:980, 985, 993, 999, 1017`) are diagnostic; sanitization deferred to Phase 5 CLI. Not a credentials-leak vector. | closed |
| T-04-26 | Repudiation | Successful writes unlogged | accept | `MergeResult.succeeded` at `merge.py:1015` is the write audit trail. Phase 5 `GRAPH_REPORT.md` surfaces it. | closed |
| T-04-27 | Tampering | Test accidentally mutating checked-in fixture | mitigate | `_copy_vault_fixture` at `tests/test_merge.py:404-409` uses `shutil.copytree(src, dst)` into `tmp_path`. All call sites (L432, L441, L457, …, L1293) use this helper; no test writes to `tests/fixtures/` directly. | closed |
| T-04-28 | Information Disclosure | CI log leaking vault content via test stderr/stdout | accept | Pure unit tests over synthetic fixtures. No production data. | closed |
| T-04-29 | Tampering | Security regression test silently weakened in future PR | mitigate | `test_malicious_label_does_not_break_sentinel_pairing` at `tests/test_merge.py:1293-1314` and `test_sentinel_pairing_survives_adversarial_connections_label` at `tests/test_templates.py:2187-2217` assert non-weakenable invariants (exact count + pairing OR explicit `_MalformedSentinel`). Listed in Plan 06 traceability matrix. | closed |

*Status: open · closed*
*Disposition: mitigate (implementation required) · accept (documented risk) · transfer (third-party)*

**Totals:** 17 mitigate · 11 accept · 1 transfer · **29 closed / 0 open**

---

## Accepted Risks Log

| Risk ID | Threat Ref | Rationale | Accepted By | Date |
|---------|------------|-----------|-------------|------|
| AR-04-01 | T-04-02 | Empty section short-circuit is defensive; sentinel grammar guarantees no stray start markers. | Phase 04 owner | 2026-04-11 |
| AR-04-02 | T-04-03 | Sentinel overhead is a fixed ~60 bytes/block — orthogonal to upstream size limits. | Phase 04 owner | 2026-04-11 |
| AR-04-03 | T-04-04 | User-local `profile.yaml` has the same trust level as CLI flags. Policy collision is an exercise of local authority, not an attack. | Phase 04 owner | 2026-04-11 |
| AR-04-04 | T-04-07 | Field policy dispatch is O(1) per key; no realistic DoS at profile sizes a user would author. | Phase 04 owner | 2026-04-11 |
| AR-04-05 | T-04-09 | Sentinel-lookalike prose is accepted because the dual-signal check (`graphify_managed` + sentinel) must both match for merge to act. | Phase 04 owner | 2026-04-11 |
| AR-04-06 | T-04-12 | Freezing `graphify_managed` via `field_policies` is user-local authority; equivalent to disabling the feature at the CLI. | Phase 04 owner | 2026-04-11 |
| AR-04-07 | T-04-13 | Wikilink strings are opaque in union mode; defense is at emission via `safe_frontmatter_value`. No new attack surface vs Phase 1. | Phase 04 owner | 2026-04-11 |
| AR-04-08 | T-04-16 | Vault files are user-controlled; file-size caps are a Phase 5 responsibility. | Phase 04 owner | 2026-04-11 |
| AR-04-09 | T-04-23 | Single-pass `rglob` is O(n); scoped cleanup deferred to Phase 5 if needed. | Phase 04 owner | 2026-04-11 |
| AR-04-10 | T-04-25 | Diagnostic error strings in `MergeResult.failed` are intentional; Phase 5 CLI is responsible for user-facing sanitization. | Phase 04 owner | 2026-04-11 |
| AR-04-11 | T-04-26 | `MergeResult.succeeded` serves as the write audit trail; Phase 5 renders it. | Phase 04 owner | 2026-04-11 |
| AR-04-12 | T-04-28 | Tests use synthetic fixtures only; no production data in CI output. | Phase 04 owner | 2026-04-11 |

---

## Security Audit Trail

| Audit Date | Threats Total | Closed | Open | Run By |
|------------|---------------|--------|------|--------|
| 2026-04-11 | 29 | 29 | 0 | gsd-security-auditor (Sonnet) |

### Audit 2026-04-11 — Initial Verification

- State B (no prior SECURITY.md; built from PLAN + SUMMARY artifacts).
- All 29 threats verified against shipped code in `graphify/templates.py`, `graphify/profile.py`, `graphify/merge.py`, `tests/test_templates.py`, `tests/test_merge.py`, `tests/test_profile.py`.
- Every SUMMARY reports `Threat Flags: None` — no unregistered attack surface discovered during execution.
- One informational hardening note (non-blocking): `test_apply_cleanup_stale_tmp` exercises regular-file `.tmp` removal but not an explicit symlink `.tmp`. Behavior is still correct (T-04-22) because `pathlib.Path.unlink()` unlinks symlinks themselves per stdlib contract. Consider an explicit symlink test in a future phase.

---

## Sign-Off

- [x] All threats have a disposition (mitigate / accept / transfer)
- [x] Accepted risks documented in Accepted Risks Log
- [x] `threats_open: 0` confirmed
- [x] `status: verified` set in frontmatter

**Approval:** verified 2026-04-11
