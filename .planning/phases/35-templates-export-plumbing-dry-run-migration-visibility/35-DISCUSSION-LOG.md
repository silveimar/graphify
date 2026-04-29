# Phase 35: Templates, Export Plumbing & Dry-Run/Migration Visibility - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md - this log preserves the alternatives considered.

**Date:** 2026-04-29T05:05:47.296Z
**Phase:** 35-templates-export-plumbing-dry-run-migration-visibility
**Areas discussed:** Migration command shape, Legacy note matching, Review output, Repo identity propagation

---

## Migration Command Shape

| Question | Selected | Alternatives Considered |
|----------|----------|--------------------------|
| Primary entry point | Dedicated command | Existing export plus flag; doctor/dry-run first; Claude decides |
| Source/target framing | Corrected: source is `work-vault/raw/`, vault is `ls-vault` | Vault-to-vault paths; CWD source; profile target inference |
| Command name and arguments | `graphify update-vault --input work-vault/raw --vault ls-vault` direction | `migrate-vault`; `vault-promote`; Claude decides |
| Apply behavior | Preview-only by default; require `--apply` | Apply by default; two-step verbs; Claude decides |
| Pipeline source | Run full graphify pipeline from `work-vault/raw` by default | Existing artifacts by default; hybrid `--from-artifacts`; Claude decides |

**User's choice:** Dedicated `update-vault` command, preview-first, full pipeline by default.
**Notes:** The user corrected the premise: this is not `work-vault` to `ls-vault` as vault-to-vault. The Obsidian vault is always `ls-vault`; the origin data is `work-vault/raw/`. The command should not imply a destructive full rebuild.

---

## Legacy Note Matching

| Question | Selected | Alternatives Considered |
|----------|----------|--------------------------|
| Scan scope | Manifest plus bounded vault scan | Manifest only; declared output subtree only; Claude decides |
| Matching priority | Manifest node/community identity first | Frontmatter first; filename pattern first; Claude decides |
| Unmatched legacy files | ORPHAN review-only entries, never deleted or moved | SKIP_CONFLICT; separate manual migration candidates; Claude decides |
| Matched legacy files | Claude decides: preserve v1.8 path contract and old files as review-only | Update old path in place; MOVE/RENAME candidate only |

**User's choice:** Use manifest plus bounded scan; trust manifest identity first; report unmatched legacy files as ORPHAN review-only.
**Notes:** For matched legacy notes, the user delegated the exact handling. Context locks the safety posture: do not update old legacy paths in place, preserve v1.8 Graphify-owned paths, and keep old legacy files review-only unless the user cleans them manually.

---

## Review Output

| Question | Selected | Alternatives Considered |
|----------|----------|--------------------------|
| Preview format | Human summary plus structured JSON sidecar | Terminal-only; JSON-only; Claude decides |
| Detail level | Claude decides: readable summary with risky cases expanded | All paths; counts only; grouped examples |
| Always-expanded outcomes | `SKIP_CONFLICT`, `SKIP_PRESERVE`, `ORPHAN`, `REPLACE` | Conflicts only; verbose-only; Claude decides |
| Persistent artifacts | Write both Markdown and JSON plan artifacts | JSON only; print only; Claude decides |
| Apply gate | Require `--apply --plan-id <id>` | `--apply` only; force token only for REPLACE; Claude decides |

**User's choice:** Preview must be both human-readable and agent/test-friendly, with Markdown and JSON artifacts and a plan-id-gated apply path.
**Notes:** Risky outcomes must be visible by default even if ordinary creates/updates are summarized.

---

## Repo Identity Propagation

| Question | Selected | Alternatives Considered |
|----------|----------|--------------------------|
| CODE frontmatter field | `repo: <identity>` | `graphify_repo`; `source_repo`; Claude decides |
| Tags | Add `repo/<identity>` to CODE notes | `graphify/repo/<identity>`; no tags; Claude decides |
| Manifest fields | Run-level metadata plus per-note repo identity | Run-level only; CODE-only; Claude decides |
| Identity drift | `SKIP_CONFLICT` until explicit resolution/override | Warn and continue; separate namespace with ORPHAN; Claude decides |
| Preview visibility | Top banner plus CODE note rows | Banner only; verbose only; Claude decides |

**User's choice:** Repo identity should be visible in frontmatter, tags, manifests, and preview output.
**Notes:** Identity drift is treated as a safety issue, not just a warning.

---

## Claude's Discretion

- Exact legacy mapping note shape and wording, provided old files stay review-only and v1.8 paths remain canonical.
- Default number of representative low-risk rows in the human preview, provided all risky cases are expanded and a verbose/details mode can show everything.

## Deferred Ideas

None.
