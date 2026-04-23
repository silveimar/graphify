# Phase 13 — Research: Agent Capability Manifest (+ SEED-002)

**Status:** Complete for Wave A planning  
**Sources:** `13-CONTEXT.md` (D-01..D-04), `.planning/REQUIREMENTS.md` (MANIFEST-01..10, HARNESS-01..08), `graphify/serve.py`, MCP registry conventions

---

## 1. MCP servers-registry `server.json` (spec dated 2025-11-25)

**Purpose (MANIFEST-01):** Repo-root **`server.json`** is the static discovery document for MCP **server registry** clients: it describes how to launch graphify as an MCP server (command, args, cwd hints, optional env) so external registries and IDEs can auto-wire the integration without reading Python.

**Shape (executor must align to the published MCP registry schema for that date):**

- Include a **`$schema`** (or equivalent registry pointer) when the spec publishes a stable JSON Schema URL — keeps validation deterministic in CI.
- **Identity:** human-readable `name`, `description`, optional `version` string aligned with `pyproject.toml`.
- **Packages / server entries:** at least one launch recipe for the **stdio** transport matching how users run graphify today (e.g. `python -m graphify serve` with default `graphify-out/graph.json` or documented argv).
- **No fictional tools:** per **D-01**, static JSON must not advertise MCP tool names that `serve.py::list_tools()` does not return at generation time.

**Wave A note:** Wave A lists **only** tools actually registered after Phases 12 + 18 per ROADMAP; no placeholder tool names.

---

## 2. JSON Schema validation (MANIFEST-04)

- **Validator:** `jsonschema` with **Draft 2020-12** (`jsonschema.Draft202012Validator`) per REQUIREMENTS; dependency is **transitive via `[mcp]`** — executor verifies import in the `[mcp]` extra venv; if missing in practice, add an explicit dependency in `pyproject.toml` (no silent skip).
- **Artifacts:**
  - **Runtime manifest** (`graphify-out/manifest.json`): validate against a **graphify-owned** schema file (e.g. `graphify/capability_manifest.schema.json`) checked into the repo — includes tool array, versioning, and extension fields (`cost_class`, `deterministic`, etc.).
  - **Static `server.json`:** validate against the **registry** schema URL or a vendored snapshot if the registry publishes one — keeps MANIFEST-01 and MANIFEST-04 aligned.
- **CLI contract:** `graphify capability --validate` loads committed `server.json` (and any paired generated artifact the gate compares), validates, exits **non-zero** on failure with **D-03** messaging (expected vs actual hash, paths, regenerate command — no huge unified diff by default).

---

## 3. Introspection pattern (MANIFEST-05, Pitfall 12)

**Single source of truth:** No hand-maintained tool lists in docs or JSON.

**Pattern:**

1. **Extract** the MCP tool table from the same code path **`list_tools()`** uses: either move tool definitions to a module-level builder `build_tool_definitions() -> list[Tool]` imported by `serve.py`, or have `graphify/capability.py` import and call a **pure** registrar that returns structured tool metadata (name, description, inputSchema, optional `_meta` / cost hints).
2. **Mirror `_handlers`:** manifest generation asserts `set(handler keys) == set(tool names from list_tools)`; mismatch fails generation or `--validate` (fail-closed).
3. **CLI dispatch (future-facing):** REQUIREMENTS name **CLI dispatch** as an introspection source — export a small registry from `__main__.py` (subcommand names) or a shared `CLI_COMMANDS` iterable for merge into `manifest.json` under a `cli` section so Wave B does not duplicate strings.

**Top-level `CAPABILITY_TOOLS`:** The generated **`manifest.json`** should expose a **`CAPABILITY_TOOLS`** (or `tools`) array that is **only** emitted from this introspection pipeline — never edited by hand.

---

## 4. Per-tool agent metadata (MANIFEST-06)

Each tool entry should carry (at minimum):

| Field | Role |
|--------|------|
| `cost_class` | `free` \| `cheap` \| `expensive` — coarse guidance for agents |
| `deterministic` | bool — whether outputs are stable given fixed graph + sidecars |
| `cacheable_until` | string or structured hint — e.g. graph mtime / manifest generation id |
| `composable_from` | list of tool names — empty for primitives |

**Source:** Defaults can live in a small **`graphify/capability_tool_meta.yaml`** (like `routing_models.yaml`) keyed by tool name, merged with introspected names — avoids scattering magic dicts in `serve.py` while keeping names DRY.

---

## 5. `capability_describe` merged payload (MANIFEST-03)

**Static slice:** Contents (or path reference) of **`server.json`** + **`manifest.json`** as generated.

**Live slice (non-secret scalars):**

- Graph: node/edge/community counts (from loaded `G` after reload).
- **Alias map size:** `len(_alias_map)` from `dedup_report.json`.
- **Sidecar freshness:** mtimes or short hashes for `graph.json`, `telemetry.json`, `annotations.jsonl`, `agent-edges.json`, `dedup_report.json`, and **`enrichment.json`** when present (Phase 15 — Wave A may stub read with “absent” if file missing).
- **Enrichment snapshot id:** from overlay file if present (e.g. top-level `snapshot_id` or version field in `enrichment.json` — executor aligns field name to Phase 15 when shipped).

**Envelope:** D-02 — `text_body + "\n---GRAPHIFY-META---\n" + json(meta)` with MCP-friendly status in `meta`.

---

## 6. Manifest content-hash in every MCP `meta` (MANIFEST-07, D-04)

**Algorithm (Claude’s discretion):** **SHA-256** over **UTF-8 bytes** of **canonical JSON** for the manifest payload (sorted keys, stable separators) — record as `manifest_content_hash` (hex) in `meta`.

**Invalidation / caching (D-04):** Recompute when **manifest-relevant state** changes — **aligned with `serve.py` reload semantics**, not only process start:

- **Minimum:** invalidate when **`graph.json`** mtime changes (same trigger as `_reload_if_stale()`).
- **Narrow allowlist (planner-refined):** also bump revision when any of these change mtime: `dedup_report.json`, `telemetry.json`, `annotations.jsonl`, `agent-edges.json`, **`enrichment.json`** (when Phase 15 lands). Optional: single **“manifest epoch”** file updated by pipeline when `manifest.json` is rewritten (MANIFEST-02) to avoid re-hashing large JSON on every RPC — cache **hash + file mtimes tuple** in `serve()` closure; recompute only when tuple changes.

**Wiring:** Centralize **`_append_graphify_meta(text, base_meta)`** in `serve.py` so **every** `call_tool` response includes the sentinel + JSON `meta` with **`manifest_content_hash`**. Handlers that already return D-02 merge/replace without duplicating sentinels.

---

## 7. Runtime `manifest.json` on pipeline runs (MANIFEST-02)

- Hook **full pipeline completion** (same path that finalizes `graphify-out/graph.json`) to write **`graphify-out/manifest.json`** via **atomic `.tmp` + `os.replace`**, using the same generator as CLI `--stdout`.
- Include **`graphify` version** string from package metadata.

---

## 8. Skill frontmatter (MANIFEST-08)

Add to **`graphify/skill.md`** (and codex variants if project policy requires parity):

```yaml
capability_manifest: graphify-out/manifest.json
```

---

## 9. P2 items (not Wave A plan 13-01 scope)

| ID | Note |
|----|------|
| **MANIFEST-09** | CI gate — wire `graphify capability --validate` into CI; committed `server.json` + hash comparison — **later plan** in Phase 13. |
| **MANIFEST-10** | Docstring → `_meta.examples` — **later plan**; depends on stable docstrings per tool. |

---

## 10. Wave B (out of scope for 13-01)

- **HARNESS-01..08** + full MCP surface after Phases 14–18 — **separate plans**; Wave B regenerates manifest and ships `graphify harness export`.

---

## RESEARCH COMPLETE

Wave A implementation can proceed: registry-shaped **`server.json`**, introspection-backed **`manifest.json`**, **`graphify capability`** CLI with **jsonschema** validation, **`capability_describe`** MCP tool with merged static+live JSON, and **manifest hash** in **all** MCP tool responses with **cache invalidation** tied to **`_reload_if_stale`** and sidecar mtimes per **D-04**.
