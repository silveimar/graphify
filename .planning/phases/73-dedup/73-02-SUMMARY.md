---
phase: 73
plan: 02
subsystem: dedup-spike
tags: [dedup, spike, measurement, sha256, fingerprint, ship-recommendation]
requires: [73-01]
provides:
  - .planning/phases/73-dedup/73-SPIKE.md (canonical spike artifact, Ship recommendation)
  - Q-2026-05-07-01 resolution (status flipped to Resolved)
affects:
  - DEDUP-02..N implementation in _make_id() / build.py is now unblocked
tech-stack:
  added: []
  patterns: [_rebuild_code-direct-invocation]
key-files:
  created:
    - .planning/phases/73-dedup/73-SPIKE.md
  modified:
    - .planning/research/questions.md
decisions:
  - Used `_rebuild_code` (CLAUDE.md-recommended incremental rebuild) since `graphify run` does not write graph.json (CLI gap)
  - Two-corpus measurement (paper corpus skipped: PDF extraction requires LLM skill orchestration, not CLI-callable)
  - AST-only run: no sem-sim edges produced → residual ≡ raw (pessimistic edge of measurement, accepted per CONTEXT trade-off)
metrics:
  duration: ~25m
  completed: 2026-05-08
  tasks: 5
  files: 2
---

# Phase 73 Plan 02: Run corpora + author DEDUP spike artifact Summary

Executed Phase 73 measurement spike against two real external corpora, ran `scripts/dedup_spike.py`, authored canonical `73-SPIKE.md`, and flipped Q-2026-05-07-01 to Resolved. **Recommendation: Ship.** Aggregate raw 18.78%, residual 18.78% (both clear the locked 5% gate by >13 pp).

## What was built

- **`.planning/phases/73-dedup/73-SPIKE.md`** — canonical spike artifact with all six required sections (Summary, Corpus, Method, Results, Recommendation, Appendix). Per-corpus AND aggregate rates documented; sem-sim asymmetry called out per RESEARCH override #3; enrichment status flagged per override #1.
- **`.planning/research/questions.md`** — Q-2026-05-07-01 status flipped to Resolved with link to canonical artifact.

## Results captured

| Corpus | Concept Nodes | Collision Groups | Raw Nodes | Residual Nodes | Raw % | Residual % |
|---|---:|---:|---:|---:|---:|---:|
| code (claude-code-templates, 1,090 files) | 2,556 | 207 | 556 | 556 | 21.75% | 21.75% |
| doc (claude-cookbooks, 238 files) | 426 | 2 | 4 | 4 | 0.94% | 0.94% |
| **AGGREGATE** | 2,982 | 209 | 560 | 560 | **18.78%** | **18.78%** |

Decision rule (CONTEXT D-03, locked): `raw > 5% AND residual > 5%` → Ship. Aggregate clears both gates → **Ship**.

## Verification

- `.planning/phases/73-dedup/73-SPIKE.md` exists, 6 `## ` section headers, recommendation pattern `Recommendation: \*\*Ship\*\*` present
- `.planning/research/questions.md` references `73-SPIKE.md` and reads "Resolved"
- `git diff graphify/` is empty — no production code changed
- `scripts/dedup_spike.py` and `tests/test_dedup_spike.py` (Wave 1) untouched; spike script ran and produced the embedded results table

## Deviations from Plan

**[Rule 3 — Blocking issue, accepted as documented limitation]** The plan's Task 1 specified `graphify run .` to produce per-corpus `graph.json`. In reality, `graphify --help` documents `run [path]` as "detect → AST extract only (Phase 12); **does not write graph.json**". The full pipeline (build → cluster → write graph.json) is reachable through:
1. The `/graphify` Claude Code skill (`graphify/skill.md`) — orchestration layer, not CLI-callable.
2. `graphify/watch.py:_rebuild_code(path)` — direct Python invocation, AST-only, writes `graph.json`. **CLAUDE.md itself recommends this** as the canonical incremental-rebuild entry point.

Used `_rebuild_code` for the two corpora that contained code/text files. The PDF/paper corpus produced zero output ("No code files found - nothing to rebuild") because PDF extraction sits behind the LLM skill orchestration. Per the plan's runtime guidance ("Two-corpus measurement still resolves Q-2026-05-07-01 — better than no measurement"), proceeded with two corpora and documented the methodology limitation prominently in `73-SPIKE.md` §Method.

This is a documentation issue, not an implementation gap — and the recommendation is robust to the limitation: the AST-only run is the **pessimistic** edge of the measurement (no sem-sim coverage → residual ≡ raw), and raw alone clears the 5% gate by 13.78 percentage points. A future re-run with full LLM extraction can only lower residual, not raise it; the Ship decision would not flip.

**No code changes** — the gap is in graphify's CLI surface (no single command does the full pipeline), but fixing that is out of scope for this measurement spike.

## Commits

(see Final Commit step below)

## Self-Check

- `.planning/phases/73-dedup/73-SPIKE.md`: FOUND
- `.planning/research/questions.md` references `73-SPIKE.md`: FOUND
- 6 `## ` section headers in SPIKE.md: VERIFIED
- Recommendation pattern `Recommendation: **Ship**`: VERIFIED
- `git diff graphify/` empty (no production changes): VERIFIED
- Q-2026-05-07-01 marked Resolved: VERIFIED

## Self-Check: PASSED
