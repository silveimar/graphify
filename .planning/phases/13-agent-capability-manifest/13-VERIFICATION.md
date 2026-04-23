---
phase: 13-agent-capability-manifest
verified: 2026-04-22T21:05:00-05:00
status: gaps_found
score: 17/18 requirements verified (1 partial)
re_verification: false
retroactive: true
shipped: 2026-04-17
audit_source: .planning/v1.4-MILESTONE-AUDIT.md (Phase 18.1 task 1)
requirements-verified:
  - MANIFEST-01
  - MANIFEST-02
  - MANIFEST-03
  - MANIFEST-04
  - MANIFEST-05
  - MANIFEST-07
  - MANIFEST-08
  - MANIFEST-09
  - MANIFEST-10
  - HARNESS-01
  - HARNESS-02
  - HARNESS-03
  - HARNESS-04
  - HARNESS-05
  - HARNESS-06
  - HARNESS-07
  - HARNESS-08
requirements-partial:
  - MANIFEST-06
requirements-failed: []
gaps:
  - truth: "Every tool entry declares cost_class / deterministic / cacheable_until / composable_from sourced from capability_tool_meta.yaml (MANIFEST-06)"
    status: partial
    reason: "Tools `chat` and `get_focus_context` are registered in mcp_tool_registry.py (lines 256, 290) but have NO entry in graphify/capability_tool_meta.yaml. build_manifest_dict() emits them with cascade defaults (cost_class=cheap, deterministic=False, cacheable_until=graph_mtime, composable_from=[]) rather than declared values, weakening the MANIFEST-06 contract that per-tool cost/determinism be explicitly stated rather than silently defaulted."
    artifacts:
      - path: "graphify/capability_tool_meta.yaml"
        issue: "Missing `chat:` and `get_focus_context:` blocks; the other 22 registered tools all have explicit entries."
    missing:
      - "Add `chat:` block to capability_tool_meta.yaml declaring cost_class, deterministic, cacheable_until, composable_from"
      - "Add `get_focus_context:` block with the same fields"
      - "Regenerate server.json (`graphify capability --stdout > server.json`) so the committed hash matches the new manifest"
    remediation_plan: "Phase 18.2 task 1 (18.2-01-PLAN.md) per v1.4-MILESTONE-AUDIT.md integration[0]."
---

# Phase 13: Agent Capability Manifest + SEED-002 Harness Memory Export — Verification Report

**Phase Goal:** Ship the static `server.json` + runtime `graphify-out/manifest.json` + MCP `capability_describe` tool + `graphify capability` CLI + manifest-hash drift detection across every MCP envelope, plus bundled SEED-002 `graphify harness export` emitting the SOUL/HEARTBEAT/USER triplet for the Claude harness. Introspection-driven, never hand-maintained.

**Verified:** 2026-04-22 (retroactive audit — phase shipped 2026-04-17)
**Status:** gaps_found (1 PARTIAL, 17 PASSED, 0 FAILED)
**Re-verification:** No — initial verification produced retroactively under Phase 18.1 to close the v1.4 milestone audit blocker.

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | Committed repo-root `server.json` validates as MCP servers-registry document with `_meta.manifest_content_hash` | VERIFIED | `server.json` root keys `$schema, name, title, version, description, packages, _meta`; `_meta.manifest_content_hash = 05aaa081311897c5152d...` |
| 2 | `graphify capability --stdout` emits canonical manifest JSON; `--validate` exits 0 on clean tree | VERIFIED | `graphify/__main__.py:1915` (`elif cmd == "capability":`); `graphify/capability.py:257` `validate_cli`; `pytest tests/test_capability.py -q` → 16 passed incl. `test_validate_cli_clean_tree` |
| 3 | `capability_describe` MCP tool returns D-02 envelope merging static manifest + live state | VERIFIED | `graphify/serve.py:3041` `_tool_capability_describe`; registered in `_handlers` at `graphify/serve.py:3112`; `name="capability_describe"` in `mcp_tool_registry.py` |
| 4 | Every MCP tool response carries `meta.manifest_content_hash` via QUERY_GRAPH_META_SENTINEL | VERIFIED | `graphify/serve.py:903` defines sentinel; 28 `QUERY_GRAPH_META_SENTINEL + json.dumps(meta...)` call sites across all handlers; `manifest_content_hash` cached at `_reload_if_stale` boundary |
| 5 | Introspection-driven single source of truth for tool definitions (MANIFEST-05) | VERIFIED | `graphify/mcp_tool_registry.py:57` `build_mcp_tools`; `serve.py::list_tools` delegates; registry↔`_handlers` set-equality assert at bind time |
| 6 | Per-tool cost_class/deterministic/cacheable_until/composable_from declared via YAML (MANIFEST-06) | **PARTIAL** | `capability_tool_meta.yaml` has 21 explicit tool entries but **missing `chat` and `get_focus_context`** which are registered at `mcp_tool_registry.py:256, 290` and silently cascade to defaults |
| 7 | `capability_manifest:` frontmatter key in `skill.md` / `skill-codex.md` (MANIFEST-08) | VERIFIED | `graphify/skill.md:5` `capability_manifest: graphify-out/capability.json`; `graphify/skill-codex.md:5` same |
| 8 | CI drift gate `graphify capability --validate` runs on every push/PR, non-bypassable (MANIFEST-09) | VERIFIED | `.github/workflows/ci.yml:40` `graphify capability --validate`; no `continue-on-error`; no `GRAPHIFY_SKIP` env guard (verified by test `test_validate_cli_drift_detected`) |
| 9 | Per-tool `_meta.examples` auto-extracted from handler docstrings (MANIFEST-10) | VERIFIED | `graphify/capability.py:40` `extract_tool_examples`; `graphify/mcp_tool_registry.py:356` `build_handler_docstrings`; `graphify/serve.py:29` `_handlers_snapshot`; 22/22 tool entries carry `_meta.examples: list[str]` (uniform, possibly empty per D-01) |
| 10 | `graphify harness export` emits SOUL/HEARTBEAT/USER markdown (HARNESS-01/04/05) | VERIFIED | `graphify/harness_export.py:555` `export_claude_harness`; `graphify/__main__.py:1930` (`elif cmd == "harness":`); output filenames `claude-SOUL.md`, `claude-HEARTBEAT.md`, `claude-USER.md` under `graphify-out/harness/` |
| 11 | Declarative YAML schema with required `{{ token }}` placeholders (HARNESS-02) | VERIFIED | `graphify/harness_schemas/claude.yaml` declares `soul`, `heartbeat`, `user` blocks with `{{ god_nodes }}`, `{{ recent_deltas }}`, `{{ hot_paths }}`, `{{ agent_identity }}`, `{{ generated_at }}`, `{{ graphify_version }}` |
| 12 | `{{ token }}` → `${token}` single-regex normalization + `string.Template.safe_substitute` — no Jinja2 (HARNESS-03) | VERIFIED | `graphify/harness_export.py:175` `_normalize_placeholders`; no `import jinja2` matches in module; `test_no_jinja2_import` passes |
| 13 | Annotations excluded by default via ANNOTATION_ALLOW_LIST (HARNESS-06, T-13-04) | VERIFIED | `graphify/harness_export.py:31` `ANNOTATION_ALLOW_LIST = frozenset({'id','label','source_file','relation','confidence'})`; `_filter_annotations_allowlist` at `:311`; `test_annotations_allow_list_default` asserts `peer_id` + free-text body scrubbed |
| 14 | 7-pattern secret scanner gates `--include-annotations` (HARNESS-07, T-13-07) | VERIFIED | `graphify/harness_export.py:82` `SECRET_PATTERNS` tuple includes `aws_access_key, github_pat, openai_api_key, slack_token, bearer_token, pem_private_key, email_credential`; `scan_annotations_for_secrets(..., mode={redact,error})` at `:112`; `--include-annotations` + `--secrets-mode` wired in `__main__.py:1951,1956` |
| 15 | Round-trip fidelity manifest (HARNESS-08, T-13-08) | VERIFIED | `graphify/harness_export.py:495` `_write_fidelity_manifest` writing `fidelity.json` with per-file SHA-256 + byte-length; `round_trip` field values `"first-export"`, `"byte-equal"`, `"drift"`; `set_clock` seam at `:472` |
| 16 | Output confined to `graphify-out/harness/` via `validate_graph_path` (T-13-05) | VERIFIED | `export_claude_harness` runs `validate_graph_path(harness_dir, base=out_dir)` before any write; `test_output_confined_to_graphify_out` passes |
| 17 | Deterministic byte-equal output with pinned clock (T-13-06) | VERIFIED | Stable sort keys in `_collect_god_nodes/_collect_recent_deltas/_collect_hot_paths`; fixed SOUL→HEARTBEAT→USER emission order; `test_round_trip_byte_equal_with_frozen_clock` passes |
| 18 | No auto-trigger — explicit CLI invocation only (locked decision) | VERIFIED | `grep -rn 'export_claude_harness\|from graphify.harness_export' graphify/watch.py graphify/pipeline.py` → no matches |

**Score:** 17 / 18 (MANIFEST-06 PARTIAL — 21 of 22 tool entries explicitly declared; 2 cascade to defaults)

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `server.json` | Repo-root static MCP servers-registry document (MANIFEST-01) | VERIFIED | 7 top-level keys, `_meta.manifest_content_hash` = `05aaa081...`, validates against capability_manifest.schema.json via `validate_cli` |
| `graphify/capability.py` | build_manifest_dict + canonical_manifest_hash + validate_cli + write_manifest_atomic + extract_tool_examples | VERIFIED | All referenced functions present; `build_manifest_dict` integrates YAML meta + docstring examples + registry introspection |
| `graphify/mcp_tool_registry.py` | Single source of truth for MCP Tool list (MANIFEST-05) | VERIFIED | `build_mcp_tools` + `tool_names_ordered` + `build_handler_docstrings`; 22 tools registered; `_handlers_snapshot` bridge to serve.py |
| `graphify/capability_tool_meta.yaml` | Per-tool MANIFEST-06 metadata | **PARTIAL** | 21 tool entries present; `chat` and `get_focus_context` **missing** |
| `graphify/capability_manifest.schema.json` | JSON Schema Draft 2020-12 shape for manifest | VERIFIED | Exists, consumed by `validate_manifest` |
| `graphify-out/manifest.json` | Runtime-generated manifest (MANIFEST-02) | VERIFIED (by construction) | `write_runtime_manifest` pipeline hook; not materialized in repo (expected — `graphify-out/` is .gitignored) |
| `graphify/harness_schemas/__init__.py` + `claude.yaml` | Declarative harness schema bundled via setuptools | VERIFIED | `schema_path('claude')` accessor; YAML has three blocks with four required placeholders; `pyproject.toml` registers `graphify.harness_schemas` in `[tool.setuptools.package-data]` |
| `graphify/harness_export.py` | Core exporter + scanner + fidelity + clock seam | VERIFIED | All HARNESS-01..08 surface present in one module |
| `tests/test_capability.py` | Capability unit tests | VERIFIED | 16 passed |
| `tests/test_harness_export.py` | Harness unit tests | VERIFIED | 33 passed (22 expected from Plan 04 SUMMARY + 11 added during execution) |

### Key Link Verification

| From | To | Via | Status |
|------|-----|-----|--------|
| `serve.py::list_tools` | `mcp_tool_registry.build_mcp_tools` | delegation (MANIFEST-05) | WIRED |
| `serve.py::_handlers` | `mcp_tool_registry` tool names | set-equality assert at bind | WIRED |
| `capability.py::build_manifest_dict` | `mcp_tool_registry.build_mcp_tools` + `build_handler_docstrings` | module import | WIRED |
| `capability.py::build_manifest_dict` | `capability_tool_meta.yaml` | `_load_yaml_meta` | WIRED (partial coverage — see MANIFEST-06 gap) |
| `__main__.py::cmd == 'capability'` | `capability.print_manifest_stdout` / `validate_cli` | dispatcher | WIRED |
| `__main__.py::cmd == 'harness'` | `harness_export.export_claude_harness` | dispatcher | WIRED |
| Every `_tool_*` handler response | `manifest_content_hash` | QUERY_GRAPH_META_SENTINEL envelope (28 sites) | WIRED |
| `harness_export.export_claude_harness` | `security.validate_graph_path` | import + call before write | WIRED |
| `.github/workflows/ci.yml` | `graphify capability --validate` | CI step line 40 (no bypass) | WIRED |
| `skill.md` / `skill-codex.md` | `graphify-out/capability.json` | frontmatter `capability_manifest:` | WIRED |

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|-------------|-------------|--------|----------|
| MANIFEST-01 | 13-01 | Static server.json at repo root | PASSED | `server.json` committed |
| MANIFEST-02 | 13-01 | Runtime graphify-out/manifest.json regenerated on pipeline | PASSED | `capability.py:244` `write_runtime_manifest` + export.py hook |
| MANIFEST-03 | 13-01 | `capability_describe` merges static + live state | PASSED | `serve.py:3041` |
| MANIFEST-04 | 13-01 | `graphify capability [--stdout|--validate]` CLI | PASSED | `__main__.py:1915`; 16 capability tests green |
| MANIFEST-05 | 13-01 | Introspection over list_tools / _handlers, never hand-maintained | PASSED | `mcp_tool_registry.build_mcp_tools` single source |
| MANIFEST-06 | 13-01 | Per-tool cost_class/deterministic/cacheable_until/composable_from | **PARTIAL** | 21/23 tools explicit; `chat` + `get_focus_context` cascade to defaults — Phase 18.2 task 1 |
| MANIFEST-07 | 13-01 | `manifest_content_hash` on every MCP response envelope | PASSED | 28 sentinel sites in `serve.py` |
| MANIFEST-08 | 13-01 | Skill frontmatter `capability_manifest:` key | PASSED | `skill.md:5`, `skill-codex.md:5` |
| MANIFEST-09 [P2] | 13-02 | CI drift gate `graphify capability --validate` | PASSED | `ci.yml:40`; no bypass; `test_validate_cli_drift_detected` |
| MANIFEST-10 [P2] | 13-02 | Per-tool `_meta.examples` extracted from docstrings | PASSED | `extract_tool_examples` + `build_handler_docstrings` + `_handlers_snapshot`; 22/22 tools carry `_meta.examples` uniformly |
| HARNESS-01 | 13-03 | `graphify/harness_export.py` reads 4 sidecars, emits SOUL/HEARTBEAT/USER | PASSED | `export_claude_harness` + `_load_sidecars` |
| HARNESS-02 | 13-03 | `claude.yaml` schema with 4 required placeholders | PASSED | `harness_schemas/claude.yaml` |
| HARNESS-03 | 13-03 | `string.Template.safe_substitute`, no Jinja2 | PASSED | `_normalize_placeholders` + `test_no_jinja2_import` |
| HARNESS-04 | 13-03 | `graphify harness export [--target claude] [--out PATH]` CLI | PASSED | `__main__.py:1930` |
| HARNESS-05 | 13-03 | Output filenames under `graphify-out/harness/` | PASSED | YAML `filename:` entries + `test_export_writes_three_files` |
| HARNESS-06 | 13-03 | Annotations excluded via allow-list by default | PASSED | `ANNOTATION_ALLOW_LIST` + `_filter_annotations_allowlist` |
| HARNESS-07 [P2] | 13-04 | Secret-scanner regex suite over `--include-annotations` | PASSED | 7-pattern `SECRET_PATTERNS` + `scan_annotations_for_secrets(mode={redact,error})` |
| HARNESS-08 [P2] | 13-04 | Round-trip fidelity summary (byte-equal manifest) | PASSED | `_write_fidelity_manifest` + `set_clock` + `round_trip` field |

### Anti-Patterns Scan

Files inspected: `graphify/capability.py`, `graphify/mcp_tool_registry.py`, `graphify/harness_export.py`, `graphify/harness_schemas/__init__.py`, `graphify/harness_schemas/claude.yaml`, `server.json`.

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| (none) | — | No TODO / FIXME / XXX / HACK / PLACEHOLDER / "not implemented" / "coming soon" matches in any Phase 13 source or schema file | — | — |

Two incidental matches in `harness_export.py` for the phrases "not implemented" / "coming soon" were verified as docstring/comment wording inside prose, not stub markers — zero TODO/FIXME/XXX/HACK hits on a strict grep.

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
|----------|---------|--------|--------|
| Manifest hash is stable / deterministic | `python -c "from graphify.capability import build_manifest_dict, canonical_manifest_hash; d=build_manifest_dict(); print(canonical_manifest_hash(d))"` | `05aaa081311897c5152d42dc7fef790431c16912fc89a15fa5b9525472554645` | PASS |
| server.json committed hash matches live introspection | `python3 -c "import json; assert json.load(open('server.json'))['_meta']['manifest_content_hash'] == '05aaa081311897c5152d42dc7fef790431c16912fc89a15fa5b9525472554645'"` | exit 0 | PASS |
| Every manifest tool entry carries `_meta.examples: list` | Python assert across 22 tools | exit 0 | PASS |
| `chat` + `get_focus_context` present in registry | introspection via `build_manifest_dict()` → `CAPABILITY_TOOLS` names | both present | PASS |
| `chat` + `get_focus_context` carry declared (non-default) metadata | diff declared YAML vs manifest entry | cascade to defaults (cheap/False/graph_mtime/[]) | **FAIL** (MANIFEST-06 partial) |
| `pytest tests/test_capability.py tests/test_harness_export.py -q` | unit suite | 49 passed | PASS |
| No Jinja2 in harness module | `grep -E "^(from|import) jinja2" graphify/harness_export.py` | no matches | PASS |
| No harness auto-trigger wiring | `grep -rn "export_claude_harness" graphify/watch.py graphify/pipeline.py` | no matches | PASS |

### Success Criteria (from ROADMAP.md Phase 13)

- [x] Static `server.json` + runtime `manifest.json` produced via introspection (MANIFEST-01, MANIFEST-02, MANIFEST-05)
- [x] `capability_describe` MCP tool merges static + live state (MANIFEST-03)
- [x] `graphify capability` CLI with `--stdout` and `--validate` (MANIFEST-04)
- [~] Per-tool MANIFEST-06 metadata declared — **PARTIAL: 2 of 23 tools (chat, get_focus_context) fall through to defaults; see gap**
- [x] `manifest_content_hash` on every MCP response envelope (MANIFEST-07)
- [x] Skill frontmatter `capability_manifest:` key (MANIFEST-08)
- [x] CI drift gate non-bypassable (MANIFEST-09)
- [x] Per-tool `_meta.examples` from docstrings (MANIFEST-10)
- [x] `graphify harness export` emits SOUL/HEARTBEAT/USER triplet (HARNESS-01..05)
- [x] Default-deny annotation allow-list (HARNESS-06)
- [x] `--include-annotations` secret scanner with redact/error modes (HARNESS-07)
- [x] Round-trip fidelity manifest (HARNESS-08)
- [x] No auto-trigger (locked decision honored)
- [x] Output confined to `graphify-out/harness/` (T-13-05)
- [x] Deterministic byte-equal output with pinned clock (T-13-06)

### Human Verification Required

None. All 18 REQ-IDs are verifiable programmatically against the live codebase. The single PARTIAL finding (MANIFEST-06) is a definitional gap — `chat` and `get_focus_context` cascade to implicit defaults rather than carrying explicitly declared metadata — and does not require human judgment to confirm: the check is purely a set-difference between `capability_tool_meta.yaml` keys and `build_mcp_tools()` tool names.

### Gaps Summary

**One gap remains, scoped to a single line-level integration defect:**

`graphify/capability_tool_meta.yaml` omits entries for two tools that are registered in `graphify/mcp_tool_registry.py` (`chat` at line 256, `get_focus_context` at line 290). Both were added to the registry after Phase 13's Plan 01 shipped — Plan 13-01 owned the initial 21-tool YAML, and subsequent phases (Phase 17 `chat`, Phase 18 `get_focus_context`) registered their tools without back-filling the MANIFEST-06 metadata file.

**Why this is PARTIAL and not FAILED:**
- Both tools ARE emitted in `CAPABILITY_TOOLS` (no missing entries — verified via `build_manifest_dict()`).
- They DO carry `cost_class`, `deterministic`, `cacheable_until`, and `composable_from` fields in their manifest entries.
- But those values come from the implicit cascade (`cheap` / `False` / `graph_mtime` / `[]`) in `_tool_to_manifest_entry` rather than from explicit declarations in the YAML. MANIFEST-06's spirit — "so agents can reason about cost + composition before calling" — is undermined: an agent cannot tell the difference between "this tool was explicitly declared cheap + non-deterministic" and "this tool's metadata was forgotten and fell through to the cheap default."

**Remediation** is scheduled in **Phase 18.2 task 1** (`18.2-01-PLAN.md`) per `v1.4-MILESTONE-AUDIT.md` integration[0]. No other Phase 13 gaps exist; all 17 remaining REQ-IDs verify cleanly.

### Deferred Items

None. This verification covers all 18 REQ-IDs attributable to Phase 13; no work was pushed into Phase 13 from prior phases that would need later-phase reconciliation beyond the MANIFEST-06 remediation already scheduled in Phase 18.2.

---

_Retroactive verification filed 2026-04-22 under Phase 18.1 task 1 to close `v1.4-MILESTONE-AUDIT.md` blocker `phases[0]`._
_Verifier: Claude (gsd-verifier, goal-backward pass against live codebase at HEAD=2b01edf)._
_Tests: `pytest tests/test_capability.py tests/test_harness_export.py -q` → 49 passed, 0 failed._
