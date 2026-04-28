---
name: SEED-vault-root-aware-cli
description: graphify CLI should detect when CWD is itself an Obsidian vault (presence of `.obsidian/`) and either route output away from the vault root or auto-load the vault profile, rather than dumping `graphify-out/` into the vault and risking re-ingestion
trigger_when: After v1.7 ships the configurable vault adapter and profile loader — OR a user reports surprise about graphify creating files inside their working vault — OR v1.7 scoping considers UX defaults for "running from inside a vault"
planted_during: v1.7 pre-scoping (2026-04-27 /gsd-explore session on obsidian export nesting bug)
planted_date: 2026-04-27
source: /gsd-explore conversation diagnosing nested `graphify-out/obsidian/graphify-out/obsidian/` paths under `~/Documents/work-vault/`
fit: tight
effort: small
---

# SEED: Vault-root-aware CLI

## The idea

When `graphify` runs from a directory that is itself an Obsidian vault (signaled by a `.obsidian/` directory at CWD), the CLI should behave differently than when run from a code repository:

- **Option A — refuse the foot-gun:** error out with an actionable message: *"CWD looks like an Obsidian vault. Pass `--output <path>` to write outside the vault, or `--write-into-vault` to opt in explicitly."*
- **Option B — auto-route:** silently write output to a sibling directory (e.g., `<vault>/.graphify-out/` hidden by default Obsidian ignore patterns) instead of `<vault>/graphify-out/`
- **Option C — auto-adopt:** if the vault has a `.graphify/profile.yaml`, treat CWD as both the input corpus and the output target, and let the v1.7 vault adapter handle placement (the "ideal" path once v1.7 ships)

## Why this is a seed, not a todo

The v1.6 self-ingestion bug fix (in `.planning/todos/pending/fix-detect-self-ingestion-graphify-out.md`) addresses the *immediate* symptom by excluding `graphify-out/` from detection. But it doesn't answer the deeper UX question: *should graphify even be writing `graphify-out/` into a real working Obsidian vault?*

That question only becomes answerable once v1.7's vault adapter exists, because the answer depends on whether placement is profile-driven (Option C is clean) or still source-path-driven (Option A is the safest stopgap).

## Trigger conditions in detail

Surface this seed when **any** of:

1. `/gsd-new-milestone v1.7` scopes Configurable Vault Adapter UX defaults
2. A user reports surprise about graphify creating files inside their working vault
3. A v1.7+ phase considers "what does graphify do when CWD has `.obsidian/`?" as a design question
4. A retrospective notes recurring user confusion about output destination

## Implementation sketch (when picked up)

- Add `_is_obsidian_vault(path: Path) -> bool` to `detect.py` (checks `path / ".obsidian"`)
- In `__main__.py`'s `run` command, branch on this check before invoking the pipeline
- If vault adapter is present (v1.7 profile loader), prefer Option C; otherwise default to Option A with clear opt-in flag

## Effort estimate

**Small.** ~50 LOC in `__main__.py` + `detect.py`, 2-3 tests, docs update. The bulk of the work is deciding the UX policy (A vs B vs C), which is a design call worth ~20 minutes of conversation, not implementation time.

## Related

- `.planning/todos/pending/fix-detect-self-ingestion-graphify-out.md` — the immediate-fix sibling
- `.planning/notes/obsidian-export-self-ingestion-loop.md` — root cause analysis
- `.planning/notes/v1.7-input-vault-adapter-no-source-mirroring.md` — v1.7 carry-forward that this seed depends on
