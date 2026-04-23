---
phase: 260416-okg
plan: 01
type: execute
wave: 1
depends_on: []
files_modified:
  - graphify/skill.md
  - graphify/skill-codex.md
  - graphify/skill-opencode.md
  - graphify/skill-claw.md
  - graphify/skill-droid.md
  - graphify/skill-trae.md
  - graphify/skill-aider.md
  - graphify/skill-copilot.md
  - graphify/skill-windows.md
autonomous: true
requirements:
  - QUICK-260416-okg
user_setup: []

must_haves:
  truths:
    - "Every skill variant that has a top-of-file `## Usage` cheat-sheet lists the three `/graphify analyze` forms."
    - "The inserted entries appear immediately after the `/graphify explain \"SwinTransformer\"` line and before the closing triple-backtick of the Usage block."
    - "Hash-comment column alignment (column 55) matches the existing Usage entries in each file."
    - "No other section of any skill variant is modified — in particular, the `## For /graphify analyze` orchestration block in `graphify/skill.md` is untouched."
    - "No ASCII-unsafe characters (emojis, `→`) are introduced."
  artifacts:
    - path: "graphify/skill.md"
      provides: "Master Claude Code skill — Usage block now documents /graphify analyze (3 lines)."
      contains: "/graphify analyze                                      #"
    - path: "graphify/skill-codex.md"
      provides: "Codex skill variant Usage cheat-sheet updated."
      contains: "/graphify analyze                                      #"
    - path: "graphify/skill-opencode.md"
      provides: "OpenCode skill variant Usage cheat-sheet updated."
      contains: "/graphify analyze                                      #"
    - path: "graphify/skill-claw.md"
      provides: "OpenClaw skill variant Usage cheat-sheet updated."
      contains: "/graphify analyze                                      #"
    - path: "graphify/skill-droid.md"
      provides: "Factory Droid skill variant Usage cheat-sheet updated."
      contains: "/graphify analyze                                      #"
    - path: "graphify/skill-trae.md"
      provides: "Trae skill variant Usage cheat-sheet updated."
      contains: "/graphify analyze                                      #"
    - path: "graphify/skill-aider.md"
      provides: "Aider skill variant Usage cheat-sheet updated."
      contains: "/graphify analyze                                      #"
    - path: "graphify/skill-copilot.md"
      provides: "Copilot skill variant Usage cheat-sheet updated."
      contains: "/graphify analyze                                      #"
    - path: "graphify/skill-windows.md"
      provides: "Windows skill variant Usage cheat-sheet updated."
      contains: "/graphify analyze                                      #"
  key_links:
    - from: "Top-of-file Usage block in each skill variant"
      to: "## For /graphify analyze section (skill.md:1224 and equivalents)"
      via: "Consistent verb documentation — cheat-sheet entries advertise the verb that the per-verb orchestration section implements."
      pattern: "/graphify analyze"
---

<objective>
Close a documentation drift: the `/graphify analyze` verb (shipped in Phase 9 of v1.2, autoreason tournament across 4 lenses) is fully orchestrated in `graphify/skill.md` at line 1224 (`## For /graphify analyze`), but the top-of-file `## Usage` cheat-sheet in all 9 skill variants never got updated to list it.

Purpose: Restore cheat-sheet <-> orchestration consistency across all 9 AI-coding-assistant platform variants so users of any platform can discover `/graphify analyze` from the Usage block.

Output: 9 skill variants with three new lines inserted into their Usage code-block (documentation-only change; no code, no tests, no CLI behavior change).
</objective>

<execution_context>
@$HOME/.claude/get-shit-done/workflows/execute-plan.md
@$HOME/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@CLAUDE.md
@graphify/skill.md
</context>

<interfaces>
<!-- The exact 3-line block to insert verbatim. Copy-paste, do not retype. -->
<!-- Hash column is 55 (matches existing entries like `/graphify explain "SwinTransformer"` at skill.md:38). -->

Block to insert (note: trailing-space padding aligns `#` at column 55):

```
/graphify analyze                                      # autoreason tournament: 4 lenses (security, architecture, complexity, onboarding) -> GRAPH_ANALYSIS.md
/graphify analyze for security and architecture        # subset-lens tournament (any of: security, architecture, complexity, onboarding)
/graphify analyze for <lens>                           # single-lens tournament (~6 LLM calls vs ~24 for all 4)
```

Insertion anchor (present in every one of the 9 files, inside the top `## Usage` fenced code-block):

```
/graphify explain "SwinTransformer"                   # plain-language explanation of a node
```

Insert the 3-line block on the line immediately after the anchor, before the closing ``` of the Usage fenced block.

Per-file anchor line numbers (pre-edit; use these as a sanity check, but match by content, not by number):

| File                          | Anchor line |
|-------------------------------|-------------|
| graphify/skill.md             | 38          |
| graphify/skill-codex.md       | 34          |
| graphify/skill-opencode.md    | 34          |
| graphify/skill-claw.md        | 34          |
| graphify/skill-droid.md       | 34          |
| graphify/skill-trae.md        | 34          |
| graphify/skill-aider.md       | 34          |
| graphify/skill-copilot.md     | 36          |
| graphify/skill-windows.md     | 37          |
</interfaces>

<tasks>

<task type="auto">
  <name>Task 1: Insert `/graphify analyze` cheat-sheet entries into all 9 skill variants</name>
  <files>graphify/skill.md, graphify/skill-codex.md, graphify/skill-opencode.md, graphify/skill-claw.md, graphify/skill-droid.md, graphify/skill-trae.md, graphify/skill-aider.md, graphify/skill-copilot.md, graphify/skill-windows.md</files>
  <action>
  For each of the 9 skill variants listed in `<files>`:

  1. Read the file's top `## Usage` fenced code-block and locate the anchor line:
     `/graphify explain "SwinTransformer"                   # plain-language explanation of a node`
     (The per-file line numbers above are a sanity check; match on content.)

  2. Using the Edit tool, insert the following 3 lines VERBATIM on the line immediately AFTER the anchor, before the closing ``` of the Usage block:

     ```
     /graphify analyze                                      # autoreason tournament: 4 lenses (security, architecture, complexity, onboarding) -> GRAPH_ANALYSIS.md
     /graphify analyze for security and architecture        # subset-lens tournament (any of: security, architecture, complexity, onboarding)
     /graphify analyze for <lens>                           # single-lens tournament (~6 LLM calls vs ~24 for all 4)
     ```

     Alignment detail: each line pads with trailing spaces so the `#` lands at column 55 (1-indexed) — the same column used by the existing `/graphify explain` line. The block above is already padded correctly; do not retype, copy verbatim.

  3. If (and only if) a given skill variant has a stripped-down Usage block (no fenced code-block, no `/graphify explain` anchor, or fewer than ~5 lines of Usage entries): SKIP that file and record it in the SUMMARY under "Files skipped (stripped-down Usage)". Do not attempt to synthesize entries. (Current grep suggests all 9 have a full Usage block with the anchor, but confirm during the edit.)

  Hard constraints (re-read before editing):
  - Do NOT modify the `## For /graphify analyze` section in `graphify/skill.md` around line 1224 (or equivalents in other variants around lines 1081-1162) — the orchestration spec is already correct.
  - Do NOT modify `graphify/__main__.py` or any Python code — `analyze` is a skill-only verb, not a CLI subcommand.
  - Do NOT commit — the orchestrator handles the final commit.
  - Do NOT run `graphify claude install` or propagate skills to `~/.claude/skills/` — the user will do this manually after review.
  - Use ASCII `->` (already in the block), no `→`, no emojis.
  </action>
  <verify>
    <automated>grep -c "^/graphify analyze" graphify/skill.md graphify/skill-codex.md graphify/skill-opencode.md graphify/skill-claw.md graphify/skill-droid.md graphify/skill-trae.md graphify/skill-aider.md graphify/skill-copilot.md graphify/skill-windows.md 2>/dev/null</automated>
  </verify>
  <done>
  - Expected verify output: every file that was edited reports `:3` (three matching lines added); any skipped stripped-down file reports `:0` and is explicitly listed in the SUMMARY.
  - Additional spot-check: `grep -n "autoreason tournament: 4 lenses" graphify/skill*.md` returns one hit per edited file, all inside the top `## Usage` code-block (verify by visual inspection that line number is < 60).
  - `git diff --stat graphify/skill*.md` shows +3 lines per edited file and 0 lines deleted. No file outside `graphify/skill*.md` is touched.
  - The `## For /graphify analyze` orchestration section in `graphify/skill.md` is byte-identical to its pre-edit state: `git diff graphify/skill.md | grep -E "^[-+]" | grep -v "^[-+][-+][-+]" | grep -v "^[+].*# (autoreason|subset-lens|single-lens)"` returns no output.
  </done>
</task>

</tasks>

<verification>
Phase-level checks run once after Task 1 completes:

1. **Entry count across all variants:**
   ```
   grep -c "^/graphify analyze" graphify/skill*.md
   ```
   Expected: each variant that was edited reports `:3`. Any `:0` must correspond to a file explicitly listed as skipped in the SUMMARY.

2. **No accidental edits elsewhere in skill.md:**
   ```
   git diff graphify/skill.md | grep -E "^@@ " | head
   ```
   Expected: a single hunk near line 38, no hunks near line 1224.

3. **No non-skill files modified:**
   ```
   git status --short | grep -v "graphify/skill" | grep -v "^ M .planning/" | grep -v "^?? .planning/"
   ```
   Expected: empty output (only skill*.md and .planning/ changes in the working tree).

4. **ASCII cleanliness:**
   ```
   grep -nP "[^\x00-\x7F]" graphify/skill*.md | grep -i "analyze"
   ```
   Expected: no hits. (If the file already contained non-ASCII elsewhere, that's pre-existing and out of scope.)
</verification>

<success_criteria>
- All 9 skill variants with a top-of-file `## Usage` cheat-sheet list the 3 `/graphify analyze` forms verbatim, with `#` aligned at column 55, inserted directly after the `/graphify explain "SwinTransformer"` line.
- `## For /graphify analyze` orchestration sections (skill.md:1224 and equivalents) are byte-identical to their pre-edit state.
- No Python files, no tests, no `pyproject.toml`, no CLI help output modified.
- No commit created by the plan executor — commit is deferred to the orchestrator.
- SUMMARY lists the exact file set edited and any files skipped (with reason).
</success_criteria>

<output>
After completion, create `.planning/quick/260416-okg-add-graphify-analyze-entries-to-usage-ch/260416-okg-01-SUMMARY.md` covering:
- Files edited (expected: 9)
- Files skipped, if any, with reason (expected: 0)
- Diff stat line (expected: `9 files changed, 27 insertions(+)`)
- Verification command outputs pasted verbatim
- Anything surprising about per-variant Usage block structure
</output>
