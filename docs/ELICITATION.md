# Tacit-to-explicit elicitation (Phase 39)

This guide covers graphify’s **discovery-first** path when you have little or no corpus yet. Requirements traceability: **ELIC-01–ELIC-07** in `.planning/REQUIREMENTS.md`.

## When to use elicitation

- **Empty or tiny corpus** — onboarding before code/docs exist (see Phase 39 D-02).
- You need **SOUL/HEARTBEAT/USER-shaped** harness markdown and a **`elicitation.json`** sidecar merged into the graph pipeline.

Use the full **`graphify run`** / **`/graphify`** pipeline once you have real files to extract.

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

## Non-goals (other phases)

- **Phase 40** — harness **import**, injection defenses, inverse import.
- **Phase 41** — **`--vault`** selector / multi-root UX productization.

For vault adapter basics, see `docs/vault-adapter.md`.
