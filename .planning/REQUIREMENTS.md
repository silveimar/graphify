# Requirements: Milestone v1.12

**Project:** graphify — Ideaverse Integration (configurable vault adapter)
**Milestone:** v1.12 — Vault Awareness, Pipeline Integration & Error Hygiene
**Audit context:** `.planning/milestones/v1.11-MILESTONE-AUDIT.md` (rec #4 + #5 carry-forward)
**Seed source:** `.planning/seeds/SEED-vault-root-aware-cli.md` (planted 2026-04-27, picked up at v1.12)

## v1.12 Requirements

### Vault-CWD-aware CLI default (VCWD)

- [ ] **VCWD-01**: `graphify` CLI detects whether CWD contains `.obsidian/` (Obsidian vault marker) before pipeline dispatch in `run`, `update-vault`, and any other output-producing command. Detection helper exposed for reuse by `doctor`.
- [ ] **VCWD-02**: When CWD is a vault AND `.graphify/profile.yaml` is present AND no explicit `--vault` / `--output` flag was passed, output is auto-routed via Phase 41's `_resolve_output_target()` (Option C — auto-adopt). Behavior identical to passing `--vault $CWD`.
- [ ] **VCWD-03**: When CWD is a vault but no `.graphify/profile.yaml` is present AND no explicit `--vault` / `--output` / `--write-into-vault` flag was passed, the CLI exits non-zero (exit 2) with two-line `[graphify] error: <msg>` + `  hint: <fix>` stderr (using Phase 58's `_emit_vault_error()`). Hint suggests `--output <path>` outside the vault or `--write-into-vault` to opt in.
- [ ] **VCWD-04**: New `--write-into-vault` opt-in flag added to commands affected by VCWD-03. When present, suppresses the refusal and proceeds with original (pre-v1.12) behavior; documented as deliberate opt-in for users who actually want output inside their vault.
- [ ] **VCWD-05**: `graphify doctor` reports the predicted vault-CWD behavior for the same inputs (auto-adopt vs refuse vs opt-in), maintaining the VAUX-01 parity contract from Phase 58.

### End-to-end pipeline integration tests (E2E)

- [ ] **E2E-01**: Subprocess-level integration test asserts a profile with both `note_type_templates` and `mapping_rule_templates` → `graphify update-vault` produces correctly-classified notes with the override ladder applied. Exercises Phase 55+56 composition end-to-end (block expansion before `${}` substitution, then template ladder resolution). Closes audit Flow 2 gap.
- [ ] **E2E-02**: Subprocess-level integration test asserts `graphify elicit` → sidecar at `artifacts_dir/elicitation.json` → `graphify update-vault` produces a merged graph with elicitation contributions visible in rendered notes. Exercises Phase 57+56 pipeline end-to-end. Closes audit Flow 3 gap.

### Harness error format normalization (HARN-FMT)

- [ ] **HARN-FMT-01**: Harness vault-write refusal at `graphify/__main__.py:2567` migrated from one-line `[graphify] refusing to write harness import...` to Phase 58's two-line `[graphify] error: <msg>` + `  hint: <fix>` format using `_emit_vault_error()`. Existing tests asserting the old stderr substring updated to match the new shape; one-line variant removed entirely.

## Future (deferred past v1.12)

- **Project-wide stderr format sweep** — normalize all remaining `[graphify] ...` stderr emissions to the two-line pattern (only the harness path is in v1.12 scope).
- **Auto-route to hidden `<vault>/.graphify-out/`** (Option B from SEED-vault-root-aware-cli) — explicitly rejected as scope creep; would conflict with the project's "no magic" principle.
- **Drift-protection regression test sweep** — audit the codebase for other intentionally-mirrored constants and add equality tests (the v1.11 pattern from `_SELF_OUTPUT_DIRS` and `_ALLOWED_CONCEPT_CODE_RELATIONS`).
- **SEED-002** — Harness Memory Export (additional target formats, multi-format round-trip)
- **SEED-bidirectional-concept-code-links** — promotion of Phase 53/54 concept↔code work to a richer first-class feature
- **SEED-001** — Tacit-to-Explicit Elicitation Engine (further beyond Phase 57 increment)

## Out of scope

- New vault resolver — must reuse Phase 41's `_resolve_output_target()` (D-09 spirit from v1.11)
- New error-emission helper — must reuse Phase 58's `_emit_vault_error()`
- Precedence policy changes — `--vault` > `GRAPHIFY_VAULT` > `--vault-list` > CWD detection ordering preserved
- Network calls in default CI tests — subprocess tests must hit a `tmp_path` vault, never a remote vault
- Replacing `string.Template` with Jinja2 — rejected milestone-over-milestone

## Traceability

| REQ-ID | Phase | Plan / notes |
|--------|-------|--------------|
| VCWD-01 | Phase 59 | `_is_obsidian_vault(path)` detection helper |
| VCWD-02 | Phase 59 | Auto-adopt path through `_resolve_output_target()` |
| VCWD-03 | Phase 59 | Refusal path via `_emit_vault_error()` with actionable hint |
| VCWD-04 | Phase 59 | `--write-into-vault` opt-in flag |
| VCWD-05 | Phase 59 | Doctor predicts new behavior (parity with VAUX-01) |
| E2E-01 | Phase 60 | Subprocess test for Phase 55+56 composition |
| E2E-02 | Phase 60 | Subprocess test for Phase 57+56 pipeline |
| HARN-FMT-01 | Phase 61 | Migrate `__main__.py:2567` to `_emit_vault_error()` |

*Phase mapping populated by gsd-roadmapper during `/gsd-new-milestone` step 10.*
