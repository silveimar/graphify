# Phase 42: Doctor profile preflight vs pinned vault — Context

**Gathered:** 2026-04-30  
**Status:** Ready for planning  
**Kind:** Gap closure (from `.planning/v1.9-MILESTONE-AUDIT.md`)

## Problem

`run_doctor()` derives `profile_home` from `resolved_output.vault_path` for locating `.graphify/profile.yaml`, but **`validate_profile_preflight`** is invoked with **`cwd_resolved`** instead of **`profile_home`**. Under **`--vault`** / **`GRAPHIFY_VAULT`** when CWD ≠ vault, profile validation can target the wrong tree — **VCLI-03** parity break.

## Goal

Run **`validate_profile_preflight(profile_home)`** (or equivalent) whenever profile files under **`profile_home`** trigger validation; preserve existing behavior when no pin.

## Requirements

- **VCLI-03** (complete parity for doctor + pins)

## Out of scope

- Changing resolver precedence (Phase 41 owns that).
