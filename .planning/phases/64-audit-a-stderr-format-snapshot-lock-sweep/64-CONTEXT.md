# Phase 64: AUDIT-A — stderr Format Snapshot Lock & Sweep - Context

**Gathered:** 2026-05-06
**Status:** Ready for planning

<domain>
## Phase Boundary

Lock the `[graphify] {error|info}:` + `  hint:` two-line stderr contract via an automated snapshot test BEFORE any reformatting touches the codebase, then migrate one-line outliers to the two-line convention, and enumerate the 7 platform skill regex parsers as a contract-surface fixture so future format changes have a documented breakage signal.

Order is load-bearing: snapshot RED → snapshot GREEN against current main → sweep one-liners → fixture for skill regexes. The snapshot must already pass before any reformatting begins, otherwise the sweep can drift the contract silently.

</domain>

<decisions>
## Implementation Decisions

### Snapshot Mechanism
- **D-01:** Capture the stderr contract as a single golden text file at `tests/fixtures/stderr_contract.txt`. Tests assert exact match. No new test dependencies; PR diffs are human-reviewable; consistent with the existing pure-unit-test convention (CLAUDE.md "Testing Conventions").

### Outlier Sweep Scope
- **D-02:** After the snapshot lands GREEN, grep for `[graphify]` across `graphify/` and migrate every one-liner to the two-line `[graphify] {prefix}: …` + `  hint: …` convention. Known starting outlier: `graphify/__main__.py:~2745` (per ROADMAP success criterion 2). The full surface is bounded — sweep all of it in this phase rather than leaving a known-drift backlog.

### Skill Regex Fixture
- **D-03:** Build a hand-curated Python list of `(platform_name, regex_pattern)` tuples mirrored from each of the 7 SKILL.md files (`skill.md`, `skill-codex.md`, `skill-opencode.md`, `skill-openclaw.md`, `skill-droid.md`, `skill-trae.md`, `skill-trae-cn.md`). Round-trip property: every canonical line in `tests/fixtures/stderr_contract.txt` must be parsed successfully by every regex in the list. Drift detection is by code review when SKILL.md files change — the test will fail closed if a regex no longer matches the contract.

### Prefix Policy
- **D-04:** Lock today's reality: `error:` and `info:` prefixes only. `info:` is mandatory (Phase 63 emits Option B breadcrumbs as `[graphify] info: …` via `emit_option_b_breadcrumb` in `graphify/output.py`). Strict whitelist — adding `warn:`/`debug:` later requires an explicit phase to extend the contract. Forces deliberate stderr-surface evolution.

### Claude's Discretion
- Exact name of the snapshot fixture file (`stderr_contract.txt` is the working name; planner may rename if a project convention dictates otherwise).
- Mechanics of the round-trip parse test (parametrize over `(platform, regex) × line` or split into per-platform tests) — left to planning.
- Whether the snapshot test calls each emitter directly via Python imports, or invokes the CLI as a subprocess and captures stderr — planner decides based on which path keeps tests fast and deterministic.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Phase scope & success criteria
- `.planning/ROADMAP.md` §"Phase 64: AUDIT-A" — goal, depends-on (Phase 63), 4 success criteria, requirement AUDIT-02
- `.planning/REQUIREMENTS.md` — AUDIT-02 row (definitive requirement text)

### Phase 63 forward pointer (mandatory context)
- `.planning/phases/63-vopt-vault-option-b-silent-reroute-explain-paths/63-VERIFICATION.md` — confirms Option B `info:` breadcrumb format that Phase 64 must accept
- `graphify/output.py` `emit_option_b_breadcrumb` — exact `[graphify] info: …` + `  hint: …` shape and `_OPTION_B_BREADCRUMB_EMITTED` sentinel that suppresses double-emission
- `graphify/output.py` `_emit_vault_error` — companion `[graphify] error: …` shape that must also be in the snapshot

### Outlier landmarks
- `graphify/__main__.py:~2745` — known one-liner outlier called out in ROADMAP success criterion 2

### Skill regex contract surface (the 7 platform files)
- `graphify/skill.md` — Claude Code variant
- `graphify/skill-codex.md` — Codex variant
- `graphify/skill-opencode.md` — OpenCode variant
- `graphify/skill-openclaw.md` — OpenClaw variant
- `graphify/skill-droid.md` — Factory Droid variant
- `graphify/skill-trae.md` — Trae variant
- `graphify/skill-trae-cn.md` — Trae CN variant

(Confirm exact filenames during planning — `_PLATFORM_CONFIG` in `graphify/__main__.py` is the source of truth for platform→file mapping.)

### Project guardrails
- `CLAUDE.md` §"Testing Conventions" — pure unit tests, no network, no fs side effects outside `tmp_path`; one test file per module
- `CLAUDE.md` §"Architecture" — `[graphify]` stderr convention is part of the public CLI contract

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `graphify/output.py` already centralizes vault-related stderr emission (`_emit_vault_error`, `_emit_vault_info`, `emit_option_b_breadcrumb`). New snapshot fixtures should source from these helpers rather than re-implementing format strings.
- `tests/fixtures/` already exists as a standard fixture location (per CLAUDE.md "Adding a new language" reference).
- `_PLATFORM_CONFIG` dict in `graphify/__main__.py` enumerates the 7 platforms — use it to drive the regex fixture rather than hard-coding platform names.

### Established Patterns
- All `[graphify] error: …` and `[graphify] info: …` emissions go to **stderr** (never stdout) — pytest captures via `capsys.readouterr().err`.
- Two-line convention: line 1 is `[graphify] {prefix}: <message>`, line 2 is `  hint: <actionable hint>` (two-space indent, no `[graphify]` re-prefix on hint line).
- Phase 63's `_OPTION_B_BREADCRUMB_EMITTED` module-level sentinel demonstrates the project's pattern for suppressing double-emission across gate+resolver paths.

### Integration Points
- New snapshot test file: `tests/test_stderr_contract.py` (one-test-per-module convention; this is a cross-module contract test, so name reflects the contract not a single source module).
- Golden fixture: `tests/fixtures/stderr_contract.txt`.
- Skill regex fixture: lives inside the test file or as `tests/fixtures/skill_regexes.py` — planner decides.
- The sweep PR touches `graphify/__main__.py` at minimum; the full surface is whatever `grep '\[graphify\]' graphify/` returns.

</code_context>

<specifics>
## Specific Ideas

- The snapshot must capture both prefixes seen today: at least one `error:` example (e.g., from `_emit_vault_error`) and at least one `info:` example (Option B breadcrumb from `emit_option_b_breadcrumb`).
- Snapshot should include the multi-line variant where Option B emits a third optional `hint:` line for legacy `graphify-out/` detection (Phase 63 VOPT-02, see commit `f63c0bd`) — that 3-line variant is currently the longest stderr output Phase 64 needs to lock.
- Failure mode the contract is protecting against: a future change reformatting `__main__.py:~2745` from one line to "[graphify] error: x\nhint: y" without the two-space indent on `hint:` — the 7 platform regexes would silently stop matching. The fixture must catch that.

</specifics>

<deferred>
## Deferred Ideas

- **`warn:` / `debug:` stderr prefixes** — explicitly out of scope per D-04. If/when graphify needs new severity levels, a future phase extends the contract (snapshot + skill regexes together).
- **Auto-extracting regexes from SKILL.md files** — considered and rejected for this phase (D-03). Could be revisited if the hand-curated list ever drifts in practice.
- **Fail-closed assertion that no other prefix appears in stderr across the suite** — interesting safety net but noisy if any test emits ad-hoc stderr; defer until/unless we see drift.

</deferred>

---

*Phase: 64-audit-a-stderr-format-snapshot-lock-sweep*
*Context gathered: 2026-05-06*
