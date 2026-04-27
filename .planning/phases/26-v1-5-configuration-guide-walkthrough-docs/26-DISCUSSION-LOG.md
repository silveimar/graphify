# Phase 26: v1.5 Configuration Guide & Walkthrough Docs - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-04-27
**Phase:** 26-v1-5-configuration-guide-walkthrough-docs
**Areas discussed:** Guide location & filename, Sample vault for walkthrough, Custom diagram_type example, MCP tool docs structure, README link placement

---

## Guide Location & Filename

| Option | Description | Selected |
|--------|-------------|----------|
| CONFIGURING_V1_5.md at root | Matches existing INSTALLATION.md / ARCHITECTURE.md / SECURITY.md / CHANGELOG.md / CLAUDE.md convention. No docs/ dir exists today. | ✓ |
| docs/v1.5-configuration.md | Establishes a docs/ tree for future per-feature guides. Cleaner long-term but introduces a new convention. | |
| docs/configuring-v1.5.md | Same as above but kebab-case filename. Still introduces docs/ as a new pattern. | |

**User's choice:** CONFIGURING_V1_5.md at root (recommended)
**Notes:** Phase 26 explicitly declines to introduce a `docs/` tree — single-file at root preserves the existing user-facing-doc convention.

---

## Sample Vault for Walkthrough

| Option | Description | Selected |
|--------|-------------|----------|
| Inline-described vault with synthetic snippets | Describe a hypothetical small vault with tree diagrams + synthetic note snippets in fenced blocks. Zero new fixtures to maintain. | ✓ |
| Ship a tiny in-repo fixture under examples/v1_5_walkthrough/ | Copy-pasteable, executable demo. Adds maintenance surface and pulls vault content into the repo. | |
| Reference an external Ideaverse vault + minimal inline snippets | Lower repo footprint but ties guide to an external dependency. | |

**User's choice:** Inline-described vault with synthetic snippets (recommended)
**Notes:** Reader copies snippets into their own vault. Guide does not promise an executable demo path; this keeps it maintenance-free as commands evolve.

---

## Custom diagram_type Example (DOCS-02)

| Option | Description | Selected |
|--------|-------------|----------|
| decision-tree | God-node + branching paths. Strong fit for D-06 gating (≥3 outbound branches) and D-07 tiebreak (highest betweenness). Visually intuitive. | ✓ |
| user-journey | Sequential flow with decision points. Weaker D-06 story — most graphs lack explicit "step N" ordering. | |
| state-machine | States + transitions. Strong topology fit but narrow appeal. | |
| dependency-map | Overlaps with built-in module/import view; risks confusing readers about what "custom" means. | |

**User's choice:** decision-tree (recommended)
**Notes:** Concrete D-06 threshold = ≥3 outbound branches; concrete D-07 tiebreak = highest betweenness centrality. Readers can transfer the pattern to their own custom types.

---

## MCP Tool Docs Structure (DOCS-03)

| Option | Description | Selected |
|--------|-------------|----------|
| Dedicated section in the guide | `## MCP Tool Integration` section near the end of CONFIGURING_V1_5.md with subsections per tool. | ✓ |
| Separate appendix file | MCP-TOOLS.md as a sibling, linked from the guide. Cleaner separation but two docs to maintain. | |
| Inline at the relevant pipeline step | Document each tool where it first appears. Fragments reference material. | |

**User's choice:** Dedicated section in the guide (recommended)
**Notes:** Keeps walkthrough linear and MCP reference discoverable in one file. Section must be reference-quality — agent author can integrate without reading source.

---

## README Link Placement (DOCS-04)

| Option | Description | Selected |
|--------|-------------|----------|
| New `### v1.5 Configuration Guide` subsection under `## Obsidian vault adapter (Ideaverse integration)` | v1.5 features all extend the Obsidian adapter — content stays grouped. | ✓ |
| New top-level `## v1.5 Configuration` section | Maximum visibility but creates a versioned top-level section that needs rework next milestone. | |
| Bullet under `## Install` → `Make your assistant always use the graph` | Treats v1.5 as install/setup; misleading because v1.5 is a feature surface. | |

**User's choice:** New subsection under `## Obsidian vault adapter` (recommended)
**Notes:** Subsection placed AFTER the existing `### Vault Promotion — graphify vault-promote` (README.md:378). One-line pitch + link only — no duplicated abstract.

---

## Claude's Discretion

- Internal section ordering of the walkthrough (mostly determined by the fixed pipeline command order).
- Exact wording, headings beyond major H2s, troubleshooting/FAQ depth (omit if it adds bulk without value).
- Whether to include a brief "What's new in v1.5" framing paragraph at the top (recommended; keep under 5 lines).

## Deferred Ideas

- Locale README updates (`README.ja-JP.md`, `README.ko-KR.md`, `README.zh-CN.md`) — follow-up translation phase.
- Screenshots / animated GIFs — future docs-polish phase.
- `docs/` directory + multi-guide index — defer until there are ≥3 distinct user-facing guides.
- Executable in-repo sample vault under `examples/v1_5_walkthrough/` — its own phase if revisited.
- Troubleshooting / FAQ section depth — Claude's discretion this phase.
- Roadmap line 268 stale plan stub for Phase 26 (`23-01-PLAN.md — Patch dedup.py...`) — flagged for the planner.
