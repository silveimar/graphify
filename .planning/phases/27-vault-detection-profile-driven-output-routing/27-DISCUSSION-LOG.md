# Phase 27: Vault Detection & Profile-Driven Output Routing - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-04-27
**Phase:** 27-vault-detection-profile-driven-output-routing
**Areas discussed:** Output destination schema, Detection trigger semantics, CLI override + precedence reporting, Scope of resolved destination

---

## Output Destination Schema

### Profile shape

| Option | Description | Selected |
|--------|-------------|----------|
| Struct with explicit strategy | New top-level `output:` block with `mode: vault-relative \| absolute \| sibling-of-vault` and `path:` string | ✓ |
| Flat string, infer from prefix | Single `output: "..."` string; leading `/` → absolute, `../` → sibling | |
| Flat string, vault-relative only | Profile only allows vault-relative; absolute/sibling require CLI flag | |

**User's choice:** Struct with explicit strategy.
**Notes:** Self-documenting, validates cleanly, no ambiguous parsing of leading `/` or `../`. Lands in `_VALID_TOP_LEVEL_KEYS`.

### Default behavior when `output:` is absent

| Option | Description | Selected |
|--------|-------------|----------|
| Refuse — require explicit field | Fail loudly with actionable message if vault detected and `output:` missing | ✓ |
| Sibling-of-vault default | Default to `<vault>/../graphify-out/` | |
| Vault-relative default | Default to `<vault>/graphify-out/` (matches today's behavior) | |

**User's choice:** Refuse with actionable message.
**Notes:** Aligns with `v1.7-input-vault-adapter-no-source-mirroring.md` — no source-path mirroring fallback. Prevents silent vault pollution.

---

## Detection Trigger Semantics

### Detection scope

| Option | Description | Selected |
|--------|-------------|----------|
| Strict CWD only | `Path('.obsidian').is_dir()` from CWD; no parent-walking | ✓ |
| Walk up to filesystem root | Walk parents until `.obsidian/` found | |
| CWD + immediate parent | Check CWD and direct parent only | |

**User's choice:** Strict CWD only.

### Vault detected, no profile

| Option | Description | Selected |
|--------|-------------|----------|
| Refuse with actionable message | Error directing user to create profile or pass `--output` | ✓ |
| Auto-write a default profile | Silently create minimal `.graphify/profile.yaml` | |
| Warn and fall back to current behavior | Print warning, write to `<vault>/graphify-out/` | |

**User's choice:** Refuse with actionable message (SEED Option A safety net).

### Command scope of auto-adopt

| Option | Description | Selected |
|--------|-------------|----------|
| Build pipeline only | Auto-adopt only on default `graphify` invocation | |
| Both build pipeline AND `--obsidian` export | Both honor profile output destination | ✓ |
| All commands that write to disk | Includes watch, vault-promote, etc. | |

**User's choice:** Both build pipeline AND `--obsidian` export.

---

## CLI Override + Precedence Reporting

### Override flag

| Option | Description | Selected |
|--------|-------------|----------|
| New unified `--output <path>` | Single new flag; existing `--out-dir` / `--obsidian-dir` retained for back-compat | ✓ |
| Reuse existing `--out-dir` / `--obsidian-dir` | No new flag | |
| Both: `--output` plus aliases | `--output` canonical, legacy flags become aliases | |

**User's choice:** New unified `--output <path>`.

### Precedence stderr message

| Option | Description | Selected |
|--------|-------------|----------|
| Single line, always shown | Predictable for scripts; suppressible via `2>/dev/null` | ✓ |
| Single line, suppressible by `--quiet` | Adds CLI surface | |
| Multi-line block with full resolution trace | More verbose | |

**User's choice:** Single line, always shown.

---

## Scope of Resolved Destination

### What `output:` controls

| Option | Description | Selected |
|--------|-------------|----------|
| Obsidian rendered notes only; build artifacts go sibling-of-vault | Notes inside vault, machine artifacts outside | ✓ |
| Everything goes to profile `output:` path | Whole `graphify-out/` tree lands at profile-declared path | |
| Two separate fields: `output.notes` and `output.artifacts` | Explicit control of both | |

**User's choice:** Obsidian rendered notes only; build artifacts go sibling-of-vault.
**Notes:** Avoids putting binary-ish artifacts and cache dirs inside the vault, simplifies Phase 28's self-ingest hardening.

### Corpus root when auto-adopt fires

| Option | Description | Selected |
|--------|-------------|----------|
| Forced to CWD (the vault) | Literal SEED Option C contract | ✓ |
| Configurable via `--source` / positional arg | More flexible | |

**User's choice:** Forced to CWD (the vault).

---

## Claude's Discretion

- Exact location and Python type of the `ResolvedOutput` data structure (function in `profile.py` vs new tiny module).
- Exact wording of error messages for the "vault but no profile" refusal and the sibling-of-vault validator.
- Whether the vault-detection report (VAULT-08) is a single line or a small block — keep terse.

## Deferred Ideas

- Auto-write a minimal default profile when vault detected but no profile present — rejected; revisit as v1.8 onboarding tied to SEED-001.
- Walking-up parent detection for `.obsidian/`.
- `--quiet` flag to suppress precedence stderr line.
- Two separate profile fields `output.notes` and `output.artifacts`.
- Multi-line precedence-resolution trace block.
- `graphify init-profile` scaffolding command — implied by error message wording, not in this phase.
