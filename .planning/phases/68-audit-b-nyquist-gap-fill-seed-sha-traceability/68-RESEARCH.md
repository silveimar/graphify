# Phase 68: AUDIT-B — Nyquist Gap-Fill & Seed-SHA Traceability — Research

**Researched:** 2026-05-06
**Domain:** Forensic audit — git history, test discovery, pyproject.toml marker registration, planning document surgery
**Confidence:** HIGH (all claims verified from git log, grep, and direct file reads in this session)

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

**D-01 Closure script form — Python + pytest marker**
`scripts/audit_b_closure.py` drives pytest by collecting tests tagged with `@pytest.mark.audit_v112`, then runs them and exits non-zero on any failure. Tests cited in `v1.12-VALIDATION.md` MUST carry this marker. Script performs `pytest -m audit_v112 --collect-only` cross-check to guarantee marker set matches citation list (no drift). Exit codes: 0 = all green, 1 = test failure, 2 = citation/marker drift.

**D-02 VALIDATION.md placement — single consolidated file**
All 5 retroactive entries live in `.planning/milestones/v1.12-VALIDATION.md`. Do NOT resurrect per-phase directories under `.planning/phases/`. Per-phase section schema (locked):
```
## Phase {N}: {name}
- **Implementing SHA:** {sha}
- **Asserting test:** {path}::{node_id}
- **Marker:** @pytest.mark.audit_v112
- **Re-run command:** `python scripts/audit_b_closure.py`
- **Status:** PASS @ {date} on {sha}
```

**D-03 Seed annotation format — inline parenthetical (extend existing pattern)**
- `SEED-001` → v1.9
- `SEED-002` → v1.4
- `SEED-vault-root-aware-cli` → v1.12 + v1.13 (Option B closes remaining 20% in Phase 63)
- `SEED-bidirectional-concept-code-links` → v1.10 / v1.11 / v1.13 (CCONF, CFED, CDRIFT, CQUERY close remaining 35% in phases 65–67)
Mirror annotations in REQUIREMENTS.md. No new traceability table.

**D-04 Identifying implementing SHA + asserting test path**
Researcher uses `git log --oneline --all` filtered by phase prefixes. Asserting test = the single test most directly asserting the phase's headline success criterion. One per phase.

**D-05 Closure on v1.12 audit items**
After 5 VALIDATION.md sections land and closure script runs green, edit `.planning/MILESTONES.md` to mark every v1.12-deferred audit item resolved. The MILESTONE-AUDIT.md "Proceed to /gsd-complete-milestone v1.12" closure path becomes runnable.

### Claude's Discretion
None listed.

### Deferred Ideas (OUT OF SCOPE)
Generalizing the `audit_v{milestone}` marker pattern as a reusable retroactive-audit primitive for future milestones.
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| AUDIT-01 | Nyquist VALIDATION.md gap-fill for v1.12 phases 59, 59.1, 60, 60.1, 61 — each entry cites implementing SHA and asserting test path; closure script re-runs cited tests | SHA forensics in §Forensic Deliverables; asserting tests in same section |
| AUDIT-03 | Retroactive seed-SHA traceability — REQUIREMENTS.md and PROJECT.md annotated with milestone that consumed each seed | Exact current text and patched form in §SEED Annotation Targets |
</phase_requirements>

---

## Summary

Phase 68 is a pure documentation and test-infrastructure phase — no new source code in `graphify/`. Three concrete deliverables are required:

1. A consolidated `.planning/milestones/v1.12-VALIDATION.md` with one section per phase (59, 59.1, 60, 60.1, 61), each citing the implementing SHA (verified from git log) and the asserting test path (verified from test discovery).
2. `scripts/audit_b_closure.py` — a self-contained Python script that runs `pytest -m audit_v112` over the 5 cited tests and performs a collect-only cross-check.
3. Surgical inline-parenthetical annotations to 4 SEED bullets in `REQUIREMENTS.md` and `PROJECT.md`, plus a new v1.12 entry in `MILESTONES.md` marking the deferred items resolved.

All forensic evidence was verified in this session via `git log`, `grep`, and direct file reads. No assumptions about SHA or test paths.

**Primary recommendation:** Write `v1.12-VALIDATION.md` first (blocking for D-01 closure script), then add the pytest marker `@pytest.mark.audit_v112` to the 5 asserting tests, then write the closure script, then patch SEED annotations and MILESTONES.md.

---

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Closure script (`scripts/audit_b_closure.py`) | CLI / scripts layer | — | Drives pytest subprocess; no graphify source coupling |
| pytest marker registration | pyproject.toml config | — | `[tool.pytest.ini_options].markers` silences PytestUnknownMarkWarning |
| `v1.12-VALIDATION.md` entries | Planning docs | — | Audit artifact; lives alongside v1.12-ROADMAP.md |
| SEED annotations | Planning docs | — | Inline surgery to REQUIREMENTS.md and PROJECT.md |
| MILESTONES.md v1.12 entry | Planning docs | — | v1.12 section is currently absent; must be created |

---

## Forensic Deliverables

### Phase 59: Vault-CWD-aware CLI default

**Requirements satisfied:** VCWD-01, VCWD-02, VCWD-03, VCWD-04, VCWD-05

**Implementing SHA:** `5eb2c17`
Verified from: `git log --oneline --all | grep "feat(59-"` — the last (most recent) feat commit for phase 59 is:
```
5eb2c17 feat(59-05): GREEN — doctor [vault-cwd] section + parity with runtime gate
```
This is the commit that closed the last plan of Phase 59 (59-05-doctor-section-PLAN.md, VCWD-05 — the headline success criterion requires the doctor section and runtime parity to be verified together). [VERIFIED: git log]

**Asserting test:** `tests/test_vault_cwd.py::test_refusal_exit_code_and_format`
Rationale: VCWD-03 (exit 2 + two-line format) is the phase's most mechanically assertive criterion — it specifies exact exit code and exact stderr format. `test_refusal_exit_code_and_format` (line 215 in `tests/test_vault_cwd.py`) directly asserts both. `test_doctor_runtime_parity` (line 369) is a close second but tests VCWD-05 parity; VCWD-03 is the headline gate. [VERIFIED: grep -n "def test_" tests/test_vault_cwd.py]

**Full commit chain for Phase 59 (chronological):**
```
32a9b48 feat(59-01): GREEN — VCWD-01 dispatch gate wired across 14 commands
42dcf49 feat(59-02): GREEN — VCWD-02 auto-adopt routes via _resolve_cli_paths(explicit_vault=cwd)
58b7c7f feat(59-03): GREEN — VCWD-03 refusal uses sanitized cwd, exit 2, verbatim two-line text
a4ab3c2 feat(59-04): GREEN — VCWD-04 --write-into-vault global+per-command, suppresses refusal only
5eb2c17 feat(59-05): GREEN — doctor [vault-cwd] section + parity with runtime gate
```

---

### Phase 59.1: Version sync hygiene and --version flag

**Requirements satisfied:** VSYNC-01, VSYNC-02, VSYNC-03, VSYNC-04

**Implementing SHA:** `671045f`
Verified from: `git log --oneline --all | grep "feat(59.1-"` — the last feat commit for Phase 59.1 is:
```
671045f feat(59.1-03): add 'version sync' section to graphify doctor (VSYNC-03)
```
This closes VSYNC-03, the final plan (59.1-03). [VERIFIED: git log]

**Asserting test:** `tests/test_version_sync.py::test_heal_happy_path_silent`
Rationale: VSYNC-01 (silent auto-self-heal, the phase's headline behavioral change — silencing a persistent per-command warning) is the most user-facing success criterion. `test_heal_happy_path_silent` (line 25 in `tests/test_version_sync.py`) directly asserts the stamp is healed and no stderr output is produced. [VERIFIED: grep -n "def test_" tests/test_version_sync.py]

**Full commit chain for Phase 59.1 (chronological):**
```
bb9eace feat(59.1-02): silent auto-self-heal of skill stamp on drift (VSYNC-01, VSYNC-04)
c0ab5dc feat(59.1-03): multi-line graphify --version output (VSYNC-02)
671045f feat(59.1-03): add 'version sync' section to graphify doctor (VSYNC-03)
```
Note: There are two commits labeled `feat(59.1-03)` — the plan had two atomic changes. The second (671045f) is the final implementing SHA.

---

### Phase 60: Milestone-level E2E integration tests

**Requirements satisfied:** E2E-01, E2E-02

**Implementing SHA:** `b6378b9`
Verified from: `git log --oneline --all | grep "feat(60-"`:
```
b6378b9 feat(60-02): GREEN — test_e2e_elicit_then_update_vault passes
```
This is the last feat commit for Phase 60 (Plan 60-02, E2E-02). [VERIFIED: git log]

**Asserting test:** `tests/test_e2e_integration.py::test_e2e_elicit_then_update_vault`
Rationale: E2E-02 (elicit → sidecar → update-vault pipeline) is the more complex of the two E2E tests and directly validates the headline multi-phase integration that was the audit gap. `test_e2e_elicit_then_update_vault` (line 291 in `tests/test_e2e_integration.py`) asserts this end-to-end chain. E2E-01 (`test_e2e_compose_override_ladder`, line 219) is equally valid but was already GREEN before Phase 60 closed Phase 60.1's RED gate (APPLY-DET-01 flipped it GREEN retroactively — see Phase 60.1 below). Either test can serve, but E2E-02 is the cleaner headline assertor. [VERIFIED: grep -n "def test_" tests/test_e2e_integration.py]

**Full commit chain for Phase 60:**
```
b6378b9 feat(60-02): GREEN — test_e2e_elicit_then_update_vault passes
```
(Phase 60-01 has no standalone feat commit — E2E-01 was made GREEN by Phase 60.1's Leiden seeding fix.)

---

### Phase 60.1: update-vault apply determinism fix

**Requirements satisfied:** APPLY-DET-01

**Implementing SHA:** `a96435a`
Verified from: `git log --oneline --all | grep "60.1"`:
```
e110ead fix(60.1-01): seed graspologic leiden with random_seed=42 for cross-process determinism
a96435a fix(60.1-03): honor note_type_templates.thing over CODE-note default in topology fallback
```
The root cause fix (Leiden seeding) is `e110ead`, but APPLY-DET-01 criterion 3 (Phase 60 E2E test must turn GREEN) required the additional render-ladder fix in `a96435a` — confirmed by `docs(60.1-03)` commit `29e6564` stating "APPLY-DET-01 closed, all 4 sub-criteria green". The last code commit that completed the success criterion is `a96435a`. [VERIFIED: git log]

**Asserting test:** `tests/test_cluster.py::test_cluster_is_deterministic_across_runs`
Rationale: This test (line 79, `tests/test_cluster.py`) was written in Phase 60.1 explicitly to guard against Leiden non-determinism — its docstring states "Guards against Leiden non-determinism (root cause of update-vault apply plan_id flicker — see Phase 60.1 / APPLY-DET-01)". It is the direct unit assertor of the implementing fix (`random_seed=42` in `cluster.py:_partition`). [VERIFIED: sed -n '79,100p' tests/test_cluster.py]

Alternative: `tests/test_e2e_integration.py::test_e2e_update_vault_auto_adopts_vault_cwd` (line 370) also validates APPLY-DET-01 determinism under auto-adopt (plan_id_1 == plan_id_2 assertion at line 437). Either is acceptable; the cluster unit test is more focused.

**Full commit chain for Phase 60.1 (chronological):**
```
e110ead fix(60.1-01): seed graspologic leiden with random_seed=42 for cross-process determinism
a96435a fix(60.1-03): honor note_type_templates.thing over CODE-note default in topology fallback
```

---

### Phase 61: Harness vault-write error format normalization

**Requirements satisfied:** HARN-FMT-01

**Implementing SHA:** `2413f18`
Verified from: `git log --oneline --all | grep "feat(61-"`:
```
2413f18 feat(61-01): GREEN — migrate harness vault-write refusal to _emit_vault_error two-line format
```
Single-plan phase; this is the only implementing commit. [VERIFIED: git log]

**Asserting test:** `tests/test_harness_import.py::test_import_refuses_vault_rooted_output`
Rationale: `test_import_refuses_vault_rooted_output` (line 125, `tests/test_harness_import.py`) asserts the harness vault-write refusal emits the two-line `[graphify] error:` + `  hint:` format — the headline HARN-FMT-01 requirement. The Phase 61 CONTEXT states "Existing tests asserting the old stderr substring updated to match the new shape; one-line variant removed entirely." This test is the asserting owner after that migration. [VERIFIED: grep -n "def test_" tests/test_harness_import.py]

---

## Standard Stack

No new library dependencies. All tooling is already present. [VERIFIED: pyproject.toml, pytest --version]

| Tool | Version | Purpose |
|------|---------|---------|
| pytest | 8.4.2 | Test runner; marker support built-in |
| Python | 3.10 (CI also: 3.12) | Closure script runtime |
| subprocess / sys | stdlib | Closure script runs pytest as subprocess |

---

## Architecture Patterns

### Closure Script Architecture

```
scripts/audit_b_closure.py
│
├── Step 1: pytest --collect-only -m audit_v112  → collect list of marked tests
├── Step 2: Compare collected set against citation_list (hardcoded 5 test IDs)
│           → mismatch: exit 2 (citation/marker drift)
├── Step 3: pytest -m audit_v112 -v              → run marked tests
│           → any failure: exit 1
└── Step 4: All pass                             → exit 0
```

The script is self-contained Python with no shell dependency. It invokes pytest via `subprocess.run(["python", "-m", "pytest", ...])` using `sys.executable` to guarantee the same interpreter.

### pyproject.toml Marker Registration

**Current state:** `[tool.pytest.ini_options]` section does NOT exist in `pyproject.toml`. [VERIFIED: grep -n "^\[" pyproject.toml confirmed sections are: build-system, project, project.urls, project.optional-dependencies, project.scripts, tool.setuptools.packages.find, tool.setuptools.package-data]

**Addition required:** A new `[tool.pytest.ini_options]` section must be appended:

```toml
[tool.pytest.ini_options]
markers = [
    "audit_v112: retroactive Nyquist validation marker for v1.12 phases (59, 59.1, 60, 60.1, 61)",
]
```

**Why required:** pytest 8.x emits `PytestUnknownMarkWarning` for unregistered markers. When running `pytest -m audit_v112`, unregistered markers do NOT cause an error — they silently collect 0 tests (confirmed by live test: `collected 1 item / 1 deselected / 0 selected`). This makes the closure script's collect-only cross-check essential: it would detect 0 tests even when markers are not applied to tests yet.

**Pitfall confirmed:** Without the marker on test functions, `-m audit_v112` collects 0 tests even if the marker is registered. The marker must be both (a) registered in pyproject.toml AND (b) applied with `@pytest.mark.audit_v112` to each asserting test function.

### Existing Marker Conflicts

**None.** A thorough grep of all test files for `@pytest.mark.` (excluding `parametrize`, `skipif`, `skip`, `xfail`, `timeout`, `usefixtures`) returned no results. [VERIFIED: grep -rn "@pytest.mark\|pytest.mark\." tests/ with exclusions]

None of the 5 candidate test functions carry any custom markers currently.

---

## SEED Annotation Targets

### REQUIREMENTS.md

**Current text (line 58):**
```
- [ ] **AUDIT-03**: Retroactive seed-SHA traceability — REQUIREMENTS.md and PROJECT.md are annotated with the milestone that consumed each seed (SEED-001 → v1.9, SEED-002 → v1.4, SEED-vault-root-aware-cli → v1.12 + v1.13 closes Option B, SEED-bidirectional-concept-code-links → v1.10 / v1.11 / v1.13 closes remainder).
```
This checkbox needs to be flipped from `[ ]` to `[x]` when Phase 68 ships. [VERIFIED: grep -n "SEED" .planning/REQUIREMENTS.md]

**Source seeds section (line 6):**
```
**Source seeds:** SEED-bidirectional-concept-code-links (35% remaining), SEED-vault-root-aware-cli (20% remaining — Option B).
```
D-03 does not require patching this line (it describes v1.13 active seeds, not a traceability annotation). The AUDIT-03 checkbox line IS the traceability annotation for REQUIREMENTS.md.

### PROJECT.md

**Current SEED bullet text (lines 50–53):**
```
- **SEED-001 Tacit-to-Explicit Elicitation Engine** — CONSUMED by **v1.9** (`graphify/elicit.py`, `__main__.py:2671`, ELIC-01..04 phases 39–44).
- **SEED-002 Harness Memory Export** — CONSUMED by **v1.4** (`harness_export.py` Phase 13; `harness_import.py` Phase 40); v1.11 Phase 57 added `--allow-vault-write` gate; v1.12 Phase 61 finalized error UX.
- **SEED-vault-root-aware-cli** — 80% CONSUMED by **v1.12** (VCWD-01..05 Phase 59; argparse fix Phase 62.1). Remaining: silent reroute Option B → scoped into v1.13.
- **SEED-bidirectional-concept-code-links** — 65% CONSUMED by **v1.10/v1.11** (Phase 46 CCODE schema; Phase 53/54 CGRAPH typed edges + `/trace` integration). Remaining 35% (cross-repo identity, per-edge confidence, drift, parameterized queries) → scoped into v1.13.
```
[VERIFIED: grep -n "SEED-001\|SEED-002\|SEED-vault\|SEED-bidir" .planning/PROJECT.md]

**Assessment:** PROJECT.md already has inline parenthetical traceability for all 4 SEEDs. The voice and format match D-03 exactly. The only gap is that SEED-vault-root-aware-cli and SEED-bidirectional-concept-code-links should be updated to reflect v1.13 closure status now that Phase 63 (VOPT) and Phases 65–67 (CCONF, CFED, CDRIFT/CQUERY) have shipped.

**Proposed patches per D-03:**

SEED-vault-root-aware-cli — current says "80% CONSUMED", remaining → v1.13. After Phase 63 shipped, should read "100% CONSUMED":
```
- **SEED-vault-root-aware-cli** — CONSUMED by **v1.12** (VCWD-01..05 Phase 59; argparse fix Phase 62.1) + **v1.13** (Option B silent reroute Phase 63, closes remaining 20%).
```

SEED-bidirectional-concept-code-links — current says "65% CONSUMED", remaining → v1.13. After Phases 65–67 shipped, should read "100% CONSUMED":
```
- **SEED-bidirectional-concept-code-links** — CONSUMED by **v1.10/v1.11** (Phase 46 CCODE schema; Phase 53/54 CGRAPH typed edges + `/trace` integration) + **v1.13** (CCONF per-edge confidence Phase 65, CFED cross-repo federation Phase 66, CDRIFT/CQUERY drift detection + parameterized queries Phase 67 — closes remaining 35%).
```

SEED-001 and SEED-002 lines already reflect their full consumption status and need no change.

**REQUIREMENTS.md mirror:** The AUDIT-03 line at line 58 already lists all 4 SEED→milestone mappings in the checkbox description. Flipping `[ ]` to `[x]` when Phase 68 ships completes the annotation. No additional prose is needed there.

---

## MILESTONES.md — v1.12 Deferred Items and D-05 Scope

### Current state

`MILESTONES.md` **has no v1.12 entry**. The file's current top entry is `## v1.11 Templates, Graph Semantics & Vault Depth (Shipped: 2026-05-03)`. The v1.12 entry was never written. [VERIFIED: grep -n "^## " .planning/MILESTONES.md — sections are v1.11, v1.10, v1.9 … v1.0]

### Deferred items that D-05 closes

From `.planning/milestones/v1.12-MILESTONE-AUDIT.md` closure section (verified by direct read):

The audit `tech_debt` items deferred from v1.12 are:
1. Nyquist VALIDATION.md gap-fill for Phases 59 / 59.1 / 60 / 60.1 / 61
2. SEED-001 / SEED-002 traceability rows in REQUIREMENTS.md
3. Adjacent `print(f"[graphify] {exc}", ...)` at `__main__.py:~2745` (second migration target)
4. HARN-FMT-01 second E2E flow

Items 1 and 2 are within Phase 68 scope. Items 3 and 4 are explicitly NOT in Phase 68 scope (CONTEXT.md Boundaries: "No new graphify source code in `graphify/`"). They remain open.

### D-05 interpretation

D-05 says: "edit `.planning/MILESTONES.md` to mark every v1.12-deferred audit item resolved." Since the v1.12 entry does not exist, the planner must **create a new `## v1.12` section** prepended immediately after the file's `# Milestones` heading (before the v1.11 entry). This section should:
- Record milestone summary (phases, outcome, audit status)
- List the deferred items that are NOW closed (Nyquist gap-fill, SEED traceability) with Phase 68 as the closing agent
- Note remaining open items (items 3 and 4 above) with their current status
- Set audit verdict to resolved for the closed items

---

## Common Pitfalls

### Pitfall 1: pytest -m with no tests collected
**What goes wrong:** `pytest -m audit_v112` returns exit 0 with "0 tests collected" if the marker is registered but not applied to any test function. The closure script MUST perform the `--collect-only` cross-check BEFORE running tests, and exit 2 if the collected count does not match the expected citation list.
**Why it happens:** pytest 8.x silently deselects tests when no test carries the requested marker. No warning at exit level.
**How to avoid:** Closure script step 1 is `pytest --collect-only -m audit_v112 -q`, parse the "X selected" line, compare against hardcoded expected count (5). [VERIFIED: live test with pytest 8.4.2]

### Pitfall 2: PytestUnknownMarkWarning without ini_options section
**What goes wrong:** Without `[tool.pytest.ini_options]` in pyproject.toml, running `pytest -m audit_v112` emits `PytestUnknownMarkWarning`. With `filterwarnings = error` (if added in the future), this becomes an error.
**Why it happens:** pyproject.toml currently has no `[tool.pytest.ini_options]` section at all. [VERIFIED: grep -n "^\[" pyproject.toml]
**How to avoid:** Add the section with the markers list as the first task (Wave 0 or Wave 1).

### Pitfall 3: Phase 60.1 has two implementing commits
**What goes wrong:** Citing only `e110ead` (the Leiden seed fix) as the Phase 60.1 SHA would be incomplete — APPLY-DET-01 criterion 3 required the additional `a96435a` render-ladder fix to turn the Phase 60 E2E test GREEN.
**How to avoid:** The D-02 schema says "Implementing SHA" (singular). Use `a96435a` — the last code commit before the docs(60.1) verification-passed commit (`6eddd83`). Mention `e110ead` as the root-cause fix in the notes. [VERIFIED: git log 60.1 chain]

### Pitfall 4: Phase 59.1 has two commits labeled feat(59.1-03)
**What goes wrong:** Two commits carry the `feat(59.1-03)` prefix: `c0ab5dc` (multi-line --version) and `671045f` (doctor version sync section). Citing `c0ab5dc` would miss VSYNC-03.
**How to avoid:** Use `671045f` — the chronologically last feat commit for the phase. [VERIFIED: git log]

### Pitfall 5: MILESTONES.md v1.12 entry is absent — not just incomplete
**What goes wrong:** Planner looks for a `## v1.12` section to edit. It does not exist; the planner must CREATE the entry, not update it.
**How to avoid:** Plan includes a task to add the `## v1.12` section to MILESTONES.md (prepended after `# Milestones` heading). [VERIFIED: grep "^## " .planning/MILESTONES.md]

---

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest 8.4.2 |
| Config file | `pyproject.toml` (configfile detected by pytest) |
| Quick run command | `python -m pytest -m audit_v112 -v` |
| Full suite command | `pytest tests/ -q` |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| AUDIT-01 | 5 retroactive VALIDATION.md entries exist and cited tests pass | smoke | `python scripts/audit_b_closure.py` | ❌ Wave 0 |
| AUDIT-03 | SEED annotations present in REQUIREMENTS.md + PROJECT.md | manual check | `grep -n "CONSUMED" .planning/PROJECT.md .planning/REQUIREMENTS.md` | n/a |

### Sampling Rate
- **Per task commit:** `python -m pytest -m audit_v112 -v` (5 tests, ~10s)
- **Per wave merge:** `pytest tests/ -q` (full suite)
- **Phase gate:** Full suite green + `python scripts/audit_b_closure.py` exit 0

### Wave 0 Gaps
- [ ] `scripts/audit_b_closure.py` — does not exist yet; must be created
- [ ] `[tool.pytest.ini_options]` section in `pyproject.toml` — does not exist; must be added
- [ ] `@pytest.mark.audit_v112` applied to 5 test functions — marker not yet on any test

*(Existing test infrastructure covers all 5 asserting tests — only the marker application and script creation are gaps)*

---

## Environment Availability

Step 2.6: SKIPPED — Phase 68 is purely documentation + test marker + closure script. No external tools beyond pytest (confirmed present at 8.4.2) are required.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Pytest subprocess invocation | Custom process spawner | `subprocess.run([sys.executable, "-m", "pytest", ...])` | Guarantees same interpreter; handles paths correctly |
| Marker-to-test cross-check | Custom import-and-reflect logic | `pytest --collect-only -m audit_v112 -q` | pytest's own collection is authoritative |

---

## Code Examples

### Closure script skeleton (verified pattern)

```python
# Source: D-01 spec in 68-CONTEXT.md
import subprocess
import sys

CITATION_LIST = [
    "tests/test_vault_cwd.py::test_refusal_exit_code_and_format",
    "tests/test_version_sync.py::test_heal_happy_path_silent",
    "tests/test_e2e_integration.py::test_e2e_elicit_then_update_vault",
    "tests/test_cluster.py::test_cluster_is_deterministic_across_runs",
    "tests/test_harness_import.py::test_import_refuses_vault_rooted_output",
]

def collect_marked() -> list[str]:
    result = subprocess.run(
        [sys.executable, "-m", "pytest", "--collect-only", "-m", "audit_v112", "-q"],
        capture_output=True, text=True
    )
    # Parse collected test IDs from stdout
    ...

def main() -> int:
    collected = collect_marked()
    if set(collected) != set(CITATION_LIST):
        print(f"[audit_b] Citation/marker drift detected", file=sys.stderr)
        return 2
    result = subprocess.run(
        [sys.executable, "-m", "pytest", "-m", "audit_v112", "-v"],
    )
    return 1 if result.returncode != 0 else 0

if __name__ == "__main__":
    sys.exit(main())
```

### pyproject.toml addition (verified — section does not exist yet)

```toml
[tool.pytest.ini_options]
markers = [
    "audit_v112: retroactive Nyquist validation marker for v1.12 phases (59, 59.1, 60, 60.1, 61)",
]
```
Insert at end of `pyproject.toml` (after `[tool.setuptools.package-data]` block). [VERIFIED: pyproject.toml ends at tool.setuptools.package-data]

### Marker application pattern (5 test functions)

```python
# In tests/test_vault_cwd.py, tests/test_version_sync.py, etc.
import pytest

@pytest.mark.audit_v112
def test_refusal_exit_code_and_format(tmp_path):
    ...
```

---

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | `test_import_refuses_vault_rooted_output` is the post-migration assertor for HARN-FMT-01 (test was updated per Phase 61 CONTEXT "existing tests updated to match new shape") | §Forensic Deliverables — Phase 61 | If the test was renamed or replaced, the closure script cites the wrong node_id — detectable by collect-only cross-check |

**All other claims verified via git log, grep, or direct file reads in this session.**

---

## Open Questions

1. **Items 3 and 4 from the v1.12 audit deferred list (MILESTONES.md entry)**
   - What we know: Items 3 (`print(f"[graphify] {exc}")` at `__main__.py:~2745`) and 4 (HARN-FMT-01 second E2E flow) are explicitly OUT of Phase 68 scope.
   - What's unclear: Should the new v1.12 MILESTONES.md entry mark them as "still open" or "out of scope for Phase 68"?
   - Recommendation: Mark them "deferred to future milestone" to preserve audit trail. The MILESTONE-AUDIT.md closure section already documents them — MILESTONES.md can reference that file.

2. **Exact prose style for the new v1.12 MILESTONES.md section**
   - What we know: The v1.11 entry sets the style (phases completed count, test growth, accomplishments, deferred items).
   - What's unclear: Should MILESTONES.md v1.12 entry be written in v1.12's voice (as if written at ship time) or in audit-closure voice?
   - Recommendation: Match v1.11 style — written as if the milestone shipped (because it did, 2026-05-04), with a `### Audit Closure` subsection noting Phase 68 closed the Nyquist and SEED gaps.

---

## Sources

### Primary (HIGH confidence)
- `git log --oneline --all` — all implementing SHAs verified by direct command output
- `grep -n "def test_"` on test files — all asserting test paths and line numbers verified
- Direct reads of `pyproject.toml`, `.planning/milestones/v1.12-MILESTONE-AUDIT.md`, `.planning/REQUIREMENTS.md`, `.planning/PROJECT.md`, `.planning/MILESTONES.md`, `.planning/phases/68-audit-b-nyquist-gap-fill-seed-sha-traceability/68-CONTEXT.md`
- Live pytest run confirming 8.4.2, marker behavior, and configfile detection

### Secondary (MEDIUM confidence)
- `v1.12-MILESTONE-AUDIT.md` closure section — records which items are deferred vs. closed by Phase 62

---

## Metadata

**Confidence breakdown:**
- Implementing SHAs: HIGH — verified from git log output
- Asserting test paths: HIGH — verified from grep + file reads
- pyproject.toml structure: HIGH — verified from direct read + pytest --version
- MILESTONES.md gap: HIGH — verified section list shows no v1.12 entry
- SEED annotation targets: HIGH — current text verified from PROJECT.md and REQUIREMENTS.md

**Research date:** 2026-05-06
**Valid until:** 2026-06-06 (stable domain — git history and test files do not change retroactively)

---

## RESEARCH COMPLETE

**Phase:** 68 — AUDIT-B — Nyquist Gap-Fill & Seed-SHA Traceability
**Confidence:** HIGH

### Key Findings

- All 5 implementing SHAs verified: Phase 59 = `5eb2c17`, Phase 59.1 = `671045f`, Phase 60 = `b6378b9`, Phase 60.1 = `a96435a`, Phase 61 = `2413f18`
- All 5 asserting test paths verified: `test_vault_cwd.py::test_refusal_exit_code_and_format`, `test_version_sync.py::test_heal_happy_path_silent`, `test_e2e_integration.py::test_e2e_elicit_then_update_vault`, `test_cluster.py::test_cluster_is_deterministic_across_runs`, `test_harness_import.py::test_import_refuses_vault_rooted_output`
- `[tool.pytest.ini_options]` section is ABSENT from pyproject.toml — must be created from scratch; no conflicts with existing markers
- MILESTONES.md has NO v1.12 entry — D-05 requires creating one, not editing an existing section
- PROJECT.md already has SEED annotations but SEED-vault-root-aware-cli and SEED-bidirectional need updating to reflect v1.13 closure
- pytest 8.4.2 confirmed; unregistered marker collects 0 tests silently — closure script's collect-only cross-check is critical safety net

### File Created
`.planning/phases/68-audit-b-nyquist-gap-fill-seed-sha-traceability/68-RESEARCH.md`

### Confidence Assessment
| Area | Level | Reason |
|------|-------|--------|
| Implementing SHAs | HIGH | Verified from git log in this session |
| Asserting test paths | HIGH | Verified from grep + file reads |
| pyproject.toml structure | HIGH | Direct read confirmed no ini_options section |
| SEED annotation targets | HIGH | Current text quoted verbatim from files |
| MILESTONES.md gap | HIGH | Section listing confirmed v1.12 absent |

### Open Questions
- Voice/style for new v1.12 MILESTONES.md entry (recommendation: match v1.11 style, add audit-closure subsection)
- Whether to mark items 3 and 4 of the v1.12 deferred list as "deferred to future" or "out of Phase 68 scope"

### Ready for Planning
Research complete. Planner can now create PLAN.md files.
