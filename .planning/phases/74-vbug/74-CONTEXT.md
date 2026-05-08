# Phase 74 — VBUG: Phase Context

**Phase**: 74 (VBUG)
**Date**: 2026-05-08
**Milestone**: v2.0 — Graph Schema Deepening
**Status**: Context captured, ready for planning (research likely skippable)

<domain>
Fix the argparse `--vault required=True` exit-2 bug that fires from a vault CWD with no `--vault` flag, and lock it in with a regression test suite. The fix is two-line per command (flip `required=False`, lean on the existing post-parse auto-adopt guard). The regression suite covers every gated subcommand so any future argparse-styled `--vault` declaration is caught immediately. Resolves the `.planning/debug/vault-cwd-gate-argparse-required.md` debug session.
</domain>

<canonical_refs>
- `.planning/debug/vault-cwd-gate-argparse-required.md` — **MUST READ** — full diagnosis, blast-radius enumeration (15 gated branches, 2 defective), fix design tradeoff table, recommendation, RED tests location
- `.planning/REQUIREMENTS.md` — VBUG-01, VBUG-02 (test file name and "every gated subcommand" wording is locked here)
- `.planning/ROADMAP.md` — Phase 74 success criteria
- `graphify/__main__.py:3286-3312` — `update-vault` dispatch + argparse spec (defective site #1)
- `graphify/__main__.py:3344-3358` — `vault-promote` dispatch + argparse spec (defective site #2)
- `tests/test_vault_cwd.py:412-455` — existing RED tests `test_update_vault_auto_adopt_no_vault_flag` and `test_vault_promote_auto_adopt_no_vault_flag`, currently `@pytest.mark.skip` referencing this debug session
- `.planning/codebase/CONVENTIONS.md` — test naming pattern (`test_<module>.py`)
</canonical_refs>

<prior_decisions>
**From debug session (2026-05-04, status `diagnosed-pending-fix-phase`):**
- Fix approach (b) is locked: flip `required=False`, set `default=None`, lean on existing post-parse auto-adopt guard, add friendly error when neither auto-adopt fires nor `--vault` is supplied.
- Approach (a) (sys.argv injection) was rejected for medium regression risk and breaks-gate-separation reasons documented in the diagnosis tradeoff table.
- Blast radius = 2 commands only (`update-vault`, `vault-promote`). The other 13 gated dispatch branches use hand-rolled parsing and are unaffected.
- The existing post-parse guard `if gate == "auto-adopt" and not _uv_vault: _uv_vault = str(Path.cwd())` already exists in both branches — it is unreachable today because argparse exits first. Flipping `required=False` makes it reachable.

**From v2.0 milestone (memory S173):**
- v2.0 is "Graph Schema Deepening". This phase is a carry-over bug fix, not a v2.0-themed change. Treat as quality work, not feature scope.
</prior_decisions>

<decisions>

### Test file location — Create new `tests/test_vault_cwd_gate.py`
- **What**: A new test module dedicated to the gate behavior, named exactly as REQUIREMENTS.md VBUG-02 specifies.
- **Migration**: The two existing RED tests in `tests/test_vault_cwd.py:412-455` (`test_update_vault_auto_adopt_no_vault_flag`, `test_vault_promote_auto_adopt_no_vault_flag`) should be **moved** into the new file (not duplicated) and **unskipped** as part of the fix. This avoids two test files exercising the same gate behavior.
- **Why**: REQUIREMENTS.md VBUG-02 names the file literally. Honoring it cleanly resolves the requirement and groups all gate-related regression coverage in one place.
- **Researcher/planner task**: Confirm the move target file does not yet exist and that the two RED tests are the only gate-relevant tests in `tests/test_vault_cwd.py` — if other tests in that file touch the gate, decide whether to move them too or leave them.

### Test scope — All 15 gated subcommands
- **What**: `tests/test_vault_cwd_gate.py` exercises **every** gated dispatch branch from a fixture vault CWD without `--vault`, asserting:
  1. No argparse exit-2 occurs
  2. Auto-adopt notice is printed to stderr
  3. The command either succeeds or fails with a non-argparse-related error (some commands may legitimately fail for unrelated reasons in the fixture environment — those failures are acceptable as long as the failure mode is not "argparse: --vault required")
- **The 15 branches** (from debug session enumeration): `update-vault`, `vault-promote`, `--obsidian`, `--diagram-seeds`, `--init-diagram-templates`, `--dedup`, `snapshot`, `approve`, `save-result`, `elicit`, `harness`, `import-harness`, `enrich`, `run`, plus the inline gate at ~line 2947.
- **Why**: REQUIREMENTS.md VBUG-02 says "every gated subcommand". Defensive net catches a future argparse command silently reintroducing the bug — exactly the failure mode the diagnosis flagged in the "Forward compatibility" row.
- **Implementation note**: Use a parametrized pytest fixture (`@pytest.mark.parametrize`) over the 15 commands. Each parameter case asserts the three properties above. The fixture creates a minimal vault structure at `tmp_path` and chdir's into it. Subprocess invocation pattern can mirror the two existing RED tests.
- **Acceptance**: 15 parametrized cases all green on Python 3.10 and 3.12.

### Fix mechanics — Locked from debug session
- `graphify/__main__.py:3312` — change `_p_uv.add_argument("--vault", required=True, ...)` to `_p_uv.add_argument("--vault", required=False, default=None, ...)`. Update help string to note "omit when running from vault CWD".
- `graphify/__main__.py:3358` — same change for `_p_vp.add_argument("--vault", ...)` in `vault-promote`.
- After argparse, in both dispatch branches, the existing post-parse guard becomes reachable. Tighten it: if `gate != "auto-adopt"` and `opts.vault is None`, emit a user-friendly stderr error and exit 2 explicitly (so the help text contract is preserved — `--vault` is still effectively required when not in a vault CWD).

### Debug session resolution
- Once the fix lands and tests are green, flip `.planning/debug/vault-cwd-gate-argparse-required.md` frontmatter:
  - `status: diagnosed-pending-fix-phase` → `status: resolved`
  - Add `resolved_in: phase-74-vbug` (or equivalent reference)
  - Update `updated:` to today's date
- This satisfies VBUG-02's "the debug session's status field flips from `diagnosed-pending-fix-phase` to `resolved` with the fix-phase reference recorded".

</decisions>

<deferred>
- **Refactoring the gate to inject `sys.argv`** — approach (a) in the debug session, evaluated and rejected. Don't reopen.
- **Centralizing all `--vault` argument declarations behind a shared helper** — possible cleanup if more argparse-styled `--vault` flags are ever added, but YAGNI for two sites. Capture as backlog only if a third site emerges.
- **Migrating the other 13 hand-rolled `--vault` parsers to argparse** — out of scope and arguably worse (would re-introduce the same bug pattern across more sites).
</deferred>

<code_context>
- **`_check_vault_cwd_gate`** (`graphify/__main__.py:3286`): pre-parse function that detects vault-shaped CWD and prints auto-adopt breadcrumb to stderr. Returns a routing signal but does NOT mutate `sys.argv`. Behavior preserved by approach (b).
- **The 13 hand-rolled gated commands**: read `--vault` from `sys.argv` manually after the gate runs and honor the post-parse `if gate == "auto-adopt"` guard naturally. They are NOT defective and require NO code change. Tests for them in `test_vault_cwd_gate.py` are pure regression coverage, not fix verification.
- **Test pattern reference** (`tests/test_vault_cwd.py:412-455`): subprocess invocation with `cwd=tmp_path/vault_dir`, asserts on `result.returncode != 2` and `b"auto-adopt" in result.stderr` (or similar). Use this pattern verbatim for the 15-case parametrize.
- **CI matrix**: tests run on Python 3.10 and 3.12 (per `pyproject.toml`). Both must pass.
</code_context>

<open_questions_for_research>
- Confirm whether `tests/test_vault_cwd.py` contains gate-related tests beyond the two RED ones (`L412-455`). If yes, propose whether to move them too or leave them.
- Confirm exact help-string update for `--vault` (suggested: append " (optional when invoked from a vault CWD)" to existing help text, both sites identical).
- Confirm the friendly error message wording for the `gate != "auto-adopt" and opts.vault is None` case (suggested: `"error: --vault is required when not running from a vault directory"`). The exact string should match argparse's stylistic conventions for consistency.
- Confirm whether the parametrized 15-command test should use `subprocess.run` (slow but accurate) or in-process invocation via the CLI entry point (fast but bypasses argparse-exit machinery). The existing two RED tests use subprocess — recommend matching that for consistency.
</open_questions_for_research>

<next_steps>
- This phase may be a candidate for `--skip-research` since the debug session has done the research already. Recommended invocation:
  - `/gsd-plan-phase 74 --auto --chain --skip-research`
- If the planner asks the four open questions above, that's fine — they're mechanical confirmations.
</next_steps>
