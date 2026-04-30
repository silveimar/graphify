# Phase 41: Vault CLI — vault flag & Multi-Vault Selector - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-04-30
**Phase:** 41-vault-cli-vault-flag-multi-vault-selector
**Areas discussed:** Flag precedence, Multi-vault selection, Doctor/dry-run alignment, Testing & docs (requirements-locked session)

---

## Tooling prerequisite

| Option | Description | Selected |
|--------|-------------|----------|
| ROADMAP `details` + phase dir | Enables `gsd-sdk query init.phase-op 41` | ✓ |
| Proceed without SDK | Fragile paths / wrong `phase_dir` | |

**Notes:** Added Phase 41 `<details>` block to `.planning/ROADMAP.md`, created `.planning/phases/41-vault-cli-vault-flag-multi-vault-selector/`, simplified summary line (avoid backticks inside XML summary). Re-ran `init.phase-op` → `phase_found: true`.

---

## Flag precedence & `--vault` (VCLI-01)

| Option | Description | Selected |
|--------|-------------|----------|
| `--vault` overrides CWD detection | Explicit pin for automation | ✓ |
| CWD-only | Keep Phase 27 only | |

**User's choice:** Locked per **VCLI-01** + **`ResolvedOutput` precedent** (`41-CONTEXT.md` **D-01–D-02**).

---

## Multi-vault selection (VCLI-02)

| Option | Description | Selected |
|--------|-------------|----------|
| `--vault` + env + optional list file + TTY-gated prompt | Meets “minimal selector”; CI-safe | ✓ |
| Interactive default | Breaks CI | |

**User's choice:** Locked per **VCLI-02** + **D-03–D-04** in CONTEXT.

---

## Doctor & dry-run alignment (VCLI-03, VCLI-04)

| Option | Description | Selected |
|--------|-------------|----------|
| Single resolver entry for doctor/run/dry-run | Consistent banners | ✓ |
| Separate ad-hoc paths | Risk drift | |

**User's choice:** **D-05–D-06**.

---

## Claude's Discretion

- Argparse structure, final env var name, bounded discovery algorithm details — planner/researcher within CONTEXT **D-01–D-08**.

## Deferred Ideas

- Full-disk vault discovery, Obsidian-plugin picker — see CONTEXT `<deferred>`.
