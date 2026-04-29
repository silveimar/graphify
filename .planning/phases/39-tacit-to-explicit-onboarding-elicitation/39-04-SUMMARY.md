---
phase: 39-tacit-to-explicit-onboarding-elicitation
plan: 04
subsystem: cli
tags: [cli, skill, resolve_output]

requires:
  - phase: 39-02
    provides: merge + artifacts paths
provides:
  - graphify elicit CLI and skill cross-links
affects: [39-05]

tech-stack:
  added: []
  patterns: [lazy imports in __main__; thin skill wrappers]

key-files:
  created: []
  modified:
    - graphify/__main__.py
    - tests/test_main_flags.py
    - graphify/skill.md
    - graphify/skill-codex.md
    - graphify/skill-opencode.md
    - graphify/skill-claw.md
    - graphify/skill-droid.md
    - graphify/skill-trae.md
    - graphify/skill-aider.md
    - graphify/skill-copilot.md
    - graphify/skill-windows.md

key-decisions:
  - "CLI uses resolve_output for artifacts_dir; --dry-run and --demo for onboarding UX."

requirements-completed: [ELIC-01, ELIC-02, ELIC-05, ELIC-06]

duration: 25min
completed: 2026-04-29
---

# Phase 39 Plan 04 Summary

**`graphify elicit` registered with onboarding help text; skills include empty/tiny corpus pointer to CLI and docs.**
