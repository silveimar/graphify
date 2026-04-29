# Phase 40 Research — Harness JSON interchange, import pipeline, MCP parity

**Phase:** 40-multi-harness-memory-inverse-import-injection-defenses  
**Status:** Planning artifact (pre-implementation)  
**Locked decisions:** `40-CONTEXT.md` D-01–D-07  
**Requirements:** PORT-01–PORT-05, SEC-01–SEC-04  

## 1. Goals (outcome-shaped)

1. **PORT-01 / D-01:** A **second first-class export target** ships as **versioned canonical JSON interchange**, not new Codex/AGENTS markdown emitters in this phase.
2. **PORT-02:** Mapping and schema artifacts live **under `graphify/harness_schemas/`** (or adjacent versioned files) and are **imported by export/import code**—not ad-hoc stringly-typed dicts.
3. **PORT-03 / D-02–D-03:** **`graphify import-harness <path>`** reads **filesystem paths only** (stdin/URL deferred); **`--format auto|json|claude|…`** dispatches parsers; output is **`{"nodes","edges"}`** (or extraction-shaped envelope) that **`validate_extraction` accepts** without bypass.
4. **PORT-04 / D-06:** Tests prove **semantic preservation** of **node ids, labels, and relations** through **export → import** within **documented limits** (whitespace/format drift allowed).
5. **PORT-05:** Import uses **`security.validate_graph_path`** / **`resolve_output()`** discipline, **size caps**, and **rejects traversal** consistent with **`security.py`**.
6. **SEC-01 / D-04:** **Layered sanitization:** existing **`sanitize_label`** / sink patterns + **explicit injection-pattern guards** on imported free text; **default strips/normalizes**, optional **strict reject** only if explicitly specified in implementation plan.
7. **SEC-02:** Exported interchange (and, where applicable, existing markdown bundles) carry **provenance**: **schema/interchange version**, **timestamp**, **graphify version**, and a **stable run identity** when available.
8. **SEC-03 / D-05:** MCP tools for harness I/O call the **same library entrypoints** as CLI—**no parallel logic**; **no stubs that claim parity**.
9. **SEC-04 / D-07:** **`SECURITY.md`** gains a **full subsection** on harness import/export: **threats, mitigations, trust boundaries**, **traceable to PORT-*/SEC-***.

## 2. Non-goals (explicit)

- Phase **41** vault selector / `--vault` UX.
- **New markdown harness emitters** beyond JSON interchange (D-01); Codex bundles are **follow-up**.
- **Stdin / URL** import (D-03).
- Breaking **Phase 39** **`elicitation.json` / harness markdown** contracts **without a migration note** (39-CONTEXT D-04, D-06).

## 3. Canonical JSON interchange (v1 sketch)

**File naming (planner discretion, executor implements):** e.g. `graphify/harness_schemas/interchange_v1.schema.json` **or** `harness_memory.v1.json` document with `$schema` pointer.

**Top-level envelope (logical shape):**

| Field | Purpose |
|--------|--------|
| `interchange_version` | Integer or semver string; bump when breaking. |
| `provenance` | Object: `generated_at` (ISO 8601 UTC), `graphify_version`, `interchange_schema_id`, optional `source_run_id`, optional `source_graph` path string (informational). |
| `extraction` | Object with **`nodes`** and **`edges`** lists matching **`validate.py`** contract. |

**Alignment with existing export:**

- Reuse **conceptual tokens** from **`claude.yaml`** / **`export_claude_harness`** where nodes/edges are derived from the same graph snapshot + sidecars.
- **HARNESS-08** `fidelity.json` remains the **byte-oriented** manifest for markdown files; interchange may ship its own **content hash** inside `provenance` for drift detection—**not** replacing D-06 semantic round-trip bar with byte identity.

## 4. Import pipeline into `validate` / `build`

**Flow:**

1. **Resolve path** — `Path` argument; reject non-file; optional `validate_graph_path` when path must live under approved roots (mirror **`--out`** / **`resolve_output()`** rules used by `harness export` / `elicit`).
2. **Read + size cap** — cap aligned with other local file reads (reuse or mirror patterns from **`security.py`** / `safe_fetch` byte philosophy for consistency).
3. **Format detection** — `auto`: sniff JSON vs Claude harness markdown (e.g. frontmatter, SOUL/HEARTBEAT/USER sections); `json` / `claude` force parsers.
4. **Parse** — JSON: `json.loads` → validate envelope → extract `extraction`. Claude: **inverse** of template token binding (planner discretion: minimal viable parser that round-trips **fixture subset** per D-06).
5. **Sanitize** — **SEC-01:** run **`sanitize_label`** (and siblings) on node/edge text fields; apply **injection gadget regexes** (e.g. unbounded directive-like lines, nested code fences where inappropriate) per D-04; optionally attach **low-risk provenance flags** on nodes (`imported_from`, `format`) for audit.
6. **Validate** — `validate_extraction(extraction)`; surface errors to CLI/MCP caller; **no** `assert_valid` bypass in production paths.
7. **Consume** — return dict for **`build.build()`** / **`build_from_json()`** or write sidecar—**executor chooses** per Phase 39 merge story; Phase 40 must **not** corrupt **`elicitation.json`** merge semantics (read-only import into validated extraction is safe).

## 5. CLI surface (D-02, D-03)

- **Single subcommand:** `graphify import-harness <path>`.
- **Flags:** `--format`, **`--out`** (or mirror **`harness export`** / **`elicit`** output flag name already in `__main__.py`—executor grep and align), optional `--strict` if strict mode is specified.
- **No** subcommand-per-format in Phase 40 unless a hard conflict emerges (D-02).

## 6. Export surface additions (PORT-01, SEC-02)

- Extend **`harness export`** (or shared helper called from it) with **`--format`** or dedicated **`--interchange`** flag—executor picks **one** consistent UX.
- Emit interchange file(s) under **resolved artifacts directory** next to markdown harness when both are requested.

## 7. MCP parity (SEC-03)

- Add tools to **`mcp_tool_registry.build_mcp_tools()`** and matching **`serve.serve` `_handlers`** keys (existing **MANIFEST-05** invariant: **set equality**).
- Suggested tool names (executor finalizes): `export_harness_interchange`, `import_harness` — each calls **`graphify.*`** library functions **shared with CLI**.
- **Inputs:** JSON-serializable arguments only; paths must pass **`validate_graph_path`** where filesystem is touched.

## 8. Sanitization layering (SEC-01)

| Layer | Mechanism |
|--------|-----------|
| Structural | JSON schema / required keys; reject malformed interchange. |
| Label/text | `sanitize_label`, length caps, HTML escape where rendered. |
| Injection heuristics | Strip or neutralize patterns that resemble **instruction injection** in harness bodies (tests from representative vectors). |
| Policy | Default **sanitize**; **strict reject** optional (`--strict` / argument flag) only when explicitly implemented—D-04. |

## 9. Testing strategy (PORT-04, PORT-05, SEC-01)

- **Unit tests** in `tests/test_harness_interchange.py` (or split): export fixture → import → `validate_extraction` clean → **ids/labels/relations** preserved modulo documented normalization.
- **Traversal / escape** tests: paths outside allowed roots **fail closed**.
- **Injection fixtures:** strings that **would** manipulate downstream prompts **are neutralized** or rejected in strict mode—**assert** post-sanitization snapshots.

## 10. Traceability matrix

| REQ | Research section |
|-----|------------------|
| PORT-01 | §3, §6 |
| PORT-02 | §3 |
| PORT-03 | §4, §5 |
| PORT-04 | §3, §9 |
| PORT-05 | §4, §9 |
| SEC-01 | §8 |
| SEC-02 | §3 |
| SEC-03 | §7 |
| SEC-04 | §1 (goal 9) — implemented in SECURITY.md edit |

---

*Artifact: 40-RESEARCH.md — Phase 40 planning input for executors.*
