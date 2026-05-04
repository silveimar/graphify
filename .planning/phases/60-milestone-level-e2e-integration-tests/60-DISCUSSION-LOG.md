---
phase: 60
phase_name: Milestone-level E2E integration tests
date: 2026-05-03
mode: discuss (default)
---

# Phase 60 Discussion Log

Audit trail of the discuss-phase session that produced `60-CONTEXT.md`. Human reference only — downstream agents read CONTEXT.md, not this file.

## Domain framing

Phase 60 is pure test infrastructure closing two audit gaps from the v1.11 milestone audit:
- Flow 2: Phase 55 + Phase 56 composition (block expansion + override ladder) end-to-end via `graphify update-vault`.
- Flow 3: Phase 57 + Phase 56 pipeline (elicit sidecar → update-vault merge).

Requirements (E2E-01, E2E-02) were already locked in REQUIREMENTS.md and ROADMAP.md before discussion. Discussion focused only on HOW.

## Areas selected for discussion

User selected (multiSelect) ALL FOUR proposed gray areas:
1. Test file layout
2. Subprocess helper choice
3. Vault profile fixture strategy
4. Assertion granularity

## Area 1 — Test file layout

**Options presented:**
- (Recommended) One new file `tests/test_e2e_integration.py` containing both tests.
- Two files: `test_e2e_compose.py` + `test_e2e_elicit.py`.
- Extend the existing `tests/test_integration.py`.

**User chose:** One new file, both tests.

**Rationale:** Two tests don't justify two files of boilerplate. Extending `test_integration.py` would conflate Phase 5 in-process pipeline tests with subprocess-level E2E and grow an already-large file.

## Area 2 — Subprocess invocation helper

**Options presented:**
- (Recommended) Reuse `_graphify` from `tests/test_main_flags.py` (PYTHONPATH-wired).
- Reuse `_run_cli` from `tests/test_main_cli.py` (simpler, no PYTHONPATH).
- New shared helper in `tests/conftest.py`.

**User chose:** Reuse `_graphify` pattern.

**Rationale:** The PYTHONPATH wiring is critical because graphify is also developed under worktrees in this repo — without it the subprocess could silently exercise the *installed* graphify instead of local edits, masking regressions. Promoting to conftest.py is a separate hygiene concern, deferred.

## Area 3 — Vault profile fixture strategy

**Options presented:**
- (Recommended) Inline YAML strings written to tmp_path per-test.
- `tests/fixtures/vaults/` dir with reusable profile bundles.
- Hybrid: a `_make_vault(tmp_path, **overrides)` helper builds a baseline, tests patch in specifics.

**User chose:** Inline YAML in the test file.

**Rationale:** The two tests have diverging profile shapes (composition+override vs. elicit-aware), so reuse value is low. Inline keeps tests self-contained and readable top-to-bottom and avoids fixture drift from production default profile semantics.

## Area 4 — Assertion granularity

**Options presented:**
- (Recommended) Structured frontmatter parse + targeted body substrings.
- Substring/regex only.
- Full snapshot files.
- Folder-shape + frontmatter only.

**User chose:** Structured frontmatter parse + body substrings.

**Rationale:** Best fit between regression-catch strength and maintenance overhead. Frontmatter is the contract surface for ladder resolution; body substrings carry the elicitation-visibility signal that E2E-02 explicitly requires. Snapshots churn too aggressively; substring-only is too weak.

## Deferred ideas

- Promote `_graphify` helper to `tests/conftest.py` as a project-wide fixture (test-hygiene phase, future).
- Additional E2E flows beyond the two audit gaps (delta + write-back round-trip, etc.) — v1.13+.
- Snapshot-based regression suite for rendered-note shape — orthogonal investment.

## Claude's discretion (not surfaced as gray areas)

- Synthetic graph size: small (a few code/document nodes, 1–2 communities) — sufficient for pipeline plumbing checks.
- `subprocess.run(check=False)` + explicit `returncode == 0` assertions so failures surface captured stderr — standard repo idiom.
- Two subprocess calls in sequence for E2E-02 (`elicit` then `update-vault`), with an intermediate assertion that the sidecar exists.
