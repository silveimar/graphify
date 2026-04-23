---
phase: 12-heterogeneous-extraction-routing
plan: "06"
subsystem: cli
tags: [graphify run, --router, skill, ROUTE-03]

requires:
  - phase: 12-04
    provides: audit flush path
  - phase: 12-05
    provides: cost pre-flight
provides:
  - `graphify run [path] [--router]` and pipeline.run_corpus
  - Skill / CLAUDE.md router opt-in documentation
  - tests/test_cli_run.py, tests/test_route_requirements_smoke.py
affects: [users, agents]

tech-stack:
  added: []
  patterns: ["default run without --router does not construct Router (D-04)"]

key-files:
  created: ["graphify/pipeline.py", "tests/test_cli_run.py", "tests/test_route_requirements_smoke.py"]
  modified: ["graphify/__main__.py", "graphify/skill.md", "graphify/skill-codex.md", "CLAUDE.md"]

key-decisions:
  - "Thin wrapper: detect → extract(router?) → audit flush"

requirements-completed: [ROUTE-03]

duration: —
completed: 2026-04-17
---

# Phase 12 — Plan 06 Summary

**`graphify run` subcommand with optional `--router`, skill parity for router opt-in, and import-smoke tests for public routing symbols.**

## Self-Check: PASSED

`pytest tests/test_cli_run.py tests/test_route_requirements_smoke.py -q`; full suite `1257 passed`.
