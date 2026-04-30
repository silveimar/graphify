# Phase 45: Baselines & Detect Self-Ingestion - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-04-30
**Phase:** 45-Baselines & Detect Self-Ingestion
**Areas discussed:** Self-ingestion strategy, Dotfiles / `.graphify/` corpus policy, collect_files vs detect parity, Regression surface

---

## Self-ingestion strategy

| Option | Description | Selected |
|--------|-------------|----------|
| Silent manifest skips | Keep D-27 silent-only | |
| Stderr summary | One-line stderr when manifest skips fire + hint | ✓ |
| Doctor-only visibility | Silent detect; doctor exposes | |

| Option | Description | Selected |
|--------|-------------|----------|
| Nested pruning only when resolved is None | Manifest requires ResolvedOutput | |
| Also load manifest from default graphify-out | Stronger protection without profile | ✓ |

| Option | Description | Selected |
|--------|-------------|----------|
| Skip only under nuanced destination rules | | |
| Always skip any manifest-recorded path | Strong anti-self-ingestion | ✓ |
| TTL / max-runs emphasis only | | |

**User's choices:** Manifest skips surfaced via stderr summary; manifest participation even when `resolved` is None; always skip paths ever recorded in manifest.

**Notes:** Tradeoff accepted — repurposed folders may need manifest hygiene.

---

## Dotfiles / `.graphify/` corpus

**User's choice (free-form):** Root-level profile section for `.graphify` include/exclude; always exclude YAML profile and config files; update profile `.graphify` section after detect discovers new files; options for update vs ignore and auto-update profile.

| Option | Description | Selected |
|--------|-------------|----------|
| Detect semantics only; defer auto profile mutation | | |
| Phase 45 includes detect + profile persistence / sync | Full scope | ✓ |
| Hard exclude entire `.graphify/` | | |

---

## Path contract (HYG-02)

| Option | Description | Selected |
|--------|-------------|----------|
| Pathlib-only refactor | | |
| String invariant only | | |
| Dual pathlib + documented string contract | | ✓ |

---

## collect_files vs detect

| Option | Description | Selected |
|--------|-------------|----------|
| Shared corpus-eligibility primitive | Single source of truth | ✓ |
| Document divergence | | |
| Optional resolved on collect_files | | |

---

## Regression surface

| Option | Description | Selected |
|--------|-------------|----------|
| Heavy fixtures | | |
| tmp_path only | | |
| Hybrid fixture vault + tmp_path edge cases | | ✓ |

---

## Claude's Discretion

Exact manifest summary wording; profile schema field names; module split for shared walker; coherence with `_OUTPUT_MANIFEST_MAX_RUNS`.

## Deferred Ideas

Concept↔code MVP (**CCODE-***) deferred to later phases.
