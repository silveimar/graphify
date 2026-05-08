# Phase 75: PKG — Context

**Date:** 2026-05-08
**Mode:** `--auto` (single-pass autonomous discuss)
**Goal (from ROADMAP.md):** graphifyy 2.0.0 ships with a coherent version stamp across pyproject.toml, server.json, and all platform SKILL.md files, with the full test suite green on Python 3.10 and 3.12.

<domain>
This phase delivers a coordinated v2.0.0 release stamp: bump the package, regenerate the MCP `server.json` manifest (with `graphify_version`-bearing `_meta.manifest_content_hash`), refresh the per-platform `.graphify_version` install stamps, and prove no regressions across the supported Python matrix. Pure release-engineering — no schema or feature work.
</domain>

<canonical_refs>
- `CLAUDE.md` — "Build & Test Commands" → canonical bump dance and skill-install-stamp behavior
- `pyproject.toml` — current `version = "1.0.0"`, PyPI name `graphifyy`, optional extras `[mcp,pdf,watch,all,...]`
- `server.json` (repo root, **not** `mcp/server.json` — see decision D5) — MCP manifest the sync script rewrites
- `scripts/bump_version.py` — strict `X.Y.Z` regex, supports `--dry-run`
- `scripts/sync_mcp_server_json.py` — reads `importlib.metadata.version("graphifyy")`; exits non-zero if installed != pyproject (so reinstall MUST precede sync)
- `graphify/__main__.py` — `_PLATFORM_CONFIG` (7 platforms) and `install` command that writes `.graphify_version` stamps
- `.planning/ROADMAP.md` — Phase 75 sits last; depends on 71/72/73/74
- `.planning/REQUIREMENTS.md` — PKG-01, PKG-02 (verbatim acceptance text below)
</canonical_refs>

<locked_requirements>
**PKG-01:** `pyproject.toml` `version = "2.0.0"`; `python scripts/bump_version.py 2.0.0` runs cleanly; `pip install -e ".[mcp,pdf,watch]"` reinstalls without error; `graphify --version` reports `2.0.0`.

**PKG-02:** `python scripts/sync_mcp_server_json.py` regenerates `server.json` with the new manifest hash incorporating `graphify_version = 2.0.0`; `graphify install` writes a fresh `.graphify_version` stamp next to each platform `SKILL.md`; full pytest suite green on Python 3.10 AND 3.12 post-bump.
</locked_requirements>

<prior_decisions>
- **From Phase 65 (CCONF) and Phase 71 (TEMP):** Schema-version pattern is established; legacy graph.json files must load without error after schema additions. Phase 75 inherits the assumption that all schema work is finalized before the version stamp is changed.
- **From CLAUDE.md (project-level):** Bump dance is fixed → `bump_version.py` → reinstall → `sync_mcp_server_json.py` → `pytest`. `graphify install` writes `.graphify_version` stamps; absence of stamp suppresses drift warnings (must run `install` to create/refresh).
- **From REQUIREMENTS.md (deferred):** OB1-RECIPE, MCP-ALIGN, DEDUP-02 are explicitly deferred from v2.0 — do not pull into Phase 75.
</prior_decisions>

<decisions>

### D1 — Pre-bump dependency gate (HARD precondition)

The bump MUST NOT proceed until Phases 71, 72, 73, 74 are all marked **Complete** in `.planning/ROADMAP.md` AND `.planning/STATE.md`. Per current state at context capture time:
- 71 TEMP: 4/5 In Progress — **must close 71-05 before Phase 75 runs**
- 72 REAS: ✅ Complete (2026-05-08)
- 73 DEDUP: ✅ Complete (2026-05-08)
- 74 VBUG: ✅ Complete (committed `f1c2470 docs(74): complete phase`) — verify status row updated in roadmap

**Planner action:** First plan/task in Phase 75 is a verification gate that reads the roadmap status table and aborts if any of {71,72,73,74} is not Complete. No version-bump work begins until the gate passes.

**Why:** Shipping `2.0.0` while a milestone phase is mid-flight produces an incoherent release; the v2.0 schema changes (Phases 71/72) and bug fixes (74) ARE the value of the bump.

### D2 — Bump dance ordering (LOCKED — canonical from CLAUDE.md)

Single linear sequence, no parallelization, fail-fast on any non-zero exit:

1. `python scripts/bump_version.py 2.0.0 --dry-run` (preview the diff before mutating files)
2. `python scripts/bump_version.py 2.0.0` (writes `pyproject.toml`)
3. `pip install -e ".[mcp,pdf,watch]"` (matches CI extras; refreshes `importlib.metadata`)
4. `python scripts/sync_mcp_server_json.py` (rewrites `server.json` + manifest hash; exits non-zero if step 3 was skipped)
5. `graphify install` (refreshes `.graphify_version` stamps for all 7 platforms)
6. `graphify --version` → must print `2.0.0` (sanity check before tests)
7. `pytest tests/ -q` (full sweep)

**Why:** `sync_mcp_server_json.py` reads the *installed* version via `importlib.metadata`, not the file. Reinstall must happen between bump and sync or step 4 fails by design.

### D3 — Test matrix coverage strategy

- **Locally:** Run `pytest tests/ -q` on whichever Python is the developer's default (3.10 or 3.12). Do NOT block on locally executing both interpreters.
- **CI:** GitHub Actions matrix on Python 3.10 and 3.12 is the authoritative gate for PKG-02's "green on Python 3.10 AND 3.12" clause. The phase is not Complete until CI is green on both, captured by linking the green workflow run in the phase summary.
- **Smoke check:** After `graphify install`, pick one platform (Claude Code) and verify the `.graphify_version` file content reads `2.0.0` — guards against the drift-stamp behavior described in CLAUDE.md.

**Why:** Both interpreters locally is ergonomic noise; CI is the contract. But a green local single-version run is a useful pre-CI smoke filter.

### D4 — Skill-stamp drift verification

After `graphify install`, perform a structural assertion (not just file existence): for each of the 7 platform SKILL.md locations from `_PLATFORM_CONFIG`, the sibling `.graphify_version` reads exactly `2.0.0`. This is the only way to catch a partial install bug that silently leaves stamps at `1.0.0` (which would *suppress* drift warnings in field, per CLAUDE.md's "missing stamp = no warning" semantics).

### D5 — `server.json` location is repo-root, NOT `mcp/server.json`

CLAUDE.md and parts of project docs reference `mcp/server.json`, but `scripts/sync_mcp_server_json.py` writes `_REPO_ROOT / "server.json"` and only that path exists. The bump uses the script's actual target (`server.json` at repo root). The CLAUDE.md path reference is a documentation drift to be fixed in a follow-up doc-update phase, NOT in Phase 75.

**Why:** Phase 75 is release-engineering; correcting prose in CLAUDE.md is out of scope and would expand the change footprint of a release commit. Capture as deferred.

### D6 — Commit topology

Two atomic commits, in order:

1. `chore(75): bump graphifyy to 2.0.0` — `pyproject.toml`, `server.json`, regenerated `.graphify_version` stamps (whichever live in-repo per platform-install convention).
2. `docs(75): record v2.0.0 release stamp` — Phase 75 SUMMARY artifacts under `.planning/phases/75-pkg/`.

No squashing. The bump commit must be reversible without touching planning docs.

### D7 — Tag/PyPI publish scope

**OUT OF SCOPE for Phase 75:** Creating a git tag `v2.0.0` and publishing to PyPI. The phase delivers an in-repo release-stamp coherent state and a green test matrix. Tagging and PyPI release are deliberate human-supervised actions (matches existing project convention — no PyPI-publish automation exists).

</decisions>

<deferred>
- **Doc-update follow-up:** Correct `mcp/server.json` references in CLAUDE.md to `server.json` (D5).
- **Release automation:** A future phase could add a `make release` target that bundles the bump dance into a single command with built-in verification of the dependency gate and skill-stamp checks (D4). Not required for v2.0.
- **CHANGELOG.md:** Project does not currently maintain one; pulling that in alongside a version bump would expand scope. Defer unless a separate phase requests it.
- **PyPI publish + git tag:** Per D7, manual human-supervised action after Phase 75 lands.
- **OB1-RECIPE-01..04, MCP-ALIGN-01..02, DEDUP-02..N** — already explicitly deferred in REQUIREMENTS.md "Future Requirements".
</deferred>

<code_context>
- **Reusable assets:**
  - `scripts/bump_version.py` — handles regex-strict X.Y.Z, idempotent `--dry-run` preview, no extra logic needed in plan
  - `scripts/sync_mcp_server_json.py` — already enforces "reinstall before sync" via `importlib.metadata` check; planner can rely on its non-zero exit as a built-in gate
  - `graphify install` (in `__main__.py`) — already iterates `_PLATFORM_CONFIG` and writes `.graphify_version`; nothing to extend
- **No new code expected** for Phase 75. If planning surfaces a need for new code, that's a signal something is wrong (likely a missing test, not a missing feature).
</code_context>

<scope_guardrails>
**Phase 75 is allowed to:**
- Edit `pyproject.toml` (version line)
- Edit `server.json` (via the sync script only; no hand-edits)
- Refresh `.graphify_version` stamps via `graphify install` only
- Add or fix tests if the bump exposes a regression in 71/72 schema work — but those fixes get committed as a Phase 75 follow-up plan AND a note that the originating phase had insufficient coverage

**Phase 75 is NOT allowed to:**
- Add features, change schemas, or modify extraction/build logic
- Edit CLAUDE.md (deferred per D5)
- Tag or publish to PyPI (deferred per D7)
- Touch any phase artifacts under `.planning/phases/71..74/`
</scope_guardrails>

<auto_log>
[--auto] Selected all gray areas: dependency-gate, bump-ordering, test-matrix, skill-stamp-verification, server-json-location, commit-topology, tag-publish-scope.
[auto] D1 — recommended default: hard pre-bump gate on phases 71/72/73/74 Complete.
[auto] D2 — recommended default: locked 7-step canonical bump dance from CLAUDE.md.
[auto] D3 — recommended default: local single-Python smoke + CI matrix as authoritative gate.
[auto] D4 — recommended default: structural .graphify_version content check, not just existence.
[auto] D5 — recommended default: trust script's actual path (server.json at root); defer CLAUDE.md fix.
[auto] D6 — recommended default: two atomic commits (chore + docs), no squash.
[auto] D7 — recommended default: out-of-scope tag/publish; humans drive release.
</auto_log>
