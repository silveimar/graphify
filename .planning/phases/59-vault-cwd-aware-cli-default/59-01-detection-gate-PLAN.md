---
phase: 59-vault-cwd-aware-cli-default
plan: 01
type: tdd
wave: 1
depends_on: []
files_modified:
  - tests/test_vault_cwd.py
  - graphify/__main__.py
autonomous: true
requirements: [VCWD-01]
nyquist_compliant: true
must_haves:
  truths:
    - "A single helper `_check_vault_cwd_gate(cmd, *, has_explicit_route, write_into_vault) -> str` exists in graphify/__main__.py and detects CWD vault state via is_obsidian_vault(Path.cwd().resolve())."
    - "The 14 gated subcommands (run, update-vault, enrich, --obsidian, vault-promote, import-harness, save-result, --diagram-seeds, --init-diagram-templates, --dedup, snapshot, approve, elicit, harness) call this helper exactly once before pipeline dispatch."
    - "The 8 read-only commands (query, doctor, install, hook, capability, benchmark, --validate-profile, --version) DO NOT call the gate."
    - "tests/test_vault_cwd.py exists with the _make_partial_vault(parent, *, with_profile) fixture (Wave 0 infrastructure)."
  artifacts:
    - path: "tests/test_vault_cwd.py"
      provides: "All Phase 59 test scaffolding + Wave 0 fixture"
      contains: "_make_partial_vault"
    - path: "graphify/__main__.py"
      provides: "_check_vault_cwd_gate helper and call sites in 14 dispatch branches"
      contains: "_check_vault_cwd_gate"
  key_links:
    - from: "graphify/__main__.py:_check_vault_cwd_gate"
      to: "graphify/output.py:is_obsidian_vault"
      via: "import + call on Path.cwd().resolve()"
      pattern: "is_obsidian_vault"
    - from: "Each gated dispatch branch in __main__.py"
      to: "_check_vault_cwd_gate"
      via: "single call after _strip_vault_flags_from_tokens"
      pattern: "_check_vault_cwd_gate\\("
---

<objective>
Wire the VCWD-01 detection gate: a single helper that classifies the CWD into "auto-adopt" / "refuse" / "n/a", invoked once at the top of each of the 14 output-producing dispatch branches in `graphify/__main__.py`, and skipped entirely for the 8 read-only commands. Wave 0 also creates the `tests/test_vault_cwd.py` test file (consumed by Plans 02–05 for their RED tests).

Purpose: Single source of truth for CWD vault detection at dispatch time. All downstream VCWD plans (02 auto-adopt, 03 refuse, 04 write-into-vault, 05 doctor) depend on this helper existing.

Output: Wave 0 fixture file, helper function, 14 call sites (initially returning "n/a" for non-vault, raising NotImplementedError for vault paths until Plans 02/03 wire those branches).
</objective>

<execution_context>
@$HOME/.claude/get-shit-done/workflows/execute-plan.md
@$HOME/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/PROJECT.md
@.planning/ROADMAP.md
@.planning/STATE.md
@.planning/REQUIREMENTS.md
@.planning/phases/59-vault-cwd-aware-cli-default/59-CONTEXT.md
@.planning/phases/59-vault-cwd-aware-cli-default/59-RESEARCH.md
@.planning/phases/59-vault-cwd-aware-cli-default/59-VALIDATION.md
@graphify/output.py
@graphify/__main__.py
@tests/test_vault_cli.py
@tests/test_e2e_integration.py

<interfaces>
<!-- All extracted at HEAD. Executor should NOT re-explore the codebase for these. -->

From graphify/output.py:
```python
def is_obsidian_vault(path: Path) -> bool:                       # line 69
def _emit_vault_error(msg: str, hint: str, *, code: int = 1) -> SystemExit:  # line 80
def resolve_execution_paths(cwd: Path, *, explicit_vault: Path|None=None,
    vault_list_file: Path|None=None, cli_output: str|None=None) -> ResolvedOutput:  # line 172
def resolve_vault_for_parity(cwd: Path, *, explicit_vault: Path|None=None,
    vault_list_file: Path|None=None) -> dict:                    # line 215
def resolve_output(cwd: Path, *, cli_output: str|None=None) -> ResolvedOutput:  # line 275
```

From graphify/__main__.py:
```python
def _strip_leading_vault_global_argv(argv: list[str]) -> tuple[list[str], Path|None, Path|None]:  # line 1394
def _strip_vault_flags_from_tokens(tokens: list[str]) -> tuple[Path|None, Path|None, list[str]]:  # line 1420
def _merge_vault_pins(...) -> tuple[Path|None, Path|None]:       # line 1448
def _resolve_cli_paths(cwd: Path, *, explicit_vault: Path|None=None,
    vault_list_file: Path|None=None, cli_output: str|None=None) -> ResolvedOutput:  # line 1467

# Global pop call site:
sys.argv, g_vault_exp, g_vault_list = _strip_leading_vault_global_argv(sys.argv)  # line 1492

# 14 gated dispatch branches:
elif cmd == "save-result":     # 2489
elif cmd == "elicit":          # 2523
elif cmd == "harness":         # 2609
elif cmd == "import-harness":  # 2672
elif cmd == "run":             # 2755
elif cmd == "enrich":          # 2856
elif cmd == "update-vault":    # 3078
elif cmd == "vault-promote":   # 3124
# Plus: --obsidian, --diagram-seeds, --init-diagram-templates, --dedup, snapshot, approve
# (verify exact line numbers via grep at execution time)

# 8 read-only branches (NO GATE):
elif cmd == "query":           # 2429
elif cmd == "capability":      # 2508
elif cmd == "doctor":          # 2965
elif cmd == "hook":            # 2417
elif cmd == "watch":           # 2924   [DECISION: not in gated-list per CONTEXT D-01]
elif cmd == "benchmark":       # 2951
# Plus: install (top-level), --validate-profile, --version (handled before dispatch)
```

From graphify/doctor.py (consumed by Plan 05):
```python
def format_report(report: DoctorReport) -> str:                  # line 514
# Section headers use: lines.append("[graphify] === Section Name ===")
```

From tests/test_vault_cli.py:
```python
def _make_vault(path: Path) -> None:                              # line 30 (reference pattern)
    # creates .obsidian/ and .graphify/profile.yaml
```

From tests/test_e2e_integration.py:
```python
def _graphify(*args, cwd: str|None = None, env: dict|None = None) -> subprocess.CompletedProcess:  # line 20
def _write_vault(path: Path) -> None:                             # line 56
```
</interfaces>
</context>

<tasks>

<task type="auto">
  <name>Task 0 (Wave 0): Create tests/test_vault_cwd.py with fixtures</name>
  <files>tests/test_vault_cwd.py</files>
  <read_first>
    - tests/test_vault_cli.py lines 1–60 (study _make_vault pattern)
    - tests/test_e2e_integration.py lines 1–80 (study _graphify and _write_vault patterns)
  </read_first>
  <action>
Create new file `tests/test_vault_cwd.py` containing the Phase 59 test scaffolding. Module docstring: "Phase 59 — VCWD-01..05 coverage. See .planning/phases/59-vault-cwd-aware-cli-default/59-VALIDATION.md".

Required imports/header:
```python
"""Phase 59 — VCWD-01..05 coverage."""
from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent


def _make_partial_vault(parent: Path, *, with_profile: bool) -> Path:
    """Create an Obsidian vault under `parent`. If with_profile, also write
    .graphify/profile.yaml so VCWD-02 auto-adopt path applies."""
    vault = parent / "vault"
    (vault / ".obsidian").mkdir(parents=True, exist_ok=True)
    if with_profile:
        gdir = vault / ".graphify"
        gdir.mkdir(parents=True, exist_ok=True)
        (gdir / "profile.yaml").write_text(
            "version: 1\nframework: ideaverse\nfolder_map: {}\n",
            encoding="utf-8",
        )
    return vault


def _make_no_vault(parent: Path) -> Path:
    """Create a regular directory with NO .obsidian/ (for VCWD-05 n/a outcome)."""
    p = parent / "not_a_vault"
    p.mkdir(parents=True, exist_ok=True)
    return p


def _graphify(*args: str, cwd: str | None = None, env: dict | None = None) -> subprocess.CompletedProcess:
    """Subprocess runner mirroring tests/test_e2e_integration.py:_graphify.
    ALWAYS passes cwd explicitly (per RESEARCH Pitfall 3 — never inherit CWD)."""
    cmd = [sys.executable, "-m", "graphify", *args]
    base_env = {**os.environ, **(env or {})}
    return subprocess.run(
        cmd, cwd=cwd, env=base_env, capture_output=True, text=True, timeout=60,
    )


# Placeholder skeleton tests — RED phase for Plan 01 only.
# Plans 02..05 add their own RED tests in this file.

GATED_COMMANDS = [
    "run", "update-vault", "enrich", "vault-promote", "import-harness",
    "save-result", "snapshot", "approve", "elicit", "harness",
    # Note: --obsidian, --diagram-seeds, --init-diagram-templates, --dedup are
    # subcommand-FLAG gated paths exercised via test_gate_runs_for_each_gated_cmd.
]

READONLY_COMMANDS = [
    "query", "doctor", "install", "hook", "capability", "benchmark",
]
```

Then add the two RED tests for Plan 01 only (the rest of plans append their own):

```python
def test_gate_runs_for_each_gated_cmd(tmp_path):
    """VCWD-01: gated commands invoke the gate from a profile-less vault CWD,
    yielding exit 2 with two-line stderr (gate refuses)."""
    vault = _make_partial_vault(tmp_path, with_profile=False)
    failures = []
    for cmd in GATED_COMMANDS:
        # Use --help so command never starts real work; gate runs BEFORE help-parsing
        # for these branches per the dispatch-time insertion (RESEARCH Pattern 1).
        # If the gate is wired correctly, exit will be 2 with 'refusing to write'.
        # If gate is missing for a command, exit will be 0 (help printed) or non-2.
        proc = _graphify(cmd, "--help", cwd=str(vault))
        if proc.returncode != 2:
            failures.append((cmd, proc.returncode, proc.stderr[:200]))
        elif "refusing to write into Obsidian vault" not in proc.stderr:
            failures.append((cmd, "missing-refusal-msg", proc.stderr[:200]))
    assert not failures, f"Gate did not fire for: {failures}"


def test_gate_skipped_for_readonly_cmds(tmp_path):
    """VCWD-01: read-only commands MUST NOT invoke the gate."""
    vault = _make_partial_vault(tmp_path, with_profile=False)
    for cmd in READONLY_COMMANDS:
        proc = _graphify(cmd, "--help", cwd=str(vault))
        # Help should succeed (exit 0); definitely no two-line refusal.
        assert "refusing to write into Obsidian vault" not in proc.stderr, (
            f"Gate fired for read-only cmd {cmd!r}: {proc.stderr[:200]}"
        )
```

Note on `--help`: if `--help` short-circuits BEFORE the gate (argparse default behavior in some branches), use a benign positional arg or omit help — the goal is to land in the dispatch branch that calls the gate. If the gate must run before argparse, the executor verifies by reading the dispatch ladder; tests that need a different invocation MUST be adjusted to land in the gate path. (Open question: validated during GREEN.)
  </action>
  <acceptance_criteria>
    - `pytest tests/test_vault_cwd.py --collect-only -q` lists at least 2 tests (test_gate_runs_for_each_gated_cmd, test_gate_skipped_for_readonly_cmds).
    - `grep -n "_make_partial_vault" tests/test_vault_cwd.py` returns at least 2 matches (def + at least one usage).
    - File has `from __future__ import annotations` on the first non-docstring import line.
    - File contains zero syntax errors: `python -c "import ast; ast.parse(open('tests/test_vault_cwd.py').read())"` exits 0.
  </acceptance_criteria>
  <verify>
    <automated>python -c "import ast; ast.parse(open('tests/test_vault_cwd.py').read())" && pytest tests/test_vault_cwd.py --collect-only -q</automated>
  </verify>
  <done>tests/test_vault_cwd.py exists with fixtures + 2 RED tests; module parses cleanly; pytest collects.</done>
</task>

<task type="tdd" tdd="true">
  <name>Task 1 (RED): Run Plan-01 tests; assert they fail because no gate exists</name>
  <files>tests/test_vault_cwd.py</files>
  <behavior>
    - test_gate_runs_for_each_gated_cmd FAILS (exit code != 2 for at least one gated command — gate not yet wired).
    - test_gate_skipped_for_readonly_cmds may PASS or FAIL depending on baseline; track for reference.
  </behavior>
  <read_first>tests/test_vault_cwd.py (just created)</read_first>
  <action>
Run the Plan-01 tests against the unmodified codebase to confirm RED. Expected: `test_gate_runs_for_each_gated_cmd` fails because no `_check_vault_cwd_gate` exists and dispatch branches do not refuse on profile-less vault CWD.

Do NOT modify production code yet. Capture stderr/exit-code to confirm RED state.

Commit message: `test(59-01): RED — assert dispatch gate wires across 14 gated commands`
  </action>
  <acceptance_criteria>
    - `pytest tests/test_vault_cwd.py::test_gate_runs_for_each_gated_cmd -x` exits non-zero.
    - Test failure message references "Gate did not fire for:" with a list of one or more commands (per D-01).
    - Git log shows the RED commit with the prefix `test(59-01): RED`.
  </acceptance_criteria>
  <verify>
    <automated>pytest tests/test_vault_cwd.py::test_gate_runs_for_each_gated_cmd -x; test $? -ne 0 && echo "RED CONFIRMED"</automated>
  </verify>
  <done>RED commit landed; failing test demonstrates absence of the gate.</done>
</task>

<task type="tdd" tdd="true">
  <name>Task 2 (GREEN): Implement _check_vault_cwd_gate and wire 14 dispatch branches</name>
  <files>graphify/__main__.py</files>
  <behavior>
    - test_gate_runs_for_each_gated_cmd PASSES (all 14 gated commands invoke the gate, refuse with exit 2 + two-line stderr).
    - test_gate_skipped_for_readonly_cmds PASSES (8 read-only commands do NOT invoke the gate).
  </behavior>
  <read_first>
    - graphify/__main__.py lines 1394–1500 (helper region — insertion point for new helper)
    - graphify/__main__.py lines 1490–1495 (main() startup, where global pop runs)
    - graphify/__main__.py lines 2489, 2523, 2609, 2672, 2755, 2856, 3078, 3124 (8 verified gated branches)
    - Use grep to locate the remaining branches: `grep -n "elif cmd ==" graphify/__main__.py` and `grep -n "obsidian\|diagram-seeds\|init-diagram-templates\|dedup\|snapshot\|approve" graphify/__main__.py`
  </read_first>
  <action>
**Step 1 — Add the helper near line 1480 (next to `_resolve_cli_paths`):**

```python
def _check_vault_cwd_gate(
    cmd: str,
    *,
    has_explicit_route: bool,
    write_into_vault: bool,
) -> str:
    """VCWD-01..04 dispatch gate.

    Classifies CWD into one of: "auto-adopt", "refuse" (never returned — raises),
    "n/a". Side effects:
      - Emits the auto-adopt stderr notice exactly once when it returns "auto-adopt".
      - Raises SystemExit(2) via _emit_vault_error() when it would otherwise
        return "refuse" AND `write_into_vault` is False.

    Per CONTEXT D-01, this helper is invoked from EXACTLY the 14 gated branches
    listed in CONTEXT.md. Read-only commands do not call it.
    """
    from graphify.output import is_obsidian_vault, _emit_vault_error
    cwd = Path.cwd().resolve()
    if not is_obsidian_vault(cwd):
        return "n/a"
    has_profile = (cwd / ".graphify" / "profile.yaml").is_file()
    if has_explicit_route:
        return "n/a"  # silent precedence — explicit routing wins
    if has_profile:
        # VCWD-02 auto-adopt notice — exactly one line, exactly once per process.
        # Plan 02 wires the routing side; this stub only emits the notice.
        print(
            f"[graphify] auto-adopted vault at {cwd} (profile: .graphify/profile.yaml)",
            file=sys.stderr,
        )
        return "auto-adopt"
    if write_into_vault:
        return "n/a"  # VCWD-04 silent opt-in
    raise _emit_vault_error(
        f"refusing to write into Obsidian vault at {cwd} — no .graphify/profile.yaml found",
        "create .graphify/profile.yaml to opt in, pass --output <path> to write outside the vault, or --write-into-vault to override",
        code=2,
    )
```

**Step 2 — Wire the 14 gated branches.** For each branch, insert the gate call IMMEDIATELY after the existing `_strip_vault_flags_from_tokens` invocation (or at branch entry if that helper is not yet called). For Plan 01 use:

```python
gate = _check_vault_cwd_gate(
    cmd,
    has_explicit_route=bool(
        g_vault_exp or g_vault_list
        or (os.environ.get("GRAPHIFY_VAULT") or "").strip()
    ),
    write_into_vault=False,  # Plan 04 wires --write-into-vault threading
)
# Plan 02 will use `gate == "auto-adopt"` to set explicit_vault=cwd.
```

(Plan 02 will replace `write_into_vault=False` and the `has_explicit_route` boolean with branch-local `lv_*` flags. Plan 04 will add the global+per-command `--write-into-vault` plumbing. Keep this insertion isolated — single line invocation per branch.)

The 14 gated insertion points (verify each at execution time via grep):
1. `elif cmd == "run":` (~2755)
2. `elif cmd == "update-vault":` (~3078)
3. `elif cmd == "enrich":` (~2856)
4. `elif cmd == "vault-promote":` (~3124)
5. `elif cmd == "import-harness":` (~2672)
6. `elif cmd == "save-result":` (~2489)
7. `elif cmd == "snapshot":` (locate via grep — `elif cmd == "snapshot"`)
8. `elif cmd == "approve":` (locate via grep)
9. `elif cmd == "elicit":` (~2523)
10. `elif cmd == "harness":` (~2609)
11. `--obsidian` flag path (locate via grep `--obsidian` in dispatch)
12. `--diagram-seeds` flag path (locate via grep)
13. `--init-diagram-templates` flag path (locate via grep)
14. `--dedup` flag path (locate via grep)

**Step 3 — Do NOT call the gate from any of:** `query`, `doctor`, `install`, `hook`, `capability`, `benchmark`, `watch`, `--validate-profile`, `--version`, plus the `claude`/`gemini`/`cursor`/`copilot`/`antigravity` install branches.

Commit message: `feat(59-01): GREEN — VCWD-01 dispatch gate wired across 14 commands`
  </action>
  <acceptance_criteria>
    - `grep -n "_check_vault_cwd_gate" graphify/__main__.py | grep -v "^#" | wc -l` >= 15 (1 def + 14 call sites). Use `-v '^#'` per planner header rule.
    - `grep -nE "elif cmd == \"(query|doctor|install|hook|capability|benchmark|watch)\"" graphify/__main__.py` confirms these branches exist; manual inspection confirms the gate is NOT called from them.
    - `pytest tests/test_vault_cwd.py::test_gate_runs_for_each_gated_cmd -x` PASSES.
    - `pytest tests/test_vault_cwd.py::test_gate_skipped_for_readonly_cmds -x` PASSES.
    - `pytest tests/ -q` exits 0; full-suite count ≥ baseline (2123) + 2 (delta from Plan 01 tests).
    - Commit message starts with `feat(59-01): GREEN`.
  </acceptance_criteria>
  <verify>
    <automated>pytest tests/test_vault_cwd.py::test_gate_runs_for_each_gated_cmd tests/test_vault_cwd.py::test_gate_skipped_for_readonly_cmds -x -q && pytest tests/ -q</automated>
  </verify>
  <done>Helper and 14 call sites in place; both Plan-01 tests green; full suite green.</done>
</task>

</tasks>

<threat_model>
## Trust Boundaries

| Boundary | Description |
|----------|-------------|
| process CWD → gate | Untrusted directory contents (user could run `graphify` from any directory, including one with adversarial path components in absolute resolution) |

## STRIDE Threat Register

| Threat ID | Category | Component | Disposition | Mitigation Plan |
|-----------|----------|-----------|-------------|-----------------|
| T-59-01 | Information Disclosure | `_check_vault_cwd_gate` resolved CWD interpolated into stderr | mitigate | Plan 03 sanitizes `<cwd>` via `security.py` rules before interpolation. Plan 01 only emits the auto-adopt notice (not the refusal); auto-adopt notice is benign because the user already implicitly trusts CWD. |
| T-59-02 | Tampering | Gate bypass by symlinking `.obsidian/` into a non-vault dir | accept | `is_obsidian_vault` already follows project precedent (Phase 41) — symlink semantics inherited; not new attack surface. |
| T-59-03 | Denial of Service | Gate I/O on `(cwd/".graphify"/"profile.yaml").is_file()` | accept | Single stat() call per process; cost is negligible. |
</threat_model>

<verification>
- All Plan 01 tests pass (`pytest tests/test_vault_cwd.py::test_gate_runs_for_each_gated_cmd tests/test_vault_cwd.py::test_gate_skipped_for_readonly_cmds -x`).
- Full suite green: `pytest tests/ -q`.
- Helper symbol count: `grep -v '^#' graphify/__main__.py | grep -c _check_vault_cwd_gate` >= 15.
- No stray `is_obsidian_vault(Path.cwd())` calls outside the helper: `grep -n "is_obsidian_vault" graphify/__main__.py | grep -v "_check_vault_cwd_gate"` should match nothing inside dispatch branches (only inside the helper).
</verification>

<success_criteria>
- VCWD-01 acceptance: detection runs in 14 gated commands; doctor (read-only) is skipped (Plan 05 adds doctor's separate parity classifier).
- All Wave 0 infrastructure (test file + fixtures) ready for Plans 02–05.
- Helper signature, return values, and side effects exactly match RESEARCH Example 1 and CONTEXT D-01..D-05.
</success_criteria>

<output>
After completion, create `.planning/phases/59-vault-cwd-aware-cli-default/59-01-SUMMARY.md` documenting:
- 14 dispatch branches modified (with line numbers)
- Helper signature
- Test count delta
- Any deviations from RESEARCH Pattern 1 (e.g., a branch that needed special handling)
</output>
