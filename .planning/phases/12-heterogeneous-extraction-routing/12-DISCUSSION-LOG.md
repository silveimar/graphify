# Phase 12: Heterogeneous Extraction Routing - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in `12-CONTEXT.md`.

**Date:** 2026-04-17
**Phase:** 12 — Heterogeneous Extraction Routing
**Areas discussed:** Router ↔ batch extraction, Activation, Classification tunability, P2 scope, Audit sidecar

---

## Router ↔ Phase 10 batch extraction

| Option | Description | Selected |
|--------|-------------|----------|
| Max tier for cluster + per-file audit | One LLM call per cluster using max tier; routing.json records each file’s class |  |
| Router disables batch | Per-file only when `--router` |  |
| Split heterogeneous clusters | Separate calls when tiers differ |  |
| You decide | Builder picks default; user prioritizes correctness | ✓ |

**User's choice:** You decide — I care about correctness over cost.
**Resolution recorded in CONTEXT:** Max-tier cluster call + per-file `routing.json` rows (D-01–D-03).

---

## Activation & defaults

| Option | Description | Selected |
|--------|-------------|----------|
| Flag only | `graphify run --router` | ✓ |
| Flag + env | `--router` OR `GRAPHIFY_USE_ROUTER=1` |  |
| Default on if YAML exists |  |  |
| You decide | Minimal surprise |  |

**User's choice:** Flag only (opt-in `--router`).

---

## Classification tunability

| Option | Description | Selected |
|--------|-------------|----------|
| YAML-all | Thresholds in YAML; safe code defaults if missing | ✓ |
| Code defaults + YAML override |  |  |
| CLI flags for experiments |  |  |
| You decide | ROUTE-01 fidelity |  |

**User's choice:** Primarily YAML (`routing_models.yaml` / paired thresholds file).

---

## P2 scope (canary, cost ceiling, images)

| Option | Description | Selected |
|--------|-------------|----------|
| P1 core + promote ceiling | Defer some P2 |  |
| Strict REQ table | P2 later |  |
| Ship ROUTE-01–10 in Phase 12 | Full scope | ✓ |
| You decide | Smallest slice |  |

**User's choice:** Ship ROUTE-01 through ROUTE-10 in one Phase 12.

---

## routing.json audit trail

| Option | Description | Selected |
|--------|-------------|----------|
| Full per-file always |  |  |
| Full + cap opt-in |  |  |
| Privacy hash mode |  |  |
| You decide | Match dedup_report patterns | ✓ |

**User's choice:** You decide — match dedup sidecar patterns (atomic write, version, security-aligned).

---

## Claude's Discretion

- Batch integration details: max-tier aggregation, per-file audit rows.
- Audit: dedup-style `routing.json` + optional human-readable companion vs GRAPH_REPORT section.

## Deferred Ideas

None.
