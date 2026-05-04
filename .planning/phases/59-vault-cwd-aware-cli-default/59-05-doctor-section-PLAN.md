---
phase: 59-vault-cwd-aware-cli-default
plan: 05
type: tdd
wave: 3
depends_on: [59-01, 59-02, 59-03, 59-04]
files_modified:
  - tests/test_vault_cwd.py
  - graphify/doctor.py
autonomous: true
requirements: [VCWD-05]
nyquist_compliant: true
must_haves:
  truths:
    - "`graphify doctor` always emits a `[vault-cwd]` section, regardless of CWD state."
    - "Section reports exactly one of three outcomes: auto-adopt (with profile path), refuse (with override hint), or n/a (CWD is not a vault)."
    - "Doctor's prediction matches the runtime gate's behavior for the same CWD inputs (parity contract)."
    - "GRAPHIFY_VAULT env pin is treated as explicit routing by both runtime gate and doctor (cross-cutting)."
    - "`--vault-list` argument is treated as explicit routing by both runtime gate and doctor (cross-cutting)."
  artifacts:
    - path: "graphify/doctor.py"
      provides: "_classify_vault_cwd helper + new format_report() section emitting [vault-cwd] line"
      contains: "[vault-cwd]"
  key_links:
    - from: "graphify/doctor.py:_classify_vault_cwd"
      to: "graphify/output.py:is_obsidian_vault"
      via: "import + Path.cwd().resolve() check"
      pattern: "is_obsidian_vault"
    - from: "graphify/doctor.py:format_report"
      to: "_classify_vault_cwd"
      via: "section append after [Vault Detection]"
      pattern: "\\[graphify\\] === Vault-CWD Default ==="
---

<objective>
VCWD-05 + cross-cutting: extend `graphify/doctor.py:format_report()` with a new `[graphify] === Vault-CWD Default ===` section that uses a pure read-only classifier (`_classify_vault_cwd`) sharing identical predicates with the runtime gate. Also add cross-cutting tests for `GRAPHIFY_VAULT` and `--vault-list` (both treated as explicit routing on both the runtime and doctor sides).

Purpose: Closes VCWD-05 acceptance + RESEARCH cross-cutting tests + parity contract.
Output: `_classify_vault_cwd` helper, doctor section, 3 VCWD-05 tests + 2 cross-cutting tests = 5 RED→GREEN test rows.
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
@.planning/phases/59-vault-cwd-aware-cli-default/59-04-SUMMARY.md
@graphify/doctor.py
@graphify/output.py
@tests/test_vault_cwd.py
@tests/test_doctor.py

<interfaces>
From graphify/doctor.py:
```python
def format_report(report: DoctorReport) -> str:                      # 514
    # Existing sections ordered:
    #   [graphify] === Vault Detection ===                            (523)
    #   [graphify] === Profile Validation ===                         (530)
    #   [graphify] === Output Destination ===                         (540)
    #   [graphify] === Ignore-List ===                                (552)
    #   [graphify] === Recommended Fixes ===                          (571)
    # Phase 59.1 will add `[graphify] === Version Sync ===` after current end.
    # Phase 59 inserts `[graphify] === Vault-CWD Default ===` AFTER Recommended Fixes
    # and BEFORE the Phase 59.1 version-sync section (which already merged at HEAD —
    # verify exact insertion point by reading format_report() at execution time).

# is_obsidian_vault is already imported at line 40.
```

From graphify/output.py:
```python
def resolve_vault_for_parity(cwd, *, explicit_vault=None, vault_list_file=None) -> dict:  # 215
    """Returns {'source', 'profile_path', 'vault_root', 'warnings', ...}."""
```
</interfaces>
</context>

<tasks>

<task type="tdd" tdd="true">
  <name>Task 1 (RED): Add VCWD-05 + cross-cutting tests (5 rows)</name>
  <files>tests/test_vault_cwd.py</files>
  <behavior>
    - All 5 tests FAIL: doctor lacks `[vault-cwd]` section; cross-cutting tests fail because helper does not yet honor env+vault-list as explicit routing in doctor parity (runtime side already correct from Plan 02).
  </behavior>
  <read_first>
    - tests/test_vault_cwd.py
    - graphify/doctor.py:514+ format_report() body
    - .planning/phases/59-vault-cwd-aware-cli-default/59-CONTEXT.md (Decision 5)
  </read_first>
  <action>
Append to `tests/test_vault_cwd.py`:

```python
def _doctor_section_lines(stdout: str) -> list[str]:
    """Extract just the [vault-cwd] lines from doctor output."""
    return [ln for ln in stdout.splitlines() if ln.startswith("[vault-cwd]")]


def test_doctor_vault_cwd_section_always_shown(tmp_path):
    """VCWD-05: doctor [vault-cwd] section appears for non-vault CWD too (n/a outcome)."""
    plain = _make_no_vault(tmp_path)
    proc = _graphify("doctor", cwd=str(plain))
    assert proc.returncode == 0, f"doctor failed: {proc.stderr}"
    section_lines = _doctor_section_lines(proc.stdout)
    assert section_lines, f"missing [vault-cwd] section in doctor output:\n{proc.stdout}"
    assert any("n/a" in ln for ln in section_lines), (
        f"non-vault CWD should yield n/a outcome; got: {section_lines}"
    )


def test_doctor_three_outcomes(tmp_path):
    """VCWD-05: all three outcomes (auto-adopt / refuse / n/a) reachable."""
    pytest.importorskip("yaml")

    # n/a
    plain = _make_no_vault(tmp_path / "noVault")
    p1 = _graphify("doctor", cwd=str(plain))
    # auto-adopt
    full = _make_partial_vault(tmp_path / "fullVault", with_profile=True)
    p2 = _graphify("doctor", cwd=str(full))
    # refuse
    bare = _make_partial_vault(tmp_path / "bareVault", with_profile=False)
    p3 = _graphify("doctor", cwd=str(bare))

    s1 = " ".join(_doctor_section_lines(p1.stdout))
    s2 = " ".join(_doctor_section_lines(p2.stdout))
    s3 = " ".join(_doctor_section_lines(p3.stdout))
    assert "n/a" in s1, f"plain dir → n/a expected; got: {s1!r}"
    assert "auto-adopt" in s2, f"vault+profile → auto-adopt expected; got: {s2!r}"
    assert "refuse" in s3, f"vault-no-profile → refuse expected; got: {s3!r}"


def test_doctor_runtime_parity(tmp_path):
    """VCWD-05 parity contract: doctor's prediction matches runtime gate behavior."""
    # refuse case
    bare = _make_partial_vault(tmp_path, with_profile=False)
    doctor = _graphify("doctor", cwd=str(bare))
    runtime = _graphify("run", cwd=str(bare))
    doc_section = " ".join(_doctor_section_lines(doctor.stdout))
    assert "refuse" in doc_section
    assert runtime.returncode == 2 and "refusing to write" in runtime.stderr, (
        f"doctor predicted refuse; runtime should refuse. runtime stderr:\n{runtime.stderr}"
    )


def test_env_pin_disables_gate(tmp_path):
    """Cross-cutting: GRAPHIFY_VAULT env pin treated as explicit routing — gate returns n/a."""
    pytest.importorskip("yaml")
    bare = _make_partial_vault(tmp_path / "bareVault", with_profile=False)
    pin_target = _make_partial_vault(tmp_path / "pinVault", with_profile=True)
    proc = _graphify(
        "run", "--help",
        cwd=str(bare),
        env={"GRAPHIFY_VAULT": str(pin_target)},
    )
    assert "refusing to write" not in proc.stderr, (
        f"GRAPHIFY_VAULT pin should suppress VCWD-03; got:\n{proc.stderr}"
    )
    # Doctor parity: with env pin set, [vault-cwd] should report n/a (explicit route wins).
    proc_doc = _graphify(
        "doctor",
        cwd=str(bare),
        env={"GRAPHIFY_VAULT": str(pin_target)},
    )
    section = " ".join(_doctor_section_lines(proc_doc.stdout))
    assert "n/a" in section, f"doctor parity broken with env pin: {section!r}"


def test_vault_list_disables_gate(tmp_path):
    """Cross-cutting: --vault-list file treated as explicit routing — gate returns n/a."""
    pytest.importorskip("yaml")
    bare = _make_partial_vault(tmp_path / "bareVault", with_profile=False)
    pin_target = _make_partial_vault(tmp_path / "pinVault", with_profile=True)
    list_file = tmp_path / "vaults.txt"
    list_file.write_text(f"{pin_target}\n", encoding="utf-8")
    proc = _graphify(
        "--vault-list", str(list_file), "run", "--help",
        cwd=str(bare),
    )
    assert "refusing to write" not in proc.stderr, (
        f"--vault-list should suppress VCWD-03; got:\n{proc.stderr}"
    )
```

Commit message: `test(59-05): RED — VCWD-05 doctor [vault-cwd] section + parity + env/vault-list cross-cutting`
  </action>
  <acceptance_criteria>
    - 5 new tests collectable.
    - `pytest tests/test_vault_cwd.py -k "doctor or env_pin or vault_list" -x` exits non-zero (RED).
    - Commit prefix `test(59-05): RED`.
  </acceptance_criteria>
  <verify>
    <automated>pytest tests/test_vault_cwd.py -k "doctor or env_pin or vault_list" -x; test $? -ne 0 && echo "RED CONFIRMED"</automated>
  </verify>
  <done>5 RED tests added; all fail.</done>
</task>

<task type="tdd" tdd="true">
  <name>Task 2 (GREEN): Add _classify_vault_cwd helper + [vault-cwd] section in format_report</name>
  <files>graphify/doctor.py</files>
  <behavior>
    - All 5 tests PASS.
    - Doctor section is emitted unconditionally and always reports exactly one outcome.
    - Doctor honors `GRAPHIFY_VAULT` env and `--vault-list` arg as explicit routing → outcome `n/a`.
    - Parity test confirms doctor's prediction matches runtime gate's behavior.
  </behavior>
  <read_first>
    - graphify/doctor.py:514–600 (format_report body to find insertion point)
    - graphify/output.py:215 resolve_vault_for_parity signature
    - tests/test_doctor.py (existing doctor tests — ensure no regression patterns)
  </read_first>
  <action>
**Step 1 — Add the classifier helper to `graphify/doctor.py` (above format_report):**

```python
def _classify_vault_cwd(
    cwd: Path,
    *,
    explicit_vault: Path | None = None,
    vault_list_file: Path | None = None,
) -> tuple[str, Path | None]:
    """Pure read-only VCWD-05 classifier — never raises, never emits stderr.

    Returns (outcome, profile_path) where outcome ∈ {"auto-adopt", "refuse", "n/a"}.
    Mirrors `graphify/__main__.py:_check_vault_cwd_gate` logic exactly to satisfy
    the parity contract."""
    cwd_r = cwd.resolve()
    if not is_obsidian_vault(cwd_r):
        return ("n/a", None)
    # Explicit route: env pin OR --vault OR --vault-list each count as explicit.
    explicit_route = bool(
        explicit_vault
        or vault_list_file
        or (os.environ.get("GRAPHIFY_VAULT") or "").strip()
    )
    if explicit_route:
        return ("n/a", None)
    profile = cwd_r / ".graphify" / "profile.yaml"
    if profile.is_file():
        return ("auto-adopt", profile)
    return ("refuse", None)
```

(`os` import already in doctor.py — confirm; add if missing.)

**Step 2 — Add the section to `format_report` AFTER the existing `[Recommended Fixes]` section and BEFORE any Phase 59.1 `[Version Sync]` section:**

```python
# Locate the line right after `lines.append("[graphify] === Recommended Fixes ===")`
# and the recommended-fixes content block, then insert:

lines.append("")
lines.append("[graphify] === Vault-CWD Default ===")
_outcome, _profile = _classify_vault_cwd(
    Path.cwd(),
    explicit_vault=getattr(report, "explicit_vault", None),
    vault_list_file=getattr(report, "vault_list_file", None),
)
_cwd_str = str(Path.cwd().resolve())
if _outcome == "auto-adopt":
    _profile_rel = _profile.relative_to(Path.cwd().resolve()) if _profile else Path(".graphify/profile.yaml")
    lines.append(
        f"[vault-cwd] auto-adopt — vault at {_cwd_str}, profile: {_profile_rel}"
    )
elif _outcome == "refuse":
    lines.append(
        f"[vault-cwd] refuse — vault at {_cwd_str}, no .graphify/profile.yaml (override: --write-into-vault)"
    )
else:
    lines.append(f"[vault-cwd] n/a — {_cwd_str} is not an Obsidian vault")
```

**Wording (locked in CONTEXT D-05) — verbatim:**
- `[vault-cwd] auto-adopt — vault at <cwd>, profile: <relative-path-to-profile>`
- `[vault-cwd] refuse — vault at <cwd>, no .graphify/profile.yaml (override: --write-into-vault)`
- `[vault-cwd] n/a — <cwd> is not an Obsidian vault`

(Em-dash `—` U+2014, not hyphen.)

**Step 3 — Pass explicit_vault and vault_list_file from `run_doctor()` to `format_report()` (or thread via DoctorReport).** Read `graphify/doctor.py` for the existing `DoctorReport` shape; if it does not carry these fields, either (a) add them, or (b) re-derive inside `_classify_vault_cwd` from `os.environ.get("GRAPHIFY_VAULT")` only and accept that doctor cannot see argv-level `--vault`/`--vault-list` flags. Per CONTEXT D-05 parity contract, doctor MUST see the same routing flags the user passed — confirm at execution time which path the existing code uses.

**Recommended path (least invasive):** Read `graphify/__main__.py` doctor branch (~2965+) — it already calls `_resolve_cli_paths(...)` with the doctor's own `_lv_dr`/`_lv_dr2` strip outputs. Pass those as keyword args into `run_doctor()` or directly into `_classify_vault_cwd` via `DoctorReport`. The exact threading mechanism is executor's discretion — the parity test is the gate.

**Step 4 — Cross-cutting parity for runtime gate.** Plan 02 already wired `GRAPHIFY_VAULT` and `--vault-list` into `has_explicit_route`. No additional runtime-side changes needed; the cross-cutting tests pass once doctor reflects the same flags.

Commit message: `feat(59-05): GREEN — doctor [vault-cwd] section + parity with runtime gate`
  </action>
  <acceptance_criteria>
    - `pytest tests/test_vault_cwd.py -k "doctor or env_pin or vault_list" -x -q` PASSES (5 tests).
    - `grep -v '^#' graphify/doctor.py | grep -c "_classify_vault_cwd"` >= 2 (def + call site).
    - `grep -v '^#' graphify/doctor.py | grep -c '\[vault-cwd\]'` >= 3 (one per outcome).
    - `grep -n "=== Vault-CWD Default ===" graphify/doctor.py | wc -l` == 1 (header appears exactly once).
    - Em-dash `—` (U+2014) present in doctor output: `python -c "from graphify.doctor import format_report; print('—' in open('graphify/doctor.py').read())"` outputs `True`.
    - `pytest tests/test_doctor.py -q` passes (no regression).
    - `pytest tests/ -q` exits 0; suite ≥ 2123 + 16 (Plans 01–05 cumulative new tests).
  </acceptance_criteria>
  <verify>
    <automated>pytest tests/test_vault_cwd.py -k "doctor or env_pin or vault_list" -x -q && pytest tests/test_doctor.py -q && pytest tests/ -q</automated>
  </verify>
  <done>VCWD-05 + cross-cutting fully wired; 5 tests green; full suite green; phase complete.</done>
</task>

<task type="tdd" tdd="true">
  <name>Task 3 (REFACTOR + Phase Gate): Final suite run, summary, retrospective notes</name>
  <files>tests/test_vault_cwd.py, graphify/__main__.py, graphify/doctor.py</files>
  <behavior>
    - All 17 VCWD test rows + 2 cross-cutting + regressions pass.
    - No grep-self-invalidation artifacts (any header prose containing trigger tokens has `# ` comments).
  </behavior>
  <read_first>
    - All Plan 01–05 SUMMARY files (after they exist)
    - graphify/__main__.py:_check_vault_cwd_gate (final form)
    - graphify/doctor.py:_classify_vault_cwd (final form)
  </read_first>
  <action>
**Refactor sweep:**

1. Confirm helper docstrings reference `VCWD-01..04` (gate) and `VCWD-05` (classifier) for traceability.
2. Verify the gate helper and the classifier helper share IDENTICAL predicate ordering for the parity contract:
   - `is_obsidian_vault(cwd)` first
   - explicit route check (env+args) second
   - profile-exists check third
   - write_into_vault opt-in fourth (gate only)
3. Run final full-suite verification.
4. If any header docstring or comment in `__main__.py` or `doctor.py` repeats refusal phrases (e.g. `"refusing to write"`), prefix with `# ` so grep gates filter via `grep -v '^#'` cleanly.

Commit message: `refactor(59-05): REFACTOR — confirm parity predicate ordering, doc cleanup`
  </action>
  <acceptance_criteria>
    - `pytest tests/ -q` exits 0; suite count is exactly the baseline (2123) + 17 new VCWD tests = 2140 minimum (additional cross-cutting may push it to 2142).
    - `grep -nE "(VCWD-0[1-5])" graphify/__main__.py graphify/doctor.py | wc -l` >= 5.
    - Final commit hash recorded in 59-05-SUMMARY.md.
  </acceptance_criteria>
  <verify>
    <automated>pytest tests/ -q</automated>
  </verify>
  <done>Phase 59 complete; all 5 VCWD requirements green; suite green; ready for /gsd-verify-work.</done>
</task>

</tasks>

<threat_model>
## Trust Boundaries

| Boundary | Description |
|----------|-------------|
| CWD path → doctor stdout | Resolved CWD interpolated into doctor section |
| GRAPHIFY_VAULT env value → classifier | env-supplied path used to decide explicit-route boolean |

## STRIDE Threat Register

| Threat ID | Category | Component | Disposition | Mitigation Plan |
|-----------|----------|-----------|-------------|-----------------|
| T-59-10 | Information Disclosure | doctor stdout printing CWD/profile path | accept | Doctor is a user-invoked diagnostic; user's own paths are within the trust boundary. |
| T-59-11 | Spoofing | Maliciously constructed `.graphify/profile.yaml` triggering false auto-adopt outcome in doctor | accept | Classifier checks `is_file()` only — does NOT load YAML. No code execution path. |
| T-59-12 | Repudiation | Doctor predicts one outcome; runtime executes another (parity break) | mitigate | `test_doctor_runtime_parity` enforces parity; identical predicate ordering enforced in REFACTOR step. |
</threat_model>

<verification>
- 5 VCWD-05 + cross-cutting tests green.
- All 17 VCWD test rows from VALIDATION.md pass.
- Full suite green; baseline + 17 new tests.
- Doctor output ordering: `[Vault Detection]` → ... → `[Recommended Fixes]` → `[Vault-CWD Default]` → (Phase 59.1 `[Version Sync]` if present).
</verification>

<success_criteria>
- ROADMAP success criterion 1 (closed): `[vault-cwd]` section reports prediction; matches runtime.
- All 5 VCWD requirements (VCWD-01..05) are testable, tested, and green.
- Phase 59 ships: ready for `/gsd-verify-work 59`.
</success_criteria>

<output>
After completion, create `.planning/phases/59-vault-cwd-aware-cli-default/59-05-SUMMARY.md` documenting:
- _classify_vault_cwd line in doctor.py
- format_report insertion point line
- Final test count delta
- Parity test invocation as the canonical regression guard
</output>
