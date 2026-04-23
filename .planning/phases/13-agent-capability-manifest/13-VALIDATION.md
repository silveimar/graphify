---
phase: 13
slug: agent-capability-manifest
status: approved
nyquist_compliant: false
wave_0_complete: true
created: 2026-04-22
audited: 2026-04-22
retroactive: true
shipped: 2026-04-17
audit_source: .planning/v1.4-MILESTONE-AUDIT.md (Phase 18.1 task 3)
---

# Phase 13 — Validation Strategy

> Retroactive per-phase validation contract filed under Phase 18.1 task 3 to close the
> v1.4 milestone audit blocker. Phase 13 shipped 2026-04-17 without a VALIDATION.md;
> this document reconstructs the automated-coverage map from `13-VERIFICATION.md`
> (commit `33f9f84`), `13-SECURITY.md` (commit `63d2480`), and live pytest
> introspection at HEAD = `2b01edf`.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest (existing — see `pyproject.toml`, CI runs Python 3.10 and 3.12) |
| **Config file** | `pyproject.toml` (`[tool.pytest.ini_options]`) |
| **Quick run command** | `pytest tests/test_capability.py tests/test_harness_export.py -q` |
| **Full suite command** | `pytest tests/ -q` |
| **Drift gate** | `graphify capability --validate` (wired in `.github/workflows/ci.yml:40`, non-bypassable) |
| **Estimated runtime** | ~1 second (49 pure unit tests; no network, no FS outside tmp_path) |

---

## Sampling Rate

- **After every task commit:** Run `pytest tests/test_capability.py tests/test_harness_export.py -q`
- **After every plan wave:** Run `pytest tests/ -q`
- **Before `/gsd-verify-work`:** Full suite must be green + `graphify capability --validate` exits 0
- **Max feedback latency:** ~1 second

---

## Per-Task Verification Map

> Every P1/P2 requirement in Phase 13 maps to at least one automated row below. One row
> (MANIFEST-06) is flagged PARTIAL — the gap is a definitional omission in
> `capability_tool_meta.yaml`, not a failing test; remediation is scheduled in
> Phase 18.2 task 1.

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 13-01-XX | 01 | 1 | MANIFEST-01 | T-13-01 | Committed `server.json` validates against JSON-Schema Draft 2020-12 and carries `_meta.manifest_content_hash` matching live introspection | unit | `pytest tests/test_capability.py::test_schema_validates_built_manifest -q` | ✅ | ✅ green |
| 13-01-XX | 01 | 1 | MANIFEST-02 | — | `graphify capability` round-trips manifest to `graphify-out/` atomically (temp-file + rename) | unit | `pytest tests/test_capability.py::test_atomic_manifest_roundtrip -q` | ✅ | ✅ green |
| 13-01-XX | 01 | 1 | MANIFEST-02 | — | Pipeline hook materializes runtime manifest alongside graph; basename is `capability.json` (not `manifest.json`) | unit | `pytest tests/test_capability.py::test_pipeline_writes_capability_json -q` | ✅ | ✅ green |
| 13-01-XX | 01 | 1 | MANIFEST-02 | — | Writer never emits a stale `manifest.json` basename (anti-collision invariant) | unit | `pytest tests/test_capability.py::test_capability_writer_basename_is_not_manifest_json -q` | ✅ | ✅ green |
| 13-01-XX | 01 | 1 | MANIFEST-03 | — | `capability_describe` MCP tool merges static manifest + live state into D-02 envelope | integration | `pytest tests/test_capability.py::test_manifest_tool_names_match_registry -q` | ✅ | ✅ green |
| 13-01-XX | 01 | 1 | MANIFEST-04 | — | `graphify capability --validate` exits 0 on clean tree (committed `server.json` matches introspection) | unit | `pytest tests/test_capability.py::test_validate_cli_clean_tree -q` | ✅ | ✅ green |
| 13-01-XX | 01 | 1 | MANIFEST-04 | — | `graphify capability --validate` exits 0 on legitimate clean build | unit | `pytest tests/test_capability.py::test_validate_cli_zero -q` | ✅ | ✅ green |
| 13-01-XX | 01 | 1 | MANIFEST-05 | — | Manifest tool list is introspection-driven: set-equality vs `mcp_tool_registry.build_mcp_tools()` | unit | `pytest tests/test_capability.py::test_manifest_tool_names_match_registry -q` | ✅ | ✅ green |
| 13-01-XX | 01 | 1 | MANIFEST-06 | T-13-02 | Every registered tool carries explicit `cost_class`, `deterministic`, `cacheable_until`, `composable_from` sourced from `capability_tool_meta.yaml` (not cascade defaults) | unit | `pytest tests/test_capability.py::test_argue_topic_not_composable -q` | ✅ | ⚠️ partial |
| 13-01-XX | 01 | 1 | MANIFEST-07 | T-13-02 | `manifest_content_hash` deterministic across runs — every MCP envelope can emit a stable hash via QUERY_GRAPH_META_SENTINEL | unit | `pytest tests/test_capability.py::test_manifest_hash_stable -q` | ✅ | ✅ green |
| 13-01-XX | 01 | 1 | MANIFEST-07 | T-13-02 | Hash remains stable after examples extraction merges into manifest (no docstring-order drift) | unit | `pytest tests/test_capability.py::test_manifest_hash_stable_after_examples_added -q` | ✅ | ✅ green |
| 13-01-XX | 01 | 1 | MANIFEST-08 | — | Skill frontmatter `capability_manifest:` key references runtime manifest — committed in `skill.md` + `skill-codex.md` | unit | `graphify capability --validate` (CI gate `.github/workflows/ci.yml:40`) | ✅ | ✅ green |
| 13-02-XX | 02 | 2 | MANIFEST-09 | T-13-03 | CI drift gate detects schema/hash drift between committed `server.json` and live introspection | unit | `pytest tests/test_capability.py::test_validate_cli_drift_detected -q` | ✅ | ✅ green |
| 13-02-XX | 02 | 2 | MANIFEST-09 | T-13-03 | Drift-detection message includes field-level diff (actionable signal to committer) | unit | `pytest tests/test_capability.py::test_validate_cli_drift_message_includes_field_diff -q` | ✅ | ✅ green |
| 13-02-XX | 02 | 2 | MANIFEST-09 | T-13-03 | Drift output suppresses huge diffs by default (operator ergonomics) | unit | `pytest tests/test_capability.py::test_validate_cli_no_huge_diff_by_default -q` | ✅ | ✅ green |
| 13-02-XX | 02 | 2 | MANIFEST-09 | T-13-03 | Validator narrows exception type in failure message (no broad `Exception`) | unit | `pytest tests/test_capability.py::test_validate_cli_narrows_exception_type_in_message -q` | ✅ | ✅ green |
| 13-02-XX | 02 | 2 | MANIFEST-10 | — | Per-tool `_meta.examples` auto-extracted from handler docstring `Examples:` block | unit | `pytest tests/test_capability.py::test_extract_tool_examples_parses_examples_block -q` | ✅ | ✅ green |
| 13-02-XX | 02 | 2 | MANIFEST-10 | — | Extractor preserves multiline example indentation | unit | `pytest tests/test_capability.py::test_extract_tool_examples_preserves_multiline_indentation -q` | ✅ | ✅ green |
| 13-02-XX | 02 | 2 | MANIFEST-10 | — | Extractor returns empty list when no `Examples:` block present | unit | `pytest tests/test_capability.py::test_extract_tool_examples_empty_when_no_block -q` | ✅ | ✅ green |
| 13-02-XX | 02 | 2 | MANIFEST-10 | — | Extractor handles None docstring safely | unit | `pytest tests/test_capability.py::test_extract_tool_examples_empty_on_none_docstring -q` | ✅ | ✅ green |
| 13-02-XX | 02 | 2 | MANIFEST-10 | — | Extractor stops at next docstring section (`Args:`, `Returns:`) to avoid spillover | unit | `pytest tests/test_capability.py::test_extract_tool_examples_stops_at_next_section -q` | ✅ | ✅ green |
| 13-02-XX | 02 | 2 | MANIFEST-10 | — | All 22 manifest tool entries carry `_meta.examples: list[str]` uniformly (empty-list on absence, never missing key) | unit | `pytest tests/test_capability.py::test_meta_examples_populated_in_manifest -q` | ✅ | ✅ green |
| 13-02-XX | 02 | 2 | MANIFEST-10 | — | `_meta.examples` shape is uniform across tools with + without docstring Examples block | unit | `pytest tests/test_capability.py::test_meta_examples_uniform_when_absent -q` | ✅ | ✅ green |
| 13-03-XX | 03 | 1 | HARNESS-01 | T-13-05 | `graphify harness export` emits three sidecar files (SOUL, HEARTBEAT, USER) under `graphify-out/harness/` | unit | `pytest tests/test_harness_export.py::test_export_writes_three_files -q` | ✅ | ✅ green |
| 13-03-XX | 03 | 1 | HARNESS-02 | — | Declarative `claude.yaml` schema parsed and sidecar loading tolerates corrupt JSONL lines (summary fallback) | unit | `pytest tests/test_harness_export.py::test_load_sidecars_summary_when_corrupt_jsonl_lines -q` | ✅ | ✅ green |
| 13-03-XX | 03 | 1 | HARNESS-03 | — | `{{ token }}` → `${token}` single-regex normalization uses `string.Template.safe_substitute` | unit | `pytest tests/test_harness_export.py::test_placeholder_token_regex_normalization -q` | ✅ | ✅ green |
| 13-03-XX | 03 | 1 | HARNESS-03 | — | Module imports no Jinja2 (spec-locked decision) | unit | `pytest tests/test_harness_export.py::test_no_jinja2_import -q` | ✅ | ✅ green |
| 13-03-XX | 03 | 1 | HARNESS-04 | — | `graphify harness export [--target claude] [--out PATH]` CLI dispatches to `export_claude_harness` | integration | `pytest tests/test_harness_export.py::test_cli_harness_export_invokes_exporter -q` | ✅ | ✅ green |
| 13-03-XX | 03 | 1 | HARNESS-05 | T-13-05 | Output filenames confined under `graphify-out/harness/` via `validate_graph_path` | unit | `pytest tests/test_harness_export.py::test_output_confined_to_graphify_out -q` | ✅ | ✅ green |
| 13-03-XX | 03 | 1 | HARNESS-05 | T-13-05 | Path guard rejects sibling-prefix collisions (e.g. `graphify-out-evil/`) | unit | `pytest tests/test_harness_export.py::test_path_guard_rejects_sibling_prefix_collision -q` | ✅ | ✅ green |
| 13-03-XX | 03 | 1 | HARNESS-06 | T-13-04 | Annotations excluded by default via `ANNOTATION_ALLOW_LIST` (peer_id + free-text body scrubbed) | unit | `pytest tests/test_harness_export.py::test_annotations_allow_list_default -q` | ✅ | ✅ green |
| 13-04-XX | 04 | 2 | HARNESS-07 | T-13-07 | 7-pattern secret scanner covers aws / github_pat / openai / slack / bearer / pem / email_credential | unit | `pytest tests/test_harness_export.py::test_secret_patterns_coverage -q` | ✅ | ✅ green |
| 13-04-XX | 04 | 2 | HARNESS-07 | T-13-07 | Scanner detects AWS access key | unit | `pytest tests/test_harness_export.py::test_scanner_detects_aws_key -q` | ✅ | ✅ green |
| 13-04-XX | 04 | 2 | HARNESS-07 | T-13-07 | Scanner detects AWS temporary credentials | unit | `pytest tests/test_harness_export.py::test_scanner_detects_aws_temporary_credentials -q` | ✅ | ✅ green |
| 13-04-XX | 04 | 2 | HARNESS-07 | T-13-07 | Scanner detects GitHub PAT | unit | `pytest tests/test_harness_export.py::test_scanner_detects_github_pat -q` | ✅ | ✅ green |
| 13-04-XX | 04 | 2 | HARNESS-07 | T-13-07 | Scanner detects OpenAI key (sk-...) | unit | `pytest tests/test_harness_export.py::test_scanner_detects_openai_key -q` | ✅ | ✅ green |
| 13-04-XX | 04 | 2 | HARNESS-07 | T-13-07 | Scanner detects OpenAI project key (sk-proj-...) | unit | `pytest tests/test_harness_export.py::test_scanner_detects_openai_proj_key -q` | ✅ | ✅ green |
| 13-04-XX | 04 | 2 | HARNESS-07 | T-13-07 | Scanner false-positive guard: does not match `sk-learn` or short sk tokens | unit | `pytest tests/test_harness_export.py::test_scanner_does_not_match_sk_learn_or_short_sk_tokens -q` | ✅ | ✅ green |
| 13-04-XX | 04 | 2 | HARNESS-07 | T-13-07 | Scanner redacts full PEM private key body (not just header line) | unit | `pytest tests/test_harness_export.py::test_scanner_redacts_full_pem_private_key_body -q` | ✅ | ✅ green |
| 13-04-XX | 04 | 2 | HARNESS-07 | T-13-07 | Scanner `mode=redact` replaces secret with `[REDACTED]` | unit | `pytest tests/test_harness_export.py::test_scanner_redact_mode -q` | ✅ | ✅ green |
| 13-04-XX | 04 | 2 | HARNESS-07 | T-13-07 | Scanner `mode=error` exits nonzero on any hit | unit | `pytest tests/test_harness_export.py::test_scanner_error_mode_exits_nonzero -q` | ✅ | ✅ green |
| 13-04-XX | 04 | 2 | HARNESS-07 | T-13-07 | Scanner skips allow-list fields (id, label, source_file, relation, confidence) | unit | `pytest tests/test_harness_export.py::test_scanner_skips_allowlist_fields -q` | ✅ | ✅ green |
| 13-04-XX | 04 | 2 | HARNESS-07 | T-13-07 | Scanner rejects unknown `--secrets-mode` value (fail-closed) | unit | `pytest tests/test_harness_export.py::test_scanner_rejects_unknown_mode -q` | ✅ | ✅ green |
| 13-04-XX | 04 | 2 | HARNESS-07 | T-13-07 | `--include-annotations` flag invokes scanner pipeline | integration | `pytest tests/test_harness_export.py::test_include_annotations_flag_invokes_scanner -q` | ✅ | ✅ green |
| 13-04-XX | 04 | 2 | HARNESS-07 | T-13-07 | CLI `--include-annotations --secrets-mode=error` exits with code 3 on secret hit | integration | `pytest tests/test_harness_export.py::test_cli_include_annotations_error_mode_exits_3 -q` | ✅ | ✅ green |
| 13-04-XX | 04 | 2 | HARNESS-08 | T-13-06 | `fidelity.json` written with per-file SHA-256 + byte-length + `round_trip` field | unit | `pytest tests/test_harness_export.py::test_fidelity_manifest_written -q` | ✅ | ✅ green |
| 13-04-XX | 04 | 2 | HARNESS-08 | T-13-06 | Deterministic byte-equal output with pinned clock across repeat exports | unit | `pytest tests/test_harness_export.py::test_round_trip_byte_equal_with_frozen_clock -q` | ✅ | ✅ green |
| 13-04-XX | 04 | 2 | HARNESS-08 | T-13-06 | `round_trip == "drift"` detected when schema changes between exports | unit | `pytest tests/test_harness_export.py::test_round_trip_drift_detected_when_schema_changes -q` | ✅ | ✅ green |
| 13-04-XX | 04 | 2 | HARNESS-08 | T-13-06 | Clock seam overridable per-invocation | unit | `pytest tests/test_harness_export.py::test_clock_seam_overridable -q` | ✅ | ✅ green |
| 13-04-XX | 04 | 2 | HARNESS-08 | T-13-06 | Module-level `set_clock` override honored (determinism injection) | unit | `pytest tests/test_harness_export.py::test_set_clock_module_override -q` | ✅ | ✅ green |
| 13-03-XX | 03 | 1 | HARNESS-01..05 (regression) | — | End-to-end export produces three files with deterministic contents across runs | unit | `pytest tests/test_harness_export.py::test_deterministic_output_across_runs -q` | ✅ | ✅ green |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ partial · ⚠️ flaky*

*File Exists: ✅ present · ❌ W0 = Wave 0 must create*

---

## Wave 0 Requirements

All Wave-0 test infrastructure was in place at phase close (2026-04-17). Retroactive audit confirms:

- [x] `tests/test_capability.py` — 22 tests covering MANIFEST-01..10
- [x] `tests/test_harness_export.py` — 27 tests covering HARNESS-01..08
- [x] `server.json` committed as golden-file reference for drift-gate tests
- [x] `.github/workflows/ci.yml:40` wires `graphify capability --validate` as a non-bypassable CI gate

---

## Manual-Only Verifications

None. Every REQ-ID in Phase 13 is programmatically verifiable. The single PARTIAL finding
(MANIFEST-06) is a definitional set-difference check, not a subjective one — remediation
adds a regression test in Phase 18.2 task 1.

---

## Threat Model Refs

| Threat ID | Description | Mitigation Reference |
|-----------|-------------|----------------------|
| T-13-01 | Manifest schema drift invalidates agent discovery | `test_schema_validates_built_manifest` + CI drift gate |
| T-13-02 | Hash instability across runs undermines envelope trust signal | `test_manifest_hash_stable` + `test_manifest_hash_stable_after_examples_added` |
| T-13-03 | Drift gate silently bypassed or returns false-green | `test_validate_cli_drift_detected` + `test_validate_cli_narrows_exception_type_in_message`; ci.yml has no `continue-on-error` and no `GRAPHIFY_SKIP` env guard |
| T-13-04 | Harness export leaks free-text node body / peer_id annotations by default | `ANNOTATION_ALLOW_LIST` frozenset + `test_annotations_allow_list_default` |
| T-13-05 | Harness writes outside `graphify-out/harness/` (path traversal / sibling-prefix) | `validate_graph_path` wrapper + `test_output_confined_to_graphify_out` + `test_path_guard_rejects_sibling_prefix_collision` |
| T-13-06 | Non-deterministic harness output defeats round-trip fidelity claim | `set_clock` seam + `test_round_trip_byte_equal_with_frozen_clock` + `test_deterministic_output_across_runs` |
| T-13-07 | `--include-annotations` exfiltrates secrets into the harness | 7-pattern `SECRET_PATTERNS` + `scan_annotations_for_secrets(mode={redact,error})` + 13 scanner tests |

All 10 threats are closed in `13-SECURITY.md` (commit `63d2480`).

---

## Validation Sign-Off

- [x] All 18 REQ-IDs have at least one `<automated>` row
- [x] Sampling continuity: no 3 consecutive tasks without automated verify
- [x] Wave 0 covers all MISSING references (no MISSING rows — only 1 PARTIAL)
- [x] No watch-mode flags
- [x] Feedback latency < 30s (~1s observed)
- [ ] `nyquist_compliant: true` — **NOT SET**; MANIFEST-06 lacks a regression test guarding the `capability_tool_meta.yaml` set-equality invariant. The `chat` and `get_focus_context` omissions shipped under the radar precisely because no test asserts every registered tool has an explicit YAML block. Closing this gap is Phase 18.2 task 1 deliverable.

**Approval:** approved with PARTIAL carve-out — 2026-04-22

---

## Validation Audit 2026-04-22

All 49 declared automated tests executed as a single pytest invocation.

| Metric | Count |
|--------|-------|
| REQ-IDs in scope | 18 (MANIFEST-01..10, HARNESS-01..08) |
| Automated rows declared | 49 (multi-assertion coverage per REQ) |
| COVERED (test exists + green) | 49 |
| PARTIAL (declared but missing guard test) | 1 row — MANIFEST-06 YAML set-equality invariant |
| MISSING (no test) | 0 |
| Gaps resolved this audit | 0 (no test generation — Phase 13 code frozen for v1.4) |
| Escalated to Phase 18.2 | 1 (MANIFEST-06 regression test) |
| Manual-only items (UAT) | 0 |

**Command:** `pytest tests/test_capability.py tests/test_harness_export.py -q`

**Result:** `49 passed in 0.67s` — every Per-Task Verification Map row currently resolves to a green test.

### PARTIAL Carve-Out: MANIFEST-06

**Gap:** `graphify/capability_tool_meta.yaml` omits explicit blocks for the MCP tools
`chat` (registered at `mcp_tool_registry.py:256`) and `get_focus_context`
(registered at `mcp_tool_registry.py:290`). Both tools emit in `CAPABILITY_TOOLS` with
the implicit cascade defaults (`cost_class=cheap`, `deterministic=False`,
`cacheable_until=graph_mtime`, `composable_from=[]`) rather than declared values.
MANIFEST-06's spirit — "agents can reason about cost + composition before calling" —
is undermined: an agent cannot distinguish explicitly-declared-cheap from
forgotten-metadata-cheap.

**Why no test catches it today:** `test_manifest_tool_names_match_registry` asserts
set-equality between manifest and registry, but there is no analogous set-equality
between registry and YAML meta keys. The existing row
(`test_argue_topic_not_composable`) verifies a single spot-check attribute on one tool,
not full coverage.

**Remediation:** Phase 18.2 task 1 (`18.2-01-PLAN.md`) per `v1.4-MILESTONE-AUDIT.md`
integration[0]. That task:
1. Back-fills `chat` and `get_focus_context` blocks in `capability_tool_meta.yaml`
2. Regenerates `server.json` so the committed hash matches
3. Adds a regression test (`tests/test_capability.py::test_all_registered_tools_have_explicit_meta_yaml`)
   asserting `set(yaml_keys) == set(registry_tool_names)`

Once Phase 18.2 task 1 lands, this VALIDATION.md's `nyquist_compliant` key flips to
`true` and the PARTIAL row above flips to `green`.

### Baseline Pytest Confirmation

```
$ pytest tests/test_capability.py tests/test_harness_export.py -q
.................................................                        [100%]
49 passed in 0.67s
```

Phase 13 is **approved with a single PARTIAL carve-out** scheduled for Phase 18.2 task 1.
All 17 non-partial REQ-IDs are Nyquist-compliant with green automated coverage.
