# Phase 59: Vault-CWD-aware CLI default — Research

**Researched:** 2026-05-04
**Domain:** CLI dispatch / vault detection / output routing (graphify Python CLI)
**Confidence:** HIGH (codebase-internal, all helpers verified at HEAD)

## Summary

Phase 59 wires a CWD-vault-detection gate into the 14 output-producing CLI subcommands of `graphify`. All required infrastructure already exists: `is_obsidian_vault()`, `_emit_vault_error()`, `resolve_execution_paths()`, and a working global-flag-stripping pattern (`_strip_leading_vault_global_argv`). Phase 59 is integration work, not new infrastructure — the planner builds (a) one detection/gate helper that classifies the CWD into one of three states (auto-adopt / refuse / n/a), (b) symmetrical `--write-into-vault` plumbing (global + per-command, via the same pop/strip pattern as `--vault`), (c) call-site insertions at the top of 14 dispatch branches in `__main__.py`, and (d) a new `[vault-cwd]` block in `graphify/doctor.py`'s `format_report()`.

**Primary recommendation:** Add a single helper `_check_vault_cwd_gate(cmd: str, *, has_explicit_route: bool, write_into_vault: bool) -> Literal["auto-adopt","refuse","n/a"]` in `graphify/__main__.py` near the other `_resolve_*` helpers (around line 1480). It performs detection, emits the auto-adopt stderr line, raises `_emit_vault_error()` on refusal, and returns "n/a" otherwise. Each gated `cmd ==` branch calls it once, immediately after argv parsing and `_strip_vault_flags_from_tokens()`. Reuse `resolve_vault_for_parity()` in `doctor.py` to compute the same prediction for VCWD-05.

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

**Decision 1 — Detection scope:** VCWD-01 gate wired before dispatch only for these subcommands:
`run`, `update-vault`, `enrich`, `--obsidian`, `vault-promote`, `import-harness`, `save-result`, `--diagram-seeds`, `--init-diagram-templates`, `--dedup`, `snapshot`, `approve`, `elicit`, `harness`.
Skipped (no gate): `query`, `doctor`, `install`, `hook`, `capability`, `benchmark`, `--validate-profile`, `--version`. Single dispatch helper, no per-command duplication.

**Decision 2 — Auto-adopt UX (VCWD-02):** Single stderr line before dispatch:
`[graphify] auto-adopted vault at <cwd> (profile: .graphify/profile.yaml)`
Tests assert presence on auto-adopt path, absence on explicit-`--vault` path.

**Decision 3 — `--write-into-vault` flag (VCWD-04):** Both leading global flag (alongside `--vault`/`--vault-list` via the `_pop_global_*` pattern at `__main__.py:1397`) AND per-subcommand flag for the 14 gated commands. When combined with `--vault`/`--output`: silent precedence (explicit routing wins, flag is no-op, no warning). Suppresses VCWD-03 only — does NOT bypass VCWD-02 auto-adopt.

**Decision 4 — VCWD-03 refusal copy:**
```
[graphify] error: refusing to write into Obsidian vault at <cwd> — no .graphify/profile.yaml found
  hint: create .graphify/profile.yaml to opt in, pass --output <path> to write outside the vault, or --write-into-vault to override
```
`<cwd>` is resolved absolute path, sanitized via `security.py`. Exit code 2.

**Decision 5 — `doctor` `[vault-cwd]` section (VCWD-05):** New dedicated section (do NOT extend `[vault]`). Always shown, three outcomes:
- `[vault-cwd] auto-adopt — vault at <cwd>, profile: <relative-path-to-profile>`
- `[vault-cwd] refuse — vault at <cwd>, no .graphify/profile.yaml (override: --write-into-vault)`
- `[vault-cwd] n/a — <cwd> is not an Obsidian vault`
Layered after `[vault]` parity block, before Phase 59.1 version-sync output. Parity contract: prediction matches runtime.

### Claude's Discretion
- Implementation site of the gate helper (single helper function vs decorator).
- Whether to introduce a new `tests/test_vault_cwd.py` file or append to `tests/test_vault_cli.py` / `tests/test_main_flags.py`.
- Internal name of the helper (e.g., `_check_vault_cwd_gate`, `_apply_vault_cwd_gate`).
- Whether the per-command `--write-into-vault` flag is parsed via the existing `argparse` blocks (per-command) or via a token-strip helper symmetrical to `_strip_vault_flags_from_tokens()`.

### Deferred Ideas (OUT OF SCOPE)
- TTY-aware quieting of the auto-adopt notice.
- `GRAPHIFY_DISABLE_VCWD=1` env escape hatch.
- Project-wide one-line `[graphify]` error sweep beyond Phase 59 surface.
- Auto-adopt for non-`.obsidian/` markers.
- `--no-vault-cwd` global force-disable flag.
- Changes to `_resolve_output_target()` or `_emit_vault_error()` signatures.
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| VCWD-01 | Detect `.obsidian/` in CWD before dispatch in 14 gated commands; reusable for `doctor` | `is_obsidian_vault()` at `output.py:69` is the detection primitive — already used by `doctor.py:395`. New helper wraps it for use at dispatch time. |
| VCWD-02 | CWD vault + profile + no flags → auto-route via `_resolve_output_target` | `resolve_execution_paths()` at `output.py:178` already handles `--vault $CWD` semantics; pass `Path.cwd()` as `explicit_vault` to reuse identical code path. Auto-adopt notice mirrors `_merge_vault_pins()` stderr pattern at `__main__.py:1471`. |
| VCWD-03 | CWD vault + no profile + no flags → exit 2 with two-line refusal | `_emit_vault_error(msg, hint, *, code=2)` at `output.py:80` produces the exact two-line format. Existing call-site reference at `__main__.py:2724–2728` (harness `--allow-vault-write` guard, Phase 57). |
| VCWD-04 | `--write-into-vault` global + per-command opt-in, silent precedence | Symmetrical pop/strip helper to `_strip_leading_vault_global_argv` (line 1394) + `_strip_vault_flags_from_tokens` (line 1422). Boolean flag, no value. |
| VCWD-05 | `doctor` predicts auto-adopt / refuse / n/a, parity-tested | `resolve_vault_for_parity()` at `output.py:215` already returns the structured dict needed; extend `format_report()` at `doctor.py:514` to add the new section. |
</phase_requirements>

## Project Constraints (from CLAUDE.md)

- Python 3.10+ (CI runs 3.10 + 3.12). `from __future__ import annotations` is mandatory.
- No new required dependencies. Use stdlib only.
- Pure unit tests, no network, no fs side effects outside `tmp_path`.
- All external/error-message-interpolated input passes through `graphify/security.py` (label sanitization, path confinement). The `<cwd>` interpolated into the VCWD-03 message must be sanitized.
- All vault-write refusals MUST use `_emit_vault_error()` (carried forward from Phase 58 / Phase 61 HARN-FMT-01). Do NOT introduce a new error helper.
- `_resolve_output_target()` and `_emit_vault_error()` signatures MUST NOT change.
- GSD workflow enforced: this research feeds directly into `/gsd-plan-phase 59` and `/gsd-execute-phase`.
- TDD mode is enabled — RED → GREEN → REFACTOR per task where applicable.

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| CWD vault detection | `graphify/output.py` (existing `is_obsidian_vault`) | — | Already lives there; phase only consumes. |
| Gate decision (auto/refuse/n/a) | `graphify/__main__.py` (new helper) | — | Decision is dispatcher-local — depends on argv parse state, env, and explicit flags. Must run *between* argv parsing and pipeline call. |
| Auto-adopt routing | `graphify/output.py:resolve_execution_paths` (reused) | `__main__.py` (passes `Path.cwd()` as `explicit_vault`) | No new resolver; PROJECT.md explicitly forbids it. |
| Refusal emission | `graphify/output.py:_emit_vault_error` (reused) | `__main__.py` (call site) | No new error helper. |
| Doctor parity prediction | `graphify/doctor.py:format_report` | `graphify/output.py:resolve_vault_for_parity` (already exists) | Doctor formats; output.py computes. Existing layering preserved. |
| `--write-into-vault` flag plumbing | `graphify/__main__.py` (global pop + per-command strip) | — | Mirrors existing `--vault` flag plumbing exactly. |
| Path sanitization for `<cwd>` interpolation | `graphify/security.py` (existing) | — | Defense-in-depth on user-controlled CWD strings. |

## Standard Stack

### Core (already installed, in-repo)
| Module | Function | Purpose | Why Used |
|--------|----------|---------|----------|
| `graphify/output.py` | `is_obsidian_vault(path)` | CWD `.obsidian/` detection (line 69) | Single source of truth for vault detection — already used by `doctor.py:395`, `output.py:124`, `output.py:282`. |
| `graphify/output.py` | `_emit_vault_error(msg, hint, *, code)` | Two-line refusal (line 80) | Phase 58/61 contract; Phase 57 harness guard already calls this pattern. |
| `graphify/output.py` | `resolve_execution_paths(...)` | Vault-pin-aware output resolution (line 178) | VCWD-02 reuses this with `explicit_vault=Path.cwd()`. |
| `graphify/output.py` | `resolve_vault_for_parity(...)` | Captures resolved state + warnings (line 215) | VCWD-05 doctor uses this — keeps doctor and runtime in sync by construction. |
| `graphify/__main__.py` | `_strip_leading_vault_global_argv` | Pop pre-subcommand globals (line 1394) | Pattern to mirror for `--write-into-vault`. |
| `graphify/__main__.py` | `_strip_vault_flags_from_tokens` | Strip per-command flags (line 1422) | Pattern to mirror per-command. |
| `graphify/__main__.py` | `_merge_vault_pins` | Conflict-with-stderr-note pattern (line 1457) | Reference for "explicit wins, no warning" silent-precedence semantics. |
| `graphify/security.py` | path/label sanitization | Sanitize `<cwd>` in messages | CLAUDE.md mandates all external input pass through this. |

### Stdlib only — no new packages.

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Single gate helper called per branch | Decorator wrapping each command body | Decorator requires refactoring 14 elif blocks into functions — high diff size, low test gain. Stay with helper call. |
| New `tests/test_vault_cwd.py` | Append to `tests/test_vault_cli.py` | New file gives clean phase ownership and easier audit; existing file is already 100 lines and Phase-41-scoped. Recommend new file. |
| Token-strip-style `--write-into-vault` parsing | Add to per-command `argparse` blocks | Token-strip is mechanical and uniform across 14 sites; argparse approach forces 14 individual edits. Recommend token-strip. |

## Architecture Patterns

### System Architecture Diagram

```
graphify <flags> <cmd> <args>
         │
         ▼
   _strip_leading_vault_global_argv  →  g_vault_exp, g_vault_list
   _pop_global_write_into_vault       →  g_write_into_vault   ← NEW (mirrors above)
         │
         ▼
   dispatch ladder (cmd == "run" | "update-vault" | "enrich" | …)
         │
         ▼  (per gated branch)
   _strip_vault_flags_from_tokens(rest)        →  l_vault, l_vlist
   _strip_write_into_vault_from_tokens(rest)   →  l_write_into_vault   ← NEW
         │
         ▼
   ┌────────────────────────────────────────────────────────┐
   │ _check_vault_cwd_gate(cmd, has_explicit_route, write)  │   ← NEW
   │   1. cwd = Path.cwd().resolve()                        │
   │   2. is_vault = is_obsidian_vault(cwd)                 │
   │   3. if not is_vault → return "n/a"                    │
   │   4. has_profile = (cwd/".graphify"/"profile.yaml")    │
   │      .is_file()                                        │
   │   5. if has_explicit_route → return "n/a" (silent)     │
   │   6. if has_profile → emit auto-adopt notice;          │
   │                       return "auto-adopt"              │
   │   7. if write_into_vault → return "n/a" (silent)       │
   │   8. else → raise _emit_vault_error(msg59, hint59,     │
   │             code=2)                                    │
   └────────────────────────────────────────────────────────┘
         │
         ▼  (auto-adopt → caller sets explicit_vault=cwd before _resolve_cli_paths)
   _resolve_cli_paths(...)  → ResolvedOutput
         │
         ▼
   pipeline (run_corpus / etc.)
```

For `doctor`:

```
graphify doctor
   │
   ▼
   run_doctor() / format_report()
      │
      ▼
   [Vault Detection]  ← existing
   [Profile Validation]
   [Output Destination]
   [Ignore-List]
   [Preview?]
   [Recommended Fixes]
   [vault-cwd]  ← NEW (uses resolve_vault_for_parity + same gate logic, pure read-only)
   [version-sync]  ← Phase 59.1, after [vault-cwd]
```

### Pattern 1: Gate helper inserted once per dispatch branch
**What:** Each of the 14 gated `elif cmd == "..."` branches calls `_check_vault_cwd_gate()` once, immediately after `_strip_vault_flags_from_tokens()` and after detection of any `--output`/`--vault`/`-o` etc. equivalents.
**When:** Every guarded subcommand listed in CONTEXT Decision 1.
**Example call site:**
```python
# Inside elif cmd == "run": (around __main__.py:2755)
rest = list(sys.argv[2:])
lv_vault, lv_vlist, rest = _strip_vault_flags_from_tokens(rest)
lv_write, rest = _strip_write_into_vault_from_tokens(rest)   # NEW
# ... parse --output into cli_output ...

has_explicit_route = bool(
    g_vault_exp or g_vault_list or lv_vault or lv_vlist or cli_output
    or (os.environ.get("GRAPHIFY_VAULT") or "").strip()
)
gate = _check_vault_cwd_gate(
    cmd, has_explicit_route=has_explicit_route,
    write_into_vault=(g_write_into_vault or lv_write),
)
if gate == "auto-adopt":
    # promote CWD to explicit vault for resolve_execution_paths
    if not g_vault_exp and not lv_vault:
        lv_vault = Path.cwd()
# (refuse path raises SystemExit inside the helper)
```

### Pattern 2: `--write-into-vault` global pop (mirrors `--vault`)
```python
# Add to graphify/__main__.py near line 1394 (next to _strip_leading_vault_global_argv)
def _pop_global_write_into_vault(argv: list[str]) -> tuple[list[str], bool]:
    out = list(argv)
    flag = False
    while len(out) > 1 and out[1] == "--write-into-vault":
        flag = True
        out = [out[0]] + out[2:]
    return out, flag

# In main(), right after _strip_leading_vault_global_argv:
sys.argv, g_write_into_vault = _pop_global_write_into_vault(sys.argv)
```

### Pattern 3: Doctor `[vault-cwd]` section
```python
# In graphify/doctor.py:format_report(), after the "Recommended Fixes" block,
# OR (per CONTEXT layering) after the existing [Vault Detection] block:
lines.append("[graphify] === Vault-CWD Default ===")
state = _classify_vault_cwd(report.cwd)  # consumes resolve_vault_for_parity
if state == "auto-adopt":
    lines.append(f"[vault-cwd] auto-adopt — vault at {report.cwd}, profile: .graphify/profile.yaml")
elif state == "refuse":
    lines.append(f"[vault-cwd] refuse — vault at {report.cwd}, no .graphify/profile.yaml (override: --write-into-vault)")
else:
    lines.append(f"[vault-cwd] n/a — {report.cwd} is not an Obsidian vault")
```
The existing `format_report()` uses `[graphify] === Section Name ===` headers (verified at `doctor.py:514`); the `[vault-cwd]` content lines deliberately omit the `[graphify]` prefix per CONTEXT Decision 5's exact wording (single-line `[vault-cwd] outcome — …` format). Confirm wording with planner — CONTEXT.md is canonical.

### Anti-Patterns to Avoid
- **Per-command detection duplication:** copy-pasting `is_obsidian_vault(Path.cwd())` into 14 branches. The single helper is the spec.
- **Silent auto-adopt:** must emit the stderr notice exactly once per process.
- **Loud silent-precedence warning:** when `--write-into-vault` combined with `--vault`/`--output`, emit NOTHING. CONTEXT Decision 3 is explicit.
- **New SystemExit codes:** VCWD-03 uses code 2 (CONTEXT Decision 4). `_emit_vault_error` defaults to 1 — caller MUST pass `code=2`.
- **Walking parents for `.obsidian/`:** `is_obsidian_vault` is strict CWD-only (D-04). Don't change semantics.
- **Writing the auto-adopt notice for explicit-`--vault $CWD`:** that case is "explicit", not auto-adopt — no notice.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Vault detection | `(Path.cwd() / ".obsidian").is_dir()` inline | `is_obsidian_vault()` from `output.py` | Already the canonical helper; doctor/output use it. |
| Two-line error | `print("[graphify] error...");print("  hint:...")` | `_emit_vault_error(msg, hint, code=2)` | Phase 58/61 contract; tests assert exact bytes. |
| Output resolution from CWD | New "auto-adopt resolver" | `resolve_execution_paths(cwd, explicit_vault=Path.cwd(), ...)` | PROJECT.md explicitly forbids new resolver. |
| Doctor parity computation | New CWD-classifier in doctor | Reuse `resolve_vault_for_parity()` + a thin classifier | Existing helper captures `warnings`, `source`, `profile_path` — exactly what VCWD-05 needs. |
| Global-flag stripping | argparse global parser | `_pop_global_write_into_vault()` mirroring `_strip_leading_vault_global_argv` | Existing pattern is battle-tested; argparse global is incompatible with subcommand passthrough. |

**Key insight:** This phase is 100% integration — every primitive needed already exists in `output.py` and `__main__.py`. The risk is in correctness of the call sites, not in algorithm design.

## Common Pitfalls

### Pitfall 1: GRAPHIFY_VAULT env var must defer to gate or vice versa
**What goes wrong:** If gate runs *before* env-var consideration, an env-pin to a different vault would be ignored and the gate would refuse based on CWD profile absence.
**Why it happens:** CONTEXT inherits from PROJECT.md "Precedence: --vault > GRAPHIFY_VAULT > --vault-list file > CWD .obsidian/ detection." The gate must respect this ordering — `GRAPHIFY_VAULT` non-empty counts as `has_explicit_route=True`.
**How to avoid:** Include `(os.environ.get("GRAPHIFY_VAULT") or "").strip()` in the `has_explicit_route` boolean (pattern already used at `__main__.py:3007` and `:3058` in doctor).
**Warning signs:** Test with `GRAPHIFY_VAULT=/path/to/other/vault` set and CWD = profile-less vault → must NOT refuse.

### Pitfall 2: `--vault-list` interaction with auto-adopt
**What goes wrong:** A `--vault-list` file is "explicit routing" but does not pin CWD. If gate auto-adopts despite a list-file, two pins compete.
**How to avoid:** Treat `--vault-list` as `has_explicit_route=True` (already in the boolean above). No auto-adopt when a list is in play.
**Warning signs:** Auto-adopt notice + `--vault pin uses vault root` notice both emitted in same run.

### Pitfall 3: Tests running from inside repo (which has its own structure)
**What goes wrong:** Subprocess tests inheriting CWD from the test runner could trigger refusal if any test fixture creates `.obsidian/` and forgets to remove it, or if a developer runs the test suite from inside a vault.
**How to avoid:** Every subprocess test passes `cwd=str(tmp_path/...)` explicitly (existing pattern in `tests/test_vault_cli.py` and `tests/test_e2e_integration.py`). Never rely on inherited CWD.
**Warning signs:** Flaky tests on local dev only.

### Pitfall 4: Phase 57 harness `--allow-vault-write` lookalike
**What goes wrong:** `harness import` already has `--allow-vault-write` (line 2724–2728) for a *different* purpose (refusing to write harness import output under any vault root, regardless of CWD). VCWD-04's `--write-into-vault` is orthogonal.
**How to avoid:** When implementing VCWD-04 on the `harness`/`import-harness` branches, both flags must coexist. `--write-into-vault` suppresses VCWD-03 (CWD-based refusal); `--allow-vault-write` suppresses the artifacts-dir-under-vault-root check. Both gates fire independently.
**Warning signs:** Tests that exercise `import-harness` from a vault CWD without a profile must pass both flags (or pass `--output` outside the vault).

### Pitfall 5: Auto-adopt notice duplication
**What goes wrong:** Helper called twice (e.g., once at gate, once internally by `resolve_execution_paths`) → notice emitted twice.
**How to avoid:** Notice is emitted ONLY by the gate helper. `resolve_execution_paths` emits its own `--vault pin uses vault root` line only when `cwd_r != effective_root` (line 1442 of output.py); auto-adopt sets `effective_root == cwd_r`, so that line stays silent. Test asserts exactly one auto-adopt line.
**Warning signs:** Two auto-adopt lines on stderr.

### Pitfall 6: Existing `tests/test_e2e_integration.py` `_write_vault` helper requires `.graphify/profile.yaml`
**What goes wrong:** That fixture creates a complete vault. Phase 59 also needs an "incomplete vault" fixture (`.obsidian/` only, no `.graphify/profile.yaml`) for VCWD-03 tests, plus a "no-vault" fixture for VCWD-05 n/a coverage.
**How to avoid:** Add a parameterized `_make_partial_vault(parent, *, with_profile: bool)` helper in the new `tests/test_vault_cwd.py` (or extend `_make_vault` in `test_vault_cli.py:30`).
**Warning signs:** Tests skipping with "PyYAML not installed" — the fixture loads YAML for a profile that VCWD-03 explicitly does not need.

## Runtime State Inventory

This is a feature phase, not a rename/refactor — runtime state inventory is non-applicable. No databases, no OS-registered tasks, no env var renames, no installed package renames. Verified by:

| Category | Items Found | Action Required |
|----------|-------------|------------------|
| Stored data | None — phase adds dispatch logic only | none |
| Live service config | None | none |
| OS-registered state | None | none |
| Secrets/env vars | `GRAPHIFY_VAULT` already exists and is read-only consumed | no changes to its semantics |
| Build artifacts | None | none |

## Environment Availability

Phase is pure-Python in-repo work; depends only on already-installed graphify dev deps.

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| Python | All | ✓ | 3.10+ | — |
| pytest | Tests | ✓ | per `pyproject.toml [test]` extra | — |
| PyYAML | Auto-adopt path resolves a profile (only via `resolve_vault_for_parity` deep call) | optional | — | VCWD-02 tests use `pytest.importorskip("yaml")` (existing pattern). VCWD-03 tests do NOT need PyYAML. |

**Missing dependencies with no fallback:** none.
**Missing dependencies with fallback:** PyYAML — gate VCWD-02 tests behind `pytest.importorskip("yaml")` per Phase 41 convention.

## Code Examples

### Example 1: Reusable gate helper (proposed implementation skeleton)
```python
# graphify/__main__.py — near line 1480 (next to _resolve_cli_paths)
def _check_vault_cwd_gate(
    cmd: str,
    *,
    has_explicit_route: bool,
    write_into_vault: bool,
) -> str:
    """VCWD-01..04 gate.

    Returns one of: "auto-adopt", "refuse" (never returned — raises), "n/a".
    Side effects: emits auto-adopt stderr line OR raises SystemExit(2).
    """
    from graphify.output import is_obsidian_vault, _emit_vault_error
    cwd = Path.cwd().resolve()
    if not is_obsidian_vault(cwd):
        return "n/a"
    has_profile = (cwd / ".graphify" / "profile.yaml").is_file()
    if has_explicit_route:
        return "n/a"   # silent precedence — explicit routing wins
    if has_profile:
        print(
            f"[graphify] auto-adopted vault at {cwd} (profile: .graphify/profile.yaml)",
            file=sys.stderr,
        )
        return "auto-adopt"
    if write_into_vault:
        return "n/a"   # silent opt-in — VCWD-04 suppresses refusal only
    raise _emit_vault_error(
        f"refusing to write into Obsidian vault at {cwd} — no .graphify/profile.yaml found",
        "create .graphify/profile.yaml to opt in, pass --output <path> to write outside the vault, or --write-into-vault to override",
        code=2,
    )
```

### Example 2: `--write-into-vault` token strip (per-command)
```python
def _strip_write_into_vault_from_tokens(tokens: list[str]) -> tuple[bool, list[str]]:
    flag = False
    out: list[str] = []
    for t in tokens:
        if t == "--write-into-vault":
            flag = True
        else:
            out.append(t)
    return flag, out
```

### Example 3: Doctor classifier (consumes existing parity helper)
```python
# graphify/doctor.py
def _classify_vault_cwd(cwd: Path) -> tuple[str, Path | None]:
    """Pure read-only classifier for VCWD-05 — never raises."""
    from graphify.output import is_obsidian_vault
    cwd_r = cwd.resolve()
    if not is_obsidian_vault(cwd_r):
        return ("n/a", None)
    profile = cwd_r / ".graphify" / "profile.yaml"
    if profile.is_file():
        return ("auto-adopt", profile)
    return ("refuse", None)
```

(The runtime gate and doctor classifier consult identical predicates — that's the parity contract. A test asserts both produce the same outcome for the same CWD.)

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Single-line `[graphify] error: …` refusals | Two-line `[graphify] error: …` + `  hint: …` via `_emit_vault_error()` | Phase 58 (VAUX-02), Phase 61 (HARN-FMT-01) | All new vault-write refusals MUST use the helper. |
| Per-command `is_obsidian_vault()` calls | Single dispatch-time gate helper | Phase 59 (this phase) | Single source of truth, single test surface. |
| `--vault` only as global pin | `--vault` global + per-command, plus `--write-into-vault` global + per-command | Phase 41 (vault), Phase 59 (write-into-vault) | Symmetrical pop/strip pattern is the project convention. |

**Deprecated/outdated:** None — Phase 59 is purely additive.

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | The 14 gated commands' dispatch branches all already call `_strip_vault_flags_from_tokens` (or accept that as the natural insertion point) [VERIFIED for `run`, `doctor`, `import-harness`, `update-vault`, `elicit`; ASSUMED for `enrich`, `vault-promote`, `save-result`, `--diagram-seeds`, `--init-diagram-templates`, `--dedup`, `snapshot`, `approve`, `harness`] | Architecture Patterns | Some branches may need refactoring before the gate can be wired cleanly — adds task scope. Planner should grep `_strip_vault_flags_from_tokens` and audit each branch in Wave 0. |
| A2 | `--write-into-vault` accepts no value (boolean flag) — CONTEXT does not state explicitly. | Pattern 2 | Wrong assumption would change strip helper signature. Confirm with user/planner. |
| A3 | The `[vault-cwd]` doctor section sits AFTER `[Vault Detection]` and BEFORE the Phase 59.1 `[version-sync]` block. | Pattern 3 | Wrong placement may break parity tests written against doctor output ordering. CONTEXT Decision 5 says "after `[vault]` parity block, before version-sync from Phase 59.1" — placement clear, but the existing `[Vault Detection]` section uses `=== … ===` style, not `[vault]`. Wording clarification needed. |

**All claims tagged `[VERIFIED]` were confirmed by reading `graphify/__main__.py`, `graphify/output.py`, `graphify/doctor.py` at HEAD this session. All `[CITED]` claims reference CONTEXT.md, ROADMAP.md, REQUIREMENTS.md, PROJECT.md as canonical.**

## Open Questions

1. **Does `--write-into-vault` accept a value, or is it a pure boolean flag?**
   - What we know: CONTEXT Decision 3 says "opt-in flag" — implies boolean.
   - What's unclear: Pre-v1.12 behavior had no equivalent; symmetrical with `--allow-vault-write` (Phase 57), which is also boolean.
   - Recommendation: Boolean. Planner confirms in Wave 0.

2. **Should the doctor `[vault-cwd]` line sit *inside* the existing `[Vault Detection]` `=== === ` section, or as its own `=== Vault-CWD Default ===` section?**
   - What we know: CONTEXT Decision 5 says "new dedicated section (do NOT extend `[vault]`)" but uses `[vault-cwd]` as the line prefix, not as a section header.
   - What's unclear: Existing `format_report` uses `[graphify] === Name ===` headers; CONTEXT-prescribed lines are `[vault-cwd] outcome — …` (no `[graphify]` prefix, no `===`).
   - Recommendation: Add `[graphify] === Vault-CWD Default ===` header line, then the `[vault-cwd] …` content line(s). Confirms with planner / discuss-phase if needed.

3. **For `--obsidian` (which already has `--output` and `--obsidian-dir`), does `--output` count as "explicit routing" for VCWD-02 / VCWD-03?**
   - What we know: VCWD-02 says "no explicit `--vault` / `--output` flag was passed".
   - What's unclear: `--obsidian-dir` is also a routing override.
   - Recommendation: Treat both `--output` AND `--obsidian-dir` as explicit routing for the `--obsidian` branch. Per-branch `has_explicit_route` boolean is the clean way to encode this.

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest >= 7 (per `pyproject.toml [test]` extra) |
| Config file | `pyproject.toml` (no separate pytest.ini) |
| Quick run command | `pytest tests/test_vault_cwd.py -x -q` |
| Full suite command | `pytest tests/ -q` |

### Phase Requirements → Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| VCWD-01 | Detection runs in 14 gated commands; reusable for doctor | unit + integration (subprocess) | `pytest tests/test_vault_cwd.py::test_gate_runs_for_each_gated_cmd -x` | ❌ Wave 0 |
| VCWD-01 | Detection does NOT run for `query`/`doctor`/`install`/`hook`/`capability`/`benchmark`/`--validate-profile`/`--version` | integration | `pytest tests/test_vault_cwd.py::test_gate_skipped_for_readonly_cmds -x` | ❌ Wave 0 |
| VCWD-02 | Auto-adopt routes identically to `--vault $CWD` | unit | `pytest tests/test_vault_cwd.py::test_auto_adopt_matches_explicit_vault -x` | ❌ Wave 0 |
| VCWD-02 | Auto-adopt emits exactly one stderr notice | integration | `pytest tests/test_vault_cwd.py::test_auto_adopt_notice_emitted_once -x` | ❌ Wave 0 |
| VCWD-02 | Explicit `--vault $CWD` does NOT emit auto-adopt notice | integration | `pytest tests/test_vault_cwd.py::test_explicit_vault_no_auto_adopt_notice -x` | ❌ Wave 0 |
| VCWD-03 | Refusal exit code 2 + two-line stderr | integration | `pytest tests/test_vault_cwd.py::test_refusal_exit_code_and_format -x` | ❌ Wave 0 |
| VCWD-03 | Refusal message text matches CONTEXT Decision 4 verbatim | integration | `pytest tests/test_vault_cwd.py::test_refusal_message_text -x` | ❌ Wave 0 |
| VCWD-04 | `--write-into-vault` (per-command) suppresses refusal | integration | `pytest tests/test_vault_cwd.py::test_write_into_vault_suppresses_refusal -x` | ❌ Wave 0 |
| VCWD-04 | `--write-into-vault` (global, leading) suppresses refusal | integration | `pytest tests/test_vault_cwd.py::test_global_write_into_vault_suppresses_refusal -x` | ❌ Wave 0 |
| VCWD-04 | `--write-into-vault` + `--vault` → silent precedence (no warning) | integration | `pytest tests/test_vault_cwd.py::test_write_into_vault_silent_precedence -x` | ❌ Wave 0 |
| VCWD-04 | `--write-into-vault` does NOT suppress VCWD-02 auto-adopt | integration | `pytest tests/test_vault_cwd.py::test_write_into_vault_yields_to_profile -x` | ❌ Wave 0 |
| VCWD-05 | Doctor `[vault-cwd]` always present | integration | `pytest tests/test_vault_cwd.py::test_doctor_vault_cwd_section_always_shown -x` | ❌ Wave 0 |
| VCWD-05 | Doctor outcome matches runtime gate (parity) | integration | `pytest tests/test_vault_cwd.py::test_doctor_runtime_parity -x` | ❌ Wave 0 |
| VCWD-05 | Doctor outcomes: auto-adopt / refuse / n/a all reachable | integration | `pytest tests/test_vault_cwd.py::test_doctor_three_outcomes -x` | ❌ Wave 0 |
| Cross-cutting | `GRAPHIFY_VAULT` env pin treated as explicit route | integration | `pytest tests/test_vault_cwd.py::test_env_pin_disables_gate -x` | ❌ Wave 0 |
| Cross-cutting | `--vault-list` treated as explicit route | integration | `pytest tests/test_vault_cwd.py::test_vault_list_disables_gate -x` | ❌ Wave 0 |
| Regression | `tests/test_vault_cli.py` (Phase 41) still green | regression | `pytest tests/test_vault_cli.py -q` | ✅ exists |
| Regression | `tests/test_e2e_integration.py` (Phase 60) still green | regression | `pytest tests/test_e2e_integration.py -q` | ✅ exists |
| Regression | Full suite green (currently 2123 tests baseline) | regression | `pytest tests/ -q` | ✅ |

### Sampling Rate
- **Per task commit:** `pytest tests/test_vault_cwd.py -x -q`
- **Per wave merge:** `pytest tests/test_vault_cwd.py tests/test_vault_cli.py tests/test_doctor.py tests/test_main_flags.py tests/test_e2e_integration.py -q`
- **Phase gate:** `pytest tests/ -q` green; ≥ 2123 tests passing (delta ≥ +15 from new VCWD coverage).

### Wave 0 Gaps
- [ ] `tests/test_vault_cwd.py` — new file, covers all 17 VCWD test rows above. Includes `_make_partial_vault(parent, *, with_profile: bool)` fixture mirroring `tests/test_vault_cli.py:_make_vault` and `tests/test_e2e_integration.py:_write_vault`.
- [ ] Confirm `--obsidian-dir` counts as explicit routing for the `--obsidian` branch (Open Question 3) — adds 1–2 test rows.

### TDD Mode Notes (tdd_mode = true)
Most VCWD tasks lend themselves to RED → GREEN → REFACTOR:
- **RED:** Write the test (e.g., assert two-line stderr + exit 2) against current code → fails because no gate exists.
- **GREEN:** Wire `_check_vault_cwd_gate` minimally to pass.
- **REFACTOR:** Consolidate token-strip helpers, doc the helper in module docstring.

Tasks that don't naturally fit TDD (lower TDD value):
- The doctor `format_report` text addition — purely cosmetic; pair the format change with one parity test asserting the new line appears, but RED phase is essentially "assert string in output → fails" (still doable but low-yield).
- The `_pop_global_write_into_vault` helper — pure unit-level, RED is trivial. Combine with a per-command strip test.

## Sources

### Primary (HIGH confidence — codebase verified at HEAD this session)
- `graphify/output.py` — `is_obsidian_vault` (line 69), `_emit_vault_error` (line 80), `resolve_execution_paths` (line 178), `resolve_vault_for_parity` (line 215), `resolve_output` (line ~282)
- `graphify/__main__.py` — `_strip_leading_vault_global_argv` (1394), `_strip_vault_flags_from_tokens` (1422), `_merge_vault_pins` (1457), `_resolve_cli_paths` (~1480), main() startup (~1492), dispatch ladder (1635, 1731, 1872, 1922, 1967, 2097, 2216, 2429, 2489, 2508, 2523, 2609, 2672, 2755, 2856, 2924, 2951, 2965, 3078, 3124), Phase 57 harness guard call site (2724–2728), doctor body (2965+)
- `graphify/doctor.py` — `format_report` (line 514), uses `is_obsidian_vault` (line 395)
- `tests/test_vault_cli.py` (Phase 41 vault CLI tests, 100 lines) — `_make_vault` helper at line 30, subprocess+monkeypatch+`pytest.importorskip("yaml")` patterns
- `tests/test_e2e_integration.py` (Phase 60 E2E, 364 lines) — `_write_vault` (line 56), `_graphify` runner (line 20), `.obsidian/`-first fixture pattern (line 67)

### Secondary (HIGH — planning canon, treated as locked spec)
- `.planning/phases/59-vault-cwd-aware-cli-default/59-CONTEXT.md` — five locked decisions
- `.planning/REQUIREMENTS.md` — VCWD-01..05 verbatim acceptance criteria (lines 10–16, 61–65)
- `.planning/ROADMAP.md` — Phase 59 success criteria (lines 420–435)
- `.planning/PROJECT.md` — v1.12 milestone goals + non-goals (referenced via CONTEXT prior_decisions)

### Tertiary (LOW — none)
None. All facts are sourced from the codebase or planning canon.

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — all helpers exist and were read at HEAD this session.
- Architecture: HIGH — patterns mirror Phase 41 `--vault` plumbing (in-tree, verified).
- Pitfalls: HIGH — derived from existing call sites and Phase 41/57/58/61 history (CONTEXT prior_decisions, ROADMAP).
- Test infrastructure: HIGH — fixtures and subprocess patterns already exist in `tests/test_vault_cli.py` and `tests/test_e2e_integration.py`.

**Research date:** 2026-05-04
**Valid until:** 2026-06-03 (30 days; codebase-internal facts are stable absent a major refactor of `__main__.py`).
