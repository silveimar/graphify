# v3 Platform Compatibility Design

**Date:** 2026-04-06
**Status:** Approved

## Problem

graphify's `skill.md` uses the Claude Code `Agent` tool for parallel semantic extraction. Users on Codex, OpenCode, and OpenClaw cannot use the skill. v3 adds platform-specific skill files so graphify works natively on all four platforms.

## Scope

- Four platform-specific skill files (one already exists)
- `graphify install --platform X` routing
- README clarifications (token efficiency, platform table)
- No always-on project hooks for non-Claude-Code platforms in v3 (deferred to v3.1)

## What Changes Per Platform

The semantic extraction step (Step 3B) is the **only** section that differs. AST extraction, merging, clustering, labelling, export, and benchmarking are identical across all platforms and live in the shared Python CLI.

| Platform | Extraction approach | Rationale |
|----------|-------------------|-----------|
| Claude Code | Parallel `Agent` tool calls | Current behavior, unchanged |
| Codex | Parallel `spawn_agent` + `wait` + `close_agent` | Codex multi-agent API (`multi_agent = true` required) |
| OpenCode | Parallel `@mention` dispatches | OpenCode's native subagent system |
| OpenClaw | Sequential loop — orchestrator extracts each file itself | OpenClaw agent support is MVP/incomplete; sequential is reliable |

## File Structure

```
graphify/
├── skill.md            # Claude Code (unchanged)
├── skill-codex.md      # Codex — parallel via spawn_agent
├── skill-opencode.md   # OpenCode — parallel via @mention
├── skill-claw.md       # OpenClaw — sequential extraction
```

All four files ship in the PyPI package via `pyproject.toml` `package-data`.

## Install Command

`graphify install` gains a `--platform` flag:

```
graphify install                     # Claude Code → ~/.claude/skills/graphify/SKILL.md
graphify install --platform codex    # Codex       → ~/.agents/skills/graphify/SKILL.md
graphify install --platform opencode # OpenCode    → ~/.config/opencode/skills/graphify/SKILL.md
graphify install --platform claw     # OpenClaw    → ~/.claw/skills/graphify/SKILL.md
```

Behaviour:
- Creates target directory if it doesn't exist (same as current Claude Code install)
- If the platform's root config directory doesn't exist, prints a warning and exits cleanly: `"Codex config directory not found — is Codex installed?"`
- `--platform` is optional; default is `claude` (current behaviour preserved)

## Skill File Content

Each file follows the same structure as `skill.md`. The extraction step (Step 3B) is rewritten for the platform:

**Codex (`skill-codex.md`):**
- For each uncached file, call `spawn_agent(agent_type="worker", message=<extraction prompt>)`
- Collect all agent handles, call `wait()` on each, then `close_agent()`
- Requires user to have `multi_agent = true` in `~/.codex/config.toml`; skill notes this requirement

**OpenCode (`skill-opencode.md`):**
- For each uncached file, dispatch via `@mention` with the extraction prompt
- Collect results as agents complete

**OpenClaw (`skill-claw.md`):**
- Loop over uncached files sequentially
- Orchestrating LLM reads each file and extracts concepts/relationships/edges directly
- Slower than parallel platforms but reliable given OpenClaw's MVP agent status
- A note in the skill explains why: "OpenClaw's multi-agent support is still early; sequential extraction ensures reliability"

## README Changes

1. Add "Platform support" table under the Install section
2. Clarify token efficiency: *"First run extracts and builds the graph — subsequent queries read the compact graph instead of raw files. The 71.5x reduction applies per query, and the cache means re-runs only re-process changed files."*
3. Note sequential extraction on OpenClaw with brief explanation

## Not In Scope (v3)

- `graphify codex install` / `graphify opencode install` (always-on project hooks for non-CC platforms) — deferred to v3.1
- Gemini CLI support — not enough information yet
- Copilot CLI support — not enough information yet

## Testing

- Unit tests in `tests/test_install.py`: verify `--platform X` routes to correct source file and target path
- Package data test: assert all four skill files are present in the installed package
- No execution tests for platform-specific extraction (requires live platform)
- Evals before release: run each platform skill on a real corpus, verify graph output is equivalent
