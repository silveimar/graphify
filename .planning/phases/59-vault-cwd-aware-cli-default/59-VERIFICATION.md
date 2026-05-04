---
phase: 59-vault-cwd-aware-cli-default
verified: 2026-05-04T18:18:48Z
status: passed
score: 5/5 must-haves verified
overrides_applied: 0
---

# Phase 59: Vault-CWD-aware CLI default — Verification Report

**Phase Goal:** When `graphify` is invoked from inside an Obsidian vault directory, the CLI detects the vault automatically, auto-routes output when a profile exists, refuses with an actionable error when no profile exists, provides an opt-in `--write-into-vault` escape hatch, and `graphify doctor` reports the predicted behavior.
**Verified:** 2026-05-04T18:18:48Z
**Status:** passed
**Re-verification:** No — initial verification

---

## Goal Achievement

### Observable Truths

| #  | Truth                                                                                                                  | Status     | Evidence                                                                                                                                           |
|----|------------------------------------------------------------------------------------------------------------------------|------------|----------------------------------------------------------------------------------------------------------------------------------------------------|
| 1  | CWD `.obsidian/` detection triggers before pipeline dispatch in 14 gated commands; read-only commands unaffected       | VERIFIED   | `_check_vault_cwd_gate()` called from exactly 14 dispatch branches (lines 1818,1960,2021,2077,2217,2346,2630,2675,2773,2844,2946,3051,3285,3343)   |
| 2  | CWD vault + profile + no flags → output auto-routes via `_resolve_output_target()` identically to `--vault $CWD`      | VERIFIED   | `gate == "auto-adopt"` sets `lv_vault = Path.cwd()` flowing into `_resolve_cli_paths(local_explicit=lv_vault)`; `test_auto_adopt_matches_explicit_vault` passes |
| 3  | CWD vault + no profile + no flags → exit 2 with two-line `[graphify] error:` / `  hint:` via `_emit_vault_error()`    | VERIFIED   | `raise _emit_vault_error(..., code=2)` with em-dash U+2014 in message; `test_vcwd03_refusal_exit_code` and `test_vcwd03_refusal_verbatim_text` pass |
| 4  | `--write-into-vault` (global + per-command) suppresses VCWD-03 refusal; silent precedence vs `--vault`/`--output`     | VERIFIED   | `_pop_global_write_into_vault` + `_strip_write_into_vault_from_tokens` wired in all 14 gated branches; suppresses refusal only (after `has_profile` check) |
| 5  | `graphify doctor` `[vault-cwd]` section reports auto-adopt / refuse / n/a; parity tested against runtime              | VERIFIED   | `_classify_vault_cwd()` + `format_report()` emit `[vault-cwd]` lines; `test_doctor_runtime_parity` and `test_doctor_three_outcomes` pass           |

**Score:** 5/5 truths verified

---

## Required Artifacts

| Artifact                              | Expected                                       | Status     | Details                                                                            |
|---------------------------------------|------------------------------------------------|------------|------------------------------------------------------------------------------------|
| `graphify/__main__.py`                | Gate helper + 14 wired dispatch branches       | VERIFIED   | `_check_vault_cwd_gate()` at line 1516; 14 call sites confirmed                   |
| `graphify/__main__.py`                | `_pop_global_write_into_vault()` global flag   | VERIFIED   | Lines 1420-1429; stripped from `sys.argv` before dispatch at line 1567             |
| `graphify/__main__.py`                | `_strip_write_into_vault_from_tokens()` per-cmd| VERIFIED   | Lines 1460-1471; called in every gated branch                                      |
| `graphify/doctor.py`                  | `_classify_vault_cwd()` pure classifier        | VERIFIED   | Lines 517-544; mirrors gate predicates for parity                                  |
| `graphify/doctor.py`                  | `[vault-cwd]` section in `format_report()`     | VERIFIED   | Lines 610-628; unconditional, three outcomes                                       |
| `tests/test_vault_cwd.py`             | 16 tests covering VCWD-01..05                  | VERIFIED   | 401 lines, 16 tests, all pass (3.76s)                                              |

---

## Key Link Verification

| From                                   | To                                              | Via                                          | Status     | Details                                                              |
|----------------------------------------|-------------------------------------------------|----------------------------------------------|------------|----------------------------------------------------------------------|
| 14 gated dispatch branches             | `_check_vault_cwd_gate()`                       | direct call                                  | WIRED      | All 14 branches confirmed at grep                                    |
| `_check_vault_cwd_gate()` auto-adopt   | `_resolve_cli_paths()` with `local_explicit=cwd`| `lv_vault = Path.cwd()` set on gate result   | WIRED      | `run` branch line 2954; pattern consistent across all 14 branches    |
| `_check_vault_cwd_gate()` refuse       | `_emit_vault_error(..., code=2)`                | `raise _emit_vault_error()`                  | WIRED      | Line 1557-1561; em-dash U+2014 present; exit 2 confirmed             |
| Global `--write-into-vault`            | `_pop_global_write_into_vault(sys.argv)`        | stripped before dispatch at line 1567        | WIRED      | `g_write_into_vault` flows into every gate call site                 |
| Per-cmd `--write-into-vault`           | `_strip_write_into_vault_from_tokens(sys.argv[2:])` | called in all 14 gated branches          | WIRED      | `lv_write_into_vault or g_write_into_vault` union in gate call       |
| `doctor` dispatch                      | `report.has_explicit_route = _had_pin`          | post `run_doctor()` assignment (line 3279)   | WIRED      | `_classify_vault_cwd` receives correct `has_explicit_route` value    |

---

## Decision Fidelity

### D-1: Detection scope — 14 gated commands, 8 read-only commands unaffected

Gated commands confirmed by grep: `run`, `update-vault`, `enrich`, `--obsidian`, `vault-promote`, `import-harness`, `save-result`, `--diagram-seeds`, `--init-diagram-templates`, `--dedup`, `snapshot`, `approve`, `elicit`, `harness` — exactly 14.

`capability`, `query`, `doctor`, `install`, `hook`, `benchmark`, `--validate-profile`, `--version` — no gate calls found. VERIFIED.

### D-2: Auto-adopt notice exact text

Actual: `[graphify] auto-adopted vault at {cwd} (profile: .graphify/profile.yaml)` (line 1549 `__main__.py`).
Expected per CONTEXT: `[graphify] auto-adopted vault at <cwd> (profile: .graphify/profile.yaml)`.
Match: VERIFIED (no em-dash in auto-adopt notice — correct per spec).

### D-3: `--write-into-vault` suppresses VCWD-03 only, NOT VCWD-02

Gate predicate ordering: `has_profile` check comes BEFORE `write_into_vault` check (lines 1544-1553). When profile exists, auto-adopt is returned before `write_into_vault` is evaluated. VERIFIED.

### D-4: VCWD-03 refusal text verbatim with em-dash U+2014, exit 2

Actual msg: `"refusing to write into Obsidian vault at {safe_cwd} — no .graphify/profile.yaml found"`
Actual hint: `"create .graphify/profile.yaml to opt in, pass --output <path> to write outside the vault, or --write-into-vault to override"`
Em-dash U+2014: present (Python `repr()` confirmed `—`). Exit code: `code=2`. VERIFIED.

### D-5: `[vault-cwd]` section is NEW, not extending `[vault]`; three outcomes; unconditional

Section header is `[graphify] === Vault-CWD Default ===` (separate from existing `=== Vault Detection ===`). `format_report()` always appends it (no conditional guard). Three outcomes: `auto-adopt`, `refuse`, `n/a` all produced. VERIFIED.

---

## Test Suite Results

| Suite                            | Result                     | Notes                                   |
|----------------------------------|----------------------------|-----------------------------------------|
| `tests/test_vault_cwd.py`        | 16 passed (3.76s)          | All VCWD-01..05 tests green             |
| `tests/` (full)                  | 2139 passed, 1 xfailed (107.86s) | 0 failed; baseline met               |
| `tests/test_e2e_integration.py`  | 5 passed (29.67s, combined)| Phase 60 E2E regression: clean          |
| `tests/test_vault_cli.py`        | 5 passed (included above)  | Phase 41 vault CLI regression: clean    |

---

## Behavioral Spot-Checks

| Behavior                               | Command                                                | Result            | Status  |
|----------------------------------------|--------------------------------------------------------|-------------------|---------|
| 16 VCWD tests pass                     | `pytest tests/test_vault_cwd.py -q`                    | 16 passed         | PASS    |
| Full suite passes                      | `pytest tests/ -q`                                     | 2139 passed, 0 failed | PASS |
| E2E + vault CLI regressions pass       | `pytest tests/test_e2e_integration.py tests/test_vault_cli.py -q` | 5 passed  | PASS |

---

## Collateral Damage Check

`git diff --stat main~13..HEAD` shows only:
- `graphify/__main__.py` (+133/-34 lines)
- `graphify/doctor.py` (+52/-1 lines)
- `tests/test_vault_cwd.py` (new, +310 lines)
- `tests/test_doctor.py` (+5/-1 lines)
- `.planning/` artifacts (summaries, roadmap, requirements, state)

No other production files touched. CLEAN.

---

## Requirements Coverage

| Requirement | Plans      | Description                                                                       | Status    | Evidence                                                              |
|-------------|------------|-----------------------------------------------------------------------------------|-----------|-----------------------------------------------------------------------|
| VCWD-01     | 59-01      | Detection helper wired into all output-producing commands                         | SATISFIED | 14 gate call sites; `test_vcwd01_gated_commands_refuse` passes        |
| VCWD-02     | 59-02      | Auto-adopt routes via `_resolve_output_target()` identically to `--vault $CWD`    | SATISFIED | `lv_vault = Path.cwd()` wiring; `test_auto_adopt_matches_explicit_vault` passes |
| VCWD-03     | 59-03      | Exit 2 with two-line profile-focused refusal via `_emit_vault_error()`            | SATISFIED | em-dash U+2014 present; code=2; verbatim text tests pass              |
| VCWD-04     | 59-04      | `--write-into-vault` (global + per-cmd) suppresses VCWD-03 only                  | SATISFIED | Both strippers wired; `test_vcwd04_*` tests pass                      |
| VCWD-05     | 59-05      | `doctor` `[vault-cwd]` section; parity contract with runtime                     | SATISFIED | `_classify_vault_cwd()` + `format_report()`; parity test passes       |

---

## Plan-Checker Advisory Follow-Through

| Advisory | Description                                                                 | Resolution                                                                                                                      |
|----------|-----------------------------------------------------------------------------|---------------------------------------------------------------------------------------------------------------------------------|
| W1       | `test_auto_adopt_matches_explicit_vault` used doctor as routing proxy       | RESOLVED — test uses `elicit --dry-run --demo` which exercises the actual gate and `_resolve_cli_paths` routing, not doctor     |
| W4       | `cmd --help` short-circuit risk: argparse may process --help before gate    | ACCEPTED/RESOLVED — gate is inserted at TOP of each dispatch branch BEFORE argparse; tests confirm gate fires first (line 71-75 of test file comments) |

---

## Anti-Patterns Found

No blockers or warnings identified. Scan of modified files:
- No `TODO`/`FIXME`/`PLACEHOLDER` in `__main__.py` or `doctor.py` in new code sections
- No `return null`/`return []` stubs in gated dispatch branches
- `_check_vault_cwd_gate()` has real logic (3 predicates + side effect emission + exit path)
- `_classify_vault_cwd()` has real logic (mirrors runtime predicates)
- All auto-adopt branches set `lv_vault = Path.cwd()` — not a stub

---

## Human Verification Required

None. All correctness properties are programmatically verifiable and verified.

---

## Gaps Summary

No gaps. All 5 must-haves VERIFIED against the codebase.

---

_Verified: 2026-05-04T18:18:48Z_
_Verifier: Claude (gsd-verifier)_
