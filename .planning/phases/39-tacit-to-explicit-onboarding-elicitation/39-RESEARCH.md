# Phase 39 — Research notes: tacit-to-explicit elicitation

**Status:** Planning artifact (executor handoff)  
**Locks:** All behavior must satisfy `39-CONTEXT.md` D-01..D-08.

## Hybrid interview (D-03)

- **Scripted backbone:** Implement as an explicit state machine (named states, deterministic transitions, inputs mapped to `nodes`/`edges` builders). This mirrors `graphify/harness_export.py`’s utilities-only, test-heavy style: no LLM in the default code path used by CI.
- **Optional deepening:** Gate behind a CLI flag (e.g. `--deepen`) and/or env (e.g. `GRAPHIFY_ELICIT_LLM=1`). Implementation should call the same semantic extraction hook pattern used elsewhere (`extract.py` / cache / API env), not a second ad-hoc client. Baseline tests stay LLM-off.

## Sidecar merge (D-06)

- **`build.build` / `build.build_from_json`:** Today `build.py` concatenates `nodes`/`edges` from multiple extraction dicts; last writer wins for duplicate node IDs (documented in module header). Elicitation sidecar should be merged as **one additional extraction dict** in a **fixed position** in the list (document the order in code comments, e.g. after AST extractions, before or after semantic — pick one and test).
- **Persisted bundle:** Prefer a single JSON file under the resolved artifacts directory, e.g. `graphify-out/elicitation.json` (name is planner discretion; must pass `validate_graph_path` relative to artifacts root). Contents: extraction-shaped `{"nodes":[],"edges":[]}` plus optional metadata block ignored by `validate_extraction` if stripped before validation (or metadata only in wrapper keys filtered before `validate_extraction`).
- **Validation:** Always run `validate.validate_extraction` on the merged dict (or per-chunk pre-merge) — same required fields as code extraction (`validate.py` `REQUIRED_NODE_FIELDS`, `REQUIRED_EDGE_FIELDS`, `VALID_CONFIDENCES`, `VALID_FILE_TYPES`). Use `file_type`: `rationale` or `document` for interview-derived concept nodes unless a seed prescribes otherwise.

## Harness export alignment (D-04)

- **`export_claude_harness`:** Entry point in `graphify/harness_export.py`; reads `graph.json`, `annotations.jsonl`, `agent-edges.json`, `telemetry.json` from the artifacts dir; emits `harness/claude-*.md` per `graphify/harness_schemas/claude.yaml` using `string.Template.safe_substitute` only (`HARNESS-03`).
- **Graph path:** After elicitation merge, a normal `graphify run` (or test helper) should produce `graph.json` such that `harness export` sees elicitation-sourced annotations or node labels in god-node / delta sections where appropriate.
- **Direct path (no graph yet):** Render SOUL/HEARTBEAT/USER-class markdown from elicitation session state by reusing the same placeholder keys as `claude.yaml` (`agent_identity`, `god_nodes`, `recent_deltas`, `hot_paths`, etc.) — either by calling internal collector helpers with synthetic graph_data or by a thin renderer that loads the YAML schema and fills from elicitation dict only. Do not introduce Jinja2.

## Vault-resolved output (D-05)

- **`ResolvedOutput`:** Defined in `graphify/output.py` (`resolve_output(cwd, cli_output=…)`). Fields: `artifacts_dir`, `notes_dir`, `vault_path`, `source`. Elicitation writes (sidecar JSON, optional harness staging) default to `resolved.artifacts_dir`, not a hard-coded `graphify-out` string when vault mode applies.
- **Precedence:** `--output` / profile / default semantics already live in `resolve_output`; elicit command should accept the same output flags as `run` where practical, or document CWD + `resolve_output` parity in `39-04` PLAN.

## CLI surface (D-01, D-02)

- **Dispatch pattern:** `graphify/__main__.py` uses `elif cmd == "harness":` with nested ArgumentParser for `harness export` (see ~lines 2181–2216). Add sibling branch `elif cmd == "elicit":` (or `graphify elicit` subcommands) calling a new `graphify.elicit` module — avoid embedding interview logic in `__main__.py`.
- **Onboarding emphasis:** Help text and `docs/ELICITATION.md` should state that elicitation is **recommended when the corpus is empty or tiny** (D-02), not a parallel mandatory step for every full repo run.

## Security

- **`validate_graph_path`:** Used in `harness_export` for output confinement (`HARNESS-05` / Phase 13 tests in `tests/test_harness_export.py`). All elicitation file writes must use the same helpers as export/harness paths.
- **Label sanitization:** Reuse `graphify.security` helpers used by export/pipeline for user-provided strings before they become node labels or markdown bodies.

## Out of scope here (explicit)

- Phase **40** import defenses and multi-harness targets; Phase **41** `--vault` productization — only stable names (`elicitation.json`, merge order contract) should be documented for forward compatibility.
