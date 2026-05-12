---
phase: 75-pkg
plan: 01
subsystem: pkg
tags: [release, version-bump, mcp-manifest, skill-stamp]
requirements: [PKG-01]
dependency-graph:
  requires: [71, 72, 73, 74]
  provides: [coherent v2.0.0 release stamp surface]
  affects: [pyproject.toml, server.json, ~/.claude/skills/graphify/.graphify_version, ~/.copilot/skills/graphify/.graphify_version, ~/.claude/skills/excalidraw-diagram/.graphify_version]
tech-stack:
  added: []
  patterns: [D2 canonical bump dance, D4 strict per-platform stamp check]
key-files:
  created: []
  modified:
    - pyproject.toml
    - server.json
decisions:
  - "D4 option-(a) strict: structural stamp check asserts each installed `.graphify_version` reads exactly `2.0.0` (existence alone insufficient)."
  - "Only active/installed platform stamps were rewritten by `graphify install`; uninstalled platforms (codex, opencode, aider, claw, droid, trae, trae-cn, antigravity) have no stamp files and are not in scope."
metrics:
  duration: ~5min (executor-time)
  completed: 2026-05-12
---

# Phase 75 Plan 01: Bump Dance Summary

**One-liner:** Executed the D2 6-step bump dance — pyproject `1.0.0` → `2.0.0`, reinstall under `[mcp,pdf,watch]` extras, regenerated `server.json` via `sync_mcp_server_json.py`, refreshed `.graphify_version` stamps via `graphify install`, and confirmed `graphify --version` == `2.0.0`.

## Bump Dance Steps (D2)

| Step | Command | Exit | Notes |
|------|---------|------|-------|
| 1 (dry-run) | `python scripts/bump_version.py 2.0.0 --dry-run` | 0 | Diff confirmed `version = "1.0.0"` → `version = "2.0.0"`, no collateral. |
| 2 (mutate)  | `python scripts/bump_version.py 2.0.0`           | 0 | `pyproject.toml` rewritten; `grep -E '^version = "2\.0\.0"$'` matches once. |
| 3 (reinstall) | `pip install -e ".[mcp,pdf,watch]"`            | 0 | `importlib.metadata` refreshed; required before step 4 by design. |
| 4 (sync)    | `python scripts/sync_mcp_server_json.py`         | 0 | `server.json` regenerated at repo root (D5: NOT `mcp/server.json`). |
| 5 (install) | `graphify install`                               | 0 | Active platform stamps refreshed to `2.0.0`. |
| 6 (sanity)  | `graphify --version`                             | 0 | Prints `graphify 2.0.0`. |

## Manifest Hash (server.json)

| Field | Value |
|-------|-------|
| Pre-bump `manifest_content_hash` | `ac31ce60…` (per executor `ac12bf4827eaa749e` capture before mutation) |
| Post-bump `manifest_content_hash` | `1bc8765726576fd0cb6c4e2e536e13396b19f0e6250396f6d7f76a000fa3c330` |
| `graphify_version` in manifest | `"2.0.0"` |

## Platform `.graphify_version` Stamps (D4 strict)

Active install locations on this machine (others = not installed; no stamp to write):

| Platform | Path | Contents |
|----------|------|----------|
| claude | `~/.claude/skills/graphify/.graphify_version` | `2.0.0` |
| copilot | `~/.copilot/skills/graphify/.graphify_version` | `2.0.0` |
| windows | `~/.claude/skills/graphify/.graphify_version` (shared with claude) | `2.0.0` |
| excalidraw | `~/.claude/skills/excalidraw-diagram/.graphify_version` | `2.0.0` |

Uninstalled platforms (codex, opencode, aider, claw, droid, trae, trae-cn, antigravity): no stamp file present — by design these have no drift surface to refresh until a user installs them, at which point `graphify install` writes `2.0.0`.

**D4 strict check verdict:** PASS — every present stamp reads exactly `2.0.0`. No stale `1.0.0` stamp anywhere.

## Scope Guardrails Honored

- No `git tag v2.0.0` (D7 deferred to human-supervised release action).
- No PyPI publish (D7 deferred).
- No edits to `CLAUDE.md` `mcp/server.json` reference (D5 deferred).
- No hand-edits to `server.json` — produced solely by `sync_mcp_server_json.py`.
- No `git add -A`; commits in 75-02 stage by exact filename.

## Self-Check: PASSED

- `pyproject.toml` `version = "2.0.0"`: FOUND
- `server.json` `graphify_version: "2.0.0"`: FOUND
- `server.json` manifest hash `1bc87657…`: FOUND
- `graphify --version` output `2.0.0`: FOUND
- All present skill stamps == `2.0.0`: FOUND
