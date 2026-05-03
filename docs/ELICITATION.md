# Tacit-to-explicit elicitation (Phase 39)

This guide covers graphify’s **discovery-first** path when you have little or no corpus yet. Requirements traceability: **ELIC-01–ELIC-07** in `.planning/REQUIREMENTS.md`.

## When to use elicitation

- **Empty or tiny corpus** — onboarding before code/docs exist (see Phase 39 D-02).
- You need **SOUL/HEARTBEAT/USER-shaped** harness markdown and a **`elicitation.json`** sidecar merged into the graph pipeline.

Use **`graphify watch`**, **`graphify update-vault`**, or the **`/graphify`** skill pipeline when you need a persisted **`graph.json`** with sidecar merge. **`graphify run`** performs detect → extract only (no graph assembly); see `--help` under **`run`**.

## CLI (canonical)

```bash
graphify elicit [--output PATH] [--dry-run] [--demo] [--force]
```

- **`--demo`** — offline sample answers (try-me).
- **`--dry-run`** — prints resolved `artifacts_dir` and extraction counts; no writes.
- **`--force`** — overwrite sidecar merge behavior where applicable.

Implementation lives in **`graphify.elicit`** — skills only point here; they do not embed the state machine.

## Where artifacts land

Paths follow **`resolve_output()`** (see `graphify/output.py`): with a vault + profile, artifacts typically resolve to the sibling **`graphify-out/`** next to the vault; without a vault, **`./graphify-out`** under the working directory. Outputs include:

| Artifact | Location |
|----------|----------|
| Sidecar (merged by `build()`) | `<artifacts_dir>/elicitation.json` |
| Harness markdown (fast path) | `<artifacts_dir>/harness/claude-*.md` + `fidelity.json` |

## Merge order in `build()`

`graphify/build.py`: list extractions are merged in order; **`elicitation`** (or sidecar appended via `merge_elicitation_into_build_inputs`) comes **after** file extractions so duplicate node **`id`** values favor elicitation.

## Where sidecar merge runs (ELIC-02 / ELIC-07)

These paths resolve `<artifacts_dir>/elicitation.json` (when present) and pass **`merge_elicitation_into_build_inputs(...)`** before **`build()`**:

| Workflow | What happens |
|----------|----------------|
| **`graphify update-vault`** (`run_update_vault`) | Preview/apply builds the graph from corpus extraction plus sidecar under the vault’s resolved **`artifacts_dir`** (typically a sibling **`graphify-out/`**). |
| **`graphify watch`** (`_rebuild_code`) | Incremental rebuild merges sidecar from **`<project>/graphify-out/`** after AST extraction (and optional semantic carry-over from existing **`graph.json`**). |
| **`graphify run`** | **Does not** call **`build()`** or write **`graph.json`** — extract-only. Use **`watch`**, **`update-vault`**, or the full skill-driven pipeline when you need graph assembly with elicitation merge. |

## Trust Boundaries

This milestone (v1.11) clarifies what `elicit` and `import-harness` will and will not do, and where the trust line sits.

### Where elicitation reads / writes

`graphify elicit` resolves its artifacts directory through **`resolve_output()`** (see `graphify/output.py`). With a vault + profile, the sidecar lands at `<artifacts_dir>/elicitation.json` (typically the sibling `graphify-out/` next to the vault); without a vault, it lands at `./graphify-out/elicitation.json`. The pipeline never reads vault configuration without explicit user consent (the user must invoke `--vault` or `--profile`).

The sidecar merge precedence (elicitation overwrites base extraction on node-id collisions; conflicting edge attrs follow last-write-wins) is asserted by the regression suite at `tests/test_elicit.py` (Phase 57 ELIC-01 tests). That test module is the canonical record of the merge contract.

### What `import-harness` will and will not do

`graphify import-harness` is **off by default**: no other graphify command (`run`, `watch`, `update-vault`, `elicit`, `doctor`) invokes it transitively. It refuses to write reconstructed extractions under any vault root unless the user passes `--allow-vault-write`. The MCP `import_harness` tool requires an explicit `path` argument; missing or empty paths are rejected by `validate_graph_path`.

### LLM trust posture during `elicit`

Free-text answers from `--demo` and interactive elicitation are passed through `sanitize_harness_text` (`graphify/security.py`) before reaching downstream LLM calls or HTML / Obsidian export. Labels are HTML-escaped at export time (see `graphify/security.py::sanitize_label`). Size caps (`MAX_HARNESS_IMPORT_BYTES`) and prompt-injection guard patterns (`guard_harness_injection_patterns`) were established in Phase 40 and apply unchanged.

## Canonical Harness Interchange (v1) Mapping

The harness interchange envelope (`graphify.harness.interchange/v1`, exported by `export_interchange_v1` in `graphify/harness_interchange.py`) is the canonical input format for `graphify import-harness`. Field mapping mirrors `graph_data_to_extraction()` exactly:

| Envelope field | Maps to extraction key | Notes |
|----------------|------------------------|-------|
| `schema` | `INTERCHANGE_SCHEMA_ID` constant (`"graphify.harness.interchange/v1"`) | Required at top level; mismatched schema is rejected by `_parse_interchange_v1`. |
| `graph.nodes[]` | `nodes[]` | Each node carries `id`, `label`, `file_type`, `source_file`. |
| `graph.edges[]` | `edges[]` | Each edge carries `source`, `target`, `relation`, `confidence`, `source_file`. |
| `provenance` | dropped | Provenance is consumed for audit, not merged into the graph. |

A future bump to `/v2` MUST update the `schema` row above. The schema-id constant is asserted to match this doc by `tests/test_harness_interchange.py::test_interchange_schema_id_locked`.

## Milestone Non-Goals (v1.11)

- **Phase 40** — harness **import**, injection defenses, inverse import.
- **Phase 41** — **`--vault`** selector / multi-root UX productization.
- **Real inverse round-trip** (harness export → import → graph equality) — deferred to a future harness-expansion phase.
- **New harness target formats** beyond what is shipped today — orthogonal capability extension.
- **Re-testing Phase 40 size caps and prompt-injection guards** (`MAX_HARNESS_IMPORT_BYTES`, `guard_harness_injection_patterns`) — already covered.

For vault adapter basics, see `docs/vault-adapter.md`.
