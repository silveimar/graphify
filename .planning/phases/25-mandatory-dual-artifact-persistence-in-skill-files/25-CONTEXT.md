---
phase: 25
phase_name: Mandatory Dual-Artifact Persistence in Skill Files
phase_slug: mandatory-dual-artifact-persistence-in-skill-files
milestone: v1.6
created: 2026-04-27
requirements: [SKILLMEM-01, SKILLMEM-02, SKILLMEM-03, SKILLMEM-04]
---

# Phase 25 — Context

<domain>
Every skill-file variant graphify ships ("graphify/skill*.md", twelve files
listed in `_PLATFORM_CONFIG` at `graphify/__main__.py:49`) carries a
"Mandatory response persistence" contract. The contract requires every
interactive `query` / `path` / `explain` / `analyze` invocation in any LLM
harness to write a paired pair of files under `graphify-out/memory/`:

- `CMD_<TS>_<SLUG>.human.md` — prose response shown to the user
- `CMD_<TS>_<SLUG>.graph.md` — YAML frontmatter + fenced JSON sub-extraction

A regression test in `tests/` grep-asserts a stable canary string in every
file referenced by `_PLATFORM_CONFIG[*].skill_dst` after `graphify install`,
locking the contract's presence and preventing silent drift across variants.
</domain>

<canonical_refs>
- `.planning/ROADMAP.md` — Phase 25 entry (goal, success criteria, requirements)
- `.planning/REQUIREMENTS.md` — SKILLMEM-01..SKILLMEM-04 (full requirement text)
- `graphify/skill.md` — master skill file, source of the verbatim contract block
- `graphify/skill-aider.md`, `skill-claw.md`, `skill-codex.md`, `skill-copilot.md`,
  `skill-droid.md`, `skill-excalidraw.md`, `skill-opencode.md`, `skill-trae.md`,
  `skill-windows.md` — verbatim-copy destinations
- `graphify/__main__.py:49-155` — `_PLATFORM_CONFIG` dict (12 entries driving
  `install`'s `skill_file` → `skill_dst` copy)
- `tests/test_install.py` — closest analog test pattern for the new regression
  (Phase 24 added subpath-isolation tests; same pytest conventions apply)
</canonical_refs>

<code_context>
- **`_PLATFORM_CONFIG` entries (12)**: claude, codex, opencode, aider, copilot,
  openclaw, droid, trae, trae-cn, agent (Cursor variant), excalidraw, windows.
  Two derivations (gemini, antigravity) are handled inline in `__main__.py`
  near line 248 / 381 and reuse `skill.md` directly. Per SKILLMEM-02, the
  excalidraw variant (different skill, only 83 lines) is NOT in scope for the
  persistence contract — it does not expose `query`/`path`/`explain`/`analyze`.
- **Existing structure of `graphify/skill.md`**: 1819 lines.
  - `## Usage` at line 12
  - `## Available slash commands` at line 46
  - `## What graphify is for` at line 55
  - Per-command sections: query (1085), path (1212), explain (1285), add (1351),
    analyze (1385)
- **No persistence language exists today.** Confirmed by grep across all
  `graphify/skill*.md` — `Mandatory response persistence`, `graphify-out/memory`,
  and `CMD_` are absent. Greenfield content addition.
- **Variants are near-clones** of `skill.md` (1294–1819 lines, mostly identical
  prose with tiny per-harness deltas). The `## Usage` / `## Available slash
  commands` neighbor structure exists in every variant, so the chosen
  insertion point translates 1:1 across files.
- **TDD/regression analog**: Phase 24 added 3 subpath-isolation tests
  (`test_routing_audit.py:12`, `test_capability.py:409`,
  `test_vault_promote.py:824`). Phase 25's regression test follows the same
  shape — one parameterized test iterating `_PLATFORM_CONFIG[*].skill_dst`.
</code_context>

<decisions>

### Canary string

**Decision:** Hidden HTML-comment sentinel `<!-- graphify:persistence-contract:v1 -->`
placed on the line immediately above the `## Mandatory response persistence`
heading.

- Invisible in rendered markdown — does not pollute the LLM's read of the
  prose contract.
- Survives any future paraphrase of heading or body across platform variants.
- Version-bumpable (`:v2`) when the contract evolves; old skill files with
  `:v1` then fail the regression test, forcing a re-emit.
- SKILLMEM-04 grep is a one-liner: `grep -F "<!-- graphify:persistence-contract:v1 -->"`
  per `_PLATFORM_CONFIG[*].skill_dst`.

### Filename schema

**Decision:** `CMD_<TS>_<SLUG>.{graph,human}.md`

- `<TS>` = `YYYYMMDDTHHMMSSZ` (UTC, compact ISO-8601 basic, no colons).
  Lex-sortable; `ls graphify-out/memory/` lists chronologically with no flags.
- `<SLUG>` = `<command-kind>-<first-6-tokens>`, lowercased, hyphenated,
  non-alphanumerics stripped, max 64 chars total. Example:
  `query-transformer-attention-deep-residual-skip`.
- `<command-kind>` ∈ {`query`, `path`, `explain`, `analyze`}.
- Both files of a pair share identical `<TS>_<SLUG>` — they are a unit.

Example: `CMD_20260427T154200Z_query-transformer-attention.{graph,human}.md`

### Artifact content schema

**Decision:** Split by audience.

`<base>.human.md` — prose response shown to the user.
- Plain markdown.
- No required frontmatter (so the file reads naturally if a user opens it).

`<base>.graph.md` — structured artifact for downstream tooling.
- YAML frontmatter (required keys):
  - `command` — one of `query|path|explain|analyze`
  - `prompt` — verbatim user prompt that triggered the response
  - `timestamp` — ISO-8601 with offset (`2026-04-27T15:42:00Z`)
  - `graph_path` — relative path to the graph JSON the response read from
  - `status` — `ok` | `error` | `empty`
  - `nodes_touched` — list of node IDs the response cited
  - `edges_touched` — list of edge IDs (or empty)
  - `communities_touched` — list of community IDs (or empty)
- Body: a single fenced ` ```json ` block containing the full sub-extraction
  (nodes, edges, communities) the response was built from. Empty arrays
  permitted on `error` / `empty`.

Downstream tooling can `glob graphify-out/memory/*.graph.md` and read frontmatter
without parsing prose — a deliberate concession to mechanical readability.

### Propagation strategy (verbatim vs paraphrase)

**Decision:** Single source, copied verbatim across all in-scope variants.

- The contract block (sentinel + `## Mandatory response persistence` heading
  + body) is authored once in `graphify/skill.md` and copied byte-for-byte
  into every other variant `_PLATFORM_CONFIG` references for graphify's core
  skill: `skill.md`, `skill-codex.md`, `skill-opencode.md`, `skill-aider.md`,
  `skill-copilot.md`, `skill-claw.md`, `skill-droid.md`, `skill-trae.md`,
  `skill-windows.md`. (Both `trae` and `trae-cn` entries reference
  `skill-trae.md`, so 9 source files cover 12 platform entries.)
- `skill-excalidraw.md` is OUT OF SCOPE (different skill; no
  query/path/explain/analyze surface).
- Per-platform tone tweaks are explicitly NOT permitted for the contract
  block. The surrounding skill text remains free to differ per variant.
- Drift defense: SKILLMEM-04's regression test is augmented with an
  identity check — the bytes of the contract block (sentinel through closing
  marker) must be byte-equal across all in-scope variants. Plan can
  implement this as a separate parameterized test or a single
  `assert all(blocks[0] == b for b in blocks)`.

### Trigger scope and error semantics

**Decision:** Contract fires on every interactive `query` / `path` / `explain`
/ `analyze` invocation — including errors and empty-result responses.

- Errors: `.human.md` carries the failure message a user would see;
  `.graph.md` frontmatter has `status: error` and empty `nodes_touched` /
  `edges_touched` / `communities_touched`. The fenced JSON body is `{}`.
- Empty results (e.g., `query` matched zero nodes): `status: empty`, empty
  arrays, fenced JSON body still present and well-formed.
- Idempotency: if `<TS>_<SLUG>` collides (sub-second repeat invocation with
  identical prompt), append `-1`, `-2`, … to the slug. The contract states
  this rule explicitly so harnesses converge.
- The persistence write is a contract on the harness, not on the Python
  CLI — `graphify` itself does not write these files. They are produced by
  whichever LLM is reading the skill.

### Section placement

**Decision:** Top-of-file global preamble.

- Insert the new `## Mandatory response persistence` section (preceded by the
  sentinel comment) immediately after `## Usage` (currently line 12) and
  before `## Available slash commands` (currently line 46) in
  `graphify/skill.md` and the corresponding analogous position in every
  in-scope variant.
- Single insertion point per file — verbatim copy is mechanical.
- Highest visibility: every LLM that reads the skill encounters the contract
  before any per-command instructions, so per-command sections do not need
  to repeat it.
- The contract body references the four commands by name; readers do not
  lose context.

</decisions>

<spec_lock>
No SPEC.md was created for Phase 25. Requirements are locked in
`.planning/REQUIREMENTS.md` (SKILLMEM-01..SKILLMEM-04). The decisions above
extend those requirements with the implementation choices needed for
research / planning.
</spec_lock>

<deferred_ideas>
- **`graphify add` persistence**: not in SKILLMEM scope (success criteria
  list only `query`/`path`/`explain`/`analyze`). If we want `add`-time
  audit trails later, file as new SKILLMEM-05 in v1.7+.
- **`skill-excalidraw.md` persistence**: out of scope this phase; revisit
  only if excalidraw-diagram skill grows interactive query commands.
- **Memory-dir retention policy / GC**: contract specifies writes only;
  rotation, compaction, and TTL are a separate ops concern. Defer to the
  v1.5 configuration docs phase or a future hardening phase.
- **Harness-side validator** (a `graphify` subcommand that lints
  `graphify-out/memory/` for schema conformance): valuable but out of
  scope for SKILLMEM-01..04. Capture as a v1.7 candidate.
</deferred_ideas>

<next_steps>
- `/gsd-plan-phase 25` (auto-advance via `--chain`)
- Researcher should focus on: (a) closest pattern for parameterized
  regression test that iterates `_PLATFORM_CONFIG`, (b) any existing
  install-time test infrastructure that mocks `Path.home()`, and (c)
  whether any harness already documents a similar persistence convention
  (codex memory, copilot artifacts) that we should align wording with
  while keeping the contract block byte-equal.
</next_steps>
