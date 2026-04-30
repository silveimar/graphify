# Plan 43-03 — Summary

**Status:** Complete

## Delivered

- `docs/ELICITATION.md` — section **Where sidecar merge runs** (update-vault, watch, vs extract-only `run`); intro sentence aligned with ELIC-07.
- `graphify/__main__.py` — top-level `--help` lines for `run` clarify no `graph.json` and point to merge surfaces + `docs/ELICITATION.md`.

## Verification

- `graphify run --help` (via main usage) reflects extract-only + pointers.
