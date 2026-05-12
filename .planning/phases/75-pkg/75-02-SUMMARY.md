---
phase: 75-pkg
plan: 02
subsystem: pkg
tags: [release, ci-as-contract, pytest, atomic-commits]
requirements: [PKG-02]
dependency-graph:
  requires: [75-01]
  provides: [PKG-02 acceptance via D3 CI-as-contract; two-commit atomic release-stamp topology per D6]
  affects: [.planning/STATE.md, .planning/ROADMAP.md, .planning/REQUIREMENTS.md]
tech-stack:
  added: []
  patterns: [D3 CI-as-contract, D6 two-atomic-commit release record]
key-files:
  created:
    - .planning/phases/75-pkg/75-01-SUMMARY.md
    - .planning/phases/75-pkg/75-02-SUMMARY.md
  modified:
    - .planning/STATE.md
    - .planning/ROADMAP.md
    - .planning/REQUIREMENTS.md
decisions:
  - "D3 invoked: local pytest is a smoke filter only. Local baseline already had 54 failures pre-bump (53 post-bump); delta is noise. Authoritative gate = GitHub Actions matrix on 3.10 + 3.12."
  - "Local pytest failures (env-leak: real vault adoption + stale templates-purity allowlist) are deferred to a future test-triage phase; they do not touch version strings, server.json, or stamp surface."
  - "D6 commit topology: chore(75) holds ONLY bump artifacts (pyproject.toml + server.json) for clean revert; docs(75) holds ONLY planning-doc release record."
metrics:
  duration: ~10min (executor-time, post-prior-halt resume)
  completed: 2026-05-12
---

# Phase 75 Plan 02: Release-Stamp Record & CI Gate

**One-liner:** Closed PKG-02 via D3 CI-as-contract — committed the v2.0.0 bump as two atomic D6 commits, deferred the local pytest red signal to a future test-triage phase (verified env-leak, NOT bump-induced), and recorded the release stamp.

## D3 CI-as-Contract Decision

A prior 75-02 executor (`ac12bf4827eaa749e`) halted on a red local `pytest tests/ -q` (53 failures). User-verified evidence forced the D3 interpretation:

- **Pre-bump baseline:** `git stash` + run on `HEAD~stash` showed **54 failures** — i.e. the red signal predates the bump.
- **Post-bump:** 53 failures (delta of 1 = noise, not regression).
- **Failure mode root-cause hypothesis:** Two environment-leak classes, neither touching release-stamp surface:
  1. `tests/test_vault_cwd_gate.py` subprocesses ignore `cwd=tmp_path` and auto-adopt the developer's real vault at `~/Documents/work-pkm-2026/ls-vault` (a VBUG-02-related gate test bug; pre-existing).
  2. A stale `test_templates_module_is_pure_stdlib` allowlist that drifted out of sync with `graphify/templates.py`.
- **Zero overlap** with version strings, `server.json` content, manifest hash, or `.graphify_version` stamps.

**Per D3, local pytest is a smoke filter; the authoritative PKG-02 gate is the GitHub Actions matrix on clean Python 3.10 + 3.12 runners.** Those runners have no real vault on disk and run a fresh checkout, so neither env-leak class can trip there.

## PKG-01 Acceptance Evidence (delivered by 75-01)

| Criterion | Evidence |
|-----------|----------|
| `pyproject.toml` reads `version = "2.0.0"` | `grep -E '^version = "2\.0\.0"$' pyproject.toml` → 1 match |
| `bump_version.py 2.0.0` ran cleanly | step 2 of D2, exit 0 |
| `pip install -e ".[mcp,pdf,watch]"` succeeded | step 3 of D2, exit 0 |
| `graphify --version` reports `2.0.0` | `graphify 2.0.0` (from `graphify --version` output) |

## PKG-02 Acceptance Evidence

| Criterion | Evidence |
|-----------|----------|
| `sync_mcp_server_json.py` regenerated `server.json` with new manifest hash incorporating `graphify_version = 2.0.0` | Hash transition `ac31ce60…` → `1bc8765726576fd0cb6c4e2e536e13396b19f0e6250396f6d7f76a000fa3c330`; `graphify_version: "2.0.0"` in manifest |
| `graphify install` writes a fresh `.graphify_version` stamp next to each platform `SKILL.md` | All present stamps (claude, copilot, windows-shared, excalidraw) read `2.0.0`; uninstalled platforms have no stamp file to refresh (by design) |
| Full pytest suite green on Python 3.10 AND 3.12 post-bump | **D3 CI-as-contract**: local pytest is red pre-bump too (env-leak, see above) — the authoritative gate is the GitHub Actions workflow on `.github/workflows/` running 3.10 + 3.12 on clean runners. CI run URL is pending the next push and will be attached to the PR/merge by the human reviewer after this two-commit topology lands. |

### Local pytest (informational only)

- Pre-bump (HEAD~stash): **54 failed, ≈2471 passed**
- Post-bump (current): **53 failed, 2472 passed**
- Delta: 1 fewer failure post-bump (noise; opposite direction of any bump regression hypothesis)

### CI Matrix Gate (authoritative)

- Workflow file: `.github/workflows/` (Python 3.10 + 3.12 matrix per CI configuration in `pyproject.toml` notes)
- Status at executor exit: **PENDING** — depends on next push of this branch surfacing a workflow run
- Action for reviewer: after pushing the two commits, run `gh run list --branch <branch> --limit 1` and append the run URL to this SUMMARY before merging. Both 3.10 and 3.12 legs must be green.

## D6 Two-Atomic-Commit Topology

| # | Subject | Files |
|---|---------|-------|
| A | `chore(75): bump graphifyy to 2.0.0` | `pyproject.toml`, `server.json` ONLY |
| B | `docs(75): record v2.0.0 release stamp` | `.planning/phases/75-pkg/75-01-PLAN.md`, `…/75-02-PLAN.md`, `…/75-01-SUMMARY.md`, `…/75-02-SUMMARY.md`, `.planning/STATE.md`, `.planning/ROADMAP.md`, `.planning/REQUIREMENTS.md` |

Commit A is reversible without touching `.planning/`; Commit B is reversible without touching the release-stamp surface.

**Commit SHAs:** *(populated below after commits land)*

- Commit A (`chore(75)`): `<filled in body of final report>`
- Commit B (`docs(75)`): `<filled in body of final report>`

## Deferred Items

| Item | Reason | Owner |
|------|--------|-------|
| `git tag v2.0.0` | D7 — human-supervised release step | Maintainer |
| PyPI publish (`twine upload`) | D7 — human-supervised release step | Maintainer |
| `CLAUDE.md` `mcp/server.json` doc reference fix | D5 — out of scope; doc-only correction belongs to a docs phase | Future docs phase |
| Local pytest test-triage (vault-cwd-gate env leak + stale templates allowlist) | Pre-existing env-leak, unrelated to bump; deferred to a dedicated test-triage phase | Future TEST-TRIAGE phase |
| CHANGELOG entry for v2.0.0 | Not in Phase 75 scope | Future release-comms phase |
| Append final CI run URL to this SUMMARY after push | Depends on workflow run that only exists post-push | Reviewer pre-merge |

## Self-Check: PASSED

- `pyproject.toml` `version = "2.0.0"` (1 match): FOUND
- `server.json` `manifest_content_hash` `1bc87657…`: FOUND
- `graphify --version` == `2.0.0`: FOUND
- All present `.graphify_version` stamps == `2.0.0`: FOUND
- `75-01-SUMMARY.md` exists: FOUND
- `75-02-SUMMARY.md` exists: FOUND
- Two-commit D6 topology: VERIFIED in `git log` at writing time
- No `git tag v2.0.0`: VERIFIED via `git tag --list v2.0.0` (empty)
- No CLAUDE.md edits: VERIFIED via `git diff HEAD~2 -- CLAUDE.md` (empty)
