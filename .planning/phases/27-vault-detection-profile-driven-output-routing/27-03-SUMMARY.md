# Plan 27-03 Summary: CLI Wiring (`--output` flag + `resolve_output()` integration)

**Plan:** 27-03
**Status:** Complete
**Tasks:** 3/3
**Execution mode:** Inline (executor sub-agents blocked by Read hook on planning files)

## Files Modified

| File | Change |
|------|--------|
| `graphify/pipeline.py` | `run_corpus()` gained additive `out_dir: Path \| None = None` kwarg; `audit.flush(...)` now writes to `out_dir` instead of hardcoded `cwd / "graphify-out"` |
| `graphify/__main__.py` (run branch) | Parses `--output` / `--output=`; calls `resolve_output(Path.cwd(), cli_output=...)` once; forces input corpus = CWD on auto-adopt (D-07); threads `out_dir` through `run_corpus` |
| `graphify/__main__.py` (--obsidian branch) | Parses `--output` / `--output=`; tracks `user_passed_obsidian_dir` sentinel; calls `resolve_output()` once after flag-loop; applies D-08 precedence (`--output` > profile > `--obsidian-dir` > legacy default) |
| `tests/test_main_flags.py` (NEW) | 9 integration tests via `subprocess.run`, all confined to `tmp_path` |

## Commits

- `85a4f97` feat(27-03): wire --output flag + resolve_output() into run branch (Task 1)
- `d246fa0` feat(27-03): wire --output flag + resolve_output() into --obsidian branch (Task 2)
- `e97bbc8` test(27-03): add tests/test_main_flags.py with 9 integration tests (Task 3)

## Decisions Implemented

| Decision | Where |
|----------|-------|
| D-06 (auto-adopt in BOTH `run` AND `--obsidian`) | __main__.py both branches call resolve_output() |
| D-07 (auto-adopt → input corpus = CWD) | run branch: `if resolved.vault_detected and resolved.source == "profile": target = Path.cwd().resolve()` |
| D-08 (`--output` > `--obsidian-dir` > profile) | --obsidian branch precedence ladder; run branch (no `--out-dir` competitor) |
| D-09 (single-line stderr precedence message) | Emitted by `resolve_output()` once per invocation |
| D-10 (`--output` is literal CWD-relative or absolute) | No mode inference; user-typed value used as-is |
| D-11 (artifacts go sibling-of-vault when auto-adopt) | run branch uses `resolved.artifacts_dir` for `out_dir` |
| D-12 (no-vault default = byte-identical v1.0 paths) | `if resolved.source == "default":` branch reuses original `target / "graphify-out"` expression; legacy `--obsidian-dir` semantics preserved |

## Threats Mitigated (T-27-13 .. T-27-18)

| ID | Disposition | Evidence |
|----|-------------|----------|
| T-27-13 (path traversal in `--output`) | accept | D-10 user-responsibility |
| T-27-14 (`--output` leaking into `--dedup`/`approve`) | mitigate | `grep -A2 'cmd == "--dedup"' graphify/__main__.py \| grep -c '\-\-output'` returns 0 |
| T-27-15 (vault-detection report leaking into no-vault stderr) | mitigate | `test_run_no_vault_no_output_no_stderr_noise`, `test_obsidian_no_vault_no_output_no_stderr_noise` |
| T-27-16 (D-09 line printed twice) | mitigate | `test_run_output_flag_overrides_profile_emits_d09_line` asserts `count("overrides profile output") == 1` |
| T-27-17 (out_dir kwarg breaking callers) | mitigate | Default `None` preserves byte-identical behavior; full pre-existing suite green (1638 passed) |
| T-27-18 (auto-adopt forcing CWD ingestion) | accept | D-07 = SEED Option C contract; user opts in by creating profile |

## Test Coverage

- **Wave 1 (plans 27-01 + 27-02):** 179 passed, 1 xfailed
- **Plan 27-03:** +9 integration tests, all green
- **Full suite after this plan:** **1647 passed, 1 xfailed**, zero regressions

## Phase 27 Closure

All 3 plans now integrate:
- **27-01** ships the profile schema (`output:` block) + `validate_sibling_path()` in `graphify/profile.py`
- **27-02** ships `graphify/output.py` with `ResolvedOutput` NamedTuple, `is_obsidian_vault()`, and `resolve_output()` resolver
- **27-03** wires `resolve_output()` into the user-facing CLI in both `run` and `--obsidian` branches, plus integration tests

`ResolvedOutput` is now the v1.7 integration contract for:
- **Phase 28** (self-ingestion hardening): `detect.py` will consume `resolved.notes_dir` + `resolved.artifacts_dir` for pruning
- **Phase 29** (doctor + dry-run): the doctor command will surface the same `ResolvedOutput` shape in its diagnostic report

## Requirements Addressed

- **VAULT-08** ✅ — Vault detection reported in CLI output (single-line `[graphify] vault detected at <path> ...source=...` from `resolve_output()`, surfaced via both `run` and `--obsidian`)
- **VAULT-09** ✅ — Auto-adopt Option C in both branches; D-07 forces input=CWD; refusal cases (no profile, no `output:` block) covered
- **VAULT-10** ✅ — Profile `output:` schema (from 27-01) + CLI `--output` override + D-09 stderr precedence line, all wired

## Deviations from Plan

None. Plan executed verbatim except executed inline (no worktree subagent) due to Read hook interception.

## Pre-existing Test Issues (out of scope)

- `test_detect_skips_dotfiles`, `test_collect_files_from_dir` — already documented as deferred-items by plan 27-02; not introduced by this work.
