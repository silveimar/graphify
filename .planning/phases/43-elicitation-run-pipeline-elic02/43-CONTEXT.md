# Phase 43: Elicitation ↔ run pipeline (ELIC-02) — Context

**Gathered:** 2026-04-30  
**Status:** Ready for planning  
**Kind:** Gap closure (from `.planning/v1.9-MILESTONE-AUDIT.md`)

## Problem

**ELIC-02** requires elicited extraction to reach **`build`** with validation. Library helpers and tests may merge elicitation; **`graphify run`** may not load **`elicitation.json`** into **`run_corpus`** by default — product intent must be explicit.

## Goal

Decide: (a) wire sidecar merge into the **`run`** pipeline, (b) document skill-only / manual merge, or (c) hybrid. Add **tests** and **docs** matching the decision so **ELIC-02** acceptance criteria are satisfied.

## Requirements

- **ELIC-02** (close audit “partial”)

## Depends on

- Phase 39 elicitation + sidecar layout (shipped or accepted baseline).
