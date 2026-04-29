# Phase 34: Mapping, Cluster Quality & Note Classes - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-04-29
**Phase:** 34-Mapping, Cluster Quality & Note Classes
**Areas discussed:** Community output semantics, Cluster-quality floor behavior, CODE note identity, CODE-concept navigation

---

## Community Output Semantics

**Selected:** Disable legacy `_COMMUNITY_*` rendering in default output, coerce legacy `community` requests to MOC with warnings, and make all Obsidian community exports MOC-only.

**Alternatives considered:**
- Remove the runtime legacy render path entirely.
- Skip deprecated community notes with a warning.
- Fail export on deprecated community output requests.
- Limit MOC-only behavior to built-in/default output.

**Notes:** Existing `_COMMUNITY_*` files already in a vault are Phase 35 migration visibility work, not Phase 34.

---

## Cluster-Quality Floor Behavior

**Selected:** Connected below-floor communities nest under the nearest host MOC; hostless/isolate communities route to `_Unclassified`; configured floor values are literal; built-in/default floor becomes `6`.

**Alternatives considered:**
- Route every below-floor community into `_Unclassified`.
- Omit isolate communities from all community MOCs.
- Preserve the existing default floor of `3`.
- Defer routing visibility to tests only.

**Notes:** Phase 34 should emit enough metadata for MOCs and dry-run plans to show standalone, hosted, or bucketed routing.

---

## CODE Note Identity

**Selected:** Add a real `code` note class for code-derived god nodes. Eligible nodes require `file_type: code` plus a real `source_file`, excluding concept nodes and file hubs. Filenames use `CODE_<repo>_<node>.md`, with deterministic hash suffixes on collision.

**Alternatives considered:**
- Keep CODE notes internally as `thing` with a filename/tag convention.
- Qualify CODE notes by source-file extension only.
- Convert all god nodes to CODE notes.
- Use source-path suffixes or fail on filename collisions.

**Notes:** Collision provenance should be available in metadata/dry-run.

---

## CODE-Concept Navigation

**Selected:** Bidirectional CODE↔concept navigation should exist in both frontmatter and body wikilinks. CODE notes point `up:` to their concept MOC. Concept MOCs list CODE-eligible god-node members, sorted by degree then label and capped for readability.

**Alternatives considered:**
- Frontmatter-only links.
- Body-only links.
- Dedicated relationship fields only.
- Context-only Phase 34 with all rendering deferred to Phase 35.

**Notes:** Phase 34 should include minimal rendering/tests proving the links exist; Phase 35 polishes final templates and export visibility.

## Claude's Discretion

- Exact warning text.
- Metadata field names for routing/collision provenance.
- CODE member listing cap, as long as it is deterministic and readability-oriented.

## Deferred Ideas

- Legacy `_COMMUNITY_*` vault scan and migration candidate/orphan reporting — Phase 35.
- Final CODE template polish and migration/dry-run presentation — Phase 35.
- Migration guide, skill alignment, and regression sweep — Phase 36.
