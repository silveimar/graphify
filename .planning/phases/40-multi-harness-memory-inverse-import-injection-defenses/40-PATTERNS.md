# Phase 40 — Implementation pattern map

Maps new work onto existing modules so executors stay consistent with the codebase.

## `graphify/harness_export.py`

| Pattern | Use for Phase 40 |
|--------|-------------------|
| `export_claude_harness`, `_BLOCK_ORDER`, `string.Template.safe_substitute` | **Forward export** remains; add **caller** to **emit interchange JSON** from same **graph_data / sidecar** inputs where possible (PORT-01). |
| `_write_fidelity_manifest`, HARNESS-08 | Keep **byte-level** fidelity for markdown; interchange uses **separate provenance** (SEC-02) — do not conflate D-06 semantic tests with byte equality. |
| `set_clock` / `_default_clock` | Reuse for **deterministic tests** (PORT-04). |
| `validate_graph_path` import | Any write path for interchange output must use existing **path confinement** (PORT-05). |
| `SECRET_PATTERNS` / `_redact_secrets` | **Optional** reuse for annotation-heavy paths; interchange **must** still run **SEC-01** injection passes on **import**. |

## `graphify/harness_schemas/`

| Pattern | Use for Phase 40 |
|--------|-------------------|
| `schema_path("claude")` | Extend **only** in line with D-01: add **bundled JSON Schema** (or manifest YAML) for **interchange v1**; avoid loading arbitrary external URLs (SEC). |
| `claude.yaml` | **Inverse mapping** for Claude markdown import: **section / placeholder** layout drives parser (Phase 39 **SOUL / HEARTBEAT / USER** compatibility). |

## `graphify/security.py`

| Pattern | Use for Phase 40 |
|--------|-------------------|
| `validate_graph_path`, label sanitization | **PORT-05:** all resolved import paths and outputs under **graphify-out/** (or vault-resolved roots per existing commands). |
| `sanitize_label` | **SEC-01:** apply to **all** user-originating harness strings before merge. |
| New helpers (expected) | **Injection-pattern** helpers: **pure functions**, unit-tested; **default** normalize/strip per D-04. |

## `graphify/validate.py`

| Pattern | Use for Phase 40 |
|--------|-------------------|
| `validate_extraction` / `assert_valid` | **PORT-03:** import **must** end in **`validate_extraction` → empty errors** before `build`; **no** alternate schema in Phase 40. |
| `REQUIRED_NODE_FIELDS`, `REQUIRED_EDGE_FIELDS` | Import mappers **populate** every required field (`source_file` may be synthetic but **bounded**, e.g. `harness:import:path`). |

## `graphify/build.py`

| Pattern | Use for Phase 40 |
|--------|-------------------|
| `build`, `build_from_json` | **Consumers** of import output; ensure **ordering** with **Phase 39 sidecars** is documented in executor plan (do not break **elicitation merge**). |

## `graphify/__main__.py`

| Pattern | Use for Phase 40 |
|--------|-------------------|
| Subcommand dispatch | Add **`import-harness`** next to **`harness`**, **`elicit`**, etc.—**single** subcommand per D-02. |
| `resolve_output()` / `--out` | **Mirror** existing harness/elicit flags for **artifact root** (D-03). |

## `graphify/serve.py` + `graphify/mcp_tool_registry.py`

| Pattern | Use for Phase 40 |
|--------|-------------------|
| `_handlers` dict **must** match `build_mcp_tools()` names (MANIFEST-05) | Add **import/export** tools only with **real** handlers calling **shared library** (SEC-03). |
| `call_tool` wrapper | **No** duplicate validation path—call **same** `import_harness*` / `export_harness*` functions as CLI. |

## `SECURITY.md`

| Pattern | Use for Phase 40 |
|--------|-------------------|
| Threat table rows | New subsection: **Harness import/export** — **trust boundaries** (filesystem, MCP client), **STRIDE-oriented** mitigations, **refs** PORT-01–05, SEC-01–04 (D-07). |

---

*Artifact: 40-PATTERNS.md — fast orientation for Phase 40 implementation.*
