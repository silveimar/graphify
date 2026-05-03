# Phase 58: Vault CLI parity & hygiene - Context

**Gathered:** 2026-05-03
**Status:** Ready for planning

<domain>
## Phase Boundary

Lock down the Phase 41 vault CLI surface against three observable contracts; do not add new functionality:

1. **Parity (VAUX-01):** `--vault` / vault discovery and `graphify doctor` agree on the resolved vault, the precedence source label, the profile path & mode, and the diagnostic warnings emitted — for the same inputs.
2. **Actionable errors (VAUX-02):** Vault CLI failures for the three documented categories (unknown vault, ambiguous selection, dry-run mismatch) produce `[graphify] error: …` + `  hint: …` stderr lines and exit non-zero. Asserted by pytest.
3. **Hygiene closure (HYG-01):** Quick-task `260427-rc7-fix-detect-self-ingestion` (already shipped 2026-04-27) is closed in `58-VERIFICATION.md` by citing its SUMMARY + adding a regression-lock test in `tests/test_detect.py`.

No new CLI flags. No new precedence rules (existing precedence is asserted, not changed). No new error-format / JSON output mode. No re-fix or formal waiver of HYG-01 — the patch already shipped.

</domain>

<decisions>
## Implementation Decisions

### VAUX-01 — Parity assertion shape
- **D-01:** Parity strategy = **structured parity helper**. Add a small helper (e.g., `resolve_vault_for_parity(args, env, cwd) -> dict`) that both the CLI dispatch path and `graphify/doctor.py` call. Tests assert both surfaces produce identical dicts for the same inputs. Aligns with Phase 41's `_resolve_output_target()` precedent (`graphify/__main__.py:1315`). NOT golden-text snapshots (brittle), NOT field-by-field inline (boilerplate).
- **D-02:** Parity dimensions asserted (all four): **resolved vault path**, **precedence source label** (e.g., `--vault flag` vs `env GRAPHIFY_VAULT` vs `--vault-list file` vs `CWD .obsidian/`), **profile path & mode** (e.g., `vault-relative` vs `default`), **diagnostic warnings** emitted by the resolver.
- **D-03:** The "diagnostic warnings" dimension implies CLI dispatch and `doctor` must share a warning-emission path (today the global-vs-per-command override note at `__main__.py:1299` is CLI-only). Researcher/planner: surface this in a single helper rather than duplicating the print sites.
- **D-04:** Parity helper lives in `graphify/output.py` or a new `graphify/vault_resolution.py` (planner picks based on existing module weight). Tests live in a new `tests/test_vault_parity.py` module — keeps existing `test_doctor.py` and `test_vault_cli.py` untouched.

### VAUX-02 — Actionable-error contract
- **D-05:** Error format = **stderr text + fix hint**, mirroring `graphify/doctor.py`'s existing `_FIX_HINTS` pattern. Two stderr lines per failure: `[graphify] error: <what failed>` then `  hint: <what to do>`. Tests assert both lines are present and non-empty.
- **D-06:** Exit codes = **single non-zero** for all three categories (use whatever code graphify already emits for argparse / config errors — researcher confirms the existing convention). No per-category exit-code taxonomy. No `--error-format=json` flag.
- **D-07:** Three failure scenarios with concrete definitions:
  - **Unknown vault** — three sub-cases must all be tested: (a) `--vault /nonexistent` (path doesn't exist), (b) `--vault /tmp/dir-without-obsidian` (path exists but no `.obsidian/` marker), (c) `--vault README.md` (path is a file, not a directory).
  - **Ambiguous selection** — primary case: `--vault-list F` where `F` lists 2+ vaults that all match (canonical Phase 41 ambiguity). Secondary cases: (b) global `--vault` and per-command `--vault` disagree, (c) `GRAPHIFY_VAULT` env vs `--vault` flag disagree. **For (b) and (c), Phase 58 keeps existing precedence** (per-command wins; `--vault` wins over env) — tests assert the existing stderr warnings exist, are clearly worded, and match what `doctor` reports. NOT promoted to hard errors. (See D-09.)
  - **Dry-run mismatch** — single case: `graphify doctor --dry-run` predicts a different resolution than a subsequent `graphify run` produces for the same inputs. The VAUX-01 parity helper is the detection vehicle: the test calls the helper from both surfaces' code paths (dry-run mode + actual-run mode) and asserts they agree. Out of scope: dry-run preview file paths vs actual write paths; concurrent vault state changes between dry-run and run.
- **D-08:** Test fixtures reuse `tests/test_doctor.py`'s `_make_vault(tmp_path)` helper pattern (synthetic `.obsidian/` + `.git/` + optional `.graphify/profile.yaml`). DO NOT introduce new fixture infrastructure.

### Behavior change boundary (no breaking changes)
- **D-09:** Phase 58 is **observation-only** for existing precedence behavior. No CLI exit code changes for global-vs-per-command or env-vs-flag conflicts (they remain warnings). No default-error-format changes. The phase locks down what already exists; any precedence policy change would belong in a separate phase with deprecation runway.

### HYG-01 — Quick-task closure evidence
- **D-10:** Closure form = **cite SUMMARY + add regression-lock test**. `58-VERIFICATION.md` references `.planning/quick/260427-rc7-fix-detect-self-ingestion/260427-rc7-SUMMARY.md` and the relevant commit hash. AND Phase 58 adds a regression-lock test in `tests/test_detect.py` asserting that `_is_noise_dir` returns `True` for `"graphify-out"` and `"graphify_out"` (matching the `_SELF_OUTPUT_DIRS` constant set 2026-04-27).
- **D-11:** Existing `tests/test_detect.py` already covers the patch in passing; the new regression-lock test is a **named, intentional guard** so future refactors of `_is_noise_dir` cannot silently drop the self-ingestion exclusion. NOT a formal waiver — the fix shipped, evidence supports closure.

### Claude's Discretion
- Exact module location of the parity helper (`graphify/output.py` extension vs new `graphify/vault_resolution.py`) — planner picks based on existing module size and cohesion.
- Specific name of the parity helper function and the dict schema it returns — researcher proposes; locked in PLAN.
- Whether the regression-lock test name is `test_self_ingestion_dirs_excluded` or similar — planner picks.
- Whether the global-vs-per-command and env-vs-flag conflict tests live in the new `test_vault_parity.py` (close to parity logic) or in `test_vault_cli.py` (close to CLI dispatch) — planner picks.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Phase scope & requirements
- `.planning/ROADMAP.md` §"Phase 58: Vault CLI parity & hygiene" — goal, success criteria, requirement IDs.
- `.planning/REQUIREMENTS.md` — VAUX-01, VAUX-02, HYG-01 definitions and the requirement-to-phase index.

### Prior phase precedent (DO NOT redo this work)
- `.planning/quick/260427-rc7-fix-detect-self-ingestion/260427-rc7-SUMMARY.md` — HYG-01 fix shipped 2026-04-27 (`_SELF_OUTPUT_DIRS` constant + extended `_is_noise_dir`). Cite this in `58-VERIFICATION.md`.
- `.planning/quick/260427-rc7-fix-detect-self-ingestion/260427-rc7-PLAN.md` — original plan for the quick-task.
- `.planning/phases/41-*` (vault CLI from v1.9) — established `_resolve_output_target()` as the shared resolver. Parity work rides on this contract.
- `.planning/milestones/v1.10-ROADMAP.md` — v1.10 close-out narrative (referenced for HYG-01 lineage).

### Code surfaces touched / referenced
- `graphify/__main__.py` lines 1237–1310 — `--vault` / `--vault-list` global+per-command parsing (`_strip_global_vault_flags`, `_strip_per_command_vault_flags`).
- `graphify/__main__.py` line 1294–1299 — per-command override stderr warning (today CLI-only; D-03 says it must move to a shared emission path).
- `graphify/__main__.py` line 1315 — `_resolve_output_target()` Phase 41 single resolver (the hub the parity helper composes around).
- `graphify/__main__.py` lines 1356–1361 — documented precedence: `--vault > GRAPHIFY_VAULT > --vault-list file > CWD .obsidian/ detection`. **Asserted, not changed.**
- `graphify/__main__.py` lines 2807–2911 — `doctor` command dispatch, including resolution + `format_report` invocation.
- `graphify/doctor.py` — `DoctorReport`, `PreviewSection`, `_FIX_HINTS`, `format_report`, `run_doctor`. Source of the error-format pattern (D-05).
- `graphify/output.py` — `ResolvedOutput`, `resolve_output()`. Likely host for the parity helper (D-04).
- `graphify/detect.py` — `_SELF_OUTPUT_DIRS = {"graphify-out", "graphify_out"}`, `_is_noise_dir`. Target of HYG-01 regression-lock test.

### Existing test fixtures (extend, don't duplicate)
- `tests/test_doctor.py` — `_make_vault(tmp_path, *, profile_text=...)` helper (`.obsidian/` + `.git/` + optional `.graphify/profile.yaml`). Reuse for VAUX-01 + VAUX-02 (D-08).
- `tests/test_vault_cli.py` — Phase 41 integration tests using `subprocess`-style invocations of the CLI. Pattern reference for VAUX-02 dry-run mismatch.
- `tests/test_detect.py` — host for the HYG-01 regression-lock test (D-10).
- `tests/test_vault_promote.py` — adjacent vault test patterns.

### New test module (create)
- `tests/test_vault_parity.py` — new module for VAUX-01 + the VAUX-02 ambiguity-warnings parity tests (D-04).

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `_resolve_output_target()` (`graphify/__main__.py:1315`) — Phase 41 single vault/output resolver shared by `run`, `--obsidian`, `doctor`, `elicit`, `import-harness`. Parity helper composes around this.
- `graphify/doctor.py:_FIX_HINTS` — the canonical error-with-hint pattern. VAUX-02 errors mirror this format.
- `_make_vault()` helper in `tests/test_doctor.py` — battle-tested vault fixture (`.obsidian/` + `.git/` markers per RESEARCH §Pitfall 6).
- `_SELF_OUTPUT_DIRS` constant in `graphify/detect.py` — already excludes `graphify-out/` and `graphify_out/` from re-ingestion. HYG-01 just needs a named regression guard pointing at it.

### Established Patterns
- **`[graphify] error: <msg>` + `  hint: <fix>` stderr** — emerging convention from `graphify/doctor.py`. VAUX-02 generalizes to other vault CLI failures.
- **Phase 57 doc-content regression lock pattern** — tests that read documented contracts and assert structural invariants. Reused for HYG-01: a test asserting `_SELF_OUTPUT_DIRS` contains both spellings.
- **Phase 57 AST allowlist meta-test pattern** — applicable if VAUX-01 needs to assert that all callers of `_resolve_output_target()` go through the parity helper. Optional, planner decides.
- **Stderr-warning style** — `[graphify] command --vault / --vault-list overrides global pin` (`__main__.py:1299`). VAUX-02 ambiguity tests assert this string (or its parity-helper-emitted equivalent).

### Integration Points
- VAUX-01 parity helper integrates with `_resolve_output_target()` — must not duplicate resolution logic.
- VAUX-02 dry-run test integrates with `graphify doctor --dry-run` and `graphify run` — uses parity helper as the comparison vehicle.
- HYG-01 regression test integrates with `graphify/detect.py` module constants — pure unit test, no fixtures needed.

</code_context>

<deferred>
## Deferred Ideas (Future Phases)

- **Per-category exit codes for vault errors** (e.g., `ERR_VAULT_AMBIGUOUS = 11`) — explicitly rejected for v1.11; revisit only with a tooling-driven use case.
- **`--error-format=json` flag for structured error output** — flagged as scope creep during discussion; not in v1.11.
- **Hard error on global-vs-per-command --vault conflict** — would break existing scripted users; needs a deprecation runway in a separate phase.
- **Hard error on GRAPHIFY_VAULT vs --vault flag conflict** — same precedence-policy concern; defer.
- **Hard error only when conflicting values genuinely differ (same-path silent, different-path error)** — middle-ground option considered and deferred; adds branch logic to the resolver without clear v1.11 demand.
- **Dry-run preview vs actual write-path mismatch tests** — broader than VAUX-02's intended scope; revisit if vault output paths grow more dynamic.

</deferred>
