# Phase 19: Vault Promotion Script (Layer B) - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-04-22
**Phase:** 19-vault-promotion-script-layer-b
**Areas discussed:** Scope vs. design note, Architecture & CLI, Classifier & scoring, Write semantics & tags

---

## Scope vs. design note

### Q1: How should Phase 19 scope handle VAULT-06 (profile write-back) and VAULT-07 (hybrid tag taxonomy) from the design note?

| Option | Description | Selected |
|--------|-------------|----------|
| Canonical only (VAULT-01..05) | Ship the 5 locked requirements. Tag taxonomy is hard-coded or read from a static profile section. No profile write-back. Clean phase, respects REQUIREMENTS.md boundary. (Recommended) | |
| Fold in VAULT-07 only | Add hybrid 3-layer tag taxonomy. Skip VAULT-06 profile write-back. | ✓ (initially) |
| Fold in both VAULT-06 + VAULT-07 | Full design-note scope. Write-back mutates `.graphify/profile.yaml`. 7 REQ-IDs. | ✓ (after Q3 confirm) |
| Defer everything past VAULT-05 | Re-tags VAULT-06/07 as a new phase (19.1 or v1.6 candidate). | |

**User's choice:** Initially "Fold in VAULT-07 only"; then via Q3 confirm re-opened scope to "VAULT-01..07 all in scope"
**Notes:** User's Q2 freeform "write-back" answer implied VAULT-06 was wanted after all. Explicit re-confirmation in Q3 locked VAULT-01..07.

### Q2: VAULT-07 Layer 3 behavior without VAULT-06 write-back?

| Option | Description | Selected |
|--------|-------------|----------|
| Detect + use in-memory only | Auto-detect per run, apply to this run's notes, never persist. (Recommended) | |
| Skip Layer 3 entirely | Only Layers 1+2. No auto-detection. | |
| Detect + write to import-log only | Auto-detect, use in-memory, advisory block in import-log.md. | |
| Other (free text: "write-back") | User typed "write-back" — implies VAULT-06 is in scope. | ✓ |

**User's choice:** Free-text "write-back" (triggered Q3 scope-confirm)

### Q2b: Ship 3 or 4 tag namespaces?

| Option | Description | Selected |
|--------|-------------|----------|
| All 4 namespaces (garden/source/graph/tech) | Full design-note fidelity. `tech/*` derived from `source_file` extensions. (Recommended) | ✓ |
| Only the 3 required by VAULT-02 | Strict REQUIREMENTS.md. No `tech/*` yet. | |

**User's choice:** All 4 namespaces

### Q3: Scope confirm after Layer-3 write-back answer

| Option | Description | Selected |
|--------|-------------|----------|
| Yes — VAULT-01..07 all in scope | Full design-note scope. 7 REQ-IDs. Planner adds VAULT-06/07 to REQUIREMENTS.md. | ✓ |
| No — detect + use in-memory, skip persistence | Keep earlier decision: VAULT-07 yes, VAULT-06 no. | |
| Write-back only, skip Layer 3 in-memory | Detected, persisted, but not applied to current run. | |

**User's choice:** Yes — VAULT-01..07 all in scope

---

## Architecture & CLI

### Q1: Relationship to existing `to_obsidian` / `compute_merge_plan` / `approve`?

| Option | Description | Selected |
|--------|-------------|----------|
| Standalone module | New `vault_promote.py`, no calls into `to_obsidian` or `compute_merge_plan`. Reuses templates and profile loaders only. (Recommended) | ✓ |
| Reuse mapping + merge | Calls `classify()` + `compute_merge_plan()` with a `write_only` policy preset. | |
| Thin wrapper over `to_obsidian` | Adds `promotion_gate` / `write_only` kwargs to existing function. | |

**User's choice:** Standalone module
**Notes:** Avoids inheriting merge-engine complexity (SKIP_CONFLICT, REPLACE, ORPHAN) that conflicts with write-only semantics.

### Q2: CLI shape — subcommand or flag?

| Option | Description | Selected |
|--------|-------------|----------|
| Subcommand: `graphify vault-promote` | Matches `harness`/`approve`/`install` family. (Recommended) | ✓ |
| Flag: `graphify --vault-promote` | Matches `--obsidian`/`--diagram-seeds` family. | |

**User's choice:** Subcommand

### Q3: Which existing utilities does `vault_promote.py` reuse? (multi-select)

| Option | Description | Selected |
|--------|-------------|----------|
| profile.py loaders | `load_profile()`, `validate_profile()`. (Recommended) | ✓ |
| security.py guards | `validate_vault_path()`, `safe_filename()`, `safe_tag()`, `safe_frontmatter_value()`. (Recommended) | ✓ |
| builtin_templates/ | Reuse 6 existing templates; add `question.md`, `quote.md`. (Recommended) | ✓ |
| analyze.py outputs | `god_nodes()`, `knowledge_gaps()` drive promotion-gate + Questions dispatch. (Recommended) | ✓ |

**User's choice:** All four

### Q4: Coexistence with `graphify approve`?

| Option | Description | Selected |
|--------|-------------|----------|
| Both supported, independent | Non-breaking. Users pick based on preference. (Recommended) | ✓ |
| vault-promote supersedes approve | Deprecate approve. Breaking change. | |
| vault-promote chains into approve | Two-step flow. Contradicts VAULT-01. | |

**User's choice:** Both supported, independent

---

## Classifier & scoring

### Q1: What does `--threshold N` gate on?

| Option | Description | Selected |
|--------|-------------|----------|
| Node degree only | `G.degree(node) >= N`. (Recommended) | ✓ |
| Composite score | `graphifyScore = degree + 3*god + 5*gap`. | |
| Disjunctive gate (design note) | `degree >= N OR is_god_node OR type in {decision, question, quote}`. | |

**User's choice:** Node degree only

### Q2: What populates `Atlas/Dots/Questions/`?

| Option | Description | Selected |
|--------|-------------|----------|
| analyze.py `knowledge_gaps()` | Isolated, thin-community, high-ambiguity. Always promoted regardless of threshold. (Recommended) | ✓ |
| Only high-ambiguity subset | AMBIGUOUS on >50% of edges. | |
| Explicit node_type tag | `file_type="rationale"` or label with `?`. | |

**User's choice:** `knowledge_gaps()`

### Q3: What populates `Atlas/Dots/Things/`?

| Option | Description | Selected |
|--------|-------------|----------|
| god_nodes, non-code | `god_nodes()` filtered to `file_type != "code"`. (Recommended) | ✓ |
| All degree>=N non-code nodes | Broader. | |
| Profile-driven via `mapping.classify` | Max configurability, re-introduces mapping-rules complexity. | |

**User's choice:** god_nodes non-code

### Q4: What about the other 5 folders (Maps, Statements, Quotes, People, Sources)?

| Option | Description | Selected |
|--------|-------------|----------|
| Maps + Sources only | Statements/Quotes/People skipped — no reliable detector. (Recommended) | |
| All 7 folders, heuristic dispatch | People regex, Quotes doc+marks, Statements relation='defines'. Noisy but design-note-faithful. | ✓ |
| Maps + Sources + People | Middle ground. | |

**User's choice:** All 7 folders, heuristic dispatch

### Q5: Map MOC frontmatter beyond `stateMaps: 🟥`?

| Option | Description | Selected |
|--------|-------------|----------|
| stateMaps + collections union | `stateMaps: 🟥`, `collections:` listing members, `up: [[Atlas]]`. No `related:`. (Recommended) | ✓ |
| Full Ideaverse Map frontmatter | Add `stateReviewed`, `mapRank`, `mapConfidence`. | |

**User's choice:** stateMaps + collections union

---

## Write semantics & tags

### Q1: Re-run strategy for self-created notes?

| Option | Description | Selected |
|--------|-------------|----------|
| Overwrite self, skip foreign | Sidecar `vault-manifest.json`: path→content-hash. Hash match = overwrite; mismatch or absent = skip+log. (Recommended) | ✓ |
| Skip if exists, require --force | First run writes, subsequent skips. `--force` overwrites. | |
| Always overwrite self (sentinel-preserved) | Reuse v1.1 `GRAPHIFY_USER_START/END` blocks. | |

**User's choice:** Overwrite self, skip foreign

### Q2: Collision handling?

| Option | Description | Selected |
|--------|-------------|----------|
| Skip + log in import-log.md | Under `## Skipped`, path + reason. Run proceeds. (Recommended) | ✓ |
| Skip + stderr warning + log | Loud but traceable. | |
| Abort run, require --force | Strictest. | |

**User's choice:** Skip + log in import-log.md

### Q3: Tag taxonomy baseline?

| Option | Description | Selected |
|--------|-------------|----------|
| Design note verbatim | Full enumerations for garden/graph/source/tech. (Recommended) | ✓ |
| Minimal baseline | Just enough to satisfy VAULT-02; rely on user overrides. | |
| file_type-aligned baseline | Match extractor `file_type` enum. | |

**User's choice:** Design note verbatim

### Q4: `import-log.md` format across runs?

| Option | Description | Selected |
|--------|-------------|----------|
| Append, latest-first | Prepend `## Run YYYY-MM-DDTHH:MM` block. History grows. (Recommended) | ✓ |
| Replace each run | Single snapshot. Loses history. | |
| Append + rotate | Rotate to archive after N=20 runs. | |

**User's choice:** Append, latest-first

---

## Claude's Discretion

- Exact regex/predicate tuning for People/Quotes/Statements heuristics (Unicode, locale handling).
- Internal JSON shape of `graphify-out/vault-manifest.json` (versioning, timestamp fields).
- Whether `question.md` and `quote.md` templates are separate files in `builtin_templates/` or inlined strings (lean toward separate files per existing convention).
- Test file organization (`tests/test_vault_promote.py` as a new file per CLAUDE.md's one-file-per-module convention).

## Deferred Ideas

- Sentinel-block preservation via `GRAPHIFY_USER_START/END` inside promoted notes.
- ACE-Aligned Vocabulary candidate phase (ROADMAP.md §146) — not subsumed by VAULT-07; remains as-is for v1.6+.
- Extended Map frontmatter (`mapRank`, `mapConfidence`, `stateReviewed`).
- More precise detectors for People/Quotes/Statements.
