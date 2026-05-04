---
phase: 59-vault-cwd-aware-cli-default
plan: 02
type: tdd
wave: 2
depends_on: [59-01]
files_modified:
  - tests/test_vault_cwd.py
  - graphify/__main__.py
autonomous: true
requirements: [VCWD-02]
nyquist_compliant: true
must_haves:
  truths:
    - "When CWD is a vault with .graphify/profile.yaml and no explicit --vault/--output/--vault-list/$GRAPHIFY_VAULT, output is routed via _resolve_cli_paths(cwd, explicit_vault=Path.cwd(), ...) — identical to passing --vault $CWD."
    - "Exactly one stderr line `[graphify] auto-adopted vault at <cwd> (profile: .graphify/profile.yaml)` is emitted on the auto-adopt path."
    - "Explicit `--vault $CWD` does NOT emit the auto-adopt notice."
  artifacts:
    - path: "graphify/__main__.py"
      provides: "Auto-adopt wiring in 14 gated branches: when gate returns 'auto-adopt', branch sets explicit_vault=cwd before _resolve_cli_paths"
      contains: "gate == \"auto-adopt\""
  key_links:
    - from: "_check_vault_cwd_gate (auto-adopt return)"
      to: "branch's _resolve_cli_paths call"
      via: "if gate == 'auto-adopt': lv_vault = lv_vault or Path.cwd()"
      pattern: "gate == \"auto-adopt\""
---

<objective>
VCWD-02 wiring: when the Plan-01 gate returns "auto-adopt", each gated dispatch branch promotes `Path.cwd()` to be the explicit vault for `_resolve_cli_paths(...)`, producing routing identical to passing `--vault $CWD`. Plan 01 already emits the stderr notice; Plan 02 wires the routing side and asserts exact-once notice + behavioral parity.

Purpose: Closes VCWD-02 acceptance. The auto-adopt UX is one line on stderr followed by normal vault-pinned execution.
Output: Routing wiring per gated branch + 3 test rows (parity, single-line notice, no-notice on explicit `--vault`).
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
@.planning/phases/59-vault-cwd-aware-cli-default/59-01-SUMMARY.md
@graphify/output.py
@graphify/__main__.py
@tests/test_vault_cwd.py

<interfaces>
From graphify/output.py:
```python
def resolve_execution_paths(cwd, *, explicit_vault=None, vault_list_file=None, cli_output=None) -> ResolvedOutput:  # 172
def resolve_output(cwd, *, cli_output=None) -> ResolvedOutput:  # 275
```

From graphify/__main__.py:
```python
def _resolve_cli_paths(cwd, *, explicit_vault=None, vault_list_file=None, cli_output=None):  # 1467

# Existing run-branch routing pattern (line ~2784):
resolved = _resolve_cli_paths(
    Path.cwd(),
    explicit_vault=lv_vault or g_vault_exp,
    vault_list_file=lv_vlist or g_vault_list,
    cli_output=cli_output,
)
```
</interfaces>
</context>

<tasks>

<task type="tdd" tdd="true">
  <name>Task 1 (RED): Add VCWD-02 tests; assert auto-adopt parity + single-line notice + no-notice on explicit</name>
  <files>tests/test_vault_cwd.py</files>
  <behavior>
    - test_auto_adopt_matches_explicit_vault FAILS (auto-adopt path resolves output differently from --vault $CWD because Plan-01 stub did not promote cwd to explicit_vault).
    - test_auto_adopt_notice_emitted_once FAILS or PASSES (notice already emitted by Plan 01 helper, but parity may not hold).
    - test_explicit_vault_no_auto_adopt_notice PASSES if helper logic correct (has_explicit_route=True returns "n/a" silently).
  </behavior>
  <read_first>
    - tests/test_vault_cwd.py (existing fixtures)
    - tests/test_vault_cli.py (Phase 41 reference for `--vault` invocation patterns)
    - graphify/output.py:215 (resolve_vault_for_parity returns dict — useful for parity comparison)
  </read_first>
  <action>
Append to `tests/test_vault_cwd.py`:

```python
# NOTE: Do NOT add module-level `pytest.importorskip("yaml")` — it would skip the entire
# file when PyYAML is absent, including non-profile tests. Per-function importorskip is
# already used inside the with-profile tests below (the correct pattern).


def _resolved_output_dir(stdout_or_stderr_combined: str) -> str | None:
    """Extract the artifacts dir line `[graphify] artifacts: <path>` if present.
    Falls back to the `[graphify] resolved output target: <path>` line."""
    for line in (stdout_or_stderr_combined or "").splitlines():
        for prefix in ("[graphify] artifacts: ", "[graphify] resolved output target: "):
            if line.startswith(prefix):
                return line[len(prefix):].strip()
    return None


def test_auto_adopt_matches_explicit_vault(tmp_path):
    """VCWD-02: with-profile vault CWD + no flags routes IDENTICALLY to --vault $CWD."""
    pytest.importorskip("yaml")
    vault = _make_partial_vault(tmp_path, with_profile=True)

    # Run 1: auto-adopt (no flags)
    proc_auto = _graphify("doctor", cwd=str(vault))
    # Run 2: explicit --vault $CWD
    proc_explicit = _graphify("--vault", str(vault), "doctor", cwd=str(vault))

    # Both runs should succeed and produce identical resolved output destinations.
    # We use `doctor` because it prints the resolved Output Destination section
    # without performing real work; doctor is read-only so the gate skips,
    # but the auto-adopt notice should still NOT appear here (gate is on
    # output-producing commands only). Use `run --help` instead — but help
    # may exit before resolve. Strategy: use `update-vault --dry-run` if it
    # exists; otherwise use a minimal-side-effect command that exercises
    # _resolve_cli_paths. RECOMMENDED: invoke `import-harness --print-target`
    # if available, else add an env-var probe via running `query` from the
    # gate (gate doesn't fire for query so this won't work).
    #
    # CONCRETE TACTIC: Use the run_corpus path with an empty corpus.
    # If executor finds a cleaner harness during GREEN, refactor.
    auto_path = _resolved_output_dir(proc_auto.stdout + proc_auto.stderr)
    explicit_path = _resolved_output_dir(proc_explicit.stdout + proc_explicit.stderr)
    assert auto_path is not None, f"no resolved path in auto-adopt output: {proc_auto.stdout}\n{proc_auto.stderr}"
    assert auto_path == explicit_path, f"auto-adopt {auto_path!r} != explicit-vault {explicit_path!r}"


def test_auto_adopt_notice_emitted_once(tmp_path):
    """VCWD-02: auto-adopt path emits the notice EXACTLY once."""
    pytest.importorskip("yaml")
    vault = _make_partial_vault(tmp_path, with_profile=True)
    proc = _graphify("run", "--help", cwd=str(vault))
    notice = "[graphify] auto-adopted vault at"
    occurrences = proc.stderr.count(notice)
    assert occurrences == 1, (
        f"expected exactly 1 auto-adopt notice, got {occurrences}\nstderr:\n{proc.stderr}"
    )
    # Also assert the line includes the profile path suffix per CONTEXT D-02.
    assert "(profile: .graphify/profile.yaml)" in proc.stderr


def test_explicit_vault_no_auto_adopt_notice(tmp_path):
    """VCWD-02: passing --vault $CWD explicitly suppresses the auto-adopt notice."""
    pytest.importorskip("yaml")
    vault = _make_partial_vault(tmp_path, with_profile=True)
    proc = _graphify("--vault", str(vault), "run", "--help", cwd=str(vault))
    assert "auto-adopted vault" not in proc.stderr, (
        f"explicit --vault must not trigger auto-adopt notice; got:\n{proc.stderr}"
    )
```

**Note on `--help` short-circuit:** if `--help` exits before the gate, swap to a minimal real invocation (e.g. `run --output /tmp/out` outside vault, or a no-op subcommand). Executor adjusts test invocation during GREEN if needed. The behavioral assertions (notice text, exit, parity) MUST remain intact.

Commit message: `test(59-02): RED — VCWD-02 auto-adopt routing parity + single-line notice`
  </action>
  <acceptance_criteria>
    - `pytest tests/test_vault_cwd.py::test_auto_adopt_matches_explicit_vault tests/test_vault_cwd.py::test_auto_adopt_notice_emitted_once -x` exits non-zero (RED for at least one).
    - `grep -n "auto_adopt" tests/test_vault_cwd.py | wc -l` >= 3.
    - Commit prefix `test(59-02): RED`.
  </acceptance_criteria>
  <verify>
    <automated>pytest tests/test_vault_cwd.py::test_auto_adopt_matches_explicit_vault tests/test_vault_cwd.py::test_auto_adopt_notice_emitted_once -x; test $? -ne 0 && echo "RED CONFIRMED"</automated>
  </verify>
  <done>3 RED tests added; auto-adopt parity test fails as expected.</done>
</task>

<task type="tdd" tdd="true">
  <name>Task 2 (GREEN): Wire auto-adopt routing in 14 gated branches</name>
  <files>graphify/__main__.py</files>
  <behavior>
    - test_auto_adopt_matches_explicit_vault PASSES.
    - test_auto_adopt_notice_emitted_once PASSES (exactly one notice line).
    - test_explicit_vault_no_auto_adopt_notice PASSES.
  </behavior>
  <read_first>
    - graphify/__main__.py — each of the 14 gated branches (find each branch's `_resolve_cli_paths` invocation; insertion happens between the gate call and the resolve call).
  </read_first>
  <action>
For each of the 14 gated branches modified by Plan 01, replace the Plan-01 stub gate call with branch-aware routing logic:

```python
# Inside each gated branch, AFTER _strip_vault_flags_from_tokens(...) yields lv_vault, lv_vlist, args:
#   (or the branch-local equivalent _lv_X, _lv_X2 names)
# AND AFTER any local --output parsing produces cli_output (or branch-local equivalent):

has_explicit_route = bool(
    g_vault_exp or g_vault_list or lv_vault or lv_vlist or cli_output
    or (os.environ.get("GRAPHIFY_VAULT") or "").strip()
)
gate = _check_vault_cwd_gate(
    cmd,
    has_explicit_route=has_explicit_route,
    write_into_vault=False,  # Plan 04 fills this in
)
if gate == "auto-adopt":
    # Promote CWD to explicit vault so _resolve_cli_paths uses identical code path
    # to passing --vault $CWD.
    if lv_vault is None and g_vault_exp is None:
        lv_vault = Path.cwd()
```

Then the existing `_resolve_cli_paths(...)` call uses `lv_vault` / `lv_vlist` and routes correctly.

**Variable name harmonization:** Branches use different local names (`lv_vault`, `_lv_e`, `_lv_ih`, `_lv_dr`, etc.). Use the branch-local names; do not introduce a global rename. The pattern is identical, the names differ.

**Branches that lack a `cli_output` variable:** Synthesize the equivalent boolean — e.g., for `vault-promote` use `bool(getattr(args, 'output', None))` after argparse runs (or the equivalent `_strip` extraction). If a branch has NO `--output`, omit `cli_output` from the boolean.

**Critical anti-pitfall (RESEARCH Pitfall 5):** Auto-adopt notice must be emitted ONLY by `_check_vault_cwd_gate`. Do NOT emit additional `--vault pin uses vault root` lines for the auto-adopt path. `resolve_execution_paths` already suppresses its own notice when `cwd_r == effective_root` (verified at output.py:1442-equivalent — the `cwd_r != effective_root` guard). When auto-adopt sets `explicit_vault=Path.cwd()`, that condition is False, so no second notice. Confirmed by test_auto_adopt_notice_emitted_once asserting `count == 1`.

Commit message: `feat(59-02): GREEN — VCWD-02 auto-adopt routes via _resolve_cli_paths(explicit_vault=cwd)`
  </action>
  <acceptance_criteria>
    - `pytest tests/test_vault_cwd.py -k "auto_adopt or explicit_vault_no_auto" -x -q` PASSES (3 tests).
    - `grep -v '^#' graphify/__main__.py | grep -c 'gate == "auto-adopt"'` >= 14 (one per gated branch).
    - `pytest tests/ -q` exits 0; suite count ≥ 2123 + 5 (Plan 01: 2, Plan 02: 3).
    - No regressions in `pytest tests/test_vault_cli.py -q`.
  </acceptance_criteria>
  <verify>
    <automated>pytest tests/test_vault_cwd.py -k "auto_adopt or explicit_vault_no_auto" -x -q && pytest tests/test_vault_cli.py -q && pytest tests/ -q</automated>
  </verify>
  <done>Auto-adopt routing wired in all 14 branches; 3 VCWD-02 tests green; full suite green.</done>
</task>

</tasks>

<threat_model>
## Trust Boundaries

| Boundary | Description |
|----------|-------------|
| CWD path interpolation → stderr | The auto-adopt notice prints the resolved CWD verbatim |

## STRIDE Threat Register

| Threat ID | Category | Component | Disposition | Mitigation Plan |
|-----------|----------|-----------|-------------|-----------------|
| T-59-04 | Information Disclosure | auto-adopt stderr line includes `<cwd>` | accept | Path is the user's own CWD; no escalation. Path resolution uses `Path.cwd().resolve()` which canonicalizes (no traversal sequences in output). |
| T-59-05 | Spoofing | Adversarial `.graphify/profile.yaml` triggering false auto-adopt | accept | The profile is loaded by `resolve_execution_paths`; profile-load itself is the trust boundary, owned by Phase 41. Phase 59 only checks `is_file()`. |
</threat_model>

<verification>
- 3 VCWD-02 tests green.
- Auto-adopt notice count == 1 in stderr per process.
- Full suite green (2123 + ≥5 baseline).
</verification>

<success_criteria>
- VCWD-02 acceptance from ROADMAP success criterion 2: auto-route identical to `--vault $CWD`, no flags required.
- CONTEXT D-02 wording verbatim in stderr (locked text).
</success_criteria>

<output>
After completion, create `.planning/phases/59-vault-cwd-aware-cli-default/59-02-SUMMARY.md` documenting:
- Each branch's variable-name binding (lv_vault vs _lv_e vs _lv_ih, etc.)
- Any branches where `cli_output` had to be synthesized differently
- Final test count delta
</output>
