# Phase 43 — Research notes

**Status:** Closed without parallel researcher agent — scope is narrow wiring per `43-CONTEXT.md`.

## Findings (code scout)

- `merge_elicitation_into_build_inputs` (`graphify/elicit.py`) is the single merge API; append ordering matches `build(..., elicitation=...)` “last wins” semantics.
- `run_update_vault` (`graphify/migration.py`) calls `build([extraction])` with no merge — gap confirmed at line ~209.
- `_rebuild_code` (`graphify/watch.py`) calls `build_from_json(result)` without reading `<graphify-out>/elicitation.json`.
- `graphify run` (`__main__.py`) ends after `run_corpus`; no `build` — ELIC-02 AC for “reaches build” is satisfied by fixing callers that already invoke `build`, plus docs clarifying `run` vs full graph outputs (`43-03-PLAN.md`).

## Risks

- Double-merge if a caller passes both `merge_elicitation_into_build_inputs` **and** `elicitation=` to `build()` — callers must use one pattern only.
