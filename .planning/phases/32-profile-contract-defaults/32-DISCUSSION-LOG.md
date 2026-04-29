# Phase 32: Profile Contract & Defaults - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-04-28
**Phase:** 32-Profile Contract & Defaults
**Areas discussed:** Default taxonomy shape, Profile contract keys, Validation severity and messages, Compatibility and precedence

---

## Folded Todo

| Option | Description | Selected |
|--------|-------------|----------|
| Fold it into Phase 32 decisions | Treat the `ls-vault` profile routing issue as part of the profile/default contract. | yes |
| Review it but keep it deferred/out of scope | Keep the todo visible but outside this phase. | |

**User's choice:** Fold it into Phase 32 decisions.
**Notes:** The no-profile/default contract must prevent generated vault notes from dumping into the vault root.

---

## Default Taxonomy Shape

| Question | User's choice |
|----------|---------------|
| How strict should the Graphify-owned subtree be? | All generated Obsidian notes under `Atlas/Sources/Graphify/`. |
| Where should default non-MOC notes go? | Typed subfolders under `Atlas/Sources/Graphify/`, such as `Things/`, `Statements/`, `People/`, and `Sources/`. |
| Should taxonomy cover notes only or artifacts too? | Notes only; manifests/artifacts keep existing `graphify-out` behavior for this phase. |
| What bucket names should defaults use? | Explicit names: `Graphify`, `MOCs`, and `_Unclassified`, while considering previously defined naming standards. |

**Notes:** The user asked for the difference between notes-only and all-output artifact scope. After clarification, they selected notes-only.

---

## Profile Contract Keys

| Question | User's choice |
|----------|---------------|
| How should the new cluster-quality key be expressed? | `mapping.min_community_size` as canonical. |
| How should conflict with existing `clustering.min_community_size` requirement wording resolve? | Use `mapping.min_community_size` and update requirement wording/traceability. |
| Should Phase 32 introduce an explicit taxonomy key? | Add a top-level `taxonomy:` block. |
| How should deprecated community overview output be represented? | Hard-deprecated warning, not fatal yet. |
| Should built-in defaults carry new keys? | Put new defaults directly in `_DEFAULT_PROFILE`. |

**Notes:** This intentionally changes the current requirements contract. Downstream planning should update all affected v1.8 references.

---

## Validation Severity And Messages

| Question | User's choice |
|----------|---------------|
| How strict should unsupported/malformed taxonomy validation be? | Errors. |
| What should deprecated community overview warnings say? | Name the deprecated setting/template and point to MOC-only output plus migration guidance. |
| How should `mapping.moc_threshold` interact with `mapping.min_community_size`? | `mapping.moc_threshold` becomes invalid immediately; users must migrate. |
| Should compatibility requirements be revised for this break? | Yes. |
| Where should validation findings surface? | Both `--validate-profile` and `graphify doctor`, sharing the same validator/preflight source. |

**Notes:** The user asked whether `mapping.moc_threshold` and `mapping.min_community_size` are the same. We clarified they are effectively the same policy surface, with the latter as the clearer v1.8 replacement.

---

## Compatibility And Precedence

| Question | User's choice |
|----------|---------------|
| If `taxonomy:` and explicit `folder_mapping` both define folder placement, which wins? | `taxonomy:` wins. |
| What should no-profile/default behavior guarantee for the folded todo? | Claude discretion: preserve non-vault behavior, but Obsidian/vault note output must use the Graphify-owned subtree and not the vault root. |
| How should existing profiles without new keys behave? | They must add new keys to pass validation; no backward compatibility needed for this branch. |
| How aggressively should requirements update? | Update all v1.8 requirement and roadmap references now. |

**Notes:** The user explicitly said there is no profile being used now, so backward compatibility is not needed.

---

## Claude's Discretion

- Preserve prior non-vault output behavior unless implementation research finds a conflict with the v1.8 contract.
- Interpret the no-root guarantee as scoped to Obsidian/vault note output.

## Deferred Ideas

None.
