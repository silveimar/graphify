# Phase 74 — VBUG: Discussion Log

**Date**: 2026-05-08
**Mode**: discuss (default)

## Context
Debug session `.planning/debug/vault-cwd-gate-argparse-required.md` already locked the architectural decisions (fix approach, blast radius, RED tests). Discussion focused on the two remaining gray areas — test file location and test scope — that REQUIREMENTS.md VBUG-02 phrasing left open.

## Q&A

### Q1 — Test file location
**Options**: New tests/test_vault_cwd_gate.py (literal REQUIREMENTS) | Unskip + augment tests/test_vault_cwd.py | Both
**Selected**: Create new tests/test_vault_cwd_gate.py. Move the two existing RED tests from tests/test_vault_cwd.py:412-455 into it and unskip them.
**Rationale**: Honors REQUIREMENTS.md VBUG-02 file naming literally; groups all gate regression coverage in one module.

### Q2 — Test scope
**Options**: Only the 2 defective commands | All 15 gated subcommands | 2 + meta-test asserting no required=True
**Selected**: All 15 gated subcommands. Parametrized over the full enumeration from the debug session.
**Rationale**: Honors REQUIREMENTS.md VBUG-02 wording ("every gated subcommand") literally; defensive net catches future argparse-styled commands silently reintroducing the bug.

## Deferred Ideas Captured
- sys.argv injection approach (a) — rejected at diagnosis time
- Centralizing --vault declarations behind a helper — YAGNI for 2 sites
- Migrating 13 hand-rolled parsers to argparse — out of scope, would worsen exposure

## Claude's Discretion (not asked)
- Help-string wording suggestion (append " (optional when invoked from a vault CWD)")
- Friendly error wording suggestion ("error: --vault is required when not running from a vault directory")
- Parametrized test mechanism (subprocess.run, matching existing RED tests)
- Phase recommendation: invoke /gsd-plan-phase 74 with --skip-research since the debug session has already done the research work
