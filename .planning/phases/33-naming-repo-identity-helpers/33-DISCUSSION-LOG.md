# Phase 33: Naming & Repo Identity Helpers - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-04-28
**Phase:** 33-Naming & Repo Identity Helpers
**Areas discussed:** Repo identity shape and precedence, Concept naming policy, Naming cache stability

---

## Repo Identity Shape and Precedence

| Question | Options Considered | Selected |
|----------|--------------------|----------|
| What should the resolved repo identity be optimized for? | Short stable slug; remote-derived owner/repo; display name plus slug; you decide | Short stable slug |
| How should graphify report which identity source won? | stderr and manifest; manifest/frontmatter only; dry-run only; you decide | stderr and manifest |
| Where should profile-supplied repo identity live? | Top-level `repo:` block; `naming.repo_identity`; `metadata.repo_identity`; you decide | Top-level `repo:` block |
| What fallback should win? | Git remote slug then current directory; current directory only; remote or error; you decide | Git remote slug then current directory |

**User's choice:** Short readable repo slug with CLI > profile > fallback precedence, visible in stderr and manifest.
**Notes:** The profile key should be top-level because repo identity is broader than filename formatting.

---

## Concept Naming Policy

| Question | Options Considered | Selected |
|----------|--------------------|----------|
| Should LLM concept naming be enabled by default? | Default-on with fallback; profile opt-in only; CLI opt-in only; you decide | Default-on with fallback |
| How much profile control is needed? | Enable/disable plus budget/style hints; enable/disable only; full prompt template; you decide | Enable/disable plus budget/style hints |
| What if the LLM title is unsafe or weak? | Reject and fallback; sanitize and use; fail run; you decide | Reject and fallback |
| What should fallback names look like? | Top meaningful terms plus id/hash; plain Community N; top node label; you decide | Top meaningful terms plus id/hash |

**User's choice:** Readable LLM names by default, with small safe profile controls and deterministic fallback for invalid or unavailable LLM output.
**Notes:** Fallback names should remain useful in a vault sidebar, not regress to opaque community numbering.

---

## Naming Cache Stability

| Question | Options Considered | Selected |
|----------|--------------------|----------|
| What should be the primary cache key? | Community signature; community id; top-node signature; you decide | Community signature |
| How sensitive should invalidation be? | Tolerate small changes; exact signature only; never invalidate; you decide | Tolerate small changes |
| Where should cache/provenance live? | `graphify-out/` sidecar; vault `.graphify/`; frontmatter only; you decide | `graphify-out/` sidecar |
| Should manual overrides ship in v1.8 Phase 33? | Not now, design for future overrides; profile overrides now; frontmatter preserve now; you decide | Not now, design for future overrides |
| How should users force refresh? | Defer explicit UI but keep format ready; add force flag now; manual sidecar deletion; you decide | Defer explicit UI |

**User's choice:** Cache by semantic community signature, tolerate small graph drift, store generated provenance in `graphify-out/`, and keep manual override/refresh behavior out of this phase.
**Notes:** Phase 33 should avoid growing into an approval or manual naming workflow.

---

## Claude's Discretion

None.

## Deferred Ideas

None.
