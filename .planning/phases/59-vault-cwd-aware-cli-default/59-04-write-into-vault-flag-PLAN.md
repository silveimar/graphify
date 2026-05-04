---
phase: 59-vault-cwd-aware-cli-default
plan: 04
type: tdd
wave: 2
depends_on: [59-01, 59-02, 59-03]
files_modified:
  - tests/test_vault_cwd.py
  - graphify/__main__.py
autonomous: true
requirements: [VCWD-04]
nyquist_compliant: true
must_haves:
  truths:
    - "`--write-into-vault` is accepted as a leading global flag (before the subcommand) and as a per-subcommand flag for each of the 14 gated commands."
    - "When --write-into-vault is set, VCWD-03 refusal is suppressed and execution proceeds with pre-v1.12 behavior."
    - "When --write-into-vault is combined with --vault or --output, the explicit routing wins silently (no warning, no error)."
    - "--write-into-vault does NOT suppress VCWD-02 auto-adopt — when a profile exists, the profile-driven route still wins."
  artifacts:
    - path: "graphify/__main__.py"
      provides: "_pop_global_write_into_vault, _strip_write_into_vault_from_tokens, threading of g_write_into_vault and lv_write_into_vault into the gate"
      contains: "_pop_global_write_into_vault"
  key_links:
    - from: "main() startup"
      to: "_pop_global_write_into_vault"
      via: "sys.argv, g_write_into_vault = _pop_global_write_into_vault(sys.argv)"
      pattern: "_pop_global_write_into_vault"
    - from: "Each gated branch"
      to: "_check_vault_cwd_gate(write_into_vault=g_write_into_vault or lv_write_into_vault)"
      via: "branch-local strip + OR with global"
      pattern: "write_into_vault=.*lv_"
---

<objective>
VCWD-04: add the `--write-into-vault` boolean flag with global-leading + per-subcommand parsing (mirroring the existing `--vault` plumbing pattern) and thread it into the Plan-01 gate so that:
- Setting the flag suppresses the VCWD-03 refusal silently.
- The flag does NOT suppress the VCWD-02 auto-adopt notice (profile-driven route still wins).
- Combining the flag with `--vault`/`--output` is silent: explicit routing wins, no warning.

Purpose: Closes VCWD-04 acceptance.
Output: 2 new helpers (global pop + per-command strip), threading in 14 branches, 4 RED→GREEN test rows.
</objective>

<execution_context>
@$HOME/.claude/get-shit-done/workflows/execute-plan.md
@$HOME/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/REQUIREMENTS.md
@.planning/phases/59-vault-cwd-aware-cli-default/59-CONTEXT.md
@.planning/phases/59-vault-cwd-aware-cli-default/59-RESEARCH.md
@.planning/phases/59-vault-cwd-aware-cli-default/59-VALIDATION.md
@.planning/phases/59-vault-cwd-aware-cli-default/59-01-SUMMARY.md
@graphify/__main__.py
@tests/test_vault_cwd.py

<interfaces>
From graphify/__main__.py:
```python
def _strip_leading_vault_global_argv(argv: list[str]) -> tuple[list[str], Path|None, Path|None]:  # 1394
    # Pattern to mirror exactly for --write-into-vault.
def _strip_vault_flags_from_tokens(tokens: list[str]) -> tuple[Path|None, Path|None, list[str]]:  # 1420
    # Pattern to mirror for per-command strip.
```

Phase 57 reference (orthogonal flag — does NOT collide):
```python
# graphify/__main__.py around 2724–2728: harness `--allow-vault-write`
# Both flags coexist on harness/import-harness branches; both gates fire independently.
```
</interfaces>
</context>

<tasks>

<task type="tdd" tdd="true">
  <name>Task 1 (RED): Add 4 VCWD-04 tests for flag plumbing + precedence</name>
  <files>tests/test_vault_cwd.py</files>
  <behavior>
    - All 4 tests FAIL (no `--write-into-vault` flag plumbing exists yet — argparse / token-strip will reject it).
  </behavior>
  <read_first>
    - tests/test_vault_cwd.py
    - .planning/phases/59-vault-cwd-aware-cli-default/59-CONTEXT.md (Decision 3 — flag semantics)
  </read_first>
  <action>
Append to `tests/test_vault_cwd.py`:

```python
def test_write_into_vault_suppresses_refusal(tmp_path):
    """VCWD-04: per-command --write-into-vault suppresses VCWD-03 refusal."""
    vault = _make_partial_vault(tmp_path, with_profile=False)
    proc = _graphify("run", "--write-into-vault", "--help", cwd=str(vault))
    # No exit-2 refusal: the flag suppresses it. exit code 0 (help) or another
    # non-2 value is acceptable; the assertion is that VCWD-03 stderr does NOT appear.
    assert "refusing to write into Obsidian vault" not in proc.stderr, (
        f"--write-into-vault should suppress refusal; got:\n{proc.stderr}"
    )
    assert proc.returncode != 2, f"unexpected exit 2 with --write-into-vault: stderr=\n{proc.stderr}"


def test_global_write_into_vault_suppresses_refusal(tmp_path):
    """VCWD-04: leading global --write-into-vault (before subcommand) suppresses refusal."""
    vault = _make_partial_vault(tmp_path, with_profile=False)
    proc = _graphify("--write-into-vault", "run", "--help", cwd=str(vault))
    assert "refusing to write into Obsidian vault" not in proc.stderr, (
        f"global --write-into-vault should suppress refusal; got:\n{proc.stderr}"
    )
    assert proc.returncode != 2


def test_write_into_vault_silent_precedence(tmp_path):
    """VCWD-04: combined with --vault / --output, explicit wins silently (no warning)."""
    vault = _make_partial_vault(tmp_path, with_profile=False)
    out_dir = tmp_path / "outside"
    out_dir.mkdir()
    proc = _graphify(
        "--vault", str(vault), "--write-into-vault",
        "run", "--help",
        cwd=str(vault),
    )
    # Silent precedence: NO warning about flag conflict / no-op redundancy.
    forbidden_phrases = [
        "ignored", "ignoring", "redundant", "no-op", "warning:",
        "--write-into-vault has no effect",
    ]
    for phrase in forbidden_phrases:
        assert phrase not in proc.stderr.lower(), (
            f"silent precedence violated: stderr contains {phrase!r}\n{proc.stderr}"
        )


def test_write_into_vault_yields_to_profile(tmp_path):
    """VCWD-04: --write-into-vault does NOT suppress VCWD-02 auto-adopt (profile wins)."""
    pytest.importorskip("yaml")
    vault = _make_partial_vault(tmp_path, with_profile=True)
    proc = _graphify("--write-into-vault", "run", "--help", cwd=str(vault))
    # Profile present: auto-adopt path takes priority. Notice still appears.
    assert "[graphify] auto-adopted vault at" in proc.stderr, (
        f"--write-into-vault must NOT suppress auto-adopt notice; stderr:\n{proc.stderr}"
    )
```

Commit message: `test(59-04): RED — VCWD-04 --write-into-vault global+per-command, silent precedence`
  </action>
  <acceptance_criteria>
    - 4 new tests collectable.
    - `pytest tests/test_vault_cwd.py -k write_into_vault -x` exits non-zero (RED).
    - Commit prefix `test(59-04): RED`.
  </acceptance_criteria>
  <verify>
    <automated>pytest tests/test_vault_cwd.py -k write_into_vault -x; test $? -ne 0 && echo "RED CONFIRMED"</automated>
  </verify>
  <done>4 RED tests added; all fail.</done>
</task>

<task type="tdd" tdd="true">
  <name>Task 2 (GREEN): Add _pop_global_write_into_vault + _strip_write_into_vault_from_tokens; thread into 14 branches</name>
  <files>graphify/__main__.py</files>
  <behavior>
    - All 4 VCWD-04 tests PASS.
    - test_write_into_vault_yields_to_profile (auto-adopt with profile) PASSES — auto-adopt wins over the opt-in flag.
    - Combined --vault + --write-into-vault produces NO stderr warning.
  </behavior>
  <read_first>
    - graphify/__main__.py:1394–1463 (existing `_strip_leading_vault_global_argv` and `_strip_vault_flags_from_tokens` to mirror)
    - graphify/__main__.py:1490–1495 (main() startup pop call site)
    - All 14 gated branches (locate via grep `_check_vault_cwd_gate`)
  </read_first>
  <action>
**Step 1 — Add `_pop_global_write_into_vault` helper near line 1394:**

```python
def _pop_global_write_into_vault(argv: list[str]) -> tuple[list[str], bool]:
    """Pop a leading `--write-into-vault` boolean flag from argv (before subcommand).
    Mirrors `_strip_leading_vault_global_argv` for symmetry."""
    out = list(argv)
    flag = False
    # Walk leading positions only (positions 1..N-1 before any non-flag token).
    while len(out) > 1 and out[1] == "--write-into-vault":
        flag = True
        out = [out[0]] + out[2:]
    return out, flag
```

**Step 2 — Add `_strip_write_into_vault_from_tokens` helper near line 1422:**

```python
def _strip_write_into_vault_from_tokens(tokens: list[str]) -> tuple[bool, list[str]]:
    """Strip per-command `--write-into-vault` boolean flag from a token list.
    Boolean flag (no value); multiple occurrences collapse to True.
    Mirrors `_strip_vault_flags_from_tokens` shape."""
    flag = False
    out: list[str] = []
    for t in tokens:
        if t == "--write-into-vault":
            flag = True
        else:
            out.append(t)
    return flag, out
```

**Step 3 — Wire global pop in `main()` startup near line 1492 (right after `_strip_leading_vault_global_argv`):**

```python
sys.argv, g_vault_exp, g_vault_list = _strip_leading_vault_global_argv(sys.argv)
sys.argv, g_write_into_vault = _pop_global_write_into_vault(sys.argv)  # NEW
```

**Step 4 — In each of the 14 gated branches, add the per-command strip and OR with global, then update the gate call:**

```python
# After existing strip:
lv_vault, lv_vlist, args = _strip_vault_flags_from_tokens(args)
# NEW:
lv_write_into_vault, args = _strip_write_into_vault_from_tokens(args)

# Then update the gate invocation:
gate = _check_vault_cwd_gate(
    cmd,
    has_explicit_route=bool(
        g_vault_exp or g_vault_list or lv_vault or lv_vlist or cli_output
        or (os.environ.get("GRAPHIFY_VAULT") or "").strip()
    ),
    write_into_vault=bool(g_write_into_vault or lv_write_into_vault),
)
```

**Anti-pitfall (RESEARCH Pitfall 4):** On `harness` and `import-harness` branches, the existing `--allow-vault-write` flag (Phase 57) is ORTHOGONAL. Both flags coexist; both must be parsed independently. `--write-into-vault` only affects the VCWD-03 refusal; `--allow-vault-write` only affects the harness artifacts-dir-under-vault-root check. Do NOT collapse them.

**Anti-pitfall (silent precedence):** When both `--write-into-vault` and `--vault` are passed, the gate returns `"n/a"` because `has_explicit_route=True` (--vault is set). The `write_into_vault` parameter is never consulted in that path → no warning emitted by anyone. Test `test_write_into_vault_silent_precedence` verifies this.

**Anti-pitfall (yields to profile):** When profile exists, the gate returns `"auto-adopt"` BEFORE checking `write_into_vault`. Per the helper logic added in Plan 01:
```python
if has_profile:
    print("...auto-adopted...", file=sys.stderr); return "auto-adopt"
if write_into_vault:
    return "n/a"
```
The order of `if has_profile` BEFORE `if write_into_vault` is what makes `test_write_into_vault_yields_to_profile` pass.

**Step 5 — Documentation in `--help` for the 14 commands:** OUT OF SCOPE for this plan (CONTEXT D-03 mentions documentation but does not lock the wording). Defer to executor's discretion if argparse `add_argument` calls naturally accept a help string. If the per-command flag is parsed via `_strip_write_into_vault_from_tokens` (token-strip pattern) rather than argparse, no help text is needed.

Commit message: `feat(59-04): GREEN — VCWD-04 --write-into-vault global+per-command, suppresses refusal only`
  </action>
  <acceptance_criteria>
    - `pytest tests/test_vault_cwd.py -k write_into_vault -x -q` PASSES (4 tests).
    - `grep -v '^#' graphify/__main__.py | grep -c '_pop_global_write_into_vault'` >= 2 (def + call site).
    - `grep -v '^#' graphify/__main__.py | grep -c '_strip_write_into_vault_from_tokens'` >= 15 (def + 14 branch usages).
    - `grep -v '^#' graphify/__main__.py | grep -c 'g_write_into_vault'` >= 2 (assignment + 14 OR-merges; could be inlined).
    - On harness branches, `--allow-vault-write` references still present: `grep -n "allow-vault-write" graphify/__main__.py | wc -l` >= 1.
    - `pytest tests/test_vault_cli.py -q` passes (Phase 41 regression).
    - `pytest tests/ -q` exits 0; suite ≥ 2123 + 11 (Plans 01–04 cumulative tests).
  </acceptance_criteria>
  <verify>
    <automated>pytest tests/test_vault_cwd.py -k write_into_vault -x -q && pytest tests/test_vault_cli.py -q && pytest tests/ -q</automated>
  </verify>
  <done>VCWD-04 flag plumbing complete; 4 tests green; auto-adopt + harness-allow-vault-write unaffected; full suite green.</done>
</task>

</tasks>

<threat_model>
## Trust Boundaries

| Boundary | Description |
|----------|-------------|
| user argv → flag plumbing | Untrusted argv tokens parsed; injection of unexpected flag values |

## STRIDE Threat Register

| Threat ID | Category | Component | Disposition | Mitigation Plan |
|-----------|----------|-----------|-------------|-----------------|
| T-59-08 | Tampering | Repeated `--write-into-vault` tokens (e.g. `... --write-into-vault --write-into-vault ...`) | accept | Boolean collapse — multiple occurrences yield True. Documented in helper docstring. |
| T-59-09 | Elevation of Privilege | A user typo `--write-into-Vault` parsed as positional → ignored | accept | Token-strip is exact-string match; case-sensitive matches Phase 41 pattern. Typos pass through to argparse which rejects them with help. |
</threat_model>

<verification>
- 4 VCWD-04 tests green.
- Helper symbol counts verified.
- Full suite green; Phase 41 + Phase 57 regressions clean.
</verification>

<success_criteria>
- ROADMAP success criterion 4: --write-into-vault suppresses VCWD-03 refusal; documented as deliberate opt-in.
- CONTEXT D-03 silent precedence verified (no warning on combined --vault + --write-into-vault).
</success_criteria>

<output>
After completion, create `.planning/phases/59-vault-cwd-aware-cli-default/59-04-SUMMARY.md` documenting:
- Helper line numbers
- 14 branch insertion points (commit hash, file:line)
- Coexistence with --allow-vault-write verified on harness/import-harness
</output>
