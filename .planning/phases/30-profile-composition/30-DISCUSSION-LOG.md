# Phase 30: Profile Composition - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-04-28
**Phase:** 30-profile-composition
**Areas discussed:** extends vs includes semantics, Fragment path resolution & layout, Per-community template pattern matching, Lost-fields diff format

---

## extends vs includes semantics

### Q1: Composition primitive(s)

| Option | Description | Selected |
|--------|-------------|----------|
| Both extends: and includes: | Single-parent inheritance + ordered mixin list. Most expressive. | ✓ |
| Only extends: (string or list) | One field, accepts string or list. | |
| Only includes: (ordered list) | Single field, list of paths. | |

### Q2: Resolution order when both present

| Option | Description | Selected |
|--------|-------------|----------|
| extends: first, then includes:, then own fields | ESLint/TS convention. | ✓ |
| includes: first, then extends:, then own fields | Reversed precedence. | |
| Reject — forbid both in same profile | Validation error. | |

### Q3: extends: shape

| Option | Description | Selected |
|--------|-------------|----------|
| String only — single parent | Strict single-parent chain. | ✓ |
| String or list — multi-parent allowed | Flexible but blurs lines with includes:. | |

### Q4: Cycle error reporting

| Option | Description | Selected |
|--------|-------------|----------|
| Stderr + non-zero exit, print full chain | Matches existing profile error pattern. | ✓ |
| Same, but graceful fallback on load_profile() | Validate fails hard, load falls back. | |
| Raise exception — hard fail everywhere | Strictest. | |

**Notes:** D-04 ended up combining options 1 and 2 — non-zero exit from `--validate-profile`, graceful stderr-fallback from `load_profile()`. Honors the existing "graphify never crashes from a bad vault profile" contract.

---

## Fragment path resolution & layout

### Q1: Path resolution semantics

| Option | Description | Selected |
|--------|-------------|----------|
| Anywhere under .graphify/, paths relative to referencing file | Sibling-relative, user organizes. | ✓ |
| Strict — only .graphify/fragments/ allowed | Enforces structure. | |
| Relative to .graphify/ root regardless of file | One mental model. | |

### Q2: External path scope

| Option | Description | Selected |
|--------|-------------|----------|
| Strict — reject anything outside .graphify/ | Reuses v1.0 path-traversal guard. | ✓ |
| Allow absolute paths for org-wide bases | Higher attack surface. | |
| Allow ~/.graphify/ user-global fragments | Middle ground. | |

### Q3: Fragment validation

| Option | Description | Selected |
|--------|-------------|----------|
| Partial allowed — only composed validates | ESLint/TS-config convention. | ✓ |
| Each fragment validates independently | Stricter, more repetition. | |

### Q4: Recursion depth cap

| Option | Description | Selected |
|--------|-------------|----------|
| Hard cap at depth 8 | Belt-and-suspenders. | ✓ |
| Generous cap at 16 | Allows deep hierarchies. | |
| No cap — cycle detection alone | Trust the cycle detector. | |

---

## Per-community template pattern matching

### Q1: Match field

| Option | Description | Selected |
|--------|-------------|----------|
| Both ID and label, explicit field selector | No ambiguity. | ✓ |
| Label only | Simpler, IDs unstable across runs. | |
| Both, auto-detected from pattern type | Less verbose, magic-prone. | |

### Q2: Pattern syntax

| Option | Description | Selected |
|--------|-------------|----------|
| fnmatch-style globs | stdlib, no new deps, familiar. | ✓ |
| Exact match + literal substring | Simplest. | |
| Regex | Maximum power, ReDoS risk. | |

### Q3: Schema location

| Option | Description | Selected |
|--------|-------------|----------|
| New top-level: community_templates | Mirrors mapping_rules. | ✓ |
| Nested under existing mapping_rules entries | Coupled. | |
| Nested under obsidian: section | Obsidian-only scope. | |

### Q4: Override scope

| Option | Description | Selected |
|--------|-------------|----------|
| MOC only — community-level template | Smallest, clearest. | ✓ |
| Any note type within community, keyed by type | More expressive. | |
| All notes inherit one template | Simplest schema. | |

---

## Lost-fields diff format

### Q1: When the diff runs

| Option | Description | Selected |
|--------|-------------|----------|
| Every --validate-profile run: chain + provenance | Single entry point. | ✓ |
| On-demand via --explain-removal flag | Targeted, more flags. | |
| Always run two-pass diff in --validate-profile | Most explicit, slowest. | |

### Q2: Output format

| Option | Description | Selected |
|--------|-------------|----------|
| Plain text, dotted keys | Matches existing style, grep-friendly. | ✓ |
| JSON via --json flag | Tooling/CI ready. | |
| Tree-style with nesting | Prettier, harder to grep. | |

### Q3: Resolved community templates section

| Option | Description | Selected |
|--------|-------------|----------|
| Yes — same output, add Resolved community templates: | Single overview. | ✓ |
| Separate flag: --show-templates | Cleaner default. | |

### Q4: Graph context handling

| Option | Description | Selected |
|--------|-------------|----------|
| List rules as written + note that resolution requires graph | Graph-blind preflight. | ✓ |
| Auto-load graph.json if present | Best UX, more code paths. | |
| Require explicit --graph flag | Verbose. | |

---

## Claude's Discretion

- Visual formatting details of the new `--validate-profile` sections (delimiters, spacing).
- Internal API split between resolver and merger (named e.g. `_resolve_profile_chain()`).
- Cycle/depth check ordering and exact error wording.
- Test fixture layout under `tests/fixtures/profiles/`.

## Deferred Ideas

- `--validate-profile --json` output.
- `--explain-removal <fragment>` targeted-diff flag.
- Tree-style provenance rendering.
- Auto-resolving community-to-template assignments by loading `graphify-out/graph.json`.
- Org-wide / user-global fragments (absolute paths, `~/.graphify/`).
- Per-type community template overrides beyond MOC.
- Multi-parent `extends:` (string-or-list).
- Regex pattern syntax for community_templates.
