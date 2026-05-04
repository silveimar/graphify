---
phase: 59-vault-cwd-aware-cli-default
title: Vault-CWD-aware CLI default
date: 2026-05-04
mode: discuss
chain: true
---

# Phase 59 Context — Vault-CWD-aware CLI default

<domain>
Make `graphify` safe to run from inside an Obsidian vault. When the CWD is a vault:
- with `.graphify/profile.yaml` → auto-route output through `_resolve_output_target()` (Option C, auto-adopt) — no flags required.
- without a profile and without explicit routing flags → refuse with a two-line `[graphify] error: ... / hint: ...` (via `_emit_vault_error()`).
- `--write-into-vault` opt-in flag suppresses the refusal.
- `graphify doctor` surfaces the predicted behavior for the same CWD inputs (parity contract).

Locked requirements: **VCWD-01..05** (`.planning/REQUIREMENTS.md`).
</domain>

<canonical_refs>
MANDATORY reading for downstream agents (researcher, planner, executor):

- `.planning/REQUIREMENTS.md` — VCWD-01..05 acceptance criteria (lines for the Vault-CWD-aware CLI default section)
- `.planning/ROADMAP.md` — Phase 59 success criteria (lines 420–435)
- `.planning/PROJECT.md` — v1.12 milestone goals + non-goals
- `graphify/output.py` — reuse helpers:
  - `is_obsidian_vault(path)` (line 69) — VCWD-01 detection
  - `_emit_vault_error(msg, hint, *, code=)` (line 80) — VCWD-03 two-line refusal
  - `resolve_output_target(...)` (line ~282) — VCWD-02 auto-adopt path
  - `resolve_vault_for_parity(...)` (line 215) — VCWD-05 doctor parity helper
- `graphify/__main__.py` — global flag stripping pattern: `_pop_global_*` (lines 1397–1463); subcommand dispatch table (lines 1630–3124+); current refusal call site at line 2724–2726
- `graphify/security.py` — path confinement rules; sanitization for any error-message interpolation of `<cwd>`
- Phase 41 prior CONTEXT — `--vault` precedence and override-stderr-line pattern (basis for VCWD-02 auto-adopt notice)
- Phase 58 prior CONTEXT — two-line `[graphify] error:` / `  hint:` format established by `_emit_vault_error()` (basis for VCWD-03 wording)
- Phase 59.1 work — VSYNC-related changes to `doctor` are already merged; layer the new `[vault-cwd]` section after them without conflict
</canonical_refs>

<prior_decisions>
**From v1.12 PROJECT.md (locked):**
- Reuse `_resolve_output_target()` (Phase 41) — no new resolver.
- Reuse `_emit_vault_error()` (Phase 58) — no new error helper.
- Precedence order preserved: `--vault` > `GRAPHIFY_VAULT` > `--vault-list` file > CWD `.obsidian/` detection.
- Option B (silent magic auto-route to hidden `.graphify-out/`) is explicitly rejected — auto-adopt only when a profile exists.

**From Phase 58 (carried forward):**
- All vault-write refusals use the two-line `_emit_vault_error()` format. Phase 61 already migrated the harness path to this format (HARN-FMT-01). Phase 59 must use the same helper — do NOT introduce a new error path.

**From Phase 41 (carried forward):**
- Stderr override notices are emitted exactly once per process, before pipeline dispatch. The auto-adopt notice in this phase follows that contract.
</prior_decisions>

<decisions>

### Decision 1 — Detection scope: output-writing commands only
**VCWD-01 gate is wired before dispatch for the following subcommands:**
`run`, `update-vault`, `enrich`, `--obsidian`, `vault-promote`, `import-harness`, `save-result`, `--diagram-seeds`, `--init-diagram-templates`, `--dedup`, `snapshot`, `approve`, `elicit`, `harness`.

**Skipped (no gate):**
`query`, `doctor`, `install`, `hook`, `capability`, `benchmark`, `--validate-profile`, `--version`.

Rationale: VCWD-01's "any other output-producing command" is interpreted strictly as commands that write artifacts to disk. Read-only / diagnostic / install commands stay unaffected to avoid surprising users running `graphify query` from inside a vault. The gate is implemented as a single dispatch helper called from each guarded branch (or as a decorator-style entry helper) — single source of truth, no per-command duplication of detection logic.

### Decision 2 — Auto-adopt UX: one-line stderr note (VCWD-02)
When the CWD is a vault AND has `.graphify/profile.yaml` AND no explicit `--vault`/`--output`/`--write-into-vault` was passed, before dispatching the pipeline emit exactly one stderr line:

```
[graphify] auto-adopted vault at <cwd> (profile: .graphify/profile.yaml)
```

Then proceed identically to passing `--vault $CWD`. This mirrors the Phase 41 `--vault` override notice pattern. Tests must assert the line is present on the auto-adopt path and absent on the explicit-`--vault` path.

### Decision 3 — `--write-into-vault` flag wiring (VCWD-04)
- Accepted as **both** a leading global flag (alongside `--vault`/`--vault-list`, stripped by the same `_pop_global_*` pattern around `__main__.py:1397`) **and** as a per-subcommand flag for the gated commands listed in Decision 1.
- When combined with `--vault` and/or `--output`, **silent precedence**: the explicit routing flag wins, `--write-into-vault` is a no-op in that combo (no warning, no error). Tests verify combined behavior matches `--vault` / `--output` alone.
- Suppresses **VCWD-03 only** (the refusal). It does NOT bypass VCWD-02 auto-adopt — when a profile exists, the profile-driven route is always preferred over a flat dump.
- Documented in `--help` and `doctor` output as "deliberate opt-in to write directly into a vault root without a profile".

### Decision 4 — VCWD-03 refusal copy (profile-focused two-line format)
Exact wording emitted via `_emit_vault_error()`:

```
[graphify] error: refusing to write into Obsidian vault at <cwd> — no .graphify/profile.yaml found
  hint: create .graphify/profile.yaml to opt in, pass --output <path> to write outside the vault, or --write-into-vault to override
```

`<cwd>` is the resolved absolute path; sanitized via `security.py` rules before interpolation. Exit code 2.

### Decision 5 — `graphify doctor` adds `[vault-cwd]` section (VCWD-05)
- Add a new dedicated section to `doctor` output (do NOT extend the existing `[vault]` parity section — keep VAUX-01 and VCWD-05 contracts independent).
- Section runs unconditionally and prints exactly one of:
  - `[vault-cwd] auto-adopt — vault at <cwd>, profile: <relative-path-to-profile>`
  - `[vault-cwd] refuse — vault at <cwd>, no .graphify/profile.yaml (override: --write-into-vault)`
  - `[vault-cwd] n/a — <cwd> is not an Obsidian vault`
- Layer placement: after the existing `[vault]` parity block, before any version-sync output added by Phase 59.1.
- Parity contract: the doctor prediction MUST match the runtime behavior for the same CWD (testable via subprocess fixture).

</decisions>

<scope_boundaries>
**In scope:**
- VCWD-01..05 only.
- New `--write-into-vault` flag (per-command + global).
- New `doctor` `[vault-cwd]` section.
- Tests for all five requirements (CI Python 3.10 + 3.12).

**Out of scope (deferred):**
- Auto-adopt for non-Obsidian markers (e.g. `.obsidian/` is the only sentinel; no `.graphify/` standalone detection).
- A flag to force-disable detection globally (e.g. `--no-vault-cwd`) — if needed, surfaces in v1.13.
- Project-wide stderr-format sweep beyond the helpers already migrated.
- Changes to `_resolve_output_target()` or `_emit_vault_error()` signatures.
- TTY-aware silent mode for the auto-adopt notice (rejected: harder to test, low value).
</scope_boundaries>

<deferred>
- TTY-aware quieting of the auto-adopt notice (only print on TTY) — revisit if CI noise complaints arise.
- A `GRAPHIFY_DISABLE_VCWD=1` env escape hatch for batch jobs that intentionally run inside vaults — capture as a v1.13 candidate if real users ask for it.
- Project-wide audit of remaining one-line `[graphify]` errors not yet migrated to the two-line format — saved for v1.13.
</deferred>

<code_context>
**Reusable assets confirmed at HEAD:**
- `graphify/output.py:69` — `is_obsidian_vault(path: Path) -> bool`
- `graphify/output.py:80` — `_emit_vault_error(msg, hint, *, code=1) -> SystemExit`
- `graphify/output.py:215` — `resolve_vault_for_parity(...)` (doctor parity)
- `graphify/output.py:282` — `resolve_output_target` / `resolve_output(...)` block (auto-route mechanism)
- `graphify/__main__.py:1397–1463` — global flag stripping pattern (`_pop_global_vault`, `_pop_global_vault_list`); add `_pop_global_write_into_vault` here
- `graphify/__main__.py:1630+` — subcommand dispatch ladder; gate is wired at the top of each guarded branch via a single helper
- `graphify/__main__.py:2724–2726` — current `_emit_vault_error` call site (Phase 61 reference)
- `graphify/__main__.py:2965+` — `doctor` command (extension point for `[vault-cwd]` section)

**Test surface to extend:**
- `tests/test_output.py` (vault detection + resolve)
- `tests/test_main.py` or per-command tests (gate behavior)
- New: `tests/test_vault_cwd.py` for VCWD-01..05 coverage if cleaner than appending to existing files
- Subprocess fixtures in `tests/test_e2e_integration.py` for CWD-based scenarios
</code_context>

<acceptance_criteria>
Lifted from ROADMAP.md Phase 59 success criteria — all 5 must hold:

1. CWD with `.obsidian/` triggers detection in `run` / `update-vault` / other gated commands; `doctor` reports the prediction (**VCWD-01**, **VCWD-05**).
2. CWD = vault + profile + no flags → output routes via `_resolve_output_target()` identically to `--vault $CWD`, with the auto-adopt stderr notice (**VCWD-02**).
3. CWD = vault + no profile + no flags → exit 2 with profile-focused two-line `[graphify] error:` / `  hint:` via `_emit_vault_error()` (**VCWD-03**).
4. `--write-into-vault` (per-command and global) suppresses VCWD-03; silent precedence vs `--vault`/`--output` (**VCWD-04**).
5. `doctor` `[vault-cwd]` section reports auto-adopt / refuse / n/a, parity-tested against runtime (**VCWD-05**).

Test matrix: Python 3.10 + 3.12 CI green; full suite passes from current 2123 baseline.
</acceptance_criteria>
