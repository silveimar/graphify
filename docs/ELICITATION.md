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

## Non-goals (other phases)

- **Phase 40** — harness **import**, injection defenses, inverse import.
- **Phase 41** — **`--vault`** selector / multi-root UX productization.

For vault adapter basics, see `docs/vault-adapter.md`.
