# Phase 75 PKG — Discussion Log

**Date:** 2026-05-08
**Mode:** `--auto` (autonomous single-pass)

## Gray Areas Auto-Selected
All identified gray areas were auto-selected per `--auto` mode:
1. Pre-bump dependency gate
2. Bump dance ordering
3. Test matrix coverage
4. Skill-stamp drift verification
5. `server.json` location discrepancy
6. Commit topology
7. Tag / PyPI publish scope

## Decisions (recommended-default selections)

| # | Question | Selected | Rationale |
|---|----------|----------|-----------|
| D1 | Should bump proceed before phases 71–74 are all Complete? | No — hard gate | Shipping 2.0.0 with milestone work in flight produces an incoherent release |
| D2 | What ordering for bump → install → sync → stamp → test? | Locked 7-step canonical from CLAUDE.md | `sync_mcp_server_json.py` reads importlib.metadata; reinstall must precede sync |
| D3 | Run both Python 3.10 and 3.12 locally? | No — CI is the contract; local single-version smoke only | Avoids ergonomic noise; CI matrix is authoritative |
| D4 | Verify .graphify_version stamps by existence or by content? | By content (must read `2.0.0`) | Per CLAUDE.md, missing stamp suppresses drift warnings — partial install would silently leave 1.0.0 |
| D5 | `mcp/server.json` (CLAUDE.md) vs `server.json` (script reality)? | Trust the script (`server.json` at root); defer CLAUDE.md fix | Phase 75 is release-eng; doc prose fix expands change footprint |
| D6 | Single commit or split chore/docs? | Two atomic commits (chore bump + docs phase artifacts) | Bump commit must be reversible without touching planning docs |
| D7 | Include git tag + PyPI publish? | Out of scope for Phase 75 | No existing publish automation; tagging is human-supervised |

## Deferred Ideas
- Doc fix: `mcp/server.json` → `server.json` correction in CLAUDE.md
- Future: `make release` target bundling the canonical bump dance with built-in gates
- Future: CHANGELOG.md adoption (separate phase)
- Future: git tag `v2.0.0` + PyPI publish (manual after Phase 75 lands)

## Scope Creep Redirected
None — phase scope was already tight (pure release-engineering).

## Notes
- Roadmap shows Phase 71 at 4/5 In Progress at context-capture time; D1 makes closing 71-05 a precondition.
- Phase 74 was just completed (commit `f1c2470`); roadmap status row may need a manual sync to "Complete" before D1's gate passes cleanly.
