---
phase: 12-heterogeneous-extraction-routing
plan: "04"
subsystem: audit
tags: [routing.json, ROUTE-05, atomic-write]

requires:
  - phase: 12-03
    provides: extract instrumentation points
provides:
  - RoutingAudit record/flush with versioned JSON and os.replace
affects: [extract, pipeline, security]

tech-stack:
  added: []
  patterns: ["atomic .tmp + os.replace under graphify-out"]

key-files:
  created: ["graphify/routing_audit.py", "tests/test_routing_sidecar.py"]
  modified: ["graphify/security.py", "graphify/extract.py"]

key-decisions:
  - "Paths validated via validate_graph_path where applicable (T-12-04)"

requirements-completed: [ROUTE-05]

duration: —
completed: 2026-04-17
---

# Phase 12 — Plan 04 Summary

**`RoutingAudit` writes `graphify-out/routing.json` with per-file class/model/endpoint/tokens/ms and atomic replace semantics.**

## Self-Check: PASSED

`pytest tests/test_routing_sidecar.py -q`; full suite `1257 passed`.
