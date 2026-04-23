# Phase 20: Diagram Seed Engine - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-04-23
**Phase:** 20-diagram-seed-engine
**Areas discussed:** Re-run behavior for seeds/, Auto vs user seed overlap, Layout heuristic precedence, suggested_template pre-Phase-21, Manifest schema, max_seeds cap surfacing, Tag write-back trigger

---

## Gray Area Selection

| Option | Description | Selected |
|--------|-------------|----------|
| Re-run behavior for seeds/ | How to handle an existing seeds/ dir on re-run | ✓ |
| Auto vs user seed overlap | What to emit when a node is both auto and user | ✓ |
| Layout heuristic precedence | Priority when multiple SEED-07 rules match | ✓ |
| suggested_template pre-Phase-21 | What template string to emit before profile support | ✓ |

**User's choice:** All four selected.

---

## Re-run Behavior for seeds/

| Option | Description | Selected |
|--------|-------------|----------|
| Clear-then-write | Delete *-seed.json at start, write fresh | |
| Overwrite by filename only | Keep existing files, overwrite matches only | |
| Fail-if-dirty + --force | Refuse to proceed unless --force | |

**User's choice:** Free-text — "use an atomic write + manifest pattern" (Phase 19 parity).
**Notes:** This became D-01/D-02/D-03: atomic tempfile+rename for every seed, `seeds-manifest.json` written last, old manifest drives deterministic stale-file cleanup.

---

## Auto vs User Seed Overlap

| Option | Description | Selected |
|--------|-------------|----------|
| One seed, trigger='user' wins (Recommended) | User intent overrides auto; user layout_hint; doesn't count vs cap | ✓ |
| One seed, trigger='auto' wins | Auto canonical; counts vs cap; loses user hint | |
| Two distinct seeds | Emit both; rely on dedup to merge | |

**User's choice:** One seed, trigger='user' wins.
**Notes:** Captured as D-04.

---

## Layout Heuristic Precedence

| Option | Description | Selected |
|--------|-------------|----------|
| Specific-first ordering (Recommended) | tree → DAG-workflow → architecture → mind-map → repo-components → glossary-graph | ✓ |
| Generic-first ordering | architecture → workflow → repo-components → mind-map → tree → glossary-graph | |
| Short-circuit on SEED-07 listing order | Exact order as declared in REQUIREMENTS.md | |

**User's choice:** Specific-first ordering.
**Notes:** Captured as D-05. User `gen-diagram-seed/<type>` slash-hint bypasses the heuristic entirely.

---

## suggested_template Pre-Phase-21

| Option | Description | Selected |
|--------|-------------|----------|
| Built-in fallback keyed by layout_type (Recommended) | Hard-coded map; Phase 21 layers profile lookup in front | ✓ |
| Null until Phase 21 | Emit null; consumers handle | |
| Placeholder string | 'TBD-<layout_type>' sentinel | |

**User's choice:** Built-in fallback keyed by layout_type.
**Notes:** Captured as D-06. 6 built-in filenames map 1:1 to the 6 layout types Phase 21 will register as profile defaults.

---

## Manifest Schema

| Option | Description | Selected |
|--------|-------------|----------|
| Decisions + cleanup source-of-truth (Recommended) | Full entries incl. dedup sources + drop reasons; drives cleanup | ✓ |
| Decisions only; no cleanup | Observability only; stale files accumulate | |
| Cleanup only; no decision table | File list only; loses audit trail | |

**User's choice:** Decisions + cleanup source-of-truth.
**Notes:** Captured as D-02/D-03.

---

## max_seeds Cap Surfacing

| Option | Description | Selected |
|--------|-------------|----------|
| seeds-manifest.json + stderr warning (Recommended) | Manifest records drops; single stderr line fires | ✓ |
| Separate seeds-log.md journal | Phase-19-style markdown log | |
| Silent drop, manifest only | No stderr | |

**User's choice:** Manifest + stderr warning.
**Notes:** Captured as D-07.

---

## Tag Write-Back Trigger

| Option | Description | Selected |
|--------|-------------|----------|
| Only when --vault is passed (Recommended) | Opt-in mutation; mirrors vault-promote --vault | ✓ |
| Always, reads vault path from profile | Automatic on any analyze; risk of surprise mutation | |
| Separate subcommand | Extract into its own command | |

**User's choice:** Only when --vault is passed.
**Notes:** Captured as D-08.

---

## Claude's Discretion

- Empty-state behavior (no auto/user seeds)
- `seed_id` format for singletons vs union-merged seeds
- Whether AMBIGUOUS-confidence edges appear in seed `relations`

## Deferred Ideas

- Multi-seed diagrams (v1.6+)
- SEED-001 Tacit Elicitation Engine (v1.6)
- `create-master-keys-work-vault.md` todo — matched on keywords, already completed 2026-04-22, not Phase 20 scope
