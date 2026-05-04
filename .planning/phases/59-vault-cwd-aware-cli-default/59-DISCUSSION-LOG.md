---
phase: 59-vault-cwd-aware-cli-default
date: 2026-05-04
mode: discuss --chain
---

# Phase 59 Discussion Log

Human-readable record of the discuss-phase conversation. Not consumed by downstream agents; canonical decisions live in `59-CONTEXT.md`.

## Areas selected for discussion

User selected all four offered areas:
1. Detection scope across commands
2. Auto-adopt UX (silent vs noisy)
3. Refusal copy + `--write-into-vault` flag
4. Doctor parity output for VCWD-05

## Area 1 — Detection scope

**Question:** Which subcommands should trigger the VCWD detection gate before dispatch?

**Options presented:**
- Output-writing only (Recommended) — `run`, `update-vault`, `enrich`, `--obsidian`, `vault-promote`, `import-harness`, `save-result`, `--diagram-seeds`, `--init-diagram-templates`, `--dedup`, `snapshot`, `approve`, `elicit`, `harness`. Skip `query`, `doctor`, `install`, `hook`, `capability`, `benchmark`, `--validate-profile`, `--version`.
- Conservative — only `run` + `update-vault`.
- All commands except install/diagnostic.

**User selected:** Output-writing only (Recommended).

**Notes:** Strict reading of "any other output-producing command" = anything that writes artifacts to disk. Read-only and diagnostic paths must remain unaffected so users can `graphify query` from inside a vault without surprises. Implementation lives in a single dispatch helper to avoid per-command duplication.

## Area 2 — Auto-adopt UX

**Question:** When VCWD-02 auto-adopts the CWD as the vault (profile present, no flags), what feedback should the user see?

**Options presented:**
- One-line stderr note (Recommended) — mirrors Phase 41 `--vault` override notice.
- Silent — identical to `--vault $CWD`, no stderr.
- Stderr note only on TTY.

**User selected:** One-line stderr note (Recommended).

**Notes:** Visibility is worth slight CI noise because auto-routing the destination is a behavior change the user should be able to observe in logs. Format aligns with Phase 41's pattern.

## Area 3 — `--write-into-vault` flag and refusal copy

**Question A:** How should `--write-into-vault` be wired and what happens when combined with explicit `--vault`/`--output`?

**Options presented:**
- Per-command + global, silent precedence (Recommended).
- Per-command only, warn on conflict.
- Per-command + global, hard-error on conflict.

**User selected:** Per-command + global, silent precedence (Recommended).

**Question B:** What should the VCWD-03 refusal say exactly?

**Options presented:**
- Profile-focused (Recommended): mentions `.graphify/profile.yaml` as the missing piece.
- Action-focused.
- Terse.

**User selected:** Profile-focused (Recommended).

**Notes:** The flag is symmetrical with `--vault` (global + per-command via the same `_pop_global_*` pattern). When combined with explicit routing, the explicit route wins silently — no warning or error. The refusal makes the missing profile the primary signal, since creating the profile is the cleanest fix for users who want vault output.

## Area 4 — Doctor parity output

**Question:** How should `graphify doctor` surface VCWD-05 prediction?

**Options presented:**
- New `[vault-cwd]` section, always shown (Recommended).
- Extend existing `[vault]` section.
- New section, only when CWD is a vault.

**User selected:** New `[vault-cwd]` section, always shown (Recommended).

**Notes:** Keeps VAUX-01 (Phase 58 parity) and VCWD-05 contracts independent. Three deterministic outcomes (auto-adopt / refuse / n/a) are easy to assert in CI subprocess fixtures.

## Deferred ideas

- TTY-aware quieting of the auto-adopt notice — revisit if CI noise complaints arise.
- `GRAPHIFY_DISABLE_VCWD=1` env escape hatch for batch jobs.
- Project-wide audit of remaining one-line `[graphify]` errors — saved for v1.13.
- Stand-alone `.graphify/` detection (without `.obsidian/`) — explicitly out of scope.

## Scope creep redirected

None. All discussion stayed within the locked VCWD-01..05 boundary.
