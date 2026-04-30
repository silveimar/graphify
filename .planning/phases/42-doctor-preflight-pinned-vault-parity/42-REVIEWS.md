---
phase: 42
reviewers:
  - claude
  - codex  # invoked — failed (401 Unauthorized); see Codex section
reviewed_at: "2026-04-30T17:05:00Z"
plans_reviewed:
  - 42-01-PLAN.md
skipped_reviewers:
  gemini: CLI not installed
  coderabbit: CLI not installed
  opencode: CLI not installed
  qwen: CLI not installed
  cursor: CLI not installed (`cursor` binary)
  ollama: server not reachable
  lm_studio: server not reachable
  llama_cpp: not checked (same pattern as Ollama)
---

# Cross-AI Plan Review — Phase 42

## Gemini Review

*Skipped — `gemini` CLI not found on PATH.*

---

## Claude Review

### Summary

This is a tightly-scoped, well-disciplined gap-closure plan that does exactly what a parity fix should do: change one argument, add one regression test, leave everything else alone. The truth statement (`validate_profile_preflight receives the same vault root as profile_home when Phase 41 pins apply`) is falsifiable and decoupled from the test's wording, which is a strength. The plan correctly identifies the root cause (argument/guard mismatch) from research and resists the temptation to refactor the surrounding resolver logic — that scope is explicitly punted to Phase 41's prior work. The main residual gap is **negative-space coverage**: the test proves the pinned-vault path is validated, but does not pin down behavior when CWD *also* has a `.graphify` and the pinned vault does not, or when `profile_home is None`. VCLI-03 is achieved as written, but a stronger regression suite would prevent future drift.

### Strengths

- **Surgical scope.** One file changed, one argument flipped, one test added. No collateral refactor, no API change. Appropriate for a parity fix.
- **Correct root-cause framing.** Plan diagnoses the bug as a guard/argument mismatch (`profile_home` vs `cwd_resolved`) rather than a resolver issue, which keeps it cleanly orthogonal to Phase 41.
- **Falsifiable invariant.** `must_haves.truths[0]` states the property independently of the test name — a future rewrite of the test still has to honor the invariant.
- **Realistic acceptance check.** `rg` shows `validate_profile_preflight(profile_home)` and no stray `cwd_resolved` call in that block gives the executor a concrete grep-able assertion.
- **Threat model is honest and minimal.** Acknowledges vault_dir remains read-only; doesn't invent threats to look thorough.
- **Verification ladder is right-sized.** Module test first, full suite second — fast feedback before broad confirmation.

### Concerns

- **MEDIUM — Single-direction test coverage.** The regression test proves *pinned-vault errors surface*. It does not prove the *symmetric* invariant: that when `resolved_output` is None or no pin, preflight still validates CWD as before. Without that, a future "fix" that makes preflight always use `profile_home` incorrectly could regress unpinned-vault behavior and the suite might miss it.
- **MEDIUM — Inverse-asymmetry edge case unaddressed.** What happens if CWD has a valid `.graphify` *and* a pinned vault has an invalid one? And the converse — invalid CWD profile, valid pinned vault? The plan's single test covers only "invalid pinned + clean CWD." A two-row parametrized test would lock down the matrix cheaply.
- **LOW — Acceptance check is grep-shaped, not behavior-shaped.** `rg` for the call site is a proxy for correctness; the truth in `must_haves.truths` is the real contract. If someone later wraps the call, the `rg` check breaks while the behavior holds.
- **LOW — `resolved_output=…` semantics unstated.** The plan assumes the executor knows how `ResolvedOutput` triggers `profile_home`; worth one line of setup in the test task.
- **LOW — No assertion on *which* errors surface.** "non-empty `profile_validation_errors`" is weak; asserting at least one error substring from the known invalid profile tightens it.
- **LOW — Plan `depends_on: []` vs roadmap.** Phase 42 logically depends on Phase 41 shipped code. Harmless because 41 is merged, but slightly inconsistent with ROADMAP wording.

### Suggestions

1. **Add a second test case** (or parametrize): unpinned path still runs preflight against CWD — symmetric guard against over-correction.
2. **Tighten assertions** — errors reference expected validator wording or pinned vault path where stable.
3. **Reframe or supplement `rg` acceptance** — pair with behavioral tests as the contract.
4. **One-line setup hint** for `ResolvedOutput` constructor / fields in Task 2.
5. **Document phase-level dependency on 41** for hygiene.

### Risk Assessment

**LOW.** One-argument change in a read-only preflight path; blast radius bounded to `run_doctor`'s preflight block. MEDIUM concerns are about *test durability*, not landing the fix.

**VCLI-03:** Achieved as written; suggestions harden the suite but are not blockers.

---

## Codex Review

**Invocation failed.** `codex exec` streamed logs then exited with **401 Unauthorized** (API/auth). No model review text was returned.

```
ERROR: exceeded retry limit, last status: 401 Unauthorized
```

*Remediation:* ensure Codex CLI is authenticated (`codex login` / OpenAI API key per Codex docs), then re-run `/gsd-review --phase 42 --codex` or paste a manual review into this file.

---

## CodeRabbit Review

*Skipped — `coderabbit` CLI not found on PATH.*

---

## OpenCode Review

*Skipped — `opencode` CLI not found on PATH.*

---

## Qwen Review

*Skipped — `qwen` CLI not found on PATH.*

---

## Cursor Review

*Skipped — `cursor` CLI not found on PATH (Cursor IDE agent is separate from a `cursor` binary).*

---

## Ollama Review

*Skipped — `http://localhost:11434/v1/models` not reachable.*

---

## LM Studio Review

*Skipped — `http://localhost:1234/v1/models` not reachable.*

---

## llama.cpp Review

*Skipped — not invoked (no local server detected in review workflow check).*

---

## Consensus Summary

> **Note:** Only **Claude** produced a full review. Treat consensus as *single-reviewer* unless Codex is re-run after auth.

### Agreed Strengths

- *(Claude)* Surgical gap-closure scope; correct root-cause (guard vs argument); falsifiable `must_haves.truths`; sensible verification ladder; minimal threat model.

### Agreed Concerns

- **Coverage / matrix (Claude, MEDIUM):** Add symmetric coverage for **no pin → CWD preflight** and optional matrix for conflicting CWD vs pinned vault trees.
- **Assertion strength (Claude, LOW):** Prefer specific error substrings over merely non-empty errors.

### Divergent Views

- **Codex:** No substantive review body — auth failure only.

---

## Next steps

1. **Optional hardening** (from Claude): second test for unpinned behavior; stronger assertions; document `depends_on: Phase 41` at phase level.
2. **Re-run reviews:** `codex login` (or fix API key), then `/gsd-review --phase 42 --codex` or `/gsd-review --phase 42 --all` after installing missing CLIs.
3. **Incorporate into plans:** `/gsd-plan-phase 42 --reviews` — only needed if you adopt the optional test-matrix suggestions; implementation may already match the original plan.
