---
phase: 13-agent-capability-manifest
audited: 2026-04-22
status: secured
asvs_level: 1
block_policy: high
threats_total: 10
threats_closed: 10
threats_open: 0
retroactive: true
shipped: 2026-04-17
audit_source: .planning/v1.4-MILESTONE-AUDIT.md (Phase 18.1 task 2)
source_plans:
  - 13-01-PLAN.md (T-13-01, T-13-02, T-13-03)
  - 13-02-PLAN.md (T-13-08, T-13-09, T-13-10)
  - 13-03-PLAN.md (T-13-04, T-13-05, T-13-06)
  - 13-04-PLAN.md (T-13-07, T-13-08)
stride_coverage:
  spoofing: 0
  tampering: 5
  repudiation: 0
  information_disclosure: 4
  denial_of_service: 1
  elevation_of_privilege: 0
---

# SECURITY — Phase 13: agent-capability-manifest + SEED-002 harness memory export

**Phase:** 13 — agent-capability-manifest
**ASVS Level:** 1
**Block policy:** high
**Threats closed:** 10 / 10
**Audit date:** 2026-04-22 (retroactive; phase shipped 2026-04-17)

## Summary

All 10 threats declared across the four Phase 13 plans (13-01 through 13-04)
are verified against live code at HEAD. Nine `mitigate` threats have code
and/or test evidence; one `accept` threat (T-13-09, docstring info-disclosure)
has documented scope-based rationale recorded here.

The Phase 13 attack surface splits into two subsystems:

1. **Capability manifest** (`capability.py`, `mcp_tool_registry.py`,
   `capability_tool_meta.yaml`, `server.json`, MCP `capability_describe`
   tool, CI drift gate). Concerns: tampering with committed manifest,
   information disclosure via `capability_describe` live block, hash-recompute
   DoS, docstring leak into `_meta.examples`, non-deterministic manifest.
2. **Harness memory export** (`harness_export.py`, `harness_schemas/claude.yaml`,
   `graphify harness` CLI). Concerns: annotation info disclosure, path
   escape, non-determinism, secret leak via `--include-annotations`,
   round-trip fidelity drift.

## Trust Boundaries

```
┌──────────────────────┐    (1) manifest read
│ External MCP agent   │ ────────────────────▶ graphify-out/manifest.json
└──────────────────────┘                        └── hash pinned in server.json
         │                                          (CI drift gate enforces)
         │ (2) capability_describe RPC
         ▼
┌──────────────────────┐    (3) SECRET_PATTERNS scan + allow-list
│ graphify MCP server  │ ◀─────────────────── Workspace sidecars
│ (serve.py handlers)  │                     (annotations.jsonl,
└──────────────────────┘                      agent-edges.json, telemetry.json)
         ▲                                           │
         │                                           │ (4) graphify harness export
         │ QUERY_GRAPH_META_SENTINEL +               ▼
         │ manifest_content_hash on               ┌──────────────────────┐
         │ every envelope (28 sites)              │ graphify-out/harness │
         │                                        │ claude-SOUL.md       │
         │                                        │ claude-HEARTBEAT.md  │
         │                                        │ claude-USER.md       │
         │                                        │ fidelity.json        │
         │                                        └──────────────────────┘
         │                                                │
         │                                                │ (5) validate_graph_path
         │                                                ▼   confines to base
         │                                        Filesystem writer
         │
┌──────────────────────┐    (6) non-bypassable drift gate
│ CI runner (push/PR)  │ ─────────── graphify capability --validate
│ .github/workflows/   │             (no continue-on-error, no env guard)
└──────────────────────┘
```

Boundaries enforced:

1. **External MCP agent → capability manifest.** Untrusted reader, trusted
   content. Content integrity guaranteed by `_meta.manifest_content_hash`
   pinned in `server.json` and revalidated on every CI push.
2. **User conversation → harness export file.** Trusted reader, semi-trusted
   content (annotations may contain secrets). Default-deny via
   `ANNOTATION_ALLOW_LIST`; opt-in `--include-annotations` gated by
   7-pattern `SECRET_PATTERNS` scanner with `--secrets-mode {redact,error}`.
3. **CI / developer → server.json drift detection.** Ensures committed
   manifest content hash matches live introspection; suppression requires
   visible edit to `.github/workflows/ci.yml` (no silent bypass).

## Threat Verification Table

### Plan 13-01 — capability manifest core (MANIFEST-01..08)

| Threat ID | Category | Component | Disposition | Status | Evidence |
|-----------|----------|-----------|-------------|--------|----------|
| T-13-01 | Information disclosure | `capability_describe` live block | mitigate | CLOSED | `graphify/serve.py:3041-3091` — `_tool_capability_describe` emits only aggregate counts (`G.number_of_nodes()`, `G.number_of_edges()`, `len(communities)`), sidecar `mtime` stamps via `_file_mtime_or_zero`, and `enrichment_snapshot_id` (non-secret). No annotation text, no `peer_id`, no free-text fields. Docstring at `serve.py:3042` notes "MANIFEST-03: static manifest + live non-secret scalars (T-13-01)." |
| T-13-02 | Tampering | `graphify-out/manifest.json` vs committed `server.json` | mitigate | CLOSED | `graphify/capability.py:257` `validate_cli` compares `canonical_manifest_hash(build_manifest_dict())` against `server.json`'s `_meta.manifest_content_hash`; MCP server recomputes from in-process registry (`mcp_tool_registry.build_mcp_tools`) rather than trusting the file. Behavioral check: `server.json` hash `05aaa081311897c5152d42dc7fef790431c16912fc89a15fa5b9525472554645` matches live introspection (`pytest tests/test_capability.py::test_validate_cli_clean_tree`). |
| T-13-03 | Denial of service | Hash recompute every RPC | mitigate | CLOSED | `manifest_content_hash` cached at `_reload_if_stale` boundary in `graphify/serve.py`; all 28 `QUERY_GRAPH_META_SENTINEL` call sites read the cached value. Mtime-gated cache per Decision D-04; no full-disk read per call. |

### Plan 13-02 — CI drift gate + docstring examples (MANIFEST-09, MANIFEST-10)

| Threat ID | Category | Component | Disposition | Status | Evidence |
|-----------|----------|-----------|-------------|--------|----------|
| T-13-08 (P2) | Tampering (CI bypass) | `.github/workflows/ci.yml` drift-gate step | mitigate | CLOSED | `.github/workflows/ci.yml:40` — `graphify capability --validate` runs unconditionally. No `continue-on-error` (grep returns no matches); no `GRAPHIFY_SKIP` env guard; no `if:` conditional. Suppression requires visible edit to `ci.yml` caught in code review. `tests/test_capability.py::test_validate_cli_drift_detected` asserts non-zero exit on drift. |
| T-13-09 | Information disclosure (docstring leak) | `_meta.examples` extraction | accept | CLOSED | Accept-rationale: docstrings are already public (visible in source + MCP `description` field); elevating `Examples:` blocks to `_meta.examples` surfaces no net-new information. Developer discipline — "do not put secrets in docstrings" — is the same rule applied to all existing docstrings. Scope limit reviewed: reasonable at ASVS Level 1. |
| T-13-10 | Integrity (non-deterministic manifest) | `build_manifest_dict` + examples ordering | mitigate | CLOSED | `graphify/capability.py:40` `extract_tool_examples` preserves input order; `graphify/mcp_tool_registry.py:57` `build_mcp_tools` returns stable order; `canonical_manifest_hash` uses `json.dumps(..., sort_keys=True)`. Determinism confirmed by behavioral spot-check in `13-VERIFICATION.md` (hash stable across repeat calls). |

### Plan 13-03 — harness export core (HARNESS-01..06, T-13-04/05/06)

| Threat ID | Category | Component | Disposition | Status | Evidence |
|-----------|----------|-----------|-------------|--------|----------|
| T-13-04 | Information disclosure | Annotation free-text fields (`body`, `peer_id`) leaking into harness output | mitigate | CLOSED | `graphify/harness_export.py:31` `ANNOTATION_ALLOW_LIST = frozenset({'id','label','source_file','relation','confidence'})`; `graphify/harness_export.py:308-318` `_filter_annotations_allowlist` drops all keys outside the allow-list when `include_annotations=False` (default). `tests/test_harness_export.py::test_annotations_allow_list_default` asserts `peer_id` + free-text body are scrubbed. |
| T-13-05 | Tampering / path escape | Harness file written outside `graphify-out/` via crafted `--out` or symlink | mitigate | CLOSED | `graphify/harness_export.py:616` `validate_graph_path(harness_dir, base=base)` raises `ValueError` on escape. Additional defense: `graphify/harness_export.py:621-625` uses `Path.resolve().relative_to(base)` (semantic containment, not lexical prefix match — WR-03 Phase 13 review fix hardening against `/tmp/out` vs `/tmp/outX` collisions). `tests/test_harness_export.py::test_output_confined_to_graphify_out` asserts escape attempts fail cleanly without writing. |
| T-13-06 | Integrity / non-determinism | Two successive exports on same input produce different byte-for-byte output | mitigate | CLOSED | `_collect_god_nodes`, `_collect_recent_deltas`, `_collect_hot_paths` all sort by stable deterministic keys before rendering. Template rendering uses `string.Template.safe_substitute` (no Jinja2) — `graphify/harness_export.py:175` `_normalize_placeholders` + `graphify/harness_export.py:697-698`. `_clock` seam at `graphify/harness_export.py:462-480` (`_system_clock`, `set_clock`) pins `generated_at` for byte-equal reproducibility. `tests/test_harness_export.py::test_round_trip_byte_equal_with_frozen_clock` passes. |

### Plan 13-04 — secret scanner + fidelity manifest (HARNESS-07, HARNESS-08)

| Threat ID | Category | Component | Disposition | Status | Evidence |
|-----------|----------|-----------|-------------|--------|----------|
| T-13-07 | Information disclosure | `--include-annotations` path leaking credentials into SOUL/HEARTBEAT/USER | mitigate | CLOSED | `graphify/harness_export.py:82-90` `SECRET_PATTERNS` declares 7 families (`aws_access_key`, `github_pat`, `openai_api_key`, `slack_token`, `bearer_token`, `pem_private_key`, `email_credential`). `graphify/harness_export.py:112-167` `scan_annotations_for_secrets` runs every pattern over all non-allow-list string values; `mode='redact'` replaces matches with `[REDACTED]` + stderr summary; `mode='error'` returns findings so CLI dispatcher exits non-zero. CLI flags wired in `graphify/__main__.py:1951,1956`. `tests/test_harness_export.py::test_include_annotations_flag_invokes_scanner` asserts end-to-end. |
| T-13-08 (dup HARNESS-08) | Integrity / silent drift | Repeated `graphify harness export` runs masking schema changes | mitigate | CLOSED | `graphify/harness_export.py:495-548` `_write_fidelity_manifest` records per-file SHA-256 + byte-length for every written file. Successive runs compare against prior `fidelity.json`; `round_trip` flips between `"first-export"` → `"byte-equal"` → `"drift"`. Corrupt priors treated as `first-export` (no false "byte-equal" reports). Written via `.tmp` + `os.replace` for atomic reader visibility. `tests/test_harness_export.py::test_round_trip_drift_detected_when_schema_changes` passes. |

## Accepted Risks Log

One threat is accepted with explicit scope-based rationale:

1. **T-13-09 — Docstring leak into `_meta.examples`.** Handler docstrings are
   already public (visible in source + exposed as MCP `description`).
   Elevating `Examples:` blocks to `_meta.examples` is surface-preserving,
   not surface-expanding. Developer discipline — "do not put secrets in
   docstrings" — applies uniformly; no new control required. ASVS L1.

## STRIDE Coverage Summary

| Category | Count | Threats |
|----------|-------|---------|
| Spoofing | 0 | — |
| Tampering | 5 | T-13-02, T-13-05, T-13-08 (CI), T-13-08 (HARNESS-08), T-13-10 |
| Repudiation | 0 | — |
| Information Disclosure | 4 | T-13-01, T-13-04, T-13-07, T-13-09 |
| Denial of Service | 1 | T-13-03 |
| Elevation of Privilege | 0 | — |

STRIDE gaps (Repudiation, EoP, Spoofing) are scoped-out by the Phase 13
threat model: the capability manifest is read-only for external agents,
the harness export requires explicit CLI invocation by the developer (no
auto-trigger), and there are no identity-asserting flows in scope.

## Unregistered Flags

None. No `## Threat Flags` sections were present in any of the four Phase 13
`SUMMARY.md` files (grep across `13-01-SUMMARY.md`..`13-04-SUMMARY.md`
returns zero matches).

## Verification Method Summary

- **Mitigate threats (9):** Code pattern located at cited `file:line`;
  corresponding test present in `tests/test_capability.py` (16 passed) or
  `tests/test_harness_export.py` (33 passed). Overall: `pytest
  tests/test_capability.py tests/test_harness_export.py -q` → 49 passed.
- **Accept threats (1):** Rationale documented; scope limits reviewed and
  deemed reasonable for ASVS Level 1.
- **Transfer threats:** none in this phase.

## Known Related Gaps (Non-Security)

The partial requirement flagged by `13-VERIFICATION.md` — **MANIFEST-06**
(per-tool metadata declared in `capability_tool_meta.yaml`) — is a
**definitional/integration gap, not a security gap**:

- Both `chat` and `get_focus_context` ARE present in `CAPABILITY_TOOLS`
  (no missing entries).
- Both DO carry `cost_class`, `deterministic`, `cacheable_until`, and
  `composable_from` fields in their manifest entries.
- The values cascade from `_tool_to_manifest_entry` defaults rather than
  being explicitly declared.
- No threat in the Phase 13 register (T-13-01..T-13-10) covers this gap;
  it does not affect the integrity, confidentiality, or availability
  properties above. Remediation is scheduled in Phase 18.2 task 1.

## Sign-off

Phase 13 is **SECURED**. All 10 threats in the register (T-13-01 through
T-13-10) are CLOSED against live code at HEAD. The capability manifest
subsystem's non-bypassable CI drift gate (`.github/workflows/ci.yml:40`)
enforces content integrity on every push/PR. The harness export subsystem's
default-deny annotation allow-list plus opt-in 7-pattern secret scanner
plus `validate_graph_path` confinement plus round-trip fidelity manifest
jointly prevent the three ROADMAP.md SC2 attack classes (manifest
injection, harness-export secret leak, capability-describe info disclosure).

_Retroactive audit filed 2026-04-22 under Phase 18.1 task 2 to close_
_`v1.4-MILESTONE-AUDIT.md` blocker `phases[0]`. Auditor: Claude_
_(gsd-secure-phase subagent, STRIDE pass against live code at HEAD=2b01edf)._
